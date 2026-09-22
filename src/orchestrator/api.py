"""L19: HTTP API facade for the research platform.

Thin FastAPI app over ResearchLoop / campaign / bench / known-values.
Optional import so unit tests without FastAPI can still collect.
"""

import os
import sys
import tempfile
from typing import Any, Optional


def _ensure_paths() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    src = os.path.dirname(here)
    root = os.path.dirname(src)
    build = os.path.join(root, "build", "src", "bindings")
    for p in (src, build):
        if p not in sys.path:
            sys.path.insert(0, p)


def _make_loop(llm=False, memory_path=None):
    from .journal import ResearchJournal
    from .research_loop import ResearchLoop

    return ResearchLoop(
        journal=ResearchJournal(log_dir=tempfile.mkdtemp(prefix="mdh-api-")),
        llm_client=llm,
        memory_path=memory_path,
    )


def create_app() -> Any:
    """Build FastAPI application. Raises ImportError if FastAPI missing."""
    _ensure_paths()
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, Field

    app = FastAPI(title="MDH-Research API", version="0.1.0")

    class RunRequest(BaseModel):
        question: str
        llm: Optional[bool] = False
        memory_path: Optional[str] = None

    class CampaignRequest(BaseModel):
        questions: list = Field(default_factory=list)
        llm: Optional[bool] = False
        memory_path: Optional[str] = None
        stop_on_verified: bool = False
        fresh_store: bool = False

    class BenchRequest(BaseModel):
        suite_path: Optional[str] = None
        llm: Optional[bool] = False

    class TrendRequest(BaseModel):
        path: str
        markdown: bool = False

    class ReportRequest(BaseModel):
        campaign_json: str
        output: Optional[str] = None
        markdown: bool = True

    @app.get("/health")
    def health():
        from .tool_registry import registry_summary

        return {"ok": True, "n_tools": registry_summary().get("count")}

    @app.post("/run")
    def run(req: RunRequest):
        if not req.question:
            raise HTTPException(status_code=400, detail="question required")
        loop = _make_loop(llm=req.llm, memory_path=req.memory_path)
        out = loop.run(req.question)
        return out.get("conclusion") or {}

    @app.post("/campaign")
    def campaign(req: CampaignRequest):
        if not req.questions:
            raise HTTPException(status_code=400, detail="questions required")
        from .campaign import run_campaign

        out = run_campaign(
            req.questions,
            loop_factory=lambda: _make_loop(llm=req.llm, memory_path=req.memory_path),
            share_store=not req.fresh_store,
            stop_on_verified=req.stop_on_verified,
        )
        return out.get("summary") or {}

    @app.post("/bench")
    def bench(req: BenchRequest):
        from .benchmark import run_benchmark

        return run_benchmark(suite_path=req.suite_path, llm=req.llm)

    @app.post("/trend")
    def trend(req: TrendRequest):
        if not req.path:
            raise HTTPException(status_code=400, detail="path required")
        from .trend import aggregate_campaigns, render_trend

        out = aggregate_campaigns(req.path)
        if req.markdown:
            return {"markdown": render_trend(out), "summary": out}
        return out

    @app.post("/report")
    def report(req: ReportRequest):
        if not req.campaign_json:
            raise HTTPException(status_code=400, detail="campaign_json required")
        if not os.path.isfile(req.campaign_json):
            raise HTTPException(status_code=404, detail=f"not found: {req.campaign_json}")
        from .report import render_campaign, render_single_run, write_report
        import json as _json

        with open(req.campaign_json, encoding="utf-8") as f:
            data = _json.load(f)
        if isinstance(data, dict) and ("summary" in data or "questions" in data):
            md = render_campaign(data)
        else:
            md = render_single_run(data)
        if req.output:
            write_report(md, req.output)
            return {"path": req.output, "written": True}
        return {"markdown": md}

    @app.get("/analytics")
    def analytics(journal_dir: str):
        if not journal_dir:
            raise HTTPException(status_code=400, detail="journal_dir required")
        from .journal_analytics import compare_sessions, load_journal_dir, render_analytics

        sessions = load_journal_dir(journal_dir)
        if not sessions:
            raise HTTPException(status_code=404, detail=f"no journals in {journal_dir}")
        summary = compare_sessions(sessions)
        return summary

    @app.get("/known-values")
    def known_values(path: Optional[str] = None):
        from .known_values import DEFAULT_CATALOG_PATH, load_catalog

        return {"path": path or DEFAULT_CATALOG_PATH, "entries": load_catalog(path)}

    @app.get("/memory/summary")
    def memory_summary(path: Optional[str] = None):
        from .hypothesis_memory import memory_summary as ms

        return ms(path)

    class CheckpointSaveRequest(BaseModel):
        question: str
        label: Optional[str] = None
        path: Optional[str] = None
        llm: Optional[bool] = False
        memory_path: Optional[str] = None

    @app.post("/checkpoint")
    def checkpoint_save(req: CheckpointSaveRequest):
        if not req.question:
            raise HTTPException(status_code=400, detail="question required")
        from .checkpoint import save_checkpoint

        loop = _make_loop(llm=req.llm, memory_path=req.memory_path)
        result = loop.run(req.question)
        path = save_checkpoint(result, path=req.path, label=req.label)
        return {
            "path": path,
            "verdict": (result.get("conclusion") or {}).get("verdict"),
            "label": req.label,
        }

    @app.get("/checkpoint/list")
    def checkpoint_list(path: Optional[str] = None):
        from .checkpoint import list_checkpoints

        return {"items": list_checkpoints(path)}

    @app.get("/checkpoint/show")
    def checkpoint_show(path: str):
        if not path:
            raise HTTPException(status_code=400, detail="path required")
        if not os.path.isfile(path):
            raise HTTPException(status_code=404, detail=f"not found: {path}")
        from .checkpoint import load_checkpoint, render_checkpoint

        ckpt = load_checkpoint(path)
        return {"checkpoint": ckpt, "markdown": render_checkpoint(ckpt)}

    @app.get("/capmap")
    def capmap():
        from .capability_map import capability_summary, render_capability_map

        return {
            "summary": capability_summary(),
            "markdown": render_capability_map(),
        }

    @app.get("/capmap/check-readme")
    def capmap_check_readme():
        from .capability_map import readme_capability_synced
        import os as _os

        root = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "..")
        stale = []
        for name in ("README.md", "README_en.md"):
            p = _os.path.join(root, name)
            if _os.path.isfile(p) and not readme_capability_synced(p):
                stale.append(name)
        return {"in_sync": not stale, "stale": stale}

    return app


def main(argv=None) -> int:
    import argparse

    _ensure_paths()
    parser = argparse.ArgumentParser(prog="research-api")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    try:
        import uvicorn
    except ImportError:
        print("uvicorn not installed", file=sys.stderr)
        return 2
    uvicorn.run(create_app(), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
