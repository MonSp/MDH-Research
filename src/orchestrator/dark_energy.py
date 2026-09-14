"""Dark energy models and modified gravity.

Implements:
1. Standard ΛCDM with cosmological constant
2. w(z) dark energy equation of state (CPL parameterization)
3. f(R) modified gravity models
4. Dark energy density evolution and cosmic acceleration
"""

from __future__ import annotations

import sys
import os
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

G = 6.67430e-11
c = 299792458.0


def hubble_lcdm(
    a: float,
    H0: float = 67.4,
    Omega_m: float = 0.315,
    Omega_r: float = 9.1e-5,
    Omega_Lambda: float = 0.685,
    Omega_k: float = 0.0,
) -> float:
    """Hubble parameter for ΛCDM.

    H²(a) = H₀² [Ω_r/a⁴ + Ω_m/a³ + Ω_k/a² + Ω_Λ]

    Args:
        a: scale factor
        H0: Hubble constant (km/s/Mpc)
        Omega_*: density parameters

    Returns:
        H(a) in km/s/Mpc.
    """
    H2 = H0**2 * (Omega_r / a**4 + Omega_m / a**3 + Omega_k / a**2 + Omega_Lambda)
    return np.sqrt(H2) if H2 > 0 else 0.0


def w_cpl(z: float, w0: float = -1.0, wa: float = 0.0) -> float:
    """CPL (Chevallier-Polarski-Linder) dark energy equation of state.

    w(a) = w₀ + wₐ(1-a) = w₀ + wₐ z/(1+z)

    Args:
        z: redshift
        w0: equation of state today
        wa: evolution parameter

    Returns:
        w(z) value.
    """
    a = 1 / (1 + z)
    return w0 + wa * (1 - a)


def dark_energy_density(
    z: float,
    w0: float = -1.0,
    wa: float = 0.0,
) -> float:
    """Dark energy density at redshift z.

    ρ_DE(z) = ρ_DE,0 × exp(3 ∫₀ᶻ (1+w(z'))/(1+z') dz')

    For w = -1 (cosmological constant): ρ_DE = const.
    For w < -1 (phantom): ρ_DE increases with z.
    For w > -1 (quintessence): ρ_DE decreases with z.

    Args:
        z: redshift
        w0: equation of state today
        wa: evolution parameter

    Returns:
        ρ_DE(z) / ρ_DE,0 (normalized to present value).
    """
    if z == 0:
        return 1.0

    # Numerical integration
    z_grid = np.linspace(0, z, 100)
    integrand = (1 + w_cpl(z_grid, w0, wa)) / (1 + z_grid)
    integral = np.trapezoid(integrand, z_grid)

    return np.exp(3 * integral)


def hubble_cpl(
    z: float,
    H0: float = 67.4,
    Omega_m: float = 0.315,
    Omega_r: float = 9.1e-5,
    w0: float = -1.0,
    wa: float = 0.0,
) -> float:
    """Hubble parameter with CPL dark energy.

    H²(z) = H₀² [Ω_r(1+z)⁴ + Ω_m(1+z)³ + Ω_DE(z)]
    where Ω_DE(z) = (1-Ω_m-Ω_r) × exp(3∫₀ᶻ (1+w)/(1+z') dz')

    Args:
        z: redshift
        H0: Hubble constant
        Omega_m: matter density
        Omega_r: radiation density
        w0, wa: CPL parameters

    Returns:
        H(z) in km/s/Mpc.
    """
    Omega_DE_0 = 1 - Omega_m - Omega_r
    rho_DE = dark_energy_density(z, w0, wa)

    H2 = H0**2 * (
        Omega_r * (1 + z)**4 +
        Omega_m * (1 + z)**3 +
        Omega_DE_0 * rho_DE
    )

    return np.sqrt(H2) if H2 > 0 else 0.0


def deceleration_parameter(
    z: float = 0.0,
    Omega_m: float = 0.315,
    w0: float = -1.0,
) -> float:
    """Deceleration parameter q(z).

    q(z) = Ω_m(z)/2 + (1+3w)Ω_DE(z)/2

    q > 0: decelerating
    q < 0: accelerating

    Args:
        z: redshift
        Omega_m: matter density
        w0: dark energy equation of state

    Returns:
        q(z) value.
    """
    a = 1 / (1 + z)
    Omega_m_a = Omega_m * (1 + z)**3 / (Omega_m * (1 + z)**3 + (1 - Omega_m))
    Omega_DE_a = 1 - Omega_m_a

    return Omega_m_a / 2 + (1 + 3 * w0) * Omega_DE_a / 2


