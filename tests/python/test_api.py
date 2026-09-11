"""Tests for the improved Python bindings API (T8)."""

import sys
import os
import pytest

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

rc = pytest.importorskip("_research_core")
sym = rc.symbol
geom = rc.geometry


class TestExpressionOperators:
    def test_add_expressions(self):
        x = sym.symbol("x")
        y = sym.symbol("y")
        expr = x + y
        assert str(expr) == "(x + y)"

    def test_add_scalar(self):
        x = sym.symbol("x")
        expr = x + 3
        assert str(expr) == "(x + 3)"

    def test_radd_scalar(self):
        x = sym.symbol("x")
        expr = 3 + x
        assert str(expr) == "(3 + x)"

    def test_sub_expressions(self):
        x = sym.symbol("x")
        y = sym.symbol("y")
        expr = x - y
        assert str(expr) == "(x + (-y))"

    def test_mul_expressions(self):
        x = sym.symbol("x")
        y = sym.symbol("y")
        expr = x * y
        assert str(expr) == "(x * y)"

    def test_mul_scalar(self):
        x = sym.symbol("x")
        expr = x * 2
        assert str(expr) == "(x * 2)"

    def test_rmul_scalar(self):
        x = sym.symbol("x")
        expr = 2 * x
        assert str(expr) == "(2 * x)"

    def test_div_expressions(self):
        x = sym.symbol("x")
        y = sym.symbol("y")
        expr = x / y
        s = str(expr)
        assert "x" in s and "y" in s and "^" in s

    def test_pow(self):
        x = sym.symbol("x")
        expr = x ** 2
        s = str(expr)
        assert "x" in s and "2" in s

    def test_neg(self):
        x = sym.symbol("x")
        expr = -x
        assert str(expr) == "(-x)"

    def test_chained_operators(self):
        x = sym.symbol("x")
        expr = x ** 2 + 2 * x + 1
        assert str(expr) != ""

    def test_str(self):
        n = sym.number(42)
        assert str(n) == "42"

    def test_repr(self):
        x = sym.symbol("x")
        r = repr(x)
        assert "Expression" in r
        assert "x" in r

    def test_eq_same(self):
        x1 = sym.symbol("x")
        x2 = sym.symbol("x")
        assert x1 == x2

    def test_eq_different(self):
        x = sym.symbol("x")
        y = sym.symbol("y")
        assert not (x == y)


class TestParseConvenience:
    def test_top_level_parse(self):
        expr = rc.parse("1 - 2*M/r")
        assert str(expr) != ""

    def test_symbol_parse(self):
        expr = sym.parse("sin(theta)^2")
        assert str(expr) != ""


class TestTensorPythonic:
    def test_getitem(self):
        m = geom.Manifold("2d", ["x", "y"])
        g = geom.Metric.from_diagonal(m, ["1", "1"])
        t = g.covariant_tensor()
        val = t[[0, 0]]
        assert val.is_one()

    def test_setitem(self):
        m = geom.Manifold("2d", ["x", "y"])
        g = geom.Metric.from_diagonal(m, ["1", "1"])
        t = g.covariant_tensor()
        t[[0, 0]] = sym.number(99)
        assert t[[0, 0]].to_string() == "99"

    def test_repr(self):
        m = geom.Manifold("2d", ["x", "y"])
        g = geom.Metric.from_diagonal(m, ["1", "1"])
        t = g.covariant_tensor()
        r = repr(t)
        assert "Tensor" in r or "rank" in r


class TestGeometryFactories:
    def test_from_diagonal(self):
        m = geom.Manifold("2d", ["x", "y"])
        g = geom.Metric.from_diagonal(m, ["1", "r^2"])
        assert g.dimension() == 2
        assert g.g(0, 0).is_one()
        s = str(g.g(1, 1))
        assert "r" in s and "2" in s

    def test_from_diagonal_schwarzschild(self):
        m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
        g = geom.Metric.from_diagonal(m, [
            "-(1 - 2*M/r)",
            "(1 - 2*M/r)^(-1)",
            "r^2",
            "r^2 * sin(theta)^2",
        ])
        assert g.dimension() == 4
        assert not g.g(0, 0).is_zero()

    def test_from_diagonal_wrong_length(self):
        m = geom.Manifold("3d", ["x", "y", "z"])
        with pytest.raises(Exception):
            geom.Metric.from_diagonal(m, ["1", "1"])

    def test_manifold_repr(self):
        m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
        r = repr(m)
        assert "spacetime" in r
        assert "4" in r

    def test_metric_repr(self):
        m = geom.Manifold("2d", ["x", "y"])
        g = geom.Metric.from_diagonal(m, ["1", "1"])
        r = repr(g)
        assert "2" in r
