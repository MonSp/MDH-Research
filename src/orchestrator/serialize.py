"""Serialize orchestrator results for LLM / journal / JSON transport."""

from __future__ import annotations

from typing import Any

_MAX_STR = 500


def _truncate(s: str) -> str:
    if len(s) <= _MAX_STR:
        return s
    return s[:_MAX_STR] + "…"


def serialize_result(obj: Any) -> Any:
    """Convert a tool result into a JSON-safe structure."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        if isinstance(obj, str):
            return _truncate(obj)
        return obj

    # numpy scalars / arrays
    if hasattr(obj, "item") and hasattr(obj, "tolist"):
        try:
            if getattr(obj, "ndim", 0) == 0:
                return obj.item()
            return obj.tolist()
        except Exception:
            pass
    if hasattr(obj, "tolist") and not isinstance(obj, (list, tuple, dict)):
        try:
            return serialize_result(obj.tolist())
        except Exception:
            pass

    # C++ Expression
    if hasattr(obj, "to_string") and hasattr(obj, "evaluate"):
        return {"__expr__": _truncate(obj.to_string())}

    # C++ Tensor: prefer nested components if exposed
    if type(obj).__name__ == "Tensor":
        try:
            return serialize_result(obj.components() if callable(getattr(obj, "components", None)) else str(obj))
        except Exception:
            return {"__tensor__": _truncate(str(obj))}

    # Live C++ geometry objects must not leak into JSON
    tname = type(obj).__name__
    if tname in ("Metric", "Manifold"):
        return {"__ref__": tname}

    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if _skip_live_geometry(k, v):
                continue
            out[str(k)] = serialize_result(v)
        return out

    if isinstance(obj, (list, tuple)):
        return [serialize_result(x) for x in obj]

    if isinstance(obj, set):
        return [serialize_result(x) for x in sorted(obj, key=str)]

    return _truncate(str(obj))


def _skip_live_geometry(key: str, value: Any) -> bool:
    """Skip live geometry objects inside solution dicts."""
    if key in ("metric", "manifold") and type(value).__name__ in ("Metric", "Manifold"):
        return True
    return False
