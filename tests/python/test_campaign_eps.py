"""L38: campaign summary aggregates sweep coverage + elasticity."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.campaign import run_campaign, summarize_campaign
from orchestrator.metric_store import reset_store


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


def _q_with_sweep(eps_slope: float = -1.0) -> dict:
    xs = [1e30, 1e31, 1e32]
    ys = [(x / 1e30) ** eps_slope for x in xs]
    pts = [{"x": x, "y": y} for x, y in zip(xs, ys)]
    return {
        "verdict": "Hypotheses verified",
        "results": [{
            "success": True,
            "sweep": {"axis_name": "M", "points": pts},
        }],
    }


class TestSummarizeSweepEps:
    def test_empty_has_sweep_fields(self):
        s = summarize_campaign([])
        assert s["n_sweep_questions"] == 0
        assert s["sweep_rate"] == 0.0
        assert s["mean_elasticity"] is None

    def test_aggregates_mean_eps(self):
        qs = [
            _q_with_sweep(-1.0),
            _q_with_sweep(-1.0),
            {"verdict": "All experiments failed"},  # no sweep
        ]
        s = summarize_campaign(qs)
        assert s["n_sweep_questions"] == 2
        assert s["sweep_rate"] == pytest.approx(2 / 3)
        assert s["mean_elasticity"] == pytest.approx(-1.0, rel=1e-6)

    def test_no_sweep_mean_none(self):
        qs = [{"verdict": "Hypotheses verified", "results": []}]
        s = summarize_campaign(qs)
        assert s["n_sweep_questions"] == 0
        assert s["mean_elasticity"] is None

    def test_live_campaign_summary(self):
        out = run_campaign(
            [
                "How does Hawking temperature vary as a function of mass? "
                "Scan several masses.",
            ],
            share_store=True,
        )
        s = out["summary"]
        assert s["n_sweep_questions"] >= 1
        assert s["mean_elasticity"] is not None
        assert s["mean_elasticity"] == pytest.approx(-1.0, rel=0.05)

    def test_report_program_summary_line(self):
        from orchestrator.report import render_campaign

        out = run_campaign(
            [
                "How does Hawking temperature vary as a function of mass? "
                "Scan several masses.",
            ],
            share_store=True,
        )
        md = render_campaign(out)
        assert "sweep" in md.lower()
        assert "ε" in md or "elasticity" in md.lower()
