"""Parameter sweep utilities."""

from __future__ import annotations

import itertools
from typing import Any


def grid_sweep(param_grid: dict[str, list[Any]]) -> list[dict[str, Any]]:
    """Generate all combinations from a parameter grid."""
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    return [dict(zip(keys, combo, strict=True)) for combo in itertools.product(*values)]
