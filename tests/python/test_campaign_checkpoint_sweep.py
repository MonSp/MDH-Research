"""L41: campaign checkpoints keep slim question sweep/grid results."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.checkpoint import (
    checkpoint_to_run_result,
    load_checkpoint,
    save_checkpoint,
)
from orchestrator.metric_store import reset_store


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


CAMPAIGN = {
    "summary": {"n_questions": 1, "n_verified": 1, "verify_rate": 1.0},
    "questions": [{
        "index": 0,
        "question": (
            "How does Hawking temperature vary as a function of mass? "
            "Scan several masses."
        ),
        "verdict": "Hypotheses verified",
        "results": [{
            "success": True,
            "sweep": {
                "axis_name": "M",
                "points": [
                    {"x": 1e30, "y": 1e-8},
                    {"x": 1e31, "y": 1e-9},
                ],
                "trend": {
                    "direction": "decreasing", "n": 2,
                    "points": [
                        {"x": 1e30, "y": 1e-8},
                        {"x": 1e31, "y": 1e-9},
                    ],
                },
            },
        }],
    }],
}


class TestCampaignCheckpointSweep:
    def test_saves_question_slim_results(self, tmp_path):
        p = save_checkpoint(
            CAMPAIGN, path=str(tmp_path / "c.json"),
            label="camp", kind="campaign",
        )
        ckpt = load_checkpoint(p)
        assert ckpt["kind"] == "campaign"
        qs = ckpt.get("questions")
        assert qs, "campaign checkpoint must keep questions"
        results = qs[0].get("results")
        assert results and results[0].get("sweep")
        # slim: no step traces
        assert all("steps" not in r for r in results)

    def test_pseudo_campaign_renders_viz(self, tmp_path):
        from orchestrator.report import render_campaign

        p = save_checkpoint(
            CAMPAIGN, path=str(tmp_path / "c.json"), kind="campaign",
        )
        ckpt = load_checkpoint(p)
        pseudo = checkpoint_to_run_result(ckpt)
        assert pseudo.get("questions")
        assert pseudo["questions"][0].get("results")
        md = render_campaign(pseudo)
        assert "Sweep viz" in md or "Sensitivity" in md

    def test_pseudo_campaign_export_csv(self, tmp_path):
        from orchestrator.sweep_viz import export_run_csv

        p = save_checkpoint(
            CAMPAIGN, path=str(tmp_path / "c.json"), kind="campaign",
        )
        ckpt = load_checkpoint(p)
        pseudo = checkpoint_to_run_result(ckpt)
        merged = {"results": []}
        for q in pseudo.get("questions") or []:
            merged["results"].extend(q.get("results") or [])
        out = str(tmp_path / "x.csv")
        got = export_run_csv(merged, out)
        assert got == out
        lines = open(out, encoding="utf-8").read().splitlines()
        assert lines[0] == "x,y"

    def test_campaign_without_sweep_still_ok(self, tmp_path):
        camp = {
            "summary": {"n_questions": 1},
            "questions": [{
                "index": 0,
                "question": "What is R?",
                "verdict": "Hypotheses verified",
                "results": [{"success": True}],
            }],
        }
        p = save_checkpoint(camp, path=str(tmp_path / "n.json"), kind="campaign")
        ckpt = load_checkpoint(p)
        results = ckpt["questions"][0].get("results")
        # non-sweep results dropped (slim only)
        assert results in (None, [])
