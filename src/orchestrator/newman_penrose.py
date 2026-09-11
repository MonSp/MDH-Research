"""Newman-Penrose formalism and Weyl scalar classification (T26).

The NP formalism uses a null tetrad (l, n, m, m̄) where:
- l^μ, n^μ: real null vectors
- m^μ, m̄^μ: complex null vectors (conjugate pair)

Normalization: l·n = -1, m·m̄ = 1, all other products = 0.

The five complex Weyl scalars classify spacetimes:
- Ψ₀: transverse outgoing radiation
- Ψ₁: longitudinal outgoing radiation
- Ψ₂: Coulomb component (mass/charge)
- Ψ₃: longitudinal ingoing radiation
- Ψ₄: transverse ingoing radiation

Petrov classification:
- Type I: Ψ₀ ≠ 0, Ψ₂ = Ψ₄ = 0 (algebraically general)
- Type II: Ψ₁ ≠ 0, Ψ₃ = Ψ₄ = 0
- Type D: Ψ₂ ≠ 0, Ψ₀ = Ψ₁ = Ψ₃ = Ψ₄ = 0 (Schwarzschild, Kerr)
- Type III: Ψ₃ ≠ 0, Ψ₀ = Ψ₁ = Ψ₂ = Ψ₄ = 0
- Type N: Ψ₄ ≠ 0, Ψ₀ = Ψ₁ = Ψ₂ = Ψ₃ = 0 (pp-waves)
- Type O: all Ψ_i = 0 (conformally flat)
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


def build_null_tetrad_diagonal(metric, coord_names: list[str], params: dict[str, float] | None = None) -> dict[str, Any]:
    """Build a null tetrad from a diagonal metric.

    For diagonal metric ds² = -A²dt² + B²dr² + C²dθ² + D²dφ²:
    l^μ = (1/A, 1/B, 0, 0)     (outgoing null)
    n^μ = (1/A, -1/B, 0, 0)    (ingoing null)
    m^μ = (0, 0, 1/(C√2), i/(D√2))  (complex null)

    Returns dict with null tetrad vectors.
    """
    sym = rc.symbol
    n = metric.dimension()

    # Extract diagonal metric components
    g_diag = []
    for i in range(n):
        g_diag.append(metric.g(i, i))

    # Build orthonormal tetrad first
    # e^0 = √(-g_tt), e^1 = √(g_rr), e^2 = √(g_θθ), e^3 = √(g_φφ)
    e = []
    for i in range(n):
        sign = sym.number(-1) if i == 0 else sym.number(1)
        e.append(sym.pow(sym.mul(sign, g_diag[i].clone()), sym.number(0.5)))

    # Null tetrad:
    # l^μ = (e₀⁻¹, e₁⁻¹, 0, 0) / √2
    # n^μ = (e₀⁻¹, -e₁⁻¹, 0, 0) / √2
    # m^μ = (0, 0, e₂⁻¹, i·e₃⁻¹) / √2

    inv_sqrt2 = sym.number(1.0 / np.sqrt(2))

    l_vec = [sym.mul(inv_sqrt2, sym.pow(e[0], sym.number(-1))),
             sym.mul(inv_sqrt2, sym.pow(e[1], sym.number(-1))),
             sym.number(0), sym.number(0)]

    n_vec = [sym.mul(inv_sqrt2, sym.pow(e[0], sym.number(-1))),
             sym.neg(sym.mul(inv_sqrt2, sym.pow(e[1], sym.number(-1)))),
             sym.number(0), sym.number(0)]

    # m is complex; store real and imaginary parts separately
    m_real = [sym.number(0), sym.number(0),
              sym.mul(inv_sqrt2, sym.pow(e[2], sym.number(-1))),
              sym.number(0)]
    m_imag = [sym.number(0), sym.number(0), sym.number(0),
              sym.mul(inv_sqrt2, sym.pow(e[3], sym.number(-1)))]

    return {
        "l": l_vec,
        "n": n_vec,
        "m_real": m_real,
        "m_imag": m_imag,
        "e": e,
        "coord_names": coord_names,
    }


def compute_weyl_scalars_from_riemann(Riemann, metric, coord_names, params=None):
    """Compute Weyl scalars Ψ₀...Ψ₄ from the Riemann tensor.

    For vacuum spacetimes (Ricci = 0), the Riemann tensor equals the Weyl tensor.
    The Weyl scalars are projections of the Weyl tensor onto the null tetrad.

    Simplified computation for diagonal metrics:
    Ψ₀ = C_{abcd} l^a m^b l^c m^d
    Ψ₁ = C_{abcd} l^a n^b l^c m^d
    Ψ₂ = C_{abcd} l^a m^b m̄^c n^d
    Ψ₃ = C_{abcd} l^a n^b m̄^c n^d
    Ψ₄ = C_{abcd} n^a m̄^b n^c m̄^d

    For vacuum: use Riemann directly as Weyl tensor.
    """
    sym = rc.symbol
    n_dim = metric.dimension()

    # Build null tetrad
    tet = build_null_tetrad_diagonal(metric, coord_names, params)
    l = tet["l"]
    n_vec = tet["n"]
    e = tet["e"]

    # For diagonal metrics, compute simplified Weyl scalars
    # The key Riemann components in tetrad frame give the Weyl scalars

    # Ψ₂ is the most important — it's the Coulomb component
    # For Schwarzschild: Ψ₂ = -M/r³
    # For Kerr: Ψ₂ = -M/(r - ia·cosθ)³

    # Simplified: extract Ψ₂ from R^0_{101} component
    # R^0_{101} in tetrad frame ≈ Ψ₂ for Petrov type D

    psi_values = {}
    psi_expressions = {}

    # For diagonal vacuum metrics, the Weyl scalars can be read from
    # specific Riemann components in the tetrad frame

    # Ψ₀ ~ R_{0101} (outgoing radiation)
    # Ψ₂ ~ R_{0212} (Coulomb)
    # Ψ₄ ~ R_{2323} (ingoing radiation)

    # For Schwarzschild/Kerr (Type D): only Ψ₂ ≠ 0
    # Ψ₂ = -M/r³ (Schwarzschild)

    # Numerical evaluation
    if params:
        var_map = dict(params)
        for coord in coord_names:
            if coord not in var_map:
                var_map[coord] = 1.0

        # Evaluate key Riemann components
        R_0101 = Riemann[0][1][0][1].evaluate(var_map) if not isinstance(Riemann[0][1][0][1], str) else 0
        R_0202 = Riemann[0][2][0][2].evaluate(var_map) if not isinstance(Riemann[0][2][0][2], str) else 0
        R_0303 = Riemann[0][3][0][3].evaluate(var_map) if not isinstance(Riemann[0][3][0][3], str) else 0
        R_1212 = Riemann[1][2][1][2].evaluate(var_map) if not isinstance(Riemann[1][2][1][2], str) else 0
        R_1313 = Riemann[1][3][1][3].evaluate(var_map) if not isinstance(Riemann[1][3][1][3], str) else 0
        R_2323 = Riemann[2][3][2][3].evaluate(var_map) if not isinstance(Riemann[2][3][2][3], str) else 0

        # Simplified Weyl scalars from Riemann components
        # These are approximations for diagonal metrics
        psi_values = {
            "Psi_0": R_0101,
            "Psi_1": 0.0,  # Typically zero for diagonal metrics
            "Psi_2": (R_0202 + R_0303) / 2,  # Coulomb component
            "Psi_3": 0.0,
            "Psi_4": R_2323,
        }

    return {
        "weyl_scalars": psi_values,
        "null_tetrad": tet,
        "coord_names": coord_names,
    }


def classify_petrov_type(weyl_scalars: dict[str, float], tol: float = 1e-10) -> dict[str, Any]:
    """Classify Petrov type from Weyl scalars.

    Petrov classification:
    - Type I: Ψ₀ ≠ 0 (algebraically general)
    - Type D: Ψ₂ ≠ 0, others ≈ 0 (Schwarzschild, Kerr)
    - Type N: Ψ₄ ≠ 0, others ≈ 0 (pp-waves)
    - Type O: all ≈ 0 (conformally flat)
    """
    psi = weyl_scalars.get("weyl_scalars", weyl_scalars)

    nonzero = {}
    for key in ["Psi_0", "Psi_1", "Psi_2", "Psi_3", "Psi_4"]:
        val = psi.get(key, 0)
        nonzero[key] = abs(val) > tol

    # Classification logic
    if not any(nonzero.values()):
        petrov_type = "O"
        description = "Conformally flat (all Weyl scalars vanish)"
    elif nonzero.get("Psi_2", False) and not any(nonzero.get(k, False) for k in ["Psi_0", "Psi_1", "Psi_3", "Psi_4"]):
        petrov_type = "D"
        description = "Type D (Schwarzschild/Kerr — only Ψ₂ ≠ 0)"
    elif nonzero.get("Psi_0", False) and not any(nonzero.get(k, False) for k in ["Psi_1", "Psi_2", "Psi_3", "Psi_4"]):
        petrov_type = "I"
        description = "Type I (algebraically general — only Ψ₀ ≠ 0)"
    elif nonzero.get("Psi_4", False) and not any(nonzero.get(k, False) for k in ["Psi_0", "Psi_1", "Psi_2", "Psi_3"]):
        petrov_type = "N"
        description = "Type N (pp-wave — only Ψ₄ ≠ 0)"
    elif nonzero.get("Psi_1", False) and not nonzero.get("Psi_3", False) and not nonzero.get("Psi_4", False):
        petrov_type = "II"
        description = "Type II"
    elif nonzero.get("Psi_3", False) and not nonzero.get("Psi_0", False) and not nonzero.get("Psi_1", False):
        petrov_type = "III"
        description = "Type III"
    else:
        petrov_type = "I"
        description = "Type I (general)"

    return {
        "petrov_type": petrov_type,
        "description": description,
        "nonzero_scalars": nonzero,
        "values": psi,
    }
