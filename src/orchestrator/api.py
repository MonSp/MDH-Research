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

    @app.get("/known-values")
    def known_values(path: Optional[str] = None):
        from .known_values import DEFAULT_CATALOG_PATH, load_catalog

        return {"path": path or DEFAULT_CATALOG_PATH, "entries": load_catalog(path)}

    @app.get("/memory/summary")
    def memory_summary(path: Optional[str] = None):
        from .hypothesis_memory import memory_summary as ms

        return ms(path)

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
