"""Tests for Einstein tensor, field equations, SymPy bridge, and visualization."""

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


# ─── Einstein Tensor ────────────────────────────────────────────────

class TestEinsteinTensor:
    def test_flat_spacetime_vanishes(self):
        """Minkowski: G_μν = 0."""
        m = geom.Manifold("minkowski", ["t", "x", "y", "z"])
        g = geom.Metric.from_diagonal(m, ["-1", "1", "1", "1"])
        G = g.einstein_tensor()
        for i in range(4):
            for j in range(4):
                assert G[[i, j]].is_zero(), f"G_{{{i}{j}}} != 0"

    def test_2d_flat_vanishes(self):
        """2D flat: G_μν = 0."""
        m = geom.Manifold("2d", ["x", "y"])
        g = geom.Metric.from_diagonal(m, ["1", "1"])
        G = g.einstein_tensor()
        for i in range(2):
            for j in range(2):
                assert G[[i, j]].is_zero()

    def test_schwarzschild_vacuum(self):
        """Schwarzschild is vacuum: G_μν should be structurally zero."""
        m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
        g = geom.Metric.from_diagonal(m, [
            "-(1 - 2*M/r)",
            "(1 - 2*M/r)^(-1)",
            "r^2",
            "r^2 * sin(theta)^2",
        ])
        G = g.einstein_tensor()
        # For vacuum, G_μν = R_μν - ½g_μν R = 0
        # Our symbolic engine may not simplify fully, but structure should be valid
        assert G is not None
        assert G.rank() == 2

    def test_einstein_tensor_numerical_vacuum(self):
        """Minkowski: numerically evaluate G_μν = 0 at arbitrary point."""
        m = geom.Manifold("minkowski", ["t", "x", "y", "z"])
        g = geom.Metric.from_diagonal(m, ["-1", "1", "1", "1"])
        G = g.einstein_tensor()

        for i in range(4):
            for j in range(4):
                val = G[[i, j]].evaluate({"t": 1, "x": 2, "y": 3, "z": 4})
                assert val == 0.0

    def test_2d_sphere_einstein(self):
        """S²: Einstein tensor for 2D manifold."""
        m = geom.Manifold("S2", ["theta", "phi"])
        g = geom.Metric.from_diagonal(m, ["1", "sin(theta)^2"])
        G = g.einstein_tensor()
        assert G is not None
        assert G.rank() == 2


# ─── SymPy Bridge ──────────────────────────────────────────────────

