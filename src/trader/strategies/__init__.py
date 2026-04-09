"""Strategy registry — import and register strategies here."""

from __future__ import annotations

from typing import Any, Protocol

from trader.datamodel import Order, TradingState


class Strategy(Protocol):
    """Interface every strategy must satisfy."""

    def compute_orders(self, state: TradingState) -> dict[str, list[Order]]:
        """Given market state, return orders keyed by product symbol."""
        ...


STRATEGIES: dict[str, type[Strategy]] = {}


def register(name: str) -> Any:
    """Decorator to register a strategy class."""

    def wrapper(cls: type[Strategy]) -> type[Strategy]:
        STRATEGIES[name] = cls
        return cls

    return wrapper


# Import strategy modules so they auto-register via @register decorator.
import trader.strategies.agent_r3_bifurcated_em_taker_tom_micro_sniper_variant_3 as _agent_r3_bifurcated_em_taker_tom_micro_sniper_variant_3  # noqa: F401, E402
import trader.strategies.fair_value as _fair_value  # noqa: F401, E402
import trader.strategies.inventory_mm as _inventory_mm  # noqa: F401, E402
import trader.strategies.market_maker as _market_maker  # noqa: F401, E402
import trader.strategies.microprice_sniper_proven as _microprice_sniper_proven  # noqa: F401, E402
import trader.strategies.noop as _noop  # noqa: F401, E402
import trader.strategies.taker_penny_proven as _taker_penny_proven  # noqa: F401, E402
