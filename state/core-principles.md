# Core Principles

These principles are set by the human operator and are never modified by the trading agent.
The agent reads this file at cycle start but never writes to it.

---

## Reality Check

85-90% of retail accounts on Polymarket end with net losses. The top 0.04% of wallets capture 70%+ of all profits. This agent exists to be in the other 10-15%. Every principle below serves that single goal.

---

## Session Mode: Overnight Crypto Sprint

**Duration:** 1 night (~8-10 hours)
**Cycle interval:** 1 hour
**Goal:** maximize number of quality trades on short-duration markets with fast capital turnover.

---

## Operator-Locked Parameters

| Parameter | Value |
|---|---|
| Execution mode | **PAPER_ONLY = true** |
| Min edge (crypto) | **0.08** (8 pp, after fees) |
| Min edge (other) | **0.08** (8 pp, after fees) |
| Kelly fraction | **0.25** (quarter-Kelly) |
| Max per trade | **$25** |
| Max total exposure | **$200** |
| Min order size | **$5** |
| Price sweet spot (YES) | **0.15 - 0.85** |
| Resolution window | priority **≤48h**; hard limit **≤72h** |
| Max per asset cluster | **2 positions** (e.g., max 2 BTC-related) |
| Max per theme cluster | **2 positions** |
| Cycle interval | **1 hour** |
| Scan limit | **≥60 markets per cycle** |

If a parameter is absent — the agent must NOT guess. Skip the trade.

---

## Market Selection

**1. You are trading mispricing, not predicting outcomes.**
The question is never "will this happen?" It is always "is this market mispriced?" If you cannot articulate what you know that the market doesn't — do not trade.

**2. Edge must be net, not gross.**
`edge_net = (p_est - price) - fee_est - slippage_buffer`. Only `edge_net` counts. If fees consume more than half the edge, skip.

**3. Price sweet spot: 0.15 to 0.85.**
Outside this range, payoff asymmetry destroys you. At $0.90+, you risk $0.90 to gain $0.10. Below $0.15, the market is usually right.

**4. Resolution window: ≤48h preferred, ≤72h hard limit.**
This is an overnight sprint. We want markets that resolve fast so capital recycles across cycles. If `end_date` is missing — skip. If resolution is >72h — skip, no exceptions.

**5. Liquidity is non-negotiable.**
Check order book depth. If bid-ask spread exceeds 4%, the edge is illusory. Crypto markets can be thin overnight — verify depth before entry.

**6. Category focus for this session.**
- **Primary:** crypto price targets (BTC, ETH, SOL, etc. hitting price levels by date), protocol events, token launches, DeFi milestones.
- **Secondary:** any other market resolving within 48h regardless of category — breaking news, scheduled events, overnight results.
- **Banned:** anything resolving >72h. No long-dated politics, no multi-week geopolitics.
- **Banned:** single-game sports matchups (consistently <2% edge, efficiently priced).

**7. Late-information trade ban.**
If the event has already occurred but the price hasn't updated — do NOT open a new position. Mark as `late_info=true` in report and skip. Only closing existing positions is allowed.

**8. Scan wide, filter hard.**
Scan ≥60 markets per cycle (increased for overnight volume). Focus scan on crypto category + short end-date. If 2 consecutive cycles produce 0 new trades, auto-increase scan limit (up to 200).

---

## Risk and Sizing

**9. Expected value is everything, win rate is nothing.**
Calculate EV explicitly: `EV = p_est * (1 - price) - (1 - p_est) * price`. Never optimize for win rate.

**10. Position sizing: quarter-Kelly with hard dollar caps.**
`size = min(0.25 * kelly_size(edge, odds), $25_per_trade, remaining_exposure)`. $25 max per trade — smaller positions allow more bets and faster capital recycling. Never override upward.

**11. Crypto correlation control.**
Crypto assets are highly correlated. BTC crash = ETH crash = SOL crash. Treat related assets as one cluster:
- **Per-asset cluster:** max 2 positions (e.g., max 2 BTC price markets).
- **Cross-crypto directional:** if you're long "BTC above $X" AND long "ETH above $Y", that's correlated. Second correlated position: size × 0.5.
- **Total crypto directional exposure** (all same-direction bets): max $100 of $200 cap.

**12. Never average down.**
Price movement against you carries genuine information. Re-examine, don't double down.

**13. Capital recycling is the priority.**
With 1h cycles, positions that resolve between cycles free up capital for new trades. Prefer markets with the shortest resolution window that still has edge. A $25 trade that resolves in 6h and recycles is worth more than a $25 trade locked for 3 days.

---

## Execution Realism (Paper Mode)

**14. Paper fills must use the order book.**
BUY at `best_ask`. SELL at `best_bid`. Quantize to `tick_size`. If the book is stale (>10s old) — skip. No fills at mid-price.

**15. Fees must reflect actual CLOB schedules.**
Apply category-specific fee formulas. Fee params changed 2026-03-30 — use current schedule.

**16. Closures before new entries.**
Fixed cycle order: monitor positions → execute sells → analyze outcomes → THEN scan for new trades. If closure step fails — do not open new positions.

---

## Behavioral Discipline

**17. Overnight markets have thin liquidity — respect it.**
Volume drops overnight. Spreads widen. Slippage increases. Apply a higher slippage buffer during low-volume hours. If the book looks thin, prefer smaller size or skip.

**18. Overreactions are exploitable.**
Crypto moves fast overnight. After a sharp dump/pump, price-target markets overshoot. Trade the correction — but only if you have a baseline probability estimate.

**19. Insider activity is real.**
Sharp price moves with no public catalyst = do NOT follow. You are providing exit liquidity.

**20. Hold unless thesis breaks.**
Do not sell because the price dipped. Sell only when thesis is fundamentally invalidated. But with ≤72h resolution — most positions should be held to resolution, not traded out.

**21. Dead positions: write off honestly.**
If `best_bid` is absent or depth is negligible — mark as `writeoff_candidate=true` and record as realized loss.

---

## Observability and Audit

**22. Every cycle produces a full audit trail.**
JSON per step + markdown report. Include skip reasons for every market rejected. 1h cycles mean 8-10 reports per night — keep them concise but complete.

**23. Brier scores are the truth metric.**
Log Brier per closed position. Short resolution windows mean we get calibration data fast — this is the advantage of overnight sprints.

**24. Core Principles are immutable by the agent.**
Any attempt to write to `state/core-principles.md` must hard-fail. The agent writes only to `state/strategy.md`.
