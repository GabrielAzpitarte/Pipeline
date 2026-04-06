"""Prompt template for result analysis (Sonnet call)."""

from __future__ import annotations

import json
from typing import Any

_SYSTEM = (
    "You are a quantitative analyst evaluating trading strategy backtest results. "
    "Output ONLY a JSON object, no markdown fencing or explanation."
)


def build_analysis_prompt(
    round_results: list[dict[str, Any]],
    best_historical: dict[str, Any] | None,
    objective: str,
) -> tuple[str, list[dict[str, str]]]:
    """Build the system prompt and messages for the analysis call.

    Returns:
        (system_prompt, messages)
    """
    results_text = json.dumps(round_results, indent=2, default=str)

    historical_text = "No prior results."
    if best_historical is not None:
        historical_text = json.dumps(best_historical, indent=2, default=str)[:500]

    user_msg = f"""## Objective
{objective}

## This round's candidate results
{results_text}

## Best historical result
{historical_text}

## Task
Analyze the results and recommend next steps.

Output a JSON object:
{{
  "best_candidate": "name of the best candidate this round",
  "reasoning": "1-2 sentences explaining why",
  "next_directions": ["suggestion 1", "suggestion 2"],
  "should_stop": false
}}

Set should_stop to true only if results have converged or no further improvement seems possible."""

    return _SYSTEM, [{"role": "user", "content": user_msg}]
