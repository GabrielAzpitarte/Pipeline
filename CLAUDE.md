# CLAUDE.md — Project Conventions

## What this project is
A trading strategy development lab for the IMC Prosperity competition. We build strategies, simulate them locally, analyse results, and package submissions.

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
1. Create `src/trader/strategies/my_strat.py`
2. Register it in `src/trader/strategies/__init__.py`
3. Add a unit test in `tests/unit/test_my_strat.py`
4. Run `make check` before committing.

## When modifying the sim engine
1. Write a regression test in `tests/regression/` first.
2. Keep a golden output snapshot in `tests/golden/` if behaviour changes.

## Hard Rules
- **Never rewrite public interfaces without permission.**
- **Prefer minimal diffs** — change only what's needed.
- **Always run tests after code edits** — `make check` before every commit.
- **Never touch submission code without explicit instruction.**
