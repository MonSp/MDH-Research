"""L5 agent mathematical foundations.

Formalizes a research run as a trajectory in a discrete state space and
computes process metrics (not physics of the world, but of the agent loop):

- tool-sequence entropy / branching pressure
- repair (replan) load
- state distance between metric-store snapshots
- outcome information for sweeps (spread + trend certainty)

These are diagnostics for orchestration quality, not proofs of intelligence.
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

# Finite-precision floor to avoid log(0)
_EPS = 1e-15


def shannon_entropy(counts: list[int] | dict[Any, int]) -> float:
    """Shannon entropy H = -Σ p log2 p of a discrete distribution."""
    if isinstance(counts, dict):
        vals = list(counts.values())
    else:
        vals = list(counts)
    total = sum(vals)
    if total <= 0:
        return 0.0
    h = 0.0
    for c in vals:
        if c <= 0:
            continue
        p = c / total
        h -= p * math.log2(p)
    return h


def tool_sequence_from_steps(steps: list[dict]) -> list[str]:
    return [str(s.get("tool")) for s in steps or [] if s.get("tool")]


def trajectory_metrics(
    tool_seq: list[str],
    n_success: int,
    n_fail: int,
    n_replans: int = 0,
    n_sweep_points: int = 0,
) -> dict[str, Any]:
    """Process metrics for one research run / hypothesis chain."""
    n = len(tool_seq)
    counts = Counter(tool_seq)
    h = shannon_entropy(counts)
    # max entropy if all tools distinct
    h_max = math.log2(n) if n > 1 else 0.0
    diversity = (h / h_max) if h_max > 0 else 0.0

    attempts = n_success + n_fail
    success_rate = (n_success / attempts) if attempts else 0.0
    repair_rate = (n_replans / (n_replans + 1)) if n_replans else 0.0

    # branching pressure: log2(|registry|) if known, else from unique tools seen
    return {
        "n_steps": n,
        "unique_tools": len(counts),
        "tool_entropy_bits": h,
        "tool_diversity": diversity,
        "max_tool_count": max(counts.values()) if counts else 0,
        "n_success": n_success,
        "n_fail": n_fail,
        "success_rate": success_rate,
        "n_replans": n_replans,
        "repair_load": repair_rate,
        "n_sweep_points": n_sweep_points,
    }


def state_snapshot_from_store(store_list: list[str], entries: dict[str, Any]) -> dict[str, Any]:
    """Compact fingerprint of MetricStore contents (names + numeric params)."""
    snap: dict[str, Any] = {}
    for name in store_list:
        e = entries.get(name) or {}
        params = e.get("params") or {}
        snap[name] = {
            "coord_names": list(e.get("coord_names") or []),
            "params": {
                k: float(v) for k, v in params.items()
                if isinstance(v, (int, float)) and not isinstance(v, bool)
            },
        }
    return snap


def state_distance(s1: dict, s2: dict) -> float:
    """L2 distance between two store fingerprints (missing metrics count as 1)."""
    keys = set(s1) | set(s2)
    if not keys:
        return 0.0
    total = 0.0
    for k in keys:
        a, b = s1.get(k), s2.get(k)
        if a is None or b is None:
            total += 1.0
            continue
        pa, pb = a.get("params") or {}, b.get("params") or {}
        pkeys = set(pa) | set(pb)
        if not pkeys:
            continue
        for pk in pkeys:
            va, vb = float(pa.get(pk, 0.0)), float(pb.get(pk, 0.0))
            denom = max(abs(va), abs(vb), 1.0)
            total += ((va - vb) / denom) ** 2
    return math.sqrt(total)


def sweep_information(trend: dict[str, Any]) -> dict[str, Any]:
    """Information content of a parameter sweep outcome.

    - y_spread_bits: log2 of dynamic range (how much the axis moved the output)
    - trend_certainty: |spearman| if present, else 1 if monotonic else 0
    - power_law: True when |log_log_slope| is finite (power-law hypothesis admissible)
    """
    if not trend or trend.get("n", 0) < 2:
        return {"y_spread_bits": 0.0, "trend_certainty": 0.0, "power_law": False}

    y_min = float(trend.get("y_min", 0.0))
    y_max = float(trend.get("y_max", 0.0))
    if y_max > 0 and y_min > 0:
        spread_bits = math.log2((y_max + _EPS) / (y_min + _EPS))
    else:
        spread_bits = math.log2((abs(y_max) + _EPS) / (abs(y_min) + _EPS)) if (y_min or y_max) else 0.0

    direction = trend.get("direction")
    rho = trend.get("spearman_rho")
    if rho is not None:
        certainty = abs(float(rho))
    elif direction in ("increasing", "decreasing"):
        certainty = 1.0
    else:
        certainty = 0.0

    slope = trend.get("log_log_slope")
    return {
        "y_spread_bits": spread_bits,
        "trend_certainty": certainty,
        "power_law": slope is not None and math.isfinite(float(slope)),
        "log_log_slope": slope,
    }


def decision_pressure(n_tools_available: int, n_tools_used: int) -> float:
    """log2 of choice space vs actual use — how constrained the agent was."""
    if n_tools_available <= 1 or n_tools_used <= 0:
        return 0.0
    return math.log2(n_tools_available) - math.log2(max(n_tools_used, 1))


def summarize_run(results: list[dict], n_registry_tools: int | None = None) -> dict[str, Any]:
    """Aggregate L5 foundations across all hypothesis results in one run."""
    tool_seq: list[str] = []
    n_success = 0
    n_fail = 0
    n_replans = 0
    n_sweep_points = 0
    sweep_infos: list[dict] = []

    for r in results or []:
        if r.get("success"):
            n_success += 1
        else:
            n_fail += 1
        if r.get("replan"):
            n_replans += 1
        steps = r.get("steps") or []
        tool_seq.extend(tool_sequence_from_steps(steps))
        sw = r.get("sweep")
        if sw:
            n_sweep_points += int((sw.get("trend") or {}).get("n") or 0)
            sweep_infos.append(sweep_information(sw.get("trend") or {}))

    base = trajectory_metrics(
        tool_seq, n_success, n_fail,
        n_replans=n_replans, n_sweep_points=n_sweep_points,
    )
    if n_registry_tools:
        base["decision_pressure_bits"] = decision_pressure(
            n_registry_tools, base["unique_tools"]
        )
        base["n_registry_tools"] = n_registry_tools

    if sweep_infos:
        base["sweep_information"] = sweep_infos
        base["mean_trend_certainty"] = sum(
            s["trend_certainty"] for s in sweep_infos
        ) / len(sweep_infos)

    return base
