"""Track and catalogue past experiment runs."""

from __future__ import annotations

from typing import Any

_REGISTRY: list[dict[str, Any]] = []


def register_run(result: dict[str, Any]) -> None:
    """Add an experiment result to the registry."""
    _REGISTRY.append(result)


def get_all_runs() -> list[dict[str, Any]]:
    """Return all registered runs."""
    return list(_REGISTRY)
