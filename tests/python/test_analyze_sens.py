"""L40: _analyze attaches SENS elasticity evidence for successful sweeps."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.journal import ResearchJournal
from orchestrator.metric_store import reset_store
from orchestrator.research_loop import ResearchLoop


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


def _sweep_result() -> dict:
    xs = [1e30, 1e31, 1e32]
    ys = [6.17e-8, 6.17e-9, 6.17e-10]
    pts = [{"x": x, "y": y} for x, y in zip(xs, ys)]
    from orchestrator.param_sweep import summarize_trend

    trend = summarize_trend(xs, ys)
    return {
        "success": True,
        "hypothesis": {"prediction": "T decreases with M"},
        "steps": [{"tool": "hawking_temperature", "params": {}, "result": {}}],
        "sweep": {
            "axis_name": "M",
            "extract": "T_K",
            "points": pts,
            "trend": trend,
            "summary": "SWEEP: T_K vs M → decreasing",
        },
    }


class TestAnalyzeSensEvidence:
    def test_sweep_adds_sens_evidence(self):
        loop = _loop()
        concl = loop._analyze("How does T vary with M?", [_sweep_result()])
        ev = concl.get("evidence") or []
        sens = [e for e in ev if e.startswith("SENS") or "ε=" in e]
        assert sens, ev
        assert "−1" in sens[0] or "-1" in sens[0]

    def test_no_sweep_no_sens(self):
        loop = _loop()
        result = {
            "success": True,
            "hypothesis": {"prediction": "R=0"},
            "steps": [{"tool": "compute_scalar_curvature", "params": {}, "result": {}}],
        }
        concl = loop._analyze("curvature", [result])
        ev = concl.get("evidence") or []
        assert not any(e.startswith("SENS") for e in ev)

    def test_live_run_has_sens(self):
        loop = _loop()
        out = loop.run(
            "How does Hawking temperature vary as a function of mass? "
            "Scan several masses."
        )
        ev = out["conclusion"].get("evidence") or []
        assert any(e.startswith("SENS") for e in ev), ev
