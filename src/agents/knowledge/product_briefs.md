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

## Round 1 results

## Round 1 results

## Round 1 results

## Round 1 results
- agent_r1_bifurcated_taker_microprice_sniper (gemini): PnL=7239 [GOOD] — Asset-specific strategy that maximizes fills by splitting logic: unconditional t
- agent_r1_bifurcated_taker_sniper (openai): PnL=15186 [GOOD] — Combine the proven static taker-penny logic on the stationary EMERALDS with the

## Round 2 results
- agent_r2_asset_optimized_microprice_sniper (gemini): PnL=547 [ok] — Hybrid strategy that maximizes per-asset fills by using a fixed, tight edge for
- agent_r2_dual_asset_fair_value_sniper (openai): PnL=0 [BAD] — A unified fair‐value sniper that applies asset‐specific fair estimates and dynam

## Round 3 results
- agent_r3_bifurcated_unconditional_penny_sniper (gemini): PnL=3398 [GOOD] — Asset-specific strategy using unconditional pennying/taking for stationary EMERA
- agent_r3_bifurcated_em_tomato_hybrid (openai): PnL=0 [BAD] — Split the logic completely by asset: EMERALDS use a static fair‐value taker+penn

## Round 4 results
- agent_r4_bifurcated_optimal_proven_hybrid (gemini): PnL=0 [BAD] — Asset-specific hybrid combining the highest-fill mechanics for each product: tak
- agent_r4_asset_hybrid_fv_sniper (openai): PnL=0 [BAD] — Asset‐tailored fair‐value sniper: EMERALDS use a fixed fair anchor to drive tigh

## Round 5 results
- agent_r5_asset_specific_microprice_taker (gemini): PnL=0 [BAD] — Combines the best per-asset proven logic by bifurcating: static taker/pennying f
- agent_r5_bifurcated_tomato_emerald_hybrid (openai): PnL=-10394 [BAD] — One unified strategy that splits logic per symbol: EMERALDS trade with static ta

## Round 6 results
- agent_r6_bifurcated_proven_taker_sniper (gemini): PnL=0 [BAD] — Bifurcated architecture combining the best performing asset-specific mechanics:
- agent_r6_bifurcated_hybrid_sniper (openai): PnL=0 [BAD] — Asset‐specific hybrid combining the proven static taker/penny logic on EMERALDS

## Round 7 results
- agent_r7_simplified_microprice_penny_sniper (gemini): PnL=-2905104 [BAD] — Unified dual-asset strategy using microprice fair value, fixed edges, strict pen
- agent_r7_microprice_penny_inventory (openai): PnL=13897 [GOOD] — Hybrid fair value and inventory-aware microprice market maker that uses constant

## Round 8 results
- agent_r8_bifurcated_specialist_microprice_penny (gemini): PnL=-1886 [BAD] — Bifurcated architecture combining the proven taker_penny logic for stationary EM
- agent_r8_asset_specific_proven_hybrid (openai): PnL=8505 [GOOD] — Unified trader that splits logic per symbol: EMERALDS use a static taker-plus-pe

## Round 9 results
- agent_r9_asset_specific_proven_specialist (gemini): PnL=13826 [GOOD] — Bifurcates logic to apply the best proven fill-maximizing mechanics for each spe
- agent_r9_emeralds_tomatoes_specialist (openai): PnL=10080 [GOOD] — Split asset logic: for EMERALDS use a static fair‐value taker+penny strategy tha

## Round 10 results
- agent_r10_corrected_microprice_skew_sniper (gemini): PnL=6700 [GOOD] — Architectural correction of the best platform-proven microprice sniper. It prope
- agent_r10_asset_split_micro_taker (openai): PnL=-957 [BAD] — Two-legged asset-specific architecture: EMERALDS run a static fair-value taker+p

## Round 1 results

## Round 1 results
- agent_r1_bifurcated_specialist_taker_sniper (gemini): PnL=0 [BAD] — Asset-specific hybrid strategy applying unconditional taking and pennying for st
- agent_r1_bifurcated_static_taker_micro_sniper (openai): PnL=12129 [GOOD] — A dual‐legged approach: EMERALDS are handled as a static fair‐value taker+penny

## Round 2 results
- agent_r2_bifurcated_proven_taker_microprice (gemini): PnL=-679443 [BAD] — Asset-specific hybrid strategy maximizing per-asset fills by bifurcating the log
- agent_r2_bifurcated_taker_micro_sniper (openai): PnL=0 [BAD] — Asset-specific two-leg strategy: EMERALDS use a static fair-value taker+penny en

## Round 3 results
- agent_r3_bifurcated_em_taker_tom_micro_sniper (gemini): PnL=15239 [GOOD] — Asset-specific hybrid strategy maximizing per-asset fills by separating the prov
- agent_r3_bifurcated_taker_micro_sniper (openai): PnL=-859398 [BAD] — Use two specialized legs: EMERALDS trade as a pure taker-penny strategy around a

## Round 4 results
- agent_r4_bifurcated_taker_microprice_hybrid (gemini): PnL=10447 [GOOD] — Bifurcated architecture applying the best proven taker/pennying logic to EMERALD
- agent_r4_bifurcated_emerald_tomato_hybrid (openai): PnL=0 [BAD] — Split the logic entirely by asset. EMERALDS are handled with a static taker‐penn

## Round 5 results
- agent_r5_unified_simple_taker_penny (gemini): PnL=15071 [GOOD] — Unified and simple taker-penny strategy with asset-specific fair values.
- agent_r5_asset_specific_microprice_penny_sniper (openai): PnL=-60397 [BAD] — Hybrid per‐asset strategy: EMERALDS use a static fair anchor (10,000) with uncon

## Round 6 results
- agent_r6_bifurcated_safe_taker_microprice (gemini): PnL=0 [BAD] — Asset-specific strategy that strictly manages position limits while maximizing f
- agent_r6_bifurcated_proven_hybrid_plus (openai): PnL=7095 [GOOD] — Hybrid strategy combining proven static taker-penny logic for EMERALDS with a mi

