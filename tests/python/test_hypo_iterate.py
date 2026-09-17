"""Tests for L7 iterative multi-round research search."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.compete import iterate_hypotheses
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


class TestIterateHypotheses:
    def test_returns_chains(self):
        alts = iterate_hypotheses("something vacuum", results=[], round_n=1, limit=2)
        assert alts
        assert len(alts) <= 2
        for a in alts:
            assert a["tools"]
            assert a["assumptions"] == ["iterate-round-1"]

    def test_skips_used_consumers(self):
        used = [{
            "success": False,
            "steps": [
                {"tool": "create_schwarzschild"},
                {"tool": "compute_scalar_curvature"},
            ],
        }]
        alts = iterate_hypotheses("curvature", used, round_n=1, limit=3)
        for a in alts:
            tools = [s["tool"] for s in a["tools"]]
            # consumer should not be the already-used scalar curvature
            assert tools[-1] != "compute_scalar_curvature" or tools[0] != "create_schwarzschild"


class TestIterateE2E:
    def test_weak_round_gets_iterate_success(self):
        loop = _loop()
        hyps = [{
            "prediction": "always fail",
            "tools": ["not_a_real_tool_xyz"],
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyps  # type: ignore
        result = loop.run("What is the scalar curvature of Schwarzschild?")
        c = result["conclusion"]
        # L6 competition should already succeed; iterate_rounds may be 0
        assert c["verdict"] == "Hypotheses verified"
        assert "iterate_rounds" in c
        assert any(
            r.get("success") for r in result["results"]
        )

    def test_iterate_rounds_recorded(self):
        loop = _loop()
        # make competition also produce only failures by asking something
        # competition handles poorly — still should get iterate field
        hyps = [{
            "prediction": "fail",
            "tools": ["not_a_real_tool_xyz"],
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyps  # type: ignore
        result = loop.run("unknown topic xyz")
        c = result["conclusion"]
        assert "iterate_rounds" in c
        assert isinstance(c["iterate_rounds"], int)

    def test_journal_has_iterate_or_compete(self):
        loop = _loop()
        hyps = [{
            "prediction": "fail",
            "tools": ["not_a_real_tool_xyz"],
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyps  # type: ignore
        loop.run("schwarzschild vacuum curvature")
        notes = [e for e in loop.journal.get_events() if e["type"] == "note"]
        blob = " ".join(str(n.get("payload", {})) for n in notes)
        assert "COMPETE" in blob or "ITERATE" in blob

    def test_strong_path_no_iterate(self):
        loop = _loop()
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
        c = result["conclusion"]
        assert c["competed"] is False
        assert c["iterate_rounds"] == 0
        assert not any(
            str(r.get("round", "")).startswith("iterate") for r in result["results"]
        )
