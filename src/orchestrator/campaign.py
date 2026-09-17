"""L9: research campaign — multi-question orchestration with shared state.

Runs a sequence of related ResearchLoop questions against a shared
MetricStore and aggregates program-level foundations / rankings.
"""

from __future__ import annotations

from typing import Any, Callable


def default_store_snapshot() -> dict:
    from .metric_store import get_store

    store = get_store()
    try:
        from .agent_math import state_snapshot_from_store

        return state_snapshot_from_store(store.list(), {
            n: store.get(n) for n in store.list()
        })
    except Exception:
        return {"names": store.list()}


def summarize_campaign(question_results: list[dict]) -> dict[str, Any]:
    """Aggregate per-question conclusions into a program summary."""
    n_q = len(question_results)
    n_ok = sum(1 for q in question_results if q.get("verdict") == "Hypotheses verified")
    n_competed = sum(1 for q in question_results if q.get("competed"))
    n_iterated = sum(1 for q in question_results if (q.get("iterate_rounds") or 0) > 0)

    kv_pass = kv_total = 0
    scores: list[float] = []
    tools: set[str] = set()
    for q in question_results:
        kv = q.get("known_value_checks") or {}
        kv_pass += int(kv.get("n_passed") or 0)
        kv_total += int(kv.get("n_checks") or 0)
        for e in q.get("hypothesis_ranking") or []:
            if e.get("score") is not None:
                scores.append(float(e["score"]))
        f = q.get("foundations") or {}
        # foundations may include tool_seq implicitly via unique_tools only
        if f.get("n_steps"):
            pass

    return {
        "n_questions": n_q,
        "n_verified": n_ok,
        "verify_rate": (n_ok / n_q) if n_q else 0.0,
        "n_competed": n_competed,
        "n_iterated": n_iterated,
        "known_value_passed": kv_pass,
        "known_value_total": kv_total,
        "known_value_rate": (kv_pass / kv_total) if kv_total else None,
        "mean_best_score": (sum(scores) / len(scores)) if scores else None,
        "max_best_score": max(scores) if scores else None,
    }


def run_campaign(
    questions: list[str],
    loop_factory: Callable[[], Any] | None = None,
    share_store: bool = True,
    stop_on_verified: bool = False,
) -> dict[str, Any]:
    """Run several research questions as one campaign.

    - share_store: keep MetricStore across questions (default True)
    - stop_on_verified: early-stop remaining questions once one is verified
    """
    from .metric_store import reset_store
    from .research_loop import ResearchLoop
    from .journal import ResearchJournal
    import tempfile

    if not share_store:
        reset_store()

    if loop_factory is None:
        def loop_factory():  # type: ignore
            return ResearchLoop(
                journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
                llm_client=False,
            )

    # one loop / one journal for the whole campaign
    loop = loop_factory()
    store_before = default_store_snapshot()

    question_results: list[dict] = []
    stopped_early = False

    for i, q in enumerate(questions):
        try:
            out = loop.run(q)
            c = out.get("conclusion") or {}
            question_results.append({
                "index": i,
                "question": q,
                "verdict": c.get("verdict"),
                "competed": c.get("competed"),
                "iterate_rounds": c.get("iterate_rounds"),
                "known_value_checks": c.get("known_value_checks"),
                "foundations": c.get("foundations"),
                "hypothesis_ranking": c.get("hypothesis_ranking"),
                "best_hypothesis": c.get("best_hypothesis"),
                "evidence": c.get("evidence"),
                "n_results": len(out.get("results") or []),
            })
        except Exception as e:
            question_results.append({
                "index": i,
                "question": q,
                "verdict": "All experiments failed",
                "error": str(e),
            })
        if stop_on_verified and question_results[-1].get("verdict") == "Hypotheses verified":
            stopped_early = True
            break

    store_after = default_store_snapshot()
    summary = summarize_campaign(question_results)
    summary["stopped_early"] = stopped_early
    # snapshots are {metric_name: fingerprint}
    summary["store_growth"] = len(store_after) - len(store_before)
    # agent_math state distance if fingerprints
    try:
        from .agent_math import state_distance

        summary["store_distance"] = state_distance(store_before, store_after)
    except Exception:
        summary["store_distance"] = None

    return {
        "questions": question_results,
        "summary": summary,
        "journal_summary": loop.journal.summary(),
    }
