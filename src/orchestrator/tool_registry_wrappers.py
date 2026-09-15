"""Metric-aware and core tool wrappers for the agent registry."""

from __future__ import annotations

from typing import Any

from .metric_store import get_store
from .serialize import serialize_result


def _metric_from_args(arguments: dict[str, Any]):
    store = get_store()
    name = store.resolve_or_create(arguments)
    return name, store.get(name)


def _merged_params(entry_params: dict, override: dict | None) -> dict:
    return {**(entry_params or {}), **(override or {})}


def _factory(factory_name: str, **kwargs):
    from . import blackholes

    solution = getattr(blackholes, factory_name)(**kwargs)
    store = get_store()
    store_key = store.register_solution(solution)
    payload = serialize_result(solution)
    payload["metric_name"] = store_key
    return payload


def create_schwarzschild(M: float = 1.0):
    return _factory("create_schwarzschild", M=M)


def create_kerr(M: float = 1.0, a: float = 0.5):
    return _factory("create_kerr", M=M, a=a)


def create_reissner_nordstrom(M: float = 1.0, Q: float = 0.5):
    return _factory("create_reissner_nordstrom", M=M, Q=Q)


def create_desitter(L: float = 1.0):
    return _factory("create_desitter", L=L)


def solve_geodesic(
    x0: list | None = None,
    u0: list | None = None,
    tau_max: float = 50.0,
    dtau: float = 0.05,
    method: str = "rk4",
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    import numpy as np

    from .geodesic import solve_geodesic as _sg

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    taus, states = _sg(
        entry["metric"],
        entry["coord_names"],
        np.array(x0 or [0, 10, 1.57, 0], dtype=float),
        np.array(u0 or [1, 0, 0, 0.03], dtype=float),
        tau_max=tau_max,
        dtau=dtau,
        method=method,
        params=_merged_params(entry["params"], params),
    )
    return {"taus": taus.tolist(), "states": states.tolist()}


def analyze_horizon(
    coord_name: str = "r",
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .blackholes import analyze_horizon as _ah

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    bh = {
        "metric": entry["metric"],
        "manifold": entry["manifold"],
        "coord_names": entry["coord_names"],
        "params": _merged_params(entry["params"], params),
    }
    return serialize_result(_ah(bh, coord_name))


def classify_symmetry(
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .killing import classify_symmetry as _cs

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return serialize_result(
        _cs(entry["metric"], entry["coord_names"], _merged_params(entry["params"], params))
    )


def detect_coordinate_killing_vectors(
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .killing import detect_coordinate_killing_vectors as _dk

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return serialize_result(
        _dk(entry["metric"], entry["coord_names"], _merged_params(entry["params"], params))
    )


def is_killing_vector(
    xi_components: list,
    tol: float = 1e-6,
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .killing import is_killing_vector as _ik

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return bool(
        _ik(
            entry["metric"],
            entry["coord_names"],
            xi_components,
            _merged_params(entry["params"], params),
            tol=tol,
        )
    )


def check_energy_conditions_for_metric(
    rho_expr: str = "0",
    p_expr: str = "0",
    test_points: list | None = None,
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .energy_conditions import check_energy_conditions_for_metric as _ck

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return serialize_result(
        _ck(
            entry["metric"],
            entry["coord_names"],
            rho_expr,
            p_expr,
            test_points or [{"r": 6.0}],
            _merged_params(entry["params"], params),
        )
    )


def field_equation_residual_numerical(
    coord_values: list | None = None,
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .field_equations import field_equation_residual_numerical as _fe

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return serialize_result(
        _fe(
            entry["metric"],
            entry["coord_names"],
            coord_values or [0, 6.0, 1.57, 0],
            _merged_params(entry["params"], params),
        )
    )


def classify_petrov_type(
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .newman_penrose import (
        classify_petrov_type as _cp,
        compute_weyl_scalars_from_riemann,
    )

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    metric = entry["metric"]
    coord_names = entry["coord_names"]
    p = _merged_params(entry["params"], params)
    R = metric.riemann_tensor()
    n = metric.dimension()
    # Tensor.at() returns Expression; build nested lists for NP helpers
    R_nested = [[[[R.at([mu, nu, rho, sigma]) for sigma in range(n)]
                  for rho in range(n)] for nu in range(n)] for mu in range(n)]
    weyl = compute_weyl_scalars_from_riemann(R_nested, metric, coord_names, p)
    return serialize_result(_cp(weyl))


def build_tetrad_diagonal(
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .tetrad import build_tetrad_diagonal as _bt

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return serialize_result(_bt(entry["metric"], entry["coord_names"]))


def classify_vector(
    tangent: list,
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .causal import classify_vector as _cv

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return serialize_result(
        _cv(
            entry["metric"],
            entry["coord_names"],
            tangent,
            _merged_params(entry["params"], params),
        )
    )


def light_cone_at_point(
    point: list,
    n_rays: int = 8,
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .causal import light_cone_at_point as _lc

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return serialize_result(
        _lc(
            entry["metric"],
            entry["coord_names"],
            point,
            _merged_params(entry["params"], params),
            n_rays=n_rays,
        )
    )


def singularity_analysis(
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .causal import singularity_analysis as _sa

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return serialize_result(
        _sa(entry["metric"], entry["coord_names"], _merged_params(entry["params"], params))
    )


def bssn_variables(
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .bssn import bssn_variables as _bv

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return serialize_result(_bv(entry["metric"], entry["coord_names"]))


def extract_adm_static(
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .adm import extract_adm_static as _ea

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return serialize_result(_ea(entry["metric"], entry["coord_names"]))


def hamiltonian_constraint_static(
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .adm import hamiltonian_constraint_static as _hc

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return serialize_result(_hc(entry["metric"], entry["coord_names"]))


def compute_scalar_curvature(
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return entry["metric"].scalar_curvature()


def compute_kretschmann(
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return entry["metric"].kretschmann_scalar()


def compute_christoffel(
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return entry["metric"].christoffel_symbols()


def compute_riemann(
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return entry["metric"].riemann_tensor()


def compute_ricci(
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return entry["metric"].ricci_tensor()


def compute_einstein(
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return entry["metric"].einstein_tensor()


def parse_expression(expression: str):
    import _research_core as rc

    return rc.symbol.parse(expression)


def evaluate_expression(expression: str, variables: dict[str, float] | None = None):
    import _research_core as rc

    return float(rc.symbol.parse(expression).evaluate(variables or {}))


def flrw_metric_symbolic(k: float = 0.0):
    from .cosmology import flrw_metric_symbolic as _flrw

    result = _flrw(k)
    if isinstance(result, (list, tuple)):
        store = get_store()
        name = f"flrw_k{k}"
        coords = ["t", "r", "theta", "phi"]
        import _research_core as rc

        m = rc.geometry.Manifold(name, coords)
        g = rc.geometry.Metric.from_diagonal(m, [str(x) for x in result])
        store.put(name, g, m, coords, {"k": k})
        return {"metric_name": name, "diagonal": [str(x) for x in result], "coords": coords}
    return serialize_result(result)


def linearized_riemann(
    h_components: list,
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    from .perturbation import linearized_riemann as _lr

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return serialize_result(
        _lr(entry["metric"], entry["coord_names"], h_components, params or entry["params"])
    )


def christoffel_at_point(
    point: list,
    metric_name: str | None = None,
    diagonal: list | None = None,
    coords: list | None = None,
    params: dict | None = None,
    name: str | None = None,
):
    """Evaluate all Christoffel symbols at a single spacetime point."""
    from .geodesic import christoffel_at_point as _cap

    _, entry = _metric_from_args(
        {
            "metric_name": metric_name,
            "diagonal": diagonal,
            "coords": coords,
            "params": params or {},
            "name": name,
        }
    )
    return serialize_result(
        _cap(
            entry["metric"],
            entry["coord_names"],
            point,
            _merged_params(entry["params"], params),
        )
    )


def _resolve_potential(potential: str, **params):
    from . import inflation as inf

    factories = {
        "chaotic": inf.chaotic_potential,
        "starobinsky": inf.starobinsky_potential,
        "higgs": inf.higgs_potential,
    }
    fn = factories.get(str(potential).lower())
    if fn is None:
        raise ValueError(f"unknown potential: {potential}; use chaotic|starobinsky|higgs")
    return fn(**params) if params else fn()


def slow_roll_parameters(
    potential: str = "chaotic",
    phi: float = 1.0,
    m: float = 1e-5,
    Lambda: float = 1e-3,
    lam: float = 0.1,
):
    from .inflation import slow_roll_parameters as _sr

    if potential == "chaotic":
        V = _resolve_potential("chaotic", m=m)
    elif potential == "starobinsky":
        V = _resolve_potential("starobinsky", Lambda=Lambda)
    else:
        V = _resolve_potential("higgs", lam=lam)
    return serialize_result(_sr(V, phi))


def inflationary_observables(
    potential: str = "chaotic",
    phi_start: float = 15.0,
    m: float = 1e-5,
    Lambda: float = 1e-3,
    lam: float = 0.1,
):
    from .inflation import inflationary_observables as _io

    if potential == "chaotic":
        V = _resolve_potential("chaotic", m=m)
    elif potential == "starobinsky":
        V = _resolve_potential("starobinsky", Lambda=Lambda)
    else:
        V = _resolve_potential("higgs", lam=lam)
    return serialize_result(_io(V, phi_start))


def number_of_efolds(
    potential: str = "chaotic",
    phi_start: float = 15.0,
    phi_end: float = 5.0,
    m: float = 1e-5,
    Lambda: float = 1e-3,
    lam: float = 0.1,
):
    from .inflation import number_of_efolds as _ne

    if potential == "chaotic":
        V = _resolve_potential("chaotic", m=m)
    elif potential == "starobinsky":
        V = _resolve_potential("starobinsky", Lambda=Lambda)
    else:
        V = _resolve_potential("higgs", lam=lam)
    return serialize_result(_ne(V, phi_start, phi_end))


def solve_tov(rho_c: float, eos: str = "sly4", r_max: float = 30e3, n_points: int = 200):
    from .neutron_star import polytropic_eos, sly4_eos, solve_tov as _tov

    eos_obj = sly4_eos() if str(eos).lower() in ("sly4", "default") else polytropic_eos()
    return serialize_result(_tov(rho_c, eos_obj, r_max=r_max, n_points=n_points))


def mass_radius_relation(eos: str = "sly4", n_points: int = 10):
    from .neutron_star import mass_radius_relation as _mr, sly4_eos

    return serialize_result(_mr(sly4_eos() if str(eos).lower() in ("sly4", "default") else None,
                                n_points=n_points))


def fisher_matrix(f: list, M_c: float, t_c: float = 0.0, phi_c: float = 0.0):
    import numpy as np

    from .gw_analysis import fisher_matrix as _fm

    return serialize_result(_fm(np.asarray(f, dtype=float), M_c, t_c, phi_c))


def matched_filter_snr(h_template: list, h_data: list, S_n: list, f: list):
    import numpy as np

    from .gw_analysis import matched_filter_snr as _mf

    return serialize_result(_mf(
        np.asarray(h_template, dtype=float),
        np.asarray(h_data, dtype=float),
        np.asarray(S_n, dtype=float),
        np.asarray(f, dtype=float),
    ))
