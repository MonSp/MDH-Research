"""Tests for SymPy simplify + field-equation residual gate in _analyze."""

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

from orchestrator.metric_store import get_store, reset_store
from orchestrator.research_loop import ResearchLoop
from orchestrator.journal import ResearchJournal
from orchestrator.verification import (
    expression_free_symbols,
    gate_counts_as_verified,
    is_vacuum_metric_tool_chain,
    numeric_eval_is_zero,
    prediction_claims_vacuum,
    should_run_vacuum_gate,
    sympy_is_zero,
    vacuum_residual_check,
)


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


class TestSympyIsZero:
    def test_plain_zero(self):
        assert sympy_is_zero(0) is True
        assert sympy_is_zero(0.0) is True

    def test_nonzero_number(self):
        assert sympy_is_zero(3.5) is False

    def test_schwarzschild_scalar_curvature_is_zero(self):
        import _research_core as rc

        m = rc.geometry.Manifold("s", ["t", "r", "theta", "phi"])
        g = rc.geometry.Metric.from_diagonal(m, [
            "-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2",
        ])
        scalar_r = g.scalar_curvature()
        assert sympy_is_zero(scalar_r) is True

    def test_nonzero_expression(self):
        import _research_core as rc

        e = rc.symbol.parse("M/r^2 + 1")
        assert sympy_is_zero(e) is False


class TestNumericEval:
    def test_unbound_symbol_not_confirmed(self):
        """C2: free L unbound must not numeric-confirm de Sitter R."""
        import _research_core as rc

        m = rc.geometry.Manifold("d", ["t", "r", "theta", "phi"])
        g = rc.geometry.Metric.from_diagonal(m, [
            "-(1 - L*r^2/3)", "(1 - L*r^2/3)^(-1)", "r^2", "r^2 * sin(theta)^2",
        ])
        scalar_r = g.scalar_curvature()
        free = expression_free_symbols(scalar_r)
        assert "L" in free
        pts = [{"t": 0, "r": 6, "theta": 1.57, "phi": 0, "M": 1}]
        is_zero, sample, note = numeric_eval_is_zero(scalar_r, pts)
        assert is_zero is None
        assert "unbound" in (note or "")
        # with L bound, R = 4L ≠ 0
        is_zero2, sample2, _ = numeric_eval_is_zero(
            scalar_r, pts, extra_params={"L": 1.0}
        )
        assert is_zero2 is False
        assert abs(sample2 - 4.0) < 0.1

    def test_bound_zero_confirms(self):
        import _research_core as rc

        m = rc.geometry.Manifold("s", ["t", "r", "theta", "phi"])
        g = rc.geometry.Metric.from_diagonal(m, [
            "-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2",
        ])
        scalar_r = g.scalar_curvature()
        pts = [{"t": 0, "r": 8, "theta": 1.57, "phi": 0, "M": 1}]
        is_zero, sample, note = numeric_eval_is_zero(scalar_r, pts, extra_params={"M": 1.0})
        assert is_zero is True, (sample, note)


class TestVacuumResidual:
    def _schwarzschild(self):
        import _research_core as rc

        m = rc.geometry.Manifold("s", ["t", "r", "theta", "phi"])
        g = rc.geometry.Metric.from_diagonal(m, [
            "-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2",
        ])
        return g, ["t", "r", "theta", "phi"]

    def test_schwarzschild_vacuum_passes(self):
        g, coords = self._schwarzschild()
        out = vacuum_residual_check(g, coords, params={"M": 1.0})
        assert out["passed"] is True, out
        assert out["max_abs"] < 1e-6

    def test_minkowski_passes(self):
        import _research_core as rc

        m = rc.geometry.Manifold("m", ["t", "x", "y", "z"])
        g = rc.geometry.Metric.from_diagonal(m, ["-1", "1", "1", "1"])
        out = vacuum_residual_check(g, ["t", "x", "y", "z"])
        assert out["passed"] is True, out

    def test_all_failed_evals_do_not_pass(self):
        """C1: silent evaluate failures must not look like residual 0."""

        class FakeMetric:
            def dimension(self):
                return 2

            def einstein_tensor(self):
                class G:
                    def at(self, idx):
                        raise RuntimeError("boom")

                return G()

        out = vacuum_residual_check(FakeMetric(), ["t", "r"])
        assert out["passed"] is False
        assert out["max_abs"] is None

    def test_nan_residual_does_not_pass(self):
        class NanMetric:
            def dimension(self):
                return 1

            def einstein_tensor(self):
                class G:
                    def at(self, idx):
                        class E:
                            def evaluate(self, vm):
                                return float("nan")

                        return E()

                return G()

        out = vacuum_residual_check(NanMetric(), ["t"], points=[{"t": 0}])
        assert out["passed"] is False


