"""Central agent tool registry for ResearchLoop and GeometrySession.

Specs align with config/research-skill-mapping.json. Handlers lazy-import
via wrappers or direct module:function refs.
"""

from __future__ import annotations

import importlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Callable

from .serialize import serialize_result

_CONFIG_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "config", "research-skill-mapping.json"
)

# Alias map: historical ResearchLoop / skill names → registry tool names
ALIASES: dict[str, str] = {
    "create_blackhole": "create_schwarzschild",
    "compute_curvature": "compute_kretschmann",
    "check_energy_conditions_symbolic": "check_energy_conditions_for_metric",
    # mapping names the low-level T_components API; agent entry is ρ/p convenience
    "check_energy_conditions_numerical": "check_energy_conditions_for_metric",
}


@dataclass(frozen=True)
class ToolSpec:
    name: str
    category: str
    game_ability: str
    description: str
    params_schema: dict[str, Any]
    returns: str = "object"
    handler: str = ""
    needs_metric: bool = False
    side_effect: str = "none"
    aliases: tuple[str, ...] = field(default_factory=tuple)


def _obj(properties: dict, required: list[str] | None = None) -> dict:
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _num(desc: str, default: float | None = None) -> dict:
    d: dict[str, Any] = {"type": "number", "description": desc}
    if default is not None:
        d["default"] = default
    return d


def _str(desc: str, default: str | None = None) -> dict:
    d: dict[str, Any] = {"type": "string", "description": desc}
    if default is not None:
        d["default"] = default
    return d


def _arr(desc: str, items: dict | None = None) -> dict:
    return {
        "type": "array",
        "description": desc,
        "items": items or {"type": "number"},
    }


def _metric_props() -> dict:
    return {
        "metric_name": _str("Name of a metric already in MetricStore"),
        "diagonal": _arr("Diagonal metric components as strings (create if metric_name absent)"),
        "coords": _arr("Coordinate names", {"type": "string"}),
        "name": _str("Store name when creating from diagonal"),
        "params": {"type": "object", "description": "Metric parameters e.g. {\"M\": 1}"},
    }


_METRIC_REQ_HINT = "Provide metric_name, or diagonal+coords."


