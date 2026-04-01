"""Quick sanity checks before submitting."""

from __future__ import annotations

from pathlib import Path


def check_file_exists(path: Path) -> bool:
    """Verify the submission file exists."""
    return path.is_file()


def check_no_imports_outside_stdlib(path: Path) -> list[str]:
    """Return any non-stdlib imports found in the file."""
    # TODO: parse imports and check against allowed list
    _ = path
    return []


def run_all_checks(path: Path) -> dict[str, bool]:
    """Run all smoke checks and return results."""
    return {
        "file_exists": check_file_exists(path),
        "clean_imports": len(check_no_imports_outside_stdlib(path)) == 0,
    }
