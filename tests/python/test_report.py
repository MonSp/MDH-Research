"""Tests for L10 research report synthesis."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.campaign import run_campaign
from orchestrator.metric_store import reset_store
from orchestrator.report import render_campaign, render_single_run, write_report
from orchestrator.research_loop import ResearchLoop
from orchestrator.journal import ResearchJournal


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


def _loop():
    return ResearchLoop(
        journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
        llm_client=False,
    )


class TestRenderSingle:
    def test_contains_verdict_and_evidence(self):
        result = {
            "question": "What is R?",
            "conclusion": {
                "verdict": "Hypotheses verified",
                "evidence": ["CONFIRMED: R=0"],
                "verification": {"numeric_confirmed": 1, "symbolic_confirmed": 0,
                                  "residual_gates": [{"metric_name": "schwarzschild",
                                                      "passed": True, "max_abs": 1e-16}]},
                "foundations": {"n_steps": 2, "unique_tools": 2,
                                "tool_entropy_bits": 1.0, "success_rate": 1.0},
                "hypothesis_ranking": [{"score": 3.0, "success": True,
                                        "prediction": "R=0"}],
                "known_value_checks": {"n_checks": 0, "n_passed": 0},
            },
        }
        md = render_single_run(result)
        assert "Hypotheses verified" in md
        assert "CONFIRMED" in md
        assert "residual gate" in md
        assert "Hypothesis ranking" in md
        assert "R=0" in md

    def test_empty_conclusion(self):
        md = render_single_run({"question": "q", "conclusion": {}})
        assert "Question" in md
        assert "n/a" in md or "Verdict" in md


class TestRenderCampaign:
    def test_campaign_report_from_live_run(self):
        out = run_campaign(
            [
                "What is the scalar curvature of Schwarzschild spacetime?",
                "What is the age of the universe?",
            ],
            loop_factory=_loop,
            share_store=True,
        )
        md = render_campaign(out)
        assert md.startswith("# Research Campaign Report")
        assert "Program summary" in md
        assert "Questions" in md
        assert "Schwarzschild" in md or "curvature" in md
        assert "verify_rate" in md

    def test_write_report(self, tmp_path):
        out = run_campaign(
            ["What is the scalar curvature of Schwarzschild spacetime?"],
            loop_factory=_loop,
        )
        md = render_campaign(out)
        path = str(tmp_path / "report.md")
        write_report(md, path)
        assert os.path.isfile(path)
        text = open(path, encoding="utf-8").read()
        assert "Research Campaign Report" in text

    def test_live_single_run_render(self):
        result = _loop().run("What is the Hawking temperature of a black hole?")
        md = render_single_run(result)
        assert "Question" in md
        assert "Verdict" in md
