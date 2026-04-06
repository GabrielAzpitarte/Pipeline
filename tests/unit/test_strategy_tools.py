"""Tests for agents/tools/strategy_tools.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from agents.tools.strategy_tools import (
    cleanup_strategy,
    register_strategy_import,
    unregister_strategy_import,
    write_strategy_file,
)


def _make_init(tmp_path: Path) -> Path:
    """Create a minimal strategies __init__.py."""
    init = tmp_path / "__init__.py"
    init.write_text("# strategies\nimport trader.strategies.noop as _noop  # noqa: F401, E402\n")
    return init


class TestWriteStrategyFile:
    def test_writes_file(self, tmp_path: Path) -> None:
        path = write_strategy_file("test_strat", "# code", tmp_path)
        assert path.exists()
        assert path.read_text() == "# code"

    def test_rejects_protected_name(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="built-in"):
            write_strategy_file("noop", "# code", tmp_path)

    def test_rejects_invalid_name(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid"):
            write_strategy_file("Bad-Name", "# code", tmp_path)

    def test_rejects_uppercase(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="Invalid"):
            write_strategy_file("MyStrategy", "# code", tmp_path)


class TestRegisterImport:
    def test_adds_import_line(self, tmp_path: Path) -> None:
        init = _make_init(tmp_path)
        register_strategy_import("test_strat", init)
        content = init.read_text()
        assert "import trader.strategies.test_strat" in content

    def test_idempotent(self, tmp_path: Path) -> None:
        init = _make_init(tmp_path)
        register_strategy_import("test_strat", init)
        register_strategy_import("test_strat", init)
        content = init.read_text()
        import_line = "import trader.strategies.test_strat as _test_strat"
        assert content.count(import_line) == 1


class TestUnregisterImport:
    def test_removes_import_line(self, tmp_path: Path) -> None:
        init = _make_init(tmp_path)
        register_strategy_import("test_strat", init)
        unregister_strategy_import("test_strat", init)
        content = init.read_text()
        assert "test_strat" not in content
        assert "noop" in content  # didn't remove noop


class TestCleanupStrategy:
    def test_removes_file_and_import(self, tmp_path: Path) -> None:
        init = _make_init(tmp_path)
        write_strategy_file("test_strat", "# code", tmp_path)
        register_strategy_import("test_strat", init)
        cleanup_strategy("test_strat", tmp_path, init)
        assert not (tmp_path / "test_strat.py").exists()
        assert "test_strat" not in init.read_text()
