"""Read/write helpers for processed data and run storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from experiments.models import RunData, dict_to_run_data, run_data_to_dict

_DEFAULT_ARTIFACTS_DIR = Path("artifacts")


def save_json(data: Any, path: Path) -> None:
    """Write data as JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_json(path: Path) -> Any:
    """Read JSON file."""
    with open(path) as f:
        return json.load(f)


def save_run(run_data: RunData, base_dir: Path | None = None) -> Path:
    """Persist a RunData to disk.

    Creates ``{base_dir}/runs/{run_id}/result.json``.
    Returns the run directory path.
    """
    base = base_dir or _DEFAULT_ARTIFACTS_DIR
    run_dir = base / "runs" / run_data.metadata.run_id
    save_json(run_data_to_dict(run_data), run_dir / "result.json")
    return run_dir


def load_run(run_id: str, base_dir: Path | None = None) -> RunData:
    """Load a RunData from disk by run_id."""
    base = base_dir or _DEFAULT_ARTIFACTS_DIR
    path = base / "runs" / run_id / "result.json"
    return dict_to_run_data(load_json(path))
