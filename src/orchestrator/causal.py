"""Causal structure analysis (T24).

Tools for analyzing the causal properties of spacetimes:
- Light cone structure at a point
- Causal classification of curves (timelike/null/spacelike)
- Horizon detection via causal analysis
- Penrose diagram structure hints
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


def classify_vector(metric, coord_names, tangent, params=None):
    """Classify a tangent vector as timelike, null, or spacelike.

    Computes g_μν v^μ v^ν:
    - < 0: timelike (in -+++ signature)
    - = 0: null
    - > 0: spacelike

    Args:
        metric: Metric object
        coord_names: coordinate names
        tangent: tangent vector components [v^0, v^1, v^2, v^3]
        params: metric parameters

    Returns:
        Dict with norm value and classification
    """
    sym = rc.symbol
    n = metric.dimension()
    params = params or {}

    # Compute norm: g_μν v^μ v^ν
    norm_expr = sym.number(0)
    for mu in range(n):
        for nu in range(n):
            norm_expr = sym.add(norm_expr,
                sym.mul(sym.mul(metric.g(mu, nu).clone(), sym.number(tangent[mu])),
                        sym.number(tangent[nu])))

    return {
        "norm": str(norm_expr),
        "classification": "timelike" if str(norm_expr).startswith("-") else "spacelike",
    }


def light_cone_at_point(metric, coord_names, point, params=None, n_rays: int = 16):
    """Compute light cone structure at a point.

    For a diagonal metric, null directions satisfy:
    g_tt (dt)² + g_rr (dr)² = 0 → dt/dr = ±√(-g_rr/g_tt)

    Returns the opening angle of the light cone in the r-t plane.
    """
    sym = rc.symbol
    n = metric.dimension()
    params = params or {}

    var_map = dict(params)
    for i in range(n):
        var_map[coord_names[i]] = float(point[i])

    g_tt_val = metric.g(0, 0).evaluate(var_map)
    g_rr_val = metric.g(1, 1).evaluate(var_map)

    # Null direction: dt/dr = ±√(-g_rr/g_tt)
    if g_tt_val >= 0:
        # Inside horizon: t becomes spacelike, r becomes timelike
        return {
            "inside_horizon": True,
            "g_tt": g_tt_val,
            "g_rr": g_rr_val,
            "note": "g_tt ≥ 0: inside event horizon, t is spacelike",
        }

    dt_dr = np.sqrt(-g_rr_val / g_tt_val)

    # Generate null rays in the t-r plane
    rays = []
    for i in range(n_rays):
        angle = 2 * np.pi * i / n_rays
        dr = np.cos(angle)
        dt = dt_dr * np.sin(angle)  # null direction
        rays.append({"dt": dt, "dr": dr, "angle": angle})

    return {
        "inside_horizon": False,
        "g_tt": g_tt_val,
        "g_rr": g_rr_val,
        "dt_dr_null": dt_dr,
        "light_cone_slope": dt_dr,
        "rays": rays,
        "note": f"Light cone opening: dt/dr = ±{dt_dr:.4f}",
    }


def causal_classification(metric, coord_names, curve_tangent, params=None):
    """Classify a curve as timelike, null, or spacelike.

    Args:
        metric: Metric object
        coord_names: coordinate names
        curve_tangent: tangent vector at a point
        params: metric parameters

    Returns:
        Dict with classification and norm
    """
    sym = rc.symbol
    n = metric.dimension()
    params = params or {}

    # Compute norm symbolically
    norm_expr = sym.number(0)
    for mu in range(n):
        for nu in range(n):
            norm_expr = sym.add(norm_expr,
                sym.mul(metric.g(mu, nu).clone(),
                        sym.mul(sym.number(curve_tangent[mu]), sym.number(curve_tangent[nu]))))

    norm_str = str(norm_expr.simplify())

    # Determine sign from string
    if norm_str.startswith("-") or norm_str.startswith("(-"):
        classification = "timelike"
    elif norm_str == "0":
        classification = "null"
    else:
        classification = "spacelike"

    return {
        "norm": norm_str,
        "classification": classification,
    }


def horizon_causal_transition(metric, coord_names, params=None, r_range=(0.5, 10), n_points=100):
    """Detect horizons by monitoring causal structure changes.

    A horizon occurs where the causal character of ∂_t changes from
    timelike to spacelike (g_tt changes sign).

    Returns list of detected horizon radii.
    """
    sym = rc.symbol
    params = params or {}

    r_vals = np.linspace(r_range[0], r_range[1], n_points)
    g_tt_vals = []

    for r_val in r_vals:
        var_map = dict(params)
        var_map["r"] = r_val
        var_map["theta"] = np.pi / 2
        var_map["t"] = 0
        var_map["phi"] = 0
        try:
            val = metric.g(0, 0).evaluate(var_map)
            g_tt_vals.append(val)
        except (ValueError, OverflowError):
            g_tt_vals.append(float('nan'))

    g_tt_vals = np.array(g_tt_vals)

    # Find sign changes
    horizons = []
    for i in range(len(g_tt_vals) - 1):
        if np.isfinite(g_tt_vals[i]) and np.isfinite(g_tt_vals[i + 1]):
            if np.sign(g_tt_vals[i]) != np.sign(g_tt_vals[i + 1]) and np.sign(g_tt_vals[i]) != 0:
                r_h = r_vals[i] - g_tt_vals[i] * (r_vals[i + 1] - r_vals[i]) / (g_tt_vals[i + 1] - g_tt_vals[i])
                if g_tt_vals[i] < 0:
                    h_type = "event_horizon"
                else:
                    h_type = "inner_horizon"
                horizons.append({"r": float(r_h), "type": h_type})

    return {
        "horizons": horizons,
        "r_values": r_vals.tolist(),
        "g_tt_values": g_tt_vals.tolist(),
    }


def singularity_analysis(metric, coord_names, params=None):
    """Analyze singularities by checking where curvature invariants diverge.

    Checks Kretschmann scalar K at various radii.
    """
    sym = rc.symbol
    params = params or {}

    K = metric.kretschmann_scalar()

    r_vals = [0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
    K_vals = []

    for r_val in r_vals:
        var_map = dict(params)
        var_map["r"] = r_val
        var_map["theta"] = np.pi / 2
        var_map["t"] = 0
        var_map["phi"] = 0
        try:
            val = K.evaluate(var_map)
            K_vals.append(val)
        except (ValueError, OverflowError):
            K_vals.append(float('inf'))

    # Find divergences
    singularities = []
    for i, (r, k) in enumerate(zip(r_vals, K_vals)):
        if abs(k) > 1e10:
            singularities.append({"r": r, "K": k, "type": "curvature_singularity"})

    return {
        "kretschmann_values": dict(zip(r_vals, K_vals)),
        "singularities": singularities,
    }
