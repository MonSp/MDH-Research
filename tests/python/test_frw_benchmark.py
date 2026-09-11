"""FLRW metric benchmark — SymPy verification of Christoffel symbols and Ricci tensor.

The Friedmann-Lemaître-Robertson-Walker metric describes a homogeneous,
isotropic expanding universe:

  ds² = -dt² + a(t)² [dr²/(1-kr²) + r²dθ² + r²sin²θ dφ²]

For k=0 (flat universe):
  g_tt = -1, g_rr = a(t)², g_θθ = a(t)²r², g_φφ = a(t)²r²sin²θ

Non-zero Christoffel symbols:
  Γ^t_{rr} = a·ȧ/(1-kr²), Γ^t_{θθ} = a·ȧ·r², Γ^t_{φφ} = a·ȧ·r²sin²θ
  Γ^r_{tr} = Γ^r_{rt} = ȧ/a, Γ^r_{rr} = k·r/(1-kr²)  [for k≠0]
  Γ^θ_{tθ} = Γ^θ_{θt} = ȧ/a, Γ^θ_{φφ} = -sinθ·cosθ
  Γ^φ_{tφ} = Γ^φ_{φt} = ȧ/a, Γ^φ_{θφ} = Γ^φ_{φθ} = cosθ/sinθ

Ricci tensor (k=0):
  R_tt = -3ä/a
  R_rr = a·ä + 2ȧ²
  R_θθ = (a·ä + 2ȧ²)r²
  R_φφ = (a·ä + 2ȧ²)r²sin²θ

Scalar curvature:
  R = 6(ä/a + ȧ²/a²) = 6(ä/a + H²)
"""

import pytest
import sympy as sp


def test_frw_christoffel_k0():
    """Verify FLRW (k=0) Christoffel symbols match known expressions."""
    t, r, theta, phi = sp.symbols("t r theta phi", positive=True)
    a = sp.Function("a")(t)
    adot = sp.diff(a, t)

    # FLRW metric k=0
    g = sp.Matrix([
        [-1, 0, 0, 0],
        [0, a**2, 0, 0],
        [0, 0, a**2 * r**2, 0],
        [0, 0, 0, a**2 * r**2 * sp.sin(theta)**2],
    ])

    g_inv = g.inv()
    coords = [t, r, theta, phi]
    n = 4

    # Christoffel symbols
    Gamma = [[[sp.S.Zero] * n for _ in range(n)] for _ in range(n)]
    for mu in range(n):
        for nu in range(n):
            for rho in range(n):
                s = sp.S.Zero
                for sigma in range(n):
                    s += sp.Rational(1, 2) * g_inv[mu, sigma] * (
                        sp.diff(g[sigma, nu], coords[rho])
                        + sp.diff(g[sigma, rho], coords[nu])
                        - sp.diff(g[nu, rho], coords[sigma])
                    )
                Gamma[mu][nu][rho] = sp.simplify(s)

    # Key non-zero components
    # Γ^t_{rr} = a*ȧ
    assert sp.simplify(Gamma[0][1][1] - a * adot) == 0, f"Γ^t_{{rr}} = {Gamma[0][1][1]}"

    # Γ^t_{θθ} = a*ȧ*r²
    assert sp.simplify(Gamma[0][2][2] - a * adot * r**2) == 0, f"Γ^t_{{θθ}} = {Gamma[0][2][2]}"

    # Γ^t_{φφ} = a*ȧ*r²*sin²θ
    assert sp.simplify(Gamma[0][3][3] - a * adot * r**2 * sp.sin(theta)**2) == 0

    # Γ^r_{tr} = ȧ/a
    assert sp.simplify(Gamma[1][0][1] - adot / a) == 0, f"Γ^r_{{tr}} = {Gamma[1][0][1]}"

    # Γ^θ_{tθ} = ȧ/a
    assert sp.simplify(Gamma[2][0][2] - adot / a) == 0

    # Γ^φ_{tφ} = ȧ/a
    assert sp.simplify(Gamma[3][0][3] - adot / a) == 0

    # Γ^θ_{φφ} = -sinθ·cosθ
    assert sp.simplify(Gamma[2][3][3] + sp.sin(theta) * sp.cos(theta)) == 0

    # Γ^φ_{θφ} = cosθ/sinθ
    assert sp.simplify(Gamma[3][2][3] - sp.cos(theta) / sp.sin(theta)) == 0

    # Γ^r_{θθ} = -r (standard spherical coordinates)
    assert sp.simplify(Gamma[1][2][2] + r) == 0, f"Γ^r_{{θθ}} = {Gamma[1][2][2]}"

    # Γ^r_{φφ} = -r·sin²θ
    assert sp.simplify(Gamma[1][3][3] + r * sp.sin(theta)**2) == 0

    # Zero components
    assert Gamma[0][0][0] == 0  # Γ^t_{tt}
    assert Gamma[1][1][1] == 0  # Γ^r_{rr} = 0 for k=0


