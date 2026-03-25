import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from openai import OpenAI
import config
from market_discovery import Market
from logger_setup import get_logger, log_decision

log = get_logger("market_analyzer")

# Lazy singleton client
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=config.OPENAI_API_KEY)
    return _client


ANALYSIS_PROMPT = """You are an expert prediction market analyst and superforecaster.

Analyze this prediction market and estimate the TRUE probability of the outcome.

## Market Details
- **Question**: {question}
- **Description**: {description}
- **Category**: {category}
- **Current YES price**: {yes_price:.3f} (market implied probability: {yes_price:.1%})
- **Current NO price**: {no_price:.3f}
- **24h Volume**: ${volume_24h:,.0f}
- **Liquidity**: ${liquidity:,.0f}
- **Resolution Date**: {end_date}
- **Today's Date**: {today}

## Your Task
1. SEARCH for the latest news, polls, data relevant to this question
2. Think about base rates, reference classes, and relevant evidence
3. Consider both sides of the argument
4. Estimate the TRUE probability (not the market price)
5. Assess your confidence in your estimate

## Response Format (JSON only)
{{
    "estimated_probability": <float 0.0-1.0>,
    "confidence": <float 0.0-1.0>,
    "reasoning": "<2-3 sentence explanation>",
    "key_factors": ["<factor1>", "<factor2>", "<factor3>"],
    "information_edge": "<what info might the market be missing or overweighting>",
    "sources_consulted": ["<url or description of source>"]
}}

Respond with ONLY valid JSON, no other text."""


@dataclass
class MarketAnalysis:
    market_id: str
    question: str
    market_price: float
    estimated_prob: float
    confidence: float
    edge: float
    reasoning: str
    key_factors: list[str]
    information_edge: str
    raw_response: dict
    sources: list[str] = field(default_factory=list)


def _extract_json_from_response(text: str) -> dict:
    """Extract JSON from response text that may contain extra content."""
    raw_text = text.strip()

    # Try direct parse first
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        pass

    # Handle markdown code blocks
    if "```" in raw_text:
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass

    # Find JSON object in text
    match = re.search(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", raw_text, re.DOTALL)
    if match:
        return json.loads(match.group(0))

    raise json.JSONDecodeError("No valid JSON found in response", raw_text, 0)


def analyze_market(market: Market) -> MarketAnalysis | None:
    """Use OpenAI to analyze a market and estimate true probability."""
    if not config.OPENAI_API_KEY:
        log.warning("No OPENAI_API_KEY set, skipping LLM analysis")
        return None

    client = _get_client()

    from datetime import date
    prompt = ANALYSIS_PROMPT.format(
        question=market.question,
        description=market.description[:1000],
        category=market.category,
        yes_price=market.yes_price,
        no_price=market.no_price,
        volume_24h=market.volume_24h,
        liquidity=market.liquidity,
        end_date=market.end_date,
        today=date.today().isoformat(),
    )

    try:
        kwargs = dict(
            model=config.OPENAI_MODEL,
            input=prompt,
        )

        if config.ENABLE_WEB_SEARCH:
            kwargs["tools"] = [{"type": "web_search"}]

        response = client.responses.create(**kwargs)
        result = _extract_json_from_response(response.output_text)

        estimated_prob = float(result["estimated_probability"])
        confidence = float(result.get("confidence", 0.5))
        edge = estimated_prob - market.yes_price
        sources = result.get("sources_consulted", [])

        analysis = MarketAnalysis(
            market_id=market.id,
            question=market.question,
            market_price=market.yes_price,
            estimated_prob=estimated_prob,
            confidence=confidence,
            edge=edge,
            reasoning=result.get("reasoning", ""),
            key_factors=result.get("key_factors", []),
            information_edge=result.get("information_edge", ""),
            raw_response=result,
            sources=sources,
        )

        log_decision(log, "market_analysis", {
            "market_id": market.id,
            "question": market.question[:80],
            "market_price": market.yes_price,
            "estimated_prob": estimated_prob,
            "edge": edge,
            "confidence": confidence,
            "web_search": config.ENABLE_WEB_SEARCH,
            "sources_count": len(sources),
        })

        log.info(
            f"Analyzed '{market.question[:60]}': "
            f"market={market.yes_price:.2f}, est={estimated_prob:.2f}, "
            f"edge={edge:+.2f}, conf={confidence:.2f}, "
            f"sources={len(sources)}"
        )
        return analysis

    except json.JSONDecodeError as e:
        log.error(f"Failed to parse OpenAI response for {market.question[:50]}: {e}")
        return None
    except Exception as e:
        log.error(f"Analysis failed for {market.question[:50]}: {e}")
        return None


def batch_analyze(markets: list[Market], max_workers: int = 4) -> list[MarketAnalysis]:
    """Analyze multiple markets in parallel, returning valid analyses."""
    analyses = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(analyze_market, m): m for m in markets}
        for future in as_completed(futures):
            market = futures[future]
            try:
                analysis = future.result()
                if analysis:
                    analyses.append(analysis)
            except Exception as e:
                log.error(f"Parallel analysis failed for {market.question[:50]}: {e}")
    return analyses