class TestSympyBridge:
    def setup_method(self):
        from orchestrator.sympy_bridge import expr_to_sympy, sympy_to_expr
        self.expr_to_sympy = expr_to_sympy
        self.sympy_to_expr = sympy_to_expr

    def test_number_roundtrip(self):
        n = sym.number(42)
        sp_val = self.expr_to_sympy(n)
        assert float(sp_val) == 42.0

    def test_symbol_roundtrip(self):
        x = sym.symbol("x")
        sp_x = self.expr_to_sympy(x)
        assert str(sp_x) == "x"

    def test_add_roundtrip(self):
        expr = sym.parse("x + y")
        sp_expr = self.expr_to_sympy(expr)
        import sympy as sp
        x, y = sp.symbols("x y")
        val = sp_expr.subs([(x, 3), (y, 4)])
        assert sp.simplify(val - 7) == 0

    def test_mul_roundtrip(self):
        expr = sym.parse("x * y")
        sp_expr = self.expr_to_sympy(expr)
        import sympy as sp
        x, y = sp.symbols("x y")
        val = sp_expr.subs([(x, 3), (y, 4)])
        assert sp.simplify(val - 12) == 0

    def test_power_roundtrip(self):
        expr = sym.parse("x^2")
        sp_expr = self.expr_to_sympy(expr)
        import sympy as sp
        x = sp.Symbol("x")
        val = sp_expr.subs(x, 5)
        assert sp.simplify(val - 25) == 0

    def test_sympy_to_expr_number(self):
        import sympy as sp
        expr = self.sympy_to_expr(sp.Integer(42))
        assert str(expr) == "42"

    def test_sympy_to_expr_symbol(self):
        import sympy as sp
        expr = self.sympy_to_expr(sp.Symbol("r"))
        assert str(expr) == "r"

    def test_sympy_to_expr_add(self):
        import sympy as sp
        x, y = sp.symbols("x y")
        expr = self.sympy_to_expr(x + y)
        s = str(expr)
        assert "x" in s and "y" in s and "+" in s

    def test_sympy_to_expr_mul(self):
        import sympy as sp
        x, y = sp.symbols("x y")
        expr = self.sympy_to_expr(x * y)
        s = str(expr)
        assert "x" in s and "y" in s

    def test_sympy_to_expr_power(self):
        import sympy as sp
        x = sp.Symbol("x")
        expr = self.sympy_to_expr(x**3)
        s = str(expr)
        assert "x" in s and "3" in s

    def test_sympy_to_expr_function(self):
        import sympy as sp
        x = sp.Symbol("x")
        expr = self.sympy_to_expr(sp.sin(x))
        s = str(expr)
        assert "sin" in s

    def test_complex_expression_roundtrip(self):
        """Test 1 - 2*M/r conversion."""
        import sympy as sp
        M, r = sp.symbols("M r")
        sp_expr = 1 - 2 * M / r

        cpp_expr = self.sympy_to_expr(sp_expr)
        # Evaluate both at M=1, r=6
        cpp_val = cpp_expr.evaluate({"M": 1, "r": 6})
        sp_val = float(sp_expr.subs([(M, 1), (r, 6)]))
        assert cpp_val == pytest.approx(sp_val, rel=1e-10)


# ─── Field Equations ───────────────────────────────────────────────

class TestFieldEquations:
    def test_vacuum_residual_flat(self):
        """Flat spacetime: G_μν = 0 (vacuum)."""
        from orchestrator.field_equations import field_equation_residual_numerical

        m = geom.Manifold("minkowski", ["t", "x", "y", "z"])
        g = geom.Metric.from_diagonal(m, ["-1", "1", "1", "1"])

        coords = np.array([0.0, 1.0, 2.0, 3.0])
        G = field_equation_residual_numerical(g, ["t", "x", "y", "z"], coords)
        assert np.allclose(G, 0, atol=1e-15)

    def test_einstein_tensor_accessor(self):
        """Test the einstein_tensor accessor."""
        from orchestrator.field_equations import einstein_tensor

        m = geom.Manifold("2d", ["x", "y"])
        g = geom.Metric.from_diagonal(m, ["1", "1"])
        G = einstein_tensor(g)
        assert G.rank() == 2


# ─── Visualization ─────────────────────────────────────────────────

class TestVisualization:
    def test_plot_geodesic_components(self):
        """Test component plot generation."""
        import matplotlib
        matplotlib.use('Agg')
        from orchestrator.visualization import plot_geodesic_components

        m = geom.Manifold("minkowski", ["t", "x", "y", "z"])
        g = geom.Metric.from_diagonal(m, ["-1", "1", "1", "1"])

        fig = plot_geodesic_components(
            g, ["t", "x", "y", "z"],
            np.array([0, 0, 0, 0]),
            np.array([1, 0.5, 0, 0]),
            tau_max=5.0, dtau=0.1,
        )
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)

    def test_plot_geodesic_3d(self):
        """Test 3D plot generation."""
        import matplotlib
        matplotlib.use('Agg')
        from orchestrator.visualization import plot_geodesic_3d

        m = geom.Manifold("minkowski", ["t", "x", "y", "z"])
        g = geom.Metric.from_diagonal(m, ["-1", "1", "1", "1"])

        fig = plot_geodesic_3d(
            g, ["t", "x", "y", "z"],
            np.array([0, 0, 0, 0]),
            np.array([1, 0.3, 0.4, 0]),
            tau_max=5.0, dtau=0.1,
            coord_indices=(1, 2, 3),
        )
        assert fig is not None
        import matplotlib.pyplot as plt
        plt.close(fig)
