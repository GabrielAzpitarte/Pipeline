"""Pure Python tools for writing, testing, and running strategies."""

from __future__ import annotations

import importlib
import re
import subprocess
from pathlib import Path
from typing import Any

from data.parse_logs import BacktestData
from experiments.runner import run_experiment
from trader.logging_utils import get_logger

_log = get_logger("agents.tools")

# Built-in strategies that must never be overwritten.
_PROTECTED_NAMES = frozenset({"noop", "market_maker", "fair_value", "inventory_mm"})


def _validate_name(name: str) -> None:
    """Ensure strategy name is safe."""
    if not re.match(r"^[a-z][a-z0-9_]*$", name):
        raise ValueError(f"Invalid strategy name: {name!r} (must be lowercase snake_case)")
    if name in _PROTECTED_NAMES:
        raise ValueError(f"Cannot overwrite built-in strategy: {name!r}")


def write_strategy_file(name: str, code: str, strategies_dir: Path) -> Path:
    """Write a strategy .py file. Returns the written path.

    Safety: validates name and checks path does not escape strategies_dir.
    """
    _validate_name(name)
    target = (strategies_dir / f"{name}.py").resolve()
    if not str(target).startswith(str(strategies_dir.resolve())):
        raise ValueError(f"Path escape detected: {target}")
    target.write_text(code)
    _log.info("Wrote strategy file: %s", target)
    return target


def register_strategy_import(name: str, init_path: Path) -> None:
    """Append import line to strategies/__init__.py if not already present."""
    _validate_name(name)
    import_line = f"import trader.strategies.{name} as _{name}  # noqa: F401, E402"
    content = init_path.read_text()
    if import_line in content:
        return
    content = content.rstrip() + f"\n{import_line}\n"
    init_path.write_text(content)
    _log.info("Registered import for %s", name)


def unregister_strategy_import(name: str, init_path: Path) -> None:
    """Remove the import line for a strategy from __init__.py."""
    import_line = f"import trader.strategies.{name} as _{name}"
    content = init_path.read_text()
    lines = [line for line in content.splitlines() if import_line not in line]
    init_path.write_text("\n".join(lines) + "\n")


def load_strategy_module(name: str) -> None:
    """Import (or reload) a strategy module so it registers in STRATEGIES."""
    module_name = f"trader.strategies.{name}"
    try:
        mod = importlib.import_module(module_name)
        importlib.reload(mod)
    except ImportError:
        _log.warning("Could not import %s", module_name)


def run_tests(project_root: Path) -> tuple[bool, str]:
    """Run quick strategy tests. Returns (passed, output)."""
    result = subprocess.run(
        ["python", "-m", "pytest", "tests/unit/test_strategies.py", "-x", "--tb=short", "-q"],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        timeout=60,
    )
    passed = result.returncode == 0
    output = result.stdout + result.stderr
    return passed, output


def run_strategy_experiment(
    strategy_name: str,
    data: BacktestData,
    params: dict[str, Any] | None = None,
    fast: bool = True,
    artifacts_dir: Path | None = None,
    data_split: float = 1.0,
) -> dict[str, float]:
    """Run an experiment and return the metrics dict."""
    from sim.engine import SimConfig

    config = SimConfig(
        strategy_name=strategy_name,
        strategy_params=params or {},
        data_split=data_split,
    )
    result = run_experiment(
        name=f"agent_{strategy_name}",
        strategy=strategy_name,
        data=data,
        config=config,
        strategy_params=params,
        save=True,
        artifacts_dir=artifacts_dir,
        fast=fast,
    )
    return result.metrics


def cleanup_strategy(name: str, strategies_dir: Path, init_path: Path) -> None:
    """Remove a generated strategy: file, import line, and registry entry."""
    from trader.strategies import STRATEGIES

    STRATEGIES.pop(name, None)
    filepath = strategies_dir / f"{name}.py"
    if filepath.exists():
        filepath.unlink()
        _log.info("Deleted strategy file: %s", filepath)
    unregister_strategy_import(name, init_path)
