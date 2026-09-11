"""Einstein field equation residual computation (T15).

Computes G_μν - 8π T_μν and related quantities.

The Einstein field equations: G_μν = 8π T_μν
Residual: R_μν = G_μν - 8π T_μν = 0 for exact solutions.
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

from .geodesic import christoffel_numerical_evaluator


def einstein_tensor(metric) -> Any:
    """Compute the Einstein tensor G_μν = R_μν - ½g_μν R.

    Returns a Tensor object.
    """
    return metric.einstein_tensor()


def stress_energy_perfect_fluid(metric, rho_expr: str, p_expr: str):
    """Build stress-energy tensor for a perfect fluid.

    T_μν = (ρ + p) u_μ u_ν + p g_μν

    For a static fluid in diagonal metric, u_μ = (-√(-g_tt), 0, 0, 0).
    Returns a list of lists of Expression objects.
    """
    n = metric.dimension()
    sym = rc.symbol
    rho = sym.parse(rho_expr)
    p = sym.parse(p_expr)

    components = []
    for mu in range(n):
        row = []
        for nu in range(n):
            if mu == nu:
                g_mu_mu = metric.g(mu, nu)
                # T_μμ = (ρ + p) u_μ u_μ + p g_μμ
                if mu == 0:
                    # T_tt = ρ * (-g_tt) for static fluid
                    row.append(sym.mul(rho, sym.neg(g_mu_mu.clone())))
                else:
                    # T_ii = p * g_ii
                    row.append(sym.mul(p, g_mu_mu.clone()))
            else:
                row.append(sym.number(0))
        components.append(row)
    return components


def field_equation_residual_symbolic(metric, T_components=None):
    """Compute the symbolic residual G_μν - κ T_μν.

    For vacuum (T=0): residual = G_μν (should be zero).
    For matter: residual = G_μν - 8π T_μν.

    Returns a Tensor of residual expressions.
    """
    G = metric.einstein_tensor()
    n = metric.dimension()

    if T_components is None:
        return G

    sym = rc.symbol
    kappa = sym.number(8 * 3.14159265358979)  # 8π

    # Build residual tensor
    dims = [n, n]
    indices = G.indices()
    residual = rc.tensor.Tensor(2, dims, indices)

    for mu in range(n):
        for nu in range(n):
            g_val = G.at([mu, nu])
            t_val = T_components[mu][nu]
            residual.at([mu, nu], rc.symbol.add(g_val, rc.symbol.neg(rc.symbol.mul(kappa, t_val))))

    return residual


def field_equation_residual_numerical(metric, coord_names, coords, params=None):
    """Compute numerical Einstein tensor G_μν at a specific point.

    For vacuum solutions, G_μν = 0.
    """
    G = metric.einstein_tensor()
    n = metric.dimension()
    params = params or {}

    var_map = dict(params)
    for i in range(n):
        var_map[coord_names[i]] = float(coords[i])

    result = np.zeros((n, n))
    for mu in range(n):
        for nu in range(n):
            result[mu, nu] = G.at([mu, nu]).evaluate(var_map)

    return result
