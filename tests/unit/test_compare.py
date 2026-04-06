"""Tests for experiments/compare.py."""

from __future__ import annotations

from pathlib import Path

from data.storage import save_run
from experiments.compare import compare_two_runs
from tests.conftest import make_test_run_data


class TestCompareTwoRuns:
    def test_loads_and_compares(self, tmp_path: Path) -> None:
        rd_a = make_test_run_data(strategy="alpha")
        rd_a.metadata.run_id = "cmp_run_a"
        rd_b = make_test_run_data(strategy="beta")
        rd_b.metadata.run_id = "cmp_run_b"

        save_run(rd_a, base_dir=tmp_path)
        save_run(rd_b, base_dir=tmp_path)

        result = compare_two_runs("cmp_run_a", "cmp_run_b", base_dir=tmp_path)
        assert "run_a" in result
        assert "run_b" in result
        assert "deltas" in result
        assert "better" in result
        assert result["better"] in ("a", "b")
        assert "total_pnl" in result["run_a"]["metrics"]
