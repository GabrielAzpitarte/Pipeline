Create a new trading strategy called "$ARGUMENTS". Follow these steps exactly:

1. Create `src/trader/strategies/$ARGUMENTS.py` with:
   - Import from `trader.datamodel` (Order, TradingState) and `trader.strategies` (register)
   - Import `mid_price_from_depth` from `trader.utils`
   - `@register("$ARGUMENTS")` decorator on the class
   - Constructor accepting `params: dict[str, Any] | None = None`
   - `compute_orders(self, state: TradingState) -> dict[str, list[Order]]` method
   - Proper docstring and type annotations
   - Strategy must be pure: state in, orders out, no side effects

2. Add this line at the bottom of `src/trader/strategies/__init__.py`:
   ```python
   import trader.strategies.$ARGUMENTS as _$ARGUMENTS  # noqa: F401, E402
   ```

3. Create `tests/unit/test_$ARGUMENTS.py` with tests for:
   - Strategy is registered (`"$ARGUMENTS" in STRATEGIES`)
   - Default params work
   - Custom params work
   - Empty order depths are handled (no crash)
   - Orders have correct symbol, price, and quantity signs

4. Run `make check` to verify everything passes.
