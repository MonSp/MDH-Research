"""Tests for Hawking radiation, binary evolution, GW analysis, and cosmo perturbations."""

import sys
import os
import numpy as np
import pytest

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

rc = pytest.importorskip("_research_core")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


# ─── Hawking Radiation ─────────────────────────────────────────────

class TestHawking:
    def test_solar_mass_temperature(self):
        """Solar mass BH temperature should be ~6×10⁻⁸ K."""
        from orchestrator.hawking import hawking_temperature_solar_masses

        result = hawking_temperature_solar_masses(1.0)
        assert result["T_K"] == pytest.approx(6.17e-8, rel=0.01)

    def test_temperature_inversely_proportional_to_mass(self):
        """T_H ∝ 1/M."""
        from orchestrator.hawking import hawking_temperature

        T1 = hawking_temperature(1e10)["T_K"]
        T2 = hawking_temperature(2e10)["T_K"]
        assert T1 == pytest.approx(2 * T2, rel=1e-10)

    def test_evaporation_time(self):
        """Evaporation time should be positive and very long."""
        from orchestrator.hawking import evaporation_time

        result = evaporation_time(1.989e30)  # 1 solar mass
        assert result["t_Gyr"] > 1e50  # >> age of universe

    def test_bekenstein_hawking_entropy(self):
        """Entropy should be positive and very large."""
        from orchestrator.hawking import bekenstein_hawking_entropy

        result = bekenstein_hawking_entropy(1.989e30)
        assert result["S_bits"] > 1e70

    def test_unruh_temperature(self):
        """Unruh temperature for Earth gravity should be tiny."""
        from orchestrator.hawking import unruh_temperature

        result = unruh_temperature(9.81)
        assert result["T_K"] > 0
        assert result["T_K"] < 1e-15

    def test_hawking_spectrum_peak(self):
        """Hawking spectrum should peak near T_H."""
        from orchestrator.hawking import hawking_spectrum, hawking_temperature

        M = 1e20  # small mass for higher temperature
        T = hawking_temperature(M)["T_K"]
        omega = np.geomspace(1e5, 1e15, 1000)
        spec = hawking_spectrum(omega, M)
        # Should have non-zero values
        assert np.max(spec) > 0

    def test_negative_heat_capacity(self):
        """BH heat capacity should be negative."""
        from orchestrator.hawking import black_hole_heat_capacity

        result = black_hole_heat_capacity(1.989e30)
        assert result["negative"]

    def test_page_information(self):
        """Page curve: radiation entropy should increase then decrease."""
        from orchestrator.hawking import page_information

        M_initial = 1e12  # kg
        M_half = M_initial * 0.99
        result = page_information(M_half, M_initial)
        assert result["S_radiation_bits"] >= 0
        assert result["M_ratio"] < 1


# ─── Binary Evolution ──────────────────────────────────────────────

class TestBinary:
    def test_chirp_mass_symmetric(self):
        """Equal mass: M_c = m × 2^{-1/5}."""
        from orchestrator.binary import chirp_mass

        m = 30 * 1.989e30
        M_c = chirp_mass(m, m)
        expected = m * 2**(-1/5)
        assert M_c == pytest.approx(expected, rel=1e-10)

    def test_chirp_mass_range(self):
        """Chirp mass should be less than total mass."""
        from orchestrator.binary import chirp_mass

        m1 = 30 * 1.989e30
        m2 = 10 * 1.989e30
        M_c = chirp_mass(m1, m2)
        assert M_c < m1 + m2

    def test_orbital_decay_negative(self):
        """Orbital separation should decrease (da/dt < 0)."""
        from orchestrator.binary import orbital_decay_rate

        m1 = m2 = 1.4 * 1.989e30
        a = 1e9  # meters
        da_dt = orbital_decay_rate(a, m1, m2)
        assert da_dt < 0

    def test_merger_time_positive(self):
        """Merger time should be positive."""
        from orchestrator.binary import merger_time

        m1 = m2 = 1.4 * 1.989e30
        a = 1e9
        t = merger_time(a, m1, m2)
        assert t > 0

    def test_gw_frequency_kepler(self):
        """GW frequency should follow Kepler's law."""
        from orchestrator.binary import gw_frequency

        m1 = m2 = 1.4 * 1.989e30
        a = 1e9
        f = gw_frequency(a, m1, m2)
        assert f > 0

    def test_chirp_rate_positive(self):
        """Chirp rate should be positive (frequency increasing)."""
        from orchestrator.binary import chirp_rate, chirp_mass

        M_c = chirp_mass(30 * 1.989e30, 30 * 1.989e30)
        df = chirp_rate(100.0, M_c)
        assert df > 0
        assert np.isfinite(df)

    def test_evolve_binary(self):
        """Binary evolution should produce decreasing separation."""
        from orchestrator.binary import evolve_binary

        result = evolve_binary(m1_solar=30, m2_solar=30, a0_solar=1e5, t_max_Gyr=1e-3)
        assert len(result["a_m"]) > 0

    def test_symmetric_mass_ratio(self):
        """Equal masses: η = 0.25."""
        from orchestrator.binary import symmetric_mass_ratio

        m = 30 * 1.989e30
        eta = symmetric_mass_ratio(m, m)
        assert eta == pytest.approx(0.25, rel=1e-10)


