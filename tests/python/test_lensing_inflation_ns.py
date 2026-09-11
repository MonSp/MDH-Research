"""Tests for gravitational lensing, inflation, and neutron stars."""

import sys
import os
import numpy as np
import pytest

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

rc = pytest.importorskip("_research_core")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


# ─── Gravitational Lensing ─────────────────────────────────────────

class TestLensing:
    def test_deflection_angle(self):
        """Deflection by Sun should be ~1.75 arcsec."""
        from orchestrator.lensing import deflection_angle

        M_sun_kg = 1.989e30
        R_sun = 6.957e8
        alpha = deflection_angle(M_sun_kg, R_sun)
        alpha_arcsec = np.degrees(alpha) * 3600
        assert alpha_arcsec == pytest.approx(1.75, rel=0.01)

    def test_einstein_radius(self):
        """Einstein radius should be positive."""
        from orchestrator.lensing import einstein_radius

        M = 1e12 * 1.989e30  # galaxy mass
        D_L = 1e25  # ~1 Gpc
        D_S = 2e25
        D_LS = 1e25
        result = einstein_radius(M, D_L, D_S, D_LS)
        assert result["theta_E_arcsec"] > 0

    def test_image_positions(self):
        """Should produce two images for a point source."""
        from orchestrator.lensing import image_positions

        theta_E = 1e-5  # radians
        beta = 0.5 * theta_E
        result = image_positions(beta, theta_E)
        assert result["n_images"] == 2
        assert result["mu_total"] > 1

    def test_magnification_diverges(self):
        """Magnification should diverge at Einstein radius."""
        from orchestrator.lensing import magnification

        theta_E = 1e-5
        mu = magnification(theta_E, theta_E)
        assert abs(mu) > 1e10  # should be very large

    def test_point_source_magnification(self):
        """Point source magnification at u=0 should diverge."""
        from orchestrator.lensing import point_source_magnification

        assert point_source_magnification(0) == float('inf')
        assert point_source_magnification(1) > 1

    def test_einstein_radius_solar_mass(self):
        """Solar mass lens should give small Einstein radius."""
        from orchestrator.lensing import einstein_radius_solar_mass

        result = einstein_radius_solar_mass(1.0, z_L=0.5, z_S=2.0)
        assert result["theta_E_arcsec"] > 0
        assert result["theta_E_arcsec"] < 1  # should be milli-arcsec scale

    def test_microlensing_light_curve(self):
        """Microlensing light curve should peak at closest approach."""
        from orchestrator.lensing import microlensing_light_curve

        t = np.linspace(-50, 50, 200)
        result = microlensing_light_curve(t, t_0=0, u_0=0.1, t_E=10)
        assert result["peak_magnification"] > 1
        # Peak should be near t_0
        peak_idx = np.argmax(result["magnification"])
        assert abs(t[peak_idx]) < 2  # within 2 days of t_0

    def test_einstein_ring_image(self):
        """Einstein ring should have finite radius."""
        from orchestrator.lensing import einstein_ring_image

        result = einstein_ring_image(M_solar=1e11, z_L=0.5, z_S=2.0)
        assert result["einstein_radius_arcsec"] > 0
        assert result["ring_type"] == "Einstein ring"


# ─── Cosmological Inflation ────────────────────────────────────────

