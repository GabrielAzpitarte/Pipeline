"""Conversation and experiment memory for the agent — with strategy cards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AgentMemory:
    """Store and retrieve context across agent interactions.

    Two stores:
    - ``_store``: round-level entries (backward compatible)
    - ``_cards``: strategy cards with structured performance data
    """

    def __init__(
        self,
        persist_path: Path | None = None,
        knowledge_dir: Path | None = None,
    ) -> None:
        self._store: list[dict[str, Any]] = []
        self._cards: list[dict[str, Any]] = []
        self._persist_path = persist_path
        self._knowledge_dir = knowledge_dir or Path("src/agents/knowledge")
        if persist_path is not None:
            self.load()
            self._load_cards()
            self.migrate_legacy_rounds()

    # ---- Round-level memory (backward compatible) -------------------------

    def add(self, entry: dict[str, Any]) -> None:
        """Add a round-level entry to memory and persist."""
        self._store.append(entry)
        if self._persist_path is not None:
            self.save()

    def search(self, query: str) -> list[dict[str, Any]]:
        """Simple keyword search over memory entries."""
        return [e for e in self._store if query.lower() in str(e).lower()]

    def recent(self, n: int = 5) -> list[dict[str, Any]]:
        """Return the last N round-level entries."""
        return self._store[-n:]

    def best_result(self, metric: str = "total_pnl") -> dict[str, Any] | None:
        """Return the entry with the highest value for the given metric."""
        best: dict[str, Any] | None = None
        best_val = float("-inf")
        for entry in self._store:
            metrics = entry.get("metrics")
            if isinstance(metrics, dict) and metric in metrics:
                val = float(metrics[metric])
                if val > best_val:
                    best_val = val
                    best = entry
        return best

    def save(self) -> None:
        """Write round-level memory to disk."""
        if self._persist_path is None:
            return
        self._persist_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._persist_path, "w") as f:
            json.dump(self._store, f, indent=2, default=str)

    def load(self) -> None:
        """Load round-level memory from disk."""
        if self._persist_path is None or not self._persist_path.exists():
            return
        with open(self._persist_path) as f:
            data: list[dict[str, Any]] = json.load(f)
            self._store = data

    def clear(self) -> None:
        """Reset all memory and delete persist files."""
        self._store.clear()
        self._cards.clear()
        if self._persist_path is not None:
            if self._persist_path.exists():
                self._persist_path.unlink()
            cards_path = self._cards_path
            if cards_path and cards_path.exists():
                cards_path.unlink()

    # ---- Strategy cards ---------------------------------------------------

    @property
    def _cards_path(self) -> Path | None:
        """Path to the strategy cards JSON file."""
        if self._persist_path is None:
            return None
        return self._persist_path.parent / "strategy_cards.json"

    def add_strategy_card(self, card: dict[str, Any]) -> None:
        """Add or update a strategy card. Auto-assigns status."""
        name = card.get("name", "")
        pnl = card.get("pnl", 0.0)
        error = card.get("error")

        # Auto-assign status
        if error or pnl < 0:
            card["status"] = "failed"
        else:
            card["status"] = "tested"

        # Upsert by name
        for i, existing in enumerate(self._cards):
            if existing.get("name") == name:
                self._cards[i] = card
                self._update_best_status()
                self._save_cards()
                return

        self._cards.append(card)
        self._update_best_status()
        self._save_cards()

    def top_strategies(self, n: int = 10) -> list[dict[str, Any]]:
        """Return top N strategy cards by PnL, excluding failures."""
        valid = [c for c in self._cards if c.get("status") != "failed"]
        valid.sort(key=lambda c: c.get("pnl", 0.0), reverse=True)
        return valid[:n]

    def failed_strategies(self, n: int = 5) -> list[dict[str, Any]]:
        """Return worst N failed strategy cards."""
        failed = [c for c in self._cards if c.get("status") == "failed"]
        failed.sort(key=lambda c: c.get("pnl", 0.0))
        return failed[:n]

    def best_strategy_card(self) -> dict[str, Any] | None:
        """Return the strategy card with status 'best', or None."""
        for card in self._cards:
            if card.get("status") == "best":
                return card
        return None

    def top_strategies_by_product(self, product: str, n: int = 3) -> list[dict[str, Any]]:
        """Return top N strategy cards targeting a specific product."""
        valid = [
            c
            for c in self._cards
            if c.get("status") != "failed" and product in c.get("products", [])
        ]
        valid.sort(key=lambda c: c.get("pnl", 0.0), reverse=True)
        return valid[:n]

    def _update_best_status(self) -> None:
        """Mark the highest-PnL card as 'best', reset others."""
        best_pnl = float("-inf")
        best_idx = -1
        for i, card in enumerate(self._cards):
            if card.get("status") == "failed":
                continue
            pnl = card.get("pnl", 0.0)
            if pnl > best_pnl:
                best_pnl = pnl
                best_idx = i

        for card in self._cards:
            if card.get("status") == "best":
                card["status"] = "tested"
        if best_idx >= 0:
            self._cards[best_idx]["status"] = "best"

    def _save_cards(self) -> None:
        """Write strategy cards to disk."""
        cards_path = self._cards_path
        if cards_path is None:
            return
        cards_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cards_path, "w") as f:
            json.dump(self._cards, f, indent=2, default=str)

    def _load_cards(self) -> None:
        """Load strategy cards from disk."""
        cards_path = self._cards_path
        if cards_path is None or not cards_path.exists():
            return
        with open(cards_path) as f:
            data: list[dict[str, Any]] = json.load(f)
            self._cards = data

    def migrate_legacy_rounds(self) -> None:
        """One-time migration: create strategy cards from old round entries."""
        if self._cards:
            return  # already has cards
        for entry in self._store:
            round_num = entry.get("round", 0)
            for c in entry.get("all_candidates", []):
                pnl = c.get("pnl") or 0.0
                self.add_strategy_card(
                    {
                        "name": c.get("name", ""),
                        "source_model": c.get("source_model", ""),
                        "description": c.get("description", ""),
                        "pnl": float(pnl),
                        "round": round_num,
                        "params": {},
                        "strengths": "",
                        "status": "",
                        "error": c.get("error"),
                    }
                )

    # ---- Knowledge files --------------------------------------------------

    def load_knowledge_file(self, name: str) -> str:
        """Read a knowledge markdown file (mechanics.md, product_briefs.md)."""
        path = self._knowledge_dir / name
        if path.exists():
            return path.read_text()
        return ""
