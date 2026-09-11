"""Neutron star equation of state and TOV solver (T38).

The Tolman-Oppenheimer-Volkoff (TOV) equation describes hydrostatic
equilibrium in general relativity:

    dP/dr = -G(m(r)ρ(r) + 4πr³P(r)/c²)(ρ(r) + P(r)/c²) / (r(r - 2Gm(r)/c²))

with mass conservation:
    dm/dr = 4πr²ρ(r)

Equation of state (EOS) options:
- Polytrope: P = K ρ^Γ
- Piecewise polytrope: different Γ in density ranges
- SLy4: realistic nuclear EOS
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

G = 6.67430e-11
c = 299792458.0
M_sun = 1.98892e30
km = 1e3
MeV_fm3_to_Pa = 1.602176634e-13 * 1e45  # MeV/fm³ to Pa
g_cm3_to_kg_m3 = 1e3  # g/cm³ to kg/m³


def polytropic_eos(K: float = 1e-3, Gamma: float = 2.0):
    """Create a polytropic EOS: P = K ρ^Γ.

    Args:
        K: polytropic constant (Pa / (kg/m³)^Γ)
        Gamma: adiabatic index

    Returns:
        Tuple of (pressure_func, density_func_from_pressure)
    """
    def pressure(rho):
        return K * rho**Gamma

    def density(P):
        if P <= 0:
            return 0.0
        return (P / K)**(1 / Gamma)

    def dP_drho(rho):
        return K * Gamma * rho**(Gamma - 1)

    return {
        "pressure": pressure,
        "density": density,
        "dP_drho": dP_drho,
        "K": K,
        "Gamma": Gamma,
        "name": f"Polytrope(K={K}, Γ={Gamma})",
    }


def sly4_eos():
    """SLy4 equation of state (piecewise polytrope approximation).

    Based on Douchin & Haensel (2001) and Read et al. (2009).
    Piecewise polytrope with 4 segments.

    Returns:
        EOS dict with pressure and density functions.
    """
    # Piecewise polytrope parameters for SLy4
    # Segment boundaries in log10(ρ [g/cm³])
    log_rho_b = [14.0, 14.7, 15.0]

    # Γ values for each segment
    Gammas = [2.21, 3.15, 3.57, 3.28]

    # K values (adjusted for continuity)
    # At boundary, P must be continuous: K_i ρ_i^Γ_i = K_{i+1} ρ_i^Γ_{i+1}
    rho_b = [10**log_rho for log_rho in log_rho_b]

    # Reference: P(ρ=10^14 g/cm³) ≈ 10^33.5 Pa (from SLy4 table)
    rho_ref = 1e14 * g_cm3_to_kg_m3
    P_ref = 10**33.5  # Pa

    K_values = [P_ref / rho_ref**Gammas[0]]
    for i in range(1, 4):
        rho_i = rho_b[i-1] * g_cm3_to_kg_m3
        P_i = K_values[i-1] * rho_i**Gammas[i-1]
        K_values.append(P_i / rho_i**Gammas[i])

    def pressure(rho):
        """Compute pressure from density using SLy4 EOS."""
        if rho <= 0:
            return 0.0
        rho_gcm3 = rho / g_cm3_to_kg_m3
        log_rho = np.log10(rho_gcm3)

        if log_rho < log_rho_b[0]:
            return K_values[0] * rho**Gammas[0]
        elif log_rho < log_rho_b[1]:
            return K_values[1] * rho**Gammas[1]
        elif log_rho < log_rho_b[2]:
            return K_values[2] * rho**Gammas[2]
        else:
            return K_values[3] * rho**Gammas[3]

    def density(P):
        """Compute density from pressure using SLy4 EOS."""
        if P <= 0:
            return 0.0
        # Binary search for density
        rho_low, rho_high = 1e10, 1e20
        for _ in range(100):
            rho_mid = (rho_low + rho_high) / 2
            P_mid = pressure(rho_mid)
            if P_mid < P:
                rho_low = rho_mid
            else:
                rho_high = rho_mid
            if abs(rho_high - rho_low) / rho_mid < 1e-10:
                break
        return (rho_low + rho_high) / 2

    return {
        "pressure": pressure,
        "density": density,
        "K_values": K_values,
        "Gammas": Gammas,
        "boundaries_g_cm3": [10**x for x in log_rho_b],
        "name": "SLy4",
    }


def tov_rhs(r: float, y: list, eos: dict) -> list:
    """Right-hand side of the TOV equations.

    y = [P, m] where P is pressure and m is enclosed mass.

    dP/dr = -G(mρ + 4πr³P/c²)(ρ + P/c²) / (r(r - 2Gm/c²))
    dm/dr = 4πr²ρ

    Args:
        r: radius
        y: [pressure, mass]
        eos: equation of state dict

    Returns:
        [dP/dr, dm/dr]
    """
    P, m = y

    if P <= 0:
        return [0, 0]

    rho = eos["density"](P)

    # TOV equation:
    # dP/dr = -(ρ + P/c²)(Gm + 4πGr³P/c²) / (r²(1 - 2Gm/(rc²)))
    r_sq = r * r
    gm_term = G * m + 4 * np.pi * G * r**3 * P / c**2
    rho_eff = rho + P / c**2
    metric_factor = 1 - 2 * G * m / (r * c**2)

    if metric_factor <= 0:
        return [0, 0]

    dP_dr = -rho_eff * gm_term / (r_sq * metric_factor)
    dm_dr = 4 * np.pi * r**2 * rho

    return [dP_dr, dm_dr]


def solve_tov(
    rho_c: float,
    eos: dict = None,
    r_max: float = 30e3,
    n_points: int = 1000,
) -> dict[str, Any]:
    """Solve the TOV equations for a neutron star.

    Args:
        rho_c: central density in kg/m³
        eos: equation of state dict
        r_max: maximum radius to integrate (meters)
        n_points: number of output points

    Returns:
        Dict with radius, pressure, density, mass profiles, and stellar parameters.
    """
    if eos is None:
        eos = polytropic_eos()

    # Initial conditions: use Taylor expansion near center
    # P(r) ≈ P_c - (2πG/3) ρ_c(ρ_c + P_c/c²) r²
    # M(r) ≈ (4π/3) ρ_c r³
    P_c = eos["pressure"](rho_c)
    r_start = 1000.0  # start at 1km (Taylor expansion is good here)

    # Initial conditions using Lane-Emden solution near center
    # For polytrope P = Kρ^Γ with Γ=2:
    # ρ(r) ≈ ρ_c [1 - r²/(6K/(πGρ_c))] near center
    # P(r) ≈ Kρ_c² [1 - r²/(6K/(πGρ_c))]
    # M(r) ≈ (4π/3) ρ_c r³

    # Use Lane-Emden approximation: P stays close to P_c for small r
    # Start at r where correction is ~1%
    # Lane-Emden scale: R² = 6K / (πGρ_c) for Γ=2 polytrope
    K_val = P_c / rho_c**2
    r_scale_sq = 6 * K_val / (np.pi * G * rho_c)
    r_scale = np.sqrt(r_scale_sq) if r_scale_sq > 0 else 1e6

    # Ensure r_start is small compared to r_scale
    r_start = min(r_start, r_scale * 0.01)
    if r_start < 10.0:
        r_start = 10.0

    P_start = P_c * (1 - (r_start / r_scale)**2)
    m_start = (4 * np.pi / 3) * rho_c * r_start**3

    if P_start <= 0:
        P_start = P_c * 0.999
        r_start = 10.0
        m_start = (4 * np.pi / 3) * rho_c * r_start**3

    def stop_condition(r, y, eos):
        return y[0]  # stop when P = 0
    stop_condition.terminal = True

    # Use Radau solver (implicit, good for stiff problems near r=0)
    sol = solve_ivp(
        tov_rhs,
        [r_start, r_max],
        [P_start, m_start],
        args=(eos,),
        events=stop_condition,
        method='Radau',
        rtol=1e-8,
        atol=1e-10,
        first_step=r_start * 0.01,
    )

    # Find stellar surface (where P drops to ~0)
    P_profile = sol.y[0]
    m_profile = sol.y[1]
    r_profile = sol.t

    # Find radius where P < threshold
    P_threshold = P_c * 1e-10
    surface_idx = np.where(P_profile < P_threshold)[0]
    if len(surface_idx) > 0:
        idx = surface_idx[0]
    else:
        idx = len(r_profile) - 1

    R = r_profile[idx]
    M = m_profile[idx]

    # Density profile
    rho_profile = np.array([eos["density"](max(P, 0)) for P in P_profile])

    # Compactness
    compactness = G * M / (R * c**2) if R > 0 else 0

    # Surface redshift
    z_s = 1 / np.sqrt(1 - 2 * compactness) - 1 if compactness < 0.5 else float('inf')

    return {
        "r_m": r_profile[:idx+1],
        "r_km": r_profile[:idx+1] / km,
        "P_Pa": P_profile[:idx+1],
        "rho_kg_m3": rho_profile[:idx+1],
        "M_kg": m_profile[:idx+1],
        "M_solar": m_profile[:idx+1] / M_sun,
        "R_m": R,
        "R_km": R / km,
        "M_total_kg": M,
        "M_total_solar": M / M_sun,
        "compactness": compactness,
        "surface_redshift": z_s,
        "rho_c": rho_c,
        "eos_name": eos["name"],
    }


def mass_radius_relation(
    eos: dict = None,
    rho_c_range: tuple = (1e14 * g_cm3_to_kg_m3, 2e15 * g_cm3_to_kg_m3),
    n_points: int = 30,
) -> dict[str, Any]:
    """Compute the mass-radius relation for a given EOS.

    Args:
        eos: equation of state
        rho_c_range: range of central densities
        n_points: number of models

    Returns:
        Dict with arrays of mass, radius, and central density.
    """
    if eos is None:
        eos = sly4_eos()

    rho_c_values = np.geomspace(rho_c_range[0], rho_c_range[1], n_points)
    masses = []
    radii = []
    compactnesses = []

    for rho_c in rho_c_values:
        result = solve_tov(rho_c, eos)
        masses.append(result["M_total_solar"])
        radii.append(result["R_km"])
        compactnesses.append(result["compactness"])

    masses = np.array(masses)
    radii = np.array(radii)
    compactnesses = np.array(compactnesses)

    # Find maximum mass
    max_idx = np.argmax(masses)

    return {
        "M_solar": masses,
        "R_km": radii,
        "rho_c": rho_c_values,
        "compactness": compactnesses,
        "max_mass_solar": masses[max_idx],
        "max_mass_radius_km": radii[max_idx],
        "max_mass_rho_c": rho_c_values[max_idx],
        "eos_name": eos["name"],
    }


def tidal_deformability(M_solar: float, R_km: float, k2: float = 0.1) -> dict[str, float]:
    """Estimate tidal deformability Λ.

    Λ = (2/3) k₂ (R/M)⁵

    where k₂ is the Love number and R,M are in geometric units.

    Args:
        M_solar: neutron star mass in solar masses
        R_km: neutron star radius in km
        k2: Love number (typical: 0.05-0.15)

    Returns:
        Dict with tidal deformability and related quantities.
    """
    M = M_solar * M_sun
    R = R_km * km

    # Compactness
    C = G * M / (R * c**2)

    # Tidal deformability (dimensionless)
    Lambda = (2 / 3) * k2 * (1 / C)**5

    return {
        "Lambda": Lambda,
        "k2": k2,
        "compactness": C,
        "M_solar": M_solar,
        "R_km": R_km,
    }
