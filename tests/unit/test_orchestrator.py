"""Tests for agents/orchestrator.py — all API calls mocked."""

from __future__ import annotations

import json
from collections import defaultdict
from typing import Any
from unittest.mock import MagicMock, patch

from agents.orchestrator import BudgetTracker, Orchestrator
from data.parse_logs import BacktestData, PriceRow


def _simple_data() -> BacktestData:
    return BacktestData(
        timestamps=[100],
        prices={
            100: {"A": PriceRow(1, 100, "A", [9998], [10], [10002], [10], 10000.0, 0.0)},
        },
        trades=defaultdict(dict),
        products={"A"},
    )


def _mock_response(
    content: dict[str, Any], input_tokens: int = 100, output_tokens: int = 50
) -> MagicMock:
    """Create a mock Anthropic API response."""
    resp = MagicMock()
    resp.content = [MagicMock(text=json.dumps(content))]
    resp.usage = MagicMock(input_tokens=input_tokens, output_tokens=output_tokens)
    return resp


class TestBudgetTracker:
    def test_initial_state(self) -> None:
        bt = BudgetTracker(budget_usd=10.0)
        assert bt.estimated_cost() == 0.0
        assert not bt.over_budget()

    def test_record_and_cost(self) -> None:
        bt = BudgetTracker(budget_usd=10.0)
        bt.record("sonnet", 1_000_000, 100_000)
        cost = bt.estimated_cost()
        assert cost > 0

    def test_over_budget(self) -> None:
        bt = BudgetTracker(budget_usd=0.001)
        bt.record("sonnet", 1_000_000, 1_000_000)
        assert bt.over_budget()

    def test_per_model_pricing(self) -> None:
        bt = BudgetTracker(budget_usd=100.0)
        bt.record("gpt-4.1-mini", 1_000_000, 0)
        gpt_cost = bt.estimated_cost()
        bt2 = BudgetTracker(budget_usd=100.0)
        bt2.record("claude-opus-4", 1_000_000, 0)
        opus_cost = bt2.estimated_cost()
        assert opus_cost > gpt_cost  # Opus is more expensive


class TestCallLlm:
    @patch("agents.orchestrator.anthropic.Anthropic")
    def test_parses_json(self, mock_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_client.messages.create.return_value = _mock_response({"result": "ok"})
        mock_cls.return_value = mock_client

        orch = Orchestrator(objective="test", data=_simple_data(), budget_usd=100.0)
        orch.client = mock_client
        result = orch._call_anthropic("sonnet", [{"role": "user", "content": "hi"}])
        assert result["result"] == "ok"

    @patch("agents.orchestrator.anthropic.Anthropic")
    def test_strips_markdown_fences(self, mock_cls: MagicMock) -> None:
        mock_client = MagicMock()
        resp = MagicMock()
        resp.content = [MagicMock(text='```json\n{"result": "ok"}\n```')]
        resp.usage = MagicMock(input_tokens=50, output_tokens=50)
        mock_client.messages.create.return_value = resp
        mock_cls.return_value = mock_client

        orch = Orchestrator(objective="test", data=_simple_data(), budget_usd=100.0)
        orch.client = mock_client
        result = orch._call_anthropic("sonnet", [{"role": "user", "content": "hi"}])
        assert result["result"] == "ok"

    @patch("agents.orchestrator.anthropic.Anthropic")
    def test_retries_on_bad_json(self, mock_cls: MagicMock) -> None:
        mock_client = MagicMock()
        bad_resp = MagicMock()
        bad_resp.content = [MagicMock(text="not json at all")]
        bad_resp.usage = MagicMock(input_tokens=50, output_tokens=50)
        good_resp = _mock_response({"fixed": True})

        mock_client.messages.create.side_effect = [bad_resp, good_resp]
        mock_cls.return_value = mock_client

        orch = Orchestrator(objective="test", data=_simple_data(), budget_usd=100.0)
        orch.client = mock_client
        result = orch._call_anthropic("sonnet", [{"role": "user", "content": "hi"}])
        assert result["fixed"] is True
        assert mock_client.messages.create.call_count == 2


class TestOrchestratorFlow:
    @patch("agents.orchestrator.anthropic.Anthropic")
    def test_stops_on_budget(self, mock_cls: MagicMock) -> None:
        mock_client = MagicMock()
        ideation_resp = _mock_response(
            {
                "candidates": [
                    {
                        "name": "test_strat",
                        "description": "test",
                        "base_strategy": "market_maker",
                        "modifications": "none",
                    }
                ]
            },
            input_tokens=500_000,
            output_tokens=500_000,
        )
        mock_client.messages.create.return_value = ideation_resp
        mock_cls.return_value = mock_client

        orch = Orchestrator(
            objective="test",
            data=_simple_data(),
            budget_usd=0.001,
            max_rounds=5,
        )
        orch.client = mock_client
        result = orch.run()
        assert result["rounds_completed"] <= 2
