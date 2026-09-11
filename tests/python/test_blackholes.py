"""Tests for black holes, Kretschmann, ADM, and causal structure."""

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


# ─── Kretschmann Scalar ────────────────────────────────────────────

class TestKretschmann:
    def test_flat_spacetime_zero(self):
        """Minkowski: K = 0."""
        m = geom.Manifold("minkowski", ["t", "x", "y", "z"])
        g = geom.Metric.from_diagonal(m, ["-1", "1", "1", "1"])
        K = g.kretschmann_scalar()
        assert K.is_zero()

    def test_schwarzschild_kretschmann(self):
        """Schwarzschild: K = 48M²/r⁶."""
        m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
        g = geom.Metric.from_diagonal(m, [
            "-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2",
        ])
        K = g.kretschmann_scalar()
        # At r=6, M=1: K = 48/6^6 = 48/46656 ≈ 0.001029
        val = K.evaluate({"M": 1, "r": 6, "theta": np.pi / 2, "t": 0, "phi": 0})
        expected = 48 * 1**2 / 6**6
        assert val == pytest.approx(expected, rel=1e-6)

    def test_kretschmann_diverges_at_singularity(self):
        """Schwarzschild K diverges as r → 0."""
        m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
        g = geom.Metric.from_diagonal(m, [
            "-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2",
        ])
        K = g.kretschmann_scalar()
        val_small = K.evaluate({"M": 1, "r": 0.1, "theta": np.pi / 2, "t": 0, "phi": 0})
        val_large = K.evaluate({"M": 1, "r": 10, "theta": np.pi / 2, "t": 0, "phi": 0})
        assert val_small > val_large


# ─── Black Hole Solutions ──────────────────────────────────────────

class TestBlackHoles:
    def test_schwarzschild_creation(self):
        from orchestrator.blackholes import create_schwarzschild
        bh = create_schwarzschild(M=1.0)
        assert bh["name"] == "Schwarzschild"
        assert bh["horizons"]["event_horizon"]["r"] == 2.0
        assert bh["metric"].dimension() == 4

    def test_kerr_creation(self):
        from orchestrator.blackholes import create_kerr
        bh = create_kerr(M=1.0, a=0.5)
        assert bh["name"] == "Kerr"
        assert bh["horizons"]["outer_event_horizon"]["r"] is not None
        assert bh["metric"].dimension() == 4

    def test_reissner_nordstrom_creation(self):
        from orchestrator.blackholes import create_reissner_nordstrom
        bh = create_reissner_nordstrom(M=1.0, Q=0.5)
        assert bh["name"] == "Reissner-Nordstrom"
        assert bh["horizons"]["outer_horizon"]["r"] is not None

    def test_desitter_creation(self):
        from orchestrator.blackholes import create_desitter
        bh = create_desitter(L=1.0)
        assert bh["name"] == "de Sitter"
        assert bh["horizons"]["cosmological_horizon"]["r"] is not None

    def test_schwarzschild_kretschmann_numerical(self):
        from orchestrator.blackholes import create_schwarzschild, compute_kretschmann_numerical
        bh = create_schwarzschild(M=1.0)
        K = compute_kretschmann_numerical(bh, r_val=6.0)
        expected = 48 / 6**6
        assert K == pytest.approx(expected, rel=1e-6)

    def test_horizon_analysis(self):
        from orchestrator.blackholes import create_schwarzschild, analyze_horizon
        bh = create_schwarzschild(M=1.0)
        result = analyze_horizon(bh)
        # Should find horizon near r=2
        assert len(result["horizon_radii"]) >= 1
        assert any(abs(r - 2.0) < 0.5 for r in result["horizon_radii"])


# ─── ADM Decomposition ─────────────────────────────────────────────

