"""Gravitational wave data analysis (T34).

Tools for GW parameter estimation and detection:
- Fisher matrix for parameter estimation
- SNR calculation for matched filtering
- Template generation for compact binary inspirals
- Parameter uncertainty estimation
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

G = 6.67430e-11
c = 299792458.0
M_sun = 1.98892e30
parsec = 3.0857e16


def chirp_mass(m1: float, m2: float) -> float:
    """Compute chirp mass M_c = (m₁ m₂)^{3/5} / (m₁ + m₂)^{1/5}."""
    return (m1 * m2)**(3/5) / (m1 + m2)**(1/5)


def inspiral_waveform_fd(f: np.ndarray, M_c: float, t_c: float = 0.0, phi_c: float = 0.0) -> np.ndarray:
    """Frequency-domain inspiral waveform (stationary phase approximation).

    h(f) = A f^{-7/6} exp(i ψ(f))

    where ψ(f) = 2πf t_c - φ_c + π/4 - (3/128) (π G M_c / c³ f)^{-5/3}

    Args:
        f: frequency array (Hz)
        M_c: chirp mass (kg)
        t_c: coalescence time
        phi_c: coalescence phase

    Returns:
        Complex frequency-domain waveform (unnormalized)
    """
    # Avoid division by zero
    f = np.maximum(f, 1e-20)

    # Amplitude: f^{-7/6}
    amp = f**(-7/6)

    # Phase: stationary phase approximation
    v = (np.pi * G * M_c * f / c**3)**(1/3)
    psi = 2 * np.pi * f * t_c - phi_c + np.pi / 4 - 3 / (128 * v**5)

    return amp * np.exp(1j * psi)


def fisher_matrix(
    f: np.ndarray,
    M_c: float,
    t_c: float = 0.0,
    phi_c: float = 0.0,
    S_n: np.ndarray = None,
    delta: dict = None,
) -> dict[str, Any]:
    """Compute Fisher matrix for inspiral parameters.

    Parameters: [M_c, t_c, phi_c]
    Γ_ij = 4 Re ∫ (∂h/∂θ_i)(∂h*/∂θ_j) / S_n(f) df

    Args:
        f: frequency array
        M_c: chirp mass
        t_c: coalescence time
        phi_c: coalescence phase
        S_n: noise PSD array
        delta: fractional step sizes for numerical derivatives

    Returns:
        Dict with Fisher matrix, covariance matrix, parameter uncertainties.
    """
    if S_n is None:
        S_n = np.ones_like(f) * 1e-40
    if delta is None:
        delta = {"M_c": 1e-6, "t_c": 1e-8, "phi_c": 1e-6}

    params = [M_c, t_c, phi_c]
    param_names = ["M_c", "t_c", "phi_c"]
    n_params = len(params)

    # Compute waveform
    h = inspiral_waveform_fd(f, M_c, t_c, phi_c)

    # Numerical derivatives
    derivatives = []
    for i, (p, dp) in enumerate(zip(params, delta.values())):
        p_plus = p * (1 + dp)
        p_minus = p * (1 - dp)

        params_plus = list(params)
        params_minus = list(params)
        params_plus[i] = p_plus
        params_minus[i] = p_minus

        h_plus = inspiral_waveform_fd(f, *params_plus)
        h_minus = inspiral_waveform_fd(f, *params_minus)

        dh = (h_plus - h_minus) / (p_plus - p_minus)
        derivatives.append(dh)

    # Fisher matrix
    df = np.diff(f)
    df = np.append(df, df[-1])

    Gamma = np.zeros((n_params, n_params))
    for i in range(n_params):
        for j in range(n_params):
            integrand = 4 * np.real(derivatives[i] * np.conj(derivatives[j])) / S_n
            integrand = np.nan_to_num(integrand, nan=0.0, posinf=0.0, neginf=0.0)
            Gamma[i, j] = np.trapezoid(integrand, f)

    # Covariance matrix (inverse of Fisher)
    try:
        cov = np.linalg.inv(Gamma)
    except (np.linalg.LinAlgError, ValueError):
        cov = np.full((n_params, n_params), np.inf)

    # Parameter uncertainties (1σ)
    uncertainties = {}
    for i, name in enumerate(param_names):
        uncertainties[name] = np.sqrt(abs(cov[i, i])) if np.isfinite(cov[i, i]) else np.inf

    # Correlation matrix
    diag = np.sqrt(np.abs(np.diag(cov)))
    diag[diag == 0] = 1
    corr = cov / np.outer(diag, diag)

    try:
        cond = np.linalg.cond(Gamma)
    except (np.linalg.LinAlgError, ValueError):
        cond = np.inf

    return {
        "fisher_matrix": Gamma,
        "covariance": cov,
        "uncertainties": uncertainties,
        "correlation": corr,
        "param_names": param_names,
        "condition_number": cond,
    }


def matched_filter_snr(
    h_template: np.ndarray,
    h_data: np.ndarray,
    S_n: np.ndarray,
    f: np.ndarray,
) -> dict[str, float]:
    """Compute matched filter SNR.

    SNR = 4 Re ∫ h*(f) d(f) / S_n(f) df / sqrt(4 ∫ |h(f)|² / S_n(f) df)

    Args:
        h_template: template waveform
        h_data: data (template + noise)
        S_n: noise PSD
        f: frequency array

    Returns:
        Dict with SNR and related quantities.
    """
    # Optimal SNR (template against itself)
    integrand_opt = 4 * np.abs(h_template)**2 / S_n
    rho_opt = np.sqrt(np.trapezoid(integrand_opt, f))

    # Matched filter SNR
    integrand_mf = 4 * np.real(np.conj(h_template) * h_data) / S_n
    rho_mf = np.trapezoid(integrand_mf, f) / rho_opt if rho_opt > 0 else 0

    return {
        "snr_optimal": rho_opt,
        "snr_matched_filter": rho_mf,
        "rho_opt": rho_opt,
        "rho_mf": rho_mf,
    }


def compute_horizon_distance(m1_solar: float, m2_solar: float, snr_threshold: float = 8.0) -> dict[str, float]:
    """Compute detection horizon distance for a binary inspiral.

    The horizon distance is the maximum distance at which a signal
    can be detected with SNR ≥ threshold.

    d_horizon ∝ M_c^{5/6} / √S_n

    Args:
        m1_solar, m2_solar: component masses
        snr_threshold: detection threshold

    Returns:
        Dict with horizon distance and related quantities.
    """
    m1 = m1_solar * M_sun
    m2 = m2_solar * M_sun
    M_c = chirp_mass(m1, m2)

    # Simplified: assume flat PSD and use characteristic strain
    # h_char ≈ (G M_c)^{5/6} f^{-1/6} / (c^{3/2} d)
    # For f ~ 100 Hz, SNR ~ h_char * √(T_obs / S_n)

    # Reference: LIGO BNS range ~ 100-200 Mpc for 1.4+1.4 M_sun
    # Scale with chirp mass
    M_c_ref = chirp_mass(1.4 * M_sun, 1.4 * M_sun)
    d_ref = 100e6 * parsec  # 100 Mpc in meters
    snr_ref = 8.0

    d_horizon = d_ref * (M_c / M_c_ref)**(5/6) * (snr_ref / snr_threshold)

    return {
        "d_horizon_Mpc": d_horizon / parsec,
        "d_horizon_m": d_horizon,
        "M_c_solar": M_c / M_sun,
        "snr_threshold": snr_threshold,
    }


def parameter_estimation_summary(
    m1_solar: float = 30.0,
    m2_solar: float = 30.0,
    distance_Mpc: float = 100.0,
) -> dict[str, Any]:
    """Compute parameter estimation summary for a GW event.

    Args:
        m1_solar, m2_solar: component masses
        distance_Mpc: luminosity distance

    Returns:
        Dict with SNR, Fisher matrix results, and uncertainties.
    """
    m1 = m1_solar * M_sun
    m2 = m2_solar * M_sun
    M_c = chirp_mass(m1, m2)

    # Frequency band (LIGO-like)
    f = np.geomspace(20, 2000, 2000)

    # Simple PSD
    f0 = 215  # Hz
    S_n = 1e-46 * ((f / f0)**(-4.14) + 2 * (f / f0)**(-0.69) * (1 + (f / f0)**2))

    # Waveform
    h = inspiral_waveform_fd(f, M_c)

    # SNR
    d = distance_Mpc * 3.0857e22
    h_scaled = h / d
    snr_sq = 4 * np.trapezoid(np.abs(h_scaled)**2 / S_n, f)
    snr = np.sqrt(snr_sq)

    # Fisher matrix
    fisher = fisher_matrix(f, M_c, S_n=S_n)

    return {
        "snr": snr,
        "M_c_solar": M_c / M_sun,
        "distance_Mpc": distance_Mpc,
        "fisher": fisher,
    }
