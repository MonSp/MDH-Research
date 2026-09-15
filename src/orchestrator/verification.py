"""Symbolic and residual verification helpers for ResearchLoop._analyze."""

from __future__ import annotations

import math
import os
import re
import sys
from typing import Any

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

try:
    import _research_core as rc
except ImportError:
    rc = None

# identifiers that are functions/operators, not free symbols
_FUNCS = {
    "sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh",
    "exp", "log", "ln", "sqrt", "abs", "sign", "min", "max", "pow",
    "pi", "e",
}

_NON_VACUUM_FACTORIES = (
    "create_reissner_nordstrom", "create_desitter",
)

_VACUUM_FACTORIES = (
    "create_schwarzschild", "create_kerr",
)

# tightened: avoid bare "ricci"/"vanish"/"r=0" false positives
_VACUUM_PATTERNS = (
    re.compile(r"vacuum"),
    re.compile(r"真空"),
    re.compile(r"ricci[-\s]?flat"),
    re.compile(r"scalar curvature[^.]{0,40}\b0\b"),
    re.compile(r"\bR\s*=\s*0\b"),
    re.compile(r"curvature\s+vanish"),
    re.compile(r"vanish(?:es)?\s+identically"),
)


def sympy_is_zero(expr: Any, timeout_s: float = 5.0) -> bool | None:
    """Decide whether a C++ Expression is identically zero via SymPy.

    Returns True/False when decided, None if conversion/simplify fails.
    C++ is_zero() is known to fail on full GR expressions.
    """
    if expr is None:
        return None
    if isinstance(expr, (int, float)):
        return bool(abs(float(expr)) < 1e-15)

    try:
        from .sympy_bridge import expr_to_sympy
        import sympy as sp
    except Exception:
        return None

    try:
        s = expr.to_string() if hasattr(expr, "to_string") else str(expr)
        if s.strip() in ("0", "0.0", "(-0)", "(-0.0)"):
            return True
    except Exception:
        pass

    try:
        import signal

        class _TO(Exception):
            pass

        def _handler(signum, frame):
            raise _TO()

        old = None
        try:
            old = signal.signal(signal.SIGALRM, _handler)
            signal.alarm(max(1, int(timeout_s)))
        except (ValueError, OSError):
            old = None

        try:
            sp_e = expr_to_sympy(expr)
            simplified = sp.simplify(sp_e)
            return bool(simplified == 0 or simplified.is_zero is True)
        finally:
            if old is not None:
                try:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old)
                except (ValueError, OSError):
                    pass
    except Exception:
        return None


def expression_free_symbols(expr: Any) -> set[str]:
    """Best-effort free-symbol names from an Expression's string form."""
    try:
        s = expr.to_string() if hasattr(expr, "to_string") else str(expr)
    except Exception:
        return set()
    ids = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", s))
    return {i for i in ids if i not in _FUNCS and not i[0].isdigit()}


def numeric_eval_is_zero(
    expr: Any,
    points: list[dict[str, float]],
    extra_params: dict[str, float] | None = None,
    tol: float = 1e-8,
) -> tuple[bool | None, float | None, str | None]:
    """Numerically check expr≈0 only when free symbols are fully bound.

    C++ evaluate treats unbound free symbols as 0 — that false-confirms
    e.g. de Sitter R=4Λ when L is omitted. Require free ⊆ point∪params.

    Returns (is_zero | None if undecidable, sample_value, note).
    """
    free = expression_free_symbols(expr)
    extra = dict(extra_params or {})
    samples = []
    for pt in points:
        var_map = {**extra, **pt}
        missing = free - set(var_map)
        if missing:
            return None, None, f"unbound symbols {sorted(missing)}"
        try:
            val = float(expr.evaluate(var_map))
        except Exception as e:
            return None, None, f"evaluate failed: {e}"
        if not math.isfinite(val):
            return None, None, f"non-finite sample {val}"
        samples.append(val)

    if not samples:
        return None, None, "no points"
    if all(abs(v) < tol for v in samples):
        return True, samples[0], None
    return False, samples[0], None


