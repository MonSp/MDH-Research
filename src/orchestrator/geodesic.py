"""Numerical geodesic solver for Riemannian/Lorentzian manifolds.

Solves the geodesic equation:
    d²x^μ/dτ² + Γ^μ_{νρ} (dx^ν/dτ)(dx^ρ/dτ) = 0

Using 4th-order Runge-Kutta integration.
"""

from __future__ import annotations

import sys
import os
from typing import Callable

import numpy as np

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

try:
    import _research_core as rc
except ImportError:
    rc = None


def christoffel_numerical_evaluator(
    metric, coord_names: list[str], params: dict[str, float] | None = None
):
    """Create a numerical Christoffel symbol evaluator from a Metric object.

    Args:
        metric: Metric object from C++ bindings
        coord_names: coordinate names (e.g. ["t", "r", "theta", "phi"])
        params: fixed parameter values (e.g. {"M": 1.0, "a": 0.5})

    Returns:
        function(coords) -> Gamma array of shape (n, n, n)
    """
    Gamma_sym = metric.christoffel_symbols()
    n = metric.dimension()
    params = params or {}

    def evaluate(coords: np.ndarray) -> np.ndarray:
        """Evaluate all Christoffel symbols at given coordinates."""
        var_map = dict(params)
        for i in range(n):
            var_map[coord_names[i]] = float(coords[i])
        result = np.zeros((n, n, n))
        for mu in range(n):
            for nu in range(n):
                for rho in range(n):
                    result[mu, nu, rho] = Gamma_sym[[mu, nu, rho]].evaluate(var_map)
        return result

    return evaluate


def geodesic_equation(
    gamma_eval: Callable,
    tau: float,
    state: np.ndarray,
) -> np.ndarray:
    """Right-hand side of the geodesic equation in first-order form.

    State: [x^0, ..., x^{n-1}, u^0, ..., u^{n-1}]
    where u^mu = dx^mu/dtau

    Returns: [u^0, ..., u^{n-1}, du^0/dtau, ..., du^{n-1}/dtau]
    """
    n = len(state) // 2
    x = state[:n]
    u = state[n:]

    Gamma = gamma_eval(x)

    dxdt = u.copy()
    dudt = np.zeros(n)
    for mu in range(n):
        for nu in range(n):
            for rho in range(n):
                dudt[mu] -= Gamma[mu, nu, rho] * u[nu] * u[rho]

    return np.concatenate([dxdt, dudt])


def solve_geodesic(
    metric,
    coord_names: list[str],
    x0: np.ndarray,
    u0: np.ndarray,
    tau_max: float,
    dtau: float = 0.01,
    method: str = "rk4",
    params: dict[str, float] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Solve the geodesic equation numerically.

    Args:
        metric: Metric object from the C++ bindings
        coord_names: list of coordinate names
        x0: initial position (n,)
        u0: initial 4-velocity (n,)
        tau_max: maximum affine parameter
        dtau: step size
        method: integration method ("rk4" or "euler")
        params: fixed metric parameters (e.g. {"M": 1.0})

    Returns:
        (taus, trajectory) where:
        - taus: array of affine parameter values
        - trajectory: array of shape (n_steps, 2*n) with [x, u] at each step
    """
    n = len(x0)
    gamma_eval = christoffel_numerical_evaluator(metric, coord_names, params)

    state = np.concatenate([x0, u0])
    states = [state.copy()]
    taus = [0.0]

    tau = 0.0
    while tau < tau_max:
        if method == "rk4":
            k1 = geodesic_equation(gamma_eval, tau, state)
            k2 = geodesic_equation(gamma_eval, tau + dtau / 2, state + dtau / 2 * k1)
            k3 = geodesic_equation(gamma_eval, tau + dtau / 2, state + dtau / 2 * k2)
            k4 = geodesic_equation(gamma_eval, tau + dtau, state + dtau * k3)
            state = state + dtau / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        elif method == "euler":
            state = state + dtau * geodesic_equation(gamma_eval, tau, state)
        else:
            raise ValueError(f"Unknown method: {method}")

        tau += dtau
        taus.append(tau)
        states.append(state.copy())

    return np.array(taus), np.array(states)


def christoffel_at_point(
    metric, coord_names: list[str], coords: np.ndarray,
    params: dict[str, float] | None = None,
) -> np.ndarray:
    """Evaluate all Christoffel symbols at a single point.

    Returns:
        Gamma array of shape (n, n, n)
    """
    gamma_eval = christoffel_numerical_evaluator(metric, coord_names, params)
    return gamma_eval(coords)
