"""Tests for L6 hypothesis competition / regeneration."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.compete import (
    heuristic_alternatives,
    should_compete,
)
from orchestrator.metric_store import reset_store
from orchestrator.research_loop import ResearchLoop
from orchestrator.journal import ResearchJournal


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


def _loop(llm: bool = False) -> ResearchLoop:
    return ResearchLoop(
        journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
        llm_client=llm,
    )


class TestShouldCompete:
    def test_empty(self):
        assert should_compete([]) is True

    def test_all_failed(self):
        assert should_compete([{"success": False}, {"success": False}]) is True

    def test_success_no_ranking(self):
        assert should_compete([{"success": True}]) is False

    def test_low_best_score(self):
        # successful first round does not compete (working path exists)
        results = [{"success": True}]
        ranking = [{"score": 1.0}]
        assert should_compete(results, ranking, score_floor=2.5) is False

    def test_high_best_score(self):
        results = [{"success": True}]
        ranking = [{"score": 4.0}]
        assert should_compete(results, ranking, score_floor=2.5) is False

    def test_all_failed_competes_even_with_ranking(self):
        results = [{"success": False}]
        ranking = [{"score": 0.0}]
        assert should_compete(results, ranking) is True


class TestHeuristicAlts:
    def test_curvature_siblings(self):
        alts = heuristic_alternatives(
            "compute curvature of schwarzschild vacuum",
            results=[],
            limit=3,
        )
        assert alts
        tools = []
        for a in alts:
            tools.extend(s["tool"] for s in a["tools"])
        assert "create_schwarzschild" in tools
        assert any(t.startswith("compute_") for t in tools)

    def test_skips_used_tools(self):
        used = [{
            "success": True,
            "steps": [
                {"tool": "create_schwarzschild"},
                {"tool": "compute_scalar_curvature"},
            ],
        }]
        alts = heuristic_alternatives("curvature vacuum", used, limit=3)
        for a in alts:
            assert all(
                s["tool"] != "compute_scalar_curvature" for s in a["tools"]
            )


class TestCompetitionE2E:
    def test_weak_first_round_triggers_competition(self):
        loop = _loop(llm=False)
        # first round fails (unknown tool); heuristics add Schwarzschild curvature chain
        hyps = [{
            "prediction": "broken first attempt",
            "tools": ["not_a_real_tool_xyz"],
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyps  # type: ignore
        result = loop.run("What is the scalar curvature of Schwarzschild?")
        assert result["conclusion"].get("competed") is True
        # competition should have succeeded
        assert result["conclusion"]["verdict"] == "Hypotheses verified"
        rounds = [
            r.get("round") for r in result["results"]
            if r.get("round") == "competition"
        ]
        assert rounds
        # ranking includes both first-round fail and competition success
        assert len(result["conclusion"]["hypothesis_ranking"]) >= 2
        assert result["conclusion"]["best_hypothesis"]["success"] is True

    def test_strong_first_round_skips_competition(self):
        loop = _loop(llm=False)
        hyps = [{
            "prediction": "R = 0 vacuum",
            "tools": [
                {"tool": "create_schwarzschild", "params": {"M": 1}},
                {"tool": "compute_scalar_curvature", "params": {}},
            ],
            "assumptions": ["vacuum"],
        }]
        loop._hypothesize_patterns = lambda q: hyps  # type: ignore
        result = loop.run("schwarzschild scalar curvature vacuum")
        # first round is strong (success + eval steps → score >= 3) so no compete
        assert result["conclusion"].get("competed") is False
        assert not any(
            r.get("round") == "competition" for r in result["results"]
        )

    def test_journal_records_compete(self):
        loop = _loop(llm=False)
        hyps = [{
            "prediction": "broken",
            "tools": ["not_a_real_tool_xyz"],
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyps  # type: ignore
        loop.run("schwarzschild vacuum curvature")
        notes = [
            e for e in loop.journal.get_events() if e["type"] == "note"
        ]
        assert any("COMPETE" in str(n.get("payload", {})) for n in notes)

    def test_conclusion_extra_has_competed_flag(self):
        loop = _loop(llm=False)
        hyps = [{
            "prediction": "broken",
            "tools": ["not_a_real_tool_xyz"],
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyps  # type: ignore
        loop.run("kerr vacuum curvature")
        events = [e for e in loop.journal.get_events() if e["type"] == "conclusion"]
        assert events
        assert "competed" in events[-1]["payload"]
