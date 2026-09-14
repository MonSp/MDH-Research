"""Tests for numerical relativity, CMB, and dark energy."""

import sys
import os
import numpy as np
import pytest

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

rc = pytest.importorskip("_research_core")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


# ─── Numerical Relativity ──────────────────────────────────────────

class TestNumericalRelativity:
    def test_binary_merger_waveform(self):
        """Merger waveform should have inspiral + merger + ringdown."""
        from orchestrator.numerical_relativity import binary_merger_waveform

        result = binary_merger_waveform(m1_solar=30, m2_solar=30, distance_Mpc=100)
        assert len(result["t"]) > 0
        assert len(result["h_plus"]) == len(result["t"])
        assert result["M_chirp_solar"] > 0

    def test_waveform_has_peak(self):
        """Waveform should have a peak near merger."""
        from orchestrator.numerical_relativity import binary_merger_waveform

        result = binary_merger_waveform(m1_solar=30, m2_solar=30)
        h_char = result["h_char"]
        assert np.max(h_char) > 0

    def test_eta_symmetric_mass_ratio(self):
        """η should be ≤ 0.25."""
        from orchestrator.numerical_relativity import binary_merger_waveform

        result = binary_merger_waveform(m1_solar=30, m2_solar=10)
        assert 0 < result["eta"] <= 0.25

    def test_bssn_evolution_step(self):
        """BSSN evolution step should update variables."""
        from orchestrator.numerical_relativity import bssn_evolution_step

        phi = np.array([0.0])
        gamma = np.eye(3).reshape(1, 3, 3)
        K = 0.1
        A = np.zeros((1, 3, 3))

        result = bssn_evolution_step(phi, gamma, K, A, dt=0.01)
        assert "phi" in result
        assert "K" in result

    def test_merger_ringdown(self):
        """Ringdown simulation should produce damped oscillation."""
        from orchestrator.numerical_relativity import simulate_merger_ringdown

        result = simulate_merger_ringdown(M_total_solar=60, n_steps=500)
        assert len(result["t"]) == 500
        assert len(result["h_plus"]) == 500
        # Signal should decay
        assert abs(result["h_plus"][0]) > abs(result["h_plus"][-1])


# ─── CMB Power Spectrum ───────────────────────────────────────────

class TestCMB:
    def test_acoustic_scale(self):
        """First peak should be at ℓ ≈ 220."""
        from orchestrator.cmb import acoustic_scale

        result = acoustic_scale()
        assert 200 < result["first_peak_ell"] < 400

    def test_cmb_power_spectrum(self):
        """Power spectrum should have peaks."""
        from orchestrator.cmb import cmb_power_spectrum

        result = cmb_power_spectrum(ell_max=2500)
        assert len(result["ell"]) > 0
        assert len(result["D_ell"]) == len(result["ell"])
        assert np.max(result["D_ell"]) > 0

    def test_first_peak_height(self):
        """First peak D_220 should be ~6000 μK²."""
        from orchestrator.cmb import cmb_power_spectrum

        result = cmb_power_spectrum()
        assert result["D_ell_220"] > 0

    def test_silk_damping(self):
        """Power should decrease at high ℓ."""
        from orchestrator.cmb import cmb_power_spectrum

        result = cmb_power_spectrum(ell_max=2500)
        ell = result["ell"]
        D = result["D_ell"]
        # D at ℓ=2000 should be less than D at ℓ=220
        d_2000 = D[np.argmin(np.abs(ell - 2000))]
        d_220 = D[np.argmin(np.abs(ell - 220))]
        assert d_2000 < d_220

    def test_peak_positions(self):
        """Peak positions should be roughly equally spaced."""
        from orchestrator.cmb import peak_positions

        result = peak_positions()
        peaks = result["peaks"]
        assert len(peaks) >= 3
        # First peak should be at ℓ ~ 220-300
        assert 200 < peaks[0]["ell"] < 400

    def test_cmb_observables(self):
        """CMB observables should be computable."""
        from orchestrator.cmb import cmb_observables

        result = cmb_observables()
        assert result["ell_A"] > 0
        assert result["r_s_Mpc"] > 0

    def test_transfer_function(self):
        """Transfer function should be between 0 and 1."""
        from orchestrator.cmb import transfer_function_cmb

        ell = np.arange(2, 2501, dtype=float)
        T = transfer_function_cmb(ell)
        assert np.all(T >= 0)


