# Simulator & Platform Mechanics

## Confirmed Semantics
- Position limits: 80 units per product (all-or-nothing enforcement)
- Order size: keep under 20 per order
- Backtester uses jmerle/prosperity4bt matching (the community standard)
- Backtester overestimates by ~5-6x consistently
- Use the backtester for RANKING — higher backtest PnL = better platform PnL
- Do NOT trust absolute numbers — use for comparing strategies only

## Calibration
- market_maker: backtest ~5400 → platform 970 (5.6x)
- sniper_pennying: platform 2200 (our best result)
- The ratio is consistent for similar strategy types

## What works
- Pennying (best_bid+1, best_ask-1)
- EMERALDS: fixed fair value 10000
- TOMATOES: EMA fair value, inventory skew
- Aggressive unwind when position > 50-60
- SIMPLE strategies are more consistent than complex ones
