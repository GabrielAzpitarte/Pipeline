"""Parse competition log files into structured data."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def parse_log_file(path: Path) -> list[dict[str, Any]]:
    """Read a single log file and return a list of tick dicts."""
    # TODO: implement for actual IMC log format
    return []


def parse_log_dir(directory: Path) -> list[dict[str, Any]]:
    """Parse all log files in a directory."""
    results: list[dict[str, Any]] = []
    for f in sorted(directory.glob("*.log")):
        results.extend(parse_log_file(f))
    return results
