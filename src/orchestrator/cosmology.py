"""FLRW cosmology and Friedmann equation solver (T31).

The Friedmann-Lemaître-Robertson-Walker (FLRW) metric:
    ds² = -dt² + a(t)² [dr²/(1-kr²) + r²dΩ²]

Friedmann equations:
    H² = (ȧ/a)² = (8πG/3)ρ - k/a² + Λ/3
    ä/a = -(4πG/3)(ρ + 3p) + Λ/3

where:
- a(t): scale factor
- H = ȧ/a: Hubble parameter
- ρ: energy density
- p: pressure
- k: spatial curvature (-1, 0, +1)
- Λ: cosmological constant

Equation of state: p = wρ
- w = 0: dust (matter)
- w = 1/3: radiation
- w = -1: cosmological constant (dark energy)
"""

from __future__ import annotations

import sys
import os
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp
from scipy.optimize import brentq

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

try:
    import _research_core as rc
except ImportError:
    rc = None

# Cosmological parameters (Planck 2018)
H0_DEFAULT = 67.4  # km/s/Mpc
Omega_m_DEFAULT = 0.315
Omega_r_DEFAULT = 9.1e-5
Omega_Lambda_DEFAULT = 0.685
Omega_k_DEFAULT = 0.0
T_CMB = 2.7255  # K

# Unit conversions
km_s_Mpc_to_s = 1 / (3.0857e19)  # 1 km/s/Mpc in 1/s
Mpc_to_m = 3.0857e22
Gyr_to_s = 3.1557e16


def friedmann_rhs(a: float, params: dict) -> float:
    """Right-hand side of the Friedmann equation: da/dt = a × H(a).

    H²(a) = H₀² [Ω_r/a⁴ + Ω_m/a³ + Ω_k/a² + Ω_Λ]

    Args:
        a: scale factor
        params: dict with H0, Omega_m, Omega_r, Omega_k, Omega_Lambda

    Returns:
        da/dt
    """
    H0 = params.get("H0", H0_DEFAULT)
    Omega_m = params.get("Omega_m", Omega_m_DEFAULT)
    Omega_r = params.get("Omega_r", Omega_r_DEFAULT)
    Omega_k = params.get("Omega_k", Omega_k_DEFAULT)
    Omega_L = params.get("Omega_Lambda", Omega_Lambda_DEFAULT)

    H0_s = H0 * km_s_Mpc_to_s

    H2 = H0_s**2 * (Omega_r / a**4 + Omega_m / a**3 + Omega_k / a**2 + Omega_L)

    if H2 < 0:
        return 0.0  # Turnaround

    return a * np.sqrt(H2)


def hubble_parameter(a: float, params: dict = None) -> float:
    """Compute Hubble parameter H(a) in km/s/Mpc.

    H²(a) = H₀² [Ω_r/a⁴ + Ω_m/a³ + Ω_k/a² + Ω_Λ]
    """
    if params is None:
        params = {}

    H0 = params.get("H0", H0_DEFAULT)
    Omega_m = params.get("Omega_m", Omega_m_DEFAULT)
    Omega_r = params.get("Omega_r", Omega_r_DEFAULT)
    Omega_k = params.get("Omega_k", Omega_k_DEFAULT)
    Omega_L = params.get("Omega_Lambda", Omega_Lambda_DEFAULT)

    H2 = H0**2 * (Omega_r / a**4 + Omega_m / a**3 + Omega_k / a**2 + Omega_L)

    return np.sqrt(H2) if H2 > 0 else 0.0


def density_parameter(a: float, component: str, params: dict = None) -> float:
    """Compute energy density of a component at scale factor a.

    ρ(a) = ρ₀ / a^{3(1+w)}
    - matter (w=0): ρ ∝ a⁻³
    - radiation (w=1/3): ρ ∝ a⁻⁴
    - dark energy (w=-1): ρ = const
    """
    if params is None:
        params = {}

    H0 = params.get("H0", H0_DEFAULT)
    H0_s = H0 * km_s_Mpc_to_s

    critical = 3 * H0_s**2 / (8 * np.pi * 6.67430e-11)

    if component == "matter":
        Omega = params.get("Omega_m", Omega_m_DEFAULT)
        return Omega * critical / a**3
    elif component == "radiation":
        Omega = params.get("Omega_r", Omega_r_DEFAULT)
        return Omega * critical / a**4
    elif component == "dark_energy":
        Omega = params.get("Omega_Lambda", Omega_Lambda_DEFAULT)
        return Omega * critical
    else:
        raise ValueError(f"Unknown component: {component}")


