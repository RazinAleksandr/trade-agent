# Feature Research

**Domain:** Autonomous prediction market trading agent with multi-agent Claude architecture
**Researched:** 2026-03-25
**Confidence:** MEDIUM-HIGH (core trading features HIGH; multi-agent LLM specifics MEDIUM)

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features the system must have to function at a basic level. Missing these = system is not an autonomous trading agent.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Market discovery and filtering | Agent must find tradeable markets from Gamma API — no markets, no trading | LOW | Filter by volume, liquidity, spread, price range. Existing `market_discovery.py` is reference. |
| Probability estimation per market | Core trading signal — need "true probability" vs market price to identify edge | HIGH | Claude sub-agent (Analyst) replaces GPT-4o. Must use real-time search via web tools. |
| Edge calculation | `edge = estimated_probability - market_price`. No edge, no trade. | LOW | Threshold filter (e.g. >10%) gates all trade decisions. |
| Kelly criterion position sizing | Industry-standard method for sizing positions with known edge + win probability | LOW | Quarter Kelly (0.25x) for safety. Existing `strategy.py` has working implementation. |
| Paper trading mode | Safe-by-default — operator must not risk real funds during development/validation | LOW | Must be the default. Live mode requires explicit opt-in config change. |
| Order execution (paper + live) | Agent decisions must result in actual order placement or simulated fills | MEDIUM | py-clob-client for live, in-memory simulation for paper. Existing `trader.py` is reference. |
| Position tracking and P&L | Know what you hold, at what cost, current value, unrealized/realized P&L | MEDIUM | Required for risk checks and Reviewer sub-agent analysis. Existing `portfolio.py` is reference. |
| Persistent trade history | Without history, agent cannot learn, Reviewer cannot analyze, operator cannot audit | LOW | SQLite. Existing `data_store.py` schema is good reference. |
| Configurable parameters | Edge threshold, Kelly fraction, max position size, max exposure — must be tunable | LOW | All in a config file/env vars. No hardcoded values elsewhere. |
| Cycle scheduling | Agent must run on a schedule without manual triggering | LOW | Cron or Python scheduler. Configurable interval (hourly, daily, etc.). |
| Graceful shutdown | Long-running process needs clean SIGINT/SIGTERM handling | LOW | Finish current cycle before exit. Existing `main.py` has working pattern. |
| Per-cycle execution log | Operator must be able to see what happened in any given cycle | LOW | Structured logging. Dual output: human-readable console + JSON file. |

### Differentiators (Competitive Advantage)

