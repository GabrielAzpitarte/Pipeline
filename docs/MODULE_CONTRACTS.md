# Module Contracts

Every module has a defined responsibility. No cross-layer shortcuts. No duplicated ownership.

## `src/sim/` — Execution Engine
- **OWNS**: order matching, position tracking, PnL computation, scenario application
- **READS**: strategy orders, market data, scenario config
- **EMITS**: SimResult (raw execution facts)
- **MUST NEVER**: compute transfer scores, make ranking decisions, access memory

## `src/analytics/` — Metrics & Diagnostics
- **OWNS**: all derived metrics (sharpe, drawdown, fill diagnostics, robustness, transfer score, market intelligence)
- **READS**: RunArtifact (raw facts only)
- **EMITS**: computed metrics, diagnostics, scores
- **MUST NEVER**: run simulations, modify artifacts, access memory, make selection decisions

## `src/experiments/` — Experiment Orchestration
- **OWNS**: running experiments, candidate evaluation, artifact storage, RunArtifact schema
- **READS**: strategy code, market data, analytics results
- **EMITS**: RunArtifact, CandidateEvaluation
- **MUST NEVER**: define matching semantics, compute metrics directly (delegates to analytics), make ideation decisions

## `src/agents/` — Research Loop
- **OWNS**: ideation, code generation, strategy memory, prompt construction, assembly decisions
- **READS**: evaluation results, analytics output, platform results
- **EMITS**: strategy candidates, strategy cards, assembled strategies
- **MUST NEVER**: run simulations directly, compute metrics, override evaluation verdicts

## `src/trader/` — Strategy Interface
- **OWNS**: strategy protocol, strategy registry, risk filtering, datamodel types
- **READS**: TradingState
- **EMITS**: orders
- **MUST NEVER**: access simulation internals, evaluation results, or memory

## `src/submission/` — Packaging
- **OWNS**: submission file generation, platform compatibility validation, strategy combination
- **READS**: strategy code, evaluation results
- **EMITS**: platform-ready .py files
- **MUST NEVER**: run simulations, compute scores, modify memory

## One Owner Per Concept

| Concept | Owner | NOT owned by |
|---------|-------|-------------|
| Execution semantics | `src/sim/` | everything else |
| Run artifact schema | `src/experiments/artifacts.py` | sim, analytics |
| Derived metrics | `src/analytics/metrics.py` | sweep_runner, evaluator |
| Fill diagnostics | `src/analytics/robustness.py` | sweep_runner |
| Transfer score | `src/analytics/robustness.py` | evaluator (delegates) |
| Per-asset scoring | `src/analytics/robustness.py` | evaluator (delegates) |
| Market intelligence | `src/analytics/market_intel.py` | prompts |
| Strategy ranking | `src/experiments/evaluator.py` | memory, prompts |
| Strategy memory | `src/agents/memory.py` | evaluator |

## Hard Design Rule

**No metric, label, or verdict may exist in two independently maintained forms.**

If `passive_fill_share` is computed, it is computed ONCE in `analytics/robustness.py` and read everywhere else. If `final_pnl` exists, it lives in `RunArtifact.summary.final_pnl` and nowhere else computes it independently.