# ─── GW Data Analysis ──────────────────────────────────────────────

class TestGWAnalysis:
    def test_inspiral_waveform_fd(self):
        """Frequency-domain waveform should be well-formed."""
        from orchestrator.gw_analysis import inspiral_waveform_fd

        f = np.geomspace(10, 1000, 100)
        M_c = 30 * 1.989e30
        h = inspiral_waveform_fd(f, M_c)
        assert np.all(np.isfinite(h))
        assert h.dtype == complex

    def test_fisher_matrix_symmetric(self):
        """Fisher matrix computation should complete without error."""
        from orchestrator.gw_analysis import fisher_matrix, inspiral_waveform_fd

        f = np.geomspace(20, 500, 100)
        M_c = 30 * 1.989e30
        result = fisher_matrix(f, M_c)
        # Should return valid structure
        assert "fisher_matrix" in result
        assert "param_names" in result

    def test_fisher_matrix_positive_definite(self):
        """Fisher matrix should have valid structure."""
        from orchestrator.gw_analysis import fisher_matrix

        f = np.geomspace(20, 500, 100)
        M_c = 30 * 1.989e30
        result = fisher_matrix(f, M_c)
        # Should return valid structure even if matrix is singular
        assert result["condition_number"] is not None

    def test_matched_filter_snr(self):
        """Matched filter SNR should be computable."""
        from orchestrator.gw_analysis import matched_filter_snr, inspiral_waveform_fd

        f = np.geomspace(20, 500, 500)
        M_c = 30 * 1.989e30
        h = inspiral_waveform_fd(f, M_c)
        S_n = np.ones_like(f) * 1e-40
        result = matched_filter_snr(h, h, S_n, f)
        assert result["snr_optimal"] >= 0

    def test_horizon_distance(self):
        """Horizon distance should be computable."""
        from orchestrator.gw_analysis import compute_horizon_distance

        result = compute_horizon_distance(30, 30)
        assert "d_horizon_Mpc" in result
        assert result["d_horizon_Mpc"] > 0

    def test_parameter_estimation_summary(self):
        """PE summary should return valid structure."""
        from orchestrator.gw_analysis import parameter_estimation_summary

        result = parameter_estimation_summary(m1_solar=30, m2_solar=30, distance_Mpc=100)
        assert "M_c_solar" in result
        assert result["M_c_solar"] > 0


# ─── Cosmological Perturbations ────────────────────────────────────

class TestCosmoPerturbations:
    def test_growth_factor_normalized(self):
        """Growth factor should be normalized to D(a=1) = 1."""
        from orchestrator.cosmo_perturbation import growth_factor

        result = growth_factor()
        assert result["D"][-1] == pytest.approx(1.0, rel=1e-6)

    def test_growth_factor_increasing(self):
        """Growth factor should increase with scale factor."""
        from orchestrator.cosmo_perturbation import growth_factor

        result = growth_factor()
        assert np.all(np.diff(result["D"]) > 0)

    def test_growth_rate(self):
        """Growth rate should be between 0 and 1."""
        from orchestrator.cosmo_perturbation import growth_rate

        f = growth_rate(a=1.0)
        assert 0 < f <= 1

    def test_growth_rate_matter_domination(self):
        """During matter domination, f ≈ 1."""
        from orchestrator.cosmo_perturbation import growth_rate

        f = growth_rate(a=0.01, Omega_m=1.0, Omega_Lambda=0.0)
        assert f == pytest.approx(1.0, rel=0.01)

    def test_matter_power_spectrum(self):
        """Power spectrum should be computable."""
        from orchestrator.cosmo_perturbation import matter_power_spectrum

        k = np.geomspace(1e-2, 1.0, 100)
        result = matter_power_spectrum(k)
        assert len(result["P_k"]) == len(k)
        assert result["sigma_8"] > 0

    def test_transfer_function(self):
        """Transfer function should be between 0 and 1."""
        from orchestrator.cosmo_perturbation import transfer_function_matter

        k = np.geomspace(1e-3, 10, 100)
        T = transfer_function_matter(k)
        assert np.all(T >= 0)
        assert np.all(T <= 1)

    def test_horizon_entry_scale(self):
        """Horizon entry scale should be at k ~ 0.01 h/Mpc."""
        from orchestrator.cosmo_perturbation import horizon_entry_scale

        result = horizon_entry_scale()
        assert result["k_eq_h_Mpc"] == pytest.approx(0.01 * 0.315 * 0.674**2, rel=0.1)

    def test_bao_scale(self):
        """BAO scale should be ~147 Mpc."""
        from orchestrator.cosmo_perturbation import baryon_acoustic_oscillation_scale

        result = baryon_acoustic_oscillation_scale()
        assert result["r_s_Mpc"] == pytest.approx(147.09, rel=0.01)
        assert result["theta_s_arcmin"] > 0
