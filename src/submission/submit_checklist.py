"""Print a human-readable pre-submission checklist."""

from __future__ import annotations

CHECKLIST = [
    "All tests pass (make check)",
    "Strategy runs without errors in local sim",
    "Position limits respected for all products",
    "No external dependencies in submission file",
    "No hardcoded paths or secrets",
    "PnL is positive on training data",
    "Submission file is self-contained",
]


def print_checklist() -> None:
    """Print the checklist to stdout."""
    print("=== Pre-Submission Checklist ===")
    for i, item in enumerate(CHECKLIST, 1):
        print(f"  [ ] {i}. {item}")
