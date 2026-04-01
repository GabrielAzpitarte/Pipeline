.PHONY: install fmt lint typecheck test check clean

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e ".[dev]"
	$(VENV)/bin/pre-commit install
	@echo "\n✅  Done. Activate with:  source $(VENV)/bin/activate"

fmt:
	$(VENV)/bin/ruff format src/ tests/

lint:
	$(VENV)/bin/ruff check src/ tests/

typecheck:
	$(VENV)/bin/mypy -p trader -p sim -p data -p experiments -p analytics -p agents -p submission

test:
	$(VENV)/bin/pytest tests/

check: fmt lint typecheck test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf dist/ build/ htmlcov/ .coverage
