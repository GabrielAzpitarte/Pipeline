# Strategy Playbook — Proven Patterns from Prosperity 1-3 Winners

> These strategies worked on DIFFERENT products than what you'll face.
> Adapt the IDEA, not the specifics. Every round has new products.

---

## Universal Winning Principles

### 1. Fair Value Anchoring
Every winning strategy starts by estimating fair value:
- **Stable assets** (Pearls, Amethysts, Resin): Price anchored at a fixed value (e.g., 10,000). Market-make around it.
- **Drifting assets** (Bananas, Starfruit, Kelp, Tomatoes): Use rolling average or EMA of mid-price as dynamic fair value.
- **Baskets/ETFs**: Compute synthetic fair value from components. Trade when basket deviates from synthetic.
- **Options**: Black-Scholes gives theoretical value. Trade when implied volatility deviates from model.

### 2. Mean Reversion (Most Consistent Winner)
Most Prosperity products mean-revert. The z-score approach works reliably:
```
z = (price - rolling_mean) / rolling_std
if z < -threshold: BUY
if z > +threshold: SELL
```
- Window: 10-20 timestamps typical
- Threshold: 1.0-2.0 standard deviations
- Works best on stable assets and spreads between correlated products

### 3. Position Management (Critical)
Winners keep inventory near zero:
- Scale order sizes inversely with current position
- Use "0-EV trades" (trades at fair value) to rebalance without losing money
- When approaching position limits, aggressively unwind
- Skew quotes: when long, lower both buy and sell prices to encourage selling

### 4. Spread Capture (Market Making)
Place buy below fair value and sell above it. Profit = spread captured per round trip:
- Tight spread (2-4 ticks) = more fills but less profit per fill
- Wide spread (6-10 ticks) = fewer fills but more profit per fill
- Queue priority: placing 1 tick better than the best bid/ask gets you filled first
- Inventory-aware: widen spread on the side where you have excess inventory

---

## Product-Type Strategies

### Stable Assets (Pearls, Amethysts, Emeralds, Resin)
**What works:** Simple market making around known fair value.
- Fair value is constant (e.g., 10,000)
- Quote both sides symmetrically
- Take any available orders that are mispriced vs fair value
- Profit comes from spread capture + taking mispriced orders
- Prosperity 1-3 winners: 10K-35K seashells from this alone

### Drifting Assets (Bananas, Starfruit, Kelp, Squid Ink, Tomatoes)
**What works:** Adaptive fair value + mean reversion.
- EMA or rolling average as fair value (alpha 0.05-0.2)
- Market-make around the EMA, not raw mid-price
- Wider spread than stable assets (more risk from drift)
- Detect large moves (>3 std dev) and bet on reversion
- Prosperity 3: Identified "informed traders" whose trades predicted direction

### Baskets/ETFs (Gift Baskets, Picnic Baskets)
**What works:** Statistical arbitrage between basket and components.
- Synthetic price = sum of (component_price × weight)
- Spread = basket_price - synthetic_price
- Spread mean-reverts around a premium (often ~370-380)
- Buy basket when spread is low, sell when high (or vice versa)
- Can also trade components individually to hedge

### Options (Coconut Coupons, Volcanic Rock Vouchers)
**What works:** Volatility trading with Black-Scholes.
- Compute implied volatility from market prices
- IV mean-reverts: buy when IV is low, sell when high
- Volatility smile: IV varies with strike/moneyness — fit a parabola, trade deviations
- Delta hedge with underlying to isolate volatility exposure
- Position limits often constrain delta hedging — accept some directional risk

### Cross-Exchange Arbitrage (Orchids, Macarons)
**What works:** Buy cheap on one exchange, sell expensive on another.
- Account for transport fees, tariffs, conversion costs
- Adaptive edge: adjust required profit margin based on fill rate
- Regime-aware: sometimes arbitrage disappears, switch to other strategies

---

## Prosperity Winner Techniques (Years 1-3)

### Prosperity 1 (2023) — Stanford Cardinal, 2nd Place
- Pearls: Fixed fair value MM around 10,000
- Bananas: Linear regression on last N timestamps for price prediction
- Picnic Baskets: Hardcoded premium of 375, arbitraged deviations
- Diving Gear: Used dolphin sighting changes >5 as directional signal

### Prosperity 2 (2024) — Linear Utility, 2nd Place (3.5M seashells)
- Amethysts: Tight MM around 10,000 + position clearing via 0-EV trades (+16K)
- Starfruit: Rolling average fair value, market maker's mid less noisy than market mid (+34K)
- Orchids: Cross-exchange arbitrage with adaptive edge (+573K)
- Gift Baskets: Z-score mean reversion on spread with hardcoded mean + rolling std (+111K)
- Coconut Coupons: Black-Scholes IV mean reversion, managed delta (+145K)
- Roses: Found R²=0.99 correlation with prior year's diving gear returns

### Prosperity 3 (2025) — Alpha Animals, 9th Global (1.19M seashells)
- Resin: Fixed 10,000 fair value, passive + aggressive MM
- Kelp: Filtered noise by identifying consistent large market makers
- Squid Ink: Volatility mean-reversion (3 std dev threshold) + copied "Olivia" trader (+8K/round)
- Picnic Baskets: Synthetic fair price, mean-reverting spread trading
- Volcanic Rock: IV smile parabola fit, scalped deviations
- Round 5: Identified insider traders by win-rate analysis, mirrored their trades

---

## What Consistently Loses Money

1. **Crossing the spread blindly** — buying at the ask and selling at the bid loses the spread every time
2. **Trend following on mean-reverting assets** — fighting the mean is expensive
3. **Ignoring position limits** — getting stuck at max position with adverse price movement
4. **Over-fitting to historical data** — strategies that look great in backtest but fail live
5. **Complex models without structural understanding** — curve fitting without knowing WHY
6. **Strategy persistence across regime changes** — what worked in round 1 may not work in round 3
7. **Over-leverage without hedges** — large positions amplify losses on adverse moves

---

## Key Quantitative Insights

- **Optimal MM spread:** 2-4 ticks for stable assets, 4-8 for volatile ones
- **EMA alpha:** 0.05-0.1 for slow-moving, 0.1-0.3 for fast-moving assets
- **Position clearing:** Aggressively unwind when |position| > 50% of limit
- **Z-score thresholds:** 1.0-1.5 for frequent trading, 2.0+ for high-conviction trades
- **Order size:** Scale with inverse of current position (large when flat, small when exposed)
- **Fill rate optimization:** Place orders 1 tick better than best bid/ask for queue priority
