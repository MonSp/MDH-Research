"""Hawking radiation and quantum effects in curved spacetime (T32).

Hawking temperature:
    T_H = ℏ c³ / (8π G M k_B)

For a Schwarzschild black hole:
    T_H ≈ 6.17 × 10⁻⁸ (M_sun/M) K

Evaporation time:
    t_evap = 5120 π G² M³ / (ℏ c⁴)

Bekenstein-Hawking entropy:
    S_BH = k_B c³ A / (4 ℏ G) = 4π k_B G M² / (ℏ c)

Unruh temperature (accelerating observer):
    T_U = ℏ a / (2π c k_B)

Quantum field theory in curved spacetime:
- Particle creation in expanding universe (Parker effect)
- Hawking radiation spectrum (Planck distribution with greybody factors)
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
hbar = 1.054571817e-34  # J·s
c = 299792458.0  # m/s
G = 6.67430e-11  # m³/(kg·s²)
k_B = 1.380649e-23  # J/K
M_sun = 1.98892e30  # kg
sigma_SB = 5.670374419e-8  # W/(m²·K⁴) Stefan-Boltzmann


def hawking_temperature(M: float) -> dict[str, float]:
    """Compute Hawking temperature for a black hole.

    T_H = ℏ c³ / (8π G M k_B)

    Args:
        M: black hole mass in kg

    Returns:
        Dict with temperature in K, eV, Hz, and other units.
    """
    T_H = hbar * c**3 / (8 * np.pi * G * M * k_B)

    # Convert to eV
    T_eV = k_B * T_H / 1.602176634e-19

    # Convert to frequency
    f_Hz = k_B * T_H / hbar

    # Wavelength
    lambda_m = c / f_Hz if f_Hz > 0 else float('inf')

    # Hawking mass
    M_H = hbar * c**3 / (8 * np.pi * G * k_B * T_H) if T_H > 0 else float('inf')

    return {
        "T_K": T_H,
        "T_eV": T_eV,
        "T_Hz": f_Hz,
        "lambda_m": lambda_m,
        "M_kg": M,
        "M_solar": M / M_sun,
    }


def hawking_temperature_solar_masses(M_solar: float) -> dict[str, float]:
    """Compute Hawking temperature for a black hole in solar masses.

    T_H ≈ 6.17 × 10⁻⁸ (M_sun/M) K

    Args:
        M_solar: mass in solar masses

    Returns:
        Dict with temperature and related quantities.
    """
    return hawking_temperature(M_solar * M_sun)


def evaporation_time(M: float) -> dict[str, float]:
    """Compute black hole evaporation time.

    t_evap = 5120 π G² M³ / (ℏ c⁴)

    Args:
        M: black hole mass in kg

    Returns:
        Dict with evaporation time in seconds, years, and age of universe units.
    """
    t_evap = 5120 * np.pi * G**2 * M**3 / (hbar * c**4)

    # Convert to years
    t_years = t_evap / (365.25 * 24 * 3600)

    # Age of universe ≈ 13.8 Gyr
    t_Gyr = t_years / 1e9

    # In units of age of universe
    t_universe = t_Gyr / 13.8

    return {
        "t_seconds": t_evap,
        "t_years": t_years,
        "t_Gyr": t_Gyr,
        "t_universe_ages": t_universe,
        "M_kg": M,
        "M_solar": M / M_sun,
    }


def bekenstein_hawking_entropy(M: float) -> dict[str, float]:
    """Compute Bekenstein-Hawking entropy.

    S_BH = 4π k_B G M² / (ℏ c)

    Args:
        M: black hole mass in kg

    Returns:
        Dict with entropy in J/K and dimensionless (in Planck units).
    """
    S = 4 * np.pi * k_B * G * M**2 / (hbar * c)

    # In Planck units: S = (M/M_Planck)² / 4
    M_planck = np.sqrt(hbar * c / G)
    S_planck = (M / M_planck)**2 / 4

    # In bits
    S_bits = S / (k_B * np.log(2))

    return {
        "S_J_per_K": S,
        "S_planck": S_planck,
        "S_bits": S_bits,
        "M_kg": M,
    }


def unruh_temperature(acceleration: float) -> dict[str, float]:
    """Compute Unruh temperature for an accelerating observer.

    T_U = ℏ a / (2π c k_B)

    Args:
        acceleration: proper acceleration in m/s²

    Returns:
        Dict with Unruh temperature and related quantities.
    """
    T_U = hbar * acceleration / (2 * np.pi * c * k_B)

    # Convert to eV
    T_eV = k_B * T_U / 1.602176634e-19

    return {
        "T_K": T_U,
        "T_eV": T_eV,
        "acceleration_m_s2": acceleration,
        "acceleration_g": acceleration / 9.81,
    }


def hawking_spectrum(omega: np.ndarray, M: float, l: int = 0) -> np.ndarray:
    """Compute Hawking radiation spectrum (greybody-approximated).

    For a Schwarzschild BH, the emission rate per unit frequency is:
    dN/dt dω = (Γ_l / (2π)) × ω / (exp(ℏω/k_BT_H) - 1)

    where Γ_l is the greybody factor (transmission coefficient).

    Args:
        omega: angular frequency array
        M: black hole mass in kg
        l: angular mode number

    Returns:
        Emission rate array (normalized, not absolute).
    """
    T = hawking_temperature(M)["T_K"]
    if T == 0:
        return np.zeros_like(omega)

    # Planck factor
    x = hbar * omega / (k_B * T)
    planck = np.where(x < 500, x / (np.exp(x) - 1), 0.0)

    # Simplified greybody factor (geometric optics approximation)
    # Γ ≈ (r_s ω)² for low frequencies
    r_s = 2 * G * M / c**2
    greybody = np.minimum((r_s * omega)**2, 1.0)

    return greybody * planck


def black_hole_heat_capacity(M: float) -> dict[str, float]:
    """Compute black hole heat capacity.

    C = dM/dT × c² = -8π G M² k_B / (ℏ c)

    Black holes have negative heat capacity — they get hotter as they lose mass.

    Args:
        M: black hole mass in kg

    Returns:
        Dict with heat capacity and related quantities.
    """
    C = -8 * np.pi * G * M**2 * k_B / (hbar * c)

    # Evaporation timescale
    L = hbar * c**6 / (15360 * np.pi * G**2 * M**2)  # Luminosity
    t_evap = M * c**2 / L if L > 0 else float('inf')

    return {
        "C_J_per_K": C,
        "negative": C < 0,
        "luminosity_W": L,
        "evaporation_time_s": t_evap,
    }


def page_information(M: float, M_initial: float) -> dict[str, float]:
    """Compute Page curve information for black hole evaporation.

    The Page curve describes how information is encoded in Hawking radiation.
    Before the Page time, entanglement entropy increases.
    After the Page time, it decreases (information is released).

    t_Page ≈ t_evap / 2

    Args:
        M: current black hole mass
        M_initial: initial black hole mass

    Returns:
        Dict with Page time, current radiation entropy, and information fraction.
    """
    # Page time ≈ half of evaporation time
    t_evap = evaporation_time(M_initial)["t_seconds"]
    t_page = t_evap / 2

    # Current evaporation time remaining
    t_remaining = evaporation_time(M)["t_seconds"]

    # Radiation entropy (simplified)
    S_BH_initial = bekenstein_hawking_entropy(M_initial)["S_bits"]
    S_BH_current = bekenstein_hawking_entropy(M)["S_bits"]
    S_rad = S_BH_initial - S_BH_current

    return {
        "t_page_s": t_page,
        "t_remaining_s": t_remaining,
        "S_initial_bits": S_BH_initial,
        "S_current_bits": S_BH_current,
        "S_radiation_bits": max(0, S_rad),
        "past_page": t_remaining < t_page,
        "M_ratio": M / M_initial,
    }
