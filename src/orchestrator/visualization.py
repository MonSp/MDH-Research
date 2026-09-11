"""Geodesic trajectory 3D visualization (T17).

Renders geodesic trajectories as 3D plots using matplotlib.
"""

from __future__ import annotations

import sys
import os
from typing import Any

import numpy as np

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

try:
    import _research_core as rc
except ImportError:
    rc = None

from .geodesic import solve_geodesic


def _to_spherical_cartesian(r, theta, phi):
    """Convert spherical coordinates to Cartesian for 3D plotting."""
    x = r * np.sin(theta) * np.cos(phi)
    y = r * np.sin(theta) * np.sin(phi)
    z = r * np.cos(theta)
    return x, y, z


def plot_geodesic_3d(
    metric,
    coord_names: list[str],
    x0: np.ndarray,
    u0: np.ndarray,
    tau_max: float,
    dtau: float = 0.01,
    params: dict[str, float] | None = None,
    coord_indices: tuple[int, int, int] = (1, 2, 3),
    title: str = "Geodesic Trajectory",
    save_path: str | None = None,
    show: bool = False,
) -> Any:
    """Plot a geodesic trajectory in 3D.

    Args:
        metric: Metric object
        coord_names: coordinate names
        x0: initial position
        u0: initial 4-velocity
        tau_max: maximum affine parameter
        dtau: step size
        params: metric parameters
        coord_indices: which 3 coordinates to plot (default: r, theta, phi)
        title: plot title
        save_path: if set, save figure to this path
        show: if True, call plt.show()

    Returns:
        matplotlib Figure object
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    taus, states = solve_geodesic(
        metric, coord_names, x0, u0, tau_max, dtau, params=params
    )

    n = len(coord_names)
    i, j, k = coord_indices
    coords_i = states[:, i]
    coords_j = states[:, j]
    coords_k = states[:, k]

    # Check if coordinates look spherical (r, theta, phi)
    coord_set = [coord_names[idx] for idx in coord_indices]
    if 'r' in coord_set and 'theta' in coord_set and 'phi' in coord_set:
        r_idx = coord_names.index('r')
        theta_idx = coord_names.index('theta')
        phi_idx = coord_names.index('phi')
        x, y, z = _to_spherical_cartesian(
            states[:, r_idx], states[:, theta_idx], states[:, phi_idx]
        )
        axis_labels = ('x', 'y', 'z')
    else:
        x, y, z = coords_i, coords_j, coords_k
        axis_labels = (coord_names[i], coord_names[j], coord_names[k])

    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Color by affine parameter
    colors = plt.cm.viridis(np.linspace(0, 1, len(x)))
    for idx in range(len(x) - 1):
        ax.plot(x[idx:idx+2], y[idx:idx+2], z[idx:idx+2],
                color=colors[idx], linewidth=1.0)

    # Mark start and end
    ax.scatter([x[0]], [y[0]], [z[0]], c='green', s=100, marker='o',
               label='Start', zorder=5)
    ax.scatter([x[-1]], [y[-1]], [z[-1]], c='red', s=100, marker='s',
               label='End', zorder=5)

    ax.set_xlabel(axis_labels[0])
    ax.set_ylabel(axis_labels[1])
    ax.set_zlabel(axis_labels[2])
    ax.set_title(title)
    ax.legend()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()

    return fig


def plot_geodesic_components(
    metric,
    coord_names: list[str],
    x0: np.ndarray,
    u0: np.ndarray,
    tau_max: float,
    dtau: float = 0.01,
    params: dict[str, float] | None = None,
    title: str = "Geodesic Coordinate Evolution",
    save_path: str | None = None,
    show: bool = False,
) -> Any:
    """Plot each coordinate as a function of affine parameter.

    Args:
        metric: Metric object
        coord_names: coordinate names
        x0, u0: initial position and velocity
        tau_max, dtau: integration parameters
        params: metric parameters
        title: plot title
        save_path: save figure to this path
        show: if True, call plt.show()

    Returns:
        matplotlib Figure object
    """
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    taus, states = solve_geodesic(
        metric, coord_names, x0, u0, tau_max, dtau, params=params
    )

    n = len(coord_names)
    fig, axes = plt.subplots(n, 1, figsize=(10, 3 * n), sharex=True)
    if n == 1:
        axes = [axes]

    for i in range(n):
        axes[i].plot(taus, states[:, i], 'b-', linewidth=1.0)
        axes[i].set_ylabel(coord_names[i])
        axes[i].grid(True, alpha=0.3)

    axes[-1].set_xlabel('τ (affine parameter)')
    fig.suptitle(title)
    fig.tight_layout()

    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()

    return fig


def plot_schwarzschild_orbit(
    M: float = 1.0,
    r0: float = 6.0,
    tau_max: float = 100.0,
    dtau: float = 0.005,
    save_path: str | None = None,
    show: bool = False,
) -> Any:
    """Plot a Schwarzschild geodesic orbit in the equatorial plane.

    Args:
        M: black hole mass
        r0: initial orbital radius
        tau_max: integration time
        dtau: step size
        save_path: save figure to this path
        show: if True, call plt.show()

    Returns:
        matplotlib Figure object
    """
    m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
    g = geom.Metric.from_diagonal(m, [
        "-(1 - 2*M/r)",
        "(1 - 2*M/r)^(-1)",
        "r^2",
        "r^2 * sin(theta)^2",
    ])

    theta0 = np.pi / 2

    # Circular orbit velocity
    dphi_dtau = np.sqrt(M / (r0**2 * (r0 - 3 * M)))
    dt_dtau = 1.0 / np.sqrt(1 - 3 * M / r0)

    x0 = np.array([0.0, r0, theta0, 0.0])
    u0 = np.array([dt_dtau, 0.0, 0.0, dphi_dtau])

    return plot_geodesic_3d(
        g, ["t", "r", "theta", "phi"], x0, u0,
        tau_max=tau_max, dtau=dtau,
        params={"M": M},
        title=f"Schwarzschild Orbit (r₀={r0}M)",
        save_path=save_path,
        show=show,
    )


# Module-level import for convenience
geom = None
if rc is not None:
    geom = rc.geometry