These are what make this system meaningfully better than a simple rules-based bot. They map directly to the project's core value: autonomous improvement over time.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Multi-agent specialization (Scanner, Analyst, Risk Manager, Planner, Reviewer) | Each sub-agent has a focused prompt and context — produces better decisions than a single monolithic agent doing everything | HIGH | The 5-agent design mirrors real trading firm structure (TradingAgents research confirms this pattern outperforms single-agent). Uses Claude Code Task tool. |
| Strategy document that evolves each cycle | Agent builds and refines its own playbook — encodes what works, prunes what doesn't — without human intervention | HIGH | Markdown file. Main agent reads it before cycle, Reviewer proposes updates, main agent writes new version. Unique to LLM-native agents. |
| Per-cycle markdown trade reports | Human-readable audit trail + machine-readable context for future cycles. Agent learns from its own written analysis. | MEDIUM | Reviewer sub-agent writes structured report: trades taken, reasoning, outcomes, what to do differently. Stored in `.planning/reports/`. |
| Planner sub-agent (strategy → concrete trade plan) | Translates abstract strategy rules into specific actions for the current cycle's market conditions | MEDIUM | Reduces main agent context bloat; keeps strategy abstract and plans concrete. |
| Bull/Bear Researcher debate pattern | Structured disagreement surfaces risks the analyst alone would miss | HIGH | Optional enhancement to Analyst sub-agent — one persona argues for the trade, one argues against. TradingAgents research validates this improves decision quality. |
| Confidence-weighted position sizing | Scale position size not just by Kelly but also by agent confidence level in its own probability estimate | MEDIUM | Low-confidence estimates get smaller positions. Reduces risk of acting on uncertain analysis. |
| Resolved market detection and P&L finalization | Automatically detects when markets resolve and locks in realized P&L — critical for learning signal | MEDIUM | Checks CLOB API for settled prices. Existing `portfolio.py` has this logic. |
| Strategy evolution history | Keep a log of every strategy update — shows how the agent's thinking changed over time | LOW | Append-only file or dated snapshots. Enables debugging of strategy regressions. |
| Market correlation awareness | Avoid over-exposure to correlated outcomes (e.g., multiple markets resolving on same event) | HIGH | Risk Manager sub-agent responsibility. Polymarket has many correlated markets. |
| Negative-risk market handling | Neg-risk markets use a separate exchange contract on-chain — must be explicitly supported for full market coverage | MEDIUM | Existing `trader.py` and `setup_wallet.py` handle this. Cherry-pick, don't reinvent. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that appear valuable but create more problems than they solve for this project.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Web UI / dashboard | "I want to see my trades visually" | Adds frontend complexity, build time, and maintenance burden with no impact on trading quality. Out of scope per PROJECT.md. | Per-cycle markdown reports in `.planning/reports/`. Readable in any text editor or GitHub. |
| Real-time streaming / WebSocket market feeds | "Capture faster price moves" | This system is batch-cycle (scheduled intervals), not HFT. Streaming adds complexity for no gain on hourly/daily cycles. Out of scope per PROJECT.md. | Snapshot-based price fetching at cycle start is sufficient for the analysis horizon. |
| Backtesting engine | "Test strategy on historical data before running live" | Historical Polymarket data is sparse and hard to obtain. Strategy starts blank and learns from paper trading — which IS the backtesting loop. Out of scope per PROJECT.md. | Paper trading mode with full cycle reporting serves as the validation environment. |
| Human approval per trade | "I want to review trades before execution" | Eliminates the autonomous value. Requires human availability. Creates decision fatigue. | Strategy document + per-cycle reports give full transparency. Human reviews reports, not individual trades. |
| Multi-exchange support | "Trade Kalshi too" | Doubles API integration complexity. Splits agent attention. Each exchange has different market types, resolution rules, and API auth. Out of scope per PROJECT.md. | Go deep on Polymarket first. Cross-exchange is a future milestone. |
| Reinforcement learning / model fine-tuning | "Train the model on outcomes" | Requires ML infrastructure, training pipelines, and model versioning. Claude's in-context learning via strategy evolution achieves the same goal with zero infrastructure. | Strategy document evolution IS the learning mechanism. No gradient descent needed. |
| Copy trading / whale following | "Follow profitable wallets" | Reactive strategy with no edge analysis. Exposes to front-running and adverse selection. Conflicts with the goal of building own analytical edge. | Build analytical edge through the Analyst sub-agent. Copy trading is a separate product category. |
| Sentiment analysis via social media scraping | "Track Twitter/Reddit signals" | Requires API access, rate limit management, NLP pipeline. Claude sub-agents already analyze text signals via web search during market analysis. | Analyst sub-agent's web search covers relevant sentiment signals without dedicated scraping infrastructure. |
| Per-trade stop-loss / take-profit orders | "Automatically exit positions" | Prediction markets are binary and illiquid — positions resolve at the market resolution date. Exit before resolution requires finding a counterparty. GTC limit orders are already the right mechanism. | Set conservative max position sizes and exposure limits instead of trying to dynamically exit. |
| Cross-exchange arbitrage | "Profit from price differences between Polymarket and Kalshi" | Requires multi-exchange accounts, liquidity on both sides, tight execution timing, and compliance across jurisdictions. Extremely complex for marginal gain. | Find edge within Polymarket's own markets rather than cross-exchange spreads. |

---

## Feature Dependencies

