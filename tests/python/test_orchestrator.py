"""Tests for the agent orchestration layer (T7)."""

import sys
import os
import pytest

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

rc = pytest.importorskip("_research_core")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from orchestrator.session import GeometrySession, TOOLS


def test_tool_definitions():
    """Tool definitions should be valid JSON Schema."""
    assert len(TOOLS) == 6
    for tool in TOOLS:
        assert "type" in tool
        assert "function" in tool
        func = tool["function"]
        assert "name" in func
        assert "parameters" in func


def test_define_manifold():
    session = GeometrySession()
    result = session.define_manifold("spacetime", ["t", "r", "theta", "phi"])
    assert result["name"] == "spacetime"
    assert result["dimension"] == 4


def test_define_flat_metric():
    session = GeometrySession()
    session.define_manifold("2d", ["x", "y"])
    result = session.define_metric("2d", [["1", "0"], ["0", "1"]])
    assert result["dimension"] == 2


def test_define_metric_unknown_manifold():
    session = GeometrySession()
    result = session.define_metric("nonexistent", [["1", "0"], ["0", "1"]])
    assert "error" in result


def test_compute_flat_christoffel():
    session = GeometrySession()
    session.define_manifold("2d", ["x", "y"])
    session.define_metric("2d", [["1", "0"], ["0", "1"]])
    result = session.compute_christoffel("2d")
    assert result["type"] == "christoffel"
    assert result["rank"] == 3


def test_compute_flat_scalar_curvature():
    session = GeometrySession()
    session.define_manifold("2d", ["x", "y"])
    session.define_metric("2d", [["1", "0"], ["0", "1"]])
    result = session.compute_scalar_curvature("2d")
    assert result["value"] == "0"


def test_execute_tool_dispatch():
    session = GeometrySession()
    result = session.execute_tool("define_manifold", {"name": "2d", "coordinates": ["x", "y"]})
    assert result["name"] == "2d"

    result = session.execute_tool("define_metric", {"manifold_name": "2d", "components": [["1", "0"], ["0", "1"]]})
    assert result["dimension"] == 2

    result = session.execute_tool("compute_scalar_curvature", {"metric_name": "2d"})
    assert result["value"] == "0"


def test_execute_unknown_tool():
    session = GeometrySession()
    result = session.execute_tool("nonexistent", {})
    assert "error" in result


def test_full_schwarzschild_pipeline():
    """Full pipeline: define Schwarzschild manifold + metric, compute curvature."""
    session = GeometrySession()

    session.execute_tool("define_manifold", {
        "name": "spacetime",
        "coordinates": ["t", "r", "theta", "phi"],
    })

    # Simplified Schwarzschild (diagonal, using symbols M and r)
    session.execute_tool("define_metric", {
        "manifold_name": "spacetime",
        "components": [
            ["M", "0", "0", "0"],  # placeholder — real impl needs expression parser
            ["0", "r", "0", "0"],
            ["0", "0", "r", "0"],
            ["0", "0", "0", "r"],
        ],
    })

    gamma_result = session.execute_tool("compute_christoffel", {"metric_name": "spacetime"})
    assert gamma_result["type"] == "christoffel"

    ric_result = session.execute_tool("compute_ricci", {"metric_name": "spacetime"})
    assert ric_result["type"] == "ricci"

    scalar_result = session.execute_tool("compute_scalar_curvature", {"metric_name": "spacetime"})
    assert "value" in scalar_result
