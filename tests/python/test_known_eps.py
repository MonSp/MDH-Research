"""L36: known-value epsilon gate for power-law sweeps (T ∝ 1/M ⇒ ε≈-1)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.known_values import (
    check_chain,
    check_sweep_sensitivity,
    summarize_checks,
)
from orchestrator.metric_store import reset_store


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


def _hawking_sweep_result(eps_slope: float = -1.0) -> dict:
    # y = C * x^eps  → log-log slope = eps
    xs = [1e30, 1e31, 1e32]
    ys = [(x / 1e30) ** eps_slope for x in xs]
    pts = [{"x": x, "y": y} for x, y in zip(xs, ys)]
    return {
        "success": True,
        "steps": [{"tool": "hawking_temperature", "params": {}, "result": {}}],
        "sweep": {"axis_name": "M", "points": pts},
        "hypothesis": {"sweep": {"tool": "hawking_temperature"}},
    }


class TestCheckSweepSensitivity:
    def test_hawking_eps_minus_one_passes(self):
        c = check_sweep_sensitivity(
            _hawking_sweep_result()["sweep"], "hawking_temperature"
        )
        assert c is not None
        assert c["name"] == "hawking_sweep_epsilon"
        assert c["passed"] is True
        assert c["expected"] == pytest.approx(-1.0)

    def test_wrong_slope_fails(self):
        c = check_sweep_sensitivity(
            _hawking_sweep_result(eps_slope=-0.5)["sweep"], "hawking_temperature"
        )
        assert c is not None
        assert c["passed"] is False

    def test_unknown_tool_skipped(self):
        c = check_sweep_sensitivity(
            _hawking_sweep_result()["sweep"], "compute_scalar_curvature"
        )
        assert c is None

    def test_empty_points_skipped(self):
        c = check_sweep_sensitivity(
            {"points": []}, "hawking_temperature"
        )
        assert c is None


class TestCheckChainSeesSweep:
    def test_chain_appends_epsilon_check(self):
        checks = check_chain([_hawking_sweep_result()])
        names = [c["name"] for c in checks]
        assert "hawking_sweep_epsilon" in names

    def test_run_analye_includes_known_value(self):
        from orchestrator.journal import ResearchJournal
        from orchestrator.research_loop import ResearchLoop
        import tempfile

        loop = ResearchLoop(
            journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
            llm_client=False,
        )
        out = loop.run(
            "How does Hawking temperature vary as a function of mass? "
            "Scan several masses."
        )
        kv = out["conclusion"].get("known_value_checks") or {}
        assert kv.get("n_checks", 0) >= 1
        names = [c.get("name") for c in kv.get("checks") or []]
        assert "hawking_sweep_epsilon" in names, kv
        s = summarize_checks(kv.get("checks") or [])
        assert s["n_passed"] >= 1
