"""L42: _analyze attaches grid axis sensitivity evidence."""

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


def _grid_result() -> dict:
    # z = x^3 * y^0.1 → dominant x
    cells = []
    for x in (1.0, 2.0, 4.0):
        for y in (1.0, 2.0):
            cells.append({"x": x, "y": y, "z": (x ** 3) * (y ** 0.1)})
    return {
        "success": True,
        "hypothesis": {"prediction": "grid scan"},
        "steps": [{"tool": "deflection_angle", "params": {}, "result": {}}],
        "grid": {
            "n": len(cells),
            "x_name": "M",
            "y_name": "b",
            "z_min": min(c["z"] for c in cells),
            "z_max": max(c["z"] for c in cells),
            "cells": cells,
            "summary": "GRID: deflection on M×b",
        },
    }


class TestAnalyzeGridSensEvidence:
    def test_grid_adds_axis_sens_evidence(self):
        loop = _loop()
        concl = loop._analyze("grid scan M vs b", [_grid_result()])
        ev = concl.get("evidence") or []
        sens = [e for e in ev if e.startswith("GRID-SENS") or "ε_x" in e]
        assert sens, ev
        assert "dominant=x" in sens[0] or "dominant=x" in sens[0].replace(" ", "")

    def test_no_grid_no_grid_sens(self):
        loop = _loop()
        result = {
            "success": True,
            "hypothesis": {"prediction": "R=0"},
            "steps": [{"tool": "compute_scalar_curvature", "params": {}, "result": {}}],
        }
        concl = loop._analyze("curvature", [result])
        ev = concl.get("evidence") or []
        assert not any(e.startswith("GRID-SENS") for e in ev)

    def test_grid_without_finite_cells_no_sens(self):
        loop = _loop()
        result = {
            "success": False,
            "hypothesis": {"prediction": "fail"},
            "steps": [],
            "error": "grid produced no finite samples",
        }
        # failed results are not in successful[]; ensure no crash
        concl = loop._analyze("grid", [result])
        assert concl.get("verdict")
