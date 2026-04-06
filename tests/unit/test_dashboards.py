"""Tests for analytics/dashboards.py — report generation."""

from __future__ import annotations

from pathlib import Path

from analytics.dashboards import (
    generate_comparison_report,
    generate_html_report,
    generate_run_report,
)
from tests.conftest import make_test_run_data


class TestGenerateRunReport:
    def test_creates_expected_files(self, tmp_path: Path) -> None:
        rd = make_test_run_data()
        out = generate_run_report(rd, output_dir=tmp_path)
        assert (out / "summary.json").exists()
        assert (out / "equity_curve.png").exists()
        assert (out / "positions.png").exists()
        assert (out / "fills.png").exists()
        assert (out / "drawdown.png").exists()
        assert (out / "dashboard.png").exists()


class TestGenerateHtmlReport:
    def test_creates_html(self, tmp_path: Path) -> None:
        rd = make_test_run_data()
        html_path = generate_html_report(rd, output_dir=tmp_path)
        assert html_path.exists()
        content = html_path.read_text()
        assert "Run Report" in content
        assert rd.metadata.run_id in content
        assert "data:image/png;base64," in content
        assert "total_pnl" in content


class TestGenerateComparisonReport:
    def test_creates_comparison_files(self, tmp_path: Path) -> None:
        rd_a = make_test_run_data(strategy="alpha")
        rd_a.metadata.run_id = "run_alpha"
        rd_b = make_test_run_data(strategy="beta")
        rd_b.metadata.run_id = "run_beta"

        html_path = generate_comparison_report(rd_a, rd_b, output_dir=tmp_path)
        out = html_path.parent
        assert (out / "comparison_summary.json").exists()
        assert (out / "comparison_equity.png").exists()
        assert html_path.exists()

        html = html_path.read_text()
        assert "run_alpha" in html
        assert "run_beta" in html
