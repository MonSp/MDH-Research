"""Tests for L4c failure replanning."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.metric_store import reset_store
from orchestrator.replan import diagnose_failure, heuristic_repair
from orchestrator.research_loop import ChainStep, ResearchLoop
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


class TestDiagnose:
    def test_missing_metric(self):
        d = diagnose_failure(
            "step 0 (compute_ricci) needs a metric but none provided and chain context has no metric_name",
            [{"tool": "compute_ricci", "error": "needs a metric"}],
        )
        assert d["kind"] == "missing_metric"
        assert d["tool"] == "compute_ricci"

    def test_unknown_tool(self):
        d = diagnose_failure("Unknown tool: foo", [{"tool": "foo", "error": "Unknown tool: foo"}])
        assert d["kind"] == "unknown_tool"

    def test_missing_param(self):
        d = diagnose_failure(
            "step 0 (hawking_temperature) failed: hawking_temperature() missing 1 required positional argument: 'M'",
            [{"tool": "hawking_temperature", "error": "missing 1 required positional argument: 'M'"}],
        )
        assert d["kind"] == "missing_param"
        assert d["tool"] == "hawking_temperature"

    def test_bad_kwarg(self):
        d = diagnose_failure(
            "step 0 (age_of_universe) failed: unexpected keyword argument 'foo'",
            [{"tool": "age_of_universe", "error": "unexpected keyword argument 'foo'"}],
        )
        assert d["kind"] == "bad_kwarg"


class TestHeuristicRepair:
    def test_prepend_factory_for_missing_metric(self):
        steps = [ChainStep("compute_ricci", {})]
        d = diagnose_failure(
            "needs a metric but none provided",
            [{"tool": "compute_ricci", "error": "needs a metric"}],
        )
        fixed = heuristic_repair(steps, d, question="kerr vacuum")
        assert fixed is not None
        assert fixed[0].tool == "create_kerr"
        assert fixed[1].tool == "compute_ricci"

    def test_minkowski_diagonal_inject(self):
        steps = [ChainStep("compute_scalar_curvature", {})]
        d = diagnose_failure("needs a metric but none provided", [{"tool": "compute_scalar_curvature"}])
        fixed = heuristic_repair(steps, d, question="flat minkowski curvature")
        assert fixed is not None
        assert fixed[0].params.get("diagonal") == ["-1", "1", "1", "1"]

    def test_fill_hawking_M(self):
        steps = [ChainStep("hawking_temperature", {})]
        d = diagnose_failure(
            "hawking_temperature() missing 1 required positional argument: 'M'",
            [{"tool": "hawking_temperature", "error": "missing ... 'M'"}],
        )
        fixed = heuristic_repair(steps, d)
        assert fixed is not None
        assert fixed[0].params["M"] == pytest.approx(1.989e30)

    def test_strip_bad_kwarg(self):
        steps = [ChainStep("age_of_universe", {"params": {}, "foo": 1})]
        d = diagnose_failure(
            "unexpected keyword argument 'foo'",
            [{"tool": "age_of_universe", "error": "unexpected keyword argument 'foo'"}],
        )
        fixed = heuristic_repair(steps, d)
        assert fixed is not None
        assert "foo" not in fixed[0].params

    def test_synonym_unknown_tool(self):
        steps = [ChainStep("compute_scalar", {"diagonal": ["-1", "1"], "coords": ["t", "x"]})]
        d = diagnose_failure("Unknown tool: compute_scalar", [{"tool": "compute_scalar"}])
        fixed = heuristic_repair(steps, d)
        assert fixed is not None
        assert fixed[0].tool == "compute_scalar_curvature"

    def test_fill_multiple_missing_args(self):
        steps = [ChainStep("chirp_mass", {})]
        d = diagnose_failure(
            "chirp_mass() missing 2 required positional arguments: 'm1' and 'm2'",
            [{"tool": "chirp_mass",
              "error": "missing 2 required positional arguments: 'm1' and 'm2'"}],
        )
        fixed = heuristic_repair(steps, d)
        assert fixed is not None
        assert fixed[0].params["m1"] == 30.0
        assert fixed[0].params["m2"] == 30.0


class TestReplanE2E:
    def test_missing_metric_chain_auto_repaired(self):
        loop = _loop()
        hyp = [{
            "prediction": "Ricci of Schwarzschild should vanish",
            "tools": [{"tool": "compute_ricci", "params": {}}],
            "assumptions": ["vacuum"],
        }]
        loop._hypothesize_patterns = lambda q: hyp  # type: ignore
        result = loop.run("schwarzschild vacuum ricci")
        r0 = result["results"][0]
        assert r0["success"] is True, r0.get("error")
        assert "replan" in r0
        tools = [s["tool"] for s in r0["steps"]]
        assert tools[0] == "create_schwarzschild"
        assert "compute_ricci" in tools

    def test_hawking_missing_M_repaired(self):
        loop = _loop()
        hyp = [{
            "prediction": "Hawking T",
            "tools": ["hawking_temperature"],
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyp  # type: ignore
        result = loop.run("hawking temperature")
        r0 = result["results"][0]
        assert r0["success"] is True, r0.get("error")
        assert r0["steps"][0]["params"]["M"] == pytest.approx(1.989e30)

    def test_journal_records_replan_note(self):
        loop = _loop()
        hyp = [{
            "prediction": "Ricci",
            "tools": [{"tool": "compute_ricci", "params": {}}],
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyp  # type: ignore
        loop.run("schwarzschild vacuum")
        notes = [
            e for e in loop.journal.get_events()
            if e["type"] == "note"
        ]
        assert any("REPLAN" in str(n.get("payload", {})) for n in notes)

    def test_irreparable_still_fails(self):
        loop = _loop()
        hyp = [{
            "prediction": "bad",
            "tools": [{"tool": "not_a_real_tool_xyz", "params": {}}],
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyp  # type: ignore
        result = loop.run("whatever")
        assert result["results"][0]["success"] is False

    def test_no_replan_when_already_has_factory(self):
        from orchestrator.replan import heuristic_repair
        steps = [
            ChainStep("create_schwarzschild", {"M": 1}),
            ChainStep("compute_ricci", {}),
        ]
        d = {"kind": "missing_metric", "tool": "compute_ricci", "error": "needs a metric"}
        assert heuristic_repair(steps, d, question="schwarzschild") is None