class TestVacuumGuards:
    def test_tightened_prediction_hints(self):
        assert prediction_claims_vacuum("R = 0 vacuum solution") is True
        assert prediction_claims_vacuum("Schwarzschild is Ricci-flat") is True
        assert prediction_claims_vacuum("Hawking temperature") is False
        assert prediction_claims_vacuum("horizon at r=0") is False
        assert prediction_claims_vacuum("horizon vanishes when a>M") is False

    def test_factory_chain(self):
        assert is_vacuum_metric_tool_chain(["create_kerr", "compute_ricci"]) is True
        assert is_vacuum_metric_tool_chain(["create_reissner_nordstrom"]) is False
        assert is_vacuum_metric_tool_chain(["create_desitter"]) is False
        assert should_run_vacuum_gate("x", ["create_schwarzschild"]) is True
        assert should_run_vacuum_gate("R=0", ["create_desitter"]) is False

    def test_gate_only_verifies_vacuum_predictions(self):
        assert gate_counts_as_verified("scalar curvature R = 0 vacuum") is True
        assert gate_counts_as_verified("Kretschmann scalar K") is False


class TestAnalyzePipeline:
    def test_schwarzschild_chain_gets_verified_and_gate(self):
        loop = _loop()
        result = loop.run("What is the scalar curvature of Schwarzschild spacetime?")
        c = result["conclusion"]
        assert c["verdict"] == "Hypotheses verified"
        v = c["verification"]
        assert v["numeric_confirmed"] >= 1 or v["symbolic_confirmed"] >= 1
        assert v["residual_gates"], "expected vacuum residual gate"
        assert v["residual_gates"][0]["passed"] is True
        assert result["results"][0].get("metric_name") == "schwarzschild"

    def test_kerr_chain_gate(self):
        loop = _loop()
        hyp = [{
            "prediction": "Kerr is a vacuum solution so R vanishes",
            "tools": [
                {"tool": "create_kerr", "params": {"M": 1, "a": 0.3}},
                {"tool": "compute_scalar_curvature", "params": {}},
            ],
            "assumptions": ["Kerr"],
        }]
        loop._hypothesize_patterns = lambda q: hyp  # type: ignore
        result = loop.run("kerr vacuum")
        c = result["conclusion"]
        assert c["verdict"] == "Hypotheses verified"
        assert c["verification"]["residual_gates"][0]["passed"] is True

    def test_desitter_not_falsely_numeric_confirmed(self):
        """C2 e2e: de Sitter R=4Λ must not be numeric-confirmed with L unbound."""
        loop = _loop()
        hyp = [{
            "prediction": "de Sitter scalar curvature",
            "tools": [
                {"tool": "create_desitter", "params": {"L": 1.0}},
                {"tool": "compute_scalar_curvature", "params": {}},
            ],
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyp  # type: ignore
        result = loop.run("de sitter curvature")
        c = result["conclusion"]
        assert c["verification"]["numeric_confirmed"] == 0
        assert c["verification"]["symbolic_confirmed"] == 0
        # no vacuum gate for de Sitter factory
        assert c["verification"]["residual_gates"] == []

    def test_hawking_chain_no_vacuum_gate(self):
        loop = _loop()
        result = loop.run("What is the Hawking temperature of a black hole?")
        c = result["conclusion"]
        v = c["verification"]
        assert v["residual_gates"] == []
        assert c["verdict"] in (
            "Experiments completed (symbolic simplification pending)",
            "Hypotheses verified",
        )

    def test_kretschmann_gate_does_not_alone_verify(self):
        loop = _loop()
        hyp = [{
            "prediction": "Kretschmann scalar of Schwarzschild",
            "tools": [
                {"tool": "create_schwarzschild", "params": {"M": 1}},
                {"tool": "compute_kretschmann", "params": {}},
            ],
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyp  # type: ignore
        result = loop.run("kretschmann")
        c = result["conclusion"]
        assert c["verification"]["symbolic_confirmed"] == 0
        assert c["verification"]["numeric_confirmed"] == 0
        # gate may run (vacuum factory) but must NOT alone flip to verified
        assert c["verdict"] != "Hypotheses verified"

    def test_all_failed_includes_verification(self, monkeypatch):
        import orchestrator.compete as compete_mod

        # disable L6 competition so this stays a pure all-failed path
        monkeypatch.setattr(compete_mod, "should_compete", lambda *a, **k: False)
        loop = _loop()
        hyp = [{
            "prediction": "fail",
            "tools": ["not_a_real_tool_xyz"],
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyp  # type: ignore
        result = loop.run("force fail")
        assert result["conclusion"]["verdict"] == "All experiments failed"
        assert "verification" in result["conclusion"]
