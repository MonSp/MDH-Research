"""L20: campaign trend aggregation.

Compare saved campaign summaries over time (verify rate, known-value
rate, scores) to see whether the platform is improving.
"""

from __future__ import annotations

import glob
import json
import os
from typing import Any


def load_campaign_summaries(path_or_glob: str) -> list[dict]:
    """Load campaign JSON files (or a directory of them) into summaries.

    Accepts:
      - path to a single JSON (campaign output or {summary:...})
      - directory containing *.json
      - glob pattern
    """
    paths: list[str] = []
    if os.path.isdir(path_or_glob):
        paths = sorted(glob.glob(os.path.join(path_or_glob, "*.json")))
    elif any(ch in path_or_glob for ch in "*?["):
        paths = sorted(glob.glob(path_or_glob))
    elif os.path.isfile(path_or_glob):
        paths = [path_or_glob]
    else:
        paths = sorted(glob.glob(path_or_glob))

    out = []
    for p in paths:
        try:
            with open(p, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        summary = data.get("summary") if isinstance(data, dict) else None
        if not isinstance(summary, dict):
            continue
        item = dict(summary)
        item["_source"] = p
        item["_source_name"] = os.path.basename(p)
        # keep questions if present
        qs = data.get("questions")
        if isinstance(qs, list):
            item["n_questions_listed"] = len(qs)
        out.append(item)
    return out


def compute_trend(summaries: list[dict]) -> dict[str, Any]:
    """Deltas between first and last summary in file order."""
    if not summaries:
        return {"n_files": 0, "delta": {}}

    def _get(s: dict, key: str):
        v = s.get(key)
        return float(v) if v is not None else None

    keys = [
        "n_questions", "n_verified", "verify_rate",
        "known_value_passed", "known_value_total", "known_value_rate",
        "mean_best_score", "n_competed", "n_iterated",
    ]
    first, last = summaries[0], summaries[-1]
    delta = {}
    for k in keys:
        a, b = _get(first, k), _get(last, k)
        if a is not None and b is not None:
            delta[k] = {"first": a, "last": b, "delta": b - a}

    improved = None
    if "verify_rate" in delta:
        d = delta["verify_rate"]["delta"]
        improved = d > 0 if d != 0 else None

    return {
        "n_files": len(summaries),
        "first": first.get("_source_name"),
        "last": last.get("_source_name"),
        "delta": delta,
        "verify_rate_improved": improved,
        "series": [
            {
                "name": s.get("_source_name"),
                "verify_rate": _get(s, "verify_rate"),
                "known_value_rate": _get(s, "known_value_rate"),
                "mean_best_score": _get(s, "mean_best_score"),
                "n_questions": _get(s, "n_questions"),
            }
            for s in summaries
        ],
    }


def render_trend(trend: dict[str, Any]) -> str:
    lines = ["# Campaign Trend\n"]
    lines.append(f"- files: **{trend.get('n_files', 0)}**")
    if trend.get("first"):
        lines.append(f"- span: `{trend.get('first')}` → `{trend.get('last')}`")
    if trend.get("verify_rate_improved") is True:
        lines.append("- verify_rate: **improved**")
    elif trend.get("verify_rate_improved") is False:
        lines.append("- verify_rate: **declined**")

    delta = trend.get("delta") or {}
    if delta:
        lines.append("\n## First → Last\n")
        lines.append("| metric | first | last | delta |")
        lines.append("|--------|------:|-----:|------:|")
        for k, v in delta.items():
            lines.append(
                f"| {k} | {v['first']:.4g} | {v['last']:.4g} | {v['delta']:+.4g} |"
            )

    series = trend.get("series") or []
    if series:
        lines.append("\n## Series\n")
        lines.append("| file | verify | kv rate | best score | n_q |")
        lines.append("|------|-------:|--------:|-----------:|----:|")
        for s in series:
            def fmt(x):
                return "—" if x is None else f"{x:.3g}"
            lines.append(
                f"| {s.get('name')} | {fmt(s.get('verify_rate'))} | "
                f"{fmt(s.get('known_value_rate'))} | {fmt(s.get('mean_best_score'))} | "
                f"{fmt(s.get('n_questions'))} |"
            )

    return "\n".join(lines) + "\n"


def aggregate_campaigns(path_or_glob: str) -> dict[str, Any]:
    summaries = load_campaign_summaries(path_or_glob)
    trend = compute_trend(summaries)
    trend["sources"] = [s.get("_source") for s in summaries]
    return trend
