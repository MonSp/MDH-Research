"""Tests for ResearchLoop sequential chain execution."""

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
from orchestrator.research_loop import (
    ChainStep,
    ResearchLoop,
    _inject_context,
    _steps_from_hypothesis,
    _tool_needs_metric,
)
from orchestrator.journal import ResearchJournal


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


def _loop() -> ResearchLoop:
    # Disable LLM so pattern path is deterministic even when LLM_API_KEY is set
    return ResearchLoop(
        journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
        llm_client=False,
    )


class TestStepsFromHypothesis:
    def test_legacy_single(self):
        steps = _steps_from_hypothesis({
            "tool": "hawking_temperature",
            "params": {"M": 1e30},
        })
        assert len(steps) == 1
        assert steps[0].tool == "hawking_temperature"
        assert steps[0].params["M"] == 1e30

    def test_tools_dict_chain(self):
        steps = _steps_from_hypothesis({
            "tools": [
                {"tool": "create_kerr", "params": {"M": 1, "a": 0.5}},
                {"tool": "compute_scalar_curvature", "params": {}},
            ],
        })
        assert [s.tool for s in steps] == ["create_kerr", "compute_scalar_curvature"]
        assert steps[0].params["a"] == 0.5

    def test_tools_string_shorthand(self):
        steps = _steps_from_hypothesis({
            "tools": ["hawking_temperature", "evaporation_time"],
        })
        assert [s.tool for s in steps] == ["hawking_temperature", "evaporation_time"]
        assert steps[0].params == {}

    def test_mixed(self):
        steps = _steps_from_hypothesis({
            "tools": [
                {"tool": "create_schwarzschild", "params": {"M": 2}},
                "classify_symmetry",
            ],
        })
        assert steps[1].tool == "classify_symmetry"

    def test_missing_raises(self):
        with pytest.raises(ValueError):
            _steps_from_hypothesis({"prediction": "x"})


class TestInjectContext:
    def test_needs_metric(self):
        assert _tool_needs_metric("compute_scalar_curvature") is True
        assert _tool_needs_metric("classify_symmetry") is True
        assert _tool_needs_metric("hawking_temperature") is False
        assert _tool_needs_metric("create_schwarzschild") is False

    def test_injects_metric_name(self):
        out = _inject_context({}, {"metric_name": "schwarzschild"}, "compute_kretschmann")
        assert out["metric_name"] == "schwarzschild"

    def test_does_not_override_explicit(self):
        out = _inject_context(
            {"metric_name": "other"}, {"metric_name": "schwarzschild"}, "compute_kretschmann"
        )
        assert out["metric_name"] == "other"

    def test_does_not_inject_when_diagonal_present(self):
        out = _inject_context(
            {"diagonal": ["-1", "1"], "coords": ["t", "x"]},
            {"metric_name": "schwarzschild"},
            "compute_scalar_curvature",
        )
        assert "metric_name" not in out

    def test_no_inject_for_scalars(self):
        out = _inject_context({}, {"metric_name": "schwarzschild"}, "hawking_temperature")
        assert "metric_name" not in out


