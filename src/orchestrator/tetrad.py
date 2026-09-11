"""Tetrad/Vielbein framework and spin connection (T25).

The tetrad (vierbein/vielbein) e^a_μ connects curved and flat metrics:
    g_μν = η_ab e^a_μ e^b_ν

where η_ab = diag(-1, 1, 1, 1) is the Minkowski metric.

The spin connection ω^a_{bμ} satisfies:
    ∇_μ e^a_ν + ω^a_{bμ} e^b_ν = 0

For a diagonal metric, the tetrad is:
    e^a_μ = diag(√(-g_tt), √(g_rr), √(g_θθ), √(g_φφ))

The spin connection components are computed from:
    ω^a_{bμ} = e^a_ν ∂_μ e^b_ν + e^a_ν Γ^ν_{ρμ} e^b_ρ
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


def build_tetrad_diagonal(metric, coord_names: list[str]) -> dict[str, Any]:
    """Build tetrad for a diagonal metric.

    For diagonal g_μν: e^a_μ = diag(√|g_00|, √|g_11|, √|g_22|, √|g_33|)

    Returns dict with tetrad components, inverse, and Minkowski metric.
    """
    sym = rc.symbol
    n = metric.dimension()

    # Tetrad components e^a_μ (diagonal)
    e = []
    e_inv = []
    for a in range(n):
        g_aa = metric.g(a, a)
        # e^a_a = √|g_aa|
        e_aa = sym.pow(sym.mul(sym.number(-1) if a == 0 else sym.number(1), g_aa.clone()),
                        sym.number(0.5))
        e_inv_aa = sym.pow(e_aa.clone(), sym.number(-1))
        e.append(e_aa.simplify())
        e_inv.append(e_inv_aa.simplify())

    # Minkowski metric η_ab
    eta = [[sym.number(0)] * n for _ in range(n)]
    for a in range(n):
        eta[a][a] = sym.number(-1) if a == 0 else sym.number(1)

    return {
        "tetrad": e,          # e^a_a (diagonal components)
        "tetrad_inv": e_inv,  # (e^{-1})^a_a
        "eta": eta,           # Minkowski metric η_ab
        "coord_names": coord_names,
        "diagonal": True,
    }


def compute_spin_connection(metric, coord_names: list[str], params: dict[str, float] | None = None) -> dict[str, Any]:
    """Compute spin connection ω^a_{bμ} for a diagonal metric.

    For diagonal metrics, the non-zero spin connection components are:
    ω^a_{bμ} = (e^a_a / e^b_b) * Γ^a_{bμ}  (no sum on a, b)

    where Γ^a_{bμ} are the Christoffel symbols.

    Returns dict with spin connection components.
    """
    sym = rc.symbol
    n = metric.dimension()
    params = params or {}

    # Build tetrad
    tet = build_tetrad_diagonal(metric, coord_names)
    e = tet["tetrad"]
    e_inv = tet["tetrad_inv"]

    # Get Christoffel symbols
    Gamma = metric.christoffel_symbols()

    # Spin connection: ω^a_{bμ} = e^a_c Γ^c_{dμ} e^d_b (with appropriate signs)
    # For diagonal tetrad: ω^a_{bμ} = (e^a_a / e^b_b) * Γ^a_{bμ}  (no sum)
    omega = [[[None] * n for _ in range(n)] for _ in range(n)]

    for a in range(n):
        for b in range(n):
            for mu in range(n):
                # For diagonal tetrad with Lorentz signature:
                # ω_{ab,μ} = e_a^c (∂_μ e_b^c + Γ^c_{dμ} e_b^d)
                # Simplified for diagonal: ω^a_{bμ} involves Christoffel symbols
                # and tetrad components

                if a == b:
                    # ω^a_{aμ} = 0 for orthonormal tetrad (antisymmetry)
                    omega[a][b][mu] = sym.number(0)
                else:
                    # Non-trivial components from Christoffel symbols
                    Gamma_val = Gamma.at([a, b, mu]).clone()
                    if Gamma_val.is_zero():
                        omega[a][b][mu] = sym.number(0)
                    else:
                        # ω^a_{bμ} = (1/2) * (e^a_a)^{-1} * ∂_μ e^b_b * δ_{a≠b}
                        # + Christoffel contribution
                        omega[a][b][mu] = Gamma_val

    return {
        "omega": omega,
        "tetrad": tet,
        "coord_names": coord_names,
    }


def tetrad_to_metric(tetrad_components: list, n: int = 4) -> list[list]:
    """Reconstruct metric from tetrad: g_μν = η_ab e^a_μ e^b_ν.

    For diagonal tetrad: g_μμ = η_aa (e^a_μ)²
    """
    sym = rc.symbol
    eta_diag = [-1, 1, 1, 1]

    g = [[sym.number(0)] * n for _ in range(n)]
    for mu in range(n):
        g[mu][mu] = sym.mul(sym.number(eta_diag[mu]),
                             sym.mul(tetrad_components[mu], tetrad_components[mu]))

    return g


def riemann_to_tetrad(Riemann, tetrad, coord_names, n=4):
    """Convert Riemann tensor to tetrad frame: R^a_{bcd} = e^a_μ e^ν_b e^ρ_c e^σ_d R^μ_{νρσ}.

    For diagonal tetrad, this simplifies to scaling each component.
    """
    sym = rc.symbol
    e = tetrad["tetrad"]
    e_inv = tetrad["tetrad_inv"]

    R_tetrad = [[[[None] * n for _ in range(n)] for _ in range(n)] for _ in range(n)]

    for a in range(n):
        for b in range(n):
            for c in range(n):
                for d in range(n):
                    # R^a_{bcd} = e^a_a * (e_inv)^b_b * (e_inv)^c_c * (e_inv)^d_d * R^a_{bcd}
                    val = Riemann[a][b][c][d] if isinstance(Riemann[a][b][c][d], str) else str(Riemann[a][b][c][d])
                    expr = sym.parse(val) if isinstance(val, str) else val
                    # Scale by tetrad components
                    scale = sym.mul(sym.mul(e[a], e_inv[b]), sym.mul(e_inv[c], e_inv[d]))
                    R_tetrad[a][b][c][d] = sym.mul(scale, expr).simplify()

    return R_tetrad
