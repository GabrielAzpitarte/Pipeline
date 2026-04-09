"""Platform result ingestion — structured evidence from platform tests.

Every platform test becomes a full research artifact with discrepancy
analysis that feeds back into calibration, memory, and realism review.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trader.logging_utils import get_logger

_log = get_logger("submission.platform_ingestion")


@dataclass
class PlatformResultArtifact:
    """Complete evidence from one platform test."""

    strategy_name: str
    submission_date: str = ""

    # Local predictions (before submission)
    local_backtest_pnl: float = 0.0
    local_transfer_score: float = 0.0
    local_prediction: float = 0.0
    local_verdict: str = ""
    local_architecture_family: str = ""

    # Platform result
    platform_pnl: float = 0.0
    platform_fills: int | None = None
    platform_per_product_pnl: dict[str, float] = field(default_factory=dict)

    # Discrepancy analysis
    prediction_error: float = 0.0
    prediction_error_pct: float = 0.0
    discrepancy_type: str = "unknown"
    discrepancy_causes: list[str] = field(default_factory=list)

    # Linking
    strategy_code_hash: str = ""


def analyze_discrepancy(
    artifact: PlatformResultArtifact,
    local_diagnostics: dict[str, Any],
) -> list[str]:
    """Classify likely causes of local vs platform discrepancy.

    Uses local diagnostics (passive share, scenario PnLs, inventory,
    markout) to explain why platform result differs from prediction.
    """
    causes: list[str] = []

    error_pct = artifact.prediction_error_pct

    # Fill shortfall: high passive share + platform underperformance
    passive_share = local_diagnostics.get("passive_fill_share", 0)
    if passive_share > 0.8 and error_pct < -20:
        causes.append("passive_fill_shortfall")

    # Queue miss: queue_hostile scenario gap is large
    scenario_pnls = local_diagnostics.get("scenario_pnls", {})
    queue_pnl = scenario_pnls.get("queue_hostile", 0)
    baseline_pnl = scenario_pnls.get("baseline", 0)
    if baseline_pnl > 0 and queue_pnl > 0 and queue_pnl / baseline_pnl < 0.5:
        causes.append("queue_position_miss")

    # Inventory fragility
    max_inv = local_diagnostics.get("max_inventory", 0)
    if max_inv >= 70 and error_pct < -10:
        causes.append("inventory_management_miss")

    # Markout degradation
    markout = local_diagnostics.get("avg_markout_5", 0)
    if markout > 0.3 and error_pct < -15:
        causes.append("markout_degradation")

    # Adverse fills worse on platform
    adverse = local_diagnostics.get("adverse_rate_5", 0)
    if adverse > 0.5 and error_pct < -10:
        causes.append("adverse_selection_worse")

    # Strategy was locally overfit (parameter sweep winner)
    if "sweep" in artifact.strategy_name.lower() and error_pct < -20:
        causes.append("parameter_overfit")

    if not causes:
        if abs(error_pct) < 15:
            causes.append("accurate_prediction")
        else:
            causes.append("unknown_discrepancy")

    return causes


def create_platform_artifact(
    strategy_name: str,
    platform_pnl: float,
    local_prediction: float,
    local_backtest_pnl: float,
    local_transfer_score: float,
    local_verdict: str,
    architecture_family: str,
    local_diagnostics: dict[str, Any],
    platform_per_product_pnl: dict[str, float] | None = None,
    platform_fills: int | None = None,
) -> PlatformResultArtifact:
    """Create a complete platform result artifact with discrepancy analysis."""
    error = platform_pnl - local_prediction
    error_pct = error / max(1, abs(local_prediction)) * 100

    if abs(error_pct) < 15:
        disc_type = "accurate"
    elif error > 0:
        disc_type = "underestimate"
    else:
        disc_type = "overestimate"

    artifact = PlatformResultArtifact(
        strategy_name=strategy_name,
        submission_date=datetime.now(tz=UTC).isoformat(),
        local_backtest_pnl=local_backtest_pnl,
        local_transfer_score=local_transfer_score,
        local_prediction=local_prediction,
        local_verdict=local_verdict,
        local_architecture_family=architecture_family,
        platform_pnl=platform_pnl,
        platform_fills=platform_fills,
        platform_per_product_pnl=platform_per_product_pnl or {},
        prediction_error=error,
        prediction_error_pct=error_pct,
        discrepancy_type=disc_type,
    )

    artifact.discrepancy_causes = analyze_discrepancy(artifact, local_diagnostics)

    _log.info(
        "Platform artifact: %s — platform=%d, predicted=%d, error=%+d (%.0f%%), type=%s, causes=%s",
        strategy_name,
        platform_pnl,
        local_prediction,
        error,
        error_pct,
        disc_type,
        artifact.discrepancy_causes,
    )

    return artifact


def save_platform_artifact(artifact: PlatformResultArtifact, base_dir: Path) -> Path:
    """Save platform artifact to disk."""
    out_dir = base_dir / "platform_results"
    out_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{artifact.strategy_name}_{artifact.submission_date[:10]}.json"
    path = out_dir / filename
    path.write_text(json.dumps(asdict(artifact), indent=2, default=str))
    return path


def load_platform_artifacts(base_dir: Path) -> list[PlatformResultArtifact]:
    """Load all platform result artifacts."""
    results_dir = base_dir / "platform_results"
    if not results_dir.exists():
        return []
    artifacts: list[PlatformResultArtifact] = []
    for path in sorted(results_dir.glob("*.json")):
        d: dict[str, Any] = json.loads(path.read_text())
        artifacts.append(
            PlatformResultArtifact(
                strategy_name=d.get("strategy_name", ""),
                submission_date=d.get("submission_date", ""),
                local_backtest_pnl=d.get("local_backtest_pnl", 0),
                local_transfer_score=d.get("local_transfer_score", 0),
                local_prediction=d.get("local_prediction", 0),
                local_verdict=d.get("local_verdict", ""),
                local_architecture_family=d.get("local_architecture_family", ""),
                platform_pnl=d.get("platform_pnl", 0),
                platform_fills=d.get("platform_fills"),
                platform_per_product_pnl=d.get("platform_per_product_pnl", {}),
                prediction_error=d.get("prediction_error", 0),
                prediction_error_pct=d.get("prediction_error_pct", 0),
                discrepancy_type=d.get("discrepancy_type", "unknown"),
                discrepancy_causes=d.get("discrepancy_causes", []),
                strategy_code_hash=d.get("strategy_code_hash", ""),
            )
        )
    return artifacts
