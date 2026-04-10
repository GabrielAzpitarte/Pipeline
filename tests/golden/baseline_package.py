"""Golden baseline package — frozen reference strategies for regression testing.

Every strategy here has known backtest PnL and (where available) known platform PnL.
Any simulation change that shifts these numbers must be investigated.
"""

from __future__ import annotations

BASELINE_STRATEGIES: dict[str, dict[str, object]] = {
    "market_maker": {
        "source": "src/trader/strategies/market_maker.py",
        "known_backtest_pnl": 1018,  # one_sided default replay
        "known_platform_pnl": 970,
        "pnl_tolerance": 10,
        "category": "baseline",
    },
    "microprice_sniper_proven": {
        "source": "src/trader/strategies/microprice_sniper_proven.py",
        "known_backtest_pnl": 4173,  # one_sided default replay
        "known_platform_pnl": 2517,
        "pnl_tolerance": 10,
        "category": "platform_proven",
    },
    "strat4_taker_penny": {
        "source": "test_strategies/strat4_taker_penny.py",
        "known_backtest_pnl": 2210,  # one_sided default replay
        "known_platform_pnl": 2540,
        "pnl_tolerance": 10,
        "category": "platform_proven",
    },
    "strat8_liquidity_momentum": {
        "source": "test_strategies/strat8_liquidity_momentum.py",
        "known_backtest_pnl": 3975,  # one_sided default replay
        "known_platform_pnl": 2490,
        "pnl_tolerance": 10,
        "category": "platform_proven",
    },
    "pipeline_best": {
        "source": "src/trader/strategies/agent_r3_bifurcated_em_taker_tom_micro_sniper_variant_3.py",
        "known_backtest_pnl": 3935,  # one_sided default replay
        "known_platform_pnl": 2500,
        "pnl_tolerance": 10,
        "category": "pipeline_generated",
    },
}
