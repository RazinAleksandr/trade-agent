# Toolkit Guide: GSD + Tâches CC Resources

Two complementary frameworks are installed. This guide explains what each does, when to use which, and how they work together.

---

## Get Shit Done (GSD) v1.28.0

**What it is:** A spec-driven development system that orchestrates multi-agent workflows with fresh context windows. Solves "context rot" by extracting structured context into `.planning/` markdown files and spawning specialized subagents.

**Core loop:** Questions → Research → Requirements → Roadmap → Plan → Execute → Verify → Ship

### When to use GSD

- **Starting a new project from scratch** → `/gsd:new-project`
- **Building features phase-by-phase** → `/gsd:plan-phase N` → `/gsd:execute-phase N` → `/gsd:verify-work N`
- **You want structured, spec-driven development** with atomic commits per task
- **Complex multi-phase work** where context would otherwise rot across a long session
- **Parallel execution** — GSD runs multiple executor agents in wave-based parallel
- **Brownfield projects** — `/gsd:map-codebase` analyzes existing code before planning
- **Quick one-off tasks** that still benefit from tracking → `/gsd:quick`

### Key GSD commands

| Command | When |
|---------|------|
| `/gsd:new-project` | Start from zero — walks through vision, research, requirements, roadmap |
| `/gsd:discuss-phase N` | Capture preferences BEFORE planning (layout choices, API design, etc.) |
| `/gsd:plan-phase N` | Research + create executable plans + verify them |
| `/gsd:execute-phase N` | Run plans with fresh-context executor agents, atomic commits |
| `/gsd:verify-work N` | Manual acceptance testing walkthrough |
| `/gsd:ship N` | Create PR from verified work |
| `/gsd:quick` | Ad-hoc task, skips full planning ceremony |
| `/gsd:next` | Auto-detect next logical step |
| `/gsd:progress` | Show current state and what's next |
| `/gsd:debug` | Systematic debugging with persistent state |
| `/gsd:pause-work` | Create handoff (HANDOFF.json) when stopping |
| `/gsd:resume-work` | Restore from last session |
| `/gsd:map-codebase` | Analyze existing codebase (4 parallel agents: tech, arch, quality, concerns) |
| `/gsd:settings` | Configure model profile and workflow toggles |

### GSD state lives in `.planning/`

```
.planning/
├── PROJECT.md          — Vision, constraints
├── REQUIREMENTS.md     — Scoped v1/v2/out-of-scope
├── ROADMAP.md          — Phase breakdown
├── STATE.md            — Living memory (position, decisions, metrics)
├── config.json         — Workflow config
├── research/           — Domain research outputs
├── phases/XX-name/     — Per-phase plans, summaries, verification
├── quick/              — Quick task tracking
└── debug/              — Debug session history
```

### GSD model profiles

| Profile | Planning | Execution | Verification |
|---------|----------|-----------|--------------|
| `quality` | Opus | Opus | Sonnet |
| `balanced` (default) | Opus | Sonnet | Sonnet |
| `budget` | Sonnet | Sonnet | Haiku |

Change with `/gsd:set-profile`.

---

## Tâches CC Resources

**What it is:** A collection of slash commands, skills, and agents for Claude Code — focused on meta-prompting, thinking frameworks, skill/command creation, and context management.

### When to use Tâches

- **Creating reusable prompts** → `/create-prompt` + `/run-prompt`
- **Applying thinking frameworks** to a decision → `/consider:first-principles`, `/consider:pareto`, etc.
- **Building new Claude Code extensions** (skills, commands, subagents, hooks, MCP servers)
- **Capturing ideas mid-conversation** → `/add-to-todos`
- **Resuming work across sessions** → `/whats-next` creates handoff, reference it in new chat
- **Deep debugging** → `/debug` (invokes expert methodology with domain detection)
- **Research tasks** → `/research:deep-dive`, `/research:competitive`, `/research:feasibility`, etc.
- **Auditing extensions** → `/audit-skill`, `/audit-slash-command`, `/audit-subagent`

### Key Tâches commands

**Meta-prompting:**
| Command | When |
|---------|------|
| `/create-prompt` | Generate optimized XML prompt for Claude-to-Claude execution |
| `/run-prompt` | Execute saved prompt in fresh subagent context |

