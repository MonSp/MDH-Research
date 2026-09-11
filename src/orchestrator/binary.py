"""Binary system evolution and gravitational wave emission (T33).

Binary systems emit gravitational waves, causing orbital decay.
The key quantities are:

Chirp mass:
    M_c = (m₁ m₂)^{3/5} / (m₁ + m₂)^{1/5}

Orbital decay rate (quadrupole formula):
    da/dt = -64 G³ m₁ m₂ (m₁ + m₂) / (5 c⁵ a³)

Merger time:
    t_merge = 5 c⁵ a⁴ / (256 G³ m₁ m₂ (m₁ + m₂))

Gravitational wave frequency:
    f_GW = (1/π) √(G(m₁+m₂)/a³)

Chirp rate (frequency evolution):
    df/dt = (96/5) π^{8/3} (G M_c/c³)^{5/3} f^{11/3}
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

# Physical constants
G = 6.67430e-11
c = 299792458.0
M_sun = 1.98892e30
parsec = 3.0857e16
Gyr_s = 3.1557e16


def chirp_mass(m1: float, m2: float) -> float:
    """Compute chirp mass.

    M_c = (m₁ m₂)^{3/5} / (m₁ + m₂)^{1/5}

    Args:
        m1, m2: component masses in kg

    Returns:
        Chirp mass in kg
    """
    return (m1 * m2)**(3/5) / (m1 + m2)**(1/5)


def symmetric_mass_ratio(m1: float, m2: float) -> float:
    """Compute symmetric mass ratio η = m₁m₂/(m₁+m₂)².

    Args:
        m1, m2: component masses

    Returns:
        Symmetric mass ratio (0 < η ≤ 0.25)
    """
    M = m1 + m2
    return m1 * m2 / M**2


def orbital_decay_rate(a: float, m1: float, m2: float) -> float:
    """Compute orbital separation decay rate da/dt.

    da/dt = -64 G³ m₁ m₂ (m₁+m₂) / (5 c⁵ a³)

    Args:
        a: orbital separation in meters
        m1, m2: component masses in kg

    Returns:
        da/dt in m/s (negative for inspiral)
    """
    M = m1 + m2
    return -64 * G**3 * m1 * m2 * M / (5 * c**5 * a**3)


def merger_time(a: float, m1: float, m2: float) -> float:
    """Compute time to merger from separation a.

    t_merge = 5 c⁵ a⁴ / (256 G³ m₁ m₂ (m₁+m₂))

    Args:
        a: orbital separation in meters
        m1, m2: component masses in kg

    Returns:
        Time to merger in seconds
    """
    M = m1 + m2
    return 5 * c**5 * a**4 / (256 * G**3 * m1 * m2 * M)


def gw_frequency(a: float, m1: float, m2: float) -> float:
    """Compute gravitational wave frequency.

    f_GW = (1/π) √(G(m₁+m₂)/a³)

    Args:
        a: orbital separation in meters
        m1, m2: component masses in kg

    Returns:
        GW frequency in Hz
    """
    M = m1 + m2
    return (1 / np.pi) * np.sqrt(G * M / a**3)


def chirp_rate(f: float, M_c: float) -> float:
    """Compute chirp rate (frequency derivative).

    df/dt = (96/5) π^{8/3} (G M_c / c³)^{5/3} f^{11/3}

    Args:
        f: GW frequency in Hz
        M_c: chirp mass in kg

    Returns:
        Chirp rate df/dt in Hz/s
    """
    return (96 / 5) * np.pi**(8/3) * (G * M_c / c**3)**(5/3) * f**(11/3)


def evolve_binary(
    m1_solar: float = 30.0,
    m2_solar: float = 30.0,
    a0_solar: float = 1e6,  # initial separation in solar radii
    t_max_Gyr: float = 13.8,
    n_points: int = 1000,
) -> dict[str, Any]:
    """Evolve a binary system due to gravitational wave emission.

    Args:
        m1_solar, m2_solar: component masses in solar masses
        a0_solar: initial separation in solar radii
        t_max_Gyr: maximum evolution time in Gyr
        n_points: number of output points

    Returns:
        Dict with time, separation, frequency, strain evolution.
    """
    m1 = m1_solar * M_sun
    m2 = m2_solar * M_sun
    M = m1 + m2
    a0 = a0_solar * 6.957e8  # solar radii to meters

    M_c = chirp_mass(m1, m2)

    # Initial merger time
    t_merge_init = merger_time(a0, m1, m2)

    def rhs(t, y):
        a = y[0]
        if a < 100:  # prevent singularity near merger
            return [0]
        return [orbital_decay_rate(a, m1, m2)]

    t_end = min(t_max_Gyr * Gyr_s, t_merge_init * 0.99)

    sol = solve_ivp(rhs, [0, t_end], [a0],
                    method='RK45', dense_output=True,
                    rtol=1e-10, max_step=t_end / n_points)

    t_eval = np.linspace(0, t_end, n_points)
    a_eval = sol.sol(t_eval)

    # Compute derived quantities
    f_gw = np.array([gw_frequency(a, m1, m2) for a in a_eval])
    df_dt = np.array([chirp_rate(f, M_c) for f in f_gw])

    return {
        "t_s": t_eval,
        "t_Gyr": t_eval / Gyr_s,
        "a_m": a_eval,
        "a_solar_radii": a_eval / 6.957e8,
        "f_GW": f_gw,
        "df_dt": df_dt,
        "M_c_kg": M_c,
        "M_c_solar": M_c / M_sun,
        "eta": symmetric_mass_ratio(m1, m2),
        "t_merge_init_s": t_merge_init,
        "m1_solar": m1_solar,
        "m2_solar": m2_solar,
    }


def lisa_sensitivity(f: float) -> float:
    """Compute LISA sensitivity curve (simplified).

    S_n(f) ≈ 10^{-40} × [1 + (f/f₀)²] × Hz⁻¹
    where f₀ ≈ 10⁻² Hz

    Args:
        f: frequency in Hz

    Returns:
        Noise power spectral density
    """
    f0 = 0.01  # Hz
    return 1e-40 * (1 + (f / f0)**2)


def snr_quadrupole(m1_solar: float, m2_solar: float, distance_Mpc: float,
                    f_low: float = 10.0, f_high: float = 1000.0) -> dict[str, float]:
    """Compute SNR for a binary inspiral (simplified).

    SNR² = ∫ |h(f)|² / S_n(f) df

    For a circular inspiral, h(f) is given by the stationary phase approximation.

    Args:
        m1_solar, m2_solar: component masses in solar masses
        distance_Mpc: luminosity distance in Mpc
        f_low, f_high: frequency band

    Returns:
        Dict with SNR and related quantities.
    """
    m1 = m1_solar * M_sun
    m2 = m2_solar * M_sun
    M_c = chirp_mass(m1, m2)
    d = distance_Mpc * 3.0857e22  # Mpc to meters

    # Stationary phase approximation for h(f)
    f = np.geomspace(f_low, f_high, 1000)

    # h(f) amplitude
    h_amp = (G * M_c / c**2)**(5/4) * (np.pi * f)**(2/3) / (d * c**(3/4))

    # SNR integrand
    S_n = lisa_sensitivity(f)
    integrand = h_amp**2 / S_n

    # Integrate
    snr_squared = np.trapezoid(integrand, f)
    snr = np.sqrt(snr_squared)

    return {
        "SNR": snr,
        "SNR_squared": snr_squared,
        "distance_Mpc": distance_Mpc,
        "f_low": f_low,
        "f_high": f_high,
        "M_c_solar": M_c / M_sun,
    }
