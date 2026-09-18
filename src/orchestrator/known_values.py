"""L8: known-value consistency gate.

Compare computed results against a small catalog of textbook relations.
This is *not* discovery — it checks that agent outputs stay consistent
with established physics when the tool/params are recognizable.
"""

from __future__ import annotations

import math
from typing import Any

M_SUN_KG = 1.989e30
# T_H ≈ 6.17e-8 (M_sun / M) K  — order-of-magnitude textbook scale
HAWKING_T_SCALE = 6.17e-8
UNIVERSE_AGE_GYR_RANGE = (12.0, 15.0)
# Schwarzschild l=2,n=0 QNM (Berti/Nollert): ω ≈ 0.3737 - 0.0890i for M=1
SCH_QNM_OMEGA_RE = 0.3737
SCH_QNM_OMEGA_IM = -0.0890


def _finite(x: Any) -> float | None:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def check_hawking_temperature(result: dict, params: dict | None = None) -> dict | None:
    """T_K should scale ~1/M with solar-mass reference."""
    if not isinstance(result, dict) or "T_K" not in result:
        return None
    t = _finite(result.get("T_K"))
    m = _finite((params or {}).get("M")) or _finite(result.get("M_kg"))
    if t is None or m is None or m <= 0 or t <= 0:
        return {"name": "hawking_temperature", "passed": False,
                "detail": "missing T_K or M"}
    expected = HAWKING_T_SCALE * (M_SUN_KG / m)
    # allow 20% relative — simplified formula vs exact constants
    rel = abs(t - expected) / expected
    return {
        "name": "hawking_temperature",
        "passed": rel < 0.25,
        "expected": expected,
        "observed": t,
        "rel_err": rel,
        "detail": f"T≈{expected:.3e} vs {t:.3e} (rel={rel:.3f})",
    }


def check_universe_age(result: dict) -> dict | None:
    if not isinstance(result, dict) or "age_gyr" not in result:
        return None
    age = _finite(result.get("age_gyr"))
    if age is None:
        return {"name": "universe_age", "passed": False, "detail": "missing age_gyr"}
    lo, hi = UNIVERSE_AGE_GYR_RANGE
    return {
        "name": "universe_age",
        "passed": lo <= age <= hi,
        "expected_range": [lo, hi],
        "observed": age,
        "detail": f"age={age:.2f} Gyr in [{lo},{hi}]",
    }


def check_chirp_mass(result: dict, params: dict | None = None) -> dict | None:
    """chirp_mass(m1,m2) = (m1 m2)^{3/5} / (m1+m2)^{1/5}."""
    val = _finite(result)
    if val is None and isinstance(result, dict):
        val = _finite(result.get("chirp_mass") or result.get("M_c"))
    p = params or {}
    m1, m2 = _finite(p.get("m1")), _finite(p.get("m2"))
    if val is None or m1 is None or m2 is None:
        return None
    expected = (m1 * m2) ** 0.6 / (m1 + m2) ** 0.2
    rel = abs(val - expected) / max(expected, 1e-30)
    return {
        "name": "chirp_mass",
        "passed": rel < 1e-6,
        "expected": expected,
        "observed": val,
        "rel_err": rel,
        "detail": f"M_c={val} vs {expected}",
    }


def check_schwarzschild_qnm(result: dict) -> dict | None:
    if not isinstance(result, dict):
        return None
    if "omega_R" not in result and "omega" not in result:
        return None
    wr = _finite(result.get("omega_R"))
    wi = _finite(result.get("omega_I"))
    if wr is None:
        try:
            w = complex(result.get("omega"))
            wr, wi = w.real, w.imag
        except Exception:
            return {"name": "schwarzschild_qnm", "passed": False, "detail": "no omega"}
    # only check default M=1 l=2 n=0
    if _finite(result.get("M")) not in (None, 1.0):
        return None
    rel_r = abs(wr - SCH_QNM_OMEGA_RE) / abs(SCH_QNM_OMEGA_RE)
    ok = rel_r < 0.05 and (wi is None or abs(wi - SCH_QNM_OMEGA_IM) < 0.02)
    return {
        "name": "schwarzschild_qnm",
        "passed": ok,
        "expected": {"omega_R": SCH_QNM_OMEGA_RE, "omega_I": SCH_QNM_OMEGA_IM},
        "observed": {"omega_R": wr, "omega_I": wi},
        "detail": f"ω≈{wr:.4f}{wi:+.4f}i vs {SCH_QNM_OMEGA_RE}{SCH_QNM_OMEGA_IM:+.4f}i",
    }


def check_kretschmann_value(result: Any, params: dict | None = None,
                            r: float | None = None) -> dict | None:
    """K = 48 M^2 / r^6 when evaluating a Schwarzschild Kretschmann Expression."""
    val = _finite(result)
    p = params or {}
    m = _finite(p.get("M"))
    if val is None or m is None or r is None or r <= 0:
        return None
    expected = 48.0 * m * m / (r ** 6)
    if expected == 0:
        return None
    rel = abs(val - expected) / abs(expected)
    return {
        "name": "kretschmann_schwarzschild",
        "passed": rel < 1e-4,
        "expected": expected,
        "observed": val,
        "rel_err": rel,
        "detail": f"K={val:.6e} vs {expected:.6e} at r={r}",
    }