class TestADM:
    def test_static_lapse(self):
        """Schwarzschild lapse N = √(1 - 2M/r)."""
        from orchestrator.adm import extract_adm_static

        m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
        g = geom.Metric.from_diagonal(m, [
            "-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2",
        ])

        adm = extract_adm_static(g, ["t", "r", "theta", "phi"])
        lapse_val = adm["lapse"].evaluate({"M": 1, "r": 10, "theta": np.pi / 2})
        expected = np.sqrt(1 - 2 / 10)
        assert lapse_val == pytest.approx(expected, rel=1e-10)

    def test_static_shift_zero(self):
        from orchestrator.adm import extract_adm_static

        m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
        g = geom.Metric.from_diagonal(m, [
            "-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2",
        ])

        adm = extract_adm_static(g, ["t", "r", "theta", "phi"])
        for s in adm["shift"]:
            assert s.is_zero()

    def test_hamiltonian_constraint_flat(self):
        """Minkowski: spatial Ricci scalar R^(3) = 0."""
        from orchestrator.adm import hamiltonian_constraint_numerical

        m = geom.Manifold("minkowski", ["t", "x", "y", "z"])
        g = geom.Metric.from_diagonal(m, ["-1", "1", "1", "1"])

        result = hamiltonian_constraint_numerical(g, ["t", "x", "y", "z"],
                                                   np.array([0, 1, 2, 3]))
        assert result["hamiltonian_satisfied"]

    def test_extrinsic_curvature_static(self):
        from orchestrator.adm import extrinsic_curvature_static
        result = extrinsic_curvature_static()
        assert result["K"] == 0


# ─── Causal Structure ──────────────────────────────────────────────

class TestCausalStructure:
    def test_light_cone_outside_horizon(self):
        """Outside Schwarzschild horizon: light cone exists."""
        from orchestrator.causal import light_cone_at_point
        from orchestrator.blackholes import create_schwarzschild

        bh = create_schwarzschild(M=1.0)
        result = light_cone_at_point(bh["metric"], bh["coord_names"],
                                      [0, 10, np.pi / 2, 0], bh["params"])
        assert not result["inside_horizon"]
        assert result["light_cone_slope"] > 0

    def test_light_cone_inside_horizon(self):
        """Inside Schwarzschild horizon: g_tt > 0 (r < 2M)."""
        from orchestrator.causal import light_cone_at_point
        from orchestrator.blackholes import create_schwarzschild

        bh = create_schwarzschild(M=1.0)
        result = light_cone_at_point(bh["metric"], bh["coord_names"],
                                      [0, 1.0, np.pi / 2, 0], bh["params"])
        assert result["inside_horizon"]

    def test_timelike_vector_classification(self):
        from orchestrator.causal import causal_classification
        from orchestrator.blackholes import create_schwarzschild

        bh = create_schwarzschild(M=1.0)
        # dt direction at r=10: timelike
        result = causal_classification(bh["metric"], bh["coord_names"],
                                        [1, 0, 0, 0], bh["params"])
        assert result["classification"] == "timelike"

    def test_spacelike_vector_classification(self):
        from orchestrator.causal import causal_classification
        from orchestrator.blackholes import create_schwarzschild

        bh = create_schwarzschild(M=1.0)
        # dr direction at r=10: spacelike
        result = causal_classification(bh["metric"], bh["coord_names"],
                                        [0, 1, 0, 0], bh["params"])
        assert result["classification"] == "spacelike"

    def test_horizon_causal_transition(self):
        from orchestrator.causal import horizon_causal_transition
        from orchestrator.blackholes import create_schwarzschild

        bh = create_schwarzschild(M=1.0)
        result = horizon_causal_transition(bh["metric"], bh["coord_names"],
                                            bh["params"])
        assert len(result["horizons"]) >= 1
        # Horizon should be near r=2M=2
        assert any(abs(h["r"] - 2.0) < 0.2 for h in result["horizons"])

    def test_singularity_analysis(self):
        from orchestrator.causal import singularity_analysis
        from orchestrator.blackholes import create_schwarzschild

        bh = create_schwarzschild(M=1.0)
        result = singularity_analysis(bh["metric"], bh["coord_names"], bh["params"])
        # K diverges at r=0
        assert len(result["singularities"]) >= 1
