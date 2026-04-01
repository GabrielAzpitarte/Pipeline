"""Plotting utilities for strategy analysis."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def plot_equity_curve(
    equity: list[float],
    title: str = "Equity Curve",
    save_path: Path | None = None,
) -> Any:
    """Plot an equity curve. Returns the figure."""
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(equity)
    ax.set_title(title)
    ax.set_xlabel("Tick")
    ax.set_ylabel("Equity")
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    return fig
