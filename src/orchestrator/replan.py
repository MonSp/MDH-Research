"""Failure diagnosis and chain replanning for ResearchLoop.

Classifies chain errors and proposes a repaired step list.
Heuristics first (no LLM required).
"""

from __future__ import annotations

import re
from typing import Any

# Defaults for tools whose Python signature has no default
_PARAM_DEFAULTS: dict[str, dict[str, Any]] = {
    "hawking_temperature": {"M": 1.989e30},
    "evaporation_time": {"M": 1.989e30},
    "bekenstein_hawking_entropy": {"M": 1.989e30},
    "chirp_mass": {"m2": 30.0},
    "orbital_decay_rate": {"m1": 30.0, "m2": 30.0},
    "merger_time": {"m1": 30.0, "m2": 30.0},
    "deflection_angle": {"b": 10.0},
}

_GENERIC_DEFAULTS = {
    "M": 1.0, "m1": 30.0, "m2": 30.0, "a": 0.5, "Q": 0.5, "L": 1.0, "b": 10.0,
}

_SYNONYMS = {
    "compute_scalar": "compute_scalar_curvature",
    "scalar_curvature": "compute_scalar_curvature",
    "kretschmann_scalar": "compute_kretschmann",
}

# (keywords, factory or None for diagonal inject)
_FACTORY_KEYWORDS = (
    (("kerr", "spin", "rotating"), "create_kerr"),
    (("reissner", "charged", "charge"), "create_reissner_nordstrom"),
    (("de sitter", "desitter", "cosmological constant"), "create_desitter"),
    (("minkowski", "flat"), None),
    (("schwarzschild", "black hole", "vacuum"), "create_schwarzschild"),
)

_MINKOWSKI_DIAGONAL = ["-1", "1", "1", "1"]
_MINKOWSKI_COORDS = ["t", "x", "y", "z"]


def _tool_from_partial(partial: list[dict] | None) -> str | None:
    if not partial:
        return None
    last = partial[-1]
    return last.get("tool")


def _tool_from_error(error: str) -> str | None:
    m = re.search(r"unknown tool:?\s*['\"]?(\w+)", error or "", re.I)
    if m:
        return m.group(1)
    m = re.search(r"step \d+ \((\w+)\)", error or "")
    if m:
        return m.group(1)
    return None


def diagnose_failure(
    error: str,
    partial_steps: list[dict] | None = None,
) -> dict[str, Any]:
    """Classify a chain failure from the error string / partial records."""
    err = (error or "").lower()
    tool = _tool_from_partial(partial_steps) or _tool_from_error(error)

    if "needs a metric" in err:
        return {"kind": "missing_metric", "tool": tool, "error": error}
    if "unknown tool" in err:
        return {"kind": "unknown_tool", "tool": tool, "error": error}
    if "missing" in err and ("required" in err or "positional" in err):
        return {"kind": "missing_param", "tool": tool, "error": error}
    if "unexpected keyword" in err:
        return {"kind": "bad_kwarg", "tool": tool, "error": error}
    if "failed:" in err:
        return {"kind": "execution_error", "tool": tool, "error": error}
    return {"kind": "unknown", "tool": tool, "error": error}


def _pick_factory_for_question(question: str) -> str | None:
    q = (question or "").lower()
    for keys, factory in _FACTORY_KEYWORDS:
        if any(k in q for k in keys):
            return factory  # None means minkowski diagonal path
    return "create_schwarzschild"


def _extract_missing_args(error: str) -> list[str]:
    """Parse one or more missing required argument names from TypeError text."""
    err = error or ""
    # singular: missing 1 required positional argument: 'M'
    m = re.search(r"missing \d+ required positional argument: '(\w+)'", err)
    if m:
        return [m.group(1)]
    # plural: missing 2 required positional arguments: 'm1' and 'm2'
    m = re.search(
        r"missing \d+ required positional arguments: (.+)$", err, re.M
    )
    if m:
        return re.findall(r"'(\w+)'", m.group(1))
    m = re.search(r"missing \d+ required keyword-only argument: '(\w+)'", err)
    if m:
        return [m.group(1)]
    m = re.search(
        r"missing \d+ required keyword-only arguments: (.+)$", err, re.M
    )
    if m:
        return re.findall(r"'(\w+)'", m.group(1))
    return []


