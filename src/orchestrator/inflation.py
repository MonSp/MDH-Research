"""Cosmological inflation framework (T37).

Tools for computing inflationary observables:
- Slow-roll parameters (ε, η)
- Number of e-folds
- Primordial power spectra (scalar and tensor)
- Scalar spectral index n_s
- Tensor-to-scalar ratio r
- Running of spectral index

The slow-roll approximation:
    ε = (M_Pl²/2) (V'/V)²
    η = M_Pl² (V''/V)

where V(φ) is the inflaton potential and M_Pl = 1/√(8πG) is the reduced Planck mass.
"""

from __future__ import annotations

import sys
import os
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp


def _derivative(f, x, n=1, dx=1e-6):
    """Compute nth derivative of f at x using central differences."""
    if n == 0:
        return f(x)
    if n == 1:
        return (f(x + dx) - f(x - dx)) / (2 * dx)
    if n == 2:
        return (f(x + dx) - 2 * f(x) + f(x - dx)) / dx**2
    raise ValueError(f"Derivative order {n} not supported")

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

try:
    import _research_core as rc
except ImportError:
    rc = None

# Physical constants
G = 6.67430e-11
hbar = 1.054571817e-34
c = 299792458.0
M_Pl = 2.435e18  # reduced Planck mass in GeV
M_Pl_kg = 2.176e-8  # Planck mass in kg


def m_pl_squared() -> float:
    """Reduced Planck mass squared M_Pl² in natural units (M_Pl = 1)."""
    return 1.0


def slow_roll_parameter_epsilon(V: callable, phi: float, delta: float = 1e-6) -> float:
    """Compute slow-roll parameter ε.

    ε = (M_Pl²/2) (V'/V)²

    Args:
        V: potential function V(φ)
        phi: field value
        delta: finite difference step

    Returns:
        Slow-roll parameter ε
    """
    V_val = V(phi)
    V_prime = _derivative(V, phi, dx=delta * abs(phi) if phi != 0 else delta)
    M2 = m_pl_squared()
    return M2 / 2 * (V_prime / V_val)**2


def slow_roll_parameter_eta(V: callable, phi: float, delta: float = 1e-6) -> float:
    """Compute slow-roll parameter η.

    η = M_Pl² (V''/V)

    Args:
        V: potential function V(φ)
        phi: field value
        delta: finite difference step

    Returns:
        Slow-roll parameter η
    """
    V_val = V(phi)
    V_double_prime = _derivative(V, phi, n=2, dx=delta * abs(phi) if phi != 0 else delta)
    M2 = m_pl_squared()
    return M2 * V_double_prime / V_val


def slow_roll_parameters(V: callable, phi: float) -> dict[str, float]:
    """Compute both slow-roll parameters.

    Args:
        V: potential function
        phi: field value

    Returns:
        Dict with ε, η, and slow-roll validity check.
    """
    eps = slow_roll_parameter_epsilon(V, phi)
    eta = slow_roll_parameter_eta(V, phi)

    return {
        "epsilon": eps,
        "eta": eta,
        "slow_roll_valid": eps < 1 and abs(eta) < 1,
        "inflation_ends": eps >= 1,
    }


def number_of_efolds(V: callable, phi_start: float, phi_end: float, n_points: int = 1000) -> dict[str, float]:
    """Compute number of e-folds of inflation.

    N = ∫ (V / V') dφ / M_Pl²

    Args:
        V: potential function
        phi_start: initial field value
        phi_end: final field value (where ε ≈ 1)
        n_points: integration points

    Returns:
        Dict with number of e-folds and related quantities.
    """
    M2 = m_pl_squared()
    phi = np.linspace(phi_start, phi_end, n_points)
    dphi = phi[1] - phi[0]

    integrand = np.zeros(n_points)
    for i in range(n_points):
        V_val = V(phi[i])
        V_prime = _derivative(V, phi[i], dx=1e-8 * abs(phi[i]) if phi[i] != 0 else 1e-8)
        if abs(V_prime) > 1e-30:
            integrand[i] = V_val / V_prime / M2

    N = np.trapezoid(integrand, phi)

    return {
        "N": abs(N),
        "phi_start": phi_start,
        "phi_end": phi_end,
        "sufficient": abs(N) > 60,  # need N > 60 for horizon problem
    }


def scalar_spectral_index(eps: float, eta: float) -> float:
    """Compute scalar spectral index n_s.

    n_s = 1 - 6ε + 2η

    Args:
        eps: slow-roll parameter ε
        eta: slow-roll parameter η

    Returns:
        Scalar spectral index n_s
    """
    return 1 - 6 * eps + 2 * eta


def tensor_to_scalar_ratio(eps: float) -> float:
    """Compute tensor-to-scalar ratio r.

    r = 16ε

    Args:
        eps: slow-roll parameter ε

    Returns:
        Tensor-to-scalar ratio r
    """
    return 16 * eps


