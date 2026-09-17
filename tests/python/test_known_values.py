"""Tests for L8 known-value consistency gate."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.known_values import (
    check_chirp_mass,
    check_hawking_temperature,
    check_result,
    check_schwarzschild_qnm,
    check_universe_age,
    summarize_checks,
)
from orchestrator.metric_store import reset_store
from orchestrator.research_loop import ResearchLoop
from orchestrator.journal import ResearchJournal
from orchestrator.tool_registry import execute_tool


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


class TestKnownChecks:
    def test_hawking_solar_mass(self):
        res = execute_tool("hawking_temperature", {"M": 1.989e30})
        c = check_hawking_temperature(res, {"M": 1.989e30})
        assert c["passed"] is True, c

    def test_hawking_wrong_order_fails(self):
        res = {"T_K": 1.0, "M_kg": 1.989e30}  # wildly wrong
        c = check_hawking_temperature(res, {"M": 1.989e30})
        assert c["passed"] is False

    def test_universe_age(self):
        res = execute_tool("age_of_universe", {})
        c = check_universe_age(res)
        assert c["passed"] is True, c

    def test_chirp_mass(self):
        val = execute_tool("chirp_mass", {"m1": 30.0, "m2": 30.0})
        c = check_chirp_mass(val, {"m1": 30.0, "m2": 30.0})
        assert c["passed"] is True, c

    def test_qnm(self):
        res = execute_tool("schwarzschild_qnm", {"l": 2, "n": 0, "M": 1})
        c = check_schwarzschild_qnm(res)
        assert c["passed"] is True, c

    def test_check_result_dispatch(self):
        res = execute_tool("hawking_temperature", {"M": 1.989e30})
        checks = check_result("hawking_temperature", res, {"M": 1.989e30})
        assert checks and checks[0]["name"] == "hawking_temperature"

    def test_summarize(self):
        checks = [{"passed": True}, {"passed": False}]
        s = summarize_checks(checks)
        assert s["n_checks"] == 2
        assert s["n_failed"] == 1
        assert s["all_passed"] is False


class TestLoopIntegration:
    def test_hawking_run_includes_known_value_pass(self):
        loop = ResearchLoop(
            journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
            llm_client=False,
        )
        result = loop.run("What is the Hawking temperature of a solar mass black hole?")
        kv = result["conclusion"]["known_value_checks"]
        assert kv["n_checks"] >= 1
        assert kv["n_passed"] >= 1
        assert any("KNOWN-VALUE PASS" in e for e in result["conclusion"]["evidence"])

    def test_universe_age_known_value(self):
        loop = ResearchLoop(
            journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
            llm_client=False,
        )
        result = loop.run("What is the age of the universe?")
        kv = result["conclusion"]["known_value_checks"]
        assert kv["n_checks"] >= 1
        assert kv["n_passed"] >= 1

    def test_curvature_run_no_known_value_checks(self):
        loop = ResearchLoop(
            journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
            llm_client=False,
        )
        result = loop.run("What is the scalar curvature of Schwarzschild spacetime?")
        kv = result["conclusion"]["known_value_checks"]
        # no catalog entry for scalar curvature path
        assert kv["n_checks"] == 0
