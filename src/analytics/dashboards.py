"""Dashboard generation for experiment review."""

from __future__ import annotations

import base64
import io
from pathlib import Path
from typing import TYPE_CHECKING, Any

from analytics.metrics import compute_all_metrics
from analytics.plots import (
    plot_dashboard,
    plot_drawdown,
    plot_equity_curve,
    plot_fill_scatter,
    plot_positions,
)
from data.storage import save_json

if TYPE_CHECKING:
    from experiments.models import RunData


def generate_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a summary dict from a list of experiment results."""
    return {
        "num_runs": len(results),
        "best_pnl": max((r.get("total_pnl", 0.0) for r in results), default=0.0),
        "worst_pnl": min((r.get("total_pnl", 0.0) for r in results), default=0.0),
    }


def generate_run_report(
    run_data: RunData,
    output_dir: Path | None = None,
) -> Path:
    """Generate a complete report for a single run.

    Creates in output_dir:
        summary.json, equity_curve.png, positions.png,
        fills.png, drawdown.png, dashboard.png
    """
    out = output_dir or Path("artifacts") / "runs" / run_data.metadata.run_id / "report"
    out.mkdir(parents=True, exist_ok=True)

    metrics = compute_all_metrics(run_data)
    save_json(metrics, out / "summary.json")

    plot_equity_curve(run_data.pnl_series, save_path=out / "equity_curve.png")
    plot_positions(
        run_data.timestamps,
        run_data.position_series,
        save_path=out / "positions.png",
    )
    plot_fill_scatter(
        run_data.fills,
        run_data.mid_price_series,
        run_data.timestamps,
        save_path=out / "fills.png",
    )
    plot_drawdown(run_data.pnl_series, save_path=out / "drawdown.png")
    plot_dashboard(run_data, save_path=out / "dashboard.png")

    return out


def _fig_to_base64(fig: Any) -> str:
    """Render a matplotlib figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")


_HTML_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Run Report: {run_id}</title>
<style>
body {{ font-family: sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }}
table {{ border-collapse: collapse; margin: 20px 0; }}
th, td {{ border: 1px solid #ccc; padding: 6px 12px; text-align: right; }}
th {{ background: #f5f5f5; text-align: left; }}
img {{ max-width: 100%; margin: 10px 0; }}
h1, h2 {{ color: #333; }}
</style>
</head>
<body>
<h1>Run Report: {run_id}</h1>
<p>Strategy: <b>{strategy}</b> | Date: {timestamp}</p>
<h2>Metrics</h2>
<table>
{metrics_rows}
</table>
<h2>Dashboard</h2>
<img src="data:image/png;base64,{dashboard_b64}">
<h2>Equity Curve</h2>
<img src="data:image/png;base64,{equity_b64}">
<h2>Positions</h2>
<img src="data:image/png;base64,{positions_b64}">
<h2>Drawdown</h2>
<img src="data:image/png;base64,{drawdown_b64}">
</body>
</html>
"""


def generate_html_report(
    run_data: RunData,
    output_dir: Path | None = None,
) -> Path:
    """Generate a self-contained HTML report for a single run.

    Embeds PNG plots as base64 data URIs.
    Returns the path to the HTML file.
    """
    out = output_dir or Path("artifacts") / "runs" / run_data.metadata.run_id / "report"
    out.mkdir(parents=True, exist_ok=True)

    metrics = compute_all_metrics(run_data)

    # Render plots to base64
    fig_dashboard = plot_dashboard(run_data)
    fig_equity = plot_equity_curve(run_data.pnl_series)
    fig_positions = plot_positions(run_data.timestamps, run_data.position_series)
    fig_drawdown = plot_drawdown(run_data.pnl_series)

    metrics_rows = "\n".join(f"<tr><th>{k}</th><td>{v:.4f}</td></tr>" for k, v in metrics.items())

    html = _HTML_TEMPLATE.format(
        run_id=run_data.metadata.run_id,
        strategy=run_data.metadata.strategy_name,
        timestamp=run_data.metadata.timestamp,
        metrics_rows=metrics_rows,
        dashboard_b64=_fig_to_base64(fig_dashboard),
        equity_b64=_fig_to_base64(fig_equity),
        positions_b64=_fig_to_base64(fig_positions),
        drawdown_b64=_fig_to_base64(fig_drawdown),
    )

    html_path = out / "report.html"
    html_path.write_text(html)
    return html_path


def generate_comparison_report(
    run_data_a: RunData,
    run_data_b: RunData,
    output_dir: Path | None = None,
) -> Path:
    """Generate a side-by-side comparison report for two runs.

    Returns the path to the comparison HTML file.
    """
    import matplotlib.pyplot as plt

    out = output_dir or Path("artifacts") / "comparisons"
    out.mkdir(parents=True, exist_ok=True)

    metrics_a = compute_all_metrics(run_data_a)
    metrics_b = compute_all_metrics(run_data_b)

    # Comparison summary
    deltas = {k: metrics_b.get(k, 0.0) - metrics_a.get(k, 0.0) for k in metrics_a}
    save_json(
        {
            "run_a": {"run_id": run_data_a.metadata.run_id, "metrics": metrics_a},
            "run_b": {"run_id": run_data_b.metadata.run_id, "metrics": metrics_b},
            "deltas": deltas,
        },
        out / "comparison_summary.json",
    )

    # Overlaid equity curves
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(
        run_data_a.timestamps,
        run_data_a.pnl_series,
        label=run_data_a.metadata.run_id[:20],
    )
    ax.plot(
        run_data_b.timestamps,
        run_data_b.pnl_series,
        label=run_data_b.metadata.run_id[:20],
    )
    ax.set_title("PnL Comparison")
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("PnL")
    ax.legend()
    fig.savefig(out / "comparison_equity.png", dpi=150, bbox_inches="tight")

    # Build comparison metrics table
    all_keys = sorted(set(list(metrics_a.keys()) + list(metrics_b.keys())))
    rows = []
    for k in all_keys:
        va = metrics_a.get(k, 0.0)
        vb = metrics_b.get(k, 0.0)
        delta = vb - va
        rows.append(f"<tr><th>{k}</th><td>{va:.4f}</td><td>{vb:.4f}</td><td>{delta:+.4f}</td></tr>")

    html = f"""\
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Comparison</title>
<style>
body {{ font-family: sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }}
table {{ border-collapse: collapse; margin: 20px 0; }}
th, td {{ border: 1px solid #ccc; padding: 6px 12px; text-align: right; }}
th {{ background: #f5f5f5; text-align: left; }}
img {{ max-width: 100%; }}
</style>
</head>
<body>
<h1>Run Comparison</h1>
<p>A: {run_data_a.metadata.run_id} | B: {run_data_b.metadata.run_id}</p>
<table>
<tr><th>Metric</th><th>Run A</th><th>Run B</th><th>Delta</th></tr>
{"".join(rows)}
</table>
<h2>Equity Curves</h2>
<img src="data:image/png;base64,{_fig_to_base64(fig)}">
</body>
</html>
"""
    plt.close(fig)
    html_path = out / "comparison.html"
    html_path.write_text(html)
    return html_path
