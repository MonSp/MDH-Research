"""Gravitational lensing (T36).

Tools for computing gravitational lensing effects:
- Light deflection angle
- Einstein ring radius
- Microlensing light curves
- Lens equation and image positions
- Magnification
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

G = 6.67430e-11
c = 299792458.0
M_sun = 1.98892e30
parsec = 3.0857e16


def deflection_angle(M: float, b: float) -> float:
    """Compute light deflection angle for a point mass.

    α = 4GM / (bc²)

    Args:
        M: lens mass in kg
        b: impact parameter in meters

    Returns:
        Deflection angle in radians
    """
    return 4 * G * M / (b * c**2)


def einstein_radius(M: float, D_L: float, D_S: float, D_LS: float) -> dict[str, float]:
    """Compute Einstein ring radius.

    θ_E² = (4GM/c²) × (D_LS / (D_L × D_S))

    Args:
        M: lens mass in kg
        D_L: distance to lens in meters
        D_S: distance to source in meters
        D_LS: distance from lens to source in meters

    Returns:
        Dict with Einstein radius in radians, arcsec, and physical size.
    """
    theta_E_sq = (4 * G * M / c**2) * (D_LS / (D_L * D_S))
    theta_E = np.sqrt(theta_E_sq) if theta_E_sq > 0 else 0.0

    # Physical Einstein radius
    R_E = theta_E * D_L

    return {
        "theta_E_rad": theta_E,
        "theta_E_arcsec": np.degrees(theta_E) * 3600,
        "R_E_m": R_E,
        "R_E_AU": R_E / 1.496e11,
    }


def lens_equation(theta: float, theta_E: float) -> float:
    """Solve the lens equation for image position.

    β = θ - θ_E²/θ

    where β is the source position and θ is the image position.

    Args:
        theta: image angular position (radians)
        theta_E: Einstein radius (radians)

    Returns:
        Source position β (radians)
    """
    return theta - theta_E**2 / theta if theta != 0 else float('inf')


def image_positions(beta: float, theta_E: float) -> dict[str, Any]:
    """Compute image positions for a given source position.

    θ± = (β ± √(β² + 4θ_E²)) / 2

    Args:
        beta: source angular position (radians)
        theta_E: Einstein radius (radians)

    Returns:
        Dict with image positions and magnifications.
    """
    discriminant = beta**2 + 4 * theta_E**2
    if discriminant < 0:
        return {"theta_plus": None, "theta_minus": None}

    theta_plus = (beta + np.sqrt(discriminant)) / 2
    theta_minus = (beta - np.sqrt(discriminant)) / 2

    # Magnifications
    mu_plus = magnification(theta_plus, theta_E)
    mu_minus = magnification(theta_minus, theta_E)
    mu_total = abs(mu_plus) + abs(mu_minus)

    return {
        "theta_plus": theta_plus,
        "theta_minus": theta_minus,
        "mu_plus": mu_plus,
        "mu_minus": mu_minus,
        "mu_total": mu_total,
        "n_images": 2 if theta_minus != 0 else 1,
    }


def magnification(theta: float, theta_E: float) -> float:
    """Compute magnification for an image at position θ.

    μ = 1 / (1 - (θ_E/θ)⁴)

    Args:
        theta: image angular position
        theta_E: Einstein radius

    Returns:
        Magnification (can be negative for parity inversion)
    """
    if theta == 0:
        return float('inf')
    u = theta_E / theta
    denom = 1 - u**4
    if abs(denom) < 1e-15:
        return float('inf')
    return 1 / denom


def point_source_magnification(u: float) -> float:
    """Magnification for a point source at normalized distance u = β/θ_E.

    μ = (u² + 2) / (u √(u² + 4))

    Args:
        u: normalized impact parameter β/θ_E

    Returns:
        Total magnification
    """
    if u == 0:
        return float('inf')
    return (u**2 + 2) / (u * np.sqrt(u**2 + 4))


def einstein_radius_solar_mass(M_solar: float, z_L: float = 0.5, z_S: float = 2.0) -> dict[str, float]:
    """Einstein radius for a solar-mass lens at cosmological distances.

    Uses simplified distance-redshift relation.

    Args:
        M_solar: lens mass in solar masses
        z_L: lens redshift
        z_S: source redshift

    Returns:
        Dict with Einstein radius in various units.
    """
    M = M_solar * M_sun

    # Simplified angular diameter distances (flat universe)
    # D_A(z) ≈ (c/H₀) × z / (1+z) for small z
    H0 = 67.4 * 1e3 / (3.0857e22)  # 1/s
    D_L = c * z_L / (H0 * (1 + z_L))
    D_S = c * z_S / (H0 * (1 + z_S))
    D_LS = D_S - D_L  # simplified

    return einstein_radius(M, D_L, D_S, D_LS)


def microlensing_light_curve(
    t: np.ndarray,
    t_0: float = 0.0,
    u_0: float = 0.1,
    t_E: float = 10.0,
) -> dict[str, Any]:
    """Compute microlensing light curve.

    u(t) = √(u₀² + ((t-t₀)/t_E)²)
    μ(t) = (u² + 2) / (u √(u² + 4))

    Args:
        t: time array (days)
        t_0: time of closest approach
        u_0: minimum impact parameter (in units of θ_E)
        t_E: Einstein crossing time (days)

    Returns:
        Dict with time, impact parameter, magnification, and flux.
    """
    u = np.sqrt(u_0**2 + ((t - t_0) / t_E)**2)

    # Magnification
    mu = np.where(u > 1e-10, (u**2 + 2) / (u * np.sqrt(u**2 + 4)), np.inf)

    # Flux (normalized)
    flux = mu  # F = μ × F_source, with F_source = 1

    # Magnitude shift
    delta_mag = -2.5 * np.log10(mu) if np.all(mu > 0) else np.zeros_like(mu)

    return {
        "t": t,
        "u": u,
        "magnification": mu,
        "flux": flux,
        "delta_mag": delta_mag,
        "peak_magnification": np.max(mu[np.isfinite(mu)]),
        "t_0": t_0,
        "u_0": u_0,
        "t_E": t_E,
    }


def einstein_ring_image(M_solar: float = 1e11, z_L: float = 0.5, z_S: float = 2.0) -> dict[str, Any]:
    """Generate an Einstein ring image description.

    Args:
        M_solar: lens mass in solar masses (galaxy-scale)
        z_L: lens redshift
        z_S: source redshift

    Returns:
        Dict with ring parameters and image description.
    """
    er = einstein_radius_solar_mass(M_solar, z_L, z_S)

    # For a perfect alignment (β=0), the image is a ring
    return {
        "einstein_radius_arcsec": er["theta_E_arcsec"],
        "einstein_radius_rad": er["theta_E_rad"],
        "ring_type": "Einstein ring" if er["theta_E_arcsec"] > 0 else "no ring",
        "n_images": 2,  # degenerate ring = 2 merged images
        "magnification": float('inf'),  # point source at perfect alignment
        "M_solar": M_solar,
        "z_L": z_L,
        "z_S": z_S,
    }
