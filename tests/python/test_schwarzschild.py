"""Python tests for the research core bindings and Schwarzschild benchmark."""

import pytest


def test_version():
    """Test that the package version is correct."""
    # This test will work once the C++ extension is built
    # For now, test the pure Python layer
    import src
    assert src.__version__ == "0.1.0"


def test_sympy_schwarzschild_christoffel():
    """Verify Schwarzschild Christoffel symbols using SymPy as reference.

    This serves as the ground-truth benchmark for the C++ engine.
    """
    sympy = pytest.importorskip("sympy")

    t, r, theta, phi, M = sympy.symbols("t r theta phi M", real=True)

    # Schwarzschild metric components
    f = 1 - 2 * M / r
    g = sympy.Matrix([
        [-f, 0, 0, 0],
        [0, 1 / f, 0, 0],
        [0, 0, r**2, 0],
        [0, 0, 0, r**2 * sympy.sin(theta)**2],
    ])

    g_inv = g.inv()
    coords = [t, r, theta, phi]
    n = 4

    # Christoffel symbols
    Gamma = [[[sympy.S.Zero] * n for _ in range(n)] for _ in range(n)]
    for mu in range(n):
        for nu in range(n):
            for rho in range(n):
                s = sympy.S.Zero
                for sigma in range(n):
                    s += sympy.Rational(1, 2) * g_inv[mu, sigma] * (
                        sympy.diff(g[sigma, nu], coords[rho])
                        + sympy.diff(g[sigma, rho], coords[nu])
                        - sympy.diff(g[nu, rho], coords[sigma])
                    )
                Gamma[mu][nu][rho] = sympy.simplify(s)

    # Verify known non-zero components
    # Gamma^t_{tr} = M / (r*(r - 2M))
    gt_tr = sympy.simplify(Gamma[0][0][1] - M / (r * (r - 2 * M)))
    assert gt_tr == 0, f"Gamma^t_{{tr}} mismatch: {Gamma[0][0][1]}"

    # Gamma^r_{tt} = M*(r - 2M) / r^3
    gr_tt = sympy.simplify(Gamma[1][0][0] - M * (r - 2 * M) / r**3)
    assert gr_tt == 0, f"Gamma^r_{{tt}} mismatch: {Gamma[1][0][0]}"

    # Gamma^r_{rr} = -M / (r*(r - 2M))
    gr_rr = sympy.simplify(Gamma[1][1][1] - (-M / (r * (r - 2 * M))))
    assert gr_rr == 0, f"Gamma^r_{{rr}} mismatch: {Gamma[1][1][1]}"

    # Gamma^r_{θθ} = -(r - 2M)
    gr_thth = sympy.simplify(Gamma[1][2][2] - (-(r - 2 * M)))
    assert gr_thth == 0, f"Gamma^r_{{θθ}} mismatch: {Gamma[1][2][2]}"

    # Gamma^θ_{rθ} = 1/r
    gth_rth = sympy.simplify(Gamma[2][1][2] - 1 / r)
    assert gth_rth == 0, f"Gamma^θ_{{rθ}} mismatch: {Gamma[2][1][2]}"

    # Gamma^φ_{rφ} = 1/r
    gph_rph = sympy.simplify(Gamma[3][1][3] - 1 / r)
    assert gph_rph == 0, f"Gamma^φ_{{rφ}} mismatch: {Gamma[3][1][3]}"

    # Gamma^θ_{φφ} = -sin(θ)*cos(θ)
    gth_pp = sympy.simplify(Gamma[2][3][3] - (-sympy.sin(theta) * sympy.cos(theta)))
    assert gth_pp == 0, f"Gamma^θ_{{φφ}} mismatch: {Gamma[2][3][3]}"


def test_sympy_schwarzschild_ricci():
    """Verify Schwarzschild Ricci tensor is zero (vacuum solution)."""
    sympy = pytest.importorskip("sympy")

    t, r, theta, phi, M = sympy.symbols("t r theta phi M", real=True)

    f = 1 - 2 * M / r
    g = sympy.Matrix([
        [-f, 0, 0, 0],
        [0, 1 / f, 0, 0],
        [0, 0, r**2, 0],
        [0, 0, 0, r**2 * sympy.sin(theta)**2],
    ])

    g_inv = g.inv()
    coords = [t, r, theta, phi]
    n = 4

    # Christoffel symbols
    Gamma = [[[sympy.S.Zero] * n for _ in range(n)] for _ in range(n)]
    for mu in range(n):
        for nu in range(n):
            for rho in range(n):
                s = sympy.S.Zero
                for sigma in range(n):
                    s += sympy.Rational(1, 2) * g_inv[mu, sigma] * (
                        sympy.diff(g[sigma, nu], coords[rho])
                        + sympy.diff(g[sigma, rho], coords[nu])
                        - sympy.diff(g[nu, rho], coords[sigma])
                    )
                Gamma[mu][nu][rho] = sympy.simplify(s)

    # Riemann tensor R^mu_{nu rho sigma}
    Riemann = [[[[sympy.S.Zero] * n for _ in range(n)] for _ in range(n)] for _ in range(n)]
    for mu in range(n):
        for nu in range(n):
            for rho in range(n):
                for sigma in range(n):
                    s = (
                        sympy.diff(Gamma[mu][nu][sigma], coords[rho])
                        - sympy.diff(Gamma[mu][nu][rho], coords[sigma])
                    )
                    for lam in range(n):
                        s += Gamma[mu][lam][rho] * Gamma[lam][nu][sigma]
                        s -= Gamma[mu][lam][sigma] * Gamma[lam][nu][rho]
                    Riemann[mu][nu][rho][sigma] = sympy.simplify(s)

    # Ricci tensor R_{nu sigma} = R^mu_{nu mu sigma}
    Ricci = [[sympy.S.Zero] * n for _ in range(n)]
    for nu in range(n):
        for sigma in range(n):
            s = sympy.S.Zero
            for mu in range(n):
                s += Riemann[mu][nu][mu][sigma]
            Ricci[nu][sigma] = sympy.simplify(s)

    # Schwarzschild is a vacuum solution: R_{mu nu} = 0
    for nu in range(n):
        for sigma in range(n):
            assert Ricci[nu][sigma] == 0, (
                f"R_{{{nu}{sigma}}} = {Ricci[nu][sigma]} != 0"
            )
