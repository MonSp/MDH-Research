"""L12: CLI facade for ResearchLoop / campaign / report / journal analytics.

Usage:
    python -m orchestrator.cli run "What is the scalar curvature of Schwarzschild?"
    python -m orchestrator.cli campaign q1.txt q2.txt --report out.md
    python -m orchestrator.cli report --campaign-json campaign.json -o report.md
    python -m orchestrator.cli analytics --journal-dir data/journal
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from typing import Any


def _ensure_paths() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.dirname(here)
    root = os.path.dirname(src)
    build = os.path.join(root, "build", "src", "bindings")
    for p in (src, build):
        if p not in sys.path:
            sys.path.insert(0, p)


def _make_loop(log_dir: str | None, llm: bool | None, memory_path: str | None = None):
    from .journal import ResearchJournal
    from .research_loop import ResearchLoop

    d = log_dir or tempfile.mkdtemp(prefix="mdh-research-")
    os.makedirs(d, exist_ok=True)
    return ResearchLoop(
        journal=ResearchJournal(log_dir=d),
        llm_client=llm,
        memory_path=memory_path,
    )


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def cmd_run(args: argparse.Namespace) -> int:
    _ensure_paths()
    llm = None if args.llm == "auto" else (args.llm == "on")
    loop = _make_loop(args.log_dir, llm, memory_path=args.memory)
    result = loop.run(args.question)
    if args.json:
        _print_json(result.get("conclusion"))
    else:
        from .report import render_single_run

        print(render_single_run(result))
    return 0


def cmd_campaign(args: argparse.Namespace) -> int:
    _ensure_paths()
    from .campaign import run_campaign
    from .report import render_campaign, write_report

    questions: list[str] = []
    for item in args.questions:
        if os.path.isfile(item):
            with open(item, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        questions.append(line)
        else:
            questions.append(item)
    if not questions:
        print("no questions", file=sys.stderr)
        return 2

    log_dir = args.log_dir or tempfile.mkdtemp(prefix="mdh-campaign-")
    llm = None if args.llm == "auto" else (args.llm == "on")

    def factory():
        return _make_loop(log_dir, llm, memory_path=args.memory)

    out = run_campaign(
        questions,
        loop_factory=factory,
        share_store=not args.fresh_store,
        stop_on_verified=args.stop_on_verified,
    )
    if args.json:
        _print_json(out.get("summary"))
    else:
        md = render_campaign(out)
        print(md)
        if args.report:
            write_report(md, args.report)
            print(f"wrote {args.report}", file=sys.stderr)
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    _ensure_paths()
    from .report import render_campaign, render_single_run, write_report

    with open(args.campaign_json, encoding="utf-8") as f:
        data = json.load(f)
    # campaign output vs single run
    if "summary" in data or "questions" in data:
        md = render_campaign(data)
    else:
        md = render_single_run(data)
    if args.output:
        write_report(md, args.output)
        print(f"wrote {args.output}")
    else:
        print(md)
    return 0


def cmd_analytics(args: argparse.Namespace) -> int:
    _ensure_paths()
    from .journal_analytics import compare_sessions, load_journal_dir, render_analytics

    sessions = load_journal_dir(args.journal_dir)
    if not sessions:
        print(f"no journals in {args.journal_dir}", file=sys.stderr)
        return 2
    summary = compare_sessions(sessions)
    if args.json:
        _print_json(summary)
    else:
        print(render_analytics(summary))
    return 0


def cmd_bench(args: argparse.Namespace) -> int:
    _ensure_paths()
    from .benchmark import render_benchmark, run_benchmark

    llm = None if args.llm == "auto" else (args.llm == "on")
    summary = run_benchmark(suite_path=args.suite, llm=llm)
    if args.json:
        _print_json(summary)
    else:
        print(render_benchmark(summary))
    # non-zero if any case failed
    return 0 if summary.get("n_passed", 0) == summary.get("n_cases", 0) else 1


def cmd_memory(args: argparse.Namespace) -> int:
    _ensure_paths()
    from .hypothesis_memory import (
        inject_memory_candidates,
        load_memory,
        memory_summary,
        recall_hypotheses,
    )

    if args.action == "summary":
        summary = memory_summary(args.path)
        _print_json(summary)
        return 0
    if args.action == "list":
        mem = load_memory(args.path)
        if args.json:
            _print_json(mem)
        else:
            for e in mem:
                tools = " → ".join(e.get("tools") or [])
                print(f"[{e.get('score')}] {tools}  | {str(e.get('prediction'))[:60]}")
        return 0
    if args.action == "recall":
        if not args.question:
            print("recall requires --question", file=sys.stderr)
            return 2
        rec = recall_hypotheses(args.question, path=args.path, limit=args.limit)
        _print_json(rec)
        return 0
    if args.action == "inject":
        if not args.question:
            print("inject requires --question", file=sys.stderr)
            return 2
        hyps = inject_memory_candidates(args.question, path=args.path, limit=args.limit)
        _print_json(hyps)
        return 0
    print(f"unknown memory action: {args.action}", file=sys.stderr)
    return 2


def cmd_known_values(args: argparse.Namespace) -> int:
    _ensure_paths()
    from .known_values import DEFAULT_CATALOG_PATH, load_catalog

    cat = load_catalog(args.path)
    if args.json:
        _print_json({"path": args.path or DEFAULT_CATALOG_PATH, "entries": cat})
        return 0
    print(f"catalog: {args.path or DEFAULT_CATALOG_PATH} ({len(cat)} entries)")
    for e in cat:
        print(f"- {e.get('id')} [{e.get('kind')}] tool={e.get('tool')} {e.get('description','')}")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    _ensure_paths()
    from .api import main as api_main

    return api_main(["--host", args.host, "--port", str(args.port)])


def cmd_trend(args: argparse.Namespace) -> int:
    _ensure_paths()
    from .trend import aggregate_campaigns, render_trend

    out = aggregate_campaigns(args.path)
    if args.json:
        _print_json(out)
    else:
        print(render_trend(out))
    return 0 if out.get("n_files", 0) > 0 else 2


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="orchestrator", description="MDH-Research CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_llm(sp):
        sp.add_argument(
            "--llm", choices=("auto", "on", "off"), default="auto",
            help="LLM policy (default auto: use LLM_API_KEY if set)",
        )

    run = sub.add_parser("run", help="Run one research question")
    run.add_argument("question")
    run.add_argument("--log-dir", default=None)
    run.add_argument("--json", action="store_true")
    run.add_argument(
        "--memory", default=None,
        help="Enable hypothesis memory at PATH (opt-in)",
    )
    add_llm(run)
    run.set_defaults(func=cmd_run)

    camp = sub.add_parser("campaign", help="Run multiple questions")
    camp.add_argument("questions", nargs="+", help="Question strings or files with one question per line")
    camp.add_argument("--log-dir", default=None)
    camp.add_argument("--report", default=None, help="Write markdown report to path")
    camp.add_argument("--json", action="store_true", help="Print summary JSON only")
    camp.add_argument("--fresh-store", action="store_true")
    camp.add_argument("--stop-on-verified", action="store_true")
    camp.add_argument(
        "--memory", default=None,
        help="Enable hypothesis memory at PATH (opt-in)",
    )
    add_llm(camp)
    camp.set_defaults(func=cmd_campaign)

    rep = sub.add_parser("report", help="Render report from saved campaign/run JSON")
    rep.add_argument("--campaign-json", required=True)
    rep.add_argument("-o", "--output", default=None)
    rep.set_defaults(func=cmd_report)

    ana = sub.add_parser("analytics", help="Cross-session journal analytics")
    ana.add_argument("--journal-dir", required=True)
    ana.add_argument("--json", action="store_true")
    ana.set_defaults(func=cmd_analytics)

    ben = sub.add_parser("bench", help="Run golden benchmark suite")
    ben.add_argument("--suite", default=None, help="Path to golden_questions.json")
    ben.add_argument("--json", action="store_true")
    add_llm(ben)
    ben.set_defaults(func=cmd_bench)

    mem = sub.add_parser("memory", help="Hypothesis memory store operations")
    mem.add_argument("action", choices=("summary", "list", "recall", "inject"))
    mem.add_argument("--path", default=None)
    mem.add_argument("--question", default=None)
    mem.add_argument("--limit", type=int, default=3)
    mem.add_argument("--json", action="store_true")
    mem.set_defaults(func=cmd_memory)

    kv = sub.add_parser("known-values", help="List extensible known-value catalog")
    kv.add_argument("--path", default=None, help="Catalog JSON path")
    kv.add_argument("--json", action="store_true")
    kv.set_defaults(func=cmd_known_values)

    serve = sub.add_parser("serve", help="Start HTTP API (requires fastapi+uvicorn)")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8080)
    serve.set_defaults(func=cmd_serve)

    trend = sub.add_parser("trend", help="Aggregate campaign JSON reports over time")
    trend.add_argument("path", help="Directory, file, or glob of campaign JSON reports")
    trend.add_argument("--json", action="store_true")
    trend.set_defaults(func=cmd_trend)

    return p


def main(argv: list[str] | None = None) -> int:
    _ensure_paths()
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
