"""Pre-submission validation checklist.

Catches common platform-crash bugs before upload.
"""

from __future__ import annotations

import re
from pathlib import Path


def validate_for_platform(strategy_path: Path) -> list[str]:
    """Run pre-submission checks. Returns list of warnings/blockers.

    An empty list means the strategy is ready for platform upload.
    """
    issues: list[str] = []
    code = strategy_path.read_text()

    # 1. No internal imports (platform doesn't have our modules)
    internal_imports = re.findall(r"from (trader|sim|data|experiments|analytics|agents)\.", code)
    if internal_imports:
        issues.append(f"BLOCKER: Internal imports found: {internal_imports}. Platform will crash.")

    # 2. Check for Any without import
    if "Any" in code and "from typing import" not in code and re.search(r"\bAny\b", code):
        issues.append("BLOCKER: Uses 'Any' without 'from typing import Any'.")

    # 3. Must have class Trader with run() method
    if "class Trader" not in code:
        issues.append("BLOCKER: No 'class Trader' found.")
    if "def run(" not in code:
        issues.append("BLOCKER: No 'def run(' method found.")

    # 4. Must compile
    try:
        compile(code, str(strategy_path), "exec")
    except SyntaxError as e:
        issues.append(f"BLOCKER: Syntax error: {e}")

    # 5. No numpy/pandas
    if "import numpy" in code or "import pandas" in code:
        issues.append("BLOCKER: numpy/pandas not available on platform.")

    # 6. Check for common utility function calls
    utility_calls = re.findall(r"\b(best_bid|best_ask|mid_price_from_depth|vwap)\s*\(", code)
    if utility_calls:
        issues.append(
            f"WARNING: Uses utility functions {utility_calls} — "
            "verify these are defined inline, not imported."
        )

    # 7. Check for math import (allowed)
    if "import math" not in code and "math." in code:
        issues.append("WARNING: Uses math module without importing it.")

    return issues


def validate_generated_code(code: str) -> list[str]:
    """Validate LLM-generated strategy code before execution.

    Catches structural issues before writing to disk. Returns list of
    errors — empty means valid.
    """
    errors: list[str] = []

    # 1. Must compile
    try:
        compile(code, "<generated>", "exec")
    except SyntaxError as e:
        errors.append(f"Syntax error: {e}")
        return errors

    # 2. Must define a strategy class
    if "class Trader" not in code and "@register" not in code and "class " not in code:
        errors.append("No strategy class found")

    # 3. Must have compute_orders or run method
    if "def compute_orders" not in code and "def run" not in code:
        errors.append("No compute_orders or run method found")

    # 4. Check for forbidden imports
    bad_imports = re.findall(r"import (numpy|pandas|scipy|sklearn)", code)
    if bad_imports:
        errors.append(f"Forbidden imports: {bad_imports}")

    # 5. Check for Any without import
    if re.search(r"\bAny\b", code) and "from typing" not in code:
        errors.append("Uses Any without importing from typing")

    # 6. Check for unwind logic
    has_unwind = "unwind" in code.lower() or "abs(pos" in code or "pos >" in code or "pos <" in code
    if not has_unwind:
        errors.append("WARNING: No apparent position unwind logic")

    return errors