class TestChainExecution:
    def test_factory_then_consumer(self):
        loop = _loop()
        result = loop.run("What is the scalar curvature of Schwarzschild spacetime?")
        assert result["conclusion"]["verdict"] == "Hypotheses verified"
        r0 = result["results"][0]
        assert r0["success"] is True
        tools = [s["tool"] for s in r0["steps"]]
        assert tools == ["create_schwarzschild", "compute_scalar_curvature"]
        # second step received injected metric_name
        assert r0["steps"][1]["params"].get("metric_name") == "schwarzschild"

    def test_kretschmann_chain(self):
        loop = _loop()
        result = loop.run("Compute the Kretschmann scalar of Schwarzschild")
        r0 = result["results"][0]
        tools = [s["tool"] for s in r0["steps"]]
        assert tools == ["create_schwarzschild", "compute_kretschmann"]

    def test_scalar_chain_no_injection(self):
        loop = _loop()
        steps = _steps_from_hypothesis({
            "tools": [
                {"tool": "hawking_temperature", "params": {"M": 1.989e30}},
                {"tool": "evaporation_time", "params": {"M": 1.989e30}},
            ],
        })
        out = loop._execute_chain(steps)
        assert len(out) == 2
        assert "metric_name" not in out[1]["params"]
        assert "result" in out[0] and "result" in out[1]

    def test_missing_metric_fails_cleanly(self):
        loop = _loop()
        steps = [ChainStep(tool="compute_scalar_curvature", params={})]
        with pytest.raises(RuntimeError, match="needs a metric"):
            loop._execute_chain(steps)

    def test_mid_chain_failure_stops(self):
        loop = _loop()
        steps = [
            ChainStep(tool="create_schwarzschild", params={"M": 1}),
            ChainStep(tool="not_a_real_tool_xyz", params={}),
            ChainStep(tool="compute_scalar_curvature", params={}),
        ]
        with pytest.raises(Exception) as ei:
            loop._execute_chain(steps)
        partial = getattr(ei.value, "partial_steps", [])
        assert len(partial) == 2  # first succeeded, second failed, third never ran
        assert partial[0].get("result") is not None or "result" in partial[0]
        assert "error" in partial[1]

    def test_symmetry_pattern_chain(self):
        loop = _loop()
        result = loop.run("Classify the Killing symmetries of Schwarzschild")
        r0 = result["results"][0]
        tools = [s["tool"] for s in r0["steps"]]
        assert tools == ["create_schwarzschild", "classify_symmetry"]
        assert r0["success"] is True

    def test_hawking_evaporation_pattern_chain(self):
        """Regression: pattern chain must pass required M (schema defaults are not applied)."""
        loop = _loop()
        result = loop.run(
            "What is the Hawking temperature and evaporation time of a black hole?"
        )
        r0 = result["results"][0]
        assert r0["success"] is True, r0.get("error")
        tools = [s["tool"] for s in r0["steps"]]
        assert tools == ["hawking_temperature", "evaporation_time"]
        assert r0["steps"][0]["params"].get("M") == pytest.approx(1.989e30)
        assert r0["steps"][1]["params"].get("M") == pytest.approx(1.989e30)

    def test_evaporation_only_pattern_reaches_hawking_chain(self):
        loop = _loop()
        result = loop.run("What is the evaporation time of a solar mass black hole?")
        r0 = result["results"][0]
        assert r0["success"] is True, r0.get("error")
        tools = [s["tool"] for s in r0["steps"]]
        assert "evaporation_time" in tools

    def test_run_level_error_journal(self):
        loop = _loop()
        # force a chain that needs a metric without providing one
        monkey_hyp = [{
            "prediction": "should fail",
            "tools": ["compute_scalar_curvature"],
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: monkey_hyp  # type: ignore
        result = loop.run("force fail")
        assert result["results"][0]["success"] is False
        events = loop.journal.get_events()
        types = [e["type"] for e in events]
        assert "error" in types

    def test_journal_has_tool_calls_per_step(self):
        loop = _loop()
        loop.run("What is the scalar curvature of Schwarzschild spacetime?")
        events = loop.journal.get_events()
        types = [e["type"] for e in events]
        assert types.count("tool_call") >= 2


class TestMockLLMChain:
    def test_llm_tools_array_end_to_end(self, monkeypatch):
        loop = ResearchLoop(
            journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
            llm_client=True,
        )

        def fake_hypothesize_llm(question):
            return [{
                "prediction": "Kerr vacuum so R=0",
                "tools": [
                    {"tool": "create_kerr", "params": {"M": 1, "a": 0.3}},
                    {"tool": "compute_scalar_curvature", "params": {}},
                ],
                "assumptions": ["Kerr"],
            }]

        monkeypatch.setattr(loop, "_hypothesize_llm", fake_hypothesize_llm)
        result = loop.run("Is Kerr Ricci-flat?")
        r0 = result["results"][0]
        assert r0["success"] is True
        assert [s["tool"] for s in r0["steps"]] == [
            "create_kerr", "compute_scalar_curvature"
        ]
        assert result["conclusion"]["verdict"] == "Hypotheses verified"
