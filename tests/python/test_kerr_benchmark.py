"""Kerr metric benchmark — SymPy verification of key curvature properties.

The Kerr metric describes a rotating black hole with mass M and angular
momentum parameter a (= J/M). In Boyer-Lindquist coordinates (t, r, θ, φ):

  Σ = r² + a²cos²θ
  Δ = r² - 2Mr + a²

  ds² = -(1 - 2Mr/Σ)dt² - (4Mar sin²θ/Σ)dt dφ
        + (Σ/Δ)dr² + Σ dθ²
        + (r² + a² + 2Ma²r sin²θ/Σ)sin²θ dφ²

Key properties to verify:
1. The metric is stationary and axisymmetric
2. Ricci tensor = 0 (vacuum solution)
3. Scalar curvature = 0
4. Kretschner scalar K = R_{μνρσ}R^{μνρσ} is finite and non-zero (curvature singularity)

For this benchmark we verify properties using a simplified diagonal
approximation that captures the essential structure.
"""

import pytest
import sympy as sp


def _compute_riemann_ricci(g, coords, simplify=True):
    """Helper to compute Riemann and Ricci tensors from metric.

    Args:
        simplify: If True, use sp.simplify (accurate but slow).
                  If False, use sp.cancel (faster, sufficient for numerical evaluation).
    """
    n = len(coords)
    g_inv = g.inv()
    simplify_fn = sp.simplify if simplify else sp.cancel

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
                Gamma[mu][nu][rho] = simplify_fn(s)

    Riemann = [[[[sp.S.Zero] * n for _ in range(n)] for _ in range(n)] for _ in range(n)]
    for mu in range(n):
        for nu in range(n):
            for rho in range(n):
                for sigma in range(n):
                    s = sp.diff(Gamma[mu][nu][sigma], coords[rho]) - sp.diff(Gamma[mu][nu][rho], coords[sigma])
                    for lam in range(n):
                        s += Gamma[mu][lam][rho] * Gamma[lam][nu][sigma]
                        s -= Gamma[mu][lam][sigma] * Gamma[lam][nu][rho]
                    Riemann[mu][nu][rho][sigma] = simplify_fn(s)

    Ricci = [[sp.S.Zero] * n for _ in range(n)]
    for nu in range(n):
        for sigma in range(n):
            s = sp.S.Zero
            for mu in range(n):
                s += Riemann[mu][nu][mu][sigma]
            Ricci[nu][sigma] = simplify_fn(s)

    return Riemann, Ricci, Gamma


def test_kerr_vacuum_ricci_flat():
    """Kerr metric (a=0 limit) reduces to Schwarzschild → Ricci = 0."""
    # When a=0, Kerr reduces to Schwarzschild
    t, r, theta, phi = sp.symbols("t r theta phi", positive=True)
    M = sp.Symbol("M", positive=True)

    f = 1 - 2 * M / r
    g = sp.Matrix([
        [-f, 0, 0, 0],
        [0, 1 / f, 0, 0],
        [0, 0, r**2, 0],
        [0, 0, 0, r**2 * sp.sin(theta)**2],
    ])

    coords = [t, r, theta, phi]
    _, Ricci, _ = _compute_riemann_ricci(g, coords)

    # Schwarzschild is vacuum: Ricci = 0
    for nu in range(4):
        for sigma in range(4):
            assert Ricci[nu][sigma] == 0, f"R_{{{nu}{sigma}}} = {Ricci[nu][sigma]}"


