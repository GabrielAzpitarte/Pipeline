"""Main Trader class that dispatches to a strategy and enforces risk."""

from __future__ import annotations

import inspect
from typing import Any

from trader.datamodel import Order, TradingState
from trader.logging_utils import get_logger
from trader.risk import RiskLimits, validate_orders
from trader.strategies import STRATEGIES, Strategy

_log = get_logger("trader")


class Trader:
    """Receives market state, delegates to a strategy, filters through risk."""

    def __init__(
        self,
        strategy_name: str = "noop",
        params: dict[str, Any] | None = None,
    ) -> None:
        self.strategy_name = strategy_name
        self._params = params
        self._strategy_instance: Strategy | None = None

    def _get_strategy(self) -> Strategy:
        """Lazy-load the strategy from the registry."""
        if self._strategy_instance is None:
            cls = STRATEGIES.get(self.strategy_name)
            if cls is None:
                available = list(STRATEGIES.keys())
                raise ValueError(f"Unknown strategy {self.strategy_name!r}. Available: {available}")
            if self._params is not None:
                sig = inspect.signature(cls.__init__)
                if "params" in sig.parameters:
                    self._strategy_instance = cls(params=self._params)  # type: ignore[call-arg]
                else:
                    self._strategy_instance = cls()
            else:
                self._strategy_instance = cls()
            _log.info("Loaded strategy: %s", self.strategy_name)
        return self._strategy_instance

    def run(
        self,
        state: TradingState,
        risk_limits: RiskLimits | None = None,
    ) -> tuple[dict[str, list[Order]], int, str]:
        """Prosperity-compatible entry point.

        Returns:
            (orders, conversions, traderData)
        """
        strategy = self._get_strategy()
        raw_orders = strategy.compute_orders(state)
        filtered = validate_orders(raw_orders, state.position, limits=risk_limits)
        return filtered, 0, ""