## Round 7 results
- agent_r7_asset_specific_taker_microprice_hybrid (gemini): PnL=5960 [GOOD] — A unified strategy that branches logic by symbol inside compute_orders, combinin
- agent_r7_emeralds_taker_tomatoes_microprice (openai): PnL=0 [BAD] — Bifurcated per‐asset strategy: EMERALDS use static fair value with taker and pen

## Round 8 results
- agent_r8_r8_bifurcated_specialist_taker_microprice (gemini): PnL=-61834 [BAD] — Bifurcated logic for stable vs drifting assets, combining the highest-fill mecha
- agent_r8_bifurcated_em_tomato_sniper (openai): PnL=14605 [GOOD] — This strategy splits execution by asset. EMERALDS uses a static fair‐value taker

## Round 9 results
- agent_r9_unified_microprice_penny_sniper (gemini): PnL=0 [BAD] — A single-loop, unified strategy that applies asset-specific fair value calculati
- agent_r9_bifurcated_em_tom_hybrid (openai): PnL=-3224 [BAD] — Split per‐symbol logic: EMERALDS use a static‐fair taker+penny engine around 100

## Round 10 results
- agent_r10_unified_optimal_taker_microprice_penny (gemini): PnL=13798 [GOOD] — Unified hybrid strategy blending the best platform-proven taker/penny mechanics
- agent_r10_bifurcated_emerald_tomato_hybrid (openai): PnL=0 [BAD] — Split the strategy per asset. For EMERALDS, use a static fair‐value taker‐and‐pe

## Round 1 results

## Round 1 results

## Round 1 results
- agent_r1_bifurcated_micro_penny_unwind (gemini): PnL=15647 [GOOD] — Bifurcated strategy tailored to product traits: fixed fair value for stationary
- agent_r1_unified_inventory_micro_sniper (openai): PnL=-4899 [BAD] — A unified inventory‐aware market maker that anchors quotes around per‐asset fair

## Round 2 results
- agent_r2_bifurcated_microprice_fixed_sniper (gemini): PnL=6325 [GOOD] — Bifurcated architecture using fixed fair value for stationary EMERALDS and EMA o
- agent_r2_bifurcated_micro_inventory_penny (openai): PnL=8960 [GOOD] — Unified market maker that uses fixed fair and pennying for stationary assets, EM

## Round 3 results
- agent_r3_bifurcated_fixed_em_adaptive_tom_sniper (gemini): PnL=0 [BAD] — Bifurcated architecture tailoring fair value and quoting mechanics to asset stat
- agent_r3_bifurcated_microprice_mm (openai): PnL=2401 [GOOD] — One unified market‐making framework that bifurcates asset logic: EMERALDS uses a

## Round 4 results
- agent_r4_bifurcated_fixed_emerald_micro_tomato (gemini): PnL=7756 [GOOD] — Bifurcated strategy applying asset-specific fair value models and quoting mechan
- agent_r4_dual_asset_micro_skew_unwind (openai): PnL=10389 [GOOD] — Unified microprice market maker that handles EMERALDS with a fixed fair and TOMA

## Round 5 results
- agent_r5_bifurcated_em_wide_tom_penny_sniper (gemini): PnL=0 [BAD] — Bifurcated logic for asset characteristics: EMERALDS uses wide quoting around fi
- agent_r5_bifurcated_dynamic_penny_unwind (openai): PnL=-26242 [BAD] — A unified fair‐value maker that bifurcates logic by asset. For EMERALDS it uses

## Round 6 results
- agent_r6_bifurcated_fixed_em_adaptive_tom (gemini): PnL=10592 [GOOD] — Bifurcated strategy using fixed fair value and wider quotes for EMERALDS, and ad
- agent_r6_bifurcated_micro_sniper_unwind (openai): PnL=0 [BAD] — A per‐asset bifurcated strategy: EMERALDS uses a fixed fair value market maker w

## Round 7 results
- agent_r7_bifurcated_static_em_adaptive_tom (gemini): PnL=9397 [GOOD] — Asset-specific strategies: fixed fair value for stationary EMERALDS with wide pa
- agent_r7_bifurcated_micro_mm (openai): PnL=2827 [GOOD] — A unified market-maker that bifurcates logic per asset: EMERALDS uses a fixed fa

## Round 8 results
- agent_r8_bifurcated_fixed_em_dynamic_tom (gemini): PnL=69 [weak] — Bifurcated strategy using fixed fair value for EMERALDS to avoid adverse selecti
- agent_r8_bifurcated_micro_fv_inv_skew (openai): PnL=0 [BAD] — A unified microprice‐driven fair‐value market maker that splits logic per asset:

## Round 9 results
- agent_r9_bifurcated_em_fixed_tom_micro_penny (gemini): PnL=0 [BAD] — Bifurcated strategy tailored to asset specifics: EMERALDS uses a fixed fair valu
- agent_r9_bifurcated_inventory_micro_mm (openai): PnL=-570 [BAD] — Hybrid inventory‐aware market maker that tailors quoting logic per asset. For EM

## Round 10 results
- agent_r10_bifurcated_specialist_wide_em_safe_tom (gemini): PnL=10230 [GOOD] — Bifurcated strategy tailored to each asset's statistical profile. EMERALDS uses
- agent_r10_bifurcated_fair_mean_mm (openai): PnL=-616 [BAD] — One unified strategy that treats EMERALDS and TOMATOES separately: for EMERALDS

## Round 1 results
- agent_r1_agent_r4_bifurcated_em_wide_tom_micro_penny (gemini): PnL=0 [BAD] — Bifurcated strategy using strict 4-tick edge minimums for EMERALDS to avoid nega

## Round 2 results
- agent_r2_bifurcated_dynamic_penny_unwind (gemini): PnL=0 [BAD] — EMERALDS uses conditional pennying bounded by fixed FV; TOMATOES uses aggressive

## Round 3 results
- agent_r3_bifurcated_wide_emeralds_penny_tomatoes (gemini): PnL=12642 [GOOD] — Bifurcated architecture: wide quotes on EMERALDS to avoid adverse markouts and f

