# Stack Research

**Domain:** Autonomous multi-agent prediction market trading system
**Researched:** 2026-03-25
**Confidence:** HIGH (all key choices verified against official docs and PyPI)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12.x | Instrument layer — all trading tools, API clients, data persistence | Type hint improvements (PEP 695), faster interpreter, already in use and working |
| Claude Code CLI (`claude`) | Latest stable | Agent layer runtime — main agent + sub-agents via Task/Agent tool | Only runtime that natively supports the Task/Agent tool for spawning specialized sub-agents; Claude Code's headless `-p` flag enables fully non-interactive invocation for scheduling |
| `claude-agent-sdk` | 0.1.50 | Programmatic invocation of Claude Code agents from Python scheduler | Official Anthropic SDK; `query()` and `ClaudeSDKClient` APIs give Python control over agent sessions without subprocess management; supports async streaming, permission callbacks, custom MCP tools |
| SQLite3 (stdlib) | 3.49.1 (bundled) | Trade history, position state, strategy metrics | Zero external deps, single-file, survives process restarts; WAL mode enables safe concurrent access from scheduler + agent; already proven in existing codebase |
| Markdown files | — | Strategy doc, per-cycle reports, sub-agent definitions | Human-readable audit trail; Claude reads/writes natively without parsing overhead; strategy evolution is observable in git diff |

### Polymarket-Specific Libraries

| Library | Version | Purpose | Why Recommended |
|---------|---------|---------|-----------------|
| `py-clob-client` | 0.34.6 | Polymarket CLOB order placement, L2 credential derivation, orderbook data | Official Polymarket Python client; handles EIP-712 signing, GTC limit orders, API authentication; existing working integration in codebase |
| `requests` | 2.33.0 | Gamma API HTTP calls for market discovery | Synchronous simplicity matches batch trading cycle; Gamma API is REST, no streaming needed; existing working integration |
| `web3` | 7.14.1 | Polygon RPC — USDC approvals, CTF setApprovalForAll for live mode | Required for live trading setup only; one-time allowance transactions; existing working integration |
| `eth-account` | 0.13.7 | EOA wallet generation, account management, signing | Required for live trading credential setup; `signature_type=0` for EOA wallets |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `python-dotenv` | 1.2.2 | `.env` file loading for secrets and config | Always — ANTHROPIC_API_KEY, PRIVATE_KEY, and all trading parameters |
| `APScheduler` | 3.11.2 | Cron-style scheduling of trading cycles | When running as a long-lived daemon process; `BackgroundScheduler` with `IntervalTrigger` or `CronTrigger`; supports SQLite job store for persistence across restarts |
| `schedule` | 1.2.2 | Lightweight interval scheduling | Alternative to APScheduler if you want minimal deps and a simple `while True` loop with `schedule.run_pending()` |
| `anthropic` | 0.86.0 | Direct Anthropic API access (analysis, tool use) | Only if building analysis tools that call Claude API directly from Python (not via Claude Code CLI); generally prefer Claude Code CLI for agent layer |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| `pip` + `requirements.txt` | Package management | No build step needed; pin exact versions for reproducibility |
| Python `venv` (stdlib) | Dependency isolation | `.venv/` at project root; activate before all runs |
| Python `unittest` (stdlib) | Test runner | Existing `tests/test_paper_trading.py` pattern; no pytest needed for smoke tests |
| `sqlite3` CLI | Database inspection | `sqlite3 trading.db .tables` for debugging state |

---

## Installation

