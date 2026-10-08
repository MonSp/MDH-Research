"""L30: sweep visualization — sparkline, text tables, CSV export."""

from __future__ import annotations

import csv
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.metric_store import reset_store
from orchestrator.sweep_viz import (
    render_grid_table,
    render_trend_table,
    sparkline,
    write_csv,
)


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


class TestSparkline:
    def test_empty(self):
        assert sparkline([]) == ""

    def test_none_and_nan_skipped(self):
        # only the finite sample remains → single block char
        assert sparkline([None, 1.0, float("nan")]) == "▁"

    def test_constant_single_char(self):
        out = sparkline([2.0, 2.0, 2.0])
        assert len(out) == 3
        assert len(set(out)) == 1

    def test_increasing_levels(self):
        out = sparkline([0.0, 1.0, 2.0, 3.0])
        assert len(out) == 4
        # non-decreasing block levels
        blocks = "▁▂▃▄▅▆▇█"
        levels = [blocks.index(ch) for ch in out]
        assert levels == sorted(levels)
        assert levels[0] < levels[-1]


class TestTrendTable:
    def test_empty_trend(self):
        out = render_trend_table({"n": 0, "points": []})
        assert out == ""

    def test_table_rows(self):
        trend = {
            "n": 2,
            "direction": "increasing",
            "points": [{"x": 1.0, "y": 10.0}, {"x": 2.0, "y": 20.0}],
        }
        out = render_trend_table(trend)
        assert "| x | y |" in out
        assert "| 1 | 10 |" in out
        assert "| 2 | 20 |" in out


class TestGridTable:
    def test_empty_grid(self):
        assert render_grid_table({"n": 0, "cells": []}) == ""

    def test_matrix_rows(self):
        grid = {
            "n": 4,
            "x_name": "M",
            "y_name": "b",
            "cells": [
                {"x": 1.0, "y": 1.0, "z": 10.0},
                {"x": 2.0, "y": 1.0, "z": 20.0},
                {"x": 1.0, "y": 2.0, "z": 30.0},
                {"x": 2.0, "y": 2.0, "z": 40.0},
            ],
        }
        out = render_grid_table(grid)
        assert "M\\b" in out
        assert "10" in out and "40" in out
        # one header line + 2 data rows
        assert len(out.strip().splitlines()) == 3


class TestWriteCsv:
    def test_trend_headers(self, tmp_path):
        path = str(tmp_path / "t.csv")
        write_csv(path, [{"x": 1.0, "y": 2.0}], headers=("x", "y"))
        text = open(path, encoding="utf-8").read()
        assert text.splitlines()[0] == "x,y"
        assert text.splitlines()[1] == "1.0,2.0"

    def test_grid_headers_xyz(self, tmp_path):
        path = str(tmp_path / "g.csv")
        write_csv(
            path,
            [{"x": 1.0, "y": 2.0, "z": 3.0}],
            headers=("x", "y", "z"),
        )
        text = open(path, encoding="utf-8").read()
        assert text.splitlines()[0] == "x,y,z"

    def test_empty_rows_header_only(self, tmp_path):
        path = str(tmp_path / "e.csv")
        write_csv(path, [], headers=("x", "y", "z"))
        text = open(path, encoding="utf-8").read()
        assert text.strip() == "x,y,z"
