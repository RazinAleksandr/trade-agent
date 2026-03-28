# Strategy

This document is updated by the trading agent after each cycle.
It starts blank and evolves based on trading experience.

## Market Selection Rules
Last updated: cycle 20260328-072519

1. Scanner should target at least 60 markets per scan (use --limit 60 or higher) to avoid pipeline starvation. In cycle 20260328-072519, only 11 markets were found vs 60 target, resulting in zero trades.
2. If the first scan pass returns fewer than 30 candidates, run a second targeted scan for crypto price-target markets to align with the primary category focus.

## Analysis Approach

No rules yet. Observations from cycle 20260328-072519: the web-search-backed analyst pipeline produced well-sourced reasoning on both markets analyzed. Analyst correctly self-flagged negative edge on the Iran market.

## Risk Parameters
Last updated: cycle 20260328-072519

1. Consider a tiered edge threshold: maintain the standard 8% net minimum for markets with confidence below 0.70, but allow 6% net for markets with confidence >= 0.75 and high liquidity (spread < 2%). This avoids rejecting near-miss opportunities when the candidate pool is thin. (Note: this is a text suggestion for operator review, not an automated parameter change.)

## Trade Entry/Exit Rules

No rules yet. Zero trades executed in inaugural cycle -- entry/exit rules will evolve once positions are opened.