def f_R_model(
    R_scalar: float,
    f0: float = 1e-6,
    n: float = 1.0,
) -> dict[str, float]:
    """f(R) modified gravity model.

    Models: f(R) = R + f0 × R^n (Starobinsky-like for n=2)

    The field equations become:
    f'(R) R_μν - ½f(R)g_μν + (g_μν □ - ∇_μ∇_ν) f'(R) = 8πG T_μν

    For f(R) = R + f0 R^n:
    f'(R) = 1 + n f0 R^{n-1}
    f''(R) = n(n-1) f0 R^{n-2}

    Args:
        R_scalar: Ricci scalar value
        f0: coupling constant
        n: exponent

    Returns:
        Dict with f(R), f'(R), f''(R) and related quantities.
    """
    f = R_scalar + f0 * R_scalar**n
    f_prime = 1 + n * f0 * R_scalar**(n - 1) if n >= 1 else 1.0
    f_double_prime = n * (n - 1) * f0 * R_scalar**(n - 2) if n >= 2 else 0.0

    # Effective gravitational constant
    G_eff = G / f_prime if f_prime != 0 else float('inf')

    # Scalaron mass (for stability analysis)
    m_s = 1 / np.sqrt(3 * f_double_prime) if f_double_prime > 0 else float('inf')

    return {
        "f": f,
        "f_prime": f_prime,
        "f_double_prime": f_double_prime,
        "G_eff": G_eff,
        "scalaron_mass": m_s,
        "R": R_scalar,
        "f0": f0,
        "n": n,
    }


def f_R_cosmology(
    a_values: np.ndarray = None,
    f0: float = 1e-6,
    n: float = 2.0,
    H0: float = 67.4,
    Omega_m: float = 0.315,
) -> dict[str, Any]:
    """Solve the Friedmann equation in f(R) gravity.

    In f(R) gravity, the Friedmann equation becomes:
    3f'(R)H² = 8πGρ + ½(f - Rf') - 3H ḟ'

    Simplified: H² ≈ H₀² [Ω_m/a³ + Ω_DE(a)]

    Args:
        a_values: scale factor array
        f0: f(R) coupling constant
        n: f(R) exponent
        H0: Hubble constant
        Omega_m: matter density

    Returns:
        Dict with scale factor and Hubble parameter arrays.
    """
    if a_values is None:
        a_values = np.geomspace(0.01, 1.0, 100)

    # Effective dark energy from f(R) modification
    # For f(R) = R + f0 R^n: Ω_DE ∝ f0 × R^{n-1}
    # At late times: R ~ H² ~ H₀²
    R_today = 12 * H0**2 * (1e3 / 3.0857e22)**2  # H₀² in SI-ish units

    H_values = []
    z_values = 1 / a_values - 1
    for a, z in zip(a_values, z_values):
        # Effective dark energy density
        f_result = f_R_model(R_today * (1 + z)**3, f0, n)
        omega_DE = abs(f_result["f_prime"] - 1) * 0.3  # simplified

        H2 = H0**2 * (Omega_m / a**3 + (1 - Omega_m) + omega_DE)
        H_values.append(np.sqrt(H2) if H2 > 0 else 0)

    return {
        "a": a_values,
        "H": np.array(H_values),
        "f0": f0,
        "n": n,
    }


def dark_energy_figure_of_merit(
    w0: float = -1.0,
    wa: float = 0.0,
    sigma_w0: float = 0.1,
    sigma_wa: float = 0.3,
    rho: float = -0.9,
) -> dict[str, float]:
    """Compute the dark energy figure of merit.

    FoM = 1 / (σ_w0 × σ_wa × √(1-ρ²))

    Higher FoM = better constraint on dark energy properties.

    Args:
        w0, wa: CPL parameters
        sigma_w0, sigma_wa: uncertainties
        rho: correlation coefficient

    Returns:
        Dict with figure of merit and related quantities.
    """
    fom = 1 / (sigma_w0 * sigma_wa * np.sqrt(1 - rho**2))

    return {
        "FoM": fom,
        "w0": w0,
        "wa": wa,
        "sigma_w0": sigma_w0,
        "sigma_wa": sigma_wa,
        "rho": rho,
    }
