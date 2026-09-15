#!/usr/bin/env python3
"""Evaluate LLM tool-selection accuracy against the research tool registry.

Usage:
    PYTHONPATH=src:build/src/bindings python3 scripts/eval_tool_selection.py

Reads LLM_BASE_URL / LLM_API_KEY / LLM_MODEL from the environment.
Writes a JSON report to data/evals/tool_selection_report.json.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
BUILD = ROOT / "build" / "src" / "bindings"
if BUILD.exists():
    sys.path.insert(0, str(BUILD))

from orchestrator.tool_registry import get_tool_specs, openai_tools_payload  # noqa: E402


# ── Gold set: question → acceptable primary/alternate tools ──────────
# Each case: id, question, expected (list; first is primary), kind (single|multi)

GOLD = [
    # differential geometry / black holes
    ("g01", "What is the scalar curvature of Schwarzschild spacetime?",
     ["compute_scalar_curvature"], "single"),
    ("g02", "Compute the Kretschmann scalar for a Schwarzschild black hole.",
     ["compute_kretschmann"], "single"),
    ("g03", "Create a Kerr black hole metric with spin a=0.7.",
     ["create_kerr"], "single"),
    ("g04", "Create a Reissner-Nordstrom charged black hole.",
     ["create_reissner_nordstrom"], "single"),
    ("g05", "Where is the event horizon of a Schwarzschild black hole with M=1?",
     ["analyze_horizon", "create_schwarzschild"], "single"),
    ("g06", "Compute Christoffel symbols for the Schwarzschild metric.",
     ["compute_christoffel"], "single"),
    ("g07", "Compute the Einstein tensor G_mn for a vacuum metric.",
     ["compute_einstein"], "single"),

    # symmetry / energy / causal
    ("s01", "Is this spacetime stationary? Classify its Killing symmetries.",
     ["classify_symmetry", "detect_coordinate_killing_vectors"], "single"),
    ("s02", "Check whether the dominant and null energy conditions hold for rho=1/r^2, p=0.",
     ["check_energy_conditions_for_metric"], "single"),
    ("s03", "Classify a vector as timelike, null, or spacelike in Schwarzschild.",
     ["classify_vector"], "single"),
    ("s04", "Find where curvature singularities occur in this metric.",
     ["singularity_analysis"], "single"),
    ("s05", "What Petrov type is the Schwarzschild spacetime?",
     ["classify_petrov_type"], "single"),
    ("s06", "Build an orthonormal tetrad for a diagonal metric.",
     ["build_tetrad_diagonal"], "single"),
    ("s07", "Evaluate the field-equation residual G_mn - 8 pi T_mn at a point.",
     ["field_equation_residual_numerical"], "single"),

    # geodesics
    ("d01", "Integrate a timelike geodesic in Schwarzschild starting at r=10M.",
     ["solve_geodesic"], "single"),
    ("d02", "Evaluate Christoffel symbols at the point (0, 6, pi/2, 0).",
     ["christoffel_at_point"], "single"),

    # Hawking
    ("h01", "What is the Hawking temperature of a one-solar-mass black hole?",
     ["hawking_temperature"], "single"),
    ("h02", "How long does a solar-mass black hole take to evaporate?",
     ["evaporation_time"], "single"),
    ("h03", "Compute the Bekenstein-Hawking entropy of a black hole.",
     ["bekenstein_hawking_entropy"], "single"),
    ("h04", "What is the Unruh temperature for acceleration 1e10 m/s^2?",
     ["unruh_temperature"], "single"),

    # lensing
    ("l01", "What is the light deflection angle for mass M and impact parameter b?",
     ["deflection_angle"], "single"),
    ("l02", "Compute the Einstein ring radius given lens and source distances.",
     ["einstein_radius"], "single"),
    ("l03", "Where are the lensed image positions for source position beta?",
     ["image_positions"], "single"),
    ("l04", "Generate a microlensing light curve.",
     ["microlensing_light_curve"], "single"),

    # GW / binary / QNM / NR
    ("w01", "What is the chirp mass of a 30+30 solar mass binary?",
     ["chirp_mass"], "single"),
    ("w02", "How long until a binary merges from separation a?",
     ["merger_time"], "single"),
    ("w03", "Compute the orbital decay rate da/dt for a compact binary.",
     ["orbital_decay_rate"], "single"),
    ("w04", "Evolve a binary under gravitational-wave emission.",
     ["evolve_binary"], "single"),
    ("w05", "What is the l=2,n=0 Schwarzschild quasinormal mode frequency?",
     ["schwarzschild_qnm"], "single"),
    ("w06", "Compute Kerr QNM frequencies for prograde modes.",
     ["kerr_qnm"], "single"),
    ("w07", "Generate a black hole ringdown waveform.",
     ["ringdown_waveform"], "single"),
    ("w08", "Generate a full binary black hole merger waveform.",
     ["binary_merger_waveform"], "single"),
    ("w09", "What is the detection horizon distance for a 30+30 Msun binary?",
     ["compute_horizon_distance"], "single"),
    ("w10", "Compute the Fisher matrix for inspiral parameters.",
     ["fisher_matrix"], "single"),
    ("w11", "What is the matched-filter SNR for this template and data?",
     ["matched_filter_snr"], "single"),
    ("w12", "Give a parameter estimation summary for a GW event.",
     ["parameter_estimation_summary"], "single"),

    # cosmology / inflation / CMB / DE
    ("c01", "What is the age of the universe in LCDM?",
     ["age_of_universe"], "single"),
    ("c02", "Solve the Friedmann equation for the scale factor a(t).",
     ["solve_friedmann"], "single"),
    ("c03", "What is the Hubble parameter today (a=1)?",
     ["hubble_parameter"], "single"),
    ("c04", "Compute luminosity and angular diameter distances at z=0.5.",
     ["cosmological_distances"], "single"),
    ("c05", "Generate the symbolic FLRW metric for k=0.",
     ["flrw_metric_symbolic"], "single"),
    ("c06", "Compute the CMB temperature power spectrum D_ell.",
     ["cmb_power_spectrum"], "single"),
    ("c07", "What is the CMB acoustic scale?",
     ["acoustic_scale"], "single"),
    ("c08", "Where are the acoustic peak positions?",
     ["peak_positions"], "single"),
    ("c09", "Summarize key CMB observables for Planck-like parameters.",
     ["cmb_observables"], "single"),
    ("c10", "What is the dark energy equation of state w(z) in CPL?",
     ["w_cpl"], "single"),
    ("c11", "Compute the deceleration parameter q(z).",
     ["deceleration_parameter"], "single"),
    ("c12", "Solve cosmology in f(R) modified gravity.",
     ["f_R_cosmology"], "single"),
    ("c13", "Compute slow-roll parameters for chaotic inflation.",
     ["slow_roll_parameters"], "single"),
    ("c14", "How many e-folds of inflation occur?",
     ["number_of_efolds"], "single"),
    ("c15", "Compute inflationary observables n_s and r for Starobinsky inflation.",
     ["inflationary_observables"], "single"),
    ("c16", "Compute the primordial scalar power spectrum P_s(k).",
     ["primordial_scalar_power_spectrum"], "single"),
    ("c17", "What is the linear growth factor D(a)?",
     ["growth_factor"], "single"),
    ("c18", "Compute the linear matter power spectrum P(k).",
     ["matter_power_spectrum"], "single"),

    # PN / NR / NS
    ("p01", "What is the 1PN perihelion advance per orbit?",
     ["perihelion_advance"], "single"),
    ("p02", "Compute the 1PN orbital energy.",
     ["pn_energy_1pn"], "single"),
    ("p03", "What is the leading-order GW flux from the quadrupole formula?",
     ["gravitational_wave_flux_quadrupole"], "single"),
    ("p04", "Solve the TOV equations for a neutron star with rho_c=1e17.",
     ["solve_tov"], "single"),
    ("p05", "Compute the neutron star mass-radius relation.",
     ["mass_radius_relation"], "single"),
    ("p06", "Estimate the tidal deformability of a 1.4 Msun neutron star.",
     ["tidal_deformability"], "single"),
    ("p07", "Extract ADM quantities for a static spacetime.",
     ["extract_adm_static"], "single"),
    ("p08", "Evaluate the Hamiltonian constraint for a static metric.",
     ["hamiltonian_constraint_static"], "single"),
    ("p09", "Extract BSSN variables from a 3-metric.",
     ["bssn_variables"], "single"),
    ("p10", "Solve the Regge-Wheeler equation for l=2.",
     ["solve_regge_wheeler"], "single"),
    ("p11", "Solve the Zerilli equation.",
     ["solve_zerilli"], "single"),
    ("p12", "Compute the gravitational wave strain h(t) from QNM parameters.",
     ["compute_gw_strain"], "single"),
    ("p13", "Compute linearized Riemann tensor for a metric perturbation h.",
     ["linearized_riemann"], "single"),

    # symbolic
    ("y01", "Parse the expression x^2 + sin(y).",
     ["parse_expression"], "single"),
    ("y02", "Numerically evaluate the expression M/r^2 at M=1, r=2.",
     ["evaluate_expression"], "single"),

    # multi-step (expect a chain; primary is first step)
    ("m01", "Create a Kerr black hole, then compute its scalar curvature and check if it vanishes.",
     ["create_kerr", "compute_scalar_curvature"], "multi"),
    ("m02", "Build a Schwarzschild metric and classify its spacetime symmetries.",
     ["create_schwarzschild", "classify_symmetry"], "multi"),
    ("m03", "Create de Sitter spacetime and compute its Kretschmann scalar.",
     ["create_desitter", "compute_kretschmann"], "multi"),
    ("m04", "For a solar-mass black hole, compute Hawking temperature and evaporation time.",
     ["hawking_temperature", "evaporation_time"], "multi"),
    ("m05", "Create Schwarzschild, integrate a geodesic, and report the trajectory.",
     ["create_schwarzschild", "solve_geodesic"], "multi"),
]


@dataclass
class CaseResult:
    id: str
    question: str
    kind: str
    expected: list[str]
    predicted: list[str]
    top1_correct: bool
    any_expected_in_topk: bool
    parse_ok: bool
    error: str | None
    latency_ms: float


def compact_catalog() -> str:
    lines = []
    for t in get_tool_specs():
        lines.append(f"- {t.name}: {t.description}")
    return "\n".join(lines)


def full_openai_tools() -> list[dict]:
    return openai_tools_payload()


SYSTEM_COMPACT = """You are a physics research assistant. Choose the best tool(s) for the question.

