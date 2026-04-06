"""Tests for experiments/models.py — RunData types and serialization."""

from __future__ import annotations

import re
from collections import defaultdict

from data.parse_logs import BacktestData, PriceRow
from experiments.models import (
    dict_to_run_data,
    generate_run_id,
    run_data_to_dict,
    sim_result_to_run_data,
)
from sim.engine import SimConfig, SimEngine
from tests.conftest import make_test_run_data


class TestGenerateRunId:
    def test_format(self) -> None:
        rid = generate_run_id("noop")
        assert "noop" in rid
        assert re.match(r"\d{8}_\d{6}_noop_[0-9a-f]{6}", rid)

    def test_uniqueness(self) -> None:
        a = generate_run_id("x")
        b = generate_run_id("x")
        assert a != b


class TestSimResultToRunData:
    def test_conversion(self) -> None:
        data = BacktestData(
            timestamps=[100, 200],
            prices={
                100: {
                    "A": PriceRow(1, 100, "A", [9998], [10], [10002], [10], 10000.0, 0.0),
                },
                200: {
                    "A": PriceRow(1, 200, "A", [9999], [12], [10001], [12], 10000.0, 0.0),
                },
            },
            trades=defaultdict(dict),
            products={"A"},
        )
        config = SimConfig(strategy_name="noop")
        sim_result = SimEngine(config).run(data)
        run_data = sim_result_to_run_data(sim_result, config, dataset_description="test")

        assert len(run_data.timestamps) == 2
        assert len(run_data.pnl_series) == 2
        assert run_data.metadata.strategy_name == "noop"
        assert run_data.metadata.dataset_description == "test"


class TestRunDataRoundTrip:
    def test_dict_roundtrip(self) -> None:
        original = make_test_run_data()
        d = run_data_to_dict(original)
        restored = dict_to_run_data(d)

        assert restored.metadata.run_id == original.metadata.run_id
        assert restored.timestamps == original.timestamps
        assert restored.pnl_series == original.pnl_series
        assert restored.final_pnl == original.final_pnl
        assert len(restored.fills) == len(original.fills)
        assert restored.fills[0].symbol == original.fills[0].symbol