def test_frw_ricci_k0():
    """Verify FLRW (k=0) Ricci tensor."""
    t, r, theta, phi = sp.symbols("t r theta phi", positive=True)
    a = sp.Function("a")(t)
    adot = sp.diff(a, t)
    addot = sp.diff(a, t, 2)

    g = sp.Matrix([
        [-1, 0, 0, 0],
        [0, a**2, 0, 0],
        [0, 0, a**2 * r**2, 0],
        [0, 0, 0, a**2 * r**2 * sp.sin(theta)**2],
    ])

    g_inv = g.inv()
    coords = [t, r, theta, phi]
    n = 4

    Gamma = [[[sp.S.Zero] * n for _ in range(n)] for _ in range(n)]
    for mu in range(n):
        for nu in range(n):
            for rho in range(n):
                s = sp.S.Zero
                for sigma in range(n):
                    s += sp.Rational(1, 2) * g_inv[mu, sigma] * (
                        sp.diff(g[sigma, nu], coords[rho])
                        + sp.diff(g[sigma, rho], coords[nu])
                        - sp.diff(g[nu, rho], coords[sigma])
                    )
                Gamma[mu][nu][rho] = sp.simplify(s)

    # Riemann -> Ricci
    Riemann = [[[[sp.S.Zero] * n for _ in range(n)] for _ in range(n)] for _ in range(n)]
    for mu in range(n):
        for nu in range(n):
            for rho in range(n):
                for sigma in range(n):
                    s = sp.diff(Gamma[mu][nu][sigma], coords[rho]) - sp.diff(Gamma[mu][nu][rho], coords[sigma])
                    for lam in range(n):
                        s += Gamma[mu][lam][rho] * Gamma[lam][nu][sigma]
                        s -= Gamma[mu][lam][sigma] * Gamma[lam][nu][rho]
                    Riemann[mu][nu][rho][sigma] = sp.simplify(s)

    Ricci = [[sp.S.Zero] * n for _ in range(n)]
    for nu in range(n):
        for sigma in range(n):
            s = sp.S.Zero
            for mu in range(n):
                s += Riemann[mu][nu][mu][sigma]
            Ricci[nu][sigma] = sp.simplify(s)

    # R_tt = -3ä/a
    assert sp.simplify(Ricci[0][0] - (-3 * addot / a)) == 0, f"R_tt = {Ricci[0][0]}"

    # R_rr = a*ä + 2ȧ²
    assert sp.simplify(Ricci[1][1] - (a * addot + 2 * adot**2)) == 0, f"R_rr = {Ricci[1][1]}"

    # R_θθ = (a*ä + 2ȧ²)r²
    assert sp.simplify(Ricci[2][2] - (a * addot + 2 * adot**2) * r**2) == 0

    # R_φφ = (a*ä + 2ȧ²)r²sin²θ
    assert sp.simplify(Ricci[3][3] - (a * addot + 2 * adot**2) * r**2 * sp.sin(theta)**2) == 0


def test_frw_scalar_curvature():
    """Verify FLRW scalar curvature R = 6(ä/a + ȧ²/a²)."""
    t = sp.Symbol("t", positive=True)
    a = sp.Function("a")(t)
    adot = sp.diff(a, t)
    addot = sp.diff(a, t, 2)

    r, theta, phi = sp.symbols("r theta phi", positive=True)
    g = sp.Matrix([
        [-1, 0, 0, 0],
        [0, a**2, 0, 0],
        [0, 0, a**2 * r**2, 0],
        [0, 0, 0, a**2 * r**2 * sp.sin(theta)**2],
    ])

    g_inv = g.inv()
    coords = [t, r, theta, phi]
    n = 4

    Gamma = [[[sp.S.Zero] * n for _ in range(n)] for _ in range(n)]
    for mu in range(n):
        for nu in range(n):
            for rho in range(n):
                s = sp.S.Zero
                for sigma in range(n):
                    s += sp.Rational(1, 2) * g_inv[mu, sigma] * (
                        sp.diff(g[sigma, nu], coords[rho])
                        + sp.diff(g[sigma, rho], coords[nu])
                        - sp.diff(g[nu, rho], coords[sigma])
                    )
                Gamma[mu][nu][rho] = sp.simplify(s)

    Riemann = [[[[sp.S.Zero] * n for _ in range(n)] for _ in range(n)] for _ in range(n)]
    for mu in range(n):
        for nu in range(n):
            for rho in range(n):
                for sigma in range(n):
                    s = sp.diff(Gamma[mu][nu][sigma], coords[rho]) - sp.diff(Gamma[mu][nu][rho], coords[sigma])
                    for lam in range(n):
                        s += Gamma[mu][lam][rho] * Gamma[lam][nu][sigma]
                        s -= Gamma[mu][lam][sigma] * Gamma[lam][nu][rho]
                    Riemann[mu][nu][rho][sigma] = sp.simplify(s)

    Ricci = [[sp.S.Zero] * n for _ in range(n)]
    for nu in range(n):
        for sigma in range(n):
            s = sp.S.Zero
            for mu in range(n):
                s += Riemann[mu][nu][mu][sigma]
            Ricci[nu][sigma] = sp.simplify(s)

    # Scalar curvature R = g^{μν} R_{μν}
    R = sp.S.Zero
    for mu in range(n):
        for nu in range(n):
            R += g_inv[mu, nu] * Ricci[mu][nu]
    R = sp.simplify(R)

    # Expected: 6(ä/a + ȧ²/a²)
    expected = 6 * (addot / a + adot**2 / a**2)
    assert sp.simplify(R - expected) == 0, f"R = {R}, expected {expected}"