def _specs() -> list[ToolSpec]:
    """Build the curated agent tool surface."""
    S: list[ToolSpec] = []
    add = S.append

    # ── symbolic / geometry core (via wrappers over C++ bindings) ──
    add(ToolSpec(
        name="parse_expression", category="symbolic_compute", game_ability="炼算",
        description="Parse a math expression string into a symbolic expression",
        params_schema=_obj({"expression": _str("Expression string")}, ["expression"]),
        returns="Expression", handler="wrapper:parse_expression",
    ))
    add(ToolSpec(
        name="evaluate_expression", category="symbolic_compute", game_ability="炼算",
        description="Numerically evaluate a symbolic expression string at given variables",
        params_schema=_obj({
            "expression": _str("Expression string"),
            "variables": {"type": "object", "description": "Variable values"},
        }, ["expression"]),
        returns="float", handler="wrapper:evaluate_expression",
    ))
    add(ToolSpec(
        name="compute_christoffel", category="differential_geometry", game_ability="参悟",
        description="Compute Christoffel symbols Γ^μ_{νρ} for a metric",
        params_schema=_obj(_metric_props()), returns="Tensor",
        handler="wrapper:compute_christoffel", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="compute_riemann", category="differential_geometry", game_ability="参悟",
        description="Compute Riemann curvature tensor for a metric",
        params_schema=_obj(_metric_props()), returns="Tensor",
        handler="wrapper:compute_riemann", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="compute_ricci", category="differential_geometry", game_ability="参悟",
        description="Compute Ricci tensor for a metric",
        params_schema=_obj(_metric_props()), returns="Tensor",
        handler="wrapper:compute_ricci", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="compute_einstein", category="differential_geometry", game_ability="参悟",
        description="Compute Einstein tensor G_μν = R_μν - ½ g_μν R",
        params_schema=_obj(_metric_props()), returns="Tensor",
        handler="wrapper:compute_einstein", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="compute_scalar_curvature", category="differential_geometry", game_ability="参悟",
        description="Compute scalar curvature R for a metric",
        params_schema=_obj(_metric_props()), returns="Expression",
        handler="wrapper:compute_scalar_curvature", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="compute_kretschmann", category="differential_geometry", game_ability="参悟",
        description="Compute Kretschmann scalar K = R_μνρσ R^μνρσ",
        params_schema=_obj(_metric_props()), returns="Expression",
        handler="wrapper:compute_kretschmann", needs_metric=True, side_effect="store_read",
    ))

    # ── black holes ──
    add(ToolSpec(
        name="create_schwarzschild", category="blackhole_solutions", game_ability="观象",
        description="Create Schwarzschild metric and store it under a name",
        params_schema=_obj({"M": _num("Mass M", 1.0)}), returns="dict",
        handler="wrapper:create_schwarzschild", side_effect="store_put",
    ))
    add(ToolSpec(
        name="create_kerr", category="blackhole_solutions", game_ability="观象",
        description="Create Kerr (diagonal approximation) metric and store it",
        params_schema=_obj({"M": _num("Mass M", 1.0), "a": _num("Spin a", 0.5)}),
        returns="dict", handler="wrapper:create_kerr", side_effect="store_put",
    ))
    add(ToolSpec(
        name="create_reissner_nordstrom", category="blackhole_solutions", game_ability="观象",
        description="Create Reissner-Nordström metric and store it",
        params_schema=_obj({"M": _num("Mass M", 1.0), "Q": _num("Charge Q", 0.5)}),
        returns="dict", handler="wrapper:create_reissner_nordstrom", side_effect="store_put",
    ))
    add(ToolSpec(
        name="create_desitter", category="blackhole_solutions", game_ability="观象",
        description="Create de Sitter spacetime metric and store it",
        params_schema=_obj({"L": _num("Cosmological constant Λ", 1.0)}),
        returns="dict", handler="wrapper:create_desitter", side_effect="store_put",
    ))
    add(ToolSpec(
        name="analyze_horizon", category="blackhole_solutions", game_ability="观象",
        description="Analyze horizons of a stored black-hole metric",
        params_schema=_obj({**_metric_props(), "coord_name": _str("Radial coordinate", "r")}),
        returns="dict", handler="wrapper:analyze_horizon", needs_metric=True, side_effect="store_read",
    ))

    # ── geodesics ──
    add(ToolSpec(
        name="solve_geodesic", category="geodesic_solver", game_ability="推演",
        description="Numerically integrate a geodesic on a metric",
        params_schema=_obj({
            **_metric_props(),
            "x0": _arr("Initial coordinates"),
            "u0": _arr("Initial 4-velocity"),
            "tau_max": _num("Max affine parameter", 50.0),
            "dtau": _num("Step size", 0.05),
            "method": _str("Integrator", "rk4"),
        }, ["x0", "u0"]),
        returns="dict", handler="wrapper:solve_geodesic", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="christoffel_at_point", category="geodesic_solver", game_ability="推演",
        description="Evaluate Christoffel symbols at a spacetime point",
        params_schema=_obj({
            **_metric_props(),
            "point": _arr("Point coordinates", {"type": "number"}),
        }, ["point"]),
        returns="object", handler="wrapper:christoffel_at_point",
        needs_metric=True, side_effect="store_read",
        aliases=("christoffel_numerical",),
    ))

    # ── Hawking ──
    add(ToolSpec(
        name="hawking_temperature", category="hawking_radiation", game_ability="参悟",
        description="Hawking temperature for a black hole mass (kg)",
        params_schema=_obj({"M": _num("Mass in kg", 1.989e30)}, ["M"]),
        returns="dict", handler="hawking:hawking_temperature",
    ))
    add(ToolSpec(
        name="evaporation_time", category="hawking_radiation", game_ability="参悟",
        description="Black hole evaporation time for mass M (kg)",
        params_schema=_obj({"M": _num("Mass in kg", 1.989e30)}, ["M"]),
        returns="float", handler="hawking:evaporation_time",
    ))
    add(ToolSpec(
        name="bekenstein_hawking_entropy", category="hawking_radiation", game_ability="参悟",
        description="Bekenstein-Hawking entropy for mass M (kg)",
        params_schema=_obj({"M": _num("Mass in kg", 1.989e30)}, ["M"]),
        returns="float", handler="hawking:bekenstein_hawking_entropy",
    ))
    add(ToolSpec(
        name="unruh_temperature", category="hawking_radiation", game_ability="参悟",
        description="Unruh temperature for proper acceleration a",
        params_schema=_obj({"acceleration": _num("Proper acceleration m/s²", 1e10)}, ["acceleration"]),
        returns="float", handler="hawking:unruh_temperature",
    ))

    # ── lensing ──
    add(ToolSpec(
        name="deflection_angle", category="gravitational_lensing", game_ability="观象",
        description="Light deflection angle for point mass M and impact parameter b",
        params_schema=_obj({"M": _num("Mass M"), "b": _num("Impact parameter b")}, ["M", "b"]),
        returns="float", handler="lensing:deflection_angle",
    ))
    add(ToolSpec(
        name="einstein_radius", category="gravitational_lensing", game_ability="观象",
        description="Einstein ring radius from lens/source distances",
        params_schema=_obj({
            "M": _num("Lens mass M"), "D_L": _num("Distance to lens"),
            "D_S": _num("Distance to source"), "D_LS": _num("Lens-source distance"),
        }, ["M", "D_L", "D_S", "D_LS"]),
        returns="float", handler="lensing:einstein_radius",
    ))
    add(ToolSpec(
        name="image_positions", category="gravitational_lensing", game_ability="观象",
        description="Image positions for source β and Einstein radius θ_E",
        params_schema=_obj({"beta": _num("Source position β"), "theta_E": _num("θ_E")}, ["beta", "theta_E"]),
        returns="list", handler="lensing:image_positions",
    ))
    add(ToolSpec(
        name="microlensing_light_curve", category="gravitational_lensing", game_ability="观象",
        description="Microlensing light curve magnification vs time",
        params_schema=_obj({
            "t": _arr("Times"), "t_0": _num("Peak time"), "u_0": _num("Impact u0"), "t_E": _num("Einstein time"),
        }, ["t", "t_0", "u_0", "t_E"]),
        returns="list", handler="lensing:microlensing_light_curve",
    ))

    # ── GW analysis ──
    add(ToolSpec(
        name="inspiral_waveform_fd", category="wave_analysis", game_ability="推演",
        description="Frequency-domain inspiral waveform (SPA)",
        params_schema=_obj({
            "f": _arr("Frequency array"), "M_c": _num("Chirp mass"),
            "t_c": _num("Coalescence time", 0.0), "phi_c": _num("Coalescence phase", 0.0),
        }, ["f", "M_c"]),
        returns="object", handler="gw_analysis:inspiral_waveform_fd",
    ))
    add(ToolSpec(
        name="compute_horizon_distance", category="wave_analysis", game_ability="推演",
        description="Detection horizon distance for a binary inspiral",
        params_schema=_obj({
            "m1_solar": _num("Primary mass (solar)"), "m2_solar": _num("Secondary mass (solar)"),
            "snr_threshold": _num("SNR threshold", 8.0),
        }, ["m1_solar", "m2_solar"]),
        returns="float", handler="gw_analysis:compute_horizon_distance",
    ))
    add(ToolSpec(
        name="parameter_estimation_summary", category="wave_analysis", game_ability="推演",
        description="Parameter estimation summary for a GW event",
        params_schema=_obj({
            "m1_solar": _num("Primary mass"), "m2_solar": _num("Secondary mass"),
            "distance_Mpc": _num("Luminosity distance Mpc"),
        }, ["m1_solar", "m2_solar", "distance_Mpc"]),
        returns="dict", handler="gw_analysis:parameter_estimation_summary",
    ))
    add(ToolSpec(
        name="fisher_matrix", category="wave_analysis", game_ability="推演",
        description="Fisher matrix for inspiral parameters [M_c, t_c, phi_c]",
        params_schema=_obj({
            "f": _arr("Frequency array"), "M_c": _num("Chirp mass"),
            "t_c": _num("t_c", 0.0), "phi_c": _num("phi_c", 0.0),
        }, ["f", "M_c"]),
        returns="dict", handler="wrapper:fisher_matrix",
    ))
    add(ToolSpec(
        name="matched_filter_snr", category="wave_analysis", game_ability="推演",
        description="Matched-filter SNR for template vs data",
        params_schema=_obj({
            "h_template": _arr("Template waveform"), "h_data": _arr("Data"),
            "S_n": _arr("Noise PSD"), "f": _arr("Frequencies"),
        }, ["h_template", "h_data", "S_n", "f"]),
        returns="dict", handler="wrapper:matched_filter_snr",
    ))

    # ── binary evolution ──
    add(ToolSpec(
        name="chirp_mass", category="binary_evolution", game_ability="推演",
        description="Chirp mass M_c from component masses",
        params_schema=_obj({"m1": _num("m1"), "m2": _num("m2")}, ["m1", "m2"]),
        returns="float", handler="binary:chirp_mass",
    ))
    add(ToolSpec(
        name="orbital_decay_rate", category="binary_evolution", game_ability="推演",
        description="Orbital separation decay rate da/dt",
        params_schema=_obj({"a": _num("Separation a"), "m1": _num("m1"), "m2": _num("m2")}, ["a", "m1", "m2"]),
        returns="float", handler="binary:orbital_decay_rate",
    ))
    add(ToolSpec(
        name="merger_time", category="binary_evolution", game_ability="推演",
        description="Time to merger from separation a",
        params_schema=_obj({"a": _num("Separation a"), "m1": _num("m1"), "m2": _num("m2")}, ["a", "m1", "m2"]),
        returns="float", handler="binary:merger_time",
    ))
    add(ToolSpec(
        name="evolve_binary", category="binary_evolution", game_ability="推演",
        description="Evolve a binary under GW emission",
        params_schema=_obj({
            "m1_solar": _num("m1 (solar)"), "m2_solar": _num("m2 (solar)"),
            "a0_solar": _num("Initial separation (solar radii)"),
            "t_max_Gyr": _num("Max time Gyr", 1.0), "n_points": _num("Samples", 50),
        }, ["m1_solar", "m2_solar", "a0_solar"]),
        returns="dict", handler="binary:evolve_binary",
    ))

    # ── QNM ──
    add(ToolSpec(
        name="schwarzschild_qnm", category="quasinormal_modes", game_ability="参悟",
        description="Schwarzschild QNM frequency ω for (l, n, M)",
        params_schema=_obj({
            "l": _num("Angular harmonic l", 2), "n": _num("Overtone n", 0), "M": _num("Mass M", 1.0),
        }, ["l", "n"]),
        returns="complex", handler="quasinormal:schwarzschild_qnm",
    ))
    add(ToolSpec(
        name="kerr_qnm", category="quasinormal_modes", game_ability="参悟",
        description="Kerr QNM frequency for (l, n, M, a, prograde)",
        params_schema=_obj({
            "l": _num("l", 2), "n": _num("n", 0), "M": _num("M", 1.0),
            "a": _num("Spin a", 0.5), "prograde": {"type": "boolean", "default": True},
        }, ["l", "n"]),
        returns="complex", handler="quasinormal:kerr_qnm",
    ))
    add(ToolSpec(
        name="qnm_spectrum", category="quasinormal_modes", game_ability="参悟",
        description="Full QNM spectrum for a black hole",
        params_schema=_obj({
            "M": _num("M", 1.0), "a": _num("Spin a", 0.0),
            "l_max": _num("l_max", 4), "n_max": _num("n_max", 3),
        }),
        returns="dict", handler="quasinormal:qnm_spectrum",
    ))
    add(ToolSpec(
        name="ringdown_waveform", category="quasinormal_modes", game_ability="参悟",
        description="Ringdown waveform from damped sinusoid QNMs",
        params_schema=_obj({
            "M": _num("M", 1.0), "a": _num("a", 0.0), "l": _num("l", 2), "m": _num("m", 2),
            "t_max": _num("t_max", 100.0), "dt": _num("dt", 0.5),
        }, ["M"]),
        returns="dict", handler="quasinormal:ringdown_waveform",
    ))

    # ── numerical relativity ──
    add(ToolSpec(
        name="binary_merger_waveform", category="numerical_relativity", game_ability="推演",
        description="Generate BBH merger waveform (inspiral+merger+ringdown)",
        params_schema=_obj({
            "m1_solar": _num("m1", 30.0), "m2_solar": _num("m2", 30.0),
            "distance_Mpc": _num("Distance Mpc", 400.0), "f_low": _num("f_low", 20.0),
        }),
        returns="dict", handler="numerical_relativity:binary_merger_waveform",
    ))
    add(ToolSpec(
        name="simulate_merger_ringdown", category="numerical_relativity", game_ability="推演",
        description="Simulate post-merger ringdown using simplified BSSN-like evolution",
        params_schema=_obj({
            "M_total_solar": _num("Total mass", 60.0), "eta": _num("Symmetric mass ratio", 0.25),
            "n_steps": _num("Steps", 100), "dt_code": _num("dt", 0.5),
        }),
        returns="dict", handler="numerical_relativity:simulate_merger_ringdown",
    ))

    # ── cosmology ──
    add(ToolSpec(
        name="solve_friedmann", category="cosmology", game_ability="观象",
        description="Solve the Friedmann equation for a(t)",
        params_schema=_obj({
            "params": {"type": "object", "description": "Cosmological parameters", "default": {}},
            "a_start": _num("a start", 1e-3), "a_end": _num("a end", 1.0),
            "n_points": _num("samples", 50),
        }),
        returns="dict", handler="cosmology:solve_friedmann",
    ))
    add(ToolSpec(
        name="age_of_universe", category="cosmology", game_ability="观象",
        description="Age of the universe for given cosmological parameters",
        params_schema=_obj({"params": {"type": "object", "default": {}}}),
        returns="dict", handler="cosmology:age_of_universe",
    ))
    add(ToolSpec(
        name="cosmological_distances", category="cosmology", game_ability="观象",
        description="Cosmological distances at redshift z",
        params_schema=_obj({
            "z": _num("Redshift z"), "params": {"type": "object", "default": {}},
        }, ["z"]),
        returns="dict", handler="cosmology:cosmological_distances",
    ))
    add(ToolSpec(
        name="hubble_parameter", category="cosmology", game_ability="观象",
        description="Hubble parameter H(a) in km/s/Mpc",
        params_schema=_obj({
            "a": _num("Scale factor a", 1.0), "params": {"type": "object", "default": {}},
        }, ["a"]),
        returns="float", handler="cosmology:hubble_parameter",
    ))
    add(ToolSpec(
        name="flrw_metric_symbolic", category="cosmology", game_ability="观象",
        description="Symbolic FLRW metric diagonal components (stored as named metric)",
        params_schema=_obj({"k": _num("Spatial curvature k ∈ {-1,0,1}", 0.0)}),
        returns="dict", handler="wrapper:flrw_metric_symbolic", side_effect="store_put",
    ))

    # ── inflation ──
    add(ToolSpec(
        name="slow_roll_parameters", category="inflation", game_ability="参悟",
        description="Slow-roll parameters ε, η for a named potential at field φ",
        params_schema=_obj({
            "potential": _str("chaotic | starobinsky | higgs", "chaotic"),
            "phi": _num("Field value", 1.0),
        }, ["potential", "phi"]),
        returns="dict", handler="wrapper:slow_roll_parameters",
    ))
    add(ToolSpec(
        name="number_of_efolds", category="inflation", game_ability="参悟",
        description="Number of e-folds between two field values for a named potential",
        params_schema=_obj({
            "potential": _str("chaotic | starobinsky | higgs", "chaotic"),
            "phi_start": _num("φ start"), "phi_end": _num("φ end"),
        }, ["potential", "phi_start", "phi_end"]),
        returns="float", handler="wrapper:number_of_efolds",
    ))
    add(ToolSpec(
        name="inflationary_observables", category="inflation", game_ability="参悟",
        description="Compute n_s, r, N for a named potential",
        params_schema=_obj({
            "potential": _str("chaotic | starobinsky | higgs", "chaotic"),
            "phi_start": _num("φ start", 15.0),
        }, ["potential"]),
        returns="dict", handler="wrapper:inflationary_observables",
    ))
    add(ToolSpec(
        name="primordial_scalar_power_spectrum", category="inflation", game_ability="参悟",
        description="Primordial scalar power spectrum P_ζ(k)",
        params_schema=_obj({
            "k": _arr("Wavenumber array"), "A_s": _num("Amplitude", 2.1e-9),
            "n_s": _num("Spectral index", 0.965),
        }, ["k"]),
        returns="dict", handler="inflation:primordial_scalar_power_spectrum",
    ))

    # ── CMB ──
    add(ToolSpec(
        name="cmb_power_spectrum", category="cmb_anisotropy", game_ability="观象",
        description="CMB temperature angular power spectrum D_ℓ",
        params_schema=_obj({
            "ell_max": _num("ℓ max", 200), "Omega_m": _num("Ω_m", 0.315),
            "Omega_b": _num("Ω_b", 0.049), "h": _num("h", 0.674),
            "n_s": _num("n_s", 0.965),
        }),
        returns="dict", handler="cmb:cmb_power_spectrum",
    ))
    add(ToolSpec(
        name="acoustic_scale", category="cmb_anisotropy", game_ability="观象",
        description="CMB acoustic scale ℓ_A",
        params_schema=_obj({"Omega_m": _num("Ω_m", 0.315), "h": _num("h", 0.674)}),
        returns="float", handler="cmb:acoustic_scale",
    ))
    add(ToolSpec(
        name="peak_positions", category="cmb_anisotropy", game_ability="观象",
        description="Acoustic peak multipole positions",
        params_schema=_obj({"Omega_m": _num("Ω_m", 0.315), "h": _num("h", 0.674)}),
        returns="list", handler="cmb:peak_positions",
    ))
    add(ToolSpec(
        name="cmb_observables", category="cmb_anisotropy", game_ability="观象",
        description="Key CMB observables summary",
        params_schema=_obj({
            "Omega_m": _num("Ω_m", 0.315), "Omega_b": _num("Ω_b", 0.049), "h": _num("h", 0.674),
        }),
        returns="dict", handler="cmb:cmb_observables",
    ))

    # ── dark energy ──
    add(ToolSpec(
        name="w_cpl", category="dark_energy", game_ability="参悟",
        description="CPL dark energy equation of state w(z)",
        params_schema=_obj({
            "z": _num("Redshift"), "w0": _num("w0", -1.0), "wa": _num("wa", 0.0),
        }, ["z"]),
        returns="float", handler="dark_energy:w_cpl",
    ))
    add(ToolSpec(
        name="dark_energy_density", category="dark_energy", game_ability="参悟",
        description="Dark energy density at redshift z (CPL)",
        params_schema=_obj({
            "z": _num("Redshift"), "w0": _num("w0", -1.0), "wa": _num("wa", 0.0),
        }, ["z"]),
        returns="float", handler="dark_energy:dark_energy_density",
    ))
    add(ToolSpec(
        name="deceleration_parameter", category="dark_energy", game_ability="参悟",
        description="Deceleration parameter q(z) for ΛCDM-like model",
        params_schema=_obj({
            "z": _num("Redshift", 0.0), "Omega_m": _num("Ω_m", 0.315), "w0": _num("w0", -1.0),
        }),
        returns="float", handler="dark_energy:deceleration_parameter",
    ))
    add(ToolSpec(
        name="f_R_cosmology", category="dark_energy", game_ability="参悟",
        description="Solve Friedmann equation in f(R) = R + f0 R^n gravity",
        params_schema=_obj({
            "a_values": _arr("Scale factors"), "f0": _num("f0", 1e-3), "n": _num("n", 2.0),
            "H0": _num("H0", 67.4), "Omega_m": _num("Ω_m", 0.315),
        }, ["a_values"]),
        returns="dict", handler="dark_energy:f_R_cosmology",
    ))

    # ── perturbation / GW micro ──
    add(ToolSpec(
        name="solve_regge_wheeler", category="perturbation_theory", game_ability="推演",
        description="Solve Regge-Wheeler equation numerically",
        params_schema=_obj({
            "M": _num("M", 1.0), "l": _num("l", 2), "omega": _num("ω", 0.37),
        }, ["M", "l", "omega"]),
        returns="dict", handler="perturbation_eqns:solve_regge_wheeler",
    ))
    add(ToolSpec(
        name="solve_zerilli", category="perturbation_theory", game_ability="推演",
        description="Solve Zerilli equation numerically",
        params_schema=_obj({
            "M": _num("M", 1.0), "l": _num("l", 2), "omega": _num("ω", 0.37),
        }, ["M", "l", "omega"]),
        returns="dict", handler="perturbation_eqns:solve_zerilli",
    ))
    add(ToolSpec(
        name="compute_gw_strain", category="perturbation_theory", game_ability="推演",
        description="GW strain h(t) from QNM parameters",
        params_schema=_obj({
            "M": _num("M", 1.0), "l": _num("l", 2), "m": _num("m", 2),
            "omega": _num("ω complex as {re, im} or float", 0.37),
            "r_obs": _num("Observer distance", 100.0),
        }, ["M", "omega"]),
        returns="dict", handler="perturbation_eqns:compute_gw_strain",
    ))
    add(ToolSpec(
        name="growth_factor", category="perturbation_theory", game_ability="推演",
        description="Linear growth factor D(a)",
        params_schema=_obj({
            "a_values": _arr("Scale factor samples"),
            "Omega_m": _num("Ω_m", 0.315), "Omega_Lambda": _num("Ω_Λ", 0.685),
        }, ["a_values"]),
        returns="list", handler="cosmo_perturbation:growth_factor",
    ))
    add(ToolSpec(
        name="matter_power_spectrum", category="perturbation_theory", game_ability="推演",
        description="Linear matter power spectrum P(k)",
        params_schema=_obj({
            "k": _arr("k samples"), "a": _num("a", 1.0), "n_s": _num("n_s", 0.965),
            "sigma_8": _num("σ8", 0.811), "Omega_m": _num("Ω_m", 0.315), "h": _num("h", 0.674),
        }, ["k"]),
        returns="list", handler="cosmo_perturbation:matter_power_spectrum",
    ))

    # ── killing / energy ──
    add(ToolSpec(
        name="classify_symmetry", category="killing_symmetry", game_ability="参悟",
        description="Classify spacetime symmetry from Killing vectors",
        params_schema=_obj(_metric_props()), returns="dict",
        handler="wrapper:classify_symmetry", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="detect_coordinate_killing_vectors", category="killing_symmetry", game_ability="参悟",
        description="Test each coordinate basis vector as a Killing candidate",
        params_schema=_obj(_metric_props()), returns="dict",
        handler="wrapper:detect_coordinate_killing_vectors", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="is_killing_vector", category="killing_symmetry", game_ability="参悟",
        description="Check whether ξ is a Killing vector",
        params_schema=_obj({
            **_metric_props(),
            "xi_components": _arr("Killing vector components", {"type": "string"}),
            "tol": _num("Tolerance", 1e-6),
        }, ["xi_components"]),
        returns="boolean", handler="wrapper:is_killing_vector", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="check_energy_conditions_for_metric", category="energy_conditions", game_ability="参悟",
        description="Check WEC/SEC/DEC/NEC for perfect fluid ρ, p on a metric",
        params_schema=_obj({
            **_metric_props(),
            "rho_expr": _str("Energy density expression", "1/r^2"),
            "p_expr": _str("Pressure expression", "0"),
            "test_points": _arr("Test points as objects with coordinate values", {"type": "object"}),
        }),
        returns="dict", handler="wrapper:check_energy_conditions_for_metric",
        needs_metric=True, side_effect="store_read",
    ))

    # ── neutron star ──
    add(ToolSpec(
        name="solve_tov", category="neutron_star", game_ability="观象",
        description="Solve TOV equations for central density ρ_c",
        params_schema=_obj({
            "rho_c": _num("Central density kg/m³", 1e17), "eos": _str("EOS name", "sly4"),
        }, ["rho_c"]),
        returns="dict", handler="wrapper:solve_tov",
    ))
    add(ToolSpec(
        name="mass_radius_relation", category="neutron_star", game_ability="观象",
        description="Neutron star mass-radius relation for an EOS",
        params_schema=_obj({
            "eos": _str("EOS name", "sly4"),
            "n_points": _num("Number of models", 10),
        }),
        returns="dict", handler="wrapper:mass_radius_relation",
    ))
    add(ToolSpec(
        name="tidal_deformability", category="neutron_star", game_ability="观象",
        description="Estimate tidal deformability Λ",
        params_schema=_obj({
            "M_solar": _num("Mass (solar)"), "R_km": _num("Radius km"), "k2": _num("Love number", 0.05),
        }, ["M_solar", "R_km"]),
        returns="float", handler="neutron_star:tidal_deformability",
    ))

    # ── B: new modules ──
    add(ToolSpec(
        name="classify_vector", category="causal_structure", game_ability="观象",
        description="Classify a tangent vector as timelike/null/spacelike",
        params_schema=_obj({**_metric_props(), "tangent": _arr("Tangent components")}, ["tangent"]),
        returns="str", handler="wrapper:classify_vector", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="light_cone_at_point", category="causal_structure", game_ability="观象",
        description="Light-cone structure at a spacetime point",
        params_schema=_obj({
            **_metric_props(), "point": _arr("Spacetime point"), "n_rays": _num("Rays", 8),
        }, ["point"]),
        returns="dict", handler="wrapper:light_cone_at_point", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="singularity_analysis", category="causal_structure", game_ability="观象",
        description="Locate curvature singularities via invariant divergence",
        params_schema=_obj(_metric_props()), returns="dict",
        handler="wrapper:singularity_analysis", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="field_equation_residual_numerical", category="field_equations", game_ability="参悟",
        description="Numerical Einstein tensor / field-equation residual at a point",
        params_schema=_obj({
            **_metric_props(),
            "coord_values": _arr("Coordinate point"),
        }),
        returns="dict", handler="wrapper:field_equation_residual_numerical",
        needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="build_tetrad_diagonal", category="tetrad", game_ability="炼算",
        description="Build orthonormal tetrad for a diagonal metric",
        params_schema=_obj(_metric_props()), returns="object",
        handler="wrapper:build_tetrad_diagonal", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="classify_petrov_type", category="newman_penrose", game_ability="参悟",
        description="Petrov classification via Weyl scalars for a stored metric",
        params_schema=_obj(_metric_props()), returns="str",
        handler="wrapper:classify_petrov_type", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="perihelion_advance", category="post_newtonian", game_ability="推演",
        description="1PN perihelion advance per orbit",
        params_schema=_obj({
            "M": _num("Central mass M"), "a": _num("Semi-major a"), "e": _num("Eccentricity e"),
        }, ["M", "a", "e"]),
        returns="float", handler="post_newtonian:perihelion_advance",
    ))
    add(ToolSpec(
        name="pn_energy_1pn", category="post_newtonian", game_ability="推演",
        description="1PN orbital energy",
        params_schema=_obj({
            "M": _num("Total mass M"), "m": _num("Reduced or test mass m"), "a": _num("a"), "e": _num("e", 0.0),
        }, ["M", "m", "a"]),
        returns="float", handler="post_newtonian:pn_energy_1pn",
    ))
    add(ToolSpec(
        name="gravitational_wave_flux_quadrupole", category="post_newtonian", game_ability="推演",
        description="Leading-order GW flux (quadrupole formula)",
        params_schema=_obj({
            "M": _num("Total mass"), "m": _num("m"), "a": _num("a"),
        }, ["M", "m", "a"]),
        returns="float", handler="post_newtonian:gravitational_wave_flux_quadrupole",
    ))
    add(ToolSpec(
        name="linearized_riemann", category="linearized_gravity", game_ability="推演",
        description="Linearized Riemann tensor for perturbation h on a background metric",
        params_schema=_obj({
            **_metric_props(),
            "h_components": _arr("Perturbation h_μν as nested string lists", {"type": "array"}),
        }, ["h_components"]),
        returns="object", handler="wrapper:linearized_riemann",
        needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="bssn_variables", category="adm_bssn", game_ability="推演",
        description="Extract BSSN variables from a 3-metric",
        params_schema=_obj(_metric_props()), returns="dict",
        handler="wrapper:bssn_variables", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="extract_adm_static", category="adm_bssn", game_ability="推演",
        description="Extract ADM quantities for a static diagonal metric",
        params_schema=_obj(_metric_props()), returns="dict",
        handler="wrapper:extract_adm_static", needs_metric=True, side_effect="store_read",
    ))
    add(ToolSpec(
        name="hamiltonian_constraint_static", category="adm_bssn", game_ability="推演",
        description="Evaluate static Hamiltonian constraint",
        params_schema=_obj(_metric_props()), returns="object",
        handler="wrapper:hamiltonian_constraint_static", needs_metric=True, side_effect="store_read",
    ))

    # L5 — agent mathematical foundations (process metrics, not world physics)
    add(ToolSpec(
        name="trajectory_metrics", category="agent_foundations", game_ability="参悟",
        description="Shannon entropy / diversity / repair load of a tool sequence",
        params_schema=_obj({
            "tool_seq": _arr("Ordered tool names used", {"type": "string"}),
            "n_success": _num("Successful hypotheses", 1),
            "n_fail": _num("Failed hypotheses", 0),
            "n_replans": _num("Repair count", 0),
        }, ["tool_seq"]),
        returns="dict", handler="agent_math:trajectory_metrics",
    ))
    add(ToolSpec(
        name="shannon_entropy_bits", category="agent_foundations", game_ability="参悟",
        description="Shannon entropy in bits of a discrete count distribution",
        params_schema=_obj({
            "counts": _arr("Counts", {"type": "number"}),
        }, ["counts"]),
        returns="float", handler="agent_math:shannon_entropy",
    ))
    add(ToolSpec(
        name="state_distance", category="agent_foundations", game_ability="参悟",
        description="L2 distance between two MetricStore fingerprints",
        params_schema=_obj({
            "s1": {"type": "object", "description": "snapshot 1"},
            "s2": {"type": "object", "description": "snapshot 2"},
        }, ["s1", "s2"]),
        returns="float", handler="agent_math:state_distance",
    ))
    add(ToolSpec(
        name="sweep_information", category="agent_foundations", game_ability="参悟",
        description="Information content of a sweep trend (spread bits, certainty, power-law)",
        params_schema=_obj({
            "trend": {"type": "object", "description": "trend dict from summarize_trend"},
        }, ["trend"]),
        returns="dict", handler="agent_math:sweep_information",
    ))
    add(ToolSpec(
        name="rank_hypotheses", category="agent_foundations", game_ability="参悟",
        description="Score and rank hypothesis results best-first",
        params_schema=_obj({
            "results": {
                "type": "array",
                "description": "List of ResearchLoop result dicts",
                "items": {"type": "object"},
            },
        }, ["results"]),
        returns="list", handler="agent_math:rank_hypotheses",
    ))

    return S