class TestInflation:
    def test_slow_roll_chaotic(self):
        """Chaotic inflation: V = ½m²φ² should have small ε for large φ."""
        from orchestrator.inflation import chaotic_potential, slow_roll_parameters

        V = chaotic_potential(m=1e-5)
        phi = 15  # in Planck units
        result = slow_roll_parameters(V, phi)
        assert result["epsilon"] > 0
        assert result["epsilon"] < 1  # slow-roll valid at large φ

    def test_number_of_efolds(self):
        """Chaotic inflation should produce e-folds."""
        from orchestrator.inflation import chaotic_potential, number_of_efolds

        V = chaotic_potential(m=1e-5)
        result = number_of_efolds(V, phi_start=15, phi_end=1)
        assert result["N"] > 0

    def test_scalar_spectral_index(self):
        """n_s should be close to 1 for slow-roll inflation."""
        from orchestrator.inflation import scalar_spectral_index

        n_s = scalar_spectral_index(eps=0.01, eta=-0.02)
        assert 0.85 < n_s < 1.0

    def test_tensor_to_scalar_ratio(self):
        """r = 16ε."""
        from orchestrator.inflation import tensor_to_scalar_ratio

        r = tensor_to_scalar_ratio(eps=0.01)
        assert r == pytest.approx(0.16, rel=1e-10)

    def test_primordial_scalar_spectrum(self):
        """Scalar power spectrum should be nearly scale-invariant."""
        from orchestrator.inflation import primordial_scalar_power_spectrum

        k = np.geomspace(1e-4, 1, 100)
        result = primordial_scalar_power_spectrum(k, n_s=0.965)
        assert np.all(result["P_s"] > 0)
        # Should be nearly scale-invariant (small k-dependence)
        ratio = result["P_s"][-1] / result["P_s"][0]
        assert ratio < 2  # not too steep

    def test_primordial_tensor_spectrum(self):
        """Tensor power spectrum should be smaller than scalar."""
        from orchestrator.inflation import primordial_scalar_power_spectrum, primordial_tensor_power_spectrum

        k = np.geomspace(1e-4, 1, 100)
        scalar = primordial_scalar_power_spectrum(k)
        tensor = primordial_tensor_power_spectrum(k, r=0.03)
        # Tensor should be smaller
        assert np.all(tensor["P_t"] < scalar["P_s"])

    def test_inflationary_observables(self):
        """Chaotic inflation observables should be computable."""
        from orchestrator.inflation import chaotic_potential, inflationary_observables

        V = chaotic_potential(m=1e-5)
        result = inflationary_observables(V, phi_start=15)
        assert "n_s" in result
        assert "r" in result
        assert "epsilon" in result

    def test_consistency_relation(self):
        """n_t should satisfy consistency relation n_t = -r/8."""
        from orchestrator.inflation import primordial_tensor_power_spectrum

        k = np.array([0.05])
        result = primordial_tensor_power_spectrum(k, r=0.1)
        assert result["n_t"] == pytest.approx(-0.1 / 8, rel=1e-10)

    def test_spectral_index_running(self):
        """Running should be computable."""
        from orchestrator.inflation import spectral_index_running

        alpha = spectral_index_running(eps=0.01, eta=-0.02)
        assert isinstance(alpha, float)


# ─── Neutron Stars ─────────────────────────────────────────────────

class TestNeutronStars:
    def test_polytropic_eos(self):
        """Polytropic EOS should produce positive pressure."""
        from orchestrator.neutron_star import polytropic_eos

        eos = polytropic_eos(K=1e5, Gamma=2.0)
        assert eos["pressure"](1e15) > 0
        assert eos["density"](eos["pressure"](1e15)) == pytest.approx(1e15, rel=1e-6)

    def test_sly4_eos(self):
        """SLy4 EOS should produce reasonable pressures."""
        from orchestrator.neutron_star import sly4_eos

        eos = sly4_eos()
        rho = 1e15 * 1e3  # 10^15 g/cm³ in kg/m³
        P = eos["pressure"](rho)
        assert P > 0

    def test_tov_solver(self):
        """TOV solver should produce a valid neutron star model."""
        from orchestrator.neutron_star import solve_tov, polytropic_eos

        eos = polytropic_eos(K=1e5, Gamma=2.0)
        rho_c = 5e17  # kg/m³
        result = solve_tov(rho_c, eos)
        assert result["M_total_solar"] > 0
        assert result["R_km"] > 0
        assert result["compactness"] > 0

    def test_tov_mass_range(self):
        """Neutron star mass should be positive."""
        from orchestrator.neutron_star import solve_tov, polytropic_eos

        eos = polytropic_eos(K=1e-2, Gamma=2.0)
        result = solve_tov(5e17, eos)
        assert result["M_total_solar"] > 0.01

    def test_tov_radius_range(self):
        """Neutron star radius should be positive."""
        from orchestrator.neutron_star import solve_tov, polytropic_eos

        eos = polytropic_eos(K=1e-2, Gamma=2.0)
        result = solve_tov(5e17, eos)
        assert result["R_km"] > 1.0

    def test_mass_radius_relation(self):
        """Mass-radius relation should show maximum mass."""
        from orchestrator.neutron_star import mass_radius_relation, polytropic_eos

        eos = polytropic_eos(K=1e-2, Gamma=2.0)
        result = mass_radius_relation(eos, n_points=10)
        assert result["max_mass_solar"] > 0.01
        assert result["max_mass_radius_km"] > 1.0

    def test_compactness(self):
        """Compactness should be less than 0.5 (not a black hole)."""
        from orchestrator.neutron_star import solve_tov, polytropic_eos

        eos = polytropic_eos(K=1e5, Gamma=2.0)
        result = solve_tov(5e17, eos)
        assert result["compactness"] < 0.5

    def test_tidal_deformability(self):
        """Tidal deformability should be positive."""
        from orchestrator.neutron_star import tidal_deformability

        result = tidal_deformability(M_solar=1.4, R_km=12, k2=0.1)
        assert result["Lambda"] > 0

    def test_surface_redshift(self):
        """Surface redshift should be positive for neutron stars."""
        from orchestrator.neutron_star import solve_tov, polytropic_eos

        eos = polytropic_eos(K=1e5, Gamma=2.0)
        result = solve_tov(5e17, eos)
        assert result["surface_redshift"] > 0
