"""L32: sweep sensitivity analysis (elasticity + grid axis ranking)."""

from __future__ import annotations

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.metric_store import reset_store
from orchestrator.param_sweep import (
    compute_sensitivity,
    format_sensitivity_sentence,
    summarize_grid_sensitivity,
)


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


class TestComputeSensitivity:
    def test_linear_positive(self):
        # y = 3x → elasticity 1
        xs = [1.0, 2.0, 4.0, 8.0]
        ys = [3.0, 6.0, 12.0, 24.0]
        s = compute_sensitivity(xs, ys)
        assert s["n"] == 4
        assert s["elasticity"] == pytest.approx(1.0, rel=1e-6)

    def test_quadratic(self):
        xs = [1.0, 2.0, 4.0]
        ys = [1.0, 4.0, 16.0]  # y = x^2
        s = compute_sensitivity(xs, ys)
        assert s["elasticity"] == pytest.approx(2.0, rel=1e-6)

    def test_empty(self):
        s = compute_sensitivity([], [])
        assert s["n"] == 0
        assert s["elasticity"] is None
        assert s["median_abs_local"] is None

    def test_nonpositive_falls_back(self):
        # y crosses zero → no log-log; local may be partial
        s = compute_sensitivity([1.0, 2.0], [0.0, 1.0])
        assert s["n"] == 2
        # elasticity only defined for positive pairs
        assert s["elasticity"] is None or math.isfinite(s["elasticity"])

    def test_local_stats(self):
        xs = [1.0, 2.0, 4.0]
        ys = [1.0, 4.0, 16.0]
        s = compute_sensitivity(xs, ys)
        assert s["local_elasticities"]
        assert s["median_abs_local"] == pytest.approx(2.0, rel=1e-6)
        assert s["max_abs_local"] == pytest.approx(2.0, rel=1e-6)


class TestGridSensitivity:
    def test_dominant_x(self):
        # z = x^3 * y^0.1 → stronger along x
        cells = []
        for x in (1.0, 2.0, 4.0):
            for y in (1.0, 2.0):
                cells.append({"x": x, "y": y, "z": (x ** 3) * (y ** 0.1)})
        g = {
            "n": len(cells), "x_name": "M", "y_name": "b",
            "cells": cells,
        }
        s = summarize_grid_sensitivity(g)
        assert s["n"] > 0
        assert s["elasticity_x"] == pytest.approx(3.0, rel=1e-3)
        assert s["dominant_axis"] == "x"

    def test_dominant_y(self):
        cells = []
        for x in (1.0, 2.0):
            for y in (1.0, 2.0, 4.0):
                cells.append({"x": x, "y": y, "z": (x ** 0.1) * (y ** 3)})
        g = {"n": len(cells), "x_name": "M", "y_name": "b", "cells": cells}
        s = summarize_grid_sensitivity(g)
        assert s["dominant_axis"] == "y"

    def test_empty(self):
        s = summarize_grid_sensitivity({"n": 0, "cells": []})
        assert s["n"] == 0
        assert s["elasticity_x"] is None
        assert s["dominant_axis"] is None


class TestFormatSentence:
    def test_trend_sentence(self):
        s = {"n": 4, "elasticity": 1.0, "median_abs_local": 1.0}
        out = format_sensitivity_sentence("M", s)
        assert "SENS" in out
        assert "M" in out
        assert "1" in out

    def test_empty_sentence(self):
        out = format_sensitivity_sentence("M", {"n": 0, "elasticity": None})
        assert "SENS" in out
        assert "n/a" in out or "no" in out.lower()


class TestReportSensitivity:
    def test_report_includes_sensitivity(self):
        from orchestrator.report import render_single_run

        result = {
            "question": "How does Hawking temperature vary as a function of mass? Scan several masses.",
            "conclusion": {"verdict": "Hypotheses verified", "evidence": []},
            "results": [{
                "success": True,
                "sweep": {
                    "axis_name": "M",
                    "points": [
                        {"x": 1e30, "y": 1e-8},
                        {"x": 1e31, "y": 1e-9},
                        {"x": 1e32, "y": 1e-10},
                    ],
                    "trend": {
                        "direction": "decreasing", "n": 3,
                        "points": [
                            {"x": 1e30, "y": 1e-8},
                            {"x": 1e31, "y": 1e-9},
                            {"x": 1e32, "y": 1e-10},
                        ],
                    },
                },
            }],
        }
        md = render_single_run(result)
        assert "Sensitivity" in md
