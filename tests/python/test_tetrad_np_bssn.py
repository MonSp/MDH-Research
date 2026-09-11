"""Tests for tetrads, Newman-Penrose, BSSN, and quasi-normal modes."""

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


# ─── Tetrads ───────────────────────────────────────────────────────

class TestTetrad:
    def test_flat_tetrad(self):
        """Minkowski tetrad should be identity-like."""
        from orchestrator.tetrad import build_tetrad_diagonal

        m = geom.Manifold("minkowski", ["t", "x", "y", "z"])
        g = geom.Metric.from_diagonal(m, ["-1", "1", "1", "1"])
        tet = build_tetrad_diagonal(g, ["t", "x", "y", "z"])

        for i in range(4):
            val = tet["tetrad"][i].evaluate({})
            assert abs(val - 1.0) < 1e-10

    def test_schwarzschild_tetrad(self):
        """Schwarzschild tetrad components should match √|g_μμ|."""
        from orchestrator.tetrad import build_tetrad_diagonal

        m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
        g = geom.Metric.from_diagonal(m, [
            "-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2",
        ])
        tet = build_tetrad_diagonal(g, ["t", "r", "theta", "phi"])

        v = {"M": 1, "r": 6, "theta": np.pi / 2, "t": 0, "phi": 0}
        e0 = tet["tetrad"][0].evaluate(v)
        e1 = tet["tetrad"][1].evaluate(v)
        # e0 = √(1 - 2/6) = √(2/3)
        assert e0 == pytest.approx(np.sqrt(1 - 2 / 6), rel=1e-10)
        # e1 = √(1/(1 - 2/6)) = √(3/2)
        assert e1 == pytest.approx(np.sqrt(1 / (1 - 2 / 6)), rel=1e-10)

    def test_tetrad_reconstructs_metric(self):
        """g_μμ = η_aa (e^a_μ)² should recover the metric."""
        from orchestrator.tetrad import build_tetrad_diagonal

        m = geom.Manifold("minkowski", ["t", "x", "y", "z"])
        g = geom.Metric.from_diagonal(m, ["-1", "1", "1", "1"])
        tet = build_tetrad_diagonal(g, ["t", "x", "y", "z"])

        for i in range(4):
            e_val = tet["tetrad"][i].evaluate({})
            eta_val = -1 if i == 0 else 1
            g_reconstructed = eta_val * e_val ** 2
            g_original = g.g(i, i).evaluate({})
            assert abs(g_reconstructed - g_original) < 1e-10


# ─── Newman-Penrose ────────────────────────────────────────────────

class TestNewmanPenrose:
    def test_null_tetrad_construction(self):
        """Null tetrad should be constructible for Schwarzschild."""
        from orchestrator.newman_penrose import build_null_tetrad_diagonal

        m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
        g = geom.Metric.from_diagonal(m, [
            "-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2",
        ])
        tet = build_null_tetrad_diagonal(g, ["t", "r", "theta", "phi"], {"M": 1})

        assert "l" in tet
        assert "n" in tet
        assert "m_real" in tet
        assert "m_imag" in tet

    def test_schwarzschild_petrov_type_d(self):
        """Schwarzschild should be Petrov type D."""
        from orchestrator.newman_penrose import classify_petrov_type

        # For Schwarzschild (Type D), only Ψ₂ ≠ 0
        # At r=6M, Ψ₂ = -M/r³ = -1/216
        weyl_scalars = {"Psi_0": 0, "Psi_1": 0, "Psi_2": -1/216, "Psi_3": 0, "Psi_4": 0}
        classification = classify_petrov_type(weyl_scalars)
        assert classification["petrov_type"] == "D"

    def test_petrov_type_o_flat(self):
        """Minkowski should be Petrov type O (conformally flat)."""
        from orchestrator.newman_penrose import classify_petrov_type

        flat_scalars = {"Psi_0": 0, "Psi_1": 0, "Psi_2": 0, "Psi_3": 0, "Psi_4": 0}
        result = classify_petrov_type(flat_scalars)
        assert result["petrov_type"] == "O"


# ─── BSSN ──────────────────────────────────────────────────────────

