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

    def top_strategies(self, n: int = 10, sort_by: str = "transfer_score") -> list[dict[str, Any]]:
        """Return top N strategy cards, excluding failures and deprecated.

        Args:
            n: Number of cards to return.
            sort_by: Field to sort by — ``"transfer_score"`` (default) or ``"pnl"``.
        """
        valid = [c for c in self._cards if c.get("status") != "failed" and not c.get("deprecated")]
        valid.sort(key=lambda c: c.get(sort_by, 0.0), reverse=True)
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
        """Return top N strategy cards targeting a specific product (by transfer score)."""
        valid = [
            c
            for c in self._cards
            if c.get("status") != "failed"
            and not c.get("deprecated")
            and product in c.get("products", [])
        ]
        valid.sort(key=lambda c: c.get("transfer_score", 0.0), reverse=True)
        return valid[:n]

    def _update_best_status(self) -> None:
        """Mark the best card using transfer_score (not raw PnL)."""
        best_score = float("-inf")
        best_idx = -1
        for i, card in enumerate(self._cards):
            if card.get("status") == "failed" or card.get("deprecated"):
                continue
            score = card.get("transfer_score", card.get("pnl", 0.0) / 10000)
            if score > best_score:
                best_score = score
                best_idx = i

        for card in self._cards:
            if card.get("status") == "best":
                card["status"] = "tested"
        if best_idx >= 0:
            self._cards[best_idx]["status"] = "best"

    # ---- Evidence-aware retrieval ------------------------------------------

    def platform_proven(self) -> list[dict[str, Any]]:
        """Return only platform-tested, non-deprecated strategies."""
        return [c for c in self._cards if c.get("platform_tested") and not c.get("deprecated")]

    def by_verdict(self, verdict: str) -> list[dict[str, Any]]:
        """Return strategies with a specific verdict."""
        return [c for c in self._cards if c.get("verdict") == verdict]

    def by_family(self, family: str) -> list[dict[str, Any]]:
        """Return strategies in a specific architecture family."""
        return [c for c in self._cards if c.get("architecture_family") == family]

    def family_distribution(self) -> dict[str, int]:
        """Count strategies per family — detect if stuck in one family."""
        dist: dict[str, int] = {}
        for card in self._cards:
            fam = card.get("architecture_family", "unknown")
            dist[fam] = dist.get(fam, 0) + 1
        return dist

    def recent_cards(self, n_rounds: int = 5) -> list[dict[str, Any]]:
        """Return strategies from the last N rounds."""
        if not self._cards:
            return []
        max_round = max(c.get("round", 0) for c in self._cards)
        cutoff = max_round - n_rounds
        return [c for c in self._cards if c.get("round", 0) >= cutoff]

    def deprecated_cards(self) -> list[dict[str, Any]]:
        """Return deprecated strategies (searchable but not authoritative)."""
        return [c for c in self._cards if c.get("deprecated")]

    def evidence_pack(self) -> dict[str, list[dict[str, Any]]]:
        """Return a balanced evidence pack for ideation prompts.

        Provides one example from each category so strategists see
        diversity, not just winners.
        """
        pack: dict[str, list[dict[str, Any]]] = {
            "robust_winners": [],
            "platform_proven": [],
            "fragile_examples": [],
            "diverse_architectures": [],
        }
        # Robust winners (by transfer score)
        robust = sorted(
            [c for c in self._cards if c.get("verdict") == "robust" and not c.get("deprecated")],
            key=lambda c: c.get("transfer_score", 0),
            reverse=True,
        )
        pack["robust_winners"] = robust[:2]

        # Platform proven (exclude deprecated)
        proven = [c for c in self._cards if c.get("platform_tested") and not c.get("deprecated")]
        pack["platform_proven"] = proven[:2]

        # Fragile examples (for learning what fails)
        fragile = [
            c
            for c in self._cards
            if c.get("verdict", "").endswith("fragile") and not c.get("deprecated")
        ]
        pack["fragile_examples"] = fragile[:2]

        # Diverse: one from each family
        seen_families: set[str] = set()
        for card in sorted(self._cards, key=lambda c: c.get("transfer_score", 0), reverse=True):
            fam = card.get("architecture_family", "unknown")
            if fam not in seen_families and not card.get("deprecated"):
                pack["diverse_architectures"].append(card)
                seen_families.add(fam)
            if len(pack["diverse_architectures"]) >= 4:
                break

        # Dead-end branches (don't repeat these)
        pack["dead_end_branches"] = self.detect_dead_ends()[:3]

        # Family dominance warning
        active_dist = self.family_distribution()
        total_active = sum(active_dist.values())
        if total_active > 0:
            max_fam = max(active_dist, key=active_dist.get)  # type: ignore[arg-type]
            max_count = active_dist[max_fam]
            if max_count / total_active > 0.7:
                pack["family_dominance_warning"] = (
                    f"{max_fam} dominates with {max_count}/{total_active} "
                    f"({max_count / total_active:.0%})"
                )

        return pack

    def age_cards(self, current_round: int, max_age: int = 10) -> None:
        """Mark old untested cards as deprecated."""
        for card in self._cards:
            age = current_round - card.get("round", 0)
            if (
                age > max_age
                and not card.get("platform_tested")
                and card.get("status") != "best"
                and not card.get("deprecated")
            ):
                card["deprecated"] = True
                card["confidence"] = "stale"
        self._save_cards()

    # ---- Audit -----------------------------------------------------------

    def audit(self) -> dict[str, Any]:
        """Report memory health before a run."""
        max_round = max((c.get("round", 0) for c in self._cards), default=0)
        stale = [
            c
            for c in self._cards
            if not c.get("platform_tested")
            and not c.get("deprecated")
            and c.get("round", 0) < max_round - 10
        ]
        return {
            "total_cards": len(self._cards),
            "platform_tested": len(self.platform_proven()),
            "deprecated": len(self.deprecated_cards()),
            "stale_untested": len(stale),
            "family_coverage": self.family_distribution(),
            "fragile_examples": len(
                [c for c in self._cards if c.get("verdict", "").endswith("fragile")]
            ),
            "robust_examples": len([c for c in self._cards if c.get("verdict") == "robust"]),
        }

    # ---- Genealogy -------------------------------------------------------

    def get_lineage(self, name: str) -> list[dict[str, Any]]:
        """Trace the ancestry of a strategy back to its root."""
        lineage: list[dict[str, Any]] = []
        current = name
        seen: set[str] = set()
        while current and current not in seen:
            seen.add(current)
            card = next((c for c in self._cards if c.get("name") == current), None)
            if card is None:
                break
            lineage.append(card)
            current = card.get("parent_strategy")
        return lineage

    def get_descendants(self, name: str) -> list[dict[str, Any]]:
        """Find all strategies derived from a given parent."""
        return [c for c in self._cards if c.get("parent_strategy") == name]

    def detect_dead_ends(self) -> list[str]:
        """Find parent strategies whose descendants all failed or are fragile.

        A dead end is a strategy that has 2+ descendants, and ALL descendants
        have verdict in (reject, queue_fragile, passive_fragile, simulator_artifact).
        """
        parents: dict[str, list[dict[str, Any]]] = {}
        for card in self._cards:
            parent = card.get("parent_strategy")
            if parent:
                parents.setdefault(parent, []).append(card)

        dead_ends: list[str] = []
        bad_verdicts = {"reject", "queue_fragile", "passive_fragile", "simulator_artifact"}
        for parent_name, children in parents.items():
            if len(children) >= 2 and all(
                c.get("verdict", "") in bad_verdicts or c.get("status") == "failed"
                for c in children
            ):
                dead_ends.append(parent_name)

        return dead_ends

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