```
[Market Discovery + Filtering]
    └──requires──> [Gamma API integration]
    └──enables──> [Scanner Sub-Agent]

[Edge Calculation]
    └──requires──> [Probability Estimation (Analyst Sub-Agent)]
    └──requires──> [Market Discovery] (needs market prices)

[Kelly Position Sizing]
    └──requires──> [Edge Calculation]
    └──requires──> [Portfolio State] (to know current exposure)

[Trade Execution]
    └──requires──> [Kelly Position Sizing]
    └──requires──> [Paper/Live Mode Config]
    └──requires──> [CLOB API + py-clob-client]

[Portfolio Tracking + P&L]
    └──requires──> [Trade Execution] (must record what was executed)
    └──requires──> [Persistent Trade History]

[Resolved Market Detection]
    └──requires──> [Portfolio Tracking]
    └──enhances──> [Trade Reviewer analysis] (needs final P&L to assess quality)

[Per-Cycle Markdown Reports]
    └──requires──> [Trade Execution results]
    └──requires──> [Portfolio Tracking]
    └──enables──> [Strategy Evolution]

[Strategy Document Evolution]
    └──requires──> [Per-Cycle Markdown Reports]
    └──requires──> [Trade Reviewer Sub-Agent]
    └──feeds──> [Planner Sub-Agent] (next cycle reads updated strategy)

[Multi-Agent Orchestration]
    └──requires──> [Claude Code CLI + Task tool]
    └──requires──> [Instrument Layer tools] (agents call Python via Bash)

[Planner Sub-Agent]
    └──requires──> [Strategy Document]
    └──requires──> [Scanner output]
    └──enhances──> [Overall cycle coherence]

[Risk Manager Sub-Agent]
    └──requires──> [Portfolio State]
    └──requires──> [Kelly Sizing output]
    └──enhances──> [Trade Execution] (final gating before trade)

[Confidence-Weighted Sizing]
    └──requires──> [Kelly Position Sizing]
    └──requires──> [Analyst Sub-Agent confidence output]

[Market Correlation Awareness]
    └──requires──> [Market Discovery] (need list of all open positions)
    └──requires──> [Portfolio Tracking]
    └──part-of──> [Risk Manager Sub-Agent]

[Strategy Evolution History]
    └──requires──> [Strategy Document Evolution]
    └──enhances──> [Debugging and operator visibility]
```

### Dependency Notes

- **Trade Execution requires Kelly Sizing:** Never execute without a sized position — the sizing IS the risk management.
- **Strategy Evolution requires Per-Cycle Reports:** The Reviewer reads reports to propose updates. Without reports, evolution is blind.
- **Risk Manager Sub-Agent requires Portfolio State:** Risk check with no knowledge of current exposure is meaningless.
- **Multi-Agent Orchestration requires Instrument Layer:** Sub-agents have no execution capability themselves — they call Python tools via Bash.
- **Planner and Reviewer conflict if run simultaneously:** Planner sets the plan at cycle start; Reviewer reviews results at cycle end. They are sequential, not parallel.

---

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to run one full autonomous cycle end-to-end and learn from it.

- [ ] Instrument layer: market discovery, probability-estimating Analyst call, Kelly sizing, paper trade execution, portfolio tracking, SQLite persistence
- [ ] Agent layer: main agent + 5 sub-agents (Scanner, Analyst, Risk Manager, Planner, Reviewer) via Claude Code Task tool
- [ ] Strategy document: starts blank, main agent writes and updates after each cycle
- [ ] Per-cycle markdown reports: Reviewer writes structured report each cycle
- [ ] Configurable parameters: edge threshold, Kelly fraction, max position, max exposure via config file
- [ ] Scheduling: cron-triggered cycle execution at configurable interval
- [ ] Paper trading mode as default, live mode requires explicit config opt-in
- [ ] Persistent trade history and portfolio state in SQLite

### Add After Validation (v1.x)

Features to add once the core cycle is working and producing useful analysis.

- [ ] Strategy evolution history (dated snapshots) — add when strategy starts diverging enough to want to track regressions
- [ ] Confidence-weighted position sizing — add when Analyst sub-agent outputs are stable enough to trust confidence scores
- [ ] Bull/Bear researcher debate within Analyst — add when probability estimates show high variance or repeated errors
- [ ] Resolved market detection and P&L finalization — add when first markets resolve during paper trading validation

### Future Consideration (v2+)

Features to defer until there is evidence the core system works well.