class TestBSSN:
    def test_conformal_factor_flat(self):
        """Flat space: φ = ln(1) / 12 = 0."""
        from orchestrator.bssn import compute_conformal_factor

        # Flat 3-metric: γ_ij = δ_ij
        metric_3d = [[sym.number(1), sym.number(0), sym.number(0)],
                      [sym.number(0), sym.number(1), sym.number(0)],
                      [sym.number(0), sym.number(0), sym.number(1)]]

        result = compute_conformal_factor(metric_3d, ["x", "y", "z"])
        # det(γ) = 1, φ = ln(1)/12 = 0
        phi_val = result["phi"].evaluate({})
        assert abs(phi_val) < 1e-10

    def test_conformal_metric_flat(self):
        """Flat space: γ̃_ij = γ_ij (conformal factor is 1)."""
        from orchestrator.bssn import compute_conformal_metric

        metric_3d = [[sym.number(1), sym.number(0), sym.number(0)],
                      [sym.number(0), sym.number(1), sym.number(0)],
                      [sym.number(0), sym.number(0), sym.number(1)]]

        result = compute_conformal_metric(metric_3d, ["x", "y", "z"])
        for i in range(3):
            val = result["gamma_tilde"][i][i].evaluate({})
            assert abs(val - 1.0) < 1e-10

    def test_bssn_variables(self):
        """BSSN variables should be well-formed."""
        from orchestrator.bssn import bssn_variables

        metric_3d = [[sym.number(4), sym.number(0), sym.number(0)],
                      [sym.number(0), sym.number(4), sym.number(0)],
                      [sym.number(0), sym.number(0), sym.number(4)]]

        result = bssn_variables(metric_3d, ["x", "y", "z"])
        assert "phi" in result
        assert "gamma_tilde" in result
        assert "det_gamma" in result
        assert "Gamma_tilde" in result

    def test_hamiltonian_constraint(self):
        """Hamiltonian constraint should be computable."""
        from orchestrator.bssn import bssn_variables, hamiltonian_constraint_bssn

        metric_3d = [[sym.number(1), sym.number(0), sym.number(0)],
                      [sym.number(0), sym.number(1), sym.number(0)],
                      [sym.number(0), sym.number(0), sym.number(1)]]

        bssn = bssn_variables(metric_3d, ["x", "y", "z"])
        result = hamiltonian_constraint_bssn(bssn)
        assert "constraint" in result


# ─── Quasi-Normal Modes ────────────────────────────────────────────

class TestQuasinormalModes:
    def test_schwarzschild_qnm_l2n0(self):
        """Schwarzschild l=2, n=0 QNM should match known values."""
        from orchestrator.quasinormal import schwarzschild_qnm

        qnm = schwarzschild_qnm(l=2, n=0, M=1.0)
        # Known value: ω ≈ 0.3737 - 0.0890i
        assert qnm["omega_R"] == pytest.approx(0.37367, rel=1e-3)
        assert qnm["omega_I"] == pytest.approx(-0.08896, rel=1e-3)
        assert qnm["stability"] == "stable"

    def test_schwarzschild_qnm_scaling(self):
        """QNM frequencies should scale as 1/M."""
        from orchestrator.quasinormal import schwarzschild_qnm

        qnm1 = schwarzschild_qnm(l=2, n=0, M=1.0)
        qnm2 = schwarzschild_qnm(l=2, n=0, M=2.0)
        assert qnm1["omega_R"] == pytest.approx(2 * qnm2["omega_R"], rel=1e-3)

    def test_kerr_qnm_prograde_faster(self):
        """Prograde Kerr QNMs should have higher frequency than Schwarzschild."""
        from orchestrator.quasinormal import schwarzschild_qnm, kerr_qnm

        schw = schwarzschild_qnm(l=2, n=0, M=1.0)
        kerr = kerr_qnm(l=2, n=0, M=1.0, a=0.9, prograde=True)
        assert kerr["omega_R"] > schw["omega_R"]

    def test_kerr_qnm_retrograde_slower(self):
        """Retrograde Kerr QNMs should have lower frequency than Schwarzschild."""
        from orchestrator.quasinormal import schwarzschild_qnm, kerr_qnm

        schw = schwarzschild_qnm(l=2, n=0, M=1.0)
        kerr = kerr_qnm(l=2, n=0, M=1.0, a=0.9, prograde=False)
        assert kerr["omega_R"] < schw["omega_R"]

    def test_qnm_spectrum(self):
        """QNM spectrum should contain multiple modes."""
        from orchestrator.quasinormal import qnm_spectrum

        result = qnm_spectrum(M=1.0, l_max=3, n_max=1)
        assert result["n_modes"] >= 4  # l=2,3 × n=0,1

    def test_qnm_waveform(self):
        """QNM waveform should decay exponentially."""
        from orchestrator.quasinormal import schwarzschild_qnm, qnm_waveform

        qnm = schwarzschild_qnm(l=2, n=0, M=1.0)
        t = np.linspace(0, 100, 1000)
        h = qnm_waveform(t, qnm["omega"])

        # Should decay
        assert abs(h[0]) > abs(h[-1])
        # Should oscillate
        assert np.max(np.abs(np.diff(h))) > 0

    def test_ringdown_waveform(self):
        """Ringdown waveform should be well-formed."""
        from orchestrator.quasinormal import ringdown_waveform

        result = ringdown_waveform(M=1.0, a=0.0, l=2, m=2, t_max=50)
        assert len(result["t"]) > 0
        assert len(result["h"]) > 0
        assert result["qnm"]["stability"] == "stable"

    def test_quality_factor(self):
        """Quality factor should be positive and finite."""
        from orchestrator.quasinormal import schwarzschild_qnm

        qnm = schwarzschild_qnm(l=2, n=0, M=1.0)
        assert qnm["quality_factor"] > 0
        assert np.isfinite(qnm["quality_factor"])
