Load and summarize the experiment run with ID: $ARGUMENTS

Steps:
1. Load the run data:
```python
from data.storage import load_run
from analytics.metrics import compute_all_metrics, per_product_metrics, top_timestamps

run_data = load_run("$ARGUMENTS")
metrics = compute_all_metrics(run_data)
per_product = per_product_metrics(run_data)
best = top_timestamps(run_data, n=3, best=True)
worst = top_timestamps(run_data, n=3, best=False)
```

2. Print a summary including:
   - Strategy name and config params
   - Timestamp range and number of ticks
   - Final PnL, cash, and positions
   - Total fills (buys vs sells), total volume
   - Sharpe ratio and max drawdown
   - Per-product breakdown (fill count, avg prices, net quantity)
   - Top 3 best timestamps (biggest PnL gains)
   - Top 3 worst timestamps (biggest PnL drops)

3. Flag any anomalies:
   - Positions near or at limit
   - Negative Sharpe ratio
   - Large drawdown (> 20%)
   - Very few or zero fills