Available tools:
{catalog}

Return ONLY JSON:
{{"tools": ["tool_name", ...], "reason": "one sentence"}}

Rules:
- Use exact tool names from the list.
- For a single computation, return one tool.
- For multi-step questions, return tools in execution order.
- Prefer create_* first when you need to build a metric, then consumer tools with metric_name.
"""


SYSTEM_FULL = """You are a physics research assistant. Choose the best tool(s) for the question.

Available tools (OpenAI function schemas):
{catalog}

Return ONLY JSON:
{{"tools": ["tool_name", ...], "reason": "one sentence"}}

Rules:
- Use exact tool names from the list.
- For a single computation, return one tool.
- For multi-step questions, return tools in execution order.
- Prefer create_* first when you need to build a metric, then consumer tools with metric_name.
"""


def call_llm(system: str, user: str, temperature: float = 0.0) -> tuple[list[str], str, float]:
    base = os.environ.get("LLM_BASE_URL", "https://api.deepseek.com").rstrip("/")
    key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY", "")
    model = os.environ.get("LLM_MODEL", "deepseek-v4-flash")
    t0 = time.time()
    resp = httpx.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": 2048,
        },
        timeout=120,
    )
    latency = (time.time() - t0) * 1000
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"].get("content") or ""
    tools, err = parse_tools(content)
    return tools, err or "", latency


def parse_tools(content: str) -> tuple[list[str], str | None]:
    text = content.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1]
            if text.startswith("json"):
                text = text[4:]
    # try JSON
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            tools = obj.get("tools") or obj.get("tool") or []
            if isinstance(tools, str):
                tools = [tools]
            return [str(t) for t in tools], None
        if isinstance(obj, list):
            return [str(t) for t in obj], None
    except json.JSONDecodeError:
        pass
    # fallback: first JSON-looking array/object
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            obj = json.loads(m.group(0))
            tools = obj.get("tools") or []
            if isinstance(tools, str):
                tools = [tools]
            return [str(t) for t in tools], None
        except json.JSONDecodeError:
            return [], f"bad json: {text[:120]}"
    return [], f"no json: {text[:120]}"


def score(expected: list[str], predicted: list[str]) -> tuple[bool, bool]:
    if not predicted:
        return False, False
    top1 = predicted[0] == expected[0]
    any_hit = any(p in expected for p in predicted[:3]) or predicted[0] in expected
    return top1, any_hit


def run_eval(mode: str = "compact", limit: int | None = None) -> dict:
    if mode == "compact":
        system = SYSTEM_COMPACT.format(catalog=compact_catalog())
    else:
        system = SYSTEM_FULL.format(
            catalog=json.dumps(full_openai_tools(), ensure_ascii=False)
        )

    valid_names = {t.name for t in get_tool_specs()}
    results: list[CaseResult] = []
    cases = GOLD[:limit] if limit else GOLD

    for cid, q, expected, kind in cases:
        try:
            predicted, err, lat = call_llm(system, q)
            parse_ok = err == "" and bool(predicted)
            # filter unknown names for fair any-hit, but keep raw for analysis
            predicted_known = [p for p in predicted if p in valid_names] or predicted
            top1, any_hit = score(expected, predicted_known)
            results.append(CaseResult(
                id=cid, question=q, kind=kind, expected=expected,
                predicted=predicted, top1_correct=top1,
                any_expected_in_topk=any_hit, parse_ok=parse_ok,
                error=err or None, latency_ms=lat,
            ))
            mark = "Y" if top1 else ("~" if any_hit else "N")
            print(f"[{mark}] {cid} kind={kind} exp={expected[0]} got={predicted[:3]}", flush=True)
        except Exception as e:
            results.append(CaseResult(
                id=cid, question=q, kind=kind, expected=expected,
                predicted=[], top1_correct=False, any_expected_in_topk=False,
                parse_ok=False, error=str(e), latency_ms=0.0,
            ))
            print(f"[E] {cid} {e}", flush=True)
        time.sleep(0.15)

    single = [r for r in results if r.kind == "single"]
    multi = [r for r in results if r.kind == "multi"]

    def acc(rows: list[CaseResult], field: str) -> float:
        if not rows:
            return 0.0
        return sum(1 for r in rows if getattr(r, field)) / len(rows)

    report = {
        "model": os.environ.get("LLM_MODEL", "unknown"),
        "base_url": os.environ.get("LLM_BASE_URL", ""),
        "mode": mode,
        "n_cases": len(results),
        "n_tools": len(valid_names),
        "overall_top1": acc(results, "top1_correct"),
        "overall_any3": acc(results, "any_expected_in_topk"),
        "parse_rate": acc(results, "parse_ok"),
        "single_top1": acc(single, "top1_correct"),
        "single_any3": acc(single, "any_expected_in_topk"),
        "multi_top1_first_step": acc(multi, "top1_correct"),
        "multi_any3": acc(multi, "any_expected_in_topk"),
        "mean_latency_ms": sum(r.latency_ms for r in results) / max(len(results), 1),
        "failures": [
            {
                "id": r.id, "kind": r.kind, "question": r.question,
                "expected": r.expected, "predicted": r.predicted, "error": r.error,
            }
            for r in results if not r.top1_correct
        ],
        "results": [asdict(r) for r in results],
    }
    return report


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "compact"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    report = run_eval(mode=mode, limit=limit)
    out_dir = ROOT / "data" / "evals"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"tool_selection_{mode}.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\n=== SUMMARY ===")
    for k in (
        "mode", "n_cases", "n_tools", "overall_top1", "overall_any3",
        "parse_rate", "single_top1", "single_any3",
        "multi_top1_first_step", "multi_any3", "mean_latency_ms",
    ):
        print(f"{k}: {report[k]}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
