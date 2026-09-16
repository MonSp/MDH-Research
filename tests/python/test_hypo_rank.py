"""Tests for L5 completion: hypothesis ranking + journal foundations."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.agent_math import rank_hypotheses, score_hypothesis
from orchestrator.metric_store import reset_store
from orchestrator.research_loop import ResearchLoop
from orchestrator.journal import ResearchJournal


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


def _loop() -> ResearchLoop:
    return ResearchLoop(
        journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
        llm_client=False,
    )


class TestScore:
    def test_success_beats_failure(self):
        ok = score_hypothesis({"success": True, "steps": [], "hypothesis": {"prediction": "a"}})
        bad = score_hypothesis({"success": False, "steps": [], "hypothesis": {"prediction": "b"}})
        assert ok["score"] > bad["score"]

    def test_eval_steps_boost(self):
        class E:
            def evaluate(self, p):
                return 0.0

        r = {
            "success": True,
            "steps": [{"tool": "x", "result": E()}],
            "hypothesis": {"prediction": "p"},
        }
        s = score_hypothesis(r)
        assert s["n_eval_steps"] == 1
        assert s["score"] >= 3.0

    def test_replan_penalty(self):
        a = score_hypothesis({"success": True, "steps": [], "hypothesis": {"prediction": "a"}})
        b = score_hypothesis({
            "success": True, "steps": [], "replan": "REPLAN(x)",
            "hypothesis": {"prediction": "b"},
        })
        assert b["score"] < a["score"]

    def test_sweep_certainty_boost(self):
        r = {
            "success": True,
            "steps": [],
            "sweep": {"trend": {"n": 3, "y_min": 1, "y_max": 8,
                                 "direction": "increasing", "spearman_rho": 1.0}},
            "hypothesis": {"prediction": "s"},
        }
        s = score_hypothesis(r)
        assert s["has_sweep"] is True
        assert s["score"] >= 3.0


class TestRank:
    def test_sorts_best_first(self):
        results = [
            {"success": False, "steps": [], "hypothesis": {"prediction": "fail"}},
            {
                "success": True,
                "steps": [{"tool": "create_schwarzschild"},
                          {"tool": "compute_ricci"}],
                "hypothesis": {"prediction": "ok"},
            },
        ]
        ranking = rank_hypotheses(results)
        assert ranking[0]["index"] == 1
        assert ranking[0]["success"] is True
        assert ranking[1]["index"] == 0

    def test_empty(self):
        assert rank_hypotheses([]) == []


class TestLoopIntegration:
    def test_conclusion_has_ranking_and_foundations(self):
        loop = _loop()
        hyps = [
            {
                "prediction": "weak fail",
                "tools": ["not_a_real_tool_xyz"],
                "assumptions": [],
            },
            {
                "prediction": "strong vacuum R=0",
                "tools": [
                    {"tool": "create_schwarzschild", "params": {"M": 1}},
                    {"tool": "compute_scalar_curvature", "params": {}},
                ],
                "assumptions": ["vacuum"],
            },
        ]
        loop._hypothesize_patterns = lambda q: hyps  # type: ignore
        result = loop.run("compare hypotheses")
        c = result["conclusion"]
        assert "foundations" in c and c["foundations"]
        assert "hypothesis_ranking" in c
        assert len(c["hypothesis_ranking"]) == 2
        assert c["best_hypothesis"]["success"] is True
        assert c["best_hypothesis"]["index"] == 1
        assert any("RANK:" in e for e in c["evidence"])

    def test_journal_conclusion_includes_l5(self):
        loop = _loop()
        loop.run("What is the scalar curvature of Schwarzschild spacetime?")
        events = [
            e for e in loop.journal.get_events() if e["type"] == "conclusion"
        ]
        assert events
        payload = events[-1]["payload"]
        assert "foundations" in payload
        assert "hypothesis_ranking" in payload
        assert payload["best_hypothesis"] is not None

    def test_registry_rank_tool(self):
        from orchestrator.tool_registry import execute_tool

        out = execute_tool("rank_hypotheses", {
            "results": [
                {"success": True, "steps": [], "hypothesis": {"prediction": "a"}},
                {"success": False, "steps": [], "hypothesis": {"prediction": "b"}},
            ]
        })
        assert out[0]["success"] is True
