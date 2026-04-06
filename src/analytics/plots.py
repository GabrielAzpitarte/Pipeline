"""Plotting utilities for strategy analysis."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from experiments.models import RunData, StoredFill


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
    plt.close(fig)
    return fig


def plot_positions(
    timestamps: list[int],
    position_series: list[dict[str, int]],
    title: str = "Positions Over Time",
    save_path: Path | None = None,
) -> Any:
    """Plot position for each product over time. One line per product."""
    import matplotlib.pyplot as plt

    products: set[str] = set()
    for pos in position_series:
        products.update(pos.keys())

    fig, ax = plt.subplots(figsize=(12, 5))
    for product in sorted(products):
        values = [pos.get(product, 0) for pos in position_series]
        ax.plot(timestamps, values, label=product)
    ax.set_title(title)
    ax.set_xlabel("Timestamp")
    ax.set_ylabel("Position")
    ax.legend()
    ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.5)
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return fig


def plot_fill_scatter(
    fills: list[StoredFill],
    mid_price_series: list[dict[str, float]],
    timestamps: list[int],
    title: str = "Fills",
    save_path: Path | None = None,
) -> Any:
    """Scatter plot of fills overlaid on mid-price. One subplot per product."""
    import matplotlib.pyplot as plt

    products: set[str] = set()
    for f in fills:
        products.add(f.symbol)
    for mp in mid_price_series:
        products.update(mp.keys())

    sorted_products = sorted(products)
    if not sorted_products:
        fig, _ = plt.subplots()
        plt.close(fig)
        return fig

    fig, axes = plt.subplots(
        len(sorted_products), 1, figsize=(12, 4 * len(sorted_products)), squeeze=False
    )

    for idx, product in enumerate(sorted_products):
        ax = axes[idx, 0]
        # Mid-price line
        mids = [mp.get(product, float("nan")) for mp in mid_price_series]
        ax.plot(timestamps, mids, color="gray", alpha=0.6, label="Mid")

        # Fills
        buys = [f for f in fills if f.symbol == product and f.quantity > 0]
        sells = [f for f in fills if f.symbol == product and f.quantity < 0]
        if buys:
            ax.scatter(
                [f.timestamp for f in buys],
                [f.price for f in buys],
                color="green",
                marker="^",
                s=40,
                label="Buy",
                zorder=5,
            )
        if sells:
            ax.scatter(
                [f.timestamp for f in sells],
                [f.price for f in sells],
                color="red",
                marker="v",
                s=40,
                label="Sell",
                zorder=5,
            )
        ax.set_title(f"{product}")
        ax.set_xlabel("Timestamp")
        ax.set_ylabel("Price")
        ax.legend(fontsize=8)

    fig.suptitle(title)
    fig.tight_layout()
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return fig


def plot_drawdown(
    pnl_series: list[float],
    title: str = "Drawdown",
    save_path: Path | None = None,
) -> Any:
    """Plot the drawdown curve (peak - current) over time."""
    import matplotlib.pyplot as plt

    if not pnl_series:
        fig, _ = plt.subplots()
        plt.close(fig)
        return fig

    peak = pnl_series[0]
    drawdowns = []
    for val in pnl_series:
        peak = max(peak, val)
        drawdowns.append(val - peak)

    fig, ax = plt.subplots(figsize=(12, 4))
    ax.fill_between(range(len(drawdowns)), drawdowns, color="red", alpha=0.3)
    ax.plot(drawdowns, color="red", linewidth=1)
    ax.set_title(title)
    ax.set_xlabel("Tick")
    ax.set_ylabel("Drawdown")
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return fig


def plot_dashboard(
    run_data: RunData,
    save_path: Path | None = None,
) -> Any:
    """Multi-panel figure: equity curve, positions, fills, drawdown."""
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

    # Equity curve (top-left)
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(run_data.timestamps, run_data.pnl_series)
    ax1.set_title("PnL Over Time")
    ax1.set_xlabel("Timestamp")
    ax1.set_ylabel("PnL")

    # Positions (top-right)
    ax2 = fig.add_subplot(gs[0, 1])
    products: set[str] = set()
    for pos in run_data.position_series:
        products.update(pos.keys())
    for product in sorted(products):
        values = [pos.get(product, 0) for pos in run_data.position_series]
        ax2.plot(run_data.timestamps, values, label=product)
    ax2.set_title("Positions Over Time")
    ax2.set_xlabel("Timestamp")
    ax2.set_ylabel("Position")
    ax2.legend(fontsize=7)

    # Fills (bottom-left)
    ax3 = fig.add_subplot(gs[1, 0])
    buys = [f for f in run_data.fills if f.quantity > 0]
    sells = [f for f in run_data.fills if f.quantity < 0]
    if buys:
        ax3.scatter(
            [f.timestamp for f in buys],
            [f.price for f in buys],
            color="green",
            marker="^",
            s=20,
            label="Buy",
        )
    if sells:
        ax3.scatter(
            [f.timestamp for f in sells],
            [f.price for f in sells],
            color="red",
            marker="v",
            s=20,
            label="Sell",
        )
    ax3.set_title("Fills")
    ax3.set_xlabel("Timestamp")
    ax3.set_ylabel("Price")
    ax3.legend(fontsize=7)

    # Drawdown (bottom-right)
    ax4 = fig.add_subplot(gs[1, 1])
    if run_data.pnl_series:
        peak = run_data.pnl_series[0]
        drawdowns = []
        for val in run_data.pnl_series:
            peak = max(peak, val)
            drawdowns.append(val - peak)
        ax4.fill_between(range(len(drawdowns)), drawdowns, color="red", alpha=0.3)
        ax4.plot(drawdowns, color="red", linewidth=1)
    ax4.set_title("Drawdown")
    ax4.set_xlabel("Tick")
    ax4.set_ylabel("Drawdown")

    fig.suptitle(f"Run: {run_data.metadata.run_id}", fontsize=11)
    if save_path:
        save_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return fig