## Round 4 results
- agent_r4_bifurcated_wide_em_penny_tom_sniper (gemini): PnL=0 [BAD] — EMERALDS: Fixed FV with wide, non-pennying quotes to avoid negative markout. TOM
- agent_r4_hybrid_emer_tom_maker (openai): PnL=0 [BAD] — Fixed‐value mean‐reversion for EMERALDS plus EMA‐drift penny market‐making for T

## Round 5 results
- agent_r5_bifurcated_em_wider_tom_penny_sniper (gemini): PnL=0 [BAD] — Bifurcated: EMERALDS uses fixed FV=10000 and joins bb/ba (wider quotes) to avoid

## Round 6 results
- agent_r6_bifurcated_em_fader_tom_penny (gemini): PnL=0 [BAD] — EMERALDS fades large moves with wider fixed quotes, TOMATOES uses dynamic microp

## Round 7 results
- agent_r7_agent_r7_bifurcated_wide_em_penny_tom (gemini): PnL=0 [BAD] — Bifurcates execution: EMERALDS uses fixed 10K FV and joins best bid/ask to avoid

## Round 8 results
- agent_r8_agent_r8_bifurcated_drift_penny_vs_stable_join (gemini): PnL=14028 [GOOD] — Bifurcated strategy: dynamic microprice EMA with fair-capped pennying for drifti

## Round 9 results
- agent_r9_bifurcated_wide_em_penny_tom (gemini): PnL=0 [BAD] — EMERALDS uses wide fixed-offset quotes to avoid negative pennying markouts, whil

## Round 10 results
- agent_r10_bifurcated_hybrid_sniper_v2 (gemini): PnL=13595 [GOOD] — Adaptive maker/taker using EMA microprice for drifting TOMATOES and fixed deep q

## Round 11 results
- agent_r11_bifurcated_safe_penny_and_wide_peg (gemini): PnL=0 [BAD] — EMERALDS pegged to 10k with wide edge to avoid adverse selection; TOMATOES uses

## Round 12 results
- agent_r12_bifurcated_momentum_fader (gemini): PnL=12107 [GOOD] — Fixed wide-edge maker for EMERALDS to fade moves, momentum-EMA bounded pennying

## Round 13 results
- agent_r13_bifurcated_em_fade_tom_penny_v1 (gemini): PnL=0 [BAD] — Bifurcated architecture: EMERALDS uses wide passive quotes to fade large moves a
- agent_r13_emerald_tomato_hybrid_maker_sniper (openai): PnL=0 [BAD] — Stationary wide‐spread mean‐revert on EMERALDS + EMA‐drift market‐make + micropr

## Round 14 results
- agent_r14_bifurcated_smart_wider_emerald_penny_tomato (gemini): PnL=0 [BAD] — Bifurcates logic: fixed FV with wide quotes/conditional pennying for EMERALDS, E

## Round 15 results
- agent_r15_bifurcated_em_fade_tom_micro_penny (gemini): PnL=12308 [GOOD] — Fixed 10k fair value with wide anchored quotes for EMERALDS; EMA microprice with

## Round 16 results
- agent_r16_bifurcated_em_fixed_wide_tom_ema_penny (gemini): PnL=9308 [GOOD] — EMERALDS: Fixed 10000 FV with wide static quotes to fade moves. TOMATOES: EMA mi

## Round 17 results
- agent_r17_bifurcated_em_wide_tom_micro_penny (gemini): PnL=0 [BAD] — EMERALDS joins BBA to avoid negative pennying markouts with fixed fair, while TO

## Round 18 results
- agent_r18_agent_r9_em_wide_tom_micro_penny (gemini): PnL=0 [BAD] — Bifurcated strategy: wide fixed quotes for EMERALDS to avoid adverse selection,

## Round 19 results
- agent_r19_bifurcated_em_wide_tom_penny (gemini): PnL=0 [BAD] — Bifurcated strategy: wide joining for mean-reverting EMERALDS, microprice EMA pe

## Round 20 results
- agent_r20_bifurcated_asset_specialist (gemini): PnL=4080 [GOOD] — Fixed 10K FV with wide passive quotes for EMERALDS to avoid adverse selection, E

## Round 1 results
- agent_r1_bifurcated_markout_adaptive_v1 (gemini): PnL=0 [BAD] — Bifurcated strategy using fixed FV passive quoting for negative markout assets a

## Round 2 results
- agent_r2_bifurcated_em_wide_tom_penny_momentum (gemini): PnL=0 [BAD] — Bifurcated strategy: fixed 10K fair value with wide non-penny quotes for EMERALD
- agent_r2_bifurcated_inventory_mm (openai): PnL=0 [BAD] — Inventory‐skewed market making with fixed fair for stationary assets and EMA‐mic

## Round 3 results
- agent_r3_bifurcated_wide_em_penny_tom_micro (gemini): PnL=0 [BAD] — Bifurcated architecture: Fixed-wide limit quoting for stationary Emeralds to avo
- agent_r3_bifurcated_skewed_mean_reversion (openai): PnL=0 [BAD] — Dual logic: fixed mean‐reversion for EMERALDS, momentum‐enhanced EMA market‐maki

## Round 4 results
- agent_r4_bifurcated_drift_and_fade (gemini): PnL=0 [BAD] — Bifurcated architecture: passive wide quotes for stationary EMERALDS to avoid ad

## Round 5 results
- agent_r5_bifurcated_fade_and_penny (gemini): PnL=0 [BAD] — Fixed fair value with passive fading for stationary assets; dynamic EMA micropri

## Round 6 results
- agent_r6_bifurcated_hybrid_sniper (gemini): PnL=0 [BAD] — Fixed fair value with strict minimum edge for stationary EMERALDS, and EMA micro

## Round 7 results
- agent_r7_bifurcated_wide_em_penny_tom (gemini): PnL=0 [BAD] — Bifurcated: Wide static quotes for Emeralds (avoiding negative markout) and EMA
- agent_r7_bifurcated_wide_spread_mean_revert (openai): PnL=4909 [GOOD] — Separate logic: EMERALDS use widened penny spread and mean-reversion around fixe

