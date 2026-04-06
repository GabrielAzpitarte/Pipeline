"""Tests for experiments/registry.py — on-disk run registry."""

from __future__ import annotations

from pathlib import Path

from experiments.registry import find_runs, get_all_runs, register_run
from tests.conftest import make_test_run_data


class TestRegistry:
    def test_register_and_get_all(self, tmp_path: Path) -> None:
        rd1 = make_test_run_data(strategy="strat_a")
        rd1.metadata.run_id = "run_1"
        rd2 = make_test_run_data(strategy="strat_b")
        rd2.metadata.run_id = "run_2"

        register_run(rd1, name="exp1", base_dir=tmp_path)
        register_run(rd2, name="exp2", base_dir=tmp_path)

        runs = get_all_runs(base_dir=tmp_path)
        assert len(runs) == 2
        assert runs[0].run_id == "run_1"
        assert runs[1].run_id == "run_2"

    def test_persists_to_disk(self, tmp_path: Path) -> None:
        rd = make_test_run_data()
        register_run(rd, base_dir=tmp_path)

        # Read again from disk (fresh call, not cached)
        runs = get_all_runs(base_dir=tmp_path)
        assert len(runs) == 1
        assert runs[0].strategy == "test_strat"

    def test_find_by_strategy(self, tmp_path: Path) -> None:
        rd1 = make_test_run_data(strategy="alpha")
        rd1.metadata.run_id = "r1"
        rd2 = make_test_run_data(strategy="beta")
        rd2.metadata.run_id = "r2"

        register_run(rd1, base_dir=tmp_path)
        register_run(rd2, base_dir=tmp_path)

        found = find_runs(strategy="alpha", base_dir=tmp_path)
        assert len(found) == 1
        assert found[0].strategy == "alpha"

    def test_find_by_tag(self, tmp_path: Path) -> None:
        rd = make_test_run_data()
        rd.metadata.tags = ["production", "v2"]
        register_run(rd, base_dir=tmp_path)

        found = find_runs(tag="production", base_dir=tmp_path)
        assert len(found) == 1

        found_none = find_runs(tag="nonexistent", base_dir=tmp_path)
        assert len(found_none) == 0
