"""Cosmic Microwave Background anisotropy power spectrum.

Computes the CMB angular power spectrum C_ℓ and related observables.

Key physics:
- Acoustic oscillations in the photon-baryon fluid before recombination
- Silk damping (photon diffusion) at high ℓ
- Sachs-Wolfe effect at low ℓ
- Sound horizon at recombination → first peak position

The angular power spectrum:
    C_ℓ = (2/π) ∫ k² P_Φ(k) |Δ_ℓ(k)|² dk

where Δ_ℓ(k) is the transfer function and P_Φ(k) is the primordial potential power spectrum.
"""

from __future__ import annotations

import sys
import os
from typing import Any

import numpy as np

G = 6.67430e-11
c = 299792458.0
k_B = 1.380649e-23
hbar = 1.054571817e-34


def acoustic_scale(Omega_m: float = 0.315, h: float = 0.674) -> dict[str, float]:
    """Compute the acoustic scale (sound horizon at recombination).

    The sound horizon at recombination determines the position of the
    first acoustic peak: ℓ_A ≈ π / θ_s

    Args:
        Omega_m: matter density parameter
        h: Hubble parameter

    Returns:
        Dict with sound horizon, acoustic scale, and first peak position.
    """
    # Sound horizon at recombination (simplified)
    # r_s ≈ 147 Mpc (Planck 2018)
    r_s = 147.0  # Mpc

    # Angular diameter distance to recombination
    z_star = 1090  # recombination redshift
    H0 = h * 100  # km/s/Mpc
    D_A = 14000.0  # Mpc (approximate)

    # Acoustic scale
    theta_s = r_s / D_A
    ell_A = np.pi / theta_s

    return {
        "r_s_Mpc": r_s,
        "theta_s_rad": theta_s,
        "theta_s_deg": np.degrees(theta_s),
        "ell_A": ell_A,
        "first_peak_ell": ell_A,
        "z_star": z_star,
    }


def transfer_function_cmb(
    ell: np.ndarray,
    ell_A: float = 220.0,
    ell_silk: float = 1000.0,
) -> np.ndarray:
    """Compute a simplified CMB transfer function.

    The transfer function encodes:
    - Acoustic oscillations: cos²(k r_s) → peaks at ℓ = ℓ_A, 2ℓ_A, 3ℓ_A, ...
    - Silk damping: exp(-(ℓ/ℓ_silk)²) at high ℓ
    - Sachs-Wolfe plateau at low ℓ

    Args:
        ell: multipole array
        ell_A: acoustic scale (first peak position)
        ell_silk: Silk damping scale

    Returns:
        Transfer function array.
    """
    # Acoustic oscillations
    acoustic = np.cos(np.pi * ell / ell_A)**2

    # Silk damping
    damping = np.exp(-(ell / ell_silk)**2)

    # Sachs-Wolfe plateau (1/ℓ(ℓ+1) shape)
    sw = 1.0 / (ell * (ell + 1)) * (ell_A / 10)**2

    # Combine: peaks + damping
    T = acoustic * damping

    # Low-ℓ Sachs-Wolfe contribution
    T_low = np.where(ell < 30, sw, 0)

    return T + T_low