- [ ] Market correlation awareness in Risk Manager — defer until portfolio grows large enough to have correlated exposure
- [ ] Live trading mode validation and hardening — defer until paper trading shows positive edge over statistically meaningful sample
- [ ] Enhanced market filtering heuristics (timing-to-resolution scoring, liquidity depth analysis) — defer until Scanner produces too many low-quality candidates

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Instrument layer (discovery, execution, portfolio) | HIGH | MEDIUM | P1 |
| Multi-agent orchestration (5 sub-agents) | HIGH | HIGH | P1 |
| Strategy document + evolution | HIGH | MEDIUM | P1 |
| Per-cycle markdown reports | HIGH | LOW | P1 |
| Paper trading mode | HIGH | LOW | P1 |
| Configurable parameters | HIGH | LOW | P1 |
| Persistent trade history (SQLite) | HIGH | LOW | P1 |
| Cycle scheduling | MEDIUM | LOW | P1 |
| Kelly + confidence-weighted sizing | MEDIUM | MEDIUM | P2 |
| Resolved market detection | MEDIUM | MEDIUM | P2 |
| Strategy evolution history | MEDIUM | LOW | P2 |
| Bull/Bear researcher debate | MEDIUM | MEDIUM | P2 |
| Market correlation awareness | LOW | HIGH | P3 |
| Live trading hardening | MEDIUM | HIGH | P3 |
| Enhanced market filtering heuristics | LOW | MEDIUM | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

---

## Competitor Feature Analysis

| Feature | Polystrat (Olas) | OpenClaw / PolyWin | Our Approach |
|---------|------------------|--------------------|--------------|
| Market analysis engine | LLM + custom workflows | Multi-layer AI (macroeconomic + sentiment + news) | Claude sub-agent (Analyst) with web search |
| Position sizing | Not disclosed | Multi-layer risk (5% max per event) | Quarter Kelly with configurable fraction |
| Reporting | Not disclosed | Real-time monitoring dashboard | Per-cycle markdown reports (no UI) |
| Strategy evolution | Inferred from live performance | Configurable parameters | Explicit markdown strategy document that agent reads and writes |
| Execution | Autonomous 24/7 | Sub-100ms automated execution | Scheduled cycles (not real-time) |
| Multi-agent structure | Not public | Multiple specialized agents | 5 named sub-agents with explicit roles |
| Operator control | Plain-English goal setting | Alert configuration | Config file parameters, paper trading default |

---

## Sources

- [AI agents are quietly rewriting prediction market trading — CoinDesk, March 2026](https://www.coindesk.com/tech/2026/03/15/ai-agents-are-quietly-rewriting-prediction-market-trading)
- [Best Polymarket Trading Bots 2026 — Medium / Steven Hansen](https://medium.com/@stevenn.hansen/best-polymarket-trading-bots-for-automated-prediction-market-strategies-in-2026-bf06df02823b)
- [The Definitive Guide to the Polymarket Ecosystem — DeFiPrime](https://defiprime.com/definitive-guide-to-the-polymarket-ecosystem)
- [TradingAgents: Multi-Agents LLM Financial Trading Framework — arXiv 2412.20138](https://arxiv.org/abs/2412.20138)
- [Orchestration Framework for Financial Agents — arXiv 2512.02227](https://arxiv.org/html/2512.02227v1)
- [TradingGroup: Multi-Agent Trading with Self-Reflection — arXiv 2508.17565](https://arxiv.org/html/2508.17565v1)
- [Claude Code Multi-Agent Orchestration Docs](https://code.claude.com/docs/en/agent-teams)
- [IOSG: Prediction Market Agents as New Product Form 2026 — KuCoin](https://www.kucoin.com/news/flash/iosg-prediction-market-agents-to-emerge-as-new-product-form-in-2026)
- [TradeTrap: Are LLM-based Trading Agents Truly Reliable? — arXiv 2512.02261](https://arxiv.org/html/2512.02261v1)
- [Beyond Simple Arbitrage — 4 Polymarket Strategies — Medium/ILLUMINATION](https://medium.com/illumination/beyond-simple-arbitrage-4-polymarket-strategies-bots-actually-profit-from-in-2026-ddacc92c5b4f)
- [Polymarket CLOB API Docs](https://docs.polymarket.com/developers/CLOB/introduction)
- [Kelly Criterion Applications — QuantConnect Research](https://www.quantconnect.com/research/18312/kelly-criterion-applications-in-trading-systems/)

---

*Feature research for: Autonomous prediction market trading agent (Polymarket, multi-agent Claude)*
*Researched: 2026-03-25*
