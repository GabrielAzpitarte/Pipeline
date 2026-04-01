"""Core simulation loop."""

from __future__ import annotations

from typing import Any

from trader.logging_utils import get_logger

logger = get_logger(__name__)


class SimEngine:
    """Run a strategy against historical data and collect results."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.results: list[dict[str, Any]] = []

    def run(self, data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Execute simulation over the provided data ticks."""
        logger.info("Starting sim with %d ticks", len(data))
        return self.results