_registry: dict[str, ToolSpec] | None = None
_alias_to_name: dict[str, str] | None = None


def build_registry() -> dict[str, ToolSpec]:
    global _registry, _alias_to_name
    if _registry is None:
        specs = _specs()
        _registry = {t.name: t for t in specs}
        _alias_to_name = dict(ALIASES)
        for t in specs:
            for a in t.aliases:
                _alias_to_name[a] = t.name
        for n in _registry:
            _alias_to_name.setdefault(n, n)
    return _registry


def resolve_tool_name(name: str) -> str:
    build_registry()
    assert _alias_to_name is not None
    if name in _registry:
        return name
    if name in _alias_to_name:
        return _alias_to_name[name]
    raise KeyError(f"unknown tool: {name}")


def get_tool_specs() -> list[ToolSpec]:
    return list(build_registry().values())


def get_handler(name: str) -> Callable[..., Any]:
    resolved = resolve_tool_name(name)
    spec = build_registry()[resolved]
    if not spec.handler:
        raise ValueError(f"tool {name} has no handler")
    if spec.handler.startswith("wrapper:"):
        from . import tool_registry_wrappers as w

        return getattr(w, spec.handler.split(":", 1)[1])
    mod_name, fn_name = spec.handler.split(":", 1)
    mod = importlib.import_module(f"orchestrator.{mod_name}")
    return getattr(mod, fn_name)


