# Product Briefs — Tutorial Round

## EMERALDS
- **Fair value:** Fixed at 10,000 (stationary)
- **Spread:** ~16 ticks (bids ~9992, asks ~10008)
- **Position limit:** 80

## TOMATOES
- **Fair value:** Drifts randomly
- **Spread:** ~14 ticks
- **Position limit:** 80

## Round 1 results
- agent_r1_adaptive_pennying_with_unwind (gemini): PnL=0 [BAD] — A dual-product strategy utilizing fair-value anchoring, pennying for queue prior
- agent_r1_dual_product_adaptive_mm (openai): PnL=-6413 [BAD] — Architecture: A unified inventory‐aware market maker that handles EMERALDS and T

## Round 2 results
- agent_r2_dynamic_inventory_pennying_mm (gemini): PnL=0 [BAD] — Dual-product market maker using fixed fair value for EMERALDS and EMA of mid-pri
- agent_r2_volatility_skewed_dual_mm (openai): PnL=173 [weak] — This strategy is a dual-product market maker that adapts to both static and drif

## Round 3 results
- agent_r3_agent_r3_pennying_inventory_unwind (gemini): PnL=12969 [GOOD] — Dual-product market maker using strict pennying (best_bid + 1, best_ask - 1) for
- agent_r3_adaptive_multisignal_dual_mm (openai): PnL=3114 [GOOD] — Dual‐product inventory‐aware market maker that fuses multiple signals: anchor EM

## Round 4 results
- agent_r4_agent_r4_sniper_pennying_dual_mm (gemini): PnL=14646 [GOOD] — Advanced dual-product strategy combining liquidity taking (sniping mispriced ord
- agent_r4_adaptive_vol_corr_skew_mm (openai): PnL=2203 [GOOD] — Dual‐product inventory‐aware market maker that blends dynamic spread management,

## Round 5 results
- agent_r5_agent_r5_microprice_imbalance_sniper_mm (gemini): PnL=0 [BAD] — Advanced dual-product market maker that builds on the winning sniper-pennying ar
- agent_r5_sniper_mean_reversion_inventory_mm (openai): PnL=13048 [GOOD] — Dual‐product market maker that combines passive liquidity providing, opportunist

## Round 1 results

## Round 1 results
