"""Package a strategy for submission."""

from __future__ import annotations

from pathlib import Path


def package_strategy(strategy_file: Path, output_dir: Path) -> Path:
    """Copy and bundle a strategy file for submission."""
    output_dir.mkdir(parents=True, exist_ok=True)
    dest = output_dir / strategy_file.name
    dest.write_text(strategy_file.read_text())
    return dest