def solve_friedmann(
    params: dict = None,
    a_start: float = 1e-10,
    a_end: float = 2.0,
    n_points: int = 1000,
) -> dict[str, Any]:
    """Solve the Friedmann equation numerically.

    Integrates a(t) from a_start to a_end.

    Args:
        params: cosmological parameters
        a_start: initial scale factor
        a_end: final scale factor
        n_points: number of output points

    Returns:
        Dict with time array, scale factor, Hubble parameter, densities.
    """
    if params is None:
        params = {}

    a_eval = np.geomspace(a_start, a_end, n_points)

    def rhs(t, y):
        a = y[0]
        return [friedmann_rhs(a, params)]

    # Time range: use 2/H₀ as upper bound (covers all cosmologies)
    H0_s = params.get("H0", H0_DEFAULT) * km_s_Mpc_to_s
    t_max = 2.0 / H0_s  # ~30 Gyr in seconds

    sol = solve_ivp(rhs, [0, t_max], [a_start],
                    t_eval=None, method='RK45',
                    dense_output=True, rtol=1e-10, max_step=t_max/1000)

    # Evaluate at requested scale factors
    t_out = []
    a_out = []
    for a_target in a_eval:
        try:
            # Find t such that a(t) = a_target
            t_root = brentq(lambda t: sol.sol(t)[0] - a_target,
                            sol.t[0], sol.t[-1])
            t_out.append(t_root)
            a_out.append(a_target)
        except ValueError:
            break

    t_out = np.array(t_out)
    a_out = np.array(a_out)

    # Compute H(a) at each point
    H_out = np.array([hubble_parameter(a, params) for a in a_out])

    # Convert time to Gyr
    t_gyr = t_out / Gyr_to_s

    # Compute densities
    rho_m = np.array([density_parameter(a, "matter", params) for a in a_out])
    rho_r = np.array([density_parameter(a, "radiation", params) for a in a_out])
    rho_L = np.array([density_parameter(a, "dark_energy", params) for a in a_out])

    return {
        "t_seconds": t_out,
        "t_gyr": t_gyr,
        "a": a_out,
        "H_km_s_Mpc": H_out,
        "rho_matter": rho_m,
        "rho_radiation": rho_r,
        "rho_dark_energy": rho_L,
        "params": params,
    }


def age_of_universe(params: dict = None) -> dict[str, float]:
    """Compute the age of the universe.

    t₀ = ∫₀¹ da / (a H(a))

    Args:
        params: cosmological parameters

    Returns:
        Dict with age in seconds, Gyr, and years.
    """
    if params is None:
        params = {}

    result = solve_friedmann(params, a_start=1e-10, a_end=1.0, n_points=100)
    age_s = result["t_seconds"][-1]
    age_gyr = age_s / Gyr_to_s

    return {
        "age_seconds": age_s,
        "age_gyr": age_gyr,
        "age_years": age_gyr * 1e9,
    }


def cosmological_distances(z: float, params: dict = None) -> dict[str, float]:
    """Compute cosmological distances at redshift z.

    Args:
        z: redshift
        params: cosmological parameters

    Returns:
        Dict with comoving distance, luminosity distance, angular diameter distance.
    """
    if params is None:
        params = {}

    H0 = params.get("H0", H0_DEFAULT)
    H0_s = H0 * km_s_Mpc_to_s

    # Scale factor at redshift z
    a_z = 1 / (1 + z)

    # Comoving distance (numerical integration)
    a_grid = np.geomspace(a_z, 1.0, 100)
    chi = 0
    for i in range(len(a_grid) - 1):
        a_mid = (a_grid[i] + a_grid[i + 1]) / 2
        H = hubble_parameter(a_mid, params) * km_s_Mpc_to_s
        da = a_grid[i + 1] - a_grid[i]
        chi += da / (a_mid**2 * H)

    # Convert to Mpc
    c_over_H0 = 1 / H0_s
    D_c = chi * c_over_H0 / Mpc_to_m  # comoving distance in Mpc

    k = params.get("Omega_k", Omega_k_DEFAULT)
    if abs(k) < 1e-10:
        D_L = D_c * (1 + z)  # luminosity distance
        D_A = D_c / (1 + z)  # angular diameter distance
    elif k < 0:
        R_k = 1 / np.sqrt(-k)
        D_L = R_k * np.sinh(D_c / R_k) * (1 + z)
        D_A = R_k * np.sinh(D_c / R_k) / (1 + z)
    else:
        R_k = 1 / np.sqrt(k)
        D_L = R_k * np.sin(D_c / R_k) * (1 + z)
        D_A = R_k * np.sin(D_c / R_k) / (1 + z)

    return {
        "comoving_distance_Mpc": D_c,
        "luminosity_distance_Mpc": D_L,
        "angular_diameter_distance_Mpc": D_A,
        "z": z,
        "a": a_z,
    }


def deceleration_parameter(params: dict = None) -> float:
    """Compute the deceleration parameter q₀.

    q₀ = Ω_m/2 - Ω_Λ

    q₀ > 0: decelerating expansion
    q₀ < 0: accelerating expansion (dark energy dominated)
    """
    if params is None:
        params = {}

    Omega_m = params.get("Omega_m", Omega_m_DEFAULT)
    Omega_L = params.get("Omega_Lambda", Omega_Lambda_DEFAULT)

    return Omega_m / 2 - Omega_L


def flrw_metric_symbolic(k: int = 0) -> dict[str, Any]:
    """Generate symbolic FLRW metric for use with the C++ engine.

    Args:
        k: spatial curvature (-1, 0, +1)

    Returns:
        Dict with metric info compatible with the geometry module.
    """
    sym = rc.symbol
    m = geom.Manifold("flrw", ["t", "r", "theta", "phi"])

    if k == 0:
        diag = ["-1", "a(t)^2", "a(t)^2 * r^2", "a(t)^2 * r^2 * sin(theta)^2"]
    elif k == 1:
        diag = ["-1", "a(t)^2 / (1 - r^2)", "a(t)^2 * r^2", "a(t)^2 * r^2 * sin(theta)^2"]
    elif k == -1:
        diag = ["-1", "a(t)^2 / (1 + r^2)", "a(t)^2 * r^2", "a(t)^2 * r^2 * sin(theta)^2"]
    else:
        raise ValueError(f"k must be -1, 0, or +1, got {k}")

    g = geom.Metric.from_diagonal(m, diag)

    return {
        "metric": g,
        "manifold": m,
        "coord_names": ["t", "r", "theta", "phi"],
        "k": k,
    }


# Module-level import
geom = rc.geometry if rc else None
