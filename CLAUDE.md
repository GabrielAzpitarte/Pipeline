# CLAUDE.md — Project Conventions

## What this project is
A trading strategy development lab for the IMC Prosperity competition. We build strategies, simulate them locally, analyse results, and package submissions.

## Repo map
```
src/
  trader/             # Strategy protocol, registry, Trader class, risk filters
    strategies/       # One file per strategy, auto-registered via @register
    datamodel.py      # Prosperity API types (Order, TradingState, OrderDepth, etc.)
    trader.py         # Dispatches to strategy, applies risk filters
    utils.py          # best_bid, best_ask, mid_price, vwap
    risk.py           # Pre-execution risk filtering
  sim/                # Local backtesting engine
    engine.py         # SimEngine — full faithful simulation loop
    fast_engine.py    # FastSimEngine — quick screening mode
    matching.py       # Two-phase order matching (book + market trades)
    pnl.py            # PnL tracking (cash + unrealized)
    limits.py         # Prosperity position limits, all-or-nothing enforcement
  data/               # Data loading and persistence
    parse_logs.py     # CSV parsing (prices, trades -> BacktestData)
    schemas.py        # Pydantic schemas for JSON state files
    storage.py        # Save/load RunData to disk
  experiments/        # Experiment orchestration
    runner.py         # run_experiment() — sim + metrics + persist
    config.py         # TOML config parsing
    cli.py            # typer CLI (run, sweep, rank, list)
    sweep_runner.py   # Parameter grid sweeps
    models.py         # RunData, RunMetadata, serialization
    registry.py       # On-disk run index
  analytics/          # Post-run analysis
    metrics.py        # Sharpe, drawdown, fill summaries
    plots.py          # Equity curve, positions, fills, drawdown, dashboard
    dashboards.py     # HTML report generation
  submission/         # Competition packaging

tests/
  unit/               # Fast isolated tests
  golden/             # Locked output snapshots — change means breakage
  regression/         # Baseline strategies on fixture data
  fixtures/           # CSV + JSON test data
  conftest.py         # Shared pytest fixtures

configs/              # TOML experiment configs
artifacts/            # Run outputs (gitignored)
```

## Code style
- Python 3.11+
- Formatting: `ruff format`
- Linting: `ruff check`
- Type checking: `mypy --strict src/`
- All public functions must have type annotations and docstrings.

## Running things
```bash
make check          # full lint + type + test pass
make test           # pytest only
make fmt            # auto-format
```

## CLI commands
```bash
python -m experiments run --config configs/sample_noop.toml      # single run
python -m experiments run --config configs/foo.toml --fast        # fast sim
python -m experiments sweep --config configs/sample_sweep.toml   # param sweep
python -m experiments rank --metric total_pnl                    # rank past runs
python -m experiments list                                       # list all runs
```

## Project structure rules
- All importable code lives under `src/`. Use `from trader.config import ...` etc.
- Strategies go in `src/trader/strategies/` — one file per strategy.
- Tests mirror `src/` structure inside `tests/unit/`.
- Raw data never gets committed — it lives in `data_raw/` (gitignored).
- Experiment outputs go to `artifacts/` (gitignored).

## Naming conventions
- Files: `snake_case.py`
- Classes: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`
- Private helpers: `_leading_underscore`

## Key constraints
- **No secrets in code.** Use `.env` for API keys, paths, etc.
- **No giant data files in git.** Keep `data_raw/`, `data_processed/`, `artifacts/` gitignored.
- **Strategies must be pure.** A strategy receives state, returns orders — no side effects.
- **Risk limits are non-negotiable.** All orders pass through `src/trader/risk.py` before execution.

## When adding a new strategy
1. Create `src/trader/strategies/my_strat.py` with `@register("my_strat")`.
2. Accept params via `__init__(self, params: dict | None = None)`.
3. Implement `compute_orders(self, state: TradingState) -> dict[str, list[Order]]`.
4. Add import in `src/trader/strategies/__init__.py`.
5. Write unit tests in `tests/unit/test_my_strat.py`.
6. Add a regression test entry in `tests/regression/test_baselines.py`.
7. Create a TOML config in `configs/`.
8. Run `make check` before committing.

## When modifying the sim engine
1. Write a regression test in `tests/regression/` first.
2. Keep a golden output snapshot in `tests/golden/` if behaviour changes.

## Simulator integrity rules
- **Never modify matching semantics** (`src/sim/matching.py`) without updating golden tests.
- **Never change position limit enforcement** without re-verifying golden snapshots.
- **Run regression suite** (`pytest tests/regression/ -v`) after any sim change.
- **Golden values are sacred** — if a golden test breaks, investigate before updating the fixture.

## Hard Rules
- **Never rewrite public interfaces without permission.**
- **Prefer minimal diffs** — change only what's needed.
- **Always run tests after code edits** — `make check` before every commit.
- **Never touch submission code without explicit instruction.**
