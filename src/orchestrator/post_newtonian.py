"""Post-Newtonian approximation framework (T30).

The post-Newtonian (PN) expansion is an approximation scheme for
gravitational dynamics in the weak-field, slow-motion regime.

Parameter: ε ~ (v/c)² ~ GM/(rc²) << 1

1PN corrections to Newtonian gravity:
- Orbital energy: E = E_N + E_1PN
- Orbital angular momentum: L = L_N + L_1PN
- Perihelion advance: Δφ = 6πGM/(a(1-e²)c²)

2PN corrections:
- Energy: additional ε² terms
- Gravitational wave flux: leading order quadrupole formula

Key formulas:
- 1PN metric: ds² = -(1 - 2U + 2βU²)dt² + (1 + 2γU)(dx² + dy² + dz²)
  where U = GM/r, β = γ = 1 in GR
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


# Physical constants (SI)
G_SI = 6.67430e-11  # m³/(kg·s²)
c_SI = 299792458.0  # m/s
M_sun = 1.98892e30  # kg
parsec = 3.0857e16  # m


def newtonian_orbital_energy(M: float, m: float, a: float) -> float:
    """Newtonian orbital energy: E = -G M m / (2a).

    Args:
        M: central mass
        m: orbiting mass
        a: semi-major axis

    Returns:
        Orbital energy (negative for bound orbits)
    """
    return -G_SI * M * m / (2 * a)


def newtonian_orbital_frequency(M: float, a: float) -> float:
    """Kepler orbital frequency: f = (1/2π) √(GM/a³).

    Args:
        M: central mass
        a: semi-major axis

    Returns:
        Orbital frequency in Hz
    """
    return np.sqrt(G_SI * M / a**3) / (2 * np.pi)


def pn_energy_1pn(M: float, m: float, a: float, e: float = 0.0) -> dict[str, float]:
    """1PN corrected orbital energy.

    E_1PN = E_N [1 - (1/4)(7-η)ε + ...]
    where η = mM/(m+M)², ε = GM/(ac²), E_N = -G M m/(2a)

    Args:
        M: primary mass
        m: secondary mass
        a: semi-major axis
        e: eccentricity

    Returns:
        Dict with Newtonian and 1PN energies, correction factor.
    """
    M_total = M + m
    eta = m * M / M_total**2  # symmetric mass ratio
    epsilon = G_SI * M / (a * c_SI**2)  # PN parameter

    E_N = newtonian_orbital_energy(M, m, a)
    correction = 1 - (7 - eta) * epsilon / 4
    E_1PN = E_N * correction

    return {
        "E_newton": E_N,
        "E_1PN": E_1PN,
        "correction": correction,
        "eta": eta,
        "epsilon": epsilon,
    }


def perihelion_advance(M: float, a: float, e: float) -> dict[str, float]:
    """1PN perihelion advance per orbit.

    Δφ = 6πGM / (a(1-e²)c²)

    Args:
        M: central mass
        a: semi-major axis
        e: eccentricity

    Returns:
        Dict with advance per orbit (radians and degrees), and per century.
    """
    delta_phi = 6 * np.pi * G_SI * M / (a * (1 - e**2) * c_SI**2)

    # Period
    P = 2 * np.pi * np.sqrt(a**3 / (G_SI * M))

    # Advances per century (assuming 365.25 days/year)
    orbits_per_century = 100 * 365.25 * 24 * 3600 / P

    return {
        "delta_phi_rad": delta_phi,
        "delta_phi_arcsec": np.degrees(delta_phi) * 3600,
        "period_seconds": P,
        "orbits_per_century": orbits_per_century,
        "advance_per_century_arcsec": np.degrees(delta_phi) * 3600 * orbits_per_century,
    }


def pn_metric_components(r: float, M: float, order: int = 1) -> dict[str, float]:
    """Compute PN metric components at a given radius.

    1PN: g_tt = -(1 - 2U + 2U²), g_rr = 1 + 2U
    2PN: g_tt = -(1 - 2U + 2U² - (10+η)U³/4), g_rr = 1 + 2U + (3-η)U²

    where U = GM/(rc²), η = 0 for test particle

    Args:
        r: radial coordinate
        M: central mass
        order: PN order (1 or 2)

    Returns:
        Dict with metric components.
    """
    U = G_SI * M / (r * c_SI**2)  # dimensionless potential

    if order >= 2:
        eta = 0  # test particle limit

    g_tt = -(1 - 2 * U)
    g_rr = 1 + 2 * U

    if order >= 1:
        g_tt = -(1 - 2 * U + 2 * U**2)
        g_rr = 1 + 2 * U

    if order >= 2:
        g_tt = -(1 - 2 * U + 2 * U**2 - (10 + 0) * U**3 / 4)
        g_rr = 1 + 2 * U + 3 * U**2

    return {
        "g_tt": g_tt,
        "g_rr": g_rr,
        "U": U,
        "order": order,
    }


def gravitational_wave_flux_quadrupole(M: float, m: float, a: float) -> dict[str, float]:
    """Leading-order gravitational wave flux (quadrupole formula).

    F = (32/5) × (G⁴ M² m² (M+m)) / (c⁵ a⁵)

    Inspiral timescale: τ = E / F

    Args:
        M: primary mass
        m: secondary mass
        a: semi-major axis (circular orbit)

    Returns:
        Dict with GW flux, inspiral time, frequency.
    """
    M_total = M + m
    eta = m * M / M_total**2

    # GW luminosity (circular orbit)
    flux = (32 / 5) * G_SI**4 * M**2 * m**2 * M_total / (c_SI**5 * a**5)

    # Orbital energy
    E = abs(newtonian_orbital_energy(M, m, a))

    # Inspiral timescale
    tau = E / flux if flux > 0 else float('inf')

    # GW frequency (2× orbital frequency)
    f_orb = newtonian_orbital_frequency(M_total, a)
    f_gw = 2 * f_orb

    return {
        "flux": flux,
        "inspiral_time": tau,
        "f_gw": f_gw,
        "eta": eta,
    }


def pn_binding_energy_2pn(M: float, m: float, v: float) -> dict[str, float]:
    """2PN binding energy as function of orbital velocity.

    E = -(μv²/2)[1 - (3+η)v²/4 - (10+7η)v⁴/8 + ...]

    where μ = mM/(m+M) is the reduced mass, η = μ/M_total

    Args:
        M: primary mass
        m: secondary mass
        v: orbital velocity (fraction of c)

    Returns:
        Dict with binding energy at each PN order.
    """
    M_total = M + m
    mu = m * M / M_total
    eta = mu / M_total

    E_0 = -mu * v**2 / 2
    E_1PN = E_0 * (1 - (3 + eta) * v**2 / 4)
    E_2PN = E_1PN * (1 - (10 + 7 * eta) * v**4 / (8 * (1 - (3 + eta) * v**2 / 4)))

    return {
        "E_newtonian": E_0,
        "E_1PN": E_1PN,
        "E_2PN": E_2PN,
        "eta": eta,
        "v": v,
    }
