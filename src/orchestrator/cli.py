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


def _make_loop(log_dir: str | None, llm: bool | None):
    from .journal import ResearchJournal
    from .research_loop import ResearchLoop

    d = log_dir or tempfile.mkdtemp(prefix="mdh-research-")
    os.makedirs(d, exist_ok=True)
    return ResearchLoop(journal=ResearchJournal(log_dir=d), llm_client=llm)


def _print_json(obj: Any) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def cmd_run(args: argparse.Namespace) -> int:
    _ensure_paths()
    llm = None if args.llm == "auto" else (args.llm == "on")
    loop = _make_loop(args.log_dir, llm)
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

    def factory():
        return _make_loop(log_dir, llm=None if args.llm == "auto" else (args.llm == "on"))

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
    add_llm(run)
    run.set_defaults(func=cmd_run)

    camp = sub.add_parser("campaign", help="Run multiple questions")
    camp.add_argument("questions", nargs="+", help="Question strings or files with one question per line")
    camp.add_argument("--log-dir", default=None)
    camp.add_argument("--report", default=None, help="Write markdown report to path")
    camp.add_argument("--json", action="store_true", help="Print summary JSON only")
    camp.add_argument("--fresh-store", action="store_true")
    camp.add_argument("--stop-on-verified", action="store_true")
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

    return p


def main(argv: list[str] | None = None) -> int:
    _ensure_paths()
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
