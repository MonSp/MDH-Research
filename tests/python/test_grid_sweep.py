"""Tests for L29 2D grid parameter sweep."""
from __future__ import annotations

from orchestrator.param_sweep import (
    MAX_GRID_POINTS,
    expand_grid,
    format_grid_sentence,
    summarize_grid,
)
from orchestrator.research_loop import ResearchLoop


def test_expand_grid_cartesian():
    cells = expand_grid(
        {"name": "M", "values": [1, 2]},
        {"name": "a", "values": [0.1, 0.5]},
    )
    assert len(cells) == 4
    xs = {c["x"] for c in cells}
    ys = {c["y"] for c in cells}
    assert xs == {1.0, 2.0}
    assert ys == {0.1, 0.5}


def test_expand_grid_caps_points():
    cells = expand_grid(
        {"name": "M", "start": 1.0, "stop": 10.0, "n": 10},
        {"name": "a", "start": 0.0, "stop": 1.0, "n": 10},
    )
    assert len(cells) <= MAX_GRID_POINTS


def test_summarize_grid_direction():
    cells = [
        {"x": 1, "y": 0, "z": 1.0},
        {"x": 2, "y": 0, "z": 2.0},
        {"x": 3, "y": 0, "z": 3.0},
        {"x": 1, "y": 1, "z": 4.0},
        {"x": 2, "y": 1, "z": 5.0},
        {"x": 3, "y": 1, "z": 6.0},
    ]
    grid = summarize_grid(cells, "M", "a")
    assert grid["n"] == 6
    assert grid["n_x"] == 3
    assert grid["n_y"] == 2
    assert grid["direction_along_x"] == "increasing"
    assert grid["z_min"] == 1.0
    assert grid["z_max"] == 6.0
    assert "increasing" in format_grid_sentence(grid, "alpha")


def test_summarize_grid_empty():
    grid = summarize_grid([], "x", "y")
    assert grid["n"] == 0
    assert grid["direction"] == "empty"
    assert "no finite" in format_grid_sentence(grid)


def _deflection_grid_hyp() -> dict:
    return {
        "prediction": "deflection grows with M at fixed b",
        "sweep": {
            "tool": "deflection_angle",
            "grid": {
                "x": {"name": "M", "values": [1e30, 2e30]},
                "y": {"name": "b", "values": [1e9, 2e9]},
            },
            "params": {},
        },
    }


def test_run_grid_hypothesis():
    loop = ResearchLoop(llm_client=False)
    hyp = _deflection_grid_hyp()
    out = loop._run_grid_hypothesis(hyp, "h1", hyp["sweep"])
    assert out["success"] is True, out.get("error")
    assert out["grid"]["n"] >= 1
    assert "GRID" in out["summary"]
    assert "result" in out


def test_grid_hypothesis_requires_tool():
    loop = ResearchLoop(llm_client=False)
    hyp = {
        "prediction": "no tool",
        "sweep": {
            "grid": {
                "x": {"name": "M", "values": [1]},
                "y": {"name": "a", "values": [0]},
            },
        },
    }
    out = loop._run_grid_hypothesis(hyp, "h2", hyp["sweep"])
    assert out["success"] is False
    assert "tool" in out["error"]


def test_grid_evidence_confirms_analysis():
    loop = ResearchLoop(llm_client=False)
    hyp = _deflection_grid_hyp()
    out = loop._run_grid_hypothesis(hyp, "h3", hyp["sweep"])
    assert out["success"], out.get("error")
    analysis = loop._analyze("deflection grows with M at fixed b", [out])
    assert analysis["verdict"] == "Hypotheses verified"
    assert analysis["n_experiments"] >= 1
    assert any("GRID" in e for e in analysis["evidence"])