## Round 1 results
- agent_r1_bifurcated_fv_anchor_ema_penny (gemini): PnL=0 [BAD] — Bifurcated strategy: Fixed 10000 FV with deep passive quoting for EMERALDS, EMA

## Round 2 results
- agent_r2_bifurcated_deep_fade_and_penny_sniper (gemini): PnL=0 [BAD] — Bifurcated architecture: Fixed fair value with deep fading quotes for stationary

## Round 3 results
- agent_r3_bifurcated_anti_penny_em_penny_tom (gemini): PnL=15208 [GOOD] — Bifurcated strategy: anti-pennying (joining/wider) for stationary EMERALDS to av
- agent_r3_bifurcated_fixed_ema_mm (openai): PnL=-9655 [BAD] — Inventory-aware market maker with fixed fair value for stationary assets and EMA

## Round 4 results
- agent_r4_bifurcated_wide_em_penny_tom (gemini): PnL=0 [BAD] — Fixed fair wide quoting for Emeralds to avoid adverse selection, EMA microprice

## Round 8 results
- agent_r8_bifurcated_em_fixed_wide_tom_micro_penny (gemini): PnL=0 [BAD] — EMERALDS uses fixed fair value with wide maker quotes to avoid adverse selection

## Round 1 results
- agent_r1_bifurcated_precision_sniper (gemini): PnL=0 [BAD] — Combines fixed-offset quoting for stationary assets to guarantee platform fills

## Round 2 results
- agent_r2_bifurcated_spread_positioning (gemini): PnL=0 [BAD] — Joins the book (never tightens) for stationary EMERALDS to avoid adverse selecti

## Round 3 results
- agent_r3_bifurcated_smart_quoter_sniper (gemini): PnL=0 [BAD] — Bifurcates logic: wide passive quotes + sniping for mean-reverting EMERALDS, and
- agent_r3_bifurcated_mean_revert_and_mixed_price_mm (openai): PnL=0 [BAD] — Inventory-skewed market making with aggressive mean-reversion on stationary asse

## Round 5 results
- agent_r5_bifurcated_anti_penny_em_penny_tom (gemini): PnL=0 [BAD] — Asset-specific architecture: Fixed FV with wide passive quotes for EMERALDS to a

## Round 9 results
- agent_r9_bifurcated_markout_optimizer (gemini): PnL=15345 [GOOD] — Asset-specific quoting driven by empirical markout data: wider fixed-edge for Em
- agent_r9_smart_bifurcated_penny_unwind (openai): PnL=0 [BAD] — Inventory‐aware market maker with asset‐specific quoting: wide‐tick mean‐reversi

## Round 4 results
- agent_r4_bifurcated_fv_and_dynamic_penny_unwind (gemini): PnL=0 [BAD] — Bifurcated architecture: Fixed FV with deep passive quotes for Emeralds; Micropr
- agent_r4_dual_asset_specialist (openai): PnL=0 [BAD] — Hybrid EMERALDS static mean-reverter + TOMATOES microprice momentum market maker

## Round 6 results
- agent_r6_bifurcated_specialist_v1 (gemini): PnL=14422 [GOOD] — Fixed 10k FV and quote joining for EMERALDS; EMA microprice and pennying for TOM
- agent_r6_bifurcated_skewed_inventory_mm (openai): PnL=0 [BAD] — Inventory‐aware market‐making: widened, skewed quotes for stationary EMERALDS; m

## Round 5 results
- agent_r5_bifurcated_fixed_em_ema_tom (gemini): PnL=0 [BAD] — Bifurcated architecture using fixed FV=10000 with wider passive quotes for Emera

## Round 10 results
- agent_r10_bifurcated_wide_em_penny_tom (gemini): PnL=0 [BAD] — Strict bifurcation: wide queue-joining for Emeralds (avoids negative markout), d

## Round 7 results
- agent_r7_bifurcated_asset_specialist (gemini): PnL=8784 [GOOD] — Fixed fair value with static edge quotes for stationary EMERALDS to avoid advers

## Round 6 results
- agent_r6_bifurcated_precision_sniper (gemini): PnL=11203 [GOOD] — Bifurcates based on stationarity: Fixed FV with wide passive edges for EMERALDS

## Round 11 results
- agent_r11_bifurcated_markout_fader_penny_sniper (gemini): PnL=0 [BAD] — Bifurcated quoting based on markout data: wide fixed-value quoting for EMERALDS

## Round 8 results
- agent_r8_bifurcated_specialist_v1 (gemini): PnL=0 [BAD] — Strict 10K FV with wide quoting for stationary EMERALDS, microprice EMA with agg
- agent_r8_layered_fade_market_maker (openai): PnL=0 [BAD] — Inventory-aware market maker with dual-layer passive quotes plus aggressive fadi

## Round 7 results
- agent_r7_bifurcated_markout_adaptive (gemini): PnL=0 [BAD] — Bifurcated logic avoiding adverse pennying on Emeralds while exploiting positive
- agent_r7_two_tiered_fv_mm_sniper (openai): PnL=860 [ok] — Static wide‐spread market making on stationary assets + adaptive microprice EMA

## Round 9 results
- agent_r9_bifurcated_precision_maker (gemini): PnL=0 [BAD] — Bifurcated architecture: passive deep-book maker for stationary EMERALDS, and ed

## Round 12 results
- agent_r12_bifurcated_precision_sniper (gemini): PnL=0 [BAD] — Asset-specific architectures: queue-joining around fixed fair value for Emeralds
- agent_r12_bifurcated_mean_revert_market_maker (openai): PnL=0 [BAD] — Inventory-skewed market maker that applies fixed-fair mean reversion on Emeralds

## Round 10 results
- agent_r10_bifurcated_specialist_v2_optimal (gemini): PnL=0 [BAD] — Strict bifurcation: Fixed FV wide quotes for EMERALDS to avoid negative penny ma

## Round 8 results
- agent_r8_bifurcated_smart_penny_sniper (gemini): PnL=15683 [GOOD] — Asset-specific fair value (fixed vs EMA) with inventory skew, smart pennying, an
- agent_r8_bifurcated_adaptive_mm (openai): PnL=0 [BAD] — Inventory-aware market maker for EMERALDS with widened spread and dynamic EMA+OB

