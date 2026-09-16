"""Tests for L5 agent mathematical foundations."""

from __future__ import annotations

import math
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.agent_math import (
    decision_pressure,
    shannon_entropy,
    state_distance,
    sweep_information,
    tool_sequence_from_steps,
    trajectory_metrics,
    summarize_run,
)
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


class TestEntropy:
    def test_uniform_two(self):
        assert shannon_entropy([1, 1]) == pytest.approx(1.0)

    def test_deterministic(self):
        assert shannon_entropy([5]) == pytest.approx(0.0)

    def test_dict(self):
        assert shannon_entropy({"a": 3, "b": 1}) > 0


class TestTrajectory:
    def test_basic(self):
        m = trajectory_metrics(
            ["create_schwarzschild", "compute_ricci", "create_schwarzschild"],
            n_success=1, n_fail=0, n_replans=1,
        )
        assert m["n_steps"] == 3
        assert m["unique_tools"] == 2
        assert m["max_tool_count"] == 2
        assert m["n_replans"] == 1
        assert 0 < m["tool_entropy_bits"] <= math.log2(3)

    def test_tool_seq_from_steps(self):
        seq = tool_sequence_from_steps([
            {"tool": "a", "result": 1},
            {"tool": "b"},
        ])
        assert seq == ["a", "b"]

    def test_decision_pressure(self):
        p = decision_pressure(80, 2)
        assert p == pytest.approx(math.log2(40))


class TestStateDistance:
    def test_identical(self):
        s = {"m": {"coord_names": ["t", "r"], "params": {"M": 1.0}}}
        assert state_distance(s, s) == pytest.approx(0.0)

    def test_param_delta(self):
        s1 = {"m": {"coord_names": ["t", "r"], "params": {"M": 1.0}}}
        s2 = {"m": {"coord_names": ["t", "r"], "params": {"M": 2.0}}}
        assert state_distance(s1, s2) > 0

    def test_missing_metric(self):
        s1 = {"a": {"params": {}}}
        s2 = {"b": {"params": {}}}
        assert state_distance(s1, s2) >= 1.0


class TestSweepInformation:
    def test_1_over_m(self):
        trend = {
            "n": 3, "y_min": 1e-9, "y_max": 1e-7,
            "direction": "decreasing", "spearman_rho": -1.0,
            "log_log_slope": -1.0,
        }
        info = sweep_information(trend)
        assert info["trend_certainty"] == pytest.approx(1.0)
        assert info["power_law"] is True
        assert info["y_spread_bits"] > 1.0

    def test_empty(self):
        assert sweep_information({"n": 0})["power_law"] is False


class TestSummarizeAndLoop:
    def test_summarize_run(self):
        results = [
            {
                "success": True,
                "replan": "REPLAN(x)",
                "steps": [
                    {"tool": "create_schwarzschild"},
                    {"tool": "compute_ricci"},
                ],
                "sweep": {
                    "trend": {
                        "n": 3, "y_min": 1.0, "y_max": 8.0,
                        "direction": "increasing", "log_log_slope": 2.0,
                    }
                },
            },
            {"success": False, "steps": [{"tool": "foo"}]},
        ]
        m = summarize_run(results, n_registry_tools=80)
        assert m["n_success"] == 1
        assert m["n_fail"] == 1
        assert m["n_replans"] == 1
        assert m["n_sweep_points"] == 3
        assert "decision_pressure_bits" in m
        assert m["mean_trend_certainty"] >= 0

    def test_loop_conclusion_has_foundations(self):
        loop = _loop()
        result = loop.run("What is the scalar curvature of Schwarzschild spacetime?")
        f = result["conclusion"]["foundations"]
        assert f["n_steps"] >= 2
        assert f["unique_tools"] >= 2
        assert f["success_rate"] > 0
        assert f["n_registry_tools"] >= 80

    def test_registry_exposes_foundations_tools(self):
        from orchestrator.tool_registry import execute_tool, resolve_tool_name

        assert resolve_tool_name("trajectory_metrics") == "trajectory_metrics"
        out = execute_tool("shannon_entropy_bits", {"counts": [1, 1, 1, 1]})
        assert out == pytest.approx(2.0)