```bash
# Core instrument layer
pip install py-clob-client==0.34.6 requests==2.33.0 python-dotenv==1.2.2

# Agent layer integration
pip install claude-agent-sdk==0.1.50 anthropic==0.86.0

# Scheduling
pip install APScheduler==3.11.2

# Live trading only (skip for paper trading)
pip install web3==7.14.1 eth-account==0.13.7
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `claude-agent-sdk` | `subprocess.Popen(["claude", "-p", ...])` | When you need extreme control over process lifecycle, or claude-agent-sdk has a blocking issue; subprocess is more reliable on Windows but loses structured output typing |
| `APScheduler` | System `cron` + shell scripts | When deploying on Linux server with stable cron infrastructure; simpler ops but requires external process management; can't dynamically adjust cycle frequency |
| `APScheduler` | `schedule` library | When you want the simplest possible loop and don't need cron expressions, job persistence, or parallel job execution |
| `requests` | `httpx` | When you need async HTTP (e.g., async trading cycle); `requests` is simpler for synchronous batch flow |
| SQLite3 | PostgreSQL | Only if multi-process writes become a bottleneck (>100 writes/second) or you need remote access; SQLite with WAL mode handles this project's load easily |
| Markdown files (strategy) | Database-backed strategy | Markdown wins because Claude reads/writes it natively, it's diffable in git, and human-readable for debugging strategy evolution |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `openai` SDK for agent analysis | The new architecture uses Claude (not GPT-4o) for all analysis; adding OpenAI creates dual-LLM complexity | Claude Code sub-agents via Task/Agent tool handle market analysis |
| LangChain / LangGraph | Framework overhead adds indirection over direct Claude Code API; not needed when Claude Code's Task tool IS the orchestration layer | Direct Claude Code CLI + `claude-agent-sdk` |
| `asyncio` event loop for instrument layer | Gamma API and CLOB API are synchronous REST; adding async complexity buys nothing for batch cycles | Synchronous `requests` + `py-clob-client` |
| OpenAI Responses API `web_search` tool | Architecture shift: Claude sub-agents do the research now, not Python calling OpenAI | Claude Code sub-agent with Bash/WebSearch tools |
| `celery` + Redis task queue | Massive operational overhead for a single-machine autonomous agent; APScheduler or cron is sufficient | APScheduler |
| `pandas` / `numpy` | No time-series analysis needed for prediction market trading; Kelly criterion math is pure Python | Plain Python `dataclasses` + stdlib `math` |

---

## Stack Patterns by Variant

**Paper trading mode (default):**
- No `web3` or `eth-account` needed at runtime
- No `PRIVATE_KEY` in `.env`
- Instrument layer records trades to SQLite only
- All other components identical to live mode

**Live trading mode:**
- Add `web3` + `eth-account` for one-time wallet setup (`setup_wallet.py`)
- `PAPER_TRADING=false` in `.env`
- `py-clob-client` routes orders to CLOB API instead of simulating
- NEVER enable without explicit user request

**Scheduled autonomous mode (recommended deployment):**
- APScheduler `BackgroundScheduler` with `CronTrigger` or `IntervalTrigger`
- `claude-agent-sdk` `query()` invokes the main agent each cycle
- Main agent spawns sub-agents via the Task/Agent tool (internal to Claude Code)
- Scheduler process stays alive; agent sessions are ephemeral per cycle

**Development / debugging mode:**
- `claude -p "run trading cycle" --allowedTools "Bash,Read,Write"` — one-shot manual invocation
- `--output-format json` for structured output inspection
- `--bare` flag skips hook/plugin discovery for faster startup

---

## Agent Layer Architecture Details

The Claude Code agent layer works differently from traditional Python orchestration:

**Sub-agent invocation** is internal to Claude Code — the main agent calls the `Task` tool (also called `Agent` tool in newer versions) to spawn sub-agents. This is NOT a Python API call. The main agent's CLAUDE.md prompt defines the sub-agents and when to use them.

**Sub-agent definitions** live in `.claude/agents/` as Markdown files with YAML frontmatter:
```yaml
---
name: market-scanner
description: Finds and filters interesting markets from Gamma API
tools: Bash, Read
model: sonnet
---
You are a market scanner. Call the Python instrument tools via Bash...
```

**Instrument tool invocation** from sub-agents uses Bash:
```bash
python market_tools.py fetch-markets --min-volume 10000
```

**Scheduling triggers the main agent** via claude-agent-sdk:
```python
from claude_agent_sdk import query, ClaudeAgentOptions
async for msg in query("Run trading cycle", options=ClaudeAgentOptions(
    allowed_tools=["Bash", "Read", "Write"],
    cwd="/path/to/project"
)):
    ...
```

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `py-clob-client==0.34.6` | Python 3.9–3.12 | Existing codebase tested on 3.12.9; `signature_type=0` required for EOA wallets |
| `web3==7.14.1` | Python 3.8–3.12 | Breaking changes from web3 5.x → 6.x → 7.x; existing code uses 7.x API |
| `claude-agent-sdk==0.1.50` | Python 3.8+ (async) | Requires `asyncio`; wrap in `asyncio.run()` when calling from sync APScheduler |
| `APScheduler==3.11.2` | Python 3.7+ | Use 3.x branch (not 4.x alpha); 4.x has different API and is not production-ready |
| `anthropic==0.86.0` | Python 3.8+ | Only needed if directly calling Anthropic API from Python; not needed for Claude Code CLI path |

---

## Sources

- `https://code.claude.com/docs/en/sub-agents` — Sub-agent file format, frontmatter fields, tool restrictions, model selection (HIGH confidence)
- `https://code.claude.com/docs/en/agent-teams` — Agent Teams vs sub-agents distinction, token costs, architecture (HIGH confidence)
- `https://code.claude.com/docs/en/headless` — Claude Code `-p` flag, `--bare` mode, `--allowedTools`, output formats (HIGH confidence)
- `https://platform.claude.com/docs/en/agent-sdk/python` — `claude-agent-sdk` Python API: `query()`, `ClaudeSDKClient`, `ClaudeAgentOptions` (HIGH confidence)
- `https://pypi.org/project/py-clob-client/` — Version 0.34.6 current (verified 2026-03-25)
- `https://pypi.org/project/claude-agent-sdk/` — Version 0.1.50 current (verified 2026-03-25)
- `https://pypi.org/project/anthropic/` — Version 0.86.0 current (verified 2026-03-25)
- `https://pypi.org/project/APScheduler/` — Version 3.11.2 current (verified 2026-03-25)
- `https://docs.polymarket.com/developers/gamma-markets-api/overview` — Gamma API endpoints, authentication (no API key required), response structure (HIGH confidence)
- `https://github.com/Polymarket/py-clob-client` — Official Polymarket Python CLOB client (HIGH confidence)
- Existing codebase (`trader.py`, `market_discovery.py`, `data_store.py`) — Working patterns for py-clob-client, requests + Gamma API, SQLite persistence (HIGH confidence — battle-tested code)

---

*Stack research for: Autonomous multi-agent prediction market trading system (Polymarket)*
*Researched: 2026-03-25*
