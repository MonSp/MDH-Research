"""L14: hypothesis memory — persist high-score hypotheses and reuse them.

Successful research chains are stored with question keywords; future runs
with overlapping keywords inject those hypotheses as candidates.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

DEFAULT_MEMORY_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "memory", "hypotheses.json"
)

MIN_SCORE_TO_REMEMBER = 2.0
MAX_ENTRIES = 200


def _default_path(path: str | None = None) -> str:
    return path or DEFAULT_MEMORY_PATH


def load_memory(path: str | None = None) -> list[dict]:
    p = _default_path(path)
    if not os.path.isfile(p):
        return []
    try:
        with open(p, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def save_memory(entries: list[dict], path: str | None = None) -> str:
    p = _default_path(path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(entries[-MAX_ENTRIES:], f, ensure_ascii=False, indent=2)
    return p


def _keywords(text: str) -> set[str]:
    stop = {
        "the", "a", "an", "of", "is", "what", "how", "does", "do", "for",
        "to", "in", "on", "and", "or", "this", "that", "with", "spacetime",
    }
    words = []
    for w in (text or "").lower().replace("?", " ").replace(",", " ").split():
        w = w.strip(".'\"")
        if len(w) >= 3 and w not in stop:
            words.append(w)
    return set(words)


def extract_memorable(results: list[dict], question: str) -> list[dict]:
    """Pull successful high-score hypotheses from a run/campaign results."""
    out = []
    kws = sorted(_keywords(question))
    for r in results or []:
        if not r.get("success"):
            continue
        hyp = r.get("hypothesis") or {}
        tools = [s.get("tool") for s in (r.get("steps") or []) if s.get("tool")]
        if not tools:
            continue
        # score later via agent_math if available
        score = None
        try:
            from .agent_math import score_hypothesis

            score = score_hypothesis(r).get("score")
        except Exception:
            score = 2.0 if r.get("success") else 0.0
        if score is None:
            score = 2.0 if r.get("success") else 0.0
        # successful chains with tools are memorable even without eval steps
        if r.get("success") and tools:
            score = max(float(score), MIN_SCORE_TO_REMEMBER)
        if float(score) < MIN_SCORE_TO_REMEMBER:
            continue
        out.append({
            "prediction": str(hyp.get("prediction", ""))[:160],
            "tools": tools,
            "params": [
                (s.get("params") or {}) for s in (r.get("steps") or []) if s.get("tool")
            ],
            "question_keywords": kws,
            "score": float(score),
            "round": r.get("round") or "first",
            "ts": time.time(),
        })
    return out


def remember_from_run(result: dict, path: str | None = None) -> list[dict]:
    """Remember memorable hypotheses from one ResearchLoop.run() result."""
    question = result.get("question") or ""
    new = extract_memorable(result.get("results") or [], question)
    if not new:
        return load_memory(path)
    mem = load_memory(path)
    # de-dupe by (tools, prediction)
    seen = {(tuple(e.get("tools") or []), e.get("prediction")) for e in mem}
    for e in new:
        key = (tuple(e.get("tools") or []), e.get("prediction"))
        if key not in seen:
            mem.append(e)
            seen.add(key)
    save_memory(mem, path)
    return mem


def recall_hypotheses(question: str, path: str | None = None, limit: int = 3) -> list[dict]:
    """Return stored hypotheses whose keywords overlap the question."""
    kws = _keywords(question)
    mem = load_memory(path)
    scored = []
    for e in mem:
        ek = set(e.get("question_keywords") or [])
        overlap = len(kws & ek)
        if overlap <= 0:
            continue
        scored.append((overlap, float(e.get("score") or 0), e))
    scored.sort(key=lambda t: (-t[0], -t[1]))
    out = []
    for _, _, e in scored[:limit]:
        out.append({
            "prediction": e.get("prediction"),
            "tools": e.get("tools"),
            "params": e.get("params"),
            "assumptions": ["memory-recall"],
            "memory_score": e.get("score"),
        })
    return out


def inject_memory_candidates(
    question: str,
    path: str | None = None,
    limit: int = 2,
) -> list[dict]:
    """Format recalled hypotheses as ResearchLoop-ready tools chains."""
    rec = recall_hypotheses(question, path=path, limit=limit)
    hyps = []
    for e in rec:
        tools = e.get("tools") or []
        params = e.get("params") or []
        steps = []
        for i, t in enumerate(tools):
            steps.append({
                "tool": t,
                "params": params[i] if i < len(params) else {},
            })
        hyps.append({
            "prediction": e.get("prediction") or "memory recall",
            "tools": steps,
            "assumptions": ["memory-recall"],
        })
    return hyps


def memory_summary(path: str | None = None) -> dict[str, Any]:
    mem = load_memory(path)
    tools: dict[str, int] = {}
    for e in mem:
        for t in e.get("tools") or []:
            tools[t] = tools.get(t, 0) + 1
    return {
        "n_entries": len(mem),
        "n_unique_tools": len(tools),
        "top_tools": sorted(tools.items(), key=lambda kv: -kv[1])[:8],
        "mean_score": (
            sum(float(e.get("score") or 0) for e in mem) / len(mem) if mem else None
        ),
    }