def _default_points_for_coords(coord_names: list[str]) -> list[dict[str, float]]:
    """Far-field sample points; diagonal Kerr residual shrinks as r grows."""
    presets = [
        {"t": 0.0, "r": 20.0, "theta": 1.5708, "phi": 0.0,
         "x": 3.0, "y": 4.0, "z": 0.0},
        {"t": 0.0, "r": 40.0, "theta": 1.2, "phi": 0.4,
         "x": 1.0, "y": 2.0, "z": 2.0},
    ]
    out = []
    for p in presets:
        out.append({name: float(p.get(name, 0.0)) for name in coord_names})
    return out


def vacuum_residual_check(
    metric: Any,
    coord_names: list[str],
    params: dict[str, float] | None = None,
    points: list[dict[str, float]] | None = None,
    tol: float = 1e-4,
) -> dict[str, Any]:
    """Check Einstein tensor G_μν ≈ 0 (vacuum) at sample points.

    Failed/NaN component evaluations are not treated as residual 0.
    """
    if metric is None or rc is None:
        return {"passed": False, "error": "metric or bindings unavailable", "max_abs": None}

    try:
        G = metric.einstein_tensor()
        n = metric.dimension()
    except Exception as e:
        return {"passed": False, "error": f"einstein_tensor failed: {e}", "max_abs": None}

    base = dict(params or {})
    pts = points or _default_points_for_coords(coord_names)
    samples = []
    max_abs = 0.0
    any_finite = False

    for pt in pts:
        var_map = dict(base)
        for i, name in enumerate(coord_names):
            if name in pt:
                var_map[name] = float(pt[name])
            else:
                var_map[name] = 0.0 if i == 0 else float(i)

        local_max = 0.0
        n_ok = 0
        n_bad = 0
        for mu in range(n):
            for nu in range(n):
                try:
                    val = float(G.at([mu, nu]).evaluate(var_map))
                except Exception:
                    n_bad += 1
                    continue
                if not math.isfinite(val):
                    n_bad += 1
                    continue
                n_ok += 1
                local_max = max(local_max, abs(val))

        if n_ok == 0:
            samples.append({
                "point": {k: var_map.get(k) for k in coord_names},
                "error": f"all {n_bad} component evaluations failed/non-finite",
            })
            continue

        any_finite = True
        max_abs = max(max_abs, local_max)
        samples.append({
            "point": {k: var_map.get(k) for k in coord_names},
            "max_abs": local_max,
            "n_ok": n_ok,
            "n_bad": n_bad,
        })

    if not samples or not any_finite:
        return {
            "passed": False,
            "error": "no finite residual samples",
            "max_abs": None,
            "samples": samples,
        }

    return {
        "passed": bool(max_abs < tol),
        "max_abs": max_abs,
        "tol": tol,
        "n_points": len(samples),
        "samples": samples,
    }


def prediction_claims_vacuum(prediction: str) -> bool:
    text = (prediction or "").lower()
    return any(p.search(text) for p in _VACUUM_PATTERNS)


def is_vacuum_metric_tool_chain(tools: list[str] | None) -> bool:
    tools = tools or []
    if any(t in _NON_VACUUM_FACTORIES for t in tools):
        return False
    return any(t in _VACUUM_FACTORIES for t in tools)


def should_run_vacuum_gate(prediction: str, tools: list[str] | None) -> bool:
    """Run residual gate only for known vacuum factories, not RN/dS."""
    return is_vacuum_metric_tool_chain(tools)


def gate_counts_as_verified(prediction: str) -> bool:
    """Residual pass certifies the metric; only count as verified if the
    prediction itself claims vacuum/R=0 (not e.g. nonzero Kretschmann)."""
    return prediction_claims_vacuum(prediction)
