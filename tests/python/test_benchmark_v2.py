"""Tests for L22 expanded golden benchmark suite."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.benchmark import load_suite, render_benchmark, run_benchmark
from orchestrator.cli import main
from orchestrator.metric_store import reset_store


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


class TestExpandedSuite:
    def test_suite_has_more_cases(self):
        cases = load_suite()
        assert len(cases) >= 8
        ids = [c["id"] for c in cases]
        assert "schwarzschild-kretschmann" in ids
        assert "hawking-evaporation" in ids
        assert "chirp-mass" in ids

    def test_full_benchmark_passes(self):
        out = run_benchmark(llm=False)
        assert out["n_cases"] >= 8
        # platform should pass most golden cases on pattern path
        assert out["pass_rate"] >= 0.8, out
        md = render_benchmark(out)
        assert "Golden Benchmark" in md

    def test_cli_bench_json(self, capsys):
        code = main(["bench", "--llm", "off", "--json"])
        assert code in (0, 1)
        data = json.loads(capsys.readouterr().out)
        assert data["n_cases"] >= 8
        assert all("id" in c for c in data["cases"])
