"""Canonical data types for persisting and reloading sim runs."""

from __future__ import annotations

import subprocess
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from sim.engine import SimConfig, SimResult
from sim.matching import Fill

# ---------------------------------------------------------------------------
# Stored types
# ---------------------------------------------------------------------------


@dataclass
class RunMetadata:
    """Identity and provenance of a single sim run."""

    run_id: str
    timestamp: str  # ISO-8601
    strategy_name: str
    config: dict[str, Any]
    git_hash: str
    dataset_description: str
    tags: list[str]


@dataclass
class StoredFill:
    """A fill with its tick timestamp attached (for storage)."""

    timestamp: int
    symbol: str
    price: int
    quantity: int
    against: str


@dataclass
class RunData:
    """The full payload for one persisted run."""

    metadata: RunMetadata
    timestamps: list[int]
    pnl_series: list[float]
    position_series: list[dict[str, int]]
    cash_series: list[float]
    mid_price_series: list[dict[str, float]]
    fills: list[StoredFill]
    orders_submitted: list[dict[str, list[dict[str, int]]]]
    final_pnl: float
    final_positions: dict[str, int]
    final_cash: float


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def generate_run_id(strategy_name: str) -> str:
    """Generate a unique run ID: YYYYMMDD_HHMMSS_{strategy}_{6-char-uuid}."""
    now = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    short_uuid = uuid.uuid4().hex[:6]
    return f"{now}_{strategy_name}_{short_uuid}"


def get_git_hash() -> str:
    """Return the short git commit hash, or '' if unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _serialize_order(order: Any) -> dict[str, int]:
    """Convert an Order object to a simple dict."""
    return {"price": int(order.price), "quantity": int(order.quantity)}


def _serialize_orders_for_tick(
    orders: dict[str, list[Any]],
) -> dict[str, list[dict[str, int]]]:
    """Serialize a tick's orders dict to JSON-friendly form."""
    return {sym: [_serialize_order(o) for o in ords] for sym, ords in orders.items()}


def _fill_to_stored(fill: Fill, timestamp: int) -> StoredFill:
    """Attach a timestamp to a Fill for storage."""
    return StoredFill(
        timestamp=timestamp,
        symbol=fill.symbol,
        price=fill.price,
        quantity=fill.quantity,
        against=fill.against,
    )


# ---------------------------------------------------------------------------
# Conversion: SimResult -> RunData
# ---------------------------------------------------------------------------


def sim_result_to_run_data(
    result: SimResult,
    config: SimConfig,
    dataset_description: str = "",
    tags: list[str] | None = None,
) -> RunData:
    """Convert a SimResult + metadata into a RunData for storage."""
    metadata = RunMetadata(
        run_id=generate_run_id(config.strategy_name),
        timestamp=datetime.now(tz=UTC).isoformat(),
        strategy_name=config.strategy_name,
        config={
            "trade_match_mode": config.trade_match_mode.value,
            "strategy_name": config.strategy_name,
            "strategy_params": dict(config.strategy_params),
            "max_order_size": config.risk_limits.max_order_size,
            "max_open_orders": config.risk_limits.max_open_orders,
        },
        git_hash=get_git_hash(),
        dataset_description=dataset_description,
        tags=tags or [],
    )

    # Build time series from TickResults
    timestamps: list[int] = []
    pnl_series: list[float] = []
    position_series: list[dict[str, int]] = []
    cash_series: list[float] = []
    mid_price_series: list[dict[str, float]] = []
    orders_submitted: list[dict[str, list[dict[str, int]]]] = []
    fills: list[StoredFill] = []

    for tick in result.ticks:
        timestamps.append(tick.timestamp)
        pnl_series.append(tick.pnl)
        position_series.append(dict(tick.positions))
        cash_series.append(tick.cash)
        mid_price_series.append(dict(tick.mid_prices))
        orders_submitted.append(_serialize_orders_for_tick(tick.orders_submitted))

        for _sym, fill_list in tick.fills.items():
            for fill in fill_list:
                fills.append(_fill_to_stored(fill, tick.timestamp))

    return RunData(
        metadata=metadata,
        timestamps=timestamps,
        pnl_series=pnl_series,
        position_series=position_series,
        cash_series=cash_series,
        mid_price_series=mid_price_series,
        fills=fills,
        orders_submitted=orders_submitted,
        final_pnl=result.final_pnl,
        final_positions=dict(result.final_positions),
        final_cash=result.final_cash,
    )


# ---------------------------------------------------------------------------
# Serialization: RunData <-> dict
# ---------------------------------------------------------------------------


def run_data_to_dict(run_data: RunData) -> dict[str, Any]:
    """Convert RunData to a JSON-serializable dict."""
    return {
        "metadata": asdict(run_data.metadata),
        "timestamps": run_data.timestamps,
        "pnl_series": run_data.pnl_series,
        "position_series": run_data.position_series,
        "cash_series": run_data.cash_series,
        "mid_price_series": run_data.mid_price_series,
        "fills": [asdict(f) for f in run_data.fills],
        "orders_submitted": run_data.orders_submitted,
        "final_pnl": run_data.final_pnl,
        "final_positions": run_data.final_positions,
        "final_cash": run_data.final_cash,
    }


def dict_to_run_data(d: dict[str, Any]) -> RunData:
    """Reconstruct a RunData from a dict loaded from JSON."""
    meta = d["metadata"]
    return RunData(
        metadata=RunMetadata(
            run_id=meta["run_id"],
            timestamp=meta["timestamp"],
            strategy_name=meta["strategy_name"],
            config=meta["config"],
            git_hash=meta["git_hash"],
            dataset_description=meta["dataset_description"],
            tags=meta["tags"],
        ),
        timestamps=d["timestamps"],
        pnl_series=d["pnl_series"],
        position_series=d["position_series"],
        cash_series=d["cash_series"],
        mid_price_series=d["mid_price_series"],
        fills=[StoredFill(**f) for f in d["fills"]],
        orders_submitted=d["orders_submitted"],
        final_pnl=d["final_pnl"],
        final_positions=d["final_positions"],
        final_cash=d["final_cash"],
    )