def spectral_index_running(eps: float, eta: float, xi: float = 0.0) -> float:
    """Compute running of spectral index.

    dn_s/d ln k = -2(16εη - 24ε² - 2ξ²)

    Args:
        eps: slow-roll parameter ε
        eta: slow-roll parameter η
        xi: second-order slow-roll parameter (default 0)

    Returns:
        Running dn_s/d ln k
    """
    return -2 * (16 * eps * eta - 24 * eps**2 - 2 * xi**2)


def primordial_scalar_power_spectrum(
    k: np.ndarray,
    A_s: float = 2.1e-9,
    n_s: float = 0.965,
    k_pivot: float = 0.05,
    alpha_s: float = 0.0,
) -> dict[str, Any]:
    """Compute primordial scalar power spectrum.

    P_s(k) = A_s × (k/k_pivot)^{n_s - 1 + (α_s/2) ln(k/k_pivot)}

    Args:
        k: wavenumber array (Mpc⁻¹)
        A_s: amplitude at pivot scale
        n_s: scalar spectral index
        k_pivot: pivot scale (Mpc⁻¹)
        alpha_s: running of spectral index

    Returns:
        Dict with k and P_s(k) arrays.
    """
    ln_k_ratio = np.log(k / k_pivot)
    P_s = A_s * (k / k_pivot)**(n_s - 1 + (alpha_s / 2) * ln_k_ratio)

    return {
        "k": k,
        "P_s": P_s,
        "A_s": A_s,
        "n_s": n_s,
        "k_pivot": k_pivot,
    }


def primordial_tensor_power_spectrum(
    k: np.ndarray,
    A_s: float = 2.1e-9,
    r: float = 0.03,
    n_t: float = None,
    k_pivot: float = 0.05,
) -> dict[str, Any]:
    """Compute primordial tensor power spectrum.

    P_t(k) = A_t × (k/k_pivot)^{n_t}

    where A_t = r × A_s and n_t = -r/8 (consistency relation)

    Args:
        k: wavenumber array (Mpc⁻¹)
        A_s: scalar amplitude
        r: tensor-to-scalar ratio
        n_t: tensor spectral index (default: -r/8)
        k_pivot: pivot scale

    Returns:
        Dict with k and P_t(k) arrays.
    """
    if n_t is None:
        n_t = -r / 8  # consistency relation

    A_t = r * A_s
    P_t = A_t * (k / k_pivot)**n_t

    return {
        "k": k,
        "P_t": P_t,
        "A_t": A_t,
        "n_t": n_t,
        "r": r,
    }


def inflationary_observables(V: callable, phi_start: float) -> dict[str, Any]:
    """Compute all inflationary observables for a given potential.

    Args:
        V: inflaton potential V(φ)
        phi_start: field value at horizon crossing

    Returns:
        Dict with all observable quantities.
    """
    # Find where inflation ends (ε = 1)
    def eps_minus_one(phi):
        return slow_roll_parameter_epsilon(V, phi) - 1

    # Search for end of inflation
    phi_end = phi_start
    for _ in range(100):
        phi_end -= 0.1
        if eps_minus_one(phi_end) > 0:
            break

    # Slow-roll parameters at horizon crossing
    sr = slow_roll_parameters(V, phi_start)

    # Number of e-folds
    N = number_of_efolds(V, phi_start, phi_end)

    # Observables
    n_s = scalar_spectral_index(sr["epsilon"], sr["eta"])
    r = tensor_to_scalar_ratio(sr["epsilon"])
    alpha_s = spectral_index_running(sr["epsilon"], sr["eta"])

    return {
        "epsilon": sr["epsilon"],
        "eta": sr["eta"],
        "N": N["N"],
        "n_s": n_s,
        "r": r,
        "alpha_s": alpha_s,
        "slow_roll_valid": sr["slow_roll_valid"],
        "sufficient_efolds": N["N"] > 60,
        "phi_start": phi_start,
        "phi_end": phi_end,
    }


# Common inflaton potentials
def chaotic_potential(m: float = 1e-5):
    """Chaotic inflation: V(φ) = ½ m² φ² (in Planck units)."""
    return lambda phi: 0.5 * m**2 * phi**2


def starobinsky_potential(Lambda: float = 1e-3):
    """Starobinsky inflation: V(φ) = Λ⁴ (1 - e^{-√(2/3) φ})² (in Planck units)."""
    return lambda phi: Lambda**4 * (1 - np.exp(-np.sqrt(2/3) * phi))**2


def higgs_potential(lam: float = 0.1):
    """Higgs inflation (simplified): V(φ) = ¼ λ φ⁴ (in Planck units)."""
    return lambda phi: 0.25 * lam * phi**4
