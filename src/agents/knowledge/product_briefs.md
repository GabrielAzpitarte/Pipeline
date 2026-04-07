# Product Briefs — Tutorial Round

## EMERALDS
- Fair value: 10,000 (stationary). Spread ~16. Limit 80.
- Best platform PnL: ~1050 (from taker_penny). 29 fills / 2000 ticks.

## TOMATOES
- Fair value: drifts. Spread ~14. Limit 80.
- Best platform PnL: ~1468 (from taker_penny). 1935 fills / 2000 ticks.
- TOMATOES = ~60% of total PnL. Most room for improvement.

## Round 1 results
- agent_r1_dynamic_penny_obi (gemini): PnL=0 [BAD] — Aggressive taker and pennying strategy using EMA combined with Order Book Imbala
- agent_r1_liquidity_momentum_sniper (openai): PnL=15003 [GOOD] — Hybrid market-making and sniping strategy that uses static fair value for EMERAL

## Round 2 results
- agent_r2_asset_specific_hybrid_penny (gemini): PnL=10475 [GOOD] — Combines the best performing asset-specific logics: strict taker/pennying for EM
- agent_r2_adaptive_inventory_sniper (openai): PnL=0 [BAD] — Hybrid inventory-aware market maker with volatility-adaptive sniping and mean-re

## Round 3 results
- agent_r3_asset_specialized_hybrid (gemini): PnL=0 [BAD] — Bifurcates logic completely between stationary (EMERALDS) and drifting (TOMATOES
- agent_r3_asset_specific_hybrid_sniper (openai): PnL=0 [BAD] — An asset-specific hybrid that combines aggressive taker/pennying for the station

## Round 4 results
- agent_r4_bifurcated_specialist_sniper (gemini): PnL=13565 [GOOD] — Asset-specific logic combining the best EMERALDS taker/pennying with the best TO
- agent_r4_asset_specific_inventory_hybrid (openai): PnL=0 [BAD] — Hybrid strategy splitting logic by asset: EMERALDS uses inventory‐aware market m

## Round 5 results
- agent_r5_best_of_both_specialist (gemini): PnL=0 [BAD] — Bifurcated logic combining the best performing EMERALDS taker/pennying with the
- agent_r5_bifurcated_taker_sniper_hybrid (openai): PnL=-3036 [BAD] — A two‐legged asset‐specific strategy: EMERALDS are handled with a static taker‐p

## Round 1 results

## Round 1 results
