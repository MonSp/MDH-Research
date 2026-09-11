"""Tests for Regge-Wheeler/Zerilli, post-Newtonian, and cosmology."""

import sys
import os
import numpy as np
import pytest

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

rc = pytest.importorskip("_research_core")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


# ─── Regge-Wheeler / Zerilli ──────────────────────────────────────

class TestReggeWheeler:
    def test_tortoise_coordinate(self):
        """Tortoise coordinate should be monotonically increasing."""
        from orchestrator.perturbation_eqns import tortoise_coordinate

        r = np.array([3.0, 5.0, 10.0, 50.0])
        r_star = tortoise_coordinate(r, M=1.0)
        assert np.all(np.diff(r_star) > 0)

    def test_rw_potential_positive(self):
        """RW potential should be positive outside horizon."""
        from orchestrator.perturbation_eqns import regge_wheeler_potential

        r = np.linspace(2.1, 50, 100)
        V = regge_wheeler_potential(r, l=2, M=1.0)
        assert np.all(V > 0)

    def test_rw_potential_zero_at_horizon(self):
        """RW potential should vanish at the horizon."""
        from orchestrator.perturbation_eqns import regge_wheeler_potential

        V = regge_wheeler_potential(np.array([2.0]), l=2, M=1.0)
        assert abs(V[0]) < 1e-10

    def test_zerilli_potential_positive(self):
        """Zerilli potential should be positive outside horizon."""
        from orchestrator.perturbation_eqns import zerilli_potential

        r = np.linspace(2.1, 50, 100)
        V = zerilli_potential(r, l=2, M=1.0)
        assert np.all(V > 0)

    def test_rw_solver(self):
        """RW solver should produce a valid solution."""
        from orchestrator.perturbation_eqns import solve_regge_wheeler

        result = solve_regge_wheeler(M=1.0, l=2, omega=0.37 - 0.09j)
        assert result["success"]
        assert len(result["psi"]) > 0
        assert np.all(np.isfinite(result["psi"]))

    def test_zerilli_solver(self):
        """Zerilli solver should produce a valid solution."""
        from orchestrator.perturbation_eqns import solve_zerilli

        result = solve_zerilli(M=1.0, l=2, omega=0.37 - 0.09j)
        assert result["success"]
        assert len(result["psi"]) > 0

    def test_gw_strain(self):
        """GW strain should oscillate and decay."""
        from orchestrator.perturbation_eqns import compute_gw_strain

        result = compute_gw_strain(M=1.0, l=2, m=2, omega=0.37 - 0.09j, t_max=100)
        assert len(result["h_plus"]) > 0
        # Should decay
        assert abs(result["h_plus"][0]) > abs(result["h_plus"][-1])

    def test_waveform_from_ringdown(self):
        """Ringdown waveform should be well-formed."""
        from orchestrator.perturbation_eqns import compute_waveform_from_ringdown

        result = compute_waveform_from_ringdown(M=1.0, a=0.0, l=2, m=2, t_max=50)
        assert len(result["t"]) > 0
        assert len(result["h_plus"]) > 0


# ─── Post-Newtonian ────────────────────────────────────────────────

class TestPostNewtonian:
    def test_newtonian_energy(self):
        """Newtonian energy should be negative for bound orbits."""
        from orchestrator.post_newtonian import newtonian_orbital_energy

        E = newtonian_orbital_energy(M=1.989e30, m=5.972e24, a=1.496e11)
        assert E < 0

    def test_kepler_frequency(self):
        """Kepler frequency for Earth orbit should be ~1/year."""
        from orchestrator.post_newtonian import newtonian_orbital_frequency

        f = newtonian_orbital_frequency(M=1.989e30, a=1.496e11)
        # ~3.17e-8 Hz = 1/year
        assert f == pytest.approx(3.17e-8, rel=0.01)

    def test_perihelion_advance_mercury(self):
        """Mercury perihelion advance should be ~43 arcsec/century."""
        from orchestrator.post_newtonian import perihelion_advance

        result = perihelion_advance(M=1.989e30, a=5.79e10, e=0.2056)
        # Known value: ~42.98 arcsec/century
        assert result["advance_per_century_arcsec"] == pytest.approx(43.0, rel=0.05)

    def test_1pn_energy_correction(self):
        """1PN correction should be small for weak fields."""
        from orchestrator.post_newtonian import pn_energy_1pn

        result = pn_energy_1pn(M=1.989e30, m=5.972e24, a=1.496e11)
        # Correction should be very close to 1 for Earth orbit
        assert abs(result["correction"] - 1.0) < 1e-6

    def test_pn_metric_weak_field(self):
        """PN metric should reduce to Schwarzschild in weak field."""
        from orchestrator.post_newtonian import pn_metric_components

        result = pn_metric_components(r=1e10, M=1.989e30, order=1)
        # g_tt should be close to -1
        assert abs(result["g_tt"] + 1.0) < 1e-3

    def test_gw_flux_positive(self):
        """GW flux should be positive."""
        from orchestrator.post_newtonian import gravitational_wave_flux_quadrupole

        result = gravitational_wave_flux_quadrupole(M=1.989e30, m=5.972e24, a=1.496e11)
        assert result["flux"] > 0
        assert result["inspiral_time"] > 0

    def test_deceleration_parameter(self):
        """Deceleration parameter should be negative (accelerating universe)."""
        from orchestrator.post_newtonian import pn_binding_energy_2pn

        result = pn_binding_energy_2pn(M=1.989e30, m=5.972e24, v=3e4 / 3e8)
        assert result["E_newtonian"] < 0


