# Strategy

This document is updated by the trading agent after each cycle.
It starts blank and evolves based on trading experience.

## Market Selection Rules

*Last updated: cycle 20260327-181358*

1. Prioritize markets with YES prices between 0.20 and 0.80 for analysis. Markets priced near 0 or 1 have limited absolute edge potential and should be deprioritized in favor of markets in the "sweet spot" price range where mispricing is more likely and more impactful. **Validated:** cycle 3 found both tradable edges (30.2% and 11.5%) within the sweet spot from a scan of 15 markets.

2. Check for resolved markets at the start of each cycle before assessing capacity for new trades. Resolved positions should be formally closed to free up capital and accurately reflect portfolio state.

3. Scan at least 40 markets per cycle (increased from 15, then 20). Wider scan windows with aggressive pre-filtering increase the chance of finding the rarer markets where Polymarket pricing diverges significantly from informed estimates. Cycle 4 analyzed 6 markets from 19 scanned and found zero qualifying edges, suggesting the funnel needs to be wider at the top.

4. **Esports markets require elevated edge thresholds (0.15+) and must not rely primarily on historical H2H records as edge justification.** The CS:GO Aurora vs TheMongolz trade (cycle 3) produced a total loss (-$7.85, Brier 0.384) despite a 7-2 H2H advantage for TheMongolz. H2H records do not account for recent form, roster changes, map pool dynamics, or tournament context. Esports may still be analyzed but with higher scrutiny. *(Revised from "Esports and niche markets deserve analysis time" based on outcome data from cycle 20260327-181358.)*

5. **Exclude single-game sports matchup and spread markets at the pre-filtering step.** These markets have never cleared the 0.10 edge threshold across four consecutive cycles, consistently showing edges below 2%. They are efficiently priced by sportsbooks and waste analyst compute. This does NOT apply to esports or niche sports (see rule 4).

6. **Exclude markets with end dates more than 90 days from now during pre-filtering** unless they show extreme volume anomalies or obvious mispricing (e.g., YES price between 0.30-0.70 on events that are very likely or very unlikely). Long-dated markets have unreliable edge estimates and tie up analytical resources. Prior ">1 year" guidance was too permissive; 90-day cutoff is more appropriate based on cycle 4 data (Newsom 2028 market wasted analyst time).

## Analysis Approach

*Last updated: cycle 20260327-181358*

1. **Commodities/macro crisis markets show the largest edges.** Crude Oil $100 had a 30.2% edge driven by the Strait of Hormuz supply shock. Markets tied to ongoing crises where supply/demand dynamics are shifting rapidly may lag in repricing. Prioritize these when geopolitical events create macro dislocation.

2. **Geopolitical markets (active conflicts):** Show edges of 3.5-9.5% — below threshold individually but valuable context for related markets (e.g., Iran conflict → oil prices). Useful for cross-market thesis building.

3. **Esports H2H analysis is unreliable as a primary edge signal.** The Aurora vs TheMongolz trade relied on a 7-2 H2H record to estimate an 11.5% edge, but Aurora won 2-0 decisively, resulting in a total loss (Brier 0.384). Historical H2H records in esports do not capture roster changes, recent form, map pool dynamics, or tournament context. When analyzing esports, require multiple independent signals beyond H2H (e.g., recent tournament results, analyst consensus, map veto patterns) and apply a confidence discount. *(Revised from "Esports H2H analysis provides quantifiable edge" based on realized outcome from cycle 20260327-181358.)*

4. **Sports markets near event time:** Deprioritize. Edges consistently 0.1-0.5%. Professional bettors make these efficient.

5. **Long-dated political markets (>1 year):** Deprioritize. Edge estimation unreliable at 2+ year horizons.

## Risk Parameters

*Last updated: cycle 20260327-103123*

1. Keep MIN_EDGE_THRESHOLD at 0.10. Cycle 3 found 2 markets exceeding 10% (30.2% and 11.5%) by expanding scan width to 15 markets and analyzing the sweet-spot price range. The issue was not the threshold but the scan scope.

2. Tiered threshold for geopolitical markets (0.07 for confidence > 0.5, volume > $500K) remains under review but is deprioritized since wider scanning solved the zero-trade problem.

## Trade Entry/Exit Rules

*Last updated: cycle 20260327-181358*

1. **Resolution monitoring:** At the start of each cycle, check existing positions for markets priced above 0.95 (YES side) or below 0.05 (YES side, meaning NO is above 0.95). Flag these as effectively resolved and prioritize closure to free up capital. The Israel-Lebanon position ($62.54 unrealized gain) has been tied up for 3+ cycles.

2. **Short-expiry markets need tight monitoring.** Both new positions (Crude Oil Mar 31, Aurora BO3 today) resolve within days. Check results promptly and close positions when markets resolve to free capital for the next cycle.

3. **Dead-position cleanup:** Positions where the market price drops below 0.01 and sell attempts fail due to zero liquidity should be automatically marked as realized losses rather than carried as open positions. This prevents stale positions from distorting portfolio exposure metrics and unrealized P&L. *(Added based on the CS:GO position at market price 0.0005 with no liquidity, cycle 20260327-181358.)*
