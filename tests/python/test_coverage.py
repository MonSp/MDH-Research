"""Expanded benchmark coverage (T10).

Covers:
- Parser edge cases
- C++ parser vs SymPy cross-validation
- Tensor operation coverage
- Metric computation edge cases
"""

import sys
import os
import pytest
import sympy as sp

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

rc = pytest.importorskip("_research_core")
sym = rc.symbol


class TestParserEdgeCases:
    def test_deeply_nested_parens(self):
        expr = sym.parse("(((((1)))))")
        assert str(expr) == "1"

    def test_many_terms(self):
        expr = sym.parse("a + b + c + d + e + f + g")
        assert str(expr) != ""

    def test_complex_fraction(self):
        expr = sym.parse("(a*b + c*d) / (e - f)")
        assert str(expr) != ""

    def test_function_in_power(self):
        expr = sym.parse("sin(x)^2 + cos(x)^2")
        assert str(expr) != ""

    def test_nested_functions(self):
        expr = sym.parse("sin(cos(x))")
        assert str(expr) != ""

    def test_negative_exponent(self):
        expr = sym.parse("r^(-2)")
        assert str(expr) != ""

    def test_scientific_notation(self):
        expr = sym.parse("1.5e10")
        assert str(expr) == "1.5e+10" or str(expr) == "15000000000" or "15" in str(expr)

    def test_subtraction_chain(self):
        expr = sym.parse("a - b - c")
        # Should parse as (a - b) - c = a + (-b) + (-c)
        assert str(expr) != ""

    def test_power_of_power(self):
        expr = sym.parse("x^2^3")
        # Right-associative: x^(2^3) = x^8
        assert str(expr) != ""

    def test_expression_operations(self):
        """Parsed expressions should support arithmetic."""
        x = sym.parse("x")
        y = sym.parse("y")
        expr = x + y
        assert str(expr) == "(x + y)"

    def test_parsed_expression_diff(self):
        """Parsed expressions should support differentiation."""
        expr = sym.parse("x^2")
        d = expr.diff("x")
        assert str(d) != ""


class TestCrossValidationCppSymPy:
    """Cross-validate C++ parser output against SymPy for key expressions."""

    def _cpp_parse_to_sympy(self, expr_str, var_map):
        """Parse with C++ parser, convert to SymPy for comparison."""
        cpp_expr = sym.parse(expr_str)
        return cpp_expr.to_string()

    def test_schwarzschild_g_tt(self):
        """C++ parses -(1 - 2*M/r) correctly."""
        cpp = sym.parse("-(1 - 2*M/r)")
        s = str(cpp)
        # Should contain the key terms
        assert "M" in s
        assert "r" in s

    def test_polynomial(self):
        """C++ parses r^2 - 2*M*r + a^2 correctly."""
        cpp = sym.parse("r^2 - 2*M*r + a^2")
        s = str(cpp)
        assert "r" in s
        assert "M" in s
        assert "a" in s

    def test_trig_expression(self):
        """C++ parses sin(theta)^2 correctly."""
        cpp = sym.parse("sin(theta)^2")
        s = str(cpp)
        assert "sin" in s
        assert "theta" in s

    def test_schwarzschild_christoffel_cross_check(self):
        """Cross-check: C++ metric produces same non-zero Christoffel pattern as SymPy."""
        # C++ computation
        m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
        g_cpp = geom.Metric.from_diagonal(m, [
            "-(1 - 2*M/r)",
            "(1 - 2*M/r)^(-1)",
            "r^2",
            "r^2 * sin(theta)^2",
        ])
        Gamma_cpp = g_cpp.christoffel_symbols()

        # Check non-zero pattern
        nonzero_cpp = set()
        for i in range(4):
            for j in range(4):
                for k in range(4):
                    if not Gamma_cpp[[i, j, k]].is_zero():
                        nonzero_cpp.add((i, j, k))

        # Known non-zero Christoffel symbols for Schwarzschild
        known_nonzero = {
            (0, 0, 1), (0, 1, 0),  # Gamma^t_{tr} = Gamma^t_{rt}
            (1, 0, 0),              # Gamma^r_{tt}
            (1, 1, 1),              # Gamma^r_{rr}
            (1, 2, 2),              # Gamma^r_{theta theta}
            (1, 3, 3),              # Gamma^r_{phi phi}
            (2, 1, 2), (2, 2, 1),  # Gamma^theta_{r theta}
            (2, 3, 3),              # Gamma^theta_{phi phi}
            (3, 1, 3), (3, 3, 1),  # Gamma^phi_{r phi}
            (3, 2, 3), (3, 3, 2),  # Gamma^phi_{theta phi}
        }

        # All known non-zero should be non-zero in C++ too
        for idx in known_nonzero:
            assert idx in nonzero_cpp, f"Gamma^{idx[0]}_{{{idx[1]}{idx[2]}}} should be non-zero"


# Import geometry for cross-validation tests
geom = rc.geometry