## Round 11 results
- agent_r11_bifurcated_wide_em_penny_tom (gemini): PnL=0 [BAD] — Bifurcated strategy: wide fixed-edge quotes for stationary Emeralds to avoid adv

## Round 9 results
- agent_r9_bifurcated_precision_sniper (gemini): PnL=12852 [GOOD] — Bifurcated architecture: dynamic EMA + pennying for TOMATOES (positive markout),

## Round 13 results
- agent_r13_bifurcated_stationary_drifting_sniper (gemini): PnL=0 [BAD] — Bifurcated architecture: fixed-anchor wide quoting for stationary assets to avoi
- agent_r13_bifurcated_mean_reversion_with_obi_sniper (openai): PnL=0 [BAD] — Mean‐reversion market‐making on stationary EMERALDS with a 2‐tick spread and agg

## Round 12 results
- agent_r12_strict_bifurcated_empirical_sniper (gemini): PnL=0 [BAD] — Fixed fair value with wide bounds for stationary EMERALDS to avoid adverse marko

## Round 14 results
- agent_r14_bifurcated_regime_sniper (gemini): PnL=69 [weak] — Fixed-anchor passive making for stationary assets; Microprice EMA pennying + sni

## Round 10 results
- agent_r10_bifurcated_markout_adapter (gemini): PnL=9959 [GOOD] — Bifurcated strategy adapting to asset-specific markouts: wide fixed quotes for E

