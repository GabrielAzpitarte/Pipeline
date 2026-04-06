"""Tests for agents/memory.py — persistent agent memory with strategy cards."""

from __future__ import annotations

from pathlib import Path

from agents.memory import AgentMemory


class TestAgentMemory:
    def test_add_and_search(self) -> None:
        mem = AgentMemory()
        mem.add({"strategy": "momentum", "pnl": 100})
        mem.add({"strategy": "mean_revert", "pnl": -50})
        results = mem.search("momentum")
        assert len(results) == 1
        assert results[0]["strategy"] == "momentum"

    def test_recent(self) -> None:
        mem = AgentMemory()
        for i in range(10):
            mem.add({"round": i})
        recent = mem.recent(3)
        assert len(recent) == 3
        assert recent[0]["round"] == 7

    def test_best_result(self) -> None:
        mem = AgentMemory()
        mem.add({"metrics": {"total_pnl": 10.0}})
        mem.add({"metrics": {"total_pnl": 50.0}})
        mem.add({"metrics": {"total_pnl": 30.0}})
        best = mem.best_result("total_pnl")
        assert best is not None
        assert best["metrics"]["total_pnl"] == 50.0

    def test_best_result_empty(self) -> None:
        mem = AgentMemory()
        assert mem.best_result() is None

    def test_persistence_save_load(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.json"
        mem1 = AgentMemory(persist_path=path)
        mem1.add({"key": "value"})
        assert path.exists()

        mem2 = AgentMemory(persist_path=path)
        assert len(mem2._store) == 1
        assert mem2._store[0]["key"] == "value"

    def test_clear_deletes_file(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.json"
        mem = AgentMemory(persist_path=path)
        mem.add({"data": 1})
        assert path.exists()
        mem.clear()
        assert not path.exists()
        assert len(mem._store) == 0

    def test_no_persist_path(self) -> None:
        mem = AgentMemory()
        mem.add({"a": 1})
        mem.save()  # should not crash
        mem.load()  # should not crash
        assert len(mem._store) == 1


class TestStrategyCards:
    def test_add_strategy_card(self) -> None:
        mem = AgentMemory()
        mem.add_strategy_card({"name": "strat_a", "pnl": 100.0, "description": "test"})
        assert len(mem._cards) == 1
        assert mem._cards[0]["name"] == "strat_a"

    def test_dedup_by_name(self) -> None:
        mem = AgentMemory()
        mem.add_strategy_card({"name": "strat_a", "pnl": 100.0})
        mem.add_strategy_card({"name": "strat_a", "pnl": 200.0})
        assert len(mem._cards) == 1
        assert mem._cards[0]["pnl"] == 200.0

    def test_top_strategies(self) -> None:
        mem = AgentMemory()
        mem.add_strategy_card({"name": "a", "pnl": 100.0})
        mem.add_strategy_card({"name": "b", "pnl": 500.0})
        mem.add_strategy_card({"name": "c", "pnl": 300.0})
        mem.add_strategy_card({"name": "d", "pnl": -50.0, "error": "crash"})
        top = mem.top_strategies(2)
        assert len(top) == 2
        assert top[0]["name"] == "b"
        assert top[1]["name"] == "c"

    def test_failed_strategies(self) -> None:
        mem = AgentMemory()
        mem.add_strategy_card({"name": "good", "pnl": 100.0})
        mem.add_strategy_card({"name": "bad1", "pnl": -50.0})
        mem.add_strategy_card({"name": "bad2", "pnl": -200.0, "error": "crash"})
        failed = mem.failed_strategies(5)
        assert len(failed) == 2
        assert failed[0]["name"] == "bad2"  # worst first

    def test_best_status_auto_assigned(self) -> None:
        mem = AgentMemory()
        mem.add_strategy_card({"name": "a", "pnl": 100.0})
        mem.add_strategy_card({"name": "b", "pnl": 500.0})
        assert mem._cards[1]["status"] == "best"
        assert mem._cards[0]["status"] == "tested"

    def test_cards_persistence(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.json"
        mem1 = AgentMemory(persist_path=path)
        mem1.add_strategy_card({"name": "strat_a", "pnl": 100.0})
        cards_path = tmp_path / "strategy_cards.json"
        assert cards_path.exists()

        mem2 = AgentMemory(persist_path=path)
        assert len(mem2._cards) == 1
        assert mem2._cards[0]["name"] == "strat_a"

    def test_load_knowledge_file(self, tmp_path: Path) -> None:
        kdir = tmp_path / "knowledge"
        kdir.mkdir()
        (kdir / "test.md").write_text("# Test Knowledge")
        mem = AgentMemory(knowledge_dir=kdir)
        content = mem.load_knowledge_file("test.md")
        assert "Test Knowledge" in content

    def test_load_knowledge_file_missing(self) -> None:
        mem = AgentMemory(knowledge_dir=Path("/nonexistent"))
        assert mem.load_knowledge_file("missing.md") == ""

    def test_zero_pnl_not_failed(self) -> None:
        mem = AgentMemory()
        mem.add_strategy_card({"name": "zero_fills", "pnl": 0.0})
        assert mem._cards[0]["status"] != "failed"

    def test_negative_pnl_is_failed(self) -> None:
        mem = AgentMemory()
        mem.add_strategy_card({"name": "bad", "pnl": -50.0})
        assert mem._cards[0]["status"] == "failed"

    def test_best_strategy_card(self) -> None:
        mem = AgentMemory()
        mem.add_strategy_card({"name": "a", "pnl": 100.0})
        mem.add_strategy_card({"name": "b", "pnl": 500.0})
        best = mem.best_strategy_card()
        assert best is not None
        assert best["name"] == "b"

    def test_best_strategy_card_empty(self) -> None:
        mem = AgentMemory()
        assert mem.best_strategy_card() is None

    def test_top_strategies_by_product(self) -> None:
        mem = AgentMemory()
        mem.add_strategy_card({"name": "a", "pnl": 100.0, "products": ["EMERALDS"]})
        mem.add_strategy_card({"name": "b", "pnl": 500.0, "products": ["TOMATOES"]})
        mem.add_strategy_card({"name": "c", "pnl": 300.0, "products": ["EMERALDS", "TOMATOES"]})
        emerald_top = mem.top_strategies_by_product("EMERALDS", 2)
        assert len(emerald_top) == 2
        assert emerald_top[0]["name"] == "c"

    def test_clear_deletes_cards(self, tmp_path: Path) -> None:
        path = tmp_path / "mem.json"
        mem = AgentMemory(persist_path=path)
        mem.add_strategy_card({"name": "a", "pnl": 100.0})
        mem.clear()
        assert len(mem._cards) == 0
        assert not (tmp_path / "strategy_cards.json").exists()
