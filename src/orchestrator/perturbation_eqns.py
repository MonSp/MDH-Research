"""Regge-Wheeler and Zerilli perturbation equation solvers (T29).

The Regge-Wheeler equation governs odd-parity (axial) perturbations
of Schwarzschild black holes:

    d²Ψ/dr*² + [ω² - V_RW(r)] Ψ = 0

where r* is the tortoise coordinate and V_RW is the Regge-Wheeler potential:
    V_RW = (1 - 2M/r) [l(l+1)/r² - 6M/r³]

The Zerilli equation governs even-parity (polar) perturbations:
    d²Ψ/dr*² + [ω² - V_Z(r)] Ψ = 0

with the Zerilli potential:
    V_Z = (1 - 2M/r) / (Λr + 3M)² × [2λ²(λ + 1)/r³ + 6λ²M/r⁴ + 18λM²/r⁵ + 18M³/r⁶]
    where λ = (l-1)(l+2)/2, Λ = λ + 3M/r
"""

from __future__ import annotations

import sys
import os
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

try:
    import _research_core as rc
except ImportError:
    rc = None


def tortoise_coordinate(r: np.ndarray, M: float) -> np.ndarray:
    """Compute tortoise coordinate r* = r + 2M ln(r/(2M) - 1).

    Args:
        r: radial coordinate array
        M: black hole mass

    Returns:
        Tortoise coordinate array
    """
    return r + 2 * M * np.log(r / (2 * M) - 1)


def regge_wheeler_potential(r: np.ndarray, l: int, M: float) -> np.ndarray:
    """Compute the Regge-Wheeler potential.

    V_RW = (1 - 2M/r) [l(l+1)/r² - 6M/r³]

    Args:
        r: radial coordinate
        l: angular mode number
        M: black hole mass

    Returns:
        Potential array
    """
    f = 1 - 2 * M / r
    return f * (l * (l + 1) / r**2 - 6 * M / r**3)


def zerilli_potential(r: np.ndarray, l: int, M: float) -> np.ndarray:
    """Compute the Zerilli potential.

    V_Z = (1 - 2M/r) / (Λr + 3M)² × [2λ²(λ+1)/r³ + 6λ²M/r⁴ + 18λM²/r⁵ + 18M³/r⁶]

    Args:
        r: radial coordinate
        l: angular mode number
        M: black hole mass

    Returns:
        Potential array
    """
    f = 1 - 2 * M / r
    lam = (l - 1) * (l + 2) / 2  # λ = (l-1)(l+2)/2
    Lambda = lam + 3 * M / r  # Λ = λ + 3M/r

    numerator = (2 * lam**2 * (lam + 1) / r**3 +
                 6 * lam**2 * M / r**4 +
                 18 * lam * M**2 / r**5 +
                 18 * M**3 / r**6)

    return f * numerator / (Lambda * r + 3 * M)**2


def solve_regge_wheeler(
    M: float = 1.0,
    l: int = 2,
    omega: complex = 0.37 - 0.09j,
    r_min: float = 2.01,
    r_max: float = 200.0,
    n_points: int = 1000,
) -> dict[str, Any]:
    """Solve the Regge-Wheeler equation numerically.

    Uses the tortoise coordinate and integrates from r_min outward.

    Args:
        M: black hole mass
        l: angular mode number
        omega: complex frequency
        r_min: inner boundary (just outside horizon)
        r_max: outer boundary
        n_points: number of grid points

    Returns:
        Dict with radial grid, solution, potential, and tortoise coordinate.
    """
    r = np.linspace(r_min, r_max, n_points)
    r_star = tortoise_coordinate(r, M)
    V = regge_wheeler_potential(r, l, M)

    # Convert to tortoise coordinate system
    # d²Ψ/dr*² + [ω² - V(r)] Ψ = 0
    # → dΨ/dr* = Ψ', dΨ'/dr* = -(ω² - V) Ψ

    # For complex ω, solve real and imaginary parts separately
    omega_R = omega.real
    omega_I = omega.imag

    # Initial conditions: incoming wave from infinity
    # Ψ ~ e^{-iωr*} as r* → ∞
    psi_0 = np.exp(-1j * omega * r_star[0])
    dpsi_0 = -1j * omega * psi_0

    # Integrate using solve_ivp
    def rhs(r_star_val, y):
        # Interpolate V at this r_star
        r_val = np.interp(r_star_val, r_star, r)
        V_val = np.interp(r_star_val, r_star, V)
        psi, dpsi = y
        d2psi = -(omega**2 - V_val) * psi
        return [dpsi, d2psi]

    sol = solve_ivp(rhs, [r_star[0], r_star[-1]],
                    [psi_0, dpsi_0],
                    t_eval=r_star,
                    method='RK45',
                    rtol=1e-10, atol=1e-12)

    return {
        "r": r,
        "r_star": r_star,
        "psi": sol.y[0],
        "dpsi": sol.y[1],
        "potential": V,
        "omega": omega,
        "l": l,
        "M": M,
        "success": sol.success,
    }


