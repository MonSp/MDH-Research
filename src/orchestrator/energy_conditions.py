"""Energy condition checker (T20).

Energy conditions constrain the stress-energy tensor T_μν:

1. Weak Energy Condition (WEC): T_μν u^μ u^ν ≥ 0 for all timelike u^μ
   ⟺ ρ ≥ 0 and ρ + p ≥ 0

2. Strong Energy Condition (SEC): (T_μν - ½g_μν T) u^μ u^ν ≥ 0 for all timelike u^μ
   ⟺ ρ + 3p ≥ 0 and ρ + p ≥ 0

3. Dominant Energy Condition (DEC): WEC + T^μ_ν u^ν is causal (non-spacelike)
   ⟺ ρ ≥ |p|

4. Null Energy Condition (NEC): T_μν k^μ k^ν ≥ 0 for all null k^μ
   ⟺ ρ + p ≥ 0

For diagonal metrics with perfect fluid T_μν = diag(ρ, p, p, p):
the conditions reduce to simple inequalities on ρ and p.
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


def energy_density_from_stress_energy(T_components, metric, coord_names, params=None):
    """Extract energy density ρ = T_μν u^μ u^ν for a static observer.

    For a static observer in a diagonal metric:
    u^μ = (1/√(-g_tt), 0, 0, 0)
    ρ = T_tt / (-g_tt)
    """
    sym = rc.symbol
    if isinstance(T_components[0][0], str):
        T_tt = sym.parse(T_components[0][0])
    else:
        T_tt = T_components[0][0]
    g_tt = metric.g(0, 0)
    # ρ = -T_tt / g_tt (since g_tt < 0 for Lorentzian)
    return sym.mul(sym.number(-1), sym.mul(T_tt, sym.pow(g_tt.clone(), sym.number(-1))))


def pressure_from_stress_energy(T_components, metric, coord_names, i=1, params=None):
    """Extract isotropic pressure p = T_ii / g_ii for spatial index i."""
    sym = rc.symbol
    if isinstance(T_components[i][i], str):
        T_ii = sym.parse(T_components[i][i])
    else:
        T_ii = T_components[i][i]
    g_ii = metric.g(i, i)
    return sym.mul(T_ii, sym.pow(g_ii.clone(), sym.number(-1)))


def check_energy_conditions_symbolic(
    metric,
    T_components: list[list],
    coord_names: list[str],
) -> dict[str, Any]:
    """Check energy conditions symbolically for a diagonal perfect fluid.

    Returns dict with each condition's status and the relevant expressions.
    """
    sym = rc.symbol
    n = metric.dimension()

    rho = energy_density_from_stress_energy(T_components, metric, coord_names)
    p = pressure_from_stress_energy(T_components, metric, coord_names, i=1)

    rho_s = rho.simplify()
    p_s = p.simplify()

    # ρ + p
    rho_plus_p = sym.add(rho_s.clone(), p_s.clone()).simplify()

    # ρ + 3p
    rho_plus_3p = sym.add(rho_s.clone(), sym.mul(sym.number(3), p_s.clone())).simplify()

    # ρ - |p| (for DEC, we check ρ - p >= 0 for positive p)
    rho_minus_p = sym.add(rho_s.clone(), sym.neg(p_s.clone())).simplify()

    return {
        "rho": str(rho_s),
        "p": str(p_s),
        "rho_plus_p": str(rho_plus_p),
        "rho_plus_3p": str(rho_plus_3p),
        "rho_minus_p": str(rho_minus_p),
        "conditions": {
            "WEC": {
                "description": "ρ ≥ 0 and ρ + p ≥ 0",
                "requirements": [
                    {"expr": str(rho_s), "condition": "≥ 0"},
                    {"expr": str(rho_plus_p), "condition": "≥ 0"},
                ],
            },
            "SEC": {
                "description": "ρ + 3p ≥ 0 and ρ + p ≥ 0",
                "requirements": [
                    {"expr": str(rho_plus_3p), "condition": "≥ 0"},
                    {"expr": str(rho_plus_p), "condition": "≥ 0"},
                ],
            },
            "DEC": {
                "description": "ρ ≥ 0 and ρ ≥ |p|",
                "requirements": [
                    {"expr": str(rho_s), "condition": "≥ 0"},
                    {"expr": f"{rho_s} ≥ |{p_s}|", "condition": "numerical check"},
                ],
            },
            "NEC": {
                "description": "ρ + p ≥ 0",
                "requirements": [
                    {"expr": str(rho_plus_p), "condition": "≥ 0"},
                ],
            },
        },
    }


def check_energy_conditions_numerical(
    metric,
    T_components: list[list],
    coord_names: list[str],
    test_points: list[np.ndarray],
    params: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Check energy conditions numerically at specific points.

    Args:
        metric: Metric object
        T_components: stress-energy components (Expression or str)
        coord_names: coordinate names
        test_points: list of coordinate arrays to test
        params: fixed parameters

    Returns:
        Dict with numerical results at each point
    """
    sym = rc.symbol
    n = metric.dimension()
    params = params or {}

    rho = energy_density_from_stress_energy(T_components, metric, coord_names)
    p = pressure_from_stress_energy(T_components, metric, coord_names, i=1)
    rho_plus_p = sym.add(rho.clone(), p.clone())
    rho_plus_3p = sym.add(rho.clone(), sym.mul(sym.number(3), p.clone()))
    rho_minus_p = sym.add(rho.clone(), sym.neg(p.clone()))

    results = []
    for pt in test_points:
        var_map = dict(params)
        for i in range(n):
            var_map[coord_names[i]] = float(pt[i])

        rho_val = rho.evaluate(var_map)
        p_val = p.evaluate(var_map)
        rp_val = rho_plus_p.evaluate(var_map)
        r3p_val = rho_plus_3p.evaluate(var_map)
        rm_val = rho_minus_p.evaluate(var_map)

        results.append({
            "point": {coord_names[i]: float(pt[i]) for i in range(n)},
            "rho": rho_val,
            "p": p_val,
            "rho_plus_p": rp_val,
            "rho_plus_3p": r3p_val,
            "rho_minus_abs_p": rho_val - abs(p_val),
            "WEC": rho_val >= -1e-12 and rp_val >= -1e-12,
            "SEC": r3p_val >= -1e-12 and rp_val >= -1e-12,
            "DEC": rho_val >= -1e-12 and rho_val >= abs(p_val) - 1e-12,
            "NEC": rp_val >= -1e-12,
        })

    all_wec = all(r["WEC"] for r in results)
    all_sec = all(r["SEC"] for r in results)
    all_dec = all(r["DEC"] for r in results)
    all_nec = all(r["NEC"] for r in results)

    return {
        "points": results,
        "summary": {
            "WEC": "SATISFIED" if all_wec else "VIOLATED",
            "SEC": "SATISFIED" if all_sec else "VIOLATED",
            "DEC": "SATISFIED" if all_dec else "VIOLATED",
            "NEC": "SATISFIED" if all_nec else "VIOLATED",
        },
    }


def check_energy_conditions_for_metric(
    metric,
    coord_names: list[str],
    rho_expr: str,
    p_expr: str,
    test_points: list[np.ndarray] | None = None,
    params: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Convenience: check energy conditions given ρ and p expressions.

    Builds T_μν = diag(ρ, p, p, p) * g_μμ and checks all conditions.
    """
    sym = rc.symbol
    n = metric.dimension()

    # Build T_μν for perfect fluid (diagonal metric assumption)
    T = []
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                if i == 0:
                    row.append(sym.parse(rho_expr))
                else:
                    row.append(sym.parse(p_expr))
            else:
                row.append(sym.number(0))
        T.append(row)

    symbolic = check_energy_conditions_symbolic(metric, T, coord_names)

    if test_points is None:
        test_points = [np.array([0.01 * (i + 1) for i in range(n)])]

    numerical = check_energy_conditions_numerical(metric, T, coord_names, test_points, params)

    return {
        "symbolic": symbolic,
        "numerical": numerical,
    }
