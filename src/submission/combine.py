"""Combine best-per-product strategies into a single submission file."""

from __future__ import annotations

import re
import textwrap
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from trader.logging_utils import get_logger

_log = get_logger("submission.combine")

# Datamodel preamble shared by all Prosperity 4 strategies.
_DATAMODEL_PREAMBLE = textwrap.dedent("""\
    from typing import Dict, List

    Time = int
    Symbol = str
    Product = str
    Position = int
    UserId = str
    ObservationValue = int


    class Listing:
        def __init__(self, symbol: Symbol, product: Product, denomination: Product) -> None:
            self.symbol = symbol
            self.product = product
            self.denomination = denomination


    class ConversionObservation:
        def __init__(self, bidPrice: float, askPrice: float, transportFees: float,
                     exportTariff: float, importTariff: float, sugarPrice: float,
                     sunlightIndex: float) -> None:
            self.bidPrice = bidPrice
            self.askPrice = askPrice
            self.transportFees = transportFees
            self.exportTariff = exportTariff
            self.importTariff = importTariff
            self.sugarPrice = sugarPrice
            self.sunlightIndex = sunlightIndex


    class Observation:
        def __init__(self, plainValueObservations: Dict[Product, ObservationValue] | None = None,
                     conversionObservations: Dict[Product, ConversionObservation] | None = None) -> None:
            self.plainValueObservations = plainValueObservations or {}
            self.conversionObservations = conversionObservations or {}


    class Order:
        def __init__(self, symbol: Symbol, price: int, quantity: int) -> None:
            self.symbol = symbol
            self.price = price
            self.quantity = quantity


    class OrderDepth:
        def __init__(self) -> None:
            self.buy_orders: Dict[int, int] = {}
            self.sell_orders: Dict[int, int] = {}


    class Trade:
        def __init__(self, symbol: Symbol, price: int, quantity: int,
                     buyer: UserId = "", seller: UserId = "",
                     timestamp: int = 0) -> None:
            self.symbol = symbol
            self.price = price
            self.quantity = quantity
            self.buyer = buyer
            self.seller = seller
            self.timestamp = timestamp


    class TradingState:
        def __init__(self, timestamp: Time, traderData: str,
                     listings: Dict[Symbol, Listing],
                     order_depths: Dict[Symbol, OrderDepth],
                     own_trades: Dict[Symbol, List[Trade]],
                     market_trades: Dict[Symbol, List[Trade]],
                     position: Dict[Product, Position],
                     observations: Observation) -> None:
            self.timestamp = timestamp
            self.traderData = traderData
            self.listings = listings
            self.order_depths = order_depths
            self.own_trades = own_trades
            self.market_trades = market_trades
            self.position = position
            self.observations = observations
""")


@dataclass
class StrategyComponent:
    """One strategy's contribution to the combined strategy."""

    source_code: str
    products: list[str]
    params: dict[str, Any] = field(default_factory=dict)


def _extract_imports(code: str) -> list[str]:
    """Extract import lines (excluding datamodel-related ones)."""
    imports: list[str] = []
    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            # Skip datamodel and typing imports (already in preamble)
            if any(
                kw in stripped for kw in ("typing", "Listing", "Order", "Trade", "TradingState")
            ):
                continue
            imports.append(stripped)
    return imports


def _extract_module_constants(code: str) -> list[str]:
    """Extract UPPER_SNAKE_CASE = value lines."""
    constants: list[str] = []
    for line in code.splitlines():
        if re.match(r"^[A-Z][A-Z0-9_]*\s*=\s*", line):
            constants.append(line)
    return constants


def _extract_init_body(code: str) -> list[str]:
    """Extract the body of __init__ (self.xxx = ... lines)."""
    lines: list[str] = []
    in_init = False
    init_indent = 0
    for line in code.splitlines():
        if "def __init__" in line:
            in_init = True
            init_indent = len(line) - len(line.lstrip())
            continue
        if in_init:
            stripped = line.strip()
            if not stripped:
                continue
            current_indent = len(line) - len(line.lstrip())
            # Stop at next method or class definition (same or lower indent)
            if current_indent <= init_indent and stripped.startswith("def "):
                break
            if "self." in line and "=" in line:
                lines.append(line.rstrip())
    return lines


def _extract_trader_class(code: str) -> str | None:
    """Extract the Trader class definition from strategy source code."""
    lines = code.splitlines()
    class_lines: list[str] = []
    in_class = False

    for line in lines:
        if re.match(r"^class Trader\b", line):
            in_class = True
            class_lines.append(line)
            continue
        if in_class:
            if line and not line[0].isspace() and not line.startswith("#"):
                break
            class_lines.append(line)

    return "\n".join(class_lines) if class_lines else None


