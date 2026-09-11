"""Black hole solution generator with horizon/singularity analysis (T22).

Provides factory functions for common black hole spacetimes and
analytical tools for locating horizons and singularities.
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

sym = rc.symbol
geom = rc.geometry


def create_schwarzschild(M: float = 1.0) -> dict[str, Any]:
    """Create Schwarzschild metric with parameter M.

    ds² = -(1 - 2M/r)dt² + (1 - 2M/r)^{-1}dr² + r²dΩ²

    Returns dict with metric, manifold, parameters, horizons, singularities.
    """
    m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
    g = geom.Metric.from_diagonal(m, [
        "-(1 - 2*M/r)",
        "(1 - 2*M/r)^(-1)",
        "r^2",
        "r^2 * sin(theta)^2",
    ])

    return {
        "name": "Schwarzschild",
        "metric": g,
        "manifold": m,
        "coord_names": ["t", "r", "theta", "phi"],
        "params": {"M": M},
        "horizons": {
            "event_horizon": {"r": 2 * M, "type": "null"},
        },
        "singularities": {
            "curvature_singularity": {"r": 0, "type": "spacelike"},
        },
        "kretschmann_expr": "48*M^2/r^6",
        "kretschmann_at_horizon": 48 * M**2 / (2 * M)**6,
    }


def create_kerr(M: float = 1.0, a: float = 0.5) -> dict[str, Any]:
    """Create Kerr metric with mass M and spin parameter a.

    In Boyer-Lindquist coordinates:
    Σ = r² + a²cos²θ, Δ = r² - 2Mr + a²

    Returns dict with metric info, horizons, singularities.
    """
    m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])

    # Diagonal approximation for computational tractability
    # Full Kerr has off-diagonal g_tφ but we use diagonal for symbolic computation
    g = geom.Metric.from_diagonal(m, [
        "-(1 - 2*M*r/(r^2 + a^2*cos(theta)^2))",
        "(r^2 + a^2*cos(theta)^2)/(r^2 - 2*M*r + a^2)",
        "r^2 + a^2*cos(theta)^2",
        "(r^2 + a^2 + 2*M*a^2*r*sin(theta)^2/(r^2 + a^2*cos(theta)^2))*sin(theta)^2",
    ])

    # Horizons: r± = M ± √(M² - a²)
    r_plus = M + np.sqrt(M**2 - a**2) if M >= a else None
    r_minus = M - np.sqrt(M**2 - a**2) if M >= a else None

    return {
        "name": "Kerr",
        "metric": g,
        "manifold": m,
        "coord_names": ["t", "r", "theta", "phi"],
        "params": {"M": M, "a": a},
        "horizons": {
            "outer_event_horizon": {"r": r_plus, "type": "null"},
            "inner_horizon": {"r": r_minus, "type": "null"},
        },
        "singularities": {
            "ring_singularity": {"r": 0, "theta": np.pi / 2, "type": "ring"},
        },
        "kretschmann_expr": "48*M^2*(r^2 - a^2*cos(theta)^2)*(r^2 + a^2*cos(theta)^2 - 4*a^2*r^2*sin(theta)^2/(r^2+a^2*cos(theta)^2)) / (r^2+a^2*cos(theta)^2)^6",
    }


def create_reissner_nordstrom(M: float = 1.0, Q: float = 0.5) -> dict[str, Any]:
    """Create Reissner-Nordstrom metric (charged, non-rotating).

    ds² = -(1 - 2M/r + Q²/r²)dt² + (1 - 2M/r + Q²/r²)^{-1}dr² + r²dΩ²
    """
    m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
    g = geom.Metric.from_diagonal(m, [
        "-(1 - 2*M/r + Q^2/r^2)",
        "(1 - 2*M/r + Q^2/r^2)^(-1)",
        "r^2",
        "r^2 * sin(theta)^2",
    ])

    # Horizons: r± = M ± √(M² - Q²)
    disc = M**2 - Q**2
    r_plus = M + np.sqrt(disc) if disc >= 0 else None
    r_minus = M - np.sqrt(disc) if disc >= 0 else None

    return {
        "name": "Reissner-Nordstrom",
        "metric": g,
        "manifold": m,
        "coord_names": ["t", "r", "theta", "phi"],
        "params": {"M": M, "Q": Q},
        "horizons": {
            "outer_horizon": {"r": r_plus, "type": "null"},
            "inner_horizon": {"r": r_minus, "type": "null"},
        },
        "singularities": {
            "curvature_singularity": {"r": 0, "type": "timelike"},
        },
    }


def create_desitter(L: float = 1.0) -> dict[str, Any]:
    """Create de Sitter spacetime (positive cosmological constant).

    ds² = -(1 - Λr²/3)dt² + (1 - Λr²/3)^{-1}dr² + r²dΩ²
    """
    m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
    g = geom.Metric.from_diagonal(m, [
        "-(1 - L*r^2/3)",
        "(1 - L*r^2/3)^(-1)",
        "r^2",
        "r^2 * sin(theta)^2",
    ])

    r_cosmo = np.sqrt(3 / L) if L > 0 else None

    return {
        "name": "de Sitter",
        "metric": g,
        "manifold": m,
        "coord_names": ["t", "r", "theta", "phi"],
        "params": {"L": L},
        "horizons": {
            "cosmological_horizon": {"r": r_cosmo, "type": "cosmological"},
        },
        "singularities": {},
    }


def analyze_horizon(bh_solution, coord_name: str = "r") -> dict[str, Any]:
    """Analyze horizons of a black hole solution.

    Horizons occur where g_tt = 0 (event horizon) or where the metric is singular.

    Returns dict with horizon radii and types.
    """
    g = bh_solution["metric"]
    params = bh_solution["params"]
    n = g.dimension()

    # Find where g_tt = 0 numerically
    g_tt = g.g(0, 0)

    # Scan over r values
    r_vals = np.linspace(0.1, 20, 200)
    g_tt_vals = []

    for r_val in r_vals:
        var_map = dict(params)
        var_map["r"] = r_val
        var_map["theta"] = np.pi / 2  # equatorial plane
        var_map["t"] = 0
        var_map["phi"] = 0
        try:
            val = g_tt.evaluate(var_map)
            g_tt_vals.append(val)
        except (ValueError, OverflowError):
            g_tt_vals.append(float('nan'))

    g_tt_vals = np.array(g_tt_vals)

    # Find sign changes (horizon crossings)
    horizons = []
    for i in range(len(g_tt_vals) - 1):
        if np.isfinite(g_tt_vals[i]) and np.isfinite(g_tt_vals[i + 1]):
            # Use sign() to handle -0.0 correctly
            if np.sign(g_tt_vals[i]) != np.sign(g_tt_vals[i + 1]) and np.sign(g_tt_vals[i]) != 0:
                # Linear interpolation for crossing point
                r_h = r_vals[i] - g_tt_vals[i] * (r_vals[i + 1] - r_vals[i]) / (g_tt_vals[i + 1] - g_tt_vals[i])
                horizons.append(float(r_h))

    return {
        "horizon_radii": horizons,
        "g_tt_values": g_tt_vals.tolist(),
        "r_scan": r_vals.tolist(),
    }


def compute_kretschmann_numerical(bh_solution, r_val: float = 6.0) -> float:
    """Compute Kretschmann scalar at a specific radius."""
    g = bh_solution["metric"]
    params = bh_solution["params"]
    K = g.kretschmann_scalar()

    var_map = dict(params)
    var_map["r"] = r_val
    var_map["theta"] = np.pi / 2
    var_map["t"] = 0
    var_map["phi"] = 0

    return K.evaluate(var_map)
