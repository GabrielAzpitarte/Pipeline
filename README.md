# IMC Trading Lab

A clean, reproducible environment for developing, simulating, and submitting trading strategies for the IMC Prosperity competition.

## Quick Start
```bash
cp .env.example .env
make install
make check
```

## Project Layout

| Directory | Purpose |
|---|---|
| `src/trader/` | Core trading logic — strategies, config, risk, utilities |
| `src/sim/` | Local simulation engine — matching, PnL, limits, state |
| `src/data/` | Log parsing, schemas, storage helpers |
| `src/experiments/` | Experiment runner, parameter sweeps, comparison tools |
| `src/analytics/` | Metrics, plots, dashboards |
| `src/agents/` | LLM-powered orchestration (optional) |
| `src/submission/` | Packaging, smoke checks, submission checklist |
| `tests/` | Unit, integration, golden, regression tests |
| `data_raw/` | Raw competition logs (gitignored) |
| `data_processed/` | Cleaned/transformed data (gitignored) |
| `artifacts/` | Experiment outputs, plots, reports (gitignored) |

## Branches

- `main` — stable, tested, submission-ready
- `dev` — current working branch
- `feature/<name>` — isolated feature work, merge into `dev`

## Makefile Targets

- `make install` — Create venv and install all deps
- `make fmt` — Auto-format with ruff
- `make lint` — Lint with ruff
- `make typecheck` — Type-check with mypy
- `make test` — Run pytest
- `make check` — fmt + lint + typecheck + test
- `make clean` — Remove caches and build artifacts