def get_handler_map() -> dict[str, Callable[..., Any]]:
    """Map of registry names + aliases → callables (for ResearchLoop)."""
    build_registry()
    out: dict[str, Callable[..., Any]] = {}
    for name in build_registry():
        out[name] = get_handler(name)
    assert _alias_to_name is not None
    for alias, target in _alias_to_name.items():
        if alias not in out:
            out[alias] = get_handler(target)
    return out


def execute_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    """Execute a registry tool by (possibly aliased) name."""
    fn = get_handler(name)
    args = dict(arguments or {})
    try:
        result = fn(**args)
    except TypeError:
        # drop unexpected keys for modules with fixed signatures
        import inspect

        sig = inspect.signature(fn)
        if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
            raise
        filtered = {k: v for k, v in args.items() if k in sig.parameters}
        result = fn(**filtered)
    return result


def openai_tools_payload(max_tools: int | None = None) -> list[dict]:
    """OpenAI function-calling payload derived from ToolSpecs."""
    specs = get_tool_specs()
    if max_tools is not None:
        specs = specs[:max_tools]
    payload = []
    for t in specs:
        payload.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.params_schema,
            },
        })
    return payload


def registry_summary() -> dict[str, Any]:
    by_cat: dict[str, int] = {}
    for t in get_tool_specs():
        by_cat[t.category] = by_cat.get(t.category, 0) + 1
    return {
        "count": len(build_registry()),
        "by_category": by_cat,
        "names": sorted(build_registry()),
    }
