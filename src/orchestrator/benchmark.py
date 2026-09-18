"""L13: golden benchmark suite for the research platform.

Runs a fixed set of questions through ResearchLoop and checks
expectations (verdict / tools used / success / sweep trend).
"""

from __future__ import annotations

import json
import os
import tempfile
from typing import Any

DEFAULT_SUITE = os.path.join(
    os.path.dirname(__file__), "..", "..", "benchmarks", "golden_questions.json"
)


def load_suite(path: str | None = None) -> list[dict]:
    p = path or DEFAULT_SUITE
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _tools_used(results: list[dict]) -> set[str]:
    tools: set[str] = set()
    for r in results or []:
        for s in r.get("steps") or []:
            if s.get("tool"):
                tools.add(str(s["tool"]))
    return tools


def check_expectation(result: dict, expect: dict) -> tuple[bool, list[str]]:
    """Return (passed, reasons)."""
    reasons: list[str] = []
    ok = True
    c = result.get("conclusion") or {}
    results = result.get("results") or []

    verdict = c.get("verdict")
    if "verdict" in expect and verdict != expect["verdict"]:
        ok = False
        reasons.append(f"verdict={verdict!r} != {expect['verdict']!r}")
    if "verdict_in" in expect and verdict not in expect["verdict_in"]:
        ok = False
        reasons.append(f"verdict={verdict!r} not in {expect['verdict_in']!r}")

    min_ok = expect.get("min_success")
    if min_ok is not None:
        n_ok = sum(1 for r in results if r.get("success"))
        if n_ok < int(min_ok):
            ok = False
            reasons.append(f"success={n_ok} < {min_ok}")

    tools_any = expect.get("tools_any")
    if tools_any:
        used = _tools_used(results)
        if not any(t in used for t in tools_any):
            ok = False
            reasons.append(f"tools_any {tools_any} missing; used={sorted(used)[:8]}")

    if expect.get("sweep"):
        sw = None
        for r in results:
            if r.get("sweep"):
                sw = r["sweep"]
                break
        if not sw:
            ok = False
            reasons.append("expected sweep in results")
        elif expect.get("sweep_direction"):
            d = (sw.get("trend") or {}).get("direction")
            if d != expect["sweep_direction"]:
                ok = False
                reasons.append(f"sweep_direction={d!r} != {expect['sweep_direction']!r}")

    kv_min = expect.get("known_value_pass_min")
    if kv_min is not None:
        kv = c.get("known_value_checks") or {}
        n_pass = int(kv.get("n_passed") or 0)
        if n_pass < int(kv_min):
            ok = False
            reasons.append(f"known_value_passed={n_pass} < {kv_min}")

    return ok, reasons


def run_benchmark(
    suite: list[dict] | None = None,
    suite_path: str | None = None,
    llm: bool | None = False,
) -> dict[str, Any]:
    """Run golden questions and score them."""
    from .journal import ResearchJournal
    from .metric_store import reset_store
    from .research_loop import ResearchLoop

    cases = suite if suite is not None else load_suite(suite_path)
    reset_store()
    loop = ResearchLoop(
        journal=ResearchJournal(log_dir=tempfile.mkdtemp(prefix="mdh-bench-")),
        llm_client=llm,
    )

    rows: list[dict] = []
    for case in cases:
        q = case.get("question") or ""
        expect = case.get("expect") or {}
        try:
            result = loop.run(q)
            passed, reasons = check_expectation(result, expect)
            rows.append({
                "id": case.get("id"),
                "question": q,
                "passed": passed,
                "reasons": reasons,
                "verdict": (result.get("conclusion") or {}).get("verdict"),
                "n_results": len(result.get("results") or []),
            })
        except Exception as e:
            rows.append({
                "id": case.get("id"),
                "question": q,
                "passed": False,
                "reasons": [f"exception: {e}"],
                "verdict": None,
                "n_results": 0,
            })

    n = len(rows)
    n_pass = sum(1 for r in rows if r["passed"])
    return {
        "n_cases": n,
        "n_passed": n_pass,
        "pass_rate": (n_pass / n) if n else 0.0,
        "cases": rows,
    }


def render_benchmark(summary: dict[str, Any]) -> str:
    lines = ["# Golden Benchmark\n"]
    lines.append(
        f"**{summary.get('n_passed', 0)}/{summary.get('n_cases', 0)}** passed "
        f"(rate {summary.get('pass_rate', 0):.0%})\n"
    )
    lines.append("| id | pass | verdict | notes |")
    lines.append("|----|:----:|---------|-------|")
    for c in summary.get("cases") or []:
        mark = "Y" if c.get("passed") else "N"
        notes = "; ".join(c.get("reasons") or [])[:80] or "—"
        lines.append(
            f"| {c.get('id')} | {mark} | {c.get('verdict') or '—'} | {notes} |"
        )
    return "\n".join(lines) + "\n"
