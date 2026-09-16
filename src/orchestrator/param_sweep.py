"""Parameter-axis expansion, numeric extraction, and trend summaries."""

from __future__ import annotations

import math
from typing import Any

MAX_SWEEP_POINTS = 12


def expand_axis(axis: dict[str, Any]) -> list[float]:
    """Expand an axis spec into a list of float values (capped)."""
    if not axis:
        raise ValueError("sweep.axis is required")

    if axis.get("values"):
        vals = [float(v) for v in axis["values"]]
        if not vals:
            raise ValueError("axis.values is empty")
        return vals[:MAX_SWEEP_POINTS]

    if "start" not in axis or "stop" not in axis:
        raise ValueError("axis needs values or start/stop")

    n = int(axis.get("n") or 5)
    n = max(2, min(n, MAX_SWEEP_POINTS))
    start = float(axis["start"])
    stop = float(axis["stop"])

    if axis.get("log"):
        if start <= 0 or stop <= 0:
            raise ValueError("log axis requires positive start/stop")
        ls, le = math.log(start), math.log(stop)
        return [math.exp(ls + (le - ls) * i / (n - 1)) for i in range(n)]

    return [start + (stop - start) * i / (n - 1) for i in range(n)]


def substitute_params(params: dict[str, Any], name: str, value: float) -> dict[str, Any]:
    out = dict(params or {})
    out[name] = value
    return out


def _first_finite_float(obj: Any) -> float | None:
    if isinstance(obj, bool):
        return None
    if isinstance(obj, (int, float)):
        v = float(obj)
        return v if math.isfinite(v) else None
    if isinstance(obj, dict):
        for v in obj.values():
            got = _first_finite_float(v)
            if got is not None:
                return got
    if isinstance(obj, (list, tuple)):
        for v in obj:
            got = _first_finite_float(v)
            if got is not None:
                return got
    return None


def extract_numeric(
    result: Any,
    key: str | None = None,
    eval_point: dict[str, float] | None = None,
) -> float | None:
    """Pull a single finite float from a tool result.

    C++ Expressions are evaluated at `eval_point` (or a neutral far-field
    default). Unbound free symbols evaluate as 0 — callers should bind
    metric params into eval_point when possible.
    """
    if result is None:
        return None

    if isinstance(result, bool):
        return None

    if isinstance(result, (int, float)):
        v = float(result)
        return v if math.isfinite(v) else None

    # complex → magnitude
    if isinstance(result, complex):
        v = abs(result)
        return v if math.isfinite(v) else None

    if isinstance(result, dict):
        if key:
            if key not in result:
                return None
            return _first_finite_float(result[key])
        return _first_finite_float(result)

    # C++ Expression: evaluate at a reference point
    if hasattr(result, "evaluate") and hasattr(result, "to_string"):
        s = result.to_string().strip()
        try:
            v = float(s)
            return v if math.isfinite(v) else None
        except ValueError:
            pass
        point = {**DEFAULT_EVAL_POINT, **(eval_point or {})}
        try:
            v = float(result.evaluate(point))
            return v if math.isfinite(v) else None
        except Exception:
            return None

    return _first_finite_float(result)


# Neutral far-field point for Expression extraction when caller has no metric params
DEFAULT_EVAL_POINT: dict[str, float] = {
    "t": 0.0, "r": 10.0, "theta": 1.5708, "phi": 0.0,
    "x": 3.0, "y": 4.0, "z": 0.0,
    "M": 1.0, "a": 0.0, "Q": 0.0, "L": 0.0,
}


def _spearman_rho(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None

    def rank(vals: list[float]) -> list[float]:
        order = sorted(range(n), key=lambda i: vals[i])
        ranks = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                ranks[order[k]] = avg
            i = j + 1
        return ranks

    rx, ry = rank(xs), rank(ys)
    mx = sum(rx) / n
    my = sum(ry) / n
    num = sum((rx[i] - mx) * (ry[i] - my) for i in range(n))
    dx = math.sqrt(sum((rx[i] - mx) ** 2 for i in range(n)))
    dy = math.sqrt(sum((ry[i] - my) ** 2 for i in range(n)))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def _log_log_slope(xs: list[float], ys: list[float]) -> float | None:
    pts = [(math.log(x), math.log(y)) for x, y in zip(xs, ys) if x > 0 and y > 0]
    if len(pts) < 2:
        return None
    n = len(pts)
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    num = sum((p[0] - mx) * (p[1] - my) for p in pts)
    den = sum((p[0] - mx) ** 2 for p in pts)
    if den == 0:
        return None
    return num / den


def summarize_trend(
    xs: list[float],
    ys: list[float],
    truncated: bool = False,
) -> dict[str, Any]:
    """Describe how y varies with x."""
    pairs = [(float(x), float(y)) for x, y in zip(xs, ys)
             if math.isfinite(float(x)) and math.isfinite(float(y))]
    if not pairs:
        return {"n": 0, "direction": "empty", "truncated": truncated}

    xs2 = [p[0] for p in pairs]
    ys2 = [p[1] for p in pairs]
    n = len(ys2)
    y_min, y_max = min(ys2), max(ys2)
    scale = max(abs(y) for y in ys2) or 1.0

    if n < 2:
        direction = "flat"
        rho = None
    else:
        diffs = [ys2[i + 1] - ys2[i] for i in range(n - 1)]
        eps = 1e-12 * scale
        if all(abs(d) <= eps for d in diffs):
            direction = "flat"
        elif all(d > eps for d in diffs):
            direction = "increasing"
        elif all(d < -eps for d in diffs):
            direction = "decreasing"
        else:
            direction = "non-monotonic"
        rho = _spearman_rho(xs2, ys2)

    y_ratio = None
    if ys2[0] != 0:
        y_ratio = ys2[-1] / ys2[0]

    return {
        "n": n,
        "y_min": y_min,
        "y_max": y_max,
        "y_first": ys2[0],
        "y_last": ys2[-1],
        "direction": direction,
        "spearman_rho": rho,
        "log_log_slope": _log_log_slope(xs2, ys2),
        "y_ratio": y_ratio,
        "truncated": truncated,
        "points": [{"x": x, "y": y} for x, y in pairs],
    }


def format_trend_sentence(axis_name: str, extract_key: str | None, trend: dict) -> str:
    key = extract_key or "value"
    if trend.get("n", 0) == 0:
        return f"SWEEP: no finite {key} samples along {axis_name}"
    d = trend["direction"]
    slope = trend.get("log_log_slope")
    extra = ""
    if slope is not None:
        extra = f", log-log slope≈{slope:.3g}"
    return (
        f"SWEEP: {key} vs {axis_name} → {d} "
        f"(n={trend['n']}, {trend['y_min']:.6g}…{trend['y_max']:.6g}{extra})"
    )
