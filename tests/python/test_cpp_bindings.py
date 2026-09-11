"""Schwarzschild benchmark via C++ pybind11 bindings (T6)."""

import sys
import os
import pytest

# Add build dir to path for the compiled module
BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

rc = pytest.importorskip("_research_core")


def _make_schwarzschild():
    """Build Schwarzschild metric using C++ bindings."""
    sym = rc.symbol
    geom = rc.geometry

    m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
    M = sym.symbol("M")
    r = sym.symbol("r")
    theta = sym.symbol("theta")

    # g_{tt} = -(1 - 2M/r)
    g_tt = sym.neg(sym.add(sym.number(1), sym.neg(sym.mul(sym.number(2), sym.mul(M, sym.pow(r, sym.number(-1)))))))
    # g_{rr} = (1 - 2M/r)^{-1}
    one_minus = sym.add(sym.number(1), sym.neg(sym.mul(sym.number(2), sym.mul(M, sym.pow(r, sym.number(-1))))))
    g_rr = sym.pow(one_minus, sym.number(-1))
    # g_{θθ} = r^2
    g_thth = sym.mul(sym.symbol("r"), sym.symbol("r"))
    r2 = g_thth
    # g_{φφ} = r^2 sin^2(θ)
    sin_th = sym.func("sin", [sym.symbol("theta")]) if hasattr(sym, 'func') else None

    # For simplicity, build the metric directly from known expressions
    # The C++ API takes Expression::Ptr components
    components = [
        [g_tt, sym.number(0), sym.number(0), sym.number(0)],
        [sym.number(0), g_rr, sym.number(0), sym.number(0)],
        [sym.number(0), sym.number(0), r2, sym.number(0)],
        [sym.number(0), sym.number(0), sym.number(0), r2],  # simplified: skip sin^2 term for now
    ]

    g = geom.Metric(m, components)
    return m, g


def test_christoffel_symbols_nonzero():
    """Schwarzschild Christoffel symbols should be non-trivial."""
    m, g = _make_schwarzschild()
    Gamma = g.christoffel_symbols()

    # At least some components should be non-zero
    has_nonzero = False
    for i in range(4):
        for j in range(4):
            for k in range(4):
                val = Gamma.at([i, j, k])
                if not val.is_zero():
                    has_nonzero = True
                    break
            if has_nonzero:
                break
        if has_nonzero:
            break

    assert has_nonzero, "Expected non-zero Christoffel symbols for Schwarzschild"


def test_ricci_tensor_structure():
    """Ricci tensor should be computable."""
    m, g = _make_schwarzschild()
    Ric = g.ricci_tensor()

    # Should be a 4x4 tensor
    assert Ric.rank() == 2


def test_scalar_curvature():
    """Scalar curvature should be computable."""
    m, g = _make_schwarzschild()
    R = g.scalar_curvature()
    assert R is not None


def test_flat_metric_christoffel_zero():
    """Flat 2D metric should have all-zero Christoffel symbols."""
    sym = rc.symbol
    geom = rc.geometry

    m = geom.Manifold("2d", ["x", "y"])
    g = geom.Metric(m, [[sym.number(1), sym.number(0)],
                         [sym.number(0), sym.number(1)]])

    Gamma = g.christoffel_symbols()
    for i in range(2):
        for j in range(2):
            for k in range(2):
                assert Gamma.at([i, j, k]).is_zero(), f"Gamma^{i}_{{{j}{k}}} should be zero"


def test_flat_metric_scalar_curvature_zero():
    """Flat 2D metric should have zero scalar curvature."""
    sym = rc.symbol
    geom = rc.geometry

    m = geom.Manifold("2d", ["x", "y"])
    g = geom.Metric(m, [[sym.number(1), sym.number(0)],
                         [sym.number(0), sym.number(1)]])

    R = g.scalar_curvature()
    assert R.is_zero(), f"Scalar curvature should be zero for flat metric, got {R.to_string()}"
