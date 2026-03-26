# Phase 2: Agent Layer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 02-agent-layer
**Areas discussed:** Orchestration flow, Analyst debate design, State & report layout

---

## Orchestration Flow

### Sub-agent dispatch pattern
| Option | Description | Selected |
|--------|-------------|----------|
| Sequential pipeline | Scanner -> Analyst -> Risk Manager -> Planner -> Execute -> Reviewer. Simpler, deterministic, easier to debug. | ✓ |
| Parallel where possible | Scanner first, then Analyst + Risk Manager in parallel. Faster but more complex. | |
| You decide | Claude picks based on Task tool behavior | |

**User's choice:** Sequential pipeline
**Notes:** None

### Failure handling
| Option | Description | Selected |
|--------|-------------|----------|
| Skip and continue | Drop failed market/step, continue cycle with whatever succeeded. Log failure. | ✓ |
| Retry once then skip | Retry failed sub-agent once, then skip. Adds resilience but doubles cost. | |
| Abort cycle | Any sub-agent failure aborts entire cycle. Strictest but fragile. | |

**User's choice:** Skip and continue
**Notes:** Mirrors Phase 1 error handling pattern

### Main agent invocation
| Option | Description | Selected |
|--------|-------------|----------|
| Python script calls Claude CLI | Python entry point invokes claude CLI | |
| Shell script orchestrator | Bash script invokes claude | |
| Direct CLI invocation | User/cron runs claude --prompt directly | |

**User's choice:** Other (free text)
**Notes:** Main agent is Claude Code itself with project instructions. Sub-agents are `.claude/agents/` files spawned via Task tool. Uses Claude Code's native agent/subagent infrastructure.

### Data passing between sub-agents
| Option | Description | Selected |
|--------|-------------|----------|
| JSON files in state/ | Each agent writes output to JSON file, next reads it. Persistent and debuggable. | ✓ |
| Task tool return values | Return structured text inline. No files, data in context window only. | |
| Both — files + returns | Write JSON files AND return summary. Files are source of truth. | |

**User's choice:** JSON files in state/
**Notes:** None

---

## Analyst Debate Design

### Bull/Bear debate structure
| Option | Description | Selected |
|--------|-------------|----------|
| Single agent, structured prompt | One call forces Bull case, Bear case, then synthesis. Cheaper, simpler. | ✓ |
| Two separate agent calls | Bull agent + Bear agent in parallel + synthesis. More thorough, 3x cost. | |
| You decide | Claude picks based on cost/quality tradeoff | |

**User's choice:** Single agent, structured prompt
**Notes:** None

### Web search usage
| Option | Description | Selected |
|--------|-------------|----------|
| Yes, always | Analyst always uses web search. Better probability estimates. | ✓ |
| Optional per market | Analyst decides per market type | |
| No web search | Relies on training data only. Cheaper but stale. | |

**User's choice:** Yes, always
**Notes:** None

### Market analysis coverage
| Option | Description | Selected |
|--------|-------------|----------|
| All from Scanner | Evaluate every market Scanner returns (up to MAX_MARKETS_PER_CYCLE). | ✓ |
| Top N ranked by Scanner | Only deep-dive top 3-5. Faster, may miss opportunities. | |
| You decide | Claude picks batch size | |

**User's choice:** All from Scanner
**Notes:** None

### Market batching
| Option | Description | Selected |
|--------|-------------|----------|
| One market per agent call | Separate Task per market. Can run in parallel. Independent failures. | ✓ |
| All markets in one call | Single call analyzes all. Cheaper but slower, all-or-nothing failure. | |
| You decide | Claude picks | |

**User's choice:** One market per agent call
**Notes:** None

---

## State & Report Layout

### State directory structure
| Option | Description | Selected |
|--------|-------------|----------|
| state/ directory | state/strategy.md, state/reports/, state/cycles/. Clean separation from code. | ✓ |
| Root-level files | strategy.md and reports/ in project root. Flat. | |
| You decide | Claude picks | |

**User's choice:** state/ directory
**Notes:** None

### Cycle history depth
| Option | Description | Selected |
|--------|-------------|----------|
| Strategy + last 3 reports | Read strategy.md + 3 most recent reports. Matches ROADMAP criteria. | ✓ |
| Strategy + last report only | Minimal context, lower cost. | |
| Strategy + all reports | Maximum context, may overwhelm window. | |

**User's choice:** Strategy + last 3 reports
**Notes:** None

### Report detail level
| Option | Description | Selected |
|--------|-------------|----------|
| Full detail | Markets scanned, analyzed (Bull/Bear), trades, sizes, portfolio, P&L, learnings. | ✓ |
| Trade-focused summary | Only trades and P&L. Skip non-traded analysis. | |
| You decide | Claude picks | |

**User's choice:** Full detail
**Notes:** None

### Intermediate output retention
| Option | Description | Selected |
|--------|-------------|----------|
| Keep per cycle | All files in state/cycles/{cycle_id}/. Full audit trail. | ✓ |
| Clean up after report | Delete intermediates after report. Only report survives. | |
| You decide | Claude picks | |

**User's choice:** Keep per cycle
**Notes:** None

---

## Claude's Discretion

- Correlation detection approach for Risk Manager (AGNT-06) — user chose not to discuss this area
- Exact JSON schemas for inter-agent communication (AGNT-09)
- max_turns limits per sub-agent (AGNT-10)
- Token cost tracking implementation
- Sub-agent prompt engineering
- Cycle report markdown format

## Deferred Ideas

None — discussion stayed within phase scope
