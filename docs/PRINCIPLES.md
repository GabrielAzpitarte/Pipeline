# Pipeline Principles

## What this pipeline optimizes for
- **Platform-transfer quality**: strategies that perform well on the real platform, not just the local backtester
- **Architecture diversity**: exploring genuinely different strategy families, not parameter churn
- **Robustness across conditions**: consistency across days, scenarios, and market regimes
- **Per-asset excellence**: identifying the best logic for each product independently

## What this pipeline does NOT optimize for
- **Raw backtest PnL alone**: higher backtest PnL does not mean higher platform PnL
- **Fill count**: more fills in the backtester often means more unrealistic passive fills
- **Prompt prestige**: a strategy is not better because a more expensive model proposed it
- **Memory popularity**: frequently appearing in cards does not make a strategy better
- **Parameter precision**: sweep-optimal params often exploit backtester artifacts

## Core beliefs (validated by platform data)
1. The local backtester overestimates PnL by ~6x for market-making strategies
2. Aggressive parameters (smaller orders, tighter edge, lower unwind) win in backtester but lose on platform
3. 97-100% of backtest fills are passive — most of these don't happen on platform
4. The backtester reliably ranks strategy ARCHITECTURES but not parameter variants
5. Cross-day consistency is a better transfer signal than single-day peak PnL
6. Scenario gap (baseline vs conservative) correlates with platform fragility

## Decision gates
Before any of these actions, require written rationale:
- Changing execution semantics (matching, scenarios)
- Promoting a new ranking objective
- Platform submission
- Changing memory retrieval rules
- Modifying the canonical artifact schema

## Historical Trade Replay Policy
- **Default: "half"** — each trade provides half its quantity to each side
- **Rationale**: Aggressor side unknown from data. Half-split is conservative (better than full-both which doubled liquidity) but not maximally pessimistic
- **Alternative: "one_sided"** — full quantity to one side only, deterministically chosen per trade. Used in hostile stress-test scenarios
- **Passive fill rate**: Applied on top of trade split. With rate=0.2 and available=1, result is 0 fills (no minimum guarantee)
