"""L33: campaign keeps sweep/grid results for report viz + CSV export."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.campaign import run_campaign
from orchestrator.metric_store import reset_store


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


SWEEP_Q = (
    "How does Hawking temperature vary as a function of mass? "
    "Scan several masses."
)


class TestCampaignKeepsSweepResults:
    def test_question_has_sweep_results(self):
        out = run_campaign([SWEEP_Q], share_store=True)
        q = out["questions"][0]
        results = q.get("results")
        assert results, "campaign question must carry results"
        assert any(r.get("sweep") for r in results), results
        pts = next(r["sweep"]["points"] for r in results if r.get("sweep"))
        assert len(pts) >= 2

    def test_campaign_report_includes_viz(self):
        from orchestrator.report import render_campaign

        out = run_campaign([SWEEP_Q], share_store=True)
        md = render_campaign(out)
        assert "Sensitivity" in md or "Sweep viz" in md

    def test_campaign_export_csv(self, tmp_path):
        from orchestrator.sweep_viz import export_run_csv

        out = run_campaign([SWEEP_Q], share_store=True)
        path = str(tmp_path / "c.csv")
        # export per-question results the same way as a run
        merged = {"results": []}
        for q in out["questions"]:
            merged["results"].extend(q.get("results") or [])
        got = export_run_csv(merged, path)
        assert got == path
        lines = open(path, encoding="utf-8").read().splitlines()
        assert lines[0] == "x,y"
        assert len(lines) >= 2
