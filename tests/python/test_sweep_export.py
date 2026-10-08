"""L31: export sweep visualization via CLI --csv and API POST /viz."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.metric_store import reset_store


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


SWEEP_RESULT = {
    "question": "How does Hawking temperature vary as a function of mass? Scan several masses.",
    "conclusion": {"verdict": "Hypotheses verified", "evidence": []},
    "results": [{
        "success": True,
        "sweep": {
            "axis_name": "M",
            "points": [{"x": 1e30, "y": 1e-8}, {"x": 1e31, "y": 1e-9}],
            "trend": {"direction": "decreasing", "n": 2,
                      "points": [{"x": 1e30, "y": 1e-8}, {"x": 1e31, "y": 1e-9}]},
        },
    }],
}

GRID_RESULT = {
    "question": "grid q",
    "conclusion": {"verdict": "Hypotheses verified", "evidence": []},
    "results": [{
        "success": True,
        "grid": {
            "n": 2, "x_name": "M", "y_name": "b",
            "cells": [
                {"x": 1.0, "y": 1.0, "z": 10.0},
                {"x": 2.0, "y": 1.0, "z": 20.0},
            ],
        },
    }],
}


class TestExportRunCsv:
    def test_sweep_headers(self, tmp_path):
        from orchestrator.sweep_viz import export_run_csv

        path = str(tmp_path / "s.csv")
        got = export_run_csv(SWEEP_RESULT, path)
        assert got == path
        lines = open(path, encoding="utf-8").read().splitlines()
        assert lines[0] == "x,y"
        assert len(lines) == 3

    def test_grid_headers_xyz(self, tmp_path):
        from orchestrator.sweep_viz import export_run_csv

        path = str(tmp_path / "g.csv")
        got = export_run_csv(GRID_RESULT, path)
        assert got == path
        lines = open(path, encoding="utf-8").read().splitlines()
        assert lines[0] == "x,y,z"

    def test_no_sweep_returns_none(self, tmp_path):
        from orchestrator.sweep_viz import export_run_csv

        path = str(tmp_path / "n.csv")
        out = export_run_csv({"results": []}, path)
        assert out is None
        assert not os.path.exists(path)


class TestCliRunCsv:
    def test_run_sweep_csv_flag(self, tmp_path):
        from orchestrator.cli import main

        path = str(tmp_path / "out.csv")
        code = main([
            "run",
            "How does Hawking temperature vary as a function of mass? Scan several masses.",
            "--llm", "off",
            "--csv", path,
        ])
        assert code == 0
        assert os.path.isfile(path)
        lines = open(path, encoding="utf-8").read().splitlines()
        assert lines[0] == "x,y"
        assert len(lines) >= 2

    def test_run_without_sweep_no_csv(self, tmp_path, capsys):
        from orchestrator.cli import main

        path = str(tmp_path / "none.csv")
        code = main([
            "run",
            "What is the scalar curvature of Schwarzschild spacetime?",
            "--llm", "off",
            "--csv", path,
        ])
        assert code == 0
        assert not os.path.exists(path)


class TestApiViz:
    def test_viz_endpoint_requires_question(self, client):
        r = client.post("/viz", json={"question": ""})
        assert r.status_code == 400

    def test_viz_sweep_markdown_and_csv(self, client):
        r = client.post("/viz", json={
            "question": "How does Hawking temperature vary as a function of mass? Scan several masses.",
            "llm": False,
        })
        assert r.status_code == 200
        data = r.json()
        assert "Sweep viz" in data.get("markdown", "")
        assert data.get("csv", "").startswith("x,y")
        assert len(data["csv"].splitlines()) >= 2


@pytest.fixture
def client():
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/httpx test client not installed")
    from orchestrator.api import create_app

    return TestClient(create_app())
