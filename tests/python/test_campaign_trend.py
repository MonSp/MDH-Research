"""Tests for L20 campaign trend aggregation."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.cli import main
from orchestrator.trend import (
    aggregate_campaigns,
    compute_trend,
    load_campaign_summaries,
    render_trend,
)


def _write_campaign(path, verify_rate, n_verified=1, n_questions=2, kv_rate=1.0, score=3.0):
    data = {
        "summary": {
            "n_questions": n_questions,
            "n_verified": n_verified,
            "verify_rate": verify_rate,
            "known_value_passed": 1,
            "known_value_total": 1,
            "known_value_rate": kv_rate,
            "mean_best_score": score,
            "n_competed": 0,
            "n_iterated": 0,
        },
        "questions": [{"index": 0, "verdict": "Hypotheses verified"}],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


class TestLoadAndTrend:
    def test_empty(self, tmp_path):
        assert load_campaign_summaries(str(tmp_path)) == []
        t = compute_trend([])
        assert t["n_files"] == 0

    def test_load_dir(self, tmp_path):
        _write_campaign(tmp_path / "a.json", 0.5)
        _write_campaign(tmp_path / "b.json", 1.0)
        summaries = load_campaign_summaries(str(tmp_path))
        assert len(summaries) == 2
        assert summaries[0]["_source_name"] == "a.json"

    def test_improved_trend(self, tmp_path):
        _write_campaign(tmp_path / "run1.json", 0.5, n_verified=1)
        _write_campaign(tmp_path / "run2.json", 1.0, n_verified=2)
        out = aggregate_campaigns(str(tmp_path))
        assert out["n_files"] == 2
        assert out["verify_rate_improved"] is True
        assert out["delta"]["verify_rate"]["delta"] == pytest.approx(0.5)
        md = render_trend(out)
        assert "improved" in md
        assert "verify_rate" in md

    def test_declined_trend(self, tmp_path):
        _write_campaign(tmp_path / "x.json", 1.0)
        _write_campaign(tmp_path / "y.json", 0.0)
        out = aggregate_campaigns(str(tmp_path))
        assert out["verify_rate_improved"] is False

    def test_single_file(self, tmp_path):
        p = tmp_path / "one.json"
        _write_campaign(p, 0.75)
        out = aggregate_campaigns(str(p))
        assert out["n_files"] == 1
        assert out["delta"]["verify_rate"]["first"] == pytest.approx(0.75)

    def test_cli_trend(self, tmp_path, capsys):
        _write_campaign(tmp_path / "t1.json", 0.4)
        _write_campaign(tmp_path / "t2.json", 0.9)
        code = main(["trend", str(tmp_path), "--json"])
        assert code == 0
        data = json.loads(capsys.readouterr().out)
        assert data["verify_rate_improved"] is True
