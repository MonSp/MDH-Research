"""Numerical verification benchmarks (T13).

Tests:
1. Expression evaluate() correctness
2. Numerical Christoffel symbols at known points
3. Geodesic solver: flat spacetime straight lines
4. Geodesic solver: Schwarzschild circular orbit
5. Geodesic solver: energy conservation check
"""

import sys
import os
import numpy as np
import pytest

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

rc = pytest.importorskip("_research_core")
sym = rc.symbol
geom = rc.geometry

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
from orchestrator.geodesic import (
    christoffel_numerical_evaluator,
    christoffel_at_point,
    solve_geodesic,
)


# ─── Expression evaluate ────────────────────────────────────────────

class TestEvaluate:
    def test_number(self):
        assert sym.number(42).evaluate({}) == 42.0

    def test_symbol(self):
        x = sym.symbol("x")
        assert x.evaluate({"x": 3.0}) == 3.0

    def test_symbol_undefined(self):
        x = sym.symbol("x")
        assert x.evaluate({}) == 0.0

    def test_add(self):
        expr = sym.parse("x + y")
        assert expr.evaluate({"x": 2, "y": 3}) == 5.0

    def test_mul(self):
        expr = sym.parse("x * y")
        assert expr.evaluate({"x": 2, "y": 3}) == 6.0

    def test_pow(self):
        expr = sym.parse("x^2")
        assert expr.evaluate({"x": 3}) == 9.0

    def test_div(self):
        expr = sym.parse("x / y")
        assert expr.evaluate({"x": 6, "y": 3}) == pytest.approx(2.0)

    def test_neg(self):
        expr = sym.parse("-x")
        assert expr.evaluate({"x": 5}) == -5.0

    def test_sin(self):
        expr = sym.parse("sin(x)")
        assert expr.evaluate({"x": 0}) == pytest.approx(0.0)
        assert expr.evaluate({"x": 3.14159265358979 / 2}) == pytest.approx(1.0)

    def test_cos(self):
        expr = sym.parse("cos(x)")
        assert expr.evaluate({"x": 0}) == pytest.approx(1.0)

    def test_complex_expression(self):
        expr = sym.parse("1 - 2*M/r")
        val = expr.evaluate({"M": 1, "r": 6})
        assert val == pytest.approx(1 - 2 / 6)

    def test_schwarzschild_g_tt(self):
        expr = sym.parse("-(1 - 2*M/r)")
        val = expr.evaluate({"M": 1, "r": 10})
        assert val == pytest.approx(-(1 - 0.2))


# ─── Numerical Christoffel ──────────────────────────────────────────

class TestNumericalChristoffel:
    def test_flat_metric_christoffel_all_zero(self):
        """Minkowski metric: all Christoffel symbols should be zero."""
        m = geom.Manifold("minkowski", ["t", "x", "y", "z"])
        g = geom.Metric.from_diagonal(m, ["-1", "1", "1", "1"])
        coords = np.array([0.0, 1.0, 2.0, 3.0])
        Gamma = christoffel_at_point(g, ["t", "x", "y", "z"], coords)
        assert np.allclose(Gamma, 0, atol=1e-15)

    def test_schwarzschild_christoffel_values(self):
        """Schwarzschild Christoffel symbols at r=6, M=1, theta=pi/2."""
        m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
        g = geom.Metric.from_diagonal(m, [
            "-(1 - 2*M/r)",
            "(1 - 2*M/r)^(-1)",
            "r^2",
            "r^2 * sin(theta)^2",
        ])

        M_val = 1.0
        r_val = 6.0
        theta_val = np.pi / 2
        coords = np.array([0.0, r_val, theta_val, 0.0])

        Gamma = christoffel_at_point(g, ["t", "r", "theta", "phi"], coords, params={"M": M_val})

        # Analytical values for Schwarzschild at these coordinates
        f = 1 - 2 * M_val / r_val  # = 2/3

        # Γ^t_{tr} = M / (r^2 * f) = 1 / (36 * 2/3) = 1/24
        expected_Gt_tr = M_val / (r_val**2 * f)
        assert Gamma[0, 0, 1] == pytest.approx(expected_Gt_tr, rel=1e-10)

        # Γ^r_{tt} = M * f / r^2 = 1 * (2/3) / 36 = 2/108 = 1/54
        expected_Gr_tt = M_val * f / r_val**2
        assert Gamma[1, 0, 0] == pytest.approx(expected_Gr_tt, rel=1e-10)

        # Γ^r_{rr} = -M / (r^2 * f) = -1/24
        expected_Gr_rr = -M_val / (r_val**2 * f)
        assert Gamma[1, 1, 1] == pytest.approx(expected_Gr_rr, rel=1e-10)

        # Γ^r_{θθ} = -r * f = -6 * 2/3 = -4
        expected_Gr_tt2 = -r_val * f
        assert Gamma[1, 2, 2] == pytest.approx(expected_Gr_tt2, rel=1e-10)

        # Γ^θ_{rθ} = 1/r = 1/6
        assert Gamma[2, 1, 2] == pytest.approx(1.0 / r_val, rel=1e-10)


