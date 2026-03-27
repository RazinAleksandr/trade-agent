# Milestones

## v1.0 MVP (Shipped: 2026-03-27)

**Phases completed:** 4 phases, 15 plans, 29 tasks

**Key accomplishments:**

- lib/ package with Config dataclass (.env + CLI override), SQLite DataStore (5 tables, neg_risk/fill_price columns), dual logging (stderr + JSON file), SIGINT/SIGTERM handler, and 14 passing pytest tests
- Gamma API market discovery with stringified JSON parsing and neg-risk detection, plus CLOB API pricing with correct inverted side semantics for paper trade fills, wrapped in two CLI tools
- Kelly criterion with quarter-Kelly default, edge calculation, position sizing with 5 USDC minimum, and two CLI tool wrappers outputting JSON
- Paper and live trade execution with CLOB API pricing, signed GTC orders, and 5 USDC minimum order validation
- Portfolio tracking with live P&L from Gamma API, resolved market detection, and risk limit warnings at 90% thresholds
- Deleted 9 v1 legacy root .py files, created .env.example with all 15 parameters, verified 93 tests pass and 7 CLI tools work end-to-end against live Gamma API
- JSON schema validation for 5 sub-agent output formats plus state directory structure with blank strategy.md for agent-layer foundation
- Scanner and Analyst Claude sub-agent definitions with YAML frontmatter, tool restrictions, maxTurns caps, and structured JSON output schemas for the market discovery and analysis pipeline stages
- Risk Manager with Kelly sizing and correlation detection, Planner with strategy-aware trade planning, and Reviewer with dual JSON/markdown cycle reporting
- Main orchestration agent wiring all 5 sub-agents into a complete trading pipeline with strategy reading, JSON validation, direct trade execution, and error-resilient cascade handling
- Strategy Updater sub-agent, validate_strategy_update() schema, restructured state/strategy.md (4 domains, no Core Principles), and 10 new tests
- Extended trading-cycle.md pipeline with Strategy Updater as Step 7, core-principles.md read at cycle start, and non-blocking strategy update error handling
- Config scheduling fields, 401 credential refresh retry for live trades, and .live-gate-pass file check blocking unauthorized live execution
- Cron-based scheduling with PID lockfile guard, interval-to-cron conversion, and crontab management CLI
- Live trading gate tool requiring paper cycle count + positive P&L + explicit confirmation, plus 18 safety tests covering all SAFE-01 through SAFE-05 requirements

---
