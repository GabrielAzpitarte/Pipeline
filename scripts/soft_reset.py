"""Curated soft reset — reclassify memory cards for clean 10-round run.

Backs up current state, assigns architecture families, reclassifies cards
into active/counterexample/deprecated/archive buckets, validates retrieval.
"""

from __future__ import annotations

import json
import shutil
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, ".")


def main() -> None:
    """Run the curated soft reset."""
    from agents.memory import AgentMemory
    from agents.taxonomy import classify_strategy

    cards_path = Path("artifacts/strategy_cards.json")
    memory_path = Path("artifacts/agent_memory.json")

    # ================================================================
    # Phase 1A: Backup
    # ================================================================
    print("=== Phase 1A: Backup ===")
    backup_dir = Path("artifacts/pre_reset_backup")
    backup_dir.mkdir(parents=True, exist_ok=True)

    if cards_path.exists():
        shutil.copy2(cards_path, backup_dir / "strategy_cards_backup.json")
        print(f"  Backed up {cards_path} -> {backup_dir}")
    if memory_path.exists():
        shutil.copy2(memory_path, backup_dir / "agent_memory_backup.json")
        print(f"  Backed up {memory_path} -> {backup_dir}")

    # Load cards
    cards: list[dict] = json.loads(cards_path.read_text()) if cards_path.exists() else []
    print(f"  Total cards loaded: {len(cards)}")

    # ================================================================
    # Phase 1B: Auto-classify architecture families
    # ================================================================
    print("\n=== Phase 1B: Auto-classify families ===")
    classified = 0
    for card in cards:
        if card.get("architecture_family") in (None, "", "unknown"):
            code = card.get("code", "")
            desc = card.get("description", "")
            if code or desc:
                card["architecture_family"] = classify_strategy(code, desc)
                classified += 1
    print(f"  Classified {classified} cards with architecture families")

    # Family distribution
    families = Counter(
        c.get("architecture_family", "unknown") for c in cards if c.get("status") != "failed"
    )
    print(f"  Family distribution: {dict(families)}")

    # ================================================================
    # Phase 1C: Reclassify into 4 buckets
    # ================================================================
    print("\n=== Phase 1C: Reclassify ===")

    # Find best card per family (by transfer_score)
    best_per_family: dict[str, float] = {}
    for card in cards:
        fam = card.get("architecture_family", "unknown")
        ts = card.get("transfer_score", 0)
        if ts > best_per_family.get(fam, 0):
            best_per_family[fam] = ts

    active = 0
    counterexample = 0
    deprecated = 0
    archived = 0

    for card in cards:
        _name = card.get("name", "?")
        ts = card.get("transfer_score", 0)
        pnl = card.get("pnl", 0)
        status = card.get("status", "")
        verdict = card.get("verdict", "")
        platform_tested = card.get("platform_tested", False)
        platform_pnl = card.get("platform_pnl")
        has_code = bool(card.get("code"))
        fam = card.get("architecture_family", "unknown")
        notes = card.get("fragility_notes", [])

        # Already deprecated? Skip
        if card.get("deprecated"):
            deprecated += 1
            continue

        # Bucket 1: KEEP ACTIVE
        if platform_tested or platform_pnl is not None:
            card["confidence"] = "platform_proven"
            active += 1
            continue

        if ts > 0.5:
            card["confidence"] = "high"
            active += 1
            continue

        # Best in family gets to stay
        if ts > 0 and ts >= best_per_family.get(fam, 0) * 0.95:
            card["confidence"] = "family_exemplar"
            active += 1
            continue

        # Bucket 2: COUNTEREXAMPLE (informative failures)
        if verdict and ("fragile" in verdict or verdict == "simulator_artifact") and notes:
            card["confidence"] = "counterexample"
            counterexample += 1
            continue

        # Bucket 3: ARCHIVE (failed with no useful info)
        if status == "failed" and not has_code:
            card["deprecated"] = True
            card["deprecation_reason"] = "archive_only"
            card["confidence"] = "archived"
            archived += 1
            continue

        # Bucket 4: DEPRECATE (stale local-only)
        if ts <= 0.3 and not platform_tested and pnl < 10000:
            card["deprecated"] = True
            card["deprecation_reason"] = "stale_local_only"
            card["confidence"] = "stale"
            deprecated += 1
            continue

        # Moderate cards: keep but mark as low confidence
        card["confidence"] = "low"
        active += 1

    # ================================================================
    # Phase 1D: Audit summary
    # ================================================================
    print("\n=== Phase 1D: Audit Summary ===")
    print(f"  Keep active:       {active}")
    print(f"  Counterexamples:   {counterexample}")
    print(f"  Deprecated:        {deprecated}")
    print(f"  Archived:          {archived}")
    print(f"  Total:             {active + counterexample + deprecated + archived}")

    # Active family coverage
    active_families = Counter(
        c.get("architecture_family", "unknown")
        for c in cards
        if not c.get("deprecated") and c.get("status") != "failed"
    )
    print(f"\n  Active family coverage: {dict(active_families)}")

    # Platform-tested kept
    platform_kept = [c for c in cards if c.get("platform_tested") or c.get("platform_pnl")]
    print(f"  Platform-tested kept: {len(platform_kept)}")

    # ================================================================
    # Phase 2A: Apply — save updated cards
    # ================================================================
    print("\n=== Phase 2A: Apply ===")
    cards_path.write_text(json.dumps(cards, indent=2, default=str))
    print(f"  Saved {len(cards)} cards to {cards_path}")

    # ================================================================
    # Phase 2B: Validate retrieval
    # ================================================================
    print("\n=== Phase 2B: Validate Retrieval ===")
    memory = AgentMemory(persist_path=memory_path)

    # Top strategies
    top = memory.top_strategies(5)
    print("\n  top_strategies(5):")
    for c in top:
        print(
            f"    {c.get('name', '?')[:35]}: ts={c.get('transfer_score', 0):.4f}, "
            f"family={c.get('architecture_family', '?')}, deprecated={c.get('deprecated', False)}"
        )

    # Evidence pack
    pack = memory.evidence_pack()
    print("\n  evidence_pack():")
    for key, items in pack.items():
        if isinstance(items, list) and items:
            if isinstance(items[0], dict):
                names = [c.get("name", "?")[:30] for c in items]
            else:
                names = items[:3]
            print(f"    {key}: {len(items)} items — {names}")
        elif isinstance(items, list):
            print(f"    {key}: {len(items)} items")

    # Check: no deprecated in top
    top_deprecated = [c for c in top if c.get("deprecated")]
    if top_deprecated:
        print(f"\n  WARNING: {len(top_deprecated)} deprecated cards in top_strategies!")
    else:
        print("\n  OK: No deprecated cards in top_strategies")

    # Memory audit
    audit = memory.audit()
    print(f"\n  Memory audit: {audit}")

    print("\n=== Soft reset complete ===")
    print("Run 1 test round to verify clean ideation before launching 10 rounds.")


if __name__ == "__main__":
    main()
