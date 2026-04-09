"""Prompt template for strategy ideation — platform-proven results prioritized."""

from __future__ import annotations

from pathlib import Path
from typing import Any

_SYSTEM = (
    "You are a quantitative trading strategy researcher for the IMC Prosperity "
    "competition. You analyze backtest results and propose strategies to maximize PnL. "
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


def build_ideation_prompt(
    objective: str,
    strategy_examples: dict[str, str],
    top_strategies: list[dict[str, Any]],
    failed_strategies: list[dict[str, Any]],
    mechanics_notes: str = "",
    product_briefs: str = "",
    num_candidates: int = 1,
    round_num: int = 1,
    best_strategy_code: str = "",
    best_strategy_card: dict[str, Any] | None = None,
    platform_summary: str = "",
) -> tuple[str, list[dict[str, str]]]:
    """Build the ideation prompt. Platform-proven results come first."""
    playbook = _load_playbook()

    examples_text = ""
    for name, code in strategy_examples.items():
        examples_text += f"\n--- {name}.py ---\n{code}\n"

    # === SECTION 1: Platform-proven strategies (TOP PRIORITY) ===
    proven_text = ""
    proven = [c for c in top_strategies if c.get("strengths", "").startswith("PLATFORM PROVEN")]
    if proven:
        proven_text = "\n## PLATFORM-PROVEN strategies (these ACTUALLY work)\n"
        for i, card in enumerate(proven[:4], 1):
            platform_pnl = ""
            strengths = card.get("strengths", "")
            if "PLATFORM PROVEN" in strengths:
                platform_pnl = strengths.split("PLATFORM PROVEN")[1].split(".")[0].strip()
            proven_text += (
                f"{i}. **{card.get('name', '?')}** — Backtest={card.get('pnl', 0):.0f}, "
                f"Platform={platform_pnl}\n"
            )
            # Per-product breakdown
            pp = card.get("per_product", {})
            if pp:
                for prod, pm in sorted(pp.items()):
                    fc = pm.get("fill_count", 0)
                    proven_text += f"   {prod}: {fc:.0f} fills\n"
            params = card.get("params", {})
            if params:
                param_str = ", ".join(f"{k}={v}" for k, v in sorted(params.items()))
                proven_text += f"   Params: {param_str}\n"
            proven_text += f"   {card.get('description', '')[:150]}\n"

    # === Per-asset best results ===
    asset_text = ""
    all_with_pp = [c for c in top_strategies if c.get("per_product")]
    if all_with_pp:
        asset_best: dict[str, tuple[str, float, float]] = {}  # prod -> (strat_name, fills, pnl)
        for card in all_with_pp:
            for prod, pm in card.get("per_product", {}).items():
                fc = pm.get("fill_count", 0)
                key = prod
                if key not in asset_best or fc > asset_best[key][1]:
                    asset_best[key] = (card.get("name", "?"), fc, card.get("pnl", 0))
        if asset_best:
            asset_text = "\n## Per-asset performance (best by fill count)\n"
            for prod, (name, fills, pnl) in sorted(asset_best.items()):
                asset_text += (
                    f"- **{prod}**: best is {name} ({fills:.0f} fills, total PnL={pnl:.0f})\n"
                )
            asset_text += (
                "\nNOTE: Total PnL = sum of per-asset PnL. Improving one asset improves the total. "
                "Consider which asset has the most room for improvement.\n"
            )

    # === SECTION 2: Best strategy code ===
    best_code_text = ""
    if best_strategy_code and best_strategy_card:
        best_pnl = best_strategy_card.get("pnl", 0)
        best_code_text = (
            f"\n## Best strategy code (beat this)\n"
            f"Backtest PnL={best_pnl:.0f}\n"
            f"```python\n{best_strategy_code}\n```\n"
        )

    # === SECTION 3: All tried strategies (brief summary) ===
    tried_text = ""
    non_proven = [
        c for c in top_strategies if not c.get("strengths", "").startswith("PLATFORM PROVEN")
    ]
    if non_proven:
        tried_text = "\n## Other strategies tried (backtest only, not platform-tested)\n"
        for card in non_proven[:6]:
            params = card.get("params", {})
            param_str = ", ".join(f"{k}={v}" for k, v in sorted(params.items())) if params else ""
            tried_text += f"- {card.get('name', '?')}: PnL={card.get('pnl', 0):.0f}"
            if param_str:
                tried_text += f" [{param_str}]"
            tried_text += "\n"

    # === SECTION 4: Failed strategies ===
    fail_text = ""
    if failed_strategies:
        fail_text = "\n## FAILED strategies (don't repeat these)\n"
        for card in failed_strategies[:5]:
            reason = card.get("failure_reason", "unknown")
            fail_text += f"- {card.get('name', '?')} — PnL={card.get('pnl', 0):.0f} [{reason}]\n"

    # === SECTION 5: Parameter history ===
    param_history_text = ""
    all_cards = [*top_strategies, *failed_strategies]
    param_values: dict[str, list[tuple[Any, float]]] = {}
    for card in all_cards:
        card_pnl = card.get("pnl", 0)
        for k, v in card.get("params", {}).items():
            param_values.setdefault(k, []).append((v, card_pnl))
    if param_values:
        param_history_text = "\n## Parameter history\n"
        for param, vals in sorted(param_values.items()):
            unique = sorted(set(vals), key=lambda x: x[1], reverse=True)[:5]
            entries = [f"{v}→{pnl:.0f}" for v, pnl in unique]
            param_history_text += f"- {param}: {', '.join(entries)}\n"

    # === Knowledge ===
    knowledge_text = ""
    if mechanics_notes:
        knowledge_text += f"\n## Platform knowledge\n{mechanics_notes[:4000]}\n"
    if product_briefs:
        knowledge_text += f"\n## Product behavior\n{product_briefs[:4000]}\n"

    # === Platform feedback ===
    platform_text = ""
    if platform_summary:
        platform_text = f"\n## Latest platform feedback\n{platform_summary}\n"

    # === Task ===
    task = (
        f"Round {round_num}. Propose exactly {num_candidates} strateg{'y' if num_candidates == 1 else 'ies'}. "
        "Study the PLATFORM-PROVEN results and per-asset breakdown above. "
        "Total PnL = EMERALDS PnL + TOMATOES PnL. Improving either asset improves the total. "
        "Look at which asset has the most room for improvement. "
        "The backtester overestimates ~6x but the RANKING is mostly correct. "
        "Describe ARCHITECTURE and LOGIC, not specific parameter values. "
        "Be bold — try things."
    )

    user_msg = f"""## Objective
{objective}

{knowledge_text}
{proven_text}
{asset_text}
{best_code_text}
{tried_text}
{param_history_text}
{fail_text}
{platform_text}

## Reference implementations
{examples_text}

## Strategy patterns (from past competitions — adapt concepts only)
{playbook}

## Task
{task}

Output a JSON object with ONE candidate. Be EXTREMELY SPECIFIC about the logic — describe exactly what the code should do, step by step, for EACH asset type (stationary vs drifting). The coder needs an unambiguous spec, not a vague idea.

{{
  "candidates": [
    {{
      "name": "short_snake_case_name",
      "description": "One-line summary of the architecture",
      "base_strategy": "market_maker or fair_value or inventory_mm",
      "per_asset_logic": {{
        "stationary_assets": "EXACT step-by-step logic for stationary/mean-reverting assets. Example: 1) fair_value = known_fair (e.g. 10000). 2) if spread>2: penny at bb+1 and ba-1 with size 12. 3) if ask < fair-2: buy aggressively at ask, size min(10, available). 4) skew quotes by position*0.5.",
        "drifting_assets": "EXACT step-by-step logic for drifting/trending assets. Example: 1) compute microprice = (bb*ask_vol + ba*bid_vol)/(total_vol). 2) ema = alpha*microprice + (1-alpha)*prev_ema. 3) fair = ema + momentum*weight. 4) penny at bb+1/ba-1 with size 12. 5) if ba < fair-edge: buy at ba, size 10."
      }},
      "unwind_logic": "When and how to unwind inventory for ALL assets. Example: if abs(pos)>55: cross the spread with size min(20, abs(pos)). Always unwind before quoting.",
      "key_innovation": "What makes this different from what we already tried. Be specific — reference the asset briefing data (fill rates, markouts, mean reversion strength, etc.)."
    }}
  ]
}}"""

    return _SYSTEM, [{"role": "user", "content": user_msg}]
