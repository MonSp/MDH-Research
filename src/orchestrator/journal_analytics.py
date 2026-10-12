"""L11: cross-session journal analytics.

Load ResearchJournal JSONL files (or in-memory event lists) and compute
process metrics across sessions: tool usage, event mix, compete/iterate
rates, success rates.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from typing import Any


def load_journal_file(path: str) -> list[dict]:
    """Read a ResearchJournal JSONL file into event dicts."""
    events: list[dict] = []
    if not path or not os.path.isfile(path):
        return events
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def load_journal_dir(dir_path: str) -> dict[str, list[dict]]:
    """Load all *.jsonl journals from a directory → {session_id: events}."""
    out: dict[str, list[dict]] = {}
    if not dir_path or not os.path.isdir(dir_path):
        return out
    for name in sorted(os.listdir(dir_path)):
        if not name.endswith(".jsonl"):
            continue
        sid = name[: -len(".jsonl")]
        out[sid] = load_journal_file(os.path.join(dir_path, name))
    return out


def _payload(e: dict) -> dict:
    p = e.get("payload")
    return p if isinstance(p, dict) else {}


def session_metrics(events: list[dict], session_id: str | None = None) -> dict[str, Any]:
    """Process metrics for one journal session."""
    types = Counter(e.get("type") for e in events)
    tools: Counter[str] = Counter()
    notes = []
    conclusions = []

    for e in events:
        p = _payload(e)
        if e.get("type") == "experiment":
            t = p.get("tool")
            if isinstance(t, str):
                tools[t] += 1
        elif e.get("type") == "tool_call":
            t = p.get("tool")
            if isinstance(t, str):
                tools[f"call:{t}"] += 1
        elif e.get("type") == "note":
            notes.append(str(p.get("text", "")))
        elif e.get("type") == "conclusion":
            conclusions.append(p)

    n_comp = sum(1 for n in notes if n.startswith("COMPETE"))
    n_iter = sum(1 for n in notes if n.startswith("ITERATE"))
    n_replan = sum(1 for n in notes if n.startswith("REPLAN"))
    n_obs = types.get("observation", 0)
    n_obs_ok = sum(
        1 for e in events
        if e.get("type") == "observation" and _payload(e).get("success")
    )

    best_scores = []
    for c in conclusions:
        ranking = c.get("hypothesis_ranking") or c.get("best_hypothesis")
        if isinstance(c.get("best_hypothesis"), dict) and c["best_hypothesis"].get("score") is not None:
            best_scores.append(float(c["best_hypothesis"]["score"]))
        elif isinstance(ranking, list) and ranking and ranking[0].get("score") is not None:
            best_scores.append(float(ranking[0]["score"]))

    # L43: sweep/grid process metrics (tool labeled sweep:/grid:)
    sweep_ids: set[str] = set()
    for e in events:
        if e.get("type") == "experiment":
            tool = str(_payload(e).get("tool") or "")
            if tool.startswith("sweep:") or tool.startswith("grid:"):
                if e.get("id"):
                    sweep_ids.add(str(e["id"]))
    n_sweep = len(sweep_ids)
    n_sweep_ok = n_sweep_fail = 0
    sweep_durations: list[float] = []
    for e in events:
        if e.get("type") != "observation":
            continue
        if str(e.get("parent_id") or "") not in sweep_ids:
            continue
        pload = _payload(e)
        if pload.get("success"):
            n_sweep_ok += 1
        else:
            n_sweep_fail += 1
        dur = pload.get("duration_ms")
        if dur is not None:
            try:
                sweep_durations.append(float(dur))
            except (TypeError, ValueError):
                pass
    n_sweep_obs = n_sweep_ok + n_sweep_fail

    return {
        "session_id": session_id,
        "n_events": len(events),
        "event_types": dict(types),
        "n_hypothesis": types.get("hypothesis", 0),
        "n_experiment": types.get("experiment", 0),
        "n_observation": n_obs,
        "observation_success_rate": (n_obs_ok / n_obs) if n_obs else None,
        "n_conclusion": types.get("conclusion", 0),
        "n_compete": n_comp,
        "n_iterate": n_iter,
        "n_replan": n_replan,
        "top_tools": tools.most_common(8),
        "mean_best_score": (sum(best_scores) / len(best_scores)) if best_scores else None,
        "n_scores": len(best_scores),
        "n_sweep_experiments": n_sweep,
        "n_sweep_failures": n_sweep_fail,
        "sweep_failure_rate": (n_sweep_fail / n_sweep_obs) if n_sweep_obs else None,
        "mean_sweep_duration_ms": (
            sum(sweep_durations) / len(sweep_durations) if sweep_durations else None
        ),
    }


def compare_sessions(sessions: dict[str, list[dict]]) -> dict[str, Any]:
    """Aggregate metrics across multiple journal sessions."""
    rows = []
    total_events = 0
    tool_all: Counter[str] = Counter()
    scores: list[float] = []
    n_comp = n_iter = n_replan = 0
    n_obs = n_obs_ok = 0
    n_conc = 0
    n_sweep = n_sweep_fail = 0
    sweep_durs: list[float] = []

    for sid, events in sessions.items():
        m = session_metrics(events, session_id=sid)
        rows.append(m)
        total_events += m["n_events"]
        n_comp += m["n_compete"]
        n_iter += m["n_iterate"]
        n_replan += m["n_replan"]
        n_obs += m["n_observation"]
        if m["observation_success_rate"] is not None:
            # reconstruct ok count
            n_obs_ok += int(round(m["observation_success_rate"] * m["n_observation"]))
        n_conc += m["n_conclusion"]
        n_sweep += m.get("n_sweep_experiments") or 0
        n_sweep_fail += m.get("n_sweep_failures") or 0
        mdur = m.get("mean_sweep_duration_ms")
        if mdur is not None:
            # weight by session count of sweep obs approximated by equal share
            sweep_durs.append(float(mdur))
        for t, c in m["top_tools"]:
            if not str(t).startswith("call:"):
                tool_all[t] += c
        if m["mean_best_score"] is not None and m["n_scores"]:
            scores.extend([m["mean_best_score"]] * m["n_scores"])

    # reconstruct sweep obs count from sessions for failure rate
    n_sweep_obs = 0
    for m in rows:
        rate = m.get("sweep_failure_rate")
        nf = m.get("n_sweep_failures") or 0
        if rate and rate > 0:
            n_sweep_obs += int(round(nf / rate))
        elif rate == 0:
            n_sweep_obs += m.get("n_sweep_experiments") or 0
        else:
            n_sweep_obs += m.get("n_sweep_experiments") or 0

    return {
        "n_sessions": len(sessions),
        "total_events": total_events,
        "n_conclusions": n_conc,
        "observation_success_rate": (n_obs_ok / n_obs) if n_obs else None,
        "n_compete": n_comp,
        "n_iterate": n_iter,
        "n_replan": n_replan,
        "top_tools": tool_all.most_common(10),
        "mean_best_score": (sum(scores) / len(scores)) if scores else None,
        "n_sweep_experiments": n_sweep,
        "n_sweep_failures": n_sweep_fail,
        "sweep_failure_rate": (n_sweep_fail / n_sweep_obs) if n_sweep_obs else None,
        "mean_sweep_duration_ms": (
            sum(sweep_durs) / len(sweep_durs) if sweep_durs else None
        ),
        "sessions": rows,
    }


def render_analytics(summary: dict[str, Any]) -> str:
    """Markdown summary of cross-session analytics."""
    lines = ["# Journal Analytics\n"]
    lines.append("## Overview\n")
    lines.append(f"- sessions: **{summary.get('n_sessions', 0)}**")
    lines.append(f"- events: **{summary.get('total_events', 0)}**")
    lines.append(f"- conclusions: {summary.get('n_conclusions', 0)}")
    rate = summary.get("observation_success_rate")
    lines.append(
        f"- observation success rate: "
        f"{'—' if rate is None else f'{rate:.2%}'}"
    )
    lines.append(
        f"- COMPETE notes: {summary.get('n_compete', 0)}  "
        f"ITERATE: {summary.get('n_iterate', 0)}  "
        f"REPLAN: {summary.get('n_replan', 0)}"
    )
    if summary.get("mean_best_score") is not None:
        lines.append(f"- mean best score: {summary['mean_best_score']:.3f}")
    if summary.get("n_sweep_experiments") is not None:
        sfr = summary.get("sweep_failure_rate")
        msd = summary.get("mean_sweep_duration_ms")
        lines.append(
            f"- sweep experiments: {summary.get('n_sweep_experiments', 0)}  "
            f"failure rate: {'—' if sfr is None else f'{sfr:.2%}'}  "
            f"mean duration: "
            f"{'—' if msd is None else f'{msd:.1f} ms'}"
        )

    top = summary.get("top_tools") or []
    if top:
        lines.append("\n## Top experiment tools\n")
        for t, c in top:
            lines.append(f"- `{t}`: {c}")

    sessions = summary.get("sessions") or []
    if sessions:
        lines.append("\n## Sessions\n")
        lines.append("| id | events | conc | compete | iterate | best_score |")
        lines.append("|----|-------:|-----:|--------:|--------:|-----------:|")
        for s in sessions:
            ms = s.get("mean_best_score")
            lines.append(
                f"| {str(s.get('session_id') or '')[:12]} | {s.get('n_events', 0)} | "
                f"{s.get('n_conclusion', 0)} | {s.get('n_compete', 0)} | "
                f"{s.get('n_iterate', 0)} | "
                f"{'—' if ms is None else f'{ms:.2f}'} |"
            )

    return "\n".join(lines) + "\n"
