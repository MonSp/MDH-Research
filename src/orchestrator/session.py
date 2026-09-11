"""LLM function-calling interface for the symbolic geometry engine.

Exposes the C++ computation core as tool definitions compatible with
OpenAI function calling / Anthropic tool use.
"""

from __future__ import annotations

import sys
import os
from typing import Any

# Ensure the C++ bindings are importable
BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

try:
    import _research_core as rc
except ImportError:
    rc = None

# Tool definitions for LLM function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "define_manifold",
            "description": "Define a differentiable manifold with named coordinates.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Name of the manifold"},
                    "coordinates": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Coordinate names, e.g. ['t', 'r', 'theta', 'phi']",
                    },
                },
                "required": ["name", "coordinates"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "define_metric",
            "description": "Define a metric tensor on a manifold. Components is a nested list of symbolic expressions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "manifold_name": {"type": "string"},
                    "components": {
                        "type": "array",
                        "items": {"type": "array", "items": {"type": "string"}},
                        "description": "Metric components as strings, e.g. [['-(1-2*M/r)', '0'], ['0', '(1-2*M/r)^(-1)']]",
                    },
                },
                "required": ["manifold_name", "components"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_christoffel",
            "description": "Compute Christoffel symbols for a defined metric.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string"},
                },
                "required": ["metric_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_riemann",
            "description": "Compute Riemann curvature tensor for a defined metric.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string"},
                },
                "required": ["metric_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_ricci",
            "description": "Compute Ricci tensor for a defined metric.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string"},
                },
                "required": ["metric_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "compute_scalar_curvature",
            "description": "Compute scalar curvature R for a defined metric.",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string"},
                },
                "required": ["metric_name"],
            },
        },
    },
]


class GeometrySession:
    """Manages stateful geometry computation sessions."""

    def __init__(self):
        if rc is None:
            raise RuntimeError("C++ bindings not available. Build with cmake first.")
        self._manifolds: dict[str, Any] = {}
        self._metrics: dict[str, Any] = {}

    def define_manifold(self, name: str, coordinates: list[str]) -> dict:
        m = rc.geometry.Manifold(name, coordinates)
        self._manifolds[name] = m
        return {"name": name, "dimension": m.dimension(), "coordinates": coordinates}

    def define_metric(self, manifold_name: str, components: list[list[str]]) -> dict:
        m = self._manifolds.get(manifold_name)
        if m is None:
            return {"error": f"Manifold '{manifold_name}' not defined"}
        # Parse component strings into Expression objects (simplified: numeric literals)
        expr_components = []
        for row in components:
            expr_row = []
            for cell in row:
                expr_row.append(self._parse_expr(cell))
            expr_components.append(expr_row)
        g = rc.geometry.Metric(m, expr_components)
        self._metrics[manifold_name] = g
        return {"manifold": manifold_name, "dimension": g.dimension()}

    def compute_christoffel(self, metric_name: str) -> dict:
        g = self._metrics.get(metric_name)
        if g is None:
            return {"error": f"Metric '{metric_name}' not defined"}
        Gamma = g.christoffel_symbols()
        return {"metric": metric_name, "type": "christoffel", "rank": 3}

    def compute_riemann(self, metric_name: str) -> dict:
        g = self._metrics.get(metric_name)
        if g is None:
            return {"error": f"Metric '{metric_name}' not defined"}
        R = g.riemann_tensor()
        return {"metric": metric_name, "type": "riemann", "rank": 4}

    def compute_ricci(self, metric_name: str) -> dict:
        g = self._metrics.get(metric_name)
        if g is None:
            return {"error": f"Metric '{metric_name}' not defined"}
        Ric = g.ricci_tensor()
        return {"metric": metric_name, "type": "ricci", "rank": 2}

    def compute_scalar_curvature(self, metric_name: str) -> dict:
        g = self._metrics.get(metric_name)
        if g is None:
            return {"error": f"Metric '{metric_name}' not defined"}
        R = g.scalar_curvature()
        return {"metric": metric_name, "type": "scalar_curvature", "value": R.to_string()}

    def execute_tool(self, name: str, arguments: dict) -> dict:
        dispatch = {
            "define_manifold": lambda: self.define_manifold(arguments["name"], arguments["coordinates"]),
            "define_metric": lambda: self.define_metric(arguments["manifold_name"], arguments["components"]),
            "compute_christoffel": lambda: self.compute_christoffel(arguments["metric_name"]),
            "compute_riemann": lambda: self.compute_riemann(arguments["metric_name"]),
            "compute_ricci": lambda: self.compute_ricci(arguments["metric_name"]),
            "compute_scalar_curvature": lambda: self.compute_scalar_curvature(arguments["metric_name"]),
        }
        handler = dispatch.get(name)
        if handler is None:
            return {"error": f"Unknown tool: {name}"}
        return handler()

    def _parse_expr(self, s: str):
        """Parse an expression string into a C++ Expression object using the full parser."""
        s = s.strip()
        return rc.symbol.parse(s)
