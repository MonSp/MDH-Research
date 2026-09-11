"""ADM 3+1 decomposition and Hamiltonian constraint (T23).

The ADM formalism decomposes spacetime into spatial hypersurfaces:
    ds² = -N²dt² + γ_ij(dx^i + N^i dt)(dx^j + N^j dt)

where:
- N: lapse function
- N^i: shift vector
- γ_ij: spatial 3-metric

Extrinsic curvature: K_ij = (1/2N)(∂_t γ_ij - ∇_i N_j - ∇_j N_i)

Hamiltonian constraint: R^(3) + K² - K_ij K^ij = 16πρ
Momentum constraint: ∇_j(K^ij - γ^ij K) = 8π j^i

For vacuum: R^(3) + K² - K_ij K^ij = 0
"""

from __future__ import annotations

import sys
import os
from typing import Any

import numpy as np

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

try:
    import _research_core as rc
except ImportError:
    rc = None


def extract_adm_static(metric, coord_names: list[str]) -> dict[str, Any]:
    """Extract ADM quantities for a static diagonal metric.

    For a static metric ds² = g_tt dt² + g_ij dx^i dx^j:
    - N = √(-g_tt)
    - N^i = 0
    - γ_ij = g_ij (spatial part)

    Args:
        metric: 4D Metric object
        coord_names: coordinate names [t, x1, x2, x3]

    Returns:
        Dict with lapse, shift, spatial metric components
    """
    sym = rc.symbol
    n = metric.dimension()
    spatial_n = n - 1

    # Lapse: N = √(-g_tt)
    g_tt = metric.g(0, 0)
    lapse_sq = sym.mul(sym.number(-1), g_tt.clone())
    lapse = sym.pow(lapse_sq, sym.number(0.5))

    # Shift: N^i = 0 for static diagonal metric
    shift = [sym.number(0)] * spatial_n

    # Spatial metric: γ_ij = g_{i+1, j+1}
    gamma = []
    for i in range(spatial_n):
        row = []
        for j in range(spatial_n):
            row.append(metric.g(i + 1, j + 1).clone())
        gamma.append(row)

    return {
        "lapse": lapse,
        "shift": shift,
        "spatial_metric": gamma,
        "spatial_coords": coord_names[1:],
        "static": True,
    }


def hamiltonian_constraint_static(metric, coord_names: list[str]) -> dict[str, Any]:
    """Evaluate the Hamiltonian constraint for a static spacetime.

    For static vacuum: R^(3) = 0 (3D Ricci scalar of spatial slice)
    For static with K=0: Hamiltonian constraint reduces to R^(3) = 16πρ

    This computes R^(3) symbolically.
    """
    sym = rc.symbol
    n = metric.dimension()
    spatial_n = n - 1

    # Extract spatial metric
    gamma = []
    for i in range(spatial_n):
        row = []
        for j in range(spatial_n):
            row.append(metric.g(i + 1, j + 1).clone())
        gamma.append(row)

    # For diagonal spatial metric, compute 3D Ricci scalar
    # This requires 3D Christoffel symbols and Riemann tensor
    # For simplicity, compute using the spatial metric components

    # Spatial coordinates
    spatial_coords = coord_names[1:]

    # For a diagonal spatial metric γ_ij, the 3D Ricci scalar can be computed
    # using the formula for diagonal metrics
    # R^(3) = -Σ_i (1/γ_ii) [∂_i²(ln√γ) + (∂_i ln√γ)²]
    # where γ = det(γ_ij) = Π_i γ_ii for diagonal metrics

    # Simplified: for static diagonal metrics, K_ij = 0
    # Hamiltonian constraint: R^(3) = 0 (vacuum) or R^(3) = 16πρ (matter)

    # Compute spatial Ricci scalar numerically at a test point
    # by constructing a 3D metric and computing its scalar curvature
    spatial_manifold = rc.geometry.Manifold("spatial_3d", spatial_coords)
    spatial_metric = rc.geometry.Metric(spatial_manifold, gamma)

    R3 = spatial_metric.scalar_curvature()

    return {
        "R3_symbolic": str(R3),
        "R3_expression": R3,
        "hamiltonian_constraint": "R^(3) + K² - K_ij K^ij = 16πρ",
        "static_note": "For static spacetimes K_ij = 0, so constraint is R^(3) = 16πρ",
        "vacuum": "R^(3) = 0 for vacuum static spacetimes",
    }


def hamiltonian_constraint_numerical(metric, coord_names, coords, params=None):
    """Evaluate Hamiltonian constraint numerically at a point.

    For static vacuum: R^(3) should be 0.
    """
    sym = rc.symbol
    n = metric.dimension()
    spatial_n = n - 1
    params = params or {}

    spatial_coords = coord_names[1:]
    gamma = []
    for i in range(spatial_n):
        row = []
        for j in range(spatial_n):
            row.append(metric.g(i + 1, j + 1).clone())
        gamma.append(row)

    spatial_manifold = rc.geometry.Manifold("spatial_3d", spatial_coords)
    spatial_metric = rc.geometry.Metric(spatial_manifold, gamma)

    R3 = spatial_metric.scalar_curvature()

    var_map = dict(params)
    for i in range(n):
        var_map[coord_names[i]] = float(coords[i])

    R3_val = R3.evaluate(var_map)

    return {
        "R3_value": R3_val,
        "hamiltonian_satisfied": abs(R3_val) < 1e-8,
        "point": {coord_names[i]: float(coords[i]) for i in range(n)},
    }


def extrinsic_curvature_static():
    """For static spacetimes, K_ij = 0 (time derivatives of spatial metric vanish).

    Returns zero extrinsic curvature.
    """
    return {
        "K_ij": "0 (static spacetime)",
        "K": 0,
        "note": "Static spacetimes have vanishing extrinsic curvature",
    }
