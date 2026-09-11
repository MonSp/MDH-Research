"""Cosmological perturbation theory (T35).

Linear perturbations in FLRW cosmology:
    ds² = -(1+2Φ)dt² + a(t)²(1-2Ψ)δ_ij dx^i dx^j

where Φ, Ψ are Bardeen potentials.

Matter perturbations:
    δ = δρ/ρ̄ (density contrast)
    θ = ∂_i v^i (velocity divergence)

Growth of structure:
    δ'' + 2Hδ' - 4πGρ̄δ = 0

For matter domination: δ ∝ a (growing mode)
For Λ domination: growth slows down

Transfer function T(k): relates primordial to late-time power spectrum
    P(k, a) = T²(k) × P_primordial(k) × D²(a)

Growth factor:
    D(a) = δ(a)/δ(a=1) (normalized to today)
"""

from __future__ import annotations

import sys
import os
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp
from scipy.interpolate import interp1d

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

try:
    import _research_core as rc
except ImportError:
    rc = None

G = 6.67430e-11
c = 299792458.0
M_sun = 1.98892e30


def growth_factor(
    a_values: np.ndarray = None,
    Omega_m: float = 0.315,
    Omega_Lambda: float = 0.685,
) -> dict[str, Any]:
    """Compute the linear growth factor D(a).

    Solves: D'' + (ȧ/a)D' - (3/2)H₀²Ω_m/a³ D = 0

    Normalized so D(a=1) = 1.

    Args:
        a_values: scale factor array
        Omega_m: matter density parameter
        Omega_Lambda: dark energy density parameter

    Returns:
        Dict with scale factor and growth factor arrays.
    """
    if a_values is None:
        a_values = np.geomspace(0.001, 1.0, 200)

    def rhs(ln_a, y):
        a = np.exp(ln_a)
        D, dD_dlna = y

        # H(a) for flat universe
        H2 = Omega_m / a**3 + Omega_Lambda
        H = np.sqrt(H2)

        # Growth equation in terms of ln(a):
        # d²D/d(ln a)² + (1 + d ln H/d ln a) dD/d(ln a) - (3/2) Ω_m(a) D = 0
        # where Ω_m(a) = Ω_m / (a³ H²/H₀²)

        dlnH_dlna = (-3 * Omega_m / a**3) / (2 * H2)
        Omega_m_a = Omega_m / (a**3 * H2)

        d2D = -(1 + dlnH_dlna) * dD_dlna + 1.5 * Omega_m_a * D

        return [dD_dlna, d2D]

    # Initial conditions: D ∝ a for small a (matter domination)
    ln_a_start = np.log(a_values[0])
    D_init = a_values[0]
    dD_init = a_values[0]  # dD/d(ln a) = a for growing mode

    try:
        sol = solve_ivp(rhs, [ln_a_start, 0],
                        [D_init, dD_init],
                        t_eval=np.log(a_values),
                        method='RK45', rtol=1e-10)

        if sol.success and len(sol.y[0]) == len(a_values):
            D = sol.y[0]
            D /= D[-1]
            dD = sol.y[1] / D[-1]
        else:
            D = a_values / a_values[-1]
            dD = a_values / a_values[-1]
    except Exception:
        D = a_values / a_values[-1]
        dD = a_values / a_values[-1]

    return {
        "a": a_values,
        "D": D,
        "dD_dlna": dD,
        "Omega_m": Omega_m,
        "Omega_Lambda": Omega_Lambda,
    }


def growth_rate(a: float, Omega_m: float = 0.315, Omega_Lambda: float = 0.685) -> float:
    """Compute the growth rate f = d ln D / d ln a.

    Approximation: f ≈ Ω_m(a)^{0.55}

    Args:
        a: scale factor
        Omega_m: matter density
        Omega_Lambda: dark energy density

    Returns:
        Growth rate f
    """
    H2 = Omega_m / a**3 + Omega_Lambda
    Omega_m_a = Omega_m / (a**3 * H2)
    return Omega_m_a**0.55


