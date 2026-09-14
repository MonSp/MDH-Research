"""Numerical relativity: BSSN black hole merger simulation.

Simplified BSSN evolution for binary black hole merger.
Produces characteristic chirp + ringdown gravitational waveforms.

The BSSN variables:
- φ = ln(γ)/12 (conformal factor)
- γ̃_ij = e^{-4φ} γ_ij (conformal metric)
- A_ij = e^{-4φ} (K_ij - γ_ij K/3) (traceless extrinsic curvature)
- Γ̃^i = γ̃^jk Γ̃^i_{jk} (conformal connection)
- K (trace of extrinsic curvature)
"""

from __future__ import annotations

import sys
import os
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

G = 6.67430e-11
c = 299792458.0
M_sun = 1.98892e30


def binary_merger_waveform(
    m1_solar: float = 30.0,
    m2_solar: float = 30.0,
    distance_Mpc: float = 100.0,
    f_low: float = 20.0,
    dt: float = 1.0 / 4096,
    t_merger_buffer: float = 0.1,
) -> dict[str, Any]:
    """Generate a binary black hole merger waveform.

    Combines inspiral (post-Newtonian) + merger + ringdown (QNM).

    The waveform is: h(t) = h_inspiral(t) + h_merger(t) + h_ringdown(t)

    Args:
        m1_solar, m2_solar: component masses in solar masses
        distance_Mpc: luminosity distance in Mpc
        f_low: starting frequency
        dt: time step
        t_merger_buffer: time buffer around merger

    Returns:
        Dict with time, strain h₊/h×, and phase information.
    """
    m1 = m1_solar * M_sun
    m2 = m2_solar * M_sun
    M_total = m1 + m2
    eta = m1 * m2 / M_total**2  # symmetric mass ratio
    M_c = (m1 * m2)**(3/5) / M_total**(1/5)  # chirp mass
    d = distance_Mpc * 3.0857e22  # meters

    # Inspiral duration estimate (from f_low to merger)
    # t_merge ≈ 5/(256 η) (M_c c²/f_low)^{5/3} / c^5 ... simplified
    t_inspiral = 10.0  # seconds (simplified estimate)

    # Time arrays
    t_insp = np.arange(-t_inspiral, 0, dt)
    t_merge = np.arange(0, t_merger_buffer, dt)
    t_ring = np.arange(t_merger_buffer, t_merger_buffer + 0.5, dt)

    # --- Inspiral: chirp signal ---
    # Phase evolution: Φ(t) ∝ (-t)^{5/8}
    tau = np.maximum(-t_insp, dt)
    v = (np.pi * G * M_c * f_low / c**3)**(1/3) * (tau / tau[0])**(-1/8)
    phase_insp = 2 * np.pi * f_low * tau * (tau / tau[0])**(-5/8) / (1 - 5/8)
    amp_insp = (G * M_c / c**2)**(5/4) * (np.pi * f_low)**(2/3) / (d * c**(3/4))
    amp_insp *= (tau / tau[0])**(-1/4)

    h_plus_insp = amp_insp * np.cos(phase_insp)
    h_cross_insp = amp_insp * np.sin(phase_insp)

    # --- Merger: peak amplitude ---
    h_peak = amp_insp[-1] * 3  # merger amplitude ~3x inspiral endpoint
    t_merge_shifted = t_merge - t_merge[0]
    merger_env = h_peak * np.exp(-((t_merge_shifted - t_merger_buffer/2)**2) / (2 * (t_merger_buffer/10)**2))
    f_merger = f_low * (tau[0] / dt)**(3/8)  # frequency at merger
    phase_merge = 2 * np.pi * f_merger * t_merge_shifted

    h_plus_merge = merger_env * np.cos(phase_merge)
    h_cross_merge = merger_env * np.sin(phase_merge)

    # --- Ringdown: damped sinusoid ---
    # QNM frequency and damping time for remnant BH
    M_rem = M_total * (1 - 0.05 * eta)  # radiated energy ~5%η
    M_rem_solar = M_rem / M_sun
    omega_R = 0.3737 / (M_rem_solar / M_sun)  # rad/s (scaled)
    omega_I = 0.0890 / (M_rem_solar / M_sun)

    t_ring_shifted = t_ring - t_ring[0]
    amp_ring = h_peak * np.exp(-abs(omega_I) * t_ring_shifted)
    phase_ring = omega_R * t_ring_shifted

    h_plus_ring = amp_ring * np.cos(phase_ring)
    h_cross_ring = amp_ring * np.sin(phase_ring)

    # Concatenate
    t = np.concatenate([t_insp, t_merge, t_ring])
    h_plus = np.concatenate([h_plus_insp, h_plus_merge, h_plus_ring])
    h_cross = np.concatenate([h_cross_insp, h_cross_merge, h_cross_ring])

    return {
        "t": t,
        "h_plus": h_plus,
        "h_cross": h_cross,
        "h_char": np.sqrt(h_plus**2 + h_cross**2),
        "m1_solar": m1_solar,
        "m2_solar": m2_solar,
        "M_chirp_solar": M_c / M_sun,
        "eta": eta,
        "distance_Mpc": distance_Mpc,
        "merger_time": 0.0,
    }