def test_kerr_metric_structure():
    """Kerr metric in Boyer-Lindquist coordinates has correct structure."""
    t, r, theta, phi = sp.symbols("t r theta phi", positive=True)
    M, a = sp.symbols("M a", positive=True)

    Sigma = r**2 + a**2 * sp.cos(theta)**2
    Delta = r**2 - 2 * M * r + a**2

    # Full Kerr metric (off-diagonal g_tt and g_tφ terms)
    g_tt = -(1 - 2 * M * r / Sigma)
    g_tphi = -2 * M * a * r * sp.sin(theta)**2 / Sigma
    g_rr = Sigma / Delta
    g_thth = Sigma
    g_phiphi = (r**2 + a**2 + 2 * M * a**2 * r * sp.sin(theta)**2 / Sigma) * sp.sin(theta)**2

    g = sp.Matrix([
        [g_tt, 0, 0, g_tphi],
        [0, g_rr, 0, 0],
        [0, 0, g_thth, 0],
        [g_tphi, 0, 0, g_phiphi],
    ])

    # Verify determinant is non-zero (metric is non-degenerate away from horizons)
    det = sp.simplify(g.det())
    assert det != 0, "Metric determinant should be non-zero"

    # Verify symmetry
    for i in range(4):
        for j in range(4):
            assert g[i, j] == g[j, i], f"g[{i},{j}] != g[{j},{i}]"

    # Verify g_tt < 0 (timelike) for large r
    g_tt_val = g_tt.subs([(r, 100), (M, 1), (a, 0.5), (theta, sp.pi / 4)])
    assert g_tt_val < 0, f"g_tt should be negative at large r, got {g_tt_val}"


def test_kerr_ricci_vacuum_numerical():
    """Full Kerr metric: Ricci tensor = 0 verified numerically at sample points.

    Full symbolic simplification is too expensive for the Kerr metric,
    so we verify numerically at several points outside the event horizon.
    """
    t_s, r_s, theta_s, phi_s = sp.symbols("t r theta phi", positive=True)
    M_s, a_s = sp.symbols("M a", positive=True)

    Sigma = r_s**2 + a_s**2 * sp.cos(theta_s)**2
    Delta = r_s**2 - 2 * M_s * r_s + a_s**2

    g_tt = -(1 - 2 * M_s * r_s / Sigma)
    g_tphi = -2 * M_s * a_s * r_s * sp.sin(theta_s)**2 / Sigma
    g_rr = Sigma / Delta
    g_thth = Sigma
    g_phiphi = (r_s**2 + a_s**2 + 2 * M_s * a_s**2 * r_s * sp.sin(theta_s)**2 / Sigma) * sp.sin(theta_s)**2

    g_sym = sp.Matrix([
        [g_tt, 0, 0, g_tphi],
        [0, g_rr, 0, 0],
        [0, 0, g_thth, 0],
        [g_tphi, 0, 0, g_phiphi],
    ])

    coords = [t_s, r_s, theta_s, phi_s]
    _, Ricci_sym, _ = _compute_riemann_ricci(g_sym, coords, simplify=False)

    # Verify numerically at several points outside the event horizon
    # M=1, a=0.5 → r+ = 1 + √0.75 ≈ 1.866
    sample_points = [
        {t_s: 0, r_s: 5, theta_s: sp.pi / 4, phi_s: 0, M_s: 1, a_s: sp.Rational(1, 2)},
        {t_s: 0, r_s: 10, theta_s: sp.pi / 3, phi_s: sp.pi, M_s: 1, a_s: sp.Rational(1, 2)},
        {t_s: 0, r_s: 3, theta_s: sp.pi / 2, phi_s: sp.pi / 4, M_s: 2, a_s: sp.Rational(1, 3)},
    ]

    for subs in sample_points:
        for nu in range(4):
            for sigma in range(4):
                val = Ricci_sym[nu][sigma].subs(subs)
                val = sp.nsimplify(val, rational=False)
                assert val == 0, (
                    f"R_{{{nu}{sigma}}} = {val} at {subs}"
                )


def test_kerr_event_horizon():
    """Kerr event horizons at r± = M ± √(M² - a²)."""
    M, a = sp.symbols("M a", positive=True)

    Delta = sp.Symbol("Delta")
    # Δ = r² - 2Mr + a² = 0 → r = M ± √(M²-a²)
    r_plus = M + sp.sqrt(M**2 - a**2)
    r_minus = M - sp.sqrt(M**2 - a**2)

    # Verify these are roots of Δ
    Delta_expr = lambda r: r**2 - 2 * M * r + a**2
    assert sp.simplify(Delta_expr(r_plus)) == 0
    assert sp.simplify(Delta_expr(r_minus)) == 0

    # For a=0, both horizons reduce to Schwarzschild radius r=2M
    r_plus_schw = r_plus.subs(a, 0)
    assert sp.simplify(r_plus_schw - 2 * M) == 0