# ─── Geodesic solver ────────────────────────────────────────────────

class TestGeodesicFlatSpacetime:
    """In flat spacetime, geodesics are straight lines."""

    def test_straight_line_x(self):
        """Particle moving in +x direction should travel in a straight line."""
        m = geom.Manifold("minkowski", ["t", "x", "y", "z"])
        g = geom.Metric.from_diagonal(m, ["-1", "1", "1", "1"])

        x0 = np.array([0.0, 0.0, 0.0, 0.0])
        u0 = np.array([1.0, 0.5, 0.0, 0.0])  # moving in +x

        taus, states = solve_geodesic(
            g, ["t", "x", "y", "z"], x0, u0, tau_max=10.0, dtau=0.01
        )

        # Position should be x = 0.5 * tau (linear)
        final_x = states[-1, 1]
        expected_x = 0.5 * taus[-1]
        assert final_x == pytest.approx(expected_x, rel=1e-6)

        # y and z should remain zero
        assert np.allclose(states[:, 2], 0, atol=1e-10)
        assert np.allclose(states[:, 3], 0, atol=1e-10)

    def test_straight_line_diagonal(self):
        """Particle moving diagonally should maintain constant velocity."""
        m = geom.Manifold("minkowski", ["t", "x", "y", "z"])
        g = geom.Metric.from_diagonal(m, ["-1", "1", "1", "1"])

        x0 = np.array([0.0, 0.0, 0.0, 0.0])
        u0 = np.array([1.0, 0.3, 0.4, 0.0])

        taus, states = solve_geodesic(
            g, ["t", "x", "y", "z"], x0, u0, tau_max=5.0, dtau=0.01
        )

        # Velocities should remain constant
        u_final = states[-1, 4:]
        np.testing.assert_allclose(u_final, u0, atol=1e-8)


class TestGeodesicSchwarzschild:
    """Test geodesics in Schwarzschild spacetime."""

    def test_circular_orbit(self):
        """Test circular orbit at r=6M (ISCO for timelike geodesics).

        For a circular orbit at radius r in Schwarzschild:
        - dphi/dtau = sqrt(M / (r^2 * (r - 3M)))  (for r > 3M)
        - dt/dtau = 1 / sqrt(1 - 3M/r)
        """
        m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
        g = geom.Metric.from_diagonal(m, [
            "-(1 - 2*M/r)",
            "(1 - 2*M/r)^(-1)",
            "r^2",
            "r^2 * sin(theta)^2",
        ])

        M = 1.0
        r0 = 6.0  # ISCO
        theta0 = np.pi / 2

        # Circular orbit initial conditions
        # dphi/dtau = sqrt(M / (r^2 * (r - 3M)))
        dphi_dtau = np.sqrt(M / (r0**2 * (r0 - 3 * M)))
        # dt/dtau = 1 / sqrt(1 - 3M/r)
        dt_dtau = 1.0 / np.sqrt(1 - 3 * M / r0)

        x0 = np.array([0.0, r0, theta0, 0.0])
        u0 = np.array([dt_dtau, 0.0, 0.0, dphi_dtau])

        taus, states = solve_geodesic(
            g, ["t", "r", "theta", "phi"], x0, u0, tau_max=50.0, dtau=0.005,
            params={"M": M}
        )

        # r should stay approximately constant at r0
        r_values = states[:, 1]
        r_deviation = np.max(np.abs(r_values - r0))
        assert r_deviation < 0.1, f"r deviated by {r_deviation} from {r0}"

        # theta should stay approximately pi/2
        theta_values = states[:, 2]
        theta_deviation = np.max(np.abs(theta_values - theta0))
        assert theta_deviation < 0.05, f"theta deviated by {theta_deviation}"

    def test_energy_conservation(self):
        """Test that the metric norm g_mu_nu u^mu u^nu is conserved along geodesic."""
        m = geom.Manifold("minkowski", ["t", "x", "y", "z"])
        g = geom.Metric.from_diagonal(m, ["-1", "1", "1", "1"])

        x0 = np.array([0.0, 0.0, 0.0, 0.0])
        u0 = np.array([1.0, 0.5, 0.3, 0.1])

        # Initial norm: -1^2 + 0.5^2 + 0.3^2 + 0.1^2 = -1 + 0.25 + 0.09 + 0.01 = -0.65
        initial_norm = -u0[0]**2 + u0[1]**2 + u0[2]**2 + u0[3]**2

        taus, states = solve_geodesic(
            g, ["t", "x", "y", "z"], x0, u0, tau_max=10.0, dtau=0.01
        )

        # Check norm conservation at each step
        norms = []
        for i in range(len(states)):
            u = states[i, 4:]
            norm = -u[0]**2 + u[1]**2 + u[2]**2 + u[3]**2
            norms.append(norm)

        norms = np.array(norms)
        norm_deviation = np.max(np.abs(norms - initial_norm))
        assert norm_deviation < 1e-6, f"Norm deviated by {norm_deviation}"
