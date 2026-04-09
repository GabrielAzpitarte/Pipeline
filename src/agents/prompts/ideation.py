"""Prompt template for strategy ideation — evidence-driven research process."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_SYSTEM = (
    "You are a quantitative trading strategy researcher for the IMC Prosperity "
    "competition. You analyze evidence from backtests, platform results, and failure "
    "modes to propose genuinely novel strategies. "
    "You always respond with ONLY a JSON object, no markdown fencing."
)

_PLAYBOOK_PATH = Path(__file__).parent / "playbook.md"


def _load_playbook() -> str:
    """Load the strategy playbook."""
    if _PLAYBOOK_PATH.exists():
        content = _PLAYBOOK_PATH.read_text()
        if len(content) > 3000:
            content = content[:3000] + "\n\n[... truncated ...]"
        return content
    return ""


def _format_card_brief(card: dict[str, Any], include_code: bool = False) -> str:
    """Format a strategy card into a concise summary."""
    name = card.get("name", "?")
    pnl = card.get("pnl", 0)
    ts = card.get("transfer_score", 0)
    verdict = card.get("verdict", "?")
    family = card.get("architecture_family", "?")
    notes = card.get("fragility_notes", [])
    desc = card.get("description", "")[:100]

    text = f"- **{name}** [{family}]: PnL={pnl:.0f}, transfer={ts:.4f}, verdict={verdict}"
    if notes:
        text += f"\n  Fragility: {'; '.join(notes[:2])}"
    if desc:
        text += f"\n  {desc}"

    # Per-asset scores
    by_sym = card.get("by_symbol", {})
    if by_sym:
        sym_parts = []
        for sym, ae in sorted(by_sym.items()):
            if isinstance(ae, dict):
                sym_parts.append(f"{sym}={ae.get('transfer_score', 0):.3f}")
        if sym_parts:
            text += f"\n  Per-asset: {', '.join(sym_parts)}"

    if include_code and card.get("code"):
        code = card["code"]
        if len(code) > 1500:
            code = code[:1500] + "\n# ... truncated"
        text += f"\n  ```python\n{code}\n  ```"

    return text


def build_ideation_prompt(
    objective: str,
    strategy_examples: dict[str, str],
    evidence_pack: dict[str, list[dict[str, Any]]],
    mechanics_notes: str = "",
    product_briefs: str = "",
    num_candidates: int = 1,
    round_num: int = 1,
    family_distribution: dict[str, int] | None = None,
    platform_summary: str = "",
    effort_allocation: dict[str, float] | None = None,
) -> tuple[str, list[dict[str, str]]]:
    """Build the ideation prompt using structured evidence packs.

    Args:
        evidence_pack: From memory.evidence_pack() — balanced evidence.
        family_distribution: From memory.family_distribution() — diversity info.
        effort_allocation: From onboarding — per-asset effort weights.
    """
    playbook = _load_playbook()

    # === Evidence Pack ===
    evidence_text = "\n## Evidence Pack\n"

    # Robust winners
    robust = evidence_pack.get("robust_winners", [])
    if robust:
        evidence_text += "\n### Robust local winners (transfer-score ranked)\n"
        for card in robust[:2]:
            evidence_text += _format_card_brief(card, include_code=True) + "\n"
    else:
        evidence_text += "\n### No robust winners found yet\n"

    # Platform proven
    proven = evidence_pack.get("platform_proven", [])
    if proven:
        evidence_text += "\n### Platform-proven strategies (THESE ACTUALLY WORK)\n"
        for card in proven[:3]:
            pp = card.get("platform_pnl")
            if pp:
                evidence_text += f"- **{card.get('name', '?')}**: Platform PnL={pp}, "
            else:
                evidence_text += f"- **{card.get('name', '?')}**: "
            evidence_text += f"Backtest={card.get('pnl', 0):.0f}\n"
    else:
        evidence_text += "\n### No platform-proven strategies yet\n"

    # Fragile examples
    fragile = evidence_pack.get("fragile_examples", [])
    if fragile:
        evidence_text += "\n### Fragile examples (learn what FAILS and WHY)\n"
        for card in fragile[:2]:
            evidence_text += _format_card_brief(card) + "\n"

    # Architecture diversity
    diverse = evidence_pack.get("diverse_architectures", [])
    if diverse:
        evidence_text += "\n### Architecture diversity explored so far\n"
        for card in diverse[:4]:
            evidence_text += (
                f"- [{card.get('architecture_family', '?')}] "
                f"{card.get('name', '?')}: PnL={card.get('pnl', 0):.0f}\n"
            )

    # Dead-end branches
    dead_ends = evidence_pack.get("dead_end_branches", [])
    if dead_ends:
        evidence_text += "\n### DEAD-END branches (DO NOT repeat these)\n"
        for name in dead_ends:
            evidence_text += f"- {name}: all descendants failed or fragile\n"

    # Family distribution + saturation warning
    if family_distribution:
        evidence_text += "\n### Family distribution\n"
        for fam, count in sorted(family_distribution.items(), key=lambda x: x[1], reverse=True):
            evidence_text += f"- {fam}: {count} strategies\n"
        total = sum(family_distribution.values())
        max_fam = (
            max(family_distribution, key=family_distribution.get) if family_distribution else ""
        )  # type: ignore[arg-type]
        max_count = family_distribution.get(max_fam, 0)
        if total > 5 and max_count / total > 0.7:
            evidence_text += (
                f"\n**WARNING: {max_count}/{total} strategies are {max_fam}. "
                "EXPLORE UNDERREPRESENTED FAMILIES.**\n"
            )

    # === Opportunity allocation ===
    allocation_text = ""
    if effort_allocation:
        allocation_text = "\n## Opportunity Allocation\n"
        for sym, weight in sorted(effort_allocation.items(), key=lambda x: x[1], reverse=True):
            label = "HIGH" if weight > 0.5 else "moderate" if weight > 0.3 else "maintenance"
            allocation_text += f"- **{sym}**: {weight:.0%} effort ({label} opportunity)\n"
        allocation_text += "\nFocus your proposal on the HIGH-OPPORTUNITY asset.\n"

    # === Knowledge ===
    knowledge_text = ""
    if mechanics_notes:
        knowledge_text += f"\n## Platform knowledge\n{mechanics_notes[:4000]}\n"
    if product_briefs:
        knowledge_text += f"\n## Asset intelligence\n{product_briefs[:4000]}\n"

    # === Platform feedback ===
    platform_text = ""
    if platform_summary:
        platform_text = f"\n## Latest platform feedback\n{platform_summary}\n"

    # === Reference implementations ===
    examples_text = ""
    for name, code in strategy_examples.items():
        examples_text += f"\n--- {name}.py ---\n{code}\n"

    # === Task ===
    task = (
        f"Round {round_num}. Propose exactly {num_candidates} "
        f"strateg{'y' if num_candidates == 1 else 'ies'}. "
        "Study the evidence pack above carefully. "
        "Learn from fragile examples — don't repeat their failure modes. "
        "If most strategies are from one family, propose from an UNDEREXPLORED family. "
        "Be bold — try genuinely different architectures, not parameter tweaks."
    )

    user_msg = f"""## Objective
{objective}

{knowledge_text}
{allocation_text}
{evidence_text}
{platform_text}

## Reference implementations
{examples_text}

## Strategy patterns (from past competitions — adapt concepts only)
{playbook}

## Task
{task}

Output a JSON object with ONE candidate. Be EXTREMELY SPECIFIC about the logic.

{{
  "candidates": [
    {{
      "name": "short_snake_case_name",
      "description": "One-line summary of the architecture",
      "base_strategy": "market_maker or fair_value or inventory_mm",
      "novelty_type": "architecture_change or mechanism_tweak or parameter_tweak",
      "market_assumption": "What specific market property are you exploiting?",
      "transfer_argument": "Why should this work on the real platform, not just backtester?",
      "expected_failure_mode": "Most likely way this strategy fails",
      "per_asset_logic": {{
        "stationary_assets": "EXACT step-by-step logic for stationary/mean-reverting assets.",
        "drifting_assets": "EXACT step-by-step logic for drifting/trending assets."
      }},
      "unwind_logic": "When and how to unwind inventory for ALL assets.",
      "key_innovation": "What makes this different from everything tried before."
    }}
  ]
}}"""

    return _SYSTEM, [{"role": "user", "content": user_msg}]
