"""Track and catalogue past experiment runs on disk."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from trader.utils import deterministic_hash

_DEFAULT_ARTIFACTS_DIR = Path("artifacts")


@dataclass
class RegistryEntry:
    """One row in the run registry index."""

    run_id: str
    name: str
    strategy: str
    timestamp: str  # ISO-8601
    final_pnl: float
    tags: list[str]
    config_hash: str


def _registry_path(base_dir: Path) -> Path:
    return base_dir / "runs" / "registry.json"


def _load_registry(base_dir: Path) -> list[dict[str, Any]]:
    """Load the registry JSON file, returning [] if it doesn't exist."""
    path = _registry_path(base_dir)
    if not path.exists():
        return []
    with open(path) as f:
        data: list[dict[str, Any]] = json.load(f)
        return data


def _save_registry(entries: list[dict[str, Any]], base_dir: Path) -> None:
    """Write the registry JSON file."""
    path = _registry_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(entries, f, indent=2, default=str)


def register_run(
    run_data: Any,
    name: str = "",
    base_dir: Path | None = None,
) -> None:
    """Append a run to the on-disk registry index.

    Args:
        run_data: A RunData object (imported at runtime to avoid circular imports).
        name: Human-readable experiment name.
        base_dir: Override base directory.
    """
    base = base_dir or _DEFAULT_ARTIFACTS_DIR
    entries = _load_registry(base)

    entry = RegistryEntry(
        run_id=run_data.metadata.run_id,
        name=name or run_data.metadata.run_id,
        strategy=run_data.metadata.strategy_name,
        timestamp=run_data.metadata.timestamp,
        final_pnl=run_data.final_pnl,
        tags=run_data.metadata.tags,
        config_hash=deterministic_hash(run_data.metadata.config),
    )
    entries.append(asdict(entry))
    _save_registry(entries, base)


def get_all_runs(base_dir: Path | None = None) -> list[RegistryEntry]:
    """Return all registered runs from the on-disk registry."""
    base = base_dir or _DEFAULT_ARTIFACTS_DIR
    raw = _load_registry(base)
    return [
        RegistryEntry(
            run_id=e["run_id"],
            name=e["name"],
            strategy=e["strategy"],
            timestamp=e["timestamp"],
            final_pnl=e["final_pnl"],
            tags=e.get("tags", []),
            config_hash=e.get("config_hash", ""),
        )
        for e in raw
    ]


def find_runs(
    strategy: str | None = None,
    tag: str | None = None,
    base_dir: Path | None = None,
) -> list[RegistryEntry]:
    """Filter runs by strategy name or tag."""
    runs = get_all_runs(base_dir)
    if strategy is not None:
        runs = [r for r in runs if r.strategy == strategy]
    if tag is not None:
        runs = [r for r in runs if tag in r.tags]
    return runs
