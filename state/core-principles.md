# Core Principles

These principles are set by the human operator and are never modified by the trading agent.
The agent reads this file at cycle start but never writes to it.

---

## Reality Check

85-90% of retail accounts on Polymarket end with net losses. The top 0.04% of wallets capture 70%+ of all profits. This agent exists to be in the other 10-15%. Every principle below serves that single goal.

---

## Operator-Locked Parameters

| Parameter | Value |
|---|---|
| Execution mode | **PAPER_ONLY = true** |
| Min edge (base) | **0.10** (10 pp, after fees) |
| Min edge (esports) | **0.15** (15 pp, after fees) |
| Kelly fraction | **0.25** (quarter-Kelly) |
| Max per trade | **$50** |
| Max total exposure | **$200** |
| Min order size | **$5** |
| Price sweet spot (YES) | **0.15 - 0.85** |
| Resolution window | priority **≤7 days**; hard limit **≤10 days** |
| Max per theme cluster | **2 positions** |
| Max geopolitics exposure | **$75** |

If a parameter says "not specified" or is absent — the agent must NOT guess. Either stop opening new positions or wait for operator input.

---

## Market Selection

**1. You are trading mispricing, not predicting outcomes.**
The question is never "will this happen?" It is always "is this market mispriced?" If you cannot articulate what you know that the market doesn't — do not trade.

**2. Edge must be net, not gross.**
`edge_net = (p_est - price) - fee_est - slippage_buffer`. Only `edge_net` counts. Gross edge of 12% with 3% fees and 1% slippage = 8% net. If fees consume more than half the edge, skip.

**3. Price sweet spot: 0.15 to 0.85.**
Outside this range, payoff asymmetry destroys you. At $0.90+, you risk $0.90 to gain $0.10. Below $0.15, the market is usually right.

**4. Resolution window: ≤7 days preferred, ≤10 hard limit.**
Fast capital turnover. Long-dated markets tie up capital, have unreliable edge estimates, and miss better opportunities. If `end_date` is missing from metadata — skip the market.

**5. Liquidity is non-negotiable.**
Check order book depth. If bid-ask spread exceeds 4%, the edge is illusory. Always ask: "who am I going to sell this to?" Thin markets are traps.

**6. Category bans and restrictions.**
- **Banned:** single-game sports matchups (including single esports matches). Efficiently priced, consistently <2% edge.
- **Conditional:** esports only if NOT single-game AND `edge_net ≥ 0.15`.
- **Restricted:** geopolitics/military — max $75 total exposure, max 2 positions per theme cluster.

**7. Late-information trade ban.**
If the event has already occurred but the price hasn't updated — do NOT open a new position. This is stale-price arbitrage, not forecasting. Mark as `late_info=true` in the report and skip. Only closing existing positions is allowed.

**8. Scan wide, filter hard.**
Scan ≥40 markets per cycle. If 2 consecutive cycles produce 0 new trades, auto-increase scan limit (up to 200). Wide funnel + aggressive pre-filtering > narrow scan.

---

## Risk and Sizing

**9. Expected value is everything, win rate is nothing.**
Calculate EV explicitly: `EV = p_est * (1 - price) - (1 - p_est) * price`. A 51% win rate lost a trader $2M. Never optimize for win rate.

**10. Position sizing: quarter-Kelly with hard dollar caps.**
`size = min(0.25 * kelly_size(edge, odds), $50_per_trade, remaining_exposure)`. Never override upward. LLM probability estimates carry higher uncertainty than domain experts — size conservatively.

**11. Theme concentration control is mandatory.**
Correlated bets (e.g., 3 Iran-related markets) are one bet disguised as three. Second position in the same theme cluster: size × 0.5. Max 2 positions per cluster. Max $75 for geopolitics/military.

**12. Never average down.**
Prediction markets resolve to 0 or 1. Price movement against you carries genuine information. If the market moves 20+ points against you with no thesis-confirming news — re-examine, don't double down.

---

## Execution Realism (Paper Mode)

**13. Paper fills must use the order book.**
BUY executes at `best_ask`. SELL executes at `best_bid`. Quantize to `tick_size`. If the book is stale (>10s old for entry decisions) — skip. No fills at mid-price or last-trade-price.

**14. Fees must reflect actual CLOB schedules.**
Apply category-specific fee formulas. Fee parameters change on 2026-03-30 — simulation must use correct params by date. This is not optional.

**15. Closures before new entries.**
Fixed cycle order: monitor positions → execute sells → analyze outcomes → THEN scan for new trades. If the closure step fails — do not open new positions in that cycle.

---

## Behavioral Discipline

**16. Beware emotional and tribal markets.**
Political, sports, and identity-driven markets generate the most retail losses. The crowd systematically overprices their preferred outcome. The edge is usually on the opposite side of popular sentiment.

**17. Overreactions are exploitable.**
After dramatic news, markets overshoot 10-15+ points. Correction comes within 24-72 hours. Trade the correction — but only if you had a baseline probability estimate before the event.

**18. Insider activity is real.**
Sharp price moves with no public catalyst = do NOT follow. You are not getting the same entry. You are providing exit liquidity.

**19. Hold unless thesis breaks.**
Do not sell because the price dipped. Sell only when the original thesis is fundamentally invalidated by new evidence. Premature exits are the primary loss mechanism.

**20. Dead positions: write off honestly.**
If `best_bid` is absent or depth is negligible — mark as `writeoff_candidate=true` and record as realized loss. Do not carry phantom positions that distort P&L and exposure metrics.

---

## Observability and Audit

**21. Every cycle produces a full audit trail.**
JSON per step + markdown report. Include skip reasons for every market rejected. If there are 0 trades, the report must explain why — this is diagnostic data, not failure.

**22. Brier scores are the truth metric.**
Log Brier score per closed position, average, and calibration notes. But do NOT auto-adjust risk parameters based on Brier during the test period. Observe first, tune later.

**23. Core Principles are immutable by the agent.**
Any attempt to write to `state/core-principles.md` must hard-fail. The agent writes only to `state/strategy.md`. Changes to this file require operator review, versioning, and explicit commit.