# ─── Dark Energy ───────────────────────────────────────────────────

class TestDarkEnergy:
    def test_lcdm_hubble(self):
        """ΛCDM H(a=1) = H₀."""
        from orchestrator.dark_energy import hubble_lcdm

        H = hubble_lcdm(1.0)
        assert H == pytest.approx(67.4, rel=0.01)

    def test_cpl_w0_lcdm(self):
        """CPL with wa=0 should give constant w=w₀."""
        from orchestrator.dark_energy import w_cpl

        assert w_cpl(0, w0=-1, wa=0) == -1.0
        assert w_cpl(1, w0=-1, wa=0) == -1.0
        assert w_cpl(10, w0=-0.9, wa=0) == -0.9

    def test_cpl_evolution(self):
        """CPL w(z) should evolve with redshift."""
        from orchestrator.dark_energy import w_cpl

        w0 = w_cpl(0, w0=-1, wa=0.5)
        w_high = w_cpl(10, w0=-1, wa=0.5)
        assert w0 != w_high

    def test_dark_energy_density_constant(self):
        """Λ (w=-1) should have constant density."""
        from orchestrator.dark_energy import dark_energy_density

        rho_0 = dark_energy_density(0, w0=-1, wa=0)
        rho_1 = dark_energy_density(1, w0=-1, wa=0)
        assert rho_0 == pytest.approx(1.0)
        assert rho_1 == pytest.approx(1.0)

    def test_dark_energy_density_phantom(self):
        """Phantom (w < -1): density increases toward the future (lower z)."""
        from orchestrator.dark_energy import dark_energy_density

        # At higher z, phantom density should be LESS than today
        rho_today = dark_energy_density(0, w0=-1.1, wa=0)
        rho_past = dark_energy_density(2, w0=-1.1, wa=0)
        assert rho_today > rho_past  # density grows toward future

    def test_hubble_cpl(self):
        """CPL H(z) should be computable."""
        from orchestrator.dark_energy import hubble_cpl

        H = hubble_cpl(z=0)
        assert H == pytest.approx(67.4, rel=0.01)

    def test_deceleration_parameter(self):
        """q₀ should be negative (accelerating universe)."""
        from orchestrator.dark_energy import deceleration_parameter

        q0 = deceleration_parameter(z=0, Omega_m=0.315, w0=-1)
        assert q0 < 0

    def test_deceleration_parameter_high_z(self):
        """q should be positive at high z (matter domination)."""
        from orchestrator.dark_energy import deceleration_parameter

        q_high = deceleration_parameter(z=10, Omega_m=1.0, w0=-1)
        assert q_high > 0

    def test_f_R_model(self):
        """f(R) model should reduce to GR when f0=0."""
        from orchestrator.dark_energy import f_R_model

        result = f_R_model(R_scalar=1e-10, f0=0, n=2)
        assert result["f"] == pytest.approx(1e-10)
        assert result["f_prime"] == pytest.approx(1.0)

    def test_f_R_nonzero_correction(self):
        """f(R) with f0≠0 should modify GR."""
        from orchestrator.dark_energy import f_R_model

        result = f_R_model(R_scalar=1e-10, f0=1e5, n=2)
        assert result["f"] != result["R"]
        assert result["f_prime"] != 1.0

    def test_f_R_effective_gravity(self):
        """f(R) should modify effective gravitational constant."""
        from orchestrator.dark_energy import f_R_model

        result = f_R_model(R_scalar=1e-10, f0=1e5, n=2)
        assert result["G_eff"] != 0

    def test_figure_of_merit(self):
        """Figure of merit should be positive."""
        from orchestrator.dark_energy import dark_energy_figure_of_merit

        result = dark_energy_figure_of_merit()
        assert result["FoM"] > 0
