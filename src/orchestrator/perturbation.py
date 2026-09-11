"""Linearized gravity and gravitational wave solutions (T19)."""

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


def linearized_riemann(background_metric, coord_names, h_components, params=None):
    """Compute linearized Riemann tensor R^(1)_μνρσ as nested list.

    R^(1)_μνρσ = ½(∂_ν∂_ρ h_μσ + ∂_μ∂_σ h_νρ - ∂_μ∂_ρ h_νσ - ∂_ν∂_σ h_μρ)
    """
    sym = rc.symbol
    n = background_metric.dimension()

    h = [[sym.parse(h_components[i][j]) if isinstance(h_components[i][j], str) else h_components[i][j]
          for j in range(n)] for i in range(n)]

    R = [[[[None] * n for _ in range(n)] for _ in range(n)] for _ in range(n)]
    for mu in range(n):
        for nu in range(n):
            for rho in range(n):
                for sigma in range(n):
                    t1 = h[mu][sigma].diff(coord_names[nu]).diff(coord_names[rho])
                    t2 = h[nu][rho].diff(coord_names[mu]).diff(coord_names[sigma])
                    t3 = h[nu][sigma].diff(coord_names[mu]).diff(coord_names[rho])
                    t4 = h[mu][rho].diff(coord_names[nu]).diff(coord_names[sigma])
                    R[mu][nu][rho][sigma] = sym.mul(sym.number(0.5),
                        sym.add(sym.add(t1, t2), sym.add(sym.neg(t3), sym.neg(t4)))).simplify()
    return R


def linearized_ricci(background_metric, coord_names, h_components, params=None):
    """Compute linearized Ricci tensor R^(1)_μν as nested list."""
    sym = rc.symbol
    n = background_metric.dimension()

    h = [[sym.parse(h_components[i][j]) if isinstance(h_components[i][j], str) else h_components[i][j]
          for j in range(n)] for i in range(n)]

    eta_inv = [sym.number(-1)] + [sym.number(1)] * (n - 1)

    h_trace = sym.number(0)
    for alpha in range(n):
        h_trace = sym.add(h_trace, sym.mul(eta_inv[alpha], h[alpha][alpha]))

    Ric = [[None] * n for _ in range(n)]
    for mu in range(n):
        for nu in range(n):
            box_h = sym.number(0)
            for alpha in range(n):
                box_h = sym.add(box_h, sym.mul(eta_inv[alpha],
                    h[mu][nu].diff(coord_names[alpha]).diff(coord_names[alpha])))
            d_mn_h = h_trace.diff(coord_names[mu]).diff(coord_names[nu])
            Ric[mu][nu] = sym.mul(sym.number(-0.5), sym.add(box_h, d_mn_h)).simplify()
    return Ric


def gravitational_wave_tt(omega=1.0, amplitude=1.0, coord_names=None):
    """Generate TT gauge gravitational wave perturbation."""
    if coord_names is None:
        coord_names = ["t", "x", "y", "z"]

    phase = f"{omega}*(t - z)"
    h_plus = f"{amplitude}*cos({phase})"
    h_cross = f"{amplitude}*sin({phase})"

    n = len(coord_names)
    h = [[str(rc.symbol.number(0)) for _ in range(n)] for _ in range(n)]

    x_idx = coord_names.index("x") if "x" in coord_names else 1
    y_idx = coord_names.index("y") if "y" in coord_names else 2

    h[x_idx][x_idx] = h_plus
    h[y_idx][y_idx] = f"-({h_plus})"
    h[x_idx][y_idx] = h_cross
    h[y_idx][x_idx] = h_cross

    return {
        "h_components": h,
        "description": f"GW in TT gauge: A={amplitude}, ω={omega}",
        "polarization": {"plus": h_plus, "cross": h_cross, "angle": 0.0},
        "coord_names": coord_names,
    }


def linearized_einstein_vacuum_check(coord_names, h_components):
    """Check if perturbation satisfies □h_μν = 0 (numerically)."""
    sym = rc.symbol
    n = len(coord_names)
    h = [[sym.parse(h_components[i][j]) if isinstance(h_components[i][j], str) else h_components[i][j]
          for j in range(n)] for i in range(n)]

    eta_inv = [sym.number(-1)] + [sym.number(1)] * (n - 1)
    results = {}
    all_zero = True

    for mu in range(n):
        for nu in range(n):
            box_h = sym.number(0)
            for alpha in range(n):
                d2 = h[mu][nu].diff(coord_names[alpha]).diff(coord_names[alpha])
                box_h = sym.add(box_h, sym.mul(eta_inv[alpha], d2))
            box_h = box_h.simplify()
            key = f"□h_{{{coord_names[mu]}{coord_names[nu]}}}"
            results[key] = str(box_h)
            if not box_h.is_zero():
                all_zero = False

    return {"vacuum_satisfied": all_zero, "wave_operators": results}
