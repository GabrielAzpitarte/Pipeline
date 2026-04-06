"""Prompt template for strategy ideation — give data, let the thinkers think."""

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
    """Build the ideation prompt with rich per-product data and param history."""
    playbook = _load_playbook()

    # Strategy code examples
    examples_text = ""
    for name, code in strategy_examples.items():
        examples_text += f"\n--- {name}.py ---\n{code}\n"

    # Results so far — with per-product and params
    results_text = ""
    if top_strategies:
        results_text = "\n## Previous results (ranked by PnL)\n"
        for i, card in enumerate(top_strategies[:8], 1):
            status = " <<<< CURRENT BEST" if card.get("status") == "best" else ""
            sharpe = card.get("sharpe", 0)
            fills = card.get("total_fills", 0)
            strengths = card.get("strengths", "")
            results_text += (
                f"{i}. {card.get('name', '?')} ({card.get('source_model', '?')}) "
                f"— PnL={card.get('pnl', 0):.0f} [sharpe={sharpe:.1f}, fills={fills:.0f}]{status}\n"
            )
            # Per-product breakdown
            pp = card.get("per_product", {})
            if pp:
                for prod, pm in sorted(pp.items()):
                    fc = pm.get("fill_count", 0)
                    vol = pm.get("total_volume", 0)
                    results_text += f"   {prod}: {fc:.0f} fills, vol={vol:.0f}\n"
            # Params
            params = card.get("params", {})
            if params:
                param_str = ", ".join(f"{k}={v}" for k, v in sorted(params.items()))
                results_text += f"   Params: {param_str}\n"
            if strengths:
                results_text += f"   Strengths: {strengths}\n"

    # Parameter history — what values have been tried and their PnL
    param_history_text = ""
    all_cards = [*top_strategies, *failed_strategies]
    param_values: dict[str, list[tuple[Any, float]]] = {}
    for card in all_cards:
        card_pnl = card.get("pnl", 0)
        for k, v in card.get("params", {}).items():
            param_values.setdefault(k, []).append((v, card_pnl))
    if param_values:
        param_history_text = "\n## Parameter history (explored ranges)\n"
        for param, vals in sorted(param_values.items()):
            unique = sorted(set(vals), key=lambda x: x[1], reverse=True)[:6]
            entries = [f"{v}→{pnl:.0f}" for v, pnl in unique]
            best_v, best_pnl = unique[0]
            param_history_text += f"- **{param}**: {', '.join(entries)} [peak: {best_v}]\n"

    # Failed strategies with specific reasons
    fail_text = ""
    if failed_strategies:
        fail_text = "\n## What failed (don't repeat these)\n"
        for card in failed_strategies[:5]:
            reason = card.get("failure_reason", "unknown")
            fail_text += f"- {card.get('name', '?')} — PnL={card.get('pnl', 0):.0f} [{reason}]\n"

    # Best strategy code
    best_code_text = ""
    if best_strategy_code and best_strategy_card:
        best_pnl = best_strategy_card.get("pnl", 0)
        best_code_text = (
            f"\n## Best strategy so far (PnL={best_pnl:.0f}) — beat this\n"
            f"```python\n{best_strategy_code}\n```\n"
        )

    # Knowledge
    knowledge_text = ""
    if mechanics_notes:
        knowledge_text += f"\n## What we know about the platform\n{mechanics_notes[:4000]}\n"
    if product_briefs:
        knowledge_text += f"\n## What we know about the products\n{product_briefs[:4000]}\n"

    # Task
    task = (
        f"Round {round_num}. Propose exactly {num_candidates} strateg{'y' if num_candidates == 1 else 'ies'}. "
        "Study the results above. Build on what scored high. Avoid what failed.\n\n"
        "IMPORTANT RULES:\n"
        "- Describe the ARCHITECTURE and LOGIC (what the strategy does, how it decides)\n"
        "- Do NOT specify exact parameter values — Claude Opus will implement the code "
        "and a parameter sweep will optimize the values automatically\n"
        "- Say things like 'use EMA for fair value' NOT 'use EMA with alpha=0.15'\n"
        "- Say 'aggressive inventory skew' NOT 'skew factor 0.75'\n"
        "- Strategies that scored >5000 used architectural ideas, "
        "strategies that scored <0 used over-specified parameters\n"
        "- Be bold — the backtester is cheap, try things out"
    )

    # Platform feedback
    platform_text = ""
    if platform_summary:
        platform_text = (
            f"\n## Real platform feedback (from previous submission — use for calibration)\n"
            f"{platform_summary}\n"
        )

    user_msg = f"""## Objective
{objective}

{knowledge_text}
{results_text}
{param_history_text}
{fail_text}
{best_code_text}
{platform_text}

## Reference implementations
{examples_text}

## Strategy patterns from past competitions (different products — adapt concepts only)
{playbook}

## Task
{task}

Output a JSON object:
{{
  "candidates": [
    {{
      "name": "short_snake_case_name",
      "description": "ARCHITECTURAL description: what the strategy does, how it manages inventory, what signals it uses. Do NOT include specific parameter values.",
      "base_strategy": "market_maker or fair_value or inventory_mm",
      "modifications": "describe the LOGIC changes, not parameter values. Claude will code it."
    }}
  ]
}}"""

    return _SYSTEM, [{"role": "user", "content": user_msg}]
