# Strategy

This document is updated by the trading agent after each cycle.
It starts blank and evolves based on trading experience.

## Market Selection Rules

*Last updated: cycle 20260327-091112*

1. Prioritize markets with YES prices between 0.20 and 0.80 for analysis. Markets priced near 0 or 1 have limited absolute edge potential and should be deprioritized in favor of markets in the "sweet spot" price range where mispricing is more likely and more impactful.

2. Check for resolved markets at the start of each cycle before assessing capacity for new trades. Resolved positions should be formally closed to free up capital and accurately reflect portfolio state.

## Analysis Approach

*No approach defined yet -- developing through experience.*

## Risk Parameters

*Last updated: cycle 20260327-091112*

1. Consider a tiered MIN_EDGE_THRESHOLD: use 0.07 (instead of default 0.10) for high-volume geopolitical markets where analyst confidence exceeds 0.5 and 24h volume exceeds $500K. This is an observation from the inaugural cycle where all 10 markets were rejected despite geopolitical markets showing edges of 3.5-6.5% with moderate-to-high confidence. *Status: under review -- needs more cycle data to validate.*

## Trade Entry/Exit Rules

*No custom rules yet -- using default edge and Kelly thresholds.*
