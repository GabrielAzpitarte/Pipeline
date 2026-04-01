"""Conversation and experiment memory for the agent."""

from __future__ import annotations

from typing import Any


class AgentMemory:
    """Store and retrieve context across agent interactions."""

    def __init__(self) -> None:
        self._store: list[dict[str, Any]] = []

    def add(self, entry: dict[str, Any]) -> None:
        """Add an entry to memory."""
        self._store.append(entry)

    def search(self, query: str) -> list[dict[str, Any]]:
        """Simple keyword search over memory entries."""
        return [e for e in self._store if query.lower() in str(e).lower()]

    def clear(self) -> None:
        """Reset memory."""
        self._store.clear()