# ─── Cosmology ─────────────────────────────────────────────────────

class TestCosmology:
    def test_hubble_parameter_today(self):
        """H(a=1) should equal H₀."""
        from orchestrator.cosmology import hubble_parameter

        H = hubble_parameter(1.0)
        assert H == pytest.approx(67.4, rel=1e-3)

    def test_hubble_parameter_scaling(self):
        """H(a) should increase for smaller a (matter domination)."""
        from orchestrator.cosmology import hubble_parameter

        H_today = hubble_parameter(1.0)
        H_early = hubble_parameter(0.1)
        assert H_early > H_today

    def test_friedmann_solver(self):
        """Friedmann solver should produce increasing scale factor."""
        from orchestrator.cosmology import solve_friedmann

        result = solve_friedmann(a_start=0.01, a_end=1.0, n_points=50)
        assert len(result["a"]) > 0
        assert result["a"][-1] >= result["a"][0]
        assert np.all(result["H_km_s_Mpc"] > 0)

    def test_age_of_universe(self):
        """Age should be ~13.8 Gyr for Planck parameters."""
        from orchestrator.cosmology import age_of_universe

        result = age_of_universe()
        assert result["age_gyr"] == pytest.approx(13.8, rel=0.05)

    def test_cosmological_distances(self):
        """Luminosity distance should increase with redshift."""
        from orchestrator.cosmology import cosmological_distances

        d1 = cosmological_distances(z=0.5)
        d2 = cosmological_distances(z=1.0)
        assert d2["luminosity_distance_Mpc"] > d1["luminosity_distance_Mpc"]

    def test_deceleration_parameter(self):
        """q₀ should be negative (accelerating universe)."""
        from orchestrator.cosmology import deceleration_parameter

        q0 = deceleration_parameter()
        assert q0 < 0  # Dark energy dominated

    def test_density_matter_scaling(self):
        """Matter density should scale as a⁻³."""
        from orchestrator.cosmology import density_parameter

        rho1 = density_parameter(1.0, "matter")
        rho2 = density_parameter(0.5, "matter")
        assert rho2 == pytest.approx(rho1 * 8, rel=1e-10)  # (1/0.5)³ = 8

    def test_density_radiation_scaling(self):
        """Radiation density should scale as a⁻⁴."""
        from orchestrator.cosmology import density_parameter

        rho1 = density_parameter(1.0, "radiation")
        rho2 = density_parameter(0.5, "radiation")
        assert rho2 == pytest.approx(rho1 * 16, rel=1e-10)  # (1/0.5)⁴ = 16

    def test_flrw_metric_symbolic(self):
        """FLRW metric should be constructible symbolically."""
        from orchestrator.cosmology import flrw_metric_symbolic

        result = flrw_metric_symbolic(k=0)
        assert result["metric"].dimension() == 4
        assert result["k"] == 0

    def test_dark_energy_constant(self):
        """Dark energy density should be constant (w=-1)."""
        from orchestrator.cosmology import density_parameter

        rho1 = density_parameter(1.0, "dark_energy")
        rho2 = density_parameter(0.5, "dark_energy")
        assert rho1 == pytest.approx(rho2)
