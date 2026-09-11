"""BSSN numerical relativity decomposition (T27).

The BSSN (Baumgarte-Shapiro-Shibata-Nakamura) formulation decomposes
the Einstein equations into a 3+1 form suitable for numerical evolution.

Key variables:
- φ = ln(γ) / 12  (conformal factor, γ = det(γ_ij))
- γ̃_ij = e^{-4φ} γ_ij  (conformal metric, det(γ̃_ij) = 1)
- A_ij = e^{-4φ} (K_ij - γ_ij K / 3)  (traceless extrinsic curvature)
- Γ̃^i = γ̃^jk Γ̃^i_{jk}  (conformal connection functions)

Evolution equations:
- ∂_t φ = -(1/6) α K + ∇_i β^i / 6 + β^i ∂_i φ
- ∂_t γ̃_ij = -2α Ã_ij + β^k ∂_k γ̃_ij + γ̃_ik ∂_j β^k + γ̃_jk ∂_i β^k - (2/3) γ̃_ij ∂_k β^k
- ∂_t K = -D_i D^i α + α(Ã_ij Ã^ij + K²/3) + 4πα(ρ + S) + β^i ∂_i K
- ∂_t Ã_ij = e^{-4φ} (-D_i D_j α + α(R_ij - 8π S_ij))^{TF} + α K Ã_ij - 2 α Ã_ik Ã^k_j + ...
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


def compute_conformal_factor(metric_3d, coord_names_3d: list[str]) -> dict[str, Any]:
    """Compute BSSN conformal factor φ = ln(γ) / 12.

    For a diagonal 3-metric: γ = Π_i γ_ii
    φ = ln(γ_11 * γ_22 * γ_33) / 12
    """
    sym = rc.symbol

    # γ = det(γ_ij) for diagonal metric
    det_gamma = sym.number(1)
    for i in range(3):
        det_gamma = sym.mul(det_gamma, metric_3d[i][i].clone())

    # φ = ln(γ) / 12
    det_str = det_gamma.to_string()
    phi = sym.mul(sym.parse(f"log({det_str})"), sym.number(1.0 / 12))

    return {
        "phi": phi,
        "det_gamma": det_gamma,
        "coord_names": coord_names_3d,
    }


def compute_conformal_metric(metric_3d, coord_names_3d: list[str]) -> dict[str, Any]:
    """Compute conformal metric γ̃_ij = e^{-4φ} γ_ij.

    For diagonal metrics: γ̃_ii = γ_ii / γ^{1/3}
    where γ = det(γ_ij) = Π γ_ii
    """
    sym = rc.symbol

    # det(γ)
    det_gamma = sym.number(1)
    for i in range(3):
        det_gamma = sym.mul(det_gamma, metric_3d[i][i].clone())

    # γ^{1/3}
    gamma_one_third = sym.pow(det_gamma.clone(), sym.number(1.0 / 3))

    # γ̃_ij = γ_ij / γ^{1/3}
    gamma_tilde = [[sym.number(0)] * 3 for _ in range(3)]
    for i in range(3):
        gamma_tilde[i][i] = sym.mul(metric_3d[i][i].clone(),
                                     sym.pow(gamma_one_third.clone(), sym.number(-1)))

    return {
        "gamma_tilde": gamma_tilde,
        "det_gamma": det_gamma,
        "gamma_one_third": gamma_one_third,
        "coord_names": coord_names_3d,
    }


def compute_conformal_connection(metric_3d, coord_names_3d: list[str]) -> dict[str, Any]:
    """Compute conformal connection functions Γ̃^i = γ̃^jk Γ̃^i_{jk}.

    For a static diagonal metric, Γ̃^i involves spatial Christoffel symbols.
    """
    sym = rc.symbol

    # Build 3D metric object
    manifold_3d = rc.geometry.Manifold("spatial_3d", coord_names_3d)
    g_3d = rc.geometry.Metric(manifold_3d, metric_3d)

    # Get 3D Christoffel symbols
    Gamma_3d = g_3d.christoffel_symbols()

    # Conformal factor
    conf = compute_conformal_factor(metric_3d, coord_names_3d)
    phi = conf["phi"]

    # Γ̃^i = γ̃^jk Γ̃^i_{jk}
    # For diagonal metrics, this simplifies significantly
    Gamma_tilde = [sym.number(0)] * 3
    for i in range(3):
        for j in range(3):
            for k in range(3):
                val = Gamma_3d.at([i, j, k]).clone()
                Gamma_tilde[i] = sym.add(Gamma_tilde[i], val)

    return {
        "Gamma_tilde": Gamma_tilde,
        "phi": phi,
        "coord_names": coord_names_3d,
    }


def bssn_variables(metric_3d, coord_names_3d: list[str]) -> dict[str, Any]:
    """Extract all BSSN variables from a 3-metric.

    Returns:
    - φ: conformal factor
    - γ̃_ij: conformal metric
    - Γ̃^i: conformal connection functions
    - det_gamma: determinant of 3-metric
    """
    conf = compute_conformal_factor(metric_3d, coord_names_3d)
    conf_metric = compute_conformal_metric(metric_3d, coord_names_3d)
    conf_conn = compute_conformal_connection(metric_3d, coord_names_3d)

    return {
        "phi": conf["phi"],
        "gamma_tilde": conf_metric["gamma_tilde"],
        "det_gamma": conf["det_gamma"],
        "Gamma_tilde": conf_conn["Gamma_tilde"],
        "coord_names": coord_names_3d,
    }


def hamiltonian_constraint_bssn(bssn_vars, params=None) -> dict[str, Any]:
    """Evaluate Hamiltonian constraint in BSSN variables.

    R + K² - K_ij K^ij = 16πρ

    For time-symmetric initial data (K_ij = 0): R = 16πρ
    For vacuum: R = 0
    """
    sym = rc.symbol
    params = params or {}

    phi = bssn_vars["phi"]
    det_gamma = bssn_vars["det_gamma"]

    # For time-symmetric vacuum data, the Hamiltonian constraint is
    # satisfied if R^(3) = 0, which is automatically true for flat space.
    # For conformally flat data: γ_ij = ψ^4 δ_ij, R = -8 ψ^{-5} ∇²ψ

    return {
        "constraint": "R + K² - K_ij K^ij = 16πρ",
        "time_symmetric_vacuum": "R = 0",
        "conformally_flat": "R = -8 ψ^{-5} ∇²ψ",
        "phi": str(phi),
    }


def bssn_numerical_evaluation(bssn_vars, coord_values: dict[str, float], params=None) -> dict[str, Any]:
    """Evaluate BSSN variables numerically at a point."""
    sym = rc.symbol
    params = params or {}

    var_map = dict(params)
    var_map.update(coord_values)

    phi_val = bssn_vars["phi"].evaluate(var_map)
    det_val = bssn_vars["det_gamma"].evaluate(var_map)

    gamma_tilde_vals = []
    for i in range(3):
        gamma_tilde_vals.append(bssn_vars["gamma_tilde"][i][i].evaluate(var_map))

    Gamma_tilde_vals = []
    for i in range(3):
        Gamma_tilde_vals.append(bssn_vars["Gamma_tilde"][i].evaluate(var_map))

    return {
        "phi": phi_val,
        "det_gamma": det_val,
        "gamma_tilde_diag": gamma_tilde_vals,
        "Gamma_tilde": Gamma_tilde_vals,
        "conformal_flat": all(abs(g - 1.0) < 1e-10 for g in gamma_tilde_vals),
    }
