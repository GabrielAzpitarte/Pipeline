# Simulator & Platform Mechanics

## Confirmed Semantics
- Position limits: 80 units per product (all-or-nothing enforcement)
- Order size: keep under 20 per order
- Backtester uses jmerle/prosperity4bt matching semantics (the community standard)
- ALL mode: market trades at or below your buy price fill you
- Backtester OVERESTIMATES by ~5x for passive strategies — this is normal and expected
- A backtest PnL of 5000 on 10K ticks means roughly 1000 on the platform
- Use the backtester for RANKING (is A better than B?), not absolute PnL prediction

## What works on the platform
- Pennying (best_bid+1, best_ask-1) — queue priority, more fills
- EMERALDS: fixed fair value 10000, simple market making
- TOMATOES: EMA fair value, inventory skew
- Aggressive unwind when position > 50-60

## Edge Cases
- Inventory > 60 requires aggressive unwind
- Very large order sizes (40+) cause runaway inventory
- Hardcoding position limits smaller than 80 wastes capacity
