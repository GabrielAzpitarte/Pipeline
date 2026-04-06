Run the full regression test suite and report results:

```bash
python -m pytest tests/regression/ -v --tb=short
```

Then run the golden tests:

```bash
python -m pytest tests/golden/ -v --tb=short
```

If any tests fail, analyze the failure:
1. Identify which strategy or scenario broke
2. Check if sim engine code changed recently (`git diff src/sim/`)
3. Explain whether the failure is a real bug or an expected change in semantics
4. Suggest whether to fix the code or update the golden fixture