def _extract_bad_kwarg(error: str) -> str | None:
    m = re.search(r"unexpected keyword argument '(\w+)'", error or "")
    return m.group(1) if m else None


def heuristic_repair(
    steps: list[Any],
    diagnosis: dict[str, Any],
    question: str = "",
    step_cls: Any = None,
) -> list[Any] | None:
    """Rule-based repair of a failed chain. Returns new steps or None."""
    if step_cls is None:
        from .research_loop import ChainStep as step_cls  # lazy

    kind = diagnosis.get("kind")
    failed_tool = diagnosis.get("tool")
    out = [step_cls(tool=s.tool, params=dict(s.params)) for s in steps]

    if kind == "unknown_tool" and failed_tool:
        if failed_tool in _SYNONYMS:
            target = _SYNONYMS[failed_tool]
            return [
                step_cls(tool=target, params=dict(s.params)) if s.tool == failed_tool
                else s
                for s in out
            ]
        return None

    if kind == "missing_metric":
        has_factory = any((s.tool or "").startswith("create_") for s in out)
        if has_factory:
            return None
        factory = _pick_factory_for_question(question)
        if factory is None:
            # Minkowski / flat: inject diagonal into the failed consumer step
            for i, s in enumerate(out):
                if s.tool == failed_tool or (
                    not s.params.get("diagonal") and not s.params.get("metric_name")
                ):
                    params = dict(s.params)
                    params.setdefault("diagonal", list(_MINKOWSKI_DIAGONAL))
                    params.setdefault("coords", list(_MINKOWSKI_COORDS))
                    params.setdefault("name", "minkowski")
                    out[i] = step_cls(tool=s.tool, params=params)
                    return out
            return None
        fparams: dict[str, Any]
        if factory == "create_kerr":
            fparams = {"M": 1.0, "a": 0.5}
        elif factory == "create_reissner_nordstrom":
            fparams = {"M": 1.0, "Q": 0.5}
        elif factory == "create_desitter":
            fparams = {"L": 1.0}
        else:
            fparams = {"M": 1.0}
        return [step_cls(tool=factory, params=fparams)] + out

    if kind == "missing_param":
        args = _extract_missing_args(diagnosis.get("error") or "")
        tool = failed_tool or (out[-1].tool if out else None)
        if tool and args:
            defaults = _PARAM_DEFAULTS.get(tool, {})
            fills: dict[str, Any] = {}
            for arg in args:
                val = defaults.get(arg, _GENERIC_DEFAULTS.get(arg))
                if val is None:
                    return None
                fills[arg] = val
            for i, s in enumerate(out):
                if s.tool == tool:
                    params = dict(s.params)
                    for k, v in fills.items():
                        params.setdefault(k, v)
                    out[i] = step_cls(tool=s.tool, params=params)
                    return out
        return None

    if kind == "bad_kwarg":
        bad = _extract_bad_kwarg(diagnosis.get("error") or "")
        tool = failed_tool
        if bad and tool:
            for i, s in enumerate(out):
                if s.tool == tool and bad in s.params:
                    params = dict(s.params)
                    params.pop(bad, None)
                    out[i] = step_cls(tool=s.tool, params=params)
                    return out
        return None

    return None


def describe_repair(before: list[Any], after: list[Any], kind: str) -> str:
    def _fmt(steps: list[Any]) -> str:
        parts = []
        for s in steps:
            keys = sorted(s.params)
            if keys:
                parts.append(f"{s.tool}({','.join(keys)})")
            else:
                parts.append(s.tool)
        return " → ".join(parts)

    return f"REPLAN({kind}): {_fmt(before)}  ⇒  {_fmt(after)}"
