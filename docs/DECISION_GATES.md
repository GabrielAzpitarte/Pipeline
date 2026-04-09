# Decision Gates

## Mandatory Review Points

### Before changing matching semantics
- Run full regression suite (`tests/regression/`, `tests/golden/`, `tests/invariants/`)
- Write rationale: what is changing, why it helps transfer, evidence
- Re-run baselines, compare against `artifacts/baseline_comparison.json`
- Update golden values only after review

### Before platform submission
- Run `validate_for_platform()` checklist
- Verify strategy compiles standalone (`python -c "exec(open('strategy.py').read())"`)
- Check: no `from trader.*` imports, no `Any` without import, no numpy
- Record local prediction + confidence before submitting

### Before changing ranking objective
- Compare old vs new ranking on frozen baselines
- Report Spearman correlation of each system vs known platform PnL
- Document which strategies change rank and why

### Before changing memory retrieval
- Audit: does the change bias toward one architecture family?
- Check: are failed strategies still visible as counterexamples?
- Verify: platform-proven strategies retain priority

## Research Modes

| Mode | Purpose | What's allowed |
|------|---------|---------------|
| Research | Explore new ideas | Any experiment, no platform submission |
| Candidate | Prepare finalists | Deep evaluation, comparison reports |
| Production | Platform submission | Checklist required, human approval gate |
