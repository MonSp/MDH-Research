"""L39: cross-campaign trend tracks sweep rate + mean elasticity."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.trend import aggregate_campaigns, compute_trend, render_trend


def _write_campaign(path, *, sweep_rate, mean_eps, verify_rate=1.0):
    data = {
        "summary": {
            "n_questions": 2,
            "n_verified": 2,
            "verify_rate": verify_rate,
            "known_value_passed": 1,
            "known_value_total": 1,
            "known_value_rate": 1.0,
            "mean_best_score": 3.0,
            "n_competed": 0,
            "n_iterated": 0,
            "n_sweep_questions": int(round(sweep_rate * 2)),
            "sweep_rate": sweep_rate,
            "mean_elasticity": mean_eps,
        },
        "questions": [],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


class TestTrendEps:
    def test_empty_has_no_eps(self):
        t = compute_trend([])
        assert t["n_files"] == 0

    def test_delta_includes_sweep_and_eps(self, tmp_path):
        _write_campaign(tmp_path / "a.json", sweep_rate=0.5, mean_eps=-0.5)
        _write_campaign(tmp_path / "b.json", sweep_rate=1.0, mean_eps=-1.0)
        t = aggregate_campaigns(str(tmp_path))
        assert t["delta"]["sweep_rate"]["first"] == pytest.approx(0.5)
        assert t["delta"]["sweep_rate"]["last"] == pytest.approx(1.0)
        assert t["delta"]["mean_elasticity"]["first"] == pytest.approx(-0.5)
        assert t["delta"]["mean_elasticity"]["last"] == pytest.approx(-1.0)
        assert t["delta"]["mean_elasticity"]["delta"] == pytest.approx(-0.5)

    def test_series_carries_eps(self, tmp_path):
        _write_campaign(tmp_path / "a.json", sweep_rate=0.0, mean_eps=None)
        _write_campaign(tmp_path / "b.json", sweep_rate=1.0, mean_eps=-1.0)
        t = aggregate_campaigns(str(tmp_path))
        assert t["series"][0]["sweep_rate"] == pytest.approx(0.0)
        assert t["series"][0]["mean_elasticity"] is None
        assert t["series"][1]["mean_elasticity"] == pytest.approx(-1.0)

    def test_render_includes_eps(self, tmp_path):
        _write_campaign(tmp_path / "a.json", sweep_rate=0.5, mean_eps=-0.5)
        _write_campaign(tmp_path / "b.json", sweep_rate=1.0, mean_eps=-1.0)
        t = aggregate_campaigns(str(tmp_path))
        md = render_trend(t)
        assert "mean_elasticity" in md
        assert "sweep_rate" in md

    def test_missing_eps_omitted_from_delta(self, tmp_path):
        _write_campaign(tmp_path / "a.json", sweep_rate=0.5, mean_eps=None)
        _write_campaign(tmp_path / "b.json", sweep_rate=1.0, mean_eps=-1.0)
        t = aggregate_campaigns(str(tmp_path))
        # first has None → not both present → no delta entry
        assert "mean_elasticity" not in t["delta"]
        assert t["series"][1]["mean_elasticity"] == pytest.approx(-1.0)
