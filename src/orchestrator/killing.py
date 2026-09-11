"""Killing vector field detection and spacetime symmetry analysis (T18).

A Killing vector field ξ^μ satisfies the Killing equation:
    ∇_μ ξ_ν + ∇_ν ξ_μ = 0
"""

from __future__ import annotations

import sys
import os
import numpy as np

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

try:
    import _research_core as rc
except ImportError:
    rc = None


def killing_equation_residual(metric, coord_names, xi_components, params=None):
    """Compute L_ξ g_μν = ∇_μ ξ_ν + ∇_ν ξ_μ as a nested list of Expressions."""
    sym = rc.symbol
    n = metric.dimension()
    Gamma = metric.christoffel_symbols()

    xi = [sym.parse(c) if isinstance(c, str) else c for c in xi_components]

    # Lower index: ξ_ν = g_νσ ξ^σ
    xi_lo = []
    for nu in range(n):
        val = sym.number(0)
        for sigma in range(n):
            val = sym.add(val, sym.mul(metric.g(nu, sigma).clone(), xi[sigma].clone()))
        xi_lo.append(val.simplify())

    # ∇_μ ξ_ν = ∂_μ ξ_ν - Γ^ρ_μν ξ_ρ
    nabla = [[None] * n for _ in range(n)]
    for mu in range(n):
        for nu in range(n):
            dxi = xi_lo[nu].diff(coord_names[mu])
            conn = sym.number(0)
            for rho in range(n):
                conn = sym.add(conn, sym.neg(sym.mul(Gamma.at([rho, mu, nu]).clone(), xi_lo[rho].clone())))
            nabla[mu][nu] = sym.add(dxi, conn).simplify()

    # Residual: ∇_μ ξ_ν + ∇_ν ξ_μ
    return [[sym.add(nabla[mu][nu], nabla[nu][mu]).simplify() for nu in range(n)] for mu in range(n)]


def is_killing_vector(metric, coord_names, xi_components, params=None, test_points=None, tol=1e-10):
    """Check if ξ is a Killing vector by numerical evaluation at test points."""
    residual = killing_equation_residual(metric, coord_names, xi_components, params)
    n = metric.dimension()
    params = params or {}

    if test_points is None:
        test_points = [np.array([0.1 * (i + 1) for i in range(n)])]

    for pt in test_points:
        var_map = dict(params)
        for i in range(n):
            var_map[coord_names[i]] = float(pt[i])
        for mu in range(n):
            for nu in range(n):
                if abs(residual[mu][nu].evaluate(var_map)) > tol:
                    return False
    return True


def detect_coordinate_killing_vectors(metric, coord_names, params=None):
    """Test each coordinate basis vector ∂_μ as a Killing vector candidate."""
    n = metric.dimension()
    results = {}
    for mu in range(n):
        xi = ["0"] * n
        xi[mu] = "1"
        results[f"d/d{coord_names[mu]}"] = is_killing_vector(metric, coord_names, xi, params)
    return results


def classify_symmetry(metric, coord_names, params=None):
    """Classify spacetime symmetry from Killing vectors."""
    killing = detect_coordinate_killing_vectors(metric, coord_names, params)
    n = metric.dimension()

    stationary = killing.get(f"d/d{coord_names[0]}", False)
    static = False
    if stationary:
        static = all(metric.g(0, i).is_zero() for i in range(1, n))

    axisymmetric = False
    for i in range(1, n):
        if killing.get(f"d/d{coord_names[i]}", False):
            if 'phi' in coord_names[i].lower() or 'φ' in coord_names[i]:
                axisymmetric = True

    return {
        "killing_vectors": killing,
        "stationary": stationary,
        "static": static,
        "axisymmetric": axisymmetric,
    }