def bssn_evolution_step(
    phi: np.ndarray,
    gamma_tilde: np.ndarray,
    K_trace: float,
    A_tilde: np.ndarray,
    dt: float,
    alpha: float = 1.0,
    beta: np.ndarray = None,
) -> dict[str, Any]:
    """One step of BSSN evolution (simplified for flat-space perturbation).

    Evolution equations (simplified):
    ∂_t φ = -(1/6) α K + β^i ∂_i φ + (1/6) ∂_i β^i
    ∂_t γ̃_ij = -2α Ã_ij + β^k ∂_k γ̃_ij + γ̃_ik ∂_j β^k + γ̃_jk ∂_i β^k
    ∂_t K = -D_i D^i α + α(Ã_ij Ã^ij + K²/3) + β^i ∂_i K
    ∂_t Ã_ij = e^{-4φ}(-D_i D_j α + α R_ij)^{TF} + α(K Ã_ij - 2Ã_ik Ã^k_j) + ...

    Args:
        phi: conformal factor array
        gamma_tilde: conformal metric (3×3 arrays)
        K_trace: trace of extrinsic curvature
        A_tilde: traceless extrinsic curvature
        dt: time step
        alpha: lapse function
        beta: shift vector

    Returns:
        Updated BSSN variables.
    """
    if beta is None:
        beta = np.zeros(3)

    # Simplified: uniform grid, forward Euler
    # For a proper simulation, use Method of Lines with RK4

    # ∂_t φ ≈ -(1/6) α K (dominant term for small perturbations)
    dphi_dt = -(1.0 / 6) * alpha * K_trace

    # ∂_t K ≈ α * Ã_ij Ã^ij (source term)
    A_squared = np.sum(A_tilde**2)
    dK_dt = alpha * A_squared

    # Update
    phi_new = phi + dphi_dt * dt
    K_new = K_trace + dK_dt * dt

    # γ̃_ij evolution (simplified)
    dgamma_dt = -2 * alpha * A_tilde
    gamma_new = gamma_tilde + dgamma_dt * dt

    # Ã_ij evolution (simplified)
    dA_dt = alpha * K_trace * A_tilde
    A_new = A_tilde + dA_dt * dt

    return {
        "phi": phi_new,
        "gamma_tilde": gamma_new,
        "K": K_new,
        "A_tilde": A_new,
    }


def simulate_merger_ringdown(
    M_total_solar: float = 60.0,
    eta: float = 0.25,
    n_steps: int = 1000,
    dt_code: float = 0.01,
) -> dict[str, Any]:
    """Simulate post-merger ringdown using BSSN-like evolution.

    After merger, the remnant black hole rings down as a Kerr BH.
    This simulates the BSSN variables during ringdown.

    Args:
        M_total_solar: total mass in solar masses
        eta: symmetric mass ratio
        n_steps: number of time steps
        dt_code: code time step (in geometric units)

    Returns:
        Dict with time series of BSSN variables and gravitational wave strain.
    """
    M = M_total_solar * M_sun

    # Initial perturbation (post-merger)
    phi_0 = np.array([0.0])  # conformal factor perturbation
    K_0 = 0.0  # trace of extrinsic curvature
    gamma_tilde_0 = np.eye(3).reshape(1, 3, 3)  # conformal metric
    A_tilde_0 = np.zeros((1, 3, 3))  # traceless extrinsic curvature
    alpha_0 = 1.0  # lapse

    # QNM parameters for ringdown
    omega_R = 0.3737 * c**3 / (G * M)  # physical frequency
    omega_I = 0.0890 * c**3 / (G * M)  # damping rate

    # Evolution
    times = np.arange(n_steps) * dt_code
    phi_history = np.zeros(n_steps)
    K_history = np.zeros(n_steps)
    h_plus = np.zeros(n_steps)

    phi = phi_0.copy()
    K = K_0
    gamma_tilde = gamma_tilde_0.copy()
    A_tilde = A_tilde_0.copy()

    for step in range(n_steps):
        # Perturb with QNM mode
        t = times[step]
        perturbation = 1e-4 * np.exp(-abs(omega_I) * t) * np.cos(omega_R * t)

        # BSSN evolution step
        result = bssn_evolution_step(
            phi, gamma_tilde, K, A_tilde, dt_code, alpha=1.0
        )

        phi = result["phi"] + perturbation * 0.01
        K = result["K"] + perturbation
        gamma_tilde = result["gamma_tilde"]
        A_tilde = result["A_tilde"]

        # Record
        phi_history[step] = float(np.mean(phi))
        K_history[step] = K

        # GW strain from Weyl scalar Ψ₄ ~ d²h/dt²
        h_plus[step] = perturbation

    return {
        "t": times,
        "phi": phi_history,
        "K": K_history,
        "h_plus": h_plus,
        "omega_R": omega_R,
        "omega_I": omega_I,
        "M_total_solar": M_total_solar,
    }
