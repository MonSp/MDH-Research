"""L10: research report synthesis.

Turn a campaign (or single ResearchLoop.run) result into a structured
markdown report. Pure text — no plotting.
"""

from __future__ import annotations

from typing import Any


def _fmt_float(x: Any, digits: int = 4) -> str:
    try:
        v = float(x)
    except (TypeError, ValueError):
        return str(x)
    if abs(v) >= 1e4 or (v != 0 and abs(v) < 1e-3):
        return f"{v:.3e}"
    return f"{v:.{digits}g}"


def _evidence_bullets(evidence: list[str] | None, limit: int = 8) -> list[str]:
    out = []
    for e in (evidence or [])[:limit]:
        e = str(e).strip()
        if not e:
            continue
        out.append(f"- {e[:200]}")
    return out


def render_single_run(result: dict) -> str:
    """Render one ResearchLoop.run() output as markdown."""
    c = result.get("conclusion") or {}
    lines: list[str] = []
    lines.append(f"## Question\n\n> {result.get('question', '')}\n")
    lines.append(f"**Verdict:** {c.get('verdict', 'n/a')}\n")

    v = c.get("verification") or {}
    lines.append("### Verification\n")
    lines.append(
        f"- numeric_confirmed: {v.get('numeric_confirmed', 0)}  "
        f"symbolic_confirmed: {v.get('symbolic_confirmed', 0)}"
    )
    gates = v.get("residual_gates") or []
    if gates:
        for g in gates:
            lines.append(
                f"- residual gate `{g.get('metric_name')}`: "
                f"{'PASS' if g.get('passed') else 'FAIL'} "
                f"max|G|={_fmt_float(g.get('max_abs'))}"
            )
    kv = c.get("known_value_checks") or {}
    if kv.get("n_checks"):
        lines.append(
            f"- known-value: {kv.get('n_passed', 0)}/{kv.get('n_checks', 0)} passed"
        )

    f = c.get("foundations") or {}
    if f:
        lines.append("\n### Process metrics (L5)\n")
        lines.append(
            f"- steps={f.get('n_steps')} unique_tools={f.get('unique_tools')} "
            f"entropy={_fmt_float(f.get('tool_entropy_bits'))} bits "
            f"success_rate={_fmt_float(f.get('success_rate'))}"
        )
        if f.get("mean_trend_certainty") is not None:
            lines.append(
                f"- mean_trend_certainty={_fmt_float(f.get('mean_trend_certainty'))}"
            )

    ranking = c.get("hypothesis_ranking") or []
    if ranking:
        lines.append("\n### Hypothesis ranking\n")
        lines.append("| rank | score | success | prediction |")
        lines.append("|------|------:|---------|------------|")
        for i, e in enumerate(ranking[:5], 1):
            pred = str(e.get("prediction", ""))[:60].replace("|", "/")
            lines.append(
                f"| {i} | {_fmt_float(e.get('score'))} | "
                f"{'Y' if e.get('success') else 'N'} | {pred} |"
            )

    lines.append("\n### Evidence\n")
    bullets = _evidence_bullets(c.get("evidence"))
    lines.extend(bullets or ["- (none)"])

    if c.get("competed") or c.get("iterate_rounds"):
        lines.append("\n### Search\n")
        lines.append(
            f"- competed={bool(c.get('competed'))} "
            f"iterate_rounds={c.get('iterate_rounds') or 0}"
        )

    return "\n".join(lines) + "\n"


def render_campaign(campaign: dict) -> str:
    """Render campaign.run_campaign() output as a markdown report."""
    summary = campaign.get("summary") or {}
    questions = campaign.get("questions") or []

    lines: list[str] = ["# Research Campaign Report\n"]

    lines.append("## Program summary\n")
    lines.append(
        f"- questions: **{summary.get('n_questions', 0)}**  "
        f"verified: **{summary.get('n_verified', 0)}**  "
        f"verify_rate: **{_fmt_float(summary.get('verify_rate'))}**"
    )
    lines.append(
        f"- competed: {summary.get('n_competed', 0)}  "
        f"iterated: {summary.get('n_iterated', 0)}"
    )
    kv_rate = summary.get("known_value_rate")
    lines.append(
        f"- known-value: {summary.get('known_value_passed', 0)}/"
        f"{summary.get('known_value_total', 0)}"
        + (f" (rate {_fmt_float(kv_rate)})" if kv_rate is not None else "")
    )
    if summary.get("mean_best_score") is not None:
        lines.append(
            f"- mean_best_score: {_fmt_float(summary.get('mean_best_score'))}  "
            f"max_best_score: {_fmt_float(summary.get('max_best_score'))}"
        )
    lines.append(
        f"- store_growth: {summary.get('store_growth', 0)}  "
        f"store_distance: {_fmt_float(summary.get('store_distance'))}"
    )
    if summary.get("stopped_early"):
        lines.append("- stopped_early: true")
    js = campaign.get("journal_summary") or {}
    if js:
        lines.append(f"- journal_events: {js.get('total_events', 'n/a')}")

    # per-question table
    if questions:
        lines.append("\n## Questions\n")
        lines.append("| # | verdict | score | kv | competed | iterate | question |")
        lines.append("|--:|---------|------:|---:|----------|--------:|----------|")
        for q in questions:
            ranking = q.get("hypothesis_ranking") or []
            best = ranking[0].get("score") if ranking else None
            kv = q.get("known_value_checks") or {}
            kv_s = (
                f"{kv.get('n_passed', 0)}/{kv.get('n_checks', 0)}"
                if kv.get("n_checks") else "—"
            )
            qtext = str(q.get("question", ""))[:48].replace("|", "/")
            lines.append(
                f"| {q.get('index', '')} | {q.get('verdict', '')[:28]} | "
                f"{_fmt_float(best) if best is not None else '—'} | {kv_s} | "
                f"{'Y' if q.get('competed') else 'N'} | "
                f"{q.get('iterate_rounds') or 0} | {qtext} |"
            )

    # detailed sections
    for q in questions:
        lines.append("\n---\n")
        # synthesize a pseudo run-result for reuse
        pseudo = {
            "question": q.get("question"),
            "conclusion": {
                "verdict": q.get("verdict"),
                "evidence": q.get("evidence"),
                "verification": {},  # not always copied
                "foundations": q.get("foundations"),
                "hypothesis_ranking": q.get("hypothesis_ranking"),
                "known_value_checks": q.get("known_value_checks"),
                "competed": q.get("compete") or q.get("competed"),
                "iterate_rounds": q.get("iterate_rounds"),
            },
        }
        lines.append(render_single_run(pseudo).rstrip())

    return "\n".join(lines) + "\n"


def write_report(text: str, path: str) -> str:
    import os

    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path
