"""False-positive and false-negative ranking audit.

Systematically studies ranking mistakes by comparing local rankings
(backtest PnL and transfer score) to actual platform outcomes.
Identifies recurring failure signatures to improve the pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from analytics.calibration import CalibrationPoint, spearman_rank_correlation

# ---------------------------------------------------------------------------
# Failure signatures
# ---------------------------------------------------------------------------

FAILURE_SIGNATURES: dict[str, str] = {
    "passive_fill_overestimate": "Strategy scored high locally due to unrealistic passive fills",
    "queue_position_ignored": "Strategy depended on fills that require queue priority",
    "parameter_overfit": "Sweep-optimized params exploited backtester artifacts",
    "inventory_trap": "Strategy hit position limits more on platform than locally",
    "architecture_mismatch": "Strategy family has consistently poor transfer",
    "scenario_gap_predicted": "Large scenario gap correctly predicted poor transfer",
    "robust_undervalued": "Low-PnL but robust strategy performed better than expected",
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class RankingMistake:
    """One instance of local vs platform ranking disagreement."""

    strategy_name: str
    mistake_type: str  # "false_positive" | "false_negative"
    local_rank: int
    platform_rank: int
    rank_shift: int
    backtest_pnl: float
    platform_pnl: float
    likely_causes: list[str] = field(default_factory=list)


@dataclass
class AuditReport:
    """Complete ranking quality audit."""

    n_strategies: int
    raw_pnl_rank_correlation: float
    transfer_score_rank_correlation: float
    false_positives: list[RankingMistake]
    false_negatives: list[RankingMistake]
    common_fp_causes: dict[str, int]  # cause → count
    common_fn_causes: dict[str, int]
    family_transfer_rates: dict[str, float]  # family → avg platform/backtest ratio


# ---------------------------------------------------------------------------
# Audit logic
# ---------------------------------------------------------------------------


def _rank_list(values: list[float]) -> list[int]:
    """Assign ranks to a list of values (1 = highest)."""
    indexed = sorted(enumerate(values), key=lambda x: x[1], reverse=True)
    ranks = [0] * len(values)
    for rank, (idx, _) in enumerate(indexed, 1):
        ranks[idx] = rank
    return ranks


def _classify_fp_causes(point: CalibrationPoint) -> list[str]:
    """Guess why a strategy was a false positive (high local, low platform)."""
    causes: list[str] = []

    if point.passive_fill_share is not None and point.passive_fill_share > 0.8:
        causes.append("passive_fill_overestimate")

    if point.scenario_pnls:
        baseline = point.scenario_pnls.get("baseline", 0)
        queue = point.scenario_pnls.get("queue_hostile", baseline)
        if baseline > 0 and queue / baseline < 0.5:
            causes.append("queue_position_ignored")

    if "sweep" in point.strategy_name.lower():
        causes.append("parameter_overfit")

    if not causes:
        causes.append("unknown")

    return causes


def _classify_fn_causes(point: CalibrationPoint) -> list[str]:
    """Guess why a strategy was a false negative (low local, high platform)."""
    causes: list[str] = []

    if point.passive_fill_share is not None and point.passive_fill_share < 0.5:
        causes.append("robust_undervalued")

    if point.scenario_pnls:
        baseline = point.scenario_pnls.get("baseline", 0)
        queue = point.scenario_pnls.get("queue_hostile", baseline)
        if baseline > 0 and queue / baseline > 0.8:
            causes.append("scenario_gap_predicted")

    if not causes:
        causes.append("unknown")

    return causes


def audit_ranking_quality(
    calibration_data: list[CalibrationPoint],
    rank_shift_threshold: int = 3,
) -> AuditReport:
    """Analyze ranking mistakes from platform evidence.

    Compares local backtest PnL ranking and transfer score ranking
    to actual platform PnL ranking. Identifies strategies that were
    significantly over- or under-ranked locally.

    Args:
        calibration_data: Known platform results with local metrics.
        rank_shift_threshold: Minimum rank shift to count as a mistake.
    """
    valid = [p for p in calibration_data if p.backtest_pnl > 0 and p.platform_pnl > 0]
    if len(valid) < 3:
        return AuditReport(
            n_strategies=len(valid),
            raw_pnl_rank_correlation=0.0,
            transfer_score_rank_correlation=0.0,
            false_positives=[],
            false_negatives=[],
            common_fp_causes={},
            common_fn_causes={},
            family_transfer_rates={},
        )

    # Compute rankings
    backtest_pnls = [p.backtest_pnl for p in valid]
    platform_pnls = [p.platform_pnl for p in valid]
    transfer_scores = [p.transfer_score or 0.0 for p in valid]

    bt_ranks = _rank_list(backtest_pnls)
    pt_ranks = _rank_list(platform_pnls)

    raw_corr = spearman_rank_correlation(backtest_pnls, platform_pnls)
    ts_corr = spearman_rank_correlation(transfer_scores, platform_pnls)

    # Find false positives (high local rank, low platform rank)
    false_positives: list[RankingMistake] = []
    false_negatives: list[RankingMistake] = []

    for i, point in enumerate(valid):
        shift = bt_ranks[i] - pt_ranks[i]  # positive = overranked locally

        if shift <= -rank_shift_threshold:
            # False positive: ranked much higher locally than on platform
            false_positives.append(
                RankingMistake(
                    strategy_name=point.strategy_name,
                    mistake_type="false_positive",
                    local_rank=bt_ranks[i],
                    platform_rank=pt_ranks[i],
                    rank_shift=shift,
                    backtest_pnl=point.backtest_pnl,
                    platform_pnl=point.platform_pnl,
                    likely_causes=_classify_fp_causes(point),
                )
            )
        elif shift >= rank_shift_threshold:
            # False negative: ranked much lower locally than on platform
            false_negatives.append(
                RankingMistake(
                    strategy_name=point.strategy_name,
                    mistake_type="false_negative",
                    local_rank=bt_ranks[i],
                    platform_rank=pt_ranks[i],
                    rank_shift=shift,
                    backtest_pnl=point.backtest_pnl,
                    platform_pnl=point.platform_pnl,
                    likely_causes=_classify_fn_causes(point),
                )
            )

    # Aggregate causes
    fp_causes: dict[str, int] = {}
    for m in false_positives:
        for cause in m.likely_causes:
            fp_causes[cause] = fp_causes.get(cause, 0) + 1

    fn_causes: dict[str, int] = {}
    for m in false_negatives:
        for cause in m.likely_causes:
            fn_causes[cause] = fn_causes.get(cause, 0) + 1

    # Family transfer rates
    family_ratios: dict[str, list[float]] = {}
    for p in valid:
        if p.architecture_family:
            ratio = p.platform_pnl / p.backtest_pnl if p.backtest_pnl > 0 else 0
            family_ratios.setdefault(p.architecture_family, []).append(ratio)
    family_rates = {fam: sum(ratios) / len(ratios) for fam, ratios in family_ratios.items()}

    return AuditReport(
        n_strategies=len(valid),
        raw_pnl_rank_correlation=raw_corr,
        transfer_score_rank_correlation=ts_corr,
        false_positives=false_positives,
        false_negatives=false_negatives,
        common_fp_causes=fp_causes,
        common_fn_causes=fn_causes,
        family_transfer_rates=family_rates,
    )


def generate_audit_report(report: AuditReport) -> str:
    """Generate a human-readable audit report."""
    lines: list[str] = []
    lines.append("# Ranking Quality Audit")
    lines.append(f"Strategies analyzed: {report.n_strategies}")
    lines.append(f"Raw PnL rank correlation: {report.raw_pnl_rank_correlation:.3f}")
    lines.append(f"Transfer score rank correlation: {report.transfer_score_rank_correlation:.3f}")
    lines.append("")

    if report.false_positives:
        lines.append(f"## False Positives ({len(report.false_positives)} strategies)")
        for m in report.false_positives:
            lines.append(
                f"- {m.strategy_name}: local rank {m.local_rank} → platform rank {m.platform_rank} "
                f"(shift {m.rank_shift}), causes: {m.likely_causes}"
            )
        lines.append(f"Common causes: {report.common_fp_causes}")

    if report.false_negatives:
        lines.append(f"\n## False Negatives ({len(report.false_negatives)} strategies)")
        for m in report.false_negatives:
            lines.append(
                f"- {m.strategy_name}: local rank {m.local_rank} → platform rank {m.platform_rank} "
                f"(shift {m.rank_shift}), causes: {m.likely_causes}"
            )
        lines.append(f"Common causes: {report.common_fn_causes}")

    if report.family_transfer_rates:
        lines.append("\n## Family Transfer Rates (platform_pnl / backtest_pnl)")
        for fam, rate in sorted(
            report.family_transfer_rates.items(), key=lambda x: x[1], reverse=True
        ):
            lines.append(f"- {fam}: {rate:.2%}")

    return "\n".join(lines)
