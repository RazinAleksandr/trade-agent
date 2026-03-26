# Phase 1: Instrument Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 01-Instrument Layer
**Areas discussed:** CLI tool interface, Shared infrastructure, Paper trade pricing

---

## CLI Tool Interface

### Argument Parsing

| Option | Description | Selected |
|--------|-------------|----------|
| argparse | Standard library, no extra deps. Auto-generates --help. Agent passes flags. | ✓ |
| Positional + flags hybrid | Required args positional, optional via flags. Simpler for agent. | |
| JSON stdin | Agent pipes JSON object as input. Max flexibility but harder to debug. | |

**User's choice:** argparse
**Notes:** None

### Output Format

| Option | Description | Selected |
|--------|-------------|----------|
| JSON to stdout always | Every tool prints JSON to stdout. --pretty flag for human-readable. Errors to stderr as JSON. | ✓ |
| JSON default, --format table option | Default JSON, optional table format for human debugging. | |
| You decide | Claude picks. | |

**User's choice:** JSON to stdout always
**Notes:** None

### Error Reporting

| Option | Description | Selected |
|--------|-------------|----------|
| JSON error to stderr + exit code | Structured JSON errors to stderr, non-zero exit codes, different codes for different error types. | ✓ |
| Plain text stderr + exit code | Simple text errors to stderr, non-zero exit. | |
| You decide | Claude picks. | |

**User's choice:** JSON error to stderr + exit code
**Notes:** None

### Tool Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Single-purpose scripts | One script per action. More files but clear separation. | ✓ |
| Grouped with subcommands | Fewer scripts with subcommands. Fewer files but more complex. | |
| You decide | Claude picks. | |

**User's choice:** Single-purpose scripts
**Notes:** None

---

## Shared Infrastructure

### Code Sharing Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Shared lib/ package | tools/ has CLI scripts, lib/ has shared modules. Clean separation. | ✓ |
| Flat shared modules alongside tools | Everything in tools/. Shared modules like _config.py next to tool scripts. | |
| Self-contained tools | Each tool contains its own config and DB access. Maximum independence. | |

**User's choice:** Shared lib/ package
**Notes:** None

### V1 File Disposition

| Option | Description | Selected |
|--------|-------------|----------|
| Delete after cherry-picking | Remove old root .py files once logic migrated to tools/ + lib/. Clean slate. | ✓ |
| Keep in root as reference | Leave old files untouched. Risk: import conflicts. | |
| Move to legacy/ directory | Archive old files in legacy/. No conflicts but adds clutter. | |

**User's choice:** Delete after cherry-picking
**Notes:** None

### Config Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Keep .env + python-dotenv | Same pattern as v1. Simple, proven. Each tool imports from lib/config.py. | ✓ |
| YAML/TOML config file | Structured config file. Richer but adds dependency. | |
| You decide | Claude picks. | |

**User's choice:** Keep .env + python-dotenv
**Notes:** None

### Config Overrides

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, flags override .env | CLI flags override env vars. Agent can customize per-call. | ✓ |
| No, .env only | Tools only read from .env. Simpler but less flexible. | |
| You decide | Claude picks. | |

**User's choice:** Yes, flags override .env
**Notes:** None

---

## Paper Trade Pricing

### Fill Price Source

| Option | Description | Selected |
|--------|-------------|----------|
| Live orderbook best ask/bid | Paper buys at best ask, sells at best bid from CLOB API snapshot. Most realistic. | ✓ |
| Live midpoint + fixed spread | Fetch midpoint, add/subtract configurable spread. Simpler but less realistic. | |
| You decide | Claude picks. | |

**User's choice:** Live orderbook best ask/bid
**Notes:** None

### CLOB Unreachable Fallback

| Option | Description | Selected |
|--------|-------------|----------|
| Fail the trade, log error | Trade fails with clear error. No fake fills. Agent retries next cycle. | ✓ |
| Use Gamma API prices as fallback | Fall back to Gamma API prices. Less granular but available. | |
| You decide | Claude picks. | |

**User's choice:** Fail the trade, log error
**Notes:** None

### Paper Mode Dependencies

| Option | Description | Selected |
|--------|-------------|----------|
| CLOB API only (no private key) | Paper mode calls CLOB read endpoints. No wallet needed. Only live needs credentials. | ✓ |
| Fully offline paper mode | Works with zero API access using cached/mock data. Less realistic. | |
| You decide | Claude picks. | |

**User's choice:** CLOB API only (no private key)
**Notes:** None

---

## Claude's Discretion

- Exact argparse flag naming conventions per tool
- Internal JSON schema structure for each tool's output
- SQLite schema evolution approach
- Logging format and verbosity levels
- Kelly criterion implementation details
- SIGINT/SIGTERM handler implementation
- Neg-risk market detection logic

## Deferred Ideas

None — discussion stayed within phase scope
