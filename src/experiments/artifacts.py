"""Canonical run artifact — single source of truth for simulation output.

Every simulation run (engine, sweep worker, evaluator) produces a RunArtifact.
Every downstream component (analytics, evaluator, memory) consumes RunArtifact.
No component may compute its own metrics if those metrics exist here.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from analytics.metrics import compute_returns, max_drawdown, sharpe_ratio

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


@dataclass
class AssetSummary:
    """Derived metrics for one asset within a run."""

    symbol: str
    pnl: float = 0.0
    cash: float = 0.0
    fills: int = 0
    passive_fills: int = 0
    aggressive_fills: int = 0
    passive_fill_share: float = 0.0
    avg_inventory: float = 0.0
    max_inventory: int = 0


@dataclass
class RunSummary:
    """Derived metrics for the full run."""

    final_pnl: float = 0.0
    final_cash: float = 0.0
    final_positions: dict[str, int] = field(default_factory=dict)
    sharpe: float = 0.0
    max_drawdown: float = 0.0
    total_fills: int = 0
    passive_fills: int = 0
    aggressive_fills: int = 0
    passive_fill_share: float = 0.0
    avg_inventory: float = 0.0
    max_inventory: int = 0
    turnover: float = 0.0


@dataclass
class StoredFill:
    """A fill with timestamp, symbol, price, quantity, and source."""

    timestamp: int
    symbol: str
    price: int
    quantity: int
    against: str  # "book" or "market_trade"


@dataclass
class RunArtifact:
    """Single canonical output from any simulation run.

    Contains both raw execution facts (immutable after run) and derived
    metrics (computed once from facts, stored alongside for convenience).
    """

    # Identity
    run_id: str = ""
    strategy_name: str = ""
    timestamp: str = ""
    git_hash: str = ""
    dataset_id: str = ""  # "day_-1", "day_-2", etc.
    scenario_name: str = "baseline"
    config: dict[str, Any] = field(default_factory=dict)

    # Raw execution facts
    tick_timestamps: list[int] = field(default_factory=list)
    pnl_path: list[float] = field(default_factory=list)
    cash_path: list[float] = field(default_factory=list)
    positions_path: list[dict[str, int]] = field(default_factory=list)
    mid_prices_path: list[dict[str, float]] = field(default_factory=list)
    fills: list[StoredFill] = field(default_factory=list)
    orders_submitted: list[dict[str, list[dict[str, int]]]] = field(default_factory=list)

    # Derived metrics
    summary: RunSummary = field(default_factory=RunSummary)
    per_asset: dict[str, AssetSummary] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Construction helpers
# ---------------------------------------------------------------------------


def generate_run_id(strategy_name: str) -> str:
    """Generate a unique run ID."""
    now = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
    short = uuid.uuid4().hex[:6]
    return f"{now}_{strategy_name}_{short}"


def compute_summary(artifact: RunArtifact) -> RunSummary:
    """Compute derived summary metrics from raw execution facts."""
    n_ticks = len(artifact.tick_timestamps)
    returns = compute_returns(artifact.pnl_path)

    # Fill counts
    total = len(artifact.fills)
    passive = sum(1 for f in artifact.fills if f.against == "market_trade")
    aggressive = total - passive

    # Inventory
    inv_sum = 0.0
    max_inv = 0
    for pos_dict in artifact.positions_path:
        tick_inv = sum(abs(v) for v in pos_dict.values())
        inv_sum += tick_inv
        max_inv = max(max_inv, max((abs(v) for v in pos_dict.values()), default=0))

    # Volume
    total_volume = sum(abs(f.quantity) for f in artifact.fills)

    return RunSummary(
        final_pnl=artifact.pnl_path[-1] if artifact.pnl_path else 0.0,
        final_cash=artifact.cash_path[-1] if artifact.cash_path else 0.0,
        final_positions=(dict(artifact.positions_path[-1]) if artifact.positions_path else {}),
        sharpe=sharpe_ratio(returns),
        max_drawdown=max_drawdown(artifact.pnl_path),
        total_fills=total,
        passive_fills=passive,
        aggressive_fills=aggressive,
        passive_fill_share=passive / max(1, total),
        avg_inventory=inv_sum / max(1, n_ticks),
        max_inventory=max_inv,
        turnover=total_volume / max(1, n_ticks),
    )


def compute_per_asset(artifact: RunArtifact) -> dict[str, AssetSummary]:
    """Compute per-asset summaries from fills and position paths."""
    # Group fills by symbol
    sym_fills: dict[str, list[StoredFill]] = {}
    for f in artifact.fills:
        sym_fills.setdefault(f.symbol, []).append(f)

    # Discover all symbols
    symbols: set[str] = set(sym_fills.keys())
    for pos_dict in artifact.positions_path:
        symbols.update(pos_dict.keys())

    n_ticks = len(artifact.tick_timestamps)
    result: dict[str, AssetSummary] = {}

    for sym in sorted(symbols):
        fills = sym_fills.get(sym, [])
        passive = sum(1 for f in fills if f.against == "market_trade")
        aggressive = len(fills) - passive

        # PnL: cash from fills + unrealized
        cash = sum(-f.price * f.quantity for f in fills)
        final_pos = artifact.positions_path[-1].get(sym, 0) if artifact.positions_path else 0
        final_mid = artifact.mid_prices_path[-1].get(sym, 0.0) if artifact.mid_prices_path else 0.0
        pnl = cash + final_pos * final_mid

        # Inventory
        inv_sum = 0.0
        max_inv = 0
        for pos_dict in artifact.positions_path:
            pos = abs(pos_dict.get(sym, 0))
            inv_sum += pos
            max_inv = max(max_inv, pos)

        result[sym] = AssetSummary(
            symbol=sym,
            pnl=pnl,
            cash=cash,
            fills=len(fills),
            passive_fills=passive,
            aggressive_fills=aggressive,
            passive_fill_share=passive / max(1, len(fills)),
            avg_inventory=inv_sum / max(1, n_ticks),
            max_inventory=max_inv,
        )

    return result


def finalize_artifact(artifact: RunArtifact) -> RunArtifact:
    """Compute and attach all derived metrics to an artifact."""
    artifact.summary = compute_summary(artifact)
    artifact.per_asset = compute_per_asset(artifact)
    return artifact


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def artifact_to_dict(artifact: RunArtifact) -> dict[str, Any]:
    """Convert a RunArtifact to a JSON-serializable dict."""
    d = asdict(artifact)
    return d


def dict_to_artifact(d: dict[str, Any]) -> RunArtifact:
    """Reconstruct a RunArtifact from a dict."""
    fills = [StoredFill(**f) for f in d.get("fills", [])]
    summary = RunSummary(**d.get("summary", {}))
    per_asset = {sym: AssetSummary(**data) for sym, data in d.get("per_asset", {}).items()}

    return RunArtifact(
        run_id=d.get("run_id", ""),
        strategy_name=d.get("strategy_name", ""),
        timestamp=d.get("timestamp", ""),
        git_hash=d.get("git_hash", ""),
        dataset_id=d.get("dataset_id", ""),
        scenario_name=d.get("scenario_name", "baseline"),
        config=d.get("config", {}),
        tick_timestamps=d.get("tick_timestamps", []),
        pnl_path=d.get("pnl_path", []),
        cash_path=d.get("cash_path", []),
        positions_path=d.get("positions_path", []),
        mid_prices_path=d.get("mid_prices_path", []),
        fills=fills,
        orders_submitted=d.get("orders_submitted", []),
        summary=summary,
        per_asset=per_asset,
    )


def save_artifact(artifact: RunArtifact, base_dir: Path) -> Path:
    """Save artifact to disk as JSON."""
    out_dir = base_dir / "runs" / artifact.run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "artifact.json"
    out_path.write_text(json.dumps(artifact_to_dict(artifact), indent=2, default=str))
    return out_path


def load_artifact(run_id: str, base_dir: Path) -> RunArtifact:
    """Load artifact from disk."""
    path = base_dir / "runs" / run_id / "artifact.json"
    d: dict[str, Any] = json.loads(path.read_text())
    return dict_to_artifact(d)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_artifact(artifact: RunArtifact) -> list[str]:
    """Check artifact for consistency errors. Returns list of error messages."""
    errors: list[str] = []
    n = len(artifact.tick_timestamps)

    if len(artifact.pnl_path) != n:
        errors.append(f"pnl_path length {len(artifact.pnl_path)} != tick count {n}")
    if len(artifact.cash_path) != n:
        errors.append(f"cash_path length {len(artifact.cash_path)} != tick count {n}")
    if len(artifact.positions_path) != n:
        errors.append(f"positions_path length {len(artifact.positions_path)} != tick count {n}")
    if len(artifact.mid_prices_path) != n:
        errors.append(f"mid_prices_path length {len(artifact.mid_prices_path)} != tick count {n}")

    if not artifact.run_id:
        errors.append("Missing run_id")
    if not artifact.strategy_name:
        errors.append("Missing strategy_name")

    # PnL reconciliation
    if artifact.pnl_path and artifact.summary.final_pnl != 0:
        path_final = artifact.pnl_path[-1]
        if abs(path_final - artifact.summary.final_pnl) > 0.01:
            errors.append(
                f"PnL mismatch: path[-1]={path_final:.2f} vs summary={artifact.summary.final_pnl:.2f}"
            )

    return errors
