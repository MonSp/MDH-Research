"""Tests for L13 golden benchmark suite."""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.benchmark import (
    check_expectation,
    load_suite,
    render_benchmark,
    run_benchmark,
)
from orchestrator.cli import main
from orchestrator.metric_store import reset_store


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


class TestLoadSuite:
    def test_default_suite(self):
        cases = load_suite()
        assert len(cases) >= 5
        assert all("id" in c and "question" in c and "expect" in c for c in cases)


class TestCheckExpectation:
    def test_verdict_match(self):
        result = {
            "conclusion": {"verdict": "Hypotheses verified"},
            "results": [{"success": True, "steps": [{"tool": "compute_scalar_curvature"}]}],
        }
        ok, reasons = check_expectation(result, {
            "verdict": "Hypotheses verified",
            "tools_any": ["compute_scalar_curvature"],
            "min_success": 1,
        })
        assert ok, reasons

    def test_fail_wrong_tool(self):
        result = {
            "conclusion": {"verdict": "Hypotheses verified"},
            "results": [{"success": True, "steps": [{"tool": "hawking_temperature"}]}],
        }
        ok, reasons = check_expectation(result, {
            "tools_any": ["compute_scalar_curvature"],
        })
        assert not ok
        assert any("tools_any" in r for r in reasons)

    def test_sweep_direction(self):
        result = {
            "conclusion": {},
            "results": [{
                "success": True,
                "sweep": {"trend": {"direction": "decreasing"}},
            }],
        }
        ok, reasons = check_expectation(result, {
            "sweep": True, "sweep_direction": "decreasing", "min_success": 1,
        })
        assert ok, reasons


class TestRunBenchmark:
    def test_mini_suite_passes(self):
        mini = [
            {
                "id": "t1",
                "question": "What is the scalar curvature of Schwarzschild spacetime?",
                "expect": {
                    "verdict": "Hypotheses verified",
                    "tools_any": ["compute_scalar_curvature"],
                    "min_success": 1,
                },
            }
        ]
        out = run_benchmark(suite=mini, llm=False)
        assert out["n_cases"] == 1
        assert out["n_passed"] == 1, out
        assert out["pass_rate"] == 1.0

    def test_full_default_suite(self):
        out = run_benchmark(llm=False)
        assert out["n_cases"] >= 5
        # platform on main should pass most/all golden cases
        assert out["pass_rate"] >= 0.8, out
        md = render_benchmark(out)
        assert "Golden Benchmark" in md

    def test_cli_bench_json(self, capsys):
        code = main(["bench", "--llm", "off", "--json"])
        assert code in (0, 1)
        data = json.loads(capsys.readouterr().out)
        assert data["n_cases"] >= 5
        assert "cases" in data
