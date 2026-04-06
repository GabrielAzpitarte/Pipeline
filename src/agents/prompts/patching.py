"""Prompt template for strategy code generation (Opus call)."""

from __future__ import annotations

from typing import Any

_SYSTEM = (
    "You are an expert Python developer writing trading strategies for the IMC Prosperity "
    "competition. You write clean, correct, profitable code. "
    "Output ONLY a JSON object, no markdown fencing or explanation."
)


def build_patching_prompt(
    candidate: dict[str, Any],
    base_strategy_code: str,
) -> tuple[str, list[dict[str, str]]]:
    """Build the system prompt and messages for code generation.

    Returns:
        (system_prompt, messages)
    """
    name = candidate.get("name", "new_strategy")
    description = candidate.get("description", "")
    modifications = candidate.get("modifications", "")

    user_msg = f"""## Task
Write a complete Python strategy file based on this specification:

**Name:** {name}
**Description:** {description}
**Modifications from base:** {modifications}

## Base strategy code to modify
```python
{base_strategy_code}
```

## Requirements
- Use `@register("{name}")` decorator
- Class must accept `params: dict[str, Any] | None = None` in __init__
- Must implement `compute_orders(self, state: TradingState) -> dict[str, list[Order]]`
- Required imports:
  ```
  from __future__ import annotations
  from typing import Any
  from trader.datamodel import Order, TradingState
  from trader.strategies import register
  from trader.utils import mid_price_from_depth, best_bid, best_ask
  ```
- Strategy must be pure: state in, orders out, no side effects
- Keep it under 60 lines

## Parameter Guidelines (use sensible defaults — a sweep will optimize later)
- Order sizes: 10-20 (never >20, never <5)
- Skew factors: 0.1-1.0 (avoid >1.5 — causes blowups)
- EMA alpha: 0.05-0.30
- Unwind threshold: 40-65 (never >70 — too close to limit 80)
- Spreads: use pennying (best_bid+1, best_ask-1) when possible
- EMERALDS fair value: always 10000 (it's stationary)

## Safety checks
- If position > 60, add aggressive unwind logic (cross the spread to reduce)
- Don't use numpy — use math stdlib only
- Test mentally: what happens at position=75? At position=-75? Does it unwind?

Output a JSON object:
{{
  "code": "the complete Python file content as a string",
  "default_params": {{"param_name": default_value}}
}}"""

    return _SYSTEM, [{"role": "user", "content": user_msg}]