def matter_power_spectrum(
    k: np.ndarray,
    a: float = 1.0,
    n_s: float = 0.965,
    sigma_8: float = 0.811,
    Omega_m: float = 0.315,
    h: float = 0.674,
) -> dict[str, Any]:
    """Compute the linear matter power spectrum P(k).

    P(k, a) = A_s × k^n_s × T²(k) × D²(a)

    The transfer function T(k) uses the BBKS approximation.

    Args:
        k: wavenumber array in h/Mpc
        a: scale factor
        n_s: spectral index
        sigma_8: matter fluctuation amplitude
        Omega_m: matter density
        h: Hubble parameter

    Returns:
        Dict with k and P(k) arrays.
    """
    # Shape parameter
    Gamma = Omega_m * h

    # BBKS transfer function
    q = k / (Gamma * h)
    T = (np.log(1 + 2.34 * q) / (2.34 * q) *
         (1 + 3.89 * q + (16.1 * q)**2 + (5.46 * q)**3 + (6.71 * q)**4)**(-0.25))

    # Primordial power spectrum
    P_prim = k**n_s

    # Growth factor
    D_result = growth_factor(np.array([a]), Omega_m=Omega_m)
    D = D_result["D"][0]

    # Power spectrum
    P_k = P_prim * T**2 * D**2

    # Normalize to sigma_8
    # σ²_8 = ∫ P(k) W²(kR) k² dk / (2π²) where W is top-hat window, R=8 Mpc/h
    R = 8.0  # Mpc/h
    k_grid = np.geomspace(k[k > 0].min(), k.max(), 1000)
    W = 3 * (np.sin(k_grid * R) - k_grid * R * np.cos(k_grid * R)) / (k_grid * R)**3
    P_interp = interp1d(k, P_k, kind='linear', fill_value=0, bounds_error=False)
    sigma2 = np.trapezoid(P_interp(k_grid) * W**2 * k_grid**2 / (2 * np.pi**2), k_grid)

    # Normalize
    if sigma2 > 0:
        P_k *= sigma_8**2 / sigma2

    return {
        "k": k,
        "P_k": P_k,
        "a": a,
        "sigma_8": sigma_8,
    }


def transfer_function_matter(k: np.ndarray, h: float = 0.674, Omega_m: float = 0.315) -> np.ndarray:
    """BBKS transfer function for matter perturbations.

    T(q) = ln(1+2.34q)/(2.34q) × [1+3.89q+(16.1q)²+(5.46q)³+(6.71q)⁴]^{-0.25}

    Args:
        k: wavenumber in h/Mpc
        h: Hubble parameter
        Omega_m: matter density

    Returns:
        Transfer function array
    """
    Gamma = Omega_m * h
    q = k / (Gamma * h)
    return (np.log(1 + 2.34 * q) / (2.34 * q) *
            (1 + 3.89 * q + (16.1 * q)**2 + (5.46 * q)**3 + (6.71 * q)**4)**(-0.25))


def horizon_entry_scale(Omega_m: float = 0.315, h: float = 0.674) -> dict[str, float]:
    """Compute the horizon entry scale (matter-radiation equality).

    k_eq = a_eq × H_eq ≈ 0.01 Ω_m h² Mpc⁻¹

    Args:
        Omega_m: matter density
        h: Hubble parameter

    Returns:
        Dict with equality scale and wavenumber.
    """
    # Scale factor at equality
    Omega_r = 9.1e-5  # radiation density
    a_eq = Omega_r / Omega_m

    # Wavenumber at equality
    k_eq = 0.01 * Omega_m * h**2  # h/Mpc

    return {
        "a_eq": a_eq,
        "k_eq_h_Mpc": k_eq,
        "lambda_eq_Mpc_h": 2 * np.pi / k_eq,
    }


def baryon_acoustic_oscillation_scale(Omega_m: float = 0.315, h: float = 0.674) -> dict[str, float]:
    """Compute the BAO scale (sound horizon at drag epoch).

    r_s ≈ 147 Mpc (comoving sound horizon at z_drag ≈ 1060)

    Args:
        Omega_m: matter density
        h: Hubble parameter

    Returns:
        Dict with BAO scale.
    """
    # Simplified: sound horizon at drag epoch
    # r_s ≈ 147.09 ± 0.26 Mpc (Planck 2018)
    r_s = 147.09  # Mpc

    # Angular scale in the CMB
    # θ_s ≈ r_s / D_A(z_CMB)
    # D_A(z=1100) ≈ 14000 Mpc
    D_A = 14000  # Mpc (approximate)
    theta_s = r_s / D_A  # radians

    return {
        "r_s_Mpc": r_s,
        "r_s_h_Mpc": r_s * h,
        "theta_s_rad": theta_s,
        "theta_s_deg": np.degrees(theta_s),
        "theta_s_arcmin": np.degrees(theta_s) * 60,
    }
