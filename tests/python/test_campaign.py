"""Tests for L9 research campaign."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.campaign import run_campaign, summarize_campaign
from orchestrator.metric_store import get_store, reset_store
from orchestrator.research_loop import ResearchLoop
from orchestrator.journal import ResearchJournal


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


def _factory():
    def _mk():
        return ResearchLoop(
            journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
            llm_client=False,
        )
    return _mk


class TestSummarize:
    def test_empty(self):
        s = summarize_campaign([])
        assert s["n_questions"] == 0
        assert s["verify_rate"] == 0.0

    def test_rates(self):
        qs = [
            {"verdict": "Hypotheses verified", "hypothesis_ranking": [{"score": 3.0}],
             "known_value_checks": {"n_passed": 1, "n_checks": 1}},
            {"verdict": "All experiments failed", "hypothesis_ranking": [{"score": 0.0}],
             "known_value_checks": {"n_passed": 0, "n_checks": 0}},
        ]
        s = summarize_campaign(qs)
        assert s["n_questions"] == 2
        assert s["n_verified"] == 1
        assert s["verify_rate"] == pytest.approx(0.5)
        assert s["known_value_rate"] == pytest.approx(1.0)


class TestCampaignE2E:
    def test_two_questions_share_store(self):
        out = run_campaign(
            [
                "What is the scalar curvature of Schwarzschild spacetime?",
                "What is the age of the universe?",
            ],
            loop_factory=_factory(),
            share_store=True,
        )
        s = out["summary"]
        assert s["n_questions"] == 2
        assert s["n_verified"] >= 1
        assert len(out["questions"]) == 2
        assert out["journal_summary"]["total_events"] > 0

    def test_stop_on_verified(self):
        out = run_campaign(
            [
                "What is the scalar curvature of Schwarzschild spacetime?",
                "What is the age of the universe?",  # skipped if early stop
            ],
            loop_factory=_factory(),
            stop_on_verified=True,
        )
        # first should verify; second may be skipped
        assert out["summary"]["n_verified"] >= 1
        assert out["summary"]["n_questions"] >= 1

    def test_store_growth_recorded(self):
        out = run_campaign(
            ["What is the scalar curvature of Schwarzschild spacetime?"],
            loop_factory=_factory(),
        )
        assert "store_growth" in out["summary"]
        assert out["summary"]["store_growth"] >= 1
        assert "schwarzschild" in get_store().list()

    def test_fresh_store_per_campaign(self):
        out = run_campaign(
            ["What is the age of the universe?"],
            loop_factory=_factory(),
            share_store=False,
        )
        assert out["summary"]["n_questions"] == 1