## Round 13 results
- agent_r13_bifurcated_wide_fade_and_micro_penny (gemini): PnL=8086 [GOOD] — Bifurcated architecture: passive wide fading for EMERALDS (avoids adverse markou

## Round 15 results
- agent_r15_bifurcated_fixed_fade_and_dynamic_penny (gemini): PnL=0 [BAD] — Bifurcated architecture: wide fixed-anchor maker for Emeralds to avoid negative

## Round 11 results
- agent_r11_bifurcated_asset_optimized_v1 (gemini): PnL=0 [BAD] — Fixed FV with passive/wider quotes for stationary EMERALDS; EMA microprice with
- agent_r11_bifurcated_asset_specific_mm_pro (openai): PnL=0 [BAD] — Inventory‐aware market maker with widened quotes on stationary assets and microp

## Round 14 results
- agent_r14_bifurcated_wide_em_penny_tom_micro (gemini): PnL=0 [BAD] — Bifurcated strategy: wide fixed-fair quotes for adverse EMERALDS, microprice EMA

## Round 16 results
- agent_r16_bifurcated_markout_adaptive_sniper (gemini): PnL=0 [BAD] — Bifurcated strategy: fixed-FV wide-quoting for EMERALDS to avoid negative markou

## Round 12 results
- agent_r12_bifurcated_conditional_penny_sniper (gemini): PnL=0 [BAD] — Bifurcated strategy using fixed fair value for stationary assets and microprice
- agent_r12_asset_specific_wide_penny_sniper (openai): PnL=-37673 [BAD] — Inventory‐aware wide‐spread pennying on Emeralds and EMA+momentum pennying with

## Round 15 results
- agent_r15_bifurcated_passive_penny_sniper (gemini): PnL=11417 [GOOD] — Bifurcated adaptive strategy: fixed-value passive maker for EMERALDS (avoids neg

## Round 16 results
- agent_r16_bifurcated_em_queue_tom_micro_penny (gemini): PnL=0 [BAD] — Bifurcated architecture: queue-joining for EMERALDS to avoid adverse selection,

## Round 13 results
- agent_r13_bifurcated_wide_emerald_penny_tomato (gemini): PnL=12410 [GOOD] — Bifurcated strategy using wide passive quotes for stationary EMERALDS to avoid a
- agent_r13_bifurcated_inventory_reversion_sniper (openai): PnL=8814 [GOOD] — Inventory‐aware mean‐reversion MM on stationary EMERALDS plus EMA+momentum penny

## Round 17 results
- agent_r17_bifurcated_static_drift_optimizer (gemini): PnL=10371 [GOOD] — Bifurcated architecture: fixed-value wider quoting for stationary EMERALDS to av

## Round 14 results
- agent_r14_bifurcated_markout_adapted_sniper (gemini): PnL=10465 [GOOD] — Bifurcated strategy using passive joining for stationary assets (avoiding advers

## Round 17 results
- agent_r17_bifurcated_drift_stationary_sniper (gemini): PnL=0 [BAD] — Bifurcated architecture: wider passive quotes for stationary EMERALDS to avoid a
- agent_r17_bifurcated_adaptive_inventory_mm (openai): PnL=0 [BAD] — Inventory-aware hybrid market maker: widened quotes on stationary EMERALDS to re

## Round 15 results
- agent_r15_bifurcated_wide_emerald_penny_tomato (gemini): PnL=9012 [GOOD] — Stop pennying Emeralds due to adverse markouts; use fixed wide quotes for Emeral

## Round 18 results
- agent_r18_bifurcated_markout_adaptive_sniper (gemini): PnL=0 [BAD] — Bifurcated strategy using wide fixed quotes for stationary EMERALDS (negative pe

## Round 18 results
- agent_r18_bifurcated_drift_sniper_v2 (gemini): PnL=0 [BAD] — Bifurcated architecture: strict fixed-distance quoting for stationary EMERALDS t

## Round 16 results
- agent_r16_agent_r16_optimized_bifurcated (gemini): PnL=8503 [GOOD] — Bifurcated strategy: wide passive quoting for stationary EMERALDS to fix adverse

## Round 19 results
- agent_r19_bifurcated_em_wide_tom_penny (gemini): PnL=13747 [GOOD] — Fixed 10k fair value with wide quotes for Emeralds to avoid adverse selection; E
- agent_r19_bifurcated_spread_zscore_sniper (openai): PnL=0 [BAD] — Widened spread market‐making on stationary assets with z-score reversion and mic

## Round 19 results
- agent_r19_bifurcated_fv_penny_momentum (gemini): PnL=11318 [GOOD] — Bifurcated architecture: Fixed FV with wide passive quotes for stationary EMERAL

## Round 17 results
- agent_r17_bifurcated_smart_penny_and_fader (gemini): PnL=0 [BAD] — Bifurcated: wide passive quotes for stationary Emeralds to combat negative marko

## Round 1 results
- agent_r1_bifurcated_drift_and_stationary_v1 (gemini): PnL=0 [BAD] — Fixed fair value with wide static quotes for stationary EMERALDS; EMA microprice
- agent_r1_depth_reversion_sniper (openai): PnL=-400859 [BAD] — Adaptive depth-skewed market making with dynamic z-score spread for stationary E

## Round 20 results
- agent_r20_bifurcated_markout_adaptive_sniper (gemini): PnL=0 [BAD] — Asset-specific strategies based on markout profiles: wide passive quotes for sta

## Round 20 results
- agent_r20_bifurcated_fv_micro_unwind (gemini): PnL=0 [BAD] — Fixed wide-margin FV for EMERALDS to avoid negative markout; OBI-adjusted microp

## Round 18 results
- agent_r18_bifurcated_smart_markout (gemini): PnL=0 [BAD] — Exploits asset-specific markouts: fixed-offset quoting for EMERALDS to avoid adv

## Round 2 results
- agent_r2_bifurcated_empirical_specialist (gemini): PnL=0 [BAD] — Strictly bifurcated strategy: fixed wide quoting for stationary Emeralds, microp
- agent_r2_bifurcated_penny_sniper (openai): PnL=0 [BAD] — Asset-specific penny-sniper with widened quotes on stationary EMERALDS and micro

## Round 19 results
- agent_r19_bifurcated_markout_adaptive (gemini): PnL=0 [BAD] — Wider fixed-fair quotes for stationary assets (to avoid negative markout) and mi

## Round 20 results
- agent_r20_bifurcated_drift_penny_and_stable_fader (gemini): PnL=0 [BAD] — Bifurcated strategy using wide passive fading for stationary assets and bounded
- agent_r20_bifurcated_mean_reversion_mm (openai): PnL=0 [BAD] — Separate market-making rules for stationary vs drifting assets with widened spre

## Round 1 results
- agent_r1_bifurcated_markout_adaptive_sniper (gemini): PnL=0 [BAD] — Bifurcated strategy using deep value quotes for stationary assets to avoid adver
- agent_r1_bifurcated_zscore_penny_sniper (openai): PnL=0 [BAD] — Separate logic per stationary vs drifting: z-score mean-reversion for EMERALDS,

## Round 1 results
- agent_r1_bifurcated_adaptive_sniper (gemini): PnL=0 [BAD] — Differentiated pipelines: wide fixed quoting for stationary assets to avoid adve

## Round 8 results
- agent_r8_bifurcated_inventory_mm (openai): PnL=0 [BAD] — Wide‐quote mean‐revert for EMERALDS; microprice‐EMA penny+sniper for TOMATOES wi

## Round 9 results
- agent_r9_bifurcated_markout_skew_mm (openai): PnL=0 [BAD] — Inventory-aware market making with asset-specific spread based on markout and mo

## Round 1 results
- agent_r1_bifurcated_skewed_microprice_fade (gemini): PnL=0 [BAD] — Inventory-skewed fading from fixed fair for stationary EMERALDS, and microprice
- agent_r1_bifurcated_stationary_wide_quote_drifting_penny_sniper (openai): PnL=0 [BAD] — Use asset-type-specific logic: EMERALDS as a fixed-fair, wider passive mean-reve

## Round 2 results
- agent_r2_bifurcated_penny_sniper_v2 (gemini): PnL=0 [BAD] — Fixed fair value for stable assets to avoid missed fills, microprice EMA for dri

## Round 13 results
- agent_r13_bifurcated_asset_specialist (gemini): PnL=0 [BAD] — Fixed 10k fair value with wider quotes for Emeralds, microprice EMA with pennyin

## Round 4 results
- agent_r4_dual_reversion_maker (openai): PnL=3997 [GOOD] — Mean-reversion market maker for EMERALDS with Z-score and dynamic microprice+mom

## Round 16 results
- agent_r16_bifurcated_wide_emerald_penny_tomato (gemini): PnL=0 [BAD] — Bifurcated architecture: Wide passive quoting for stationary EMERALDS to fade mo

## Round 5 results
- agent_r5_bifurcated_passive_emerald_penny_tomato (gemini): PnL=0 [BAD] — Wide passive quoting for stable assets to avoid adverse markout, and EMA-based p

## Round 17 results
- agent_r17_bifurcated_penny_and_fade (gemini): PnL=11579 [GOOD] — Bifurcated execution: fixed fair fading for Emeralds, microprice EMA pennying fo

## Round 6 results
- agent_r6_bifurcated_markout_optimized_sniper (gemini): PnL=15654 [GOOD] — Bifurcated strategy using wide queue-joining for stationary Emeralds (to avoid a

## Round 1 results
- agent_r1_bifurcated_wide_stationary_tight_drifting (gemini): PnL=11242 [GOOD] — Bifurcates execution: wide-edge fixed-fair deep quoting for stationary assets to
- agent_r1_bifurcated_stationary_wide_quote_drifting_penny_sniper (openai): PnL=14099 [GOOD] — Use asset classification explicitly: EMERALDS as stationary with fixed-fair wide

## Round 7 results
- agent_r7_bifurcated_wide_emerald_penny_tomato (gemini): PnL=9323 [GOOD] — Fixed wide-edge quotes for Emeralds to dodge adverse markout, combined with aggr

## Round 18 results
- agent_r18_bifurcated_static_wide_dynamic_penny_sniper (gemini): PnL=10161 [GOOD] — Fixed 10K anchor with wide quotes for EMERALDS (anti-adverse selection) + EMA mi
- agent_r18_bifurcated_reversion_sniper (openai): PnL=0 [BAD] — Use aggressive mean‐reversion on stationary EMERALDS and dynamic EMA+microprice

## Round 2 results
- agent_r2_bifurcated_markout_specialist (gemini): PnL=0 [BAD] — Bifurcated strategy using fixed-anchored wide quotes for stationary assets (avoi
- agent_r2_tomato_heavy_bifurcated_penny_reversion_unwind (openai): PnL=13272 [GOOD] — Asset-specific simple maker: conservative fixed-fair quoting for stationary EMER

## Round 8 results
- agent_r8_bifurcated_drift_penny_stable_fade (gemini): PnL=7312 [GOOD] — Bifurcated logic: wide passive quotes around 10k for EMERALDS (fading moves) and

## Round 19 results
- agent_r19_bifurcated_wide_stationary_penny_drifter (gemini): PnL=3363 [GOOD] — Fixed fair value with wide resting quotes for stationary assets to avoid adverse
- agent_r19_bifurcated_dynamic_mm (openai): PnL=7619 [GOOD] — Hybrid inventory-aware market maker: dynamic spread for emeralds, microprice+mom

## Round 3 results
- agent_r3_asymmetric_markout_optimizer (gemini): PnL=13474 [GOOD] — Bifurcated strategy using fixed wide bounds for negative-markout stationary asse
- agent_r3_asset_specific_quote_gating_sniper (openai): PnL=7534 [GOOD] — Bifurcated maker-sniper: conservative fixed-fair quoting for stationary EMERALDS

## Round 9 results
- agent_r9_bifurcated_safe_penny_sniper (gemini): PnL=15882 [GOOD] — Bifurcates logic: fixed fair value for stationary EMERALDS, EMA microprice for d
- agent_r9_bifurcated_reversion_mm (openai): PnL=0 [BAD] — Inventory-skewed MM with wide reversion quotes on stationary assets and EMA+micr

## Round 20 results
- agent_r20_bifurcated_penny_and_fade (gemini): PnL=9690 [GOOD] — Strict bifurcation: Dynamic EMA microprice + pennying for drifting TOMATOES, fix
- agent_r20_asset_specific_bifurcated_mm (openai): PnL=0 [BAD] — Adaptive inventory‐aware market maker: widen and mean‐revert on stationary asset

## Round 10 results
- agent_r10_bifurcated_wide_maker_and_obi_penny_sniper (gemini): PnL=-27432 [BAD] — Wide passive maker for EMERALDS to avoid adverse selection; OBI-enhanced EMA mic

## Round 4 results
- agent_r4_bifurcated_wide_emerald_penny_tomato (gemini): PnL=5494 [GOOD] — Bifurcated strategy using wide passive quotes for adverse-selection assets (EMER
- agent_r4_asymmetric_stationary_wide_and_drifting_penny_sniper (openai): PnL=8840 [GOOD] — Use asset-class bifurcation: conservative wide fixed-fair making for stationary

## Round 5 results
- agent_r5_bifurcated_markout_adaptive (gemini): PnL=10353 [GOOD] — Strict asset bifurcation: stationary wide-quoting for EMERALDS (avoids negative
- agent_r5_asymmetric_stationary_widequote_drifting_penny_sniper (openai): PnL=10468 [GOOD] — Use asset-class-specific quoting: EMERALDS gets conservative fixed-fair wide pas

## Round 11 results
- agent_r11_bifurcated_proven_microprice_sniper (gemini): PnL=10690 [GOOD] — Replicates the 2517 platform-proven logic for drifting assets (EMA+OBI, edge 8)
- agent_r11_bifurcated_adaptive_sniper (openai): PnL=1368 [GOOD] — Inventory‐aware, bifurcated mean‐reversion + sniper: wide‐edge for stationary EM

## Round 12 results
- agent_r12_bifurcated_wide_emeralds_micro_tomatoes (gemini): PnL=0 [BAD] — Bifurcated logic: wide passive quoting for EMERALDS to avoid adverse selection,

## Round 6 results
- agent_r6_agent_r9_bifurcated_drift_and_fade (gemini): PnL=14288 [GOOD] — Bifurcated strategy: dynamic EMA microprice tracking with pennying for drifting
- agent_r6_asset_specific_penny_with_stationary_widening_and_tomato_snipes (openai): PnL=4891 [GOOD] — Bifurcated two-asset market maker: conservative fixed-fair quoting for stationar

## Round 13 results
- agent_r13_bifurcated_adaptive_markout_sniper (gemini): PnL=0 [BAD] — Bifurcated strategy using wide fixed-distance fading for EMERALDS (anti-adverse

## Round 14 results
- agent_r14_bifurcated_momentum_microprice_sniper (gemini): PnL=14704 [GOOD] — Bifurcated logic using fixed FV with wide quotes for Emeralds to avoid negative

## Round 7 results
- agent_r7_bifurcated_value_constrained_pennying (gemini): PnL=13872 [GOOD] — Bifurcated strategy: EMERALDS uses stationary constraint to avoid adverse select
- agent_r7_asset_specific_quote_filter_unwind (openai): PnL=14371 [GOOD] — Bifurcated market maker: wide passive fixed-fair quoting for stationary EMERALDS

## Round 15 results
- agent_r15_wide_emerald_penny_tomato (gemini): PnL=1334 [GOOD] — Bifurcated: wide fading quotes for stationary EMERALDS to avoid adverse markout,
- agent_r15_bifurcated_zscore_momentum_mm (openai): PnL=1778 [GOOD] — Combine z-score mean-reversion for stationary EMERALDS with momentum-adjusted EM

## Round 8 results
- agent_r8_bifurcated_smart_fader_sniper (gemini): PnL=13423 [GOOD] — Asset-specific quote mechanics: queue-capped fixed fading for stationary EMERALD
- agent_r8_asset_specific_penny_sniper_with_stationary_wide_quotes (openai): PnL=12046 [GOOD] — Use bifurcated logic: conservative fixed-fair wide quoting for stationary EMERAL

## Round 16 results
- agent_r16_agent_r10_markout_adaptive_bifurcated (gemini): PnL=-5244 [BAD] — Bifurcated strategy using deep markout intelligence to dictate quote aggression

## Round 9 results
- agent_r9_bifurcated_wide_emerald_capped_penny_tomato (gemini): PnL=6183 [GOOD] — Bifurcated architecture: wide fixed-anchor quotes for stationary EMERALDS to fad
- agent_r9_bifurcated_stationary_wide_quote_drifting_penny_sniper (openai): PnL=14726 [GOOD] — Use asset-type-specific logic: wider, fixed-fair passive quoting for stationary

## Round 17 results
- agent_r17_bifurcated_wide_emerald_dynamic_tomato (gemini): PnL=13140 [GOOD] — Fixed-width quoting to avoid adverse selection on EMERALDS, combined with OBI-en
- agent_r17_zscore_mean_revert_sniper (openai): PnL=-61668 [BAD] — Z-score based mean reversion with differentiated maker/taker and inventory skew

## Round 10 results
- agent_r10_bifurcated_markout_optimizer (gemini): PnL=2232 [GOOD] — Bifurcated strategy: fixed-edge maker for Emeralds (due to negative penny markou
- agent_r10_stationary_wide_quotes_drifting_penny_sniper (openai): PnL=10750 [GOOD] — Asset-class bifurcated maker: wide fixed-fair quoting for stationary EMERALDS, d

## Round 18 results
- agent_r18_bifurcated_drift_adaptive_sniper (gemini): PnL=7216 [GOOD] — Bifurcated architecture combining fixed FV for EMERALDS and microprice EMA for T

## Round 11 results
- agent_r11_bifurcated_markout_adaptive_sniper (gemini): PnL=12297 [GOOD] — Bifurcated strategy using aggressive pennying for favorable markout assets (Toma
- agent_r11_asset_specific_penny_sniper_with_emerald_reversion_fade (openai): PnL=13472 [GOOD] — Bifurcated simple strategy: conservative fixed-fair reversion maker for stationa

## Round 19 results
- agent_r19_bifurcated_markout_specialist (gemini): PnL=11795 [GOOD] — Fixed wide quoting for stationary assets to avoid adverse pennying; EMA micropri
- agent_r19_zscore_obi_meanrevert_sniper (openai): PnL=13458 [GOOD] — Dual bifurcated mean–reversion with z-score widening on EMERALDS and hybrid EMA+

## Round 12 results
- agent_r12_bifurcated_markout_adaptive_sniper (gemini): PnL=7385 [GOOD] — Bifurcated strategy using fixed wide maker quotes for EMERALDS (avoids adverse m
- agent_r12_asset_specific_penny_with_stationary_fade_and_tomato_snipes (openai): PnL=13708 [GOOD] — Use bifurcated logic: EMERALDS gets fixed-fair passive market making with fade-o

## Round 20 results
- agent_r20_agent_r10_bifurcated_wide_emerald_penny_tomato (gemini): PnL=16353 [GOOD] — Bifurcated logic: Wide maker quoting for EMERALDS to avoid negative markout, and

## Round 13 results
- agent_r13_bifurcated_wide_maker_penny_sniper (gemini): PnL=11954 [GOOD] — Bifurcates by asset: wide passive quotes for stationary Emeralds to capture mean
- agent_r13_asset_split_emerald_fade_tomato_ema_penny_sniper (openai): PnL=14550 [GOOD] — Use bifurcated logic: EMERALDS gets fixed-fair fade/wide passive quoting to avoi

## Round 14 results
- agent_r14_bifurcated_fade_and_penny (gemini): PnL=14954 [GOOD] — Passive deep-book fading for stationary EMERALDS, aggressive microprice pennying
- agent_r14_asset_specific_penny_sniper_with_stationary_widening (openai): PnL=14082 [GOOD] — Bifurcated maker-sniper: conservative fixed-fair quoting for stationary EMERALDS

## Round 15 results
- agent_r15_bifurcated_markout_adaptive_sniper (gemini): PnL=0 [BAD] — EMERALDS avoids negative markout via fixed wide quotes, while TOMATOES exploits
- agent_r15_asset_specific_penny_sniper_with_emeralds_wider_quotes (openai): PnL=0 [BAD] — Bifurcated two-asset strategy: conservative fixed-fair market making for station

## Round 16 results
- agent_r16_bifurcated_adaptive_sniper (gemini): PnL=9578 [GOOD] — Asset-specific quoting: wide firm quotes around fixed fair for stationary, micro
- agent_r16_asset_specific_penny_with_emerald_fade_and_tomato_ema_sniper (openai): PnL=7014 [GOOD] — Use bifurcated logic: EMERALDS gets fixed-fair mean-reversion quotes with select

## Round 17 results
- agent_r17_bifurcated_value_momentum_sniper (gemini): PnL=9434 [GOOD] — Fixed wide quotes for stationary Emeralds to avoid adverse markout, dynamic EMA
- agent_r17_asset_specific_penny_with_stationary_fade_and_tomato_sniper (openai): PnL=9798 [GOOD] — Bifurcated simple maker: EMERALDS uses fixed-fair passive fading with selective

## Round 18 results
- agent_r18_bifurcated_fader_penny_sniper (gemini): PnL=6904 [GOOD] — Passive wide quotes to fade EMERALDS (avoids negative markout), while actively p
- agent_r18_asset_split_penny_sniper_with_passive_emeralds (openai): PnL=14624 [GOOD] — Bifurcated quoting: very conservative fixed-fair passive maker for stationary EM

## Round 19 results
- agent_r19_bifurcated_stationary_fade_drifting_penny (gemini): PnL=0 [BAD] — EMERALDS: Wide fixed quotes to fade moves. TOMATOES: EMA microprice fair value +
- agent_r19_asset_split_penny_sniper_with_stationary_wide_quotes (openai): PnL=15115 [GOOD] — Bifurcated simple market maker: EMERALDS uses fixed-fair wider passive quotes pl

## Round 20 results
- agent_r20_bifurcated_micro_penny_sniper (gemini): PnL=10511 [GOOD] — Bifurcated strategy using fixed fair value wide quoting for stationary assets an
- agent_r20_asset_split_passive_emeralds_active_tomatoes (openai): PnL=10579 [GOOD] — Bifurcated quoting: EMERALDS uses conservative fixed-fair passive market making

## Round 1 results

## Round 1 results

## Round 1 results

## Round 1 results

## Round 1 results

## Round 1 results

## Round 1 results

## Round 1 results
