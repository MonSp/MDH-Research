"""L6: hypothesis competition / regeneration.

When a first research round is weak (all failed, or best score too low),
propose alternative hypotheses and let ranking pick a winner.
Heuristics first; optional LLM when ResearchLoop.llm is enabled.
"""

from __future__ import annotations

from typing import Any

# best score below this → worth competing
DEFAULT_SCORE_FLOOR = 2.5

# sibling tools when the first-round question looks like curvature/vacuum
_CURVATURE_SIBLINGS = [
    "compute_scalar_curvature",
    "compute_ricci",
    "compute_einstein",
    "compute_kretschmann",
]

_ANALYSIS_SIBLINGS = [
    "classify_symmetry",
    "analyze_horizon",
    "classify_petrov_type",
    "check_energy_conditions_for_metric",
]


def should_compete(
    results: list[dict],
    ranking: list[dict] | None = None,
    score_floor: float = DEFAULT_SCORE_FLOOR,
) -> bool:
    """True when the first round produced no working path.

    Competition is for *failed* rounds. A successful dict-only tool
    (e.g. Hawking T) still counts as a working path — do not compete.
    """
    if not results:
        return True
    return not any(r.get("success") for r in results)


def _tools_used(results: list[dict]) -> set[str]:
    used: set[str] = set()
    for r in results or []:
        for s in r.get("steps") or []:
            if s.get("tool"):
                used.add(str(s["tool"]))
    return used


def heuristic_alternatives(
    question: str,
    results: list[dict],
    limit: int = 3,
) -> list[dict]:
    """Rule-based alternative hypotheses derived from the question + failures."""
    q = (question or "").lower()
    used = _tools_used(results)
    alts: list[dict] = []

    # 1) sibling curvature tools on Schwarzschild vacuum
    if any(k in q for k in ("curvature", "ricci", "vacuum", "einstein", "scalar")):
        for tool in _CURVATURE_SIBLINGS:
            if tool in used:
                continue
            alts.append({
                "prediction": f"Alternative: {tool} on Schwarzschild vacuum",
                "tools": [
                    {"tool": "create_schwarzschild", "params": {"M": 1}},
                    {"tool": tool, "params": {}},
                ],
                "assumptions": ["Schwarzschild", "competition-round"],
            })
            if len(alts) >= limit:
                return alts

    # 2) analysis siblings for black-hole style questions
    if any(k in q for k in ("black hole", "horizon", "symmetry", "kerr", "petrov")):
        for tool in _ANALYSIS_SIBLINGS:
            if tool in used:
                continue
            factory = "create_kerr" if "kerr" in q else "create_schwarzschild"
            fparams = {"M": 1, "a": 0.5} if factory == "create_kerr" else {"M": 1}
            alts.append({
                "prediction": f"Alternative: {tool}",
                "tools": [
                    {"tool": factory, "params": fparams},
                    {"tool": tool, "params": {}},
                ],
                "assumptions": ["competition-round"],
            })
            if len(alts) >= limit:
                return alts

    # 3) always try a known-good vacuum chain if nothing else
    if not alts and "compute_scalar_curvature" not in used:
        alts.append({
            "prediction": "Fallback: Schwarzschild scalar curvature",
            "tools": [
                {"tool": "create_schwarzschild", "params": {"M": 1}},
                {"tool": "compute_scalar_curvature", "params": {}},
            ],
            "assumptions": ["competition-fallback"],
        })

    return alts[:limit]


def llm_alternatives(
    question: str,
    results: list[dict],
    tools_payload: list[dict],
    client: Any = None,
    limit: int = 3,
) -> list[dict]:
    """Ask an OpenAI-compatible LLM for alternative hypotheses. Best-effort."""
    import json
    import os

    import httpx

    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY", "")
    if not api_key:
        return []
    base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    summary = []
    for i, r in enumerate(results or []):
        summary.append({
            "i": i,
            "success": bool(r.get("success")),
            "error": (r.get("error") or "")[:160],
            "tools": [s.get("tool") for s in (r.get("steps") or [])],
            "prediction": (r.get("hypothesis") or {}).get("prediction", "")[:120],
        })

    system = (
        "You propose NEW physics experiment hypotheses after a weak first round. "
        "Return ONLY a JSON array of up to "
        f"{limit} hypotheses. Each: prediction, tools (ordered array of "
        '{{"tool","params"}}), assumptions. Use only known tool names. '
        "Avoid tools already tried successfully. Prefer create_* then consumer.\n"
        "Tool schemas:\n" + json.dumps(tools_payload[:40], ensure_ascii=False)
    )
    user = json.dumps(
        {"question": question, "first_round": summary},
        ensure_ascii=False,
    )
    try:
        resp = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": 0.4,
                "max_tokens": 1500,
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"].get("content") or ""
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        data = json.loads(content)
        if isinstance(data, dict):
            data = data.get("hypotheses") or data.get("tools") or []
        out = []
        for h in data[:limit]:
            if not isinstance(h, dict) or "prediction" not in h:
                continue
            if not (h.get("tools") or h.get("tool")):
                continue
            h = dict(h)
            h.setdefault("assumptions", []).append("competition-llm")
            out.append(h)
        return out
    except Exception:
        return []