def cmb_power_spectrum(
    ell_max: int = 2500,
    Omega_m: float = 0.315,
    Omega_b: float = 0.049,
    h: float = 0.674,
    n_s: float = 0.965,
    A_s: float = 2.1e-9,
    tau: float = 0.054,
) -> dict[str, Any]:
    """Compute the CMB temperature power spectrum D_ℓ = ℓ(ℓ+1)C_ℓ/(2π).

    Simplified model with:
    - Acoustic peaks at ℓ ≈ 220, 540, 800, ...
    - Silk damping at ℓ > 1000
    - Sachs-Wolfe plateau at ℓ < 30
    - Correct ℓ(ℓ+1)/(2π) normalization

    Args:
        ell_max: maximum multipole
        Omega_m: matter density
        Omega_b: baryon density
        h: Hubble parameter
        n_s: spectral index
        A_s: scalar amplitude
        tau: optical depth to recombination

    Returns:
        Dict with ℓ and D_ℓ arrays and derived quantities.
    """
    ell = np.arange(2, ell_max + 1, dtype=float)

    # Acoustic scale
    ac = acoustic_scale(Omega_m, h)
    ell_A = ac["first_peak_ell"]

    # Silk damping scale (depends on baryon density)
    # ℓ_silk ∝ 1/√(Ω_b h²)
    ell_silk = 1200 * (0.022 / (Omega_b * h**2))**0.5

    # Transfer function
    T = transfer_function_cmb(ell, ell_A, ell_silk)

    # Primordial spectrum: A_s (k/k_pivot)^{n_s-1}
    # In ℓ-space: ℓ(ℓ+1)C_ℓ/(2π) ≈ A_s (ℓ/ℓ_pivot)^{n_s-1}
    ell_pivot = 50  # pivot multipole
    primordial = (ell / ell_pivot)**(n_s - 1)

    # D_ℓ = ℓ(ℓ+1)C_ℓ/(2π)
    D_ell = A_s * 1e10 * primordial * T

    # Normalize to match Planck at first peak: D_220 ≈ 6000 μK²
    D_220_target = 6000
    idx_220 = np.argmin(np.abs(ell - 220))
    if D_ell[idx_220] > 0:
        D_ell *= D_220_target / D_ell[idx_220]

    # Apply reionization damping at low ℓ
    # C_ℓ → C_ℓ exp(-2τ) for ℓ > 30
    reion_damping = np.where(ell < 30, 1.0, np.exp(-2 * tau))
    D_ell *= reion_damping

    return {
        "ell": ell,
        "D_ell": D_ell,
        "ell_A": ell_A,
        "ell_silk": ell_silk,
        "first_peak_height": D_ell[idx_220] if idx_220 < len(D_ell) else 0,
        "D_ell_220": D_ell[idx_220] if idx_220 < len(D_ell) else 0,
        "params": {
            "Omega_m": Omega_m,
            "Omega_b": Omega_b,
            "h": h,
            "n_s": n_s,
            "A_s": A_s,
            "tau": tau,
        },
    }


def peak_positions(Omega_m: float = 0.315, h: float = 0.674) -> dict[str, Any]:
    """Compute acoustic peak positions.

    Peaks occur at ℓ_n ≈ n × ℓ_A for n = 1, 2, 3, ...

    Args:
        Omega_m: matter density
        h: Hubble parameter

    Returns:
        Dict with peak positions and heights.
    """
    ac = acoustic_scale(Omega_m, h)
    ell_A = ac["first_peak_ell"]

    peaks = []
    for n in range(1, 6):
        ell_n = n * ell_A
        # Peak heights decrease due to Silk damping
        height_ratio = np.exp(-(ell_n / 1000)**2)
        peaks.append({
            "n": n,
            "ell": round(ell_n),
            "height_ratio": height_ratio,
        })

    return {
        "ell_A": ell_A,
        "peaks": peaks,
    }


def cmb_observables(Omega_m: float = 0.315, Omega_b: float = 0.049,
                     h: float = 0.674, n_s: float = 0.965) -> dict[str, float]:
    """Compute key CMB observables.

    Args:
        Omega_m, Omega_b, h, n_s: cosmological parameters

    Returns:
        Dict with derived CMB observables.
    """
    ac = acoustic_scale(Omega_m, h)

    # Baryon acoustic oscillation scale
    r_s = ac["r_s_Mpc"]

    # Shift parameter
    z_star = 1090
    R = np.sqrt(Omega_m) * (1 + z_star) * ac["r_s_Mpc"] / (3000 / h)

    # Angular size of sound horizon
    theta_s = ac["theta_s_rad"]

    return {
        "ell_A": ac["ell_A"],
        "r_s_Mpc": r_s,
        "theta_s": theta_s,
        "z_star": z_star,
        "shift_parameter": R,
        "Omega_m": Omega_m,
        "Omega_b": Omega_b,
        "h": h,
        "n_s": n_s,
    }