def check_result(tool: str, result: Any, params: dict | None = None) -> list[dict]:
    """Run all applicable known-value checks for one tool result."""
    checks: list[dict] = []
    if tool == "hawking_temperature":
        c = check_hawking_temperature(result, params)
        if c:
            checks.append(c)
    elif tool == "age_of_universe":
        c = check_universe_age(result)
        if c:
            checks.append(c)
    elif tool == "chirp_mass":
        c = check_chirp_mass(result, params)
        if c:
            checks.append(c)
    elif tool == "schwarzschild_qnm":
        c = check_schwarzschild_qnm(result)
        if c:
            checks.append(c)
    return checks


# ── L18: extensible JSON catalog ─────────────────────────────────────

import os as _os

DEFAULT_CATALOG_PATH = _os.path.join(
    _os.path.dirname(__file__), "..", "..", "benchmarks", "known_values.json"
)


def _eval_formula(name: str, params: dict[str, float]) -> float | None:
    if name == "hawking_T":
        m = _finite(params.get("M"))
        if m is None or m <= 0:
            return None
        return HAWKING_T_SCALE * (M_SUN_KG / m)
    if name == "chirp_mass":
        m1, m2 = _finite(params.get("m1")), _finite(params.get("m2"))
        if m1 is None or m2 is None:
            return None
        return (m1 * m2) ** 0.6 / (m1 + m2) ** 0.2
    if name == "deflection_angle":
        m, b = _finite(params.get("M")), _finite(params.get("b"))
        if m is None or b is None or b <= 0:
            return None
        return 4.0 * m / b
    return None


def _extract_value(result: Any, extract: str | None) -> float | None:
    if extract:
        if isinstance(result, dict):
            return _finite(result.get(extract))
        return None
    return _finite(result)


def evaluate_catalog_entry(
    entry: dict, tool: str, result: Any, params: dict | None = None
) -> dict | None:
    """Evaluate one catalog entry against a tool result."""
    if entry.get("tool") and entry["tool"] != tool:
        return None
    kind = entry.get("kind") or "range"
    name = str(entry.get("id") or tool)
    p = dict(params or {})

    if kind == "formula":
        expected = _eval_formula(str(entry.get("formula")), p)
        observed = _extract_value(result, entry.get("extract"))
        if expected is None or observed is None:
            return None
        tol = float(entry.get("tol_rel") or 0.05)
        rel = abs(observed - expected) / max(abs(expected), 1e-30)
        return {
            "name": name,
            "passed": rel < tol,
            "expected": expected,
            "observed": observed,
            "rel_err": rel,
            "detail": entry.get("description") or str(entry.get("formula")),
        }

    if kind == "range":
        observed = _extract_value(result, entry.get("extract"))
        if observed is None:
            return None
        lo = _finite(entry.get("min"))
        hi = _finite(entry.get("max"))
        ok = True
        if lo is not None and observed < lo:
            ok = False
        if hi is not None and observed > hi:
            ok = False
        return {
            "name": name,
            "passed": ok,
            "expected_range": [lo, hi],
            "observed": observed,
            "detail": entry.get("description") or "",
        }

    if kind == "near":
        observed = _extract_value(result, entry.get("extract"))
        expected = _finite(entry.get("expected"))
        if observed is None or expected is None:
            return None
        tol = float(entry.get("tol_rel") or 0.05)
        rel = abs(observed - expected) / max(abs(expected), 1e-30)
        return {
            "name": name,
            "passed": rel < tol,
            "expected": expected,
            "observed": observed,
            "rel_err": rel,
            "detail": entry.get("description") or "",
        }

    if kind == "positive":
        observed = _extract_value(result, entry.get("extract"))
        if observed is None:
            return None
        return {
            "name": name,
            "passed": observed > 0 and math.isfinite(observed),
            "observed": observed,
            "detail": entry.get("description") or "",
        }

    return None


def load_catalog(path: str | None = None) -> list[dict]:
    p = path or DEFAULT_CATALOG_PATH
    if not p or not _os.path.isfile(p):
        return []
    try:
        import json

        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def check_result_with_catalog(
    tool: str,
    result: Any,
    params: dict | None = None,
    catalog: list[dict] | None = None,
    catalog_path: str | None = None,
) -> list[dict]:
    """Built-in checks + catalog-driven checks."""
    checks = check_result(tool, result, params)
    cat = catalog if catalog is not None else load_catalog(catalog_path)
    seen = {c.get("name") for c in checks}
    for entry in cat:
        c = evaluate_catalog_entry(entry, tool, result, params)
        if c and c.get("name") not in seen:
            checks.append(c)
            seen.add(c.get("name"))
    return checks


def check_chain(
    results: list[dict],
    catalog: list[dict] | None = None,
    catalog_path: str | None = None,
) -> list[dict]:
    """Scan ResearchLoop results for known-value checks."""
    out: list[dict] = []
    for r in results or []:
        for s in r.get("steps") or []:
            tool = str(s.get("tool") or "")
            out.extend(
                check_result_with_catalog(
                    tool,
                    s.get("result"),
                    s.get("params"),
                    catalog=catalog,
                    catalog_path=catalog_path,
                )
            )
    return out


def summarize_checks(checks: list[dict]) -> dict:
    passed = sum(1 for c in checks if c.get("passed"))
    failed = [c for c in checks if c and not c.get("passed")]
    return {
        "n_checks": len(checks),
        "n_passed": passed,
        "n_failed": len(failed),
        "all_passed": bool(checks) and not failed,
        "checks": checks,
    }
