"""Named MetricStore for agent tool handoff.

C++ Metric/Manifold objects are not JSON-serializable. Factories put them
here under a string name; consumers resolve by name.
"""

from __future__ import annotations

import sys
import os
from typing import Any

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

try:
    import _research_core as rc
except ImportError:
    rc = None


class MetricStore:
    """Process-local named pool of Metric/Manifold objects."""

    def __init__(self) -> None:
        self._entries: dict[str, dict[str, Any]] = {}

    def put(
        self,
        name: str,
        metric: Any,
        manifold: Any,
        coord_names: list[str],
        params: dict[str, float] | None = None,
    ) -> None:
        self._entries[name] = {
            "metric": metric,
            "manifold": manifold,
            "coord_names": list(coord_names),
            "params": dict(params or {}),
        }

    def get(self, name: str) -> dict[str, Any]:
        if name not in self._entries:
            raise KeyError(f"metric not found: {name!r}; available={self.list()}")
        return self._entries[name]

    def get_metric(self, name: str) -> Any:
        return self.get(name)["metric"]

    def list(self) -> list[str]:
        return sorted(self._entries)

    def drop(self, name: str) -> None:
        self._entries.pop(name, None)

    def resolve_or_create(self, spec: dict[str, Any]) -> str:
        """Resolve a metric name from a tool argument dict.

        Accepts either:
          - {"metric_name": "..."} pointing at an existing entry
          - {"name": "...", "diagonal": [...], "coords": [...], "params": {...}}
            which creates via Metric.from_diagonal and stores under name
        """
        if rc is None:
            raise RuntimeError("C++ bindings not available")

        if "metric_name" in spec and spec["metric_name"]:
            name = str(spec["metric_name"])
            self.get(name)  # raise if missing
            return name

        diagonal = spec.get("diagonal")
        coords = spec.get("coords")
        if not diagonal or not coords:
            raise ValueError(
                "need metric_name, or diagonal+coords to create a metric"
            )
        name = str(spec.get("name") or f"metric_{len(self._entries)}")
        params = spec.get("params") or {}
        m = rc.geometry.Manifold(name, list(coords))
        g = rc.geometry.Metric.from_diagonal(m, list(diagonal))
        self.put(name, g, m, list(coords), params)
        return name

    def register_solution(self, solution: dict[str, Any], name: str | None = None) -> str:
        """Register a blackholes.create_* style dict and return the store name."""
        raw = name or str(solution.get("name", "solution"))
        key = raw.lower().replace("-", "_").replace(" ", "_")
        self.put(
            key,
            solution["metric"],
            solution["manifold"],
            list(solution["coord_names"]),
            dict(solution.get("params") or {}),
        )
        return key


_store: MetricStore | None = None


def get_store() -> MetricStore:
    global _store
    if _store is None:
        _store = MetricStore()
    return _store


def reset_store() -> None:
    """Test helper: drop the process singleton."""
    global _store
    _store = None
