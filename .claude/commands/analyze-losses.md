Analyze the worst-performing timestamps for run: $ARGUMENTS

Steps:
1. Load the run:
```python
from data.storage import load_run
from analytics.metrics import compute_returns

run_data = load_run("$ARGUMENTS")
returns = compute_returns(run_data.pnl_series)
```

2. Find the 5 timestamps with the largest PnL drops (most negative returns).

3. For each bad timestamp, examine the corresponding tick in `run_data`:
   - What orders were submitted (`orders_submitted`)
   - What fills occurred (`fills` — was it a buy or sell, at what price)
   - Position before and after
   - Mid prices at that tick
   - Cash and PnL change

4. For each loss, explain the likely cause:
   - **Adverse fill**: bought high or sold low relative to mid
   - **Inventory mark-to-market**: held a position when the mid price moved against you
   - **Spread compression**: quoted too tight and got picked off
   - **Position limit**: orders rejected, missed a profitable trade

5. Suggest potential improvements:
   - Widen spread?
   - Reduce order size?
   - Increase skew factor?
   - Add a signal or filter?