def combine_strategies_python(
    components: list[StrategyComponent],
) -> str | None:
    """Combine strategies via composition: one sub-Trader per product.

    Each component's Trader class is renamed (e.g. ``_Trader_emeralds``)
    and included in the output. The main ``Trader`` class holds instances
    of each sub-trader and dispatches by product symbol.
    """
    if len(components) < 2:
        return None

    # Collect all imports and constants
    all_imports: set[str] = set()
    all_constants: list[str] = []
    for comp in components:
        all_imports.update(_extract_imports(comp.source_code))
        all_constants.extend(_extract_module_constants(comp.source_code))

    seen_constants: dict[str, str] = {}
    for line in all_constants:
        name = line.split("=")[0].strip()
        seen_constants[name] = line

    # Extract and rename each Trader class
    sub_traders: list[tuple[str, str, list[str]]] = []  # (cls_name, class_code, products)
    for comp in components:
        product_tag = "_".join(p.lower() for p in comp.products)
        cls_name = f"_Trader_{product_tag}"

        class_code = _extract_trader_class(comp.source_code)
        if class_code is None:
            return None
        class_code = class_code.replace("class Trader", f"class {cls_name}", 1)
        sub_traders.append((cls_name, class_code, comp.products))

    # Build output
    all_products: list[str] = []
    for comp in components:
        all_products.extend(comp.products)

    parts: list[str] = []
    parts.append(f'"""Combined strategy: {", ".join(sorted(all_products))}."""\n\n')
    parts.append("import math\n")
    for imp in sorted(all_imports):
        if "math" not in imp:
            parts.append(imp + "\n")
    parts.append("\n")
    parts.append(_DATAMODEL_PREAMBLE)
    parts.append("\n")

    if seen_constants:
        for line in seen_constants.values():
            parts.append(line + "\n")
        parts.append("\n\n")

    for _, cls_code, _ in sub_traders:
        parts.append(cls_code + "\n\n\n")

    # Main dispatcher
    parts.append("class Trader:\n")
    parts.append("    def __init__(self) -> None:\n")
    dispatch_entries: list[str] = []
    for cls_name, _, products in sub_traders:
        attr = f"_sub_{products[0].lower()}"
        parts.append(f"        self.{attr} = {cls_name}()\n")
        for product in products:
            dispatch_entries.append(f'"{product}": self.{attr}')
    parts.append("        self._dispatch = {" + ", ".join(dispatch_entries) + "}\n")
    parts.append("\n")
    parts.append(
        "    def run(self, state: TradingState) -> tuple[dict[str, list[Order]], int, str]:\n"
    )
    parts.append("        combined: dict[str, list[Order]] = {}\n")
    parts.append("        for product in state.order_depths:\n")
    parts.append("            sub = self._dispatch.get(product)\n")
    parts.append("            if sub is None:\n")
    parts.append("                continue\n")
    parts.append("            result = sub.run(state)\n")
    parts.append("            sub_orders = result[0] if isinstance(result, tuple) else result\n")
    parts.append("            for sym, ords in sub_orders.items():\n")
    parts.append("                if sym == product:\n")
    parts.append("                    combined[sym] = ords\n")
    parts.append('        return combined, 0, ""\n')

    return "".join(parts)


def combine_strategies_llm(
    components: list[StrategyComponent],
    model: str = "claude-sonnet-4-20250514",
) -> str:
    """Combine strategies using an LLM for complex cases.

    Sends both strategy codes + instructions to Claude, which generates
    the combined file.
    """
    import anthropic

    client = anthropic.Anthropic()

    product_assignments = []
    code_blocks = []
    for i, comp in enumerate(components):
        label = chr(ord("A") + i)
        product_assignments.append(f"Strategy {label} handles: {', '.join(comp.products)}")
        params_note = ""
        if comp.params:
            params_note = f"\nUse these optimized params: {comp.params}"
        code_blocks.append(f"### Strategy {label}{params_note}\n```python\n{comp.source_code}\n```")

    prompt = (
        "Combine these strategies into a SINGLE self-contained Trader class.\n\n"
        "Requirements:\n"
        "- Include ALL datamodel classes inline (Listing, Order, OrderDepth, etc.)\n"
        "- The Trader class must have: __init__(self) and "
        "run(self, state) -> tuple[dict, int, str]\n"
        f"- {'; '.join(product_assignments)}\n"
        "- Do NOT change the order generation logic, only merge initialization and dispatch\n"
        "- Import math if needed. No other external imports.\n"
        "- Output ONLY the Python code, no explanations.\n\n" + "\n\n".join(code_blocks)
    )

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text  # type: ignore[union-attr]

    # Strip markdown fences if present
    if "```python" in text:
        text = text.split("```python", 1)[1]
        text = text.rsplit("```", 1)[0]

    return text.strip()


def combine_best_per_product(
    emeralds_code: str,
    emeralds_params: dict[str, Any],
    tomatoes_code: str,
    tomatoes_params: dict[str, Any],
    output_path: Path,
    use_llm: bool = False,
) -> Path:
    """Combine best strategy per product into one submission file.

    Tries the deterministic Python combiner first. Falls back to
    LLM-based combination if the Python combiner fails or ``use_llm``
    is set.

    Returns:
        Path to the combined strategy file.
    """
    from agents.tools.strategy_tools import apply_params_to_code

    # Apply optimized params to each source
    em_code = (
        apply_params_to_code(emeralds_code, emeralds_params) if emeralds_params else emeralds_code
    )
    tom_code = (
        apply_params_to_code(tomatoes_code, tomatoes_params) if tomatoes_params else tomatoes_code
    )

    components = [
        StrategyComponent(source_code=em_code, products=["EMERALDS"], params=emeralds_params),
        StrategyComponent(source_code=tom_code, products=["TOMATOES"], params=tomatoes_params),
    ]

    combined: str | None = None

    if not use_llm:
        combined = combine_strategies_python(components)
        if combined is None:
            _log.info("Python combiner failed, falling back to LLM")

    if combined is None:
        combined = combine_strategies_llm(components)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(combined)
    _log.info("Combined strategy written to %s", output_path)

    return output_path
