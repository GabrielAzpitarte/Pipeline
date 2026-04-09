"""Prompt template for strategy code generation (Opus call)."""

from __future__ import annotations

from typing import Any

_SYSTEM = (
    "You are an expert Python developer writing trading strategies for the IMC Prosperity "
    "competition. You write clean, correct, profitable code. "
    "Output ONLY the Python code inside a ```python code block. No explanation, no JSON wrapping."
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
    per_asset_logic = candidate.get("per_asset_logic", {})
    unwind_logic = candidate.get("unwind_logic", "")
    key_innovation = candidate.get("key_innovation", "")
    modifications = candidate.get("modifications", "")

    # Build detailed spec from structured fields if available
    if per_asset_logic:
        asset_specs = ""
        for asset_type, logic in per_asset_logic.items():
            asset_specs += f"\n### {asset_type}\n{logic}\n"

        spec_block = f"""## Strategy Specification (implement EXACTLY as described)

**Name:** {name}
**Summary:** {description}
**Key innovation:** {key_innovation}

## Per-Asset Logic
{asset_specs}
### Unwind/Safety Logic (all assets)
{unwind_logic}
"""
    else:
        spec_block = f"""## Strategy Specification
**Name:** {name}
**Description:** {description}
**Modifications from base:** {modifications}
"""

    user_msg = f"""## Task
Implement this trading strategy EXACTLY as specified. Do not deviate from the logic described.

{spec_block}

## Base strategy code (for reference — modify as needed)
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
- MUST handle each asset with appropriate logic (stationary vs drifting)
- Position limit is 80 per asset — never exceed it
- Classify each asset by its behavior and apply the matching logic from the spec

## Parameter Guidelines
- Order sizes: 10-20 (never >20, never <5)
- Skew factors: 0.1-1.0
- EMA alpha: 0.05-0.30
- Unwind threshold: 40-65
- EMERALDS fair value: always 10000

## Critical Safety
- If abs(position) > 55: MUST add aggressive unwind (cross the spread)
- Always quote every tick — don't skip ticks
- Don't use numpy — use math stdlib only
- Check: does unwind work at position=75? At position=-75?

Output ONLY the complete Python file inside a ```python code block. Nothing else — no JSON, no explanation.

```python
from __future__ import annotations
...your code here...
```"""

    return _SYSTEM, [{"role": "user", "content": user_msg}]