**Thinking frameworks (`/consider:*`):**
| Command | Best for |
|---------|----------|
| `/consider:first-principles` | Breaking a problem to fundamentals |
| `/consider:inversion` | "What guarantees failure?" — solve backwards |
| `/consider:pareto` | Finding the 20% effort that delivers 80% value |
| `/consider:5-whys` | Root cause analysis |
| `/consider:second-order` | Thinking through consequences of consequences |
| `/consider:occams-razor` | Finding the simplest explanation |
| `/consider:one-thing` | Identifying highest-leverage action |
| `/consider:swot` | Strengths/weaknesses/opportunities/threats mapping |
| `/consider:eisenhower-matrix` | Urgent vs important prioritization |
| `/consider:10-10-10` | Evaluating across time horizons |
| `/consider:opportunity-cost` | Analyzing what you give up |
| `/consider:via-negativa` | Improving by removing |

**Context management:**
| Command | When |
|---------|------|
| `/add-to-todos` | Capture idea with context (problem/files/solution) without losing focus |
| `/check-todos` | List pending todos, pick one, load its context |
| `/whats-next` | Create comprehensive handoff doc for session continuity |

**Research:**
| Command | When |
|---------|------|
| `/research:deep-dive` | Deep technical investigation |
| `/research:landscape` | Market/ecosystem analysis |
| `/research:competitive` | Competitor/alternative analysis |
| `/research:options` | Evaluate multiple approaches |
| `/research:technical` | Technical feasibility study |
| `/research:feasibility` | Overall feasibility assessment |
| `/research:open-source` | Open source options research |

**Extension creation:**
| Command | When |
|---------|------|
| `/create-agent-skill` | Build a new reusable skill (SKILL.md + references + templates) |
| `/create-slash-command` | Build a new `/command` shortcut |
| `/create-subagent` | Create a specialized agent definition |
| `/create-hook` | Create event-driven automation |
| `/create-meta-prompt` | Build multi-stage prompt pipelines |

---

## GSD vs Tâches: Decision Guide

| Situation | Use |
|-----------|-----|
| Building a project from scratch | GSD (`/gsd:new-project`) |
| Multi-phase feature development | GSD (plan → execute → verify loop) |
| Need parallel agent execution | GSD (wave-based executors) |
| Quick one-off coding task | GSD (`/gsd:quick`) or just do it directly |
| Creating a reusable prompt | Tâches (`/create-prompt`) |
| Applying a decision framework | Tâches (`/consider:*`) |
| Building Claude Code extensions | Tâches (create-* skills) |
| Capturing an idea for later | Tâches (`/add-to-todos`) |
| Session handoff | Either — GSD has `/gsd:pause-work`, Tâches has `/whats-next` |
| Debugging | Either — GSD has `/gsd:debug`, Tâches has `/debug` |
| Research | Either — GSD does research as part of planning, Tâches has standalone `/research:*` commands |

### Using them together

1. **Plan with GSD, decide with Tâches**: Use `/consider:pareto` or `/consider:first-principles` to clarify requirements, then feed that clarity into `/gsd:new-project`.

2. **GSD for building, Tâches for meta-work**: GSD handles the build pipeline. Tâches handles creating new commands/skills/agents to improve your workflow.

3. **Tâches todos alongside GSD phases**: Use `/add-to-todos` during GSD execution to capture ideas without derailing a phase.

4. **Research with Tâches, plan with GSD**: Use `/research:deep-dive` or `/research:options` for initial exploration, then use GSD's structured planning for implementation.

---

## Hooks (active)

These run automatically via `.claude/settings.json`:

| Hook | Event | Purpose |
|------|-------|---------|
| `gsd-statusline.js` | Status line | Shows model, task, directory, context usage |
| `gsd-context-monitor.js` | PostToolUse | Warns at 35% / 25% context remaining |
| `gsd-check-update.js` | SessionStart | Checks for GSD updates |
| `gsd-prompt-guard.js` | PreToolUse | Scans `.planning/` writes for injection patterns |

---

## Source locations

- GSD source: `./get-shit-done/`
- Tâches source: `./taches-cc-resources/`
- Installed commands: `.claude/commands/`
- Installed agents: `.claude/agents/`
- Installed hooks: `.claude/hooks/`
- Installed skills: `~/.claude/skills/` (global)
- GSD framework runtime: `.claude/get-shit-done/`
