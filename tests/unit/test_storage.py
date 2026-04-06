"""Tests for data/storage.py — save_run/load_run."""

from __future__ import annotations

from pathlib import Path

import pytest

from data.storage import load_run, save_run
from tests.conftest import make_test_run_data


class TestSaveAndLoadRun:
    def test_roundtrip(self, tmp_path: Path) -> None:
        original = make_test_run_data()
        save_run(original, base_dir=tmp_path)
        loaded = load_run(original.metadata.run_id, base_dir=tmp_path)

        assert loaded.metadata.run_id == original.metadata.run_id
        assert loaded.timestamps == original.timestamps
        assert loaded.pnl_series == original.pnl_series
        assert loaded.final_pnl == original.final_pnl
        assert len(loaded.fills) == len(original.fills)

    def test_creates_directory(self, tmp_path: Path) -> None:
        rd = make_test_run_data()
        run_dir = save_run(rd, base_dir=tmp_path)
        assert run_dir.exists()
        assert (run_dir / "result.json").exists()

    def test_load_nonexistent_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load_run("nonexistent_run_id", base_dir=tmp_path)