def compute_gw_strain(
    M: float = 1.0,
    l: int = 2,
    m: int = 2,
    omega: complex = 0.37 - 0.09j,
    r_obs: float = 100.0,
    t_max: float = 200.0,
    dt: float = 0.5,
) -> dict[str, Any]:
    """Compute gravitational wave strain h(t) from QNM.

    The strain is:
    h(t) = (1/r_obs) Ψ(t) × Y_lm(θ, φ)

    For the dominant l=m=2 mode:
    h₊(t) = A cos(ω_R t) exp(ω_I t)
    h×(t) = A sin(ω_R t) exp(ω_I t)

    Args:
        M: black hole mass
        l: angular mode
        m: azimuthal mode
        omega: complex QNM frequency
        r_obs: observer distance
        t_max: maximum time
        dt: time step

    Returns:
        Dict with time array, strain h₊ and h×, and parameters.
    """
    t = np.arange(0, t_max, dt)
    omega_R = omega.real
    omega_I = omega.imag

    # Amplitude scaling
    A = 1.0 / r_obs

    # Strain components
    envelope = A * np.exp(omega_I * t)
    h_plus = envelope * np.cos(omega_R * t)
    h_cross = envelope * np.sin(omega_R * t)

    # Characteristic strain
    h_char = np.sqrt(h_plus**2 + h_cross**2)

    return {
        "t": t,
        "h_plus": h_plus,
        "h_cross": h_cross,
        "h_char": h_char,
        "omega": omega,
        "l": l,
        "m": m,
        "M": M,
        "r_obs": r_obs,
    }


def compute_waveform_from_ringdown(
    M: float = 1.0,
    a: float = 0.0,
    l: int = 2,
    m: int = 2,
    t_max: float = 200.0,
    dt: float = 0.5,
) -> dict[str, Any]:
    """Compute gravitational waveform from ringdown phase.

    Uses QNM frequencies from the quasinormal module.
    """
    sys.path.insert(0, os.path.dirname(__file__))
    from quasinormal import schwarzschild_qnm, kerr_qnm

    if a > 0:
        qnm = kerr_qnm(l, 0, M, a, prograde=True)
    else:
        qnm = schwarzschild_qnm(l, 0, M)

    omega = qnm["omega"]

    return compute_gw_strain(M=M, l=l, m=m, omega=omega, t_max=t_max, dt=dt)


def solve_zerilli(
    M: float = 1.0,
    l: int = 2,
    omega: complex = 0.37 - 0.09j,
    r_min: float = 2.01,
    r_max: float = 200.0,
    n_points: int = 1000,
) -> dict[str, Any]:
    """Solve the Zerilli equation numerically.

    Same structure as Regge-Wheeler but with Zerilli potential.
    """
    r = np.linspace(r_min, r_max, n_points)
    r_star = tortoise_coordinate(r, M)
    V = zerilli_potential(r, l, M)

    psi_0 = np.exp(-1j * omega * r_star[0])
    dpsi_0 = -1j * omega * psi_0

    def rhs(r_star_val, y):
        r_val = np.interp(r_star_val, r_star, r)
        V_val = np.interp(r_star_val, r_star, V)
        psi, dpsi = y
        d2psi = -(omega**2 - V_val) * psi
        return [dpsi, d2psi]

    sol = solve_ivp(rhs, [r_star[0], r_star[-1]],
                    [psi_0, dpsi_0],
                    t_eval=r_star,
                    method='RK45',
                    rtol=1e-10, atol=1e-12)

    return {
        "r": r,
        "r_star": r_star,
        "psi": sol.y[0],
        "dpsi": sol.y[1],
        "potential": V,
        "omega": omega,
        "l": l,
        "M": M,
        "success": sol.success,
    }
