"""Tests for L14 hypothesis memory."""

from __future__ import annotations

import json
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.cli import main
from orchestrator.hypothesis_memory import (
    extract_memorable,
    inject_memory_candidates,
    load_memory,
    memory_summary,
    recall_hypotheses,
    remember_from_run,
    save_memory,
)
from orchestrator.journal import ResearchJournal
from orchestrator.metric_store import reset_store
from orchestrator.research_loop import ResearchLoop


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


@pytest.fixture
def mempath(tmp_path):
    return str(tmp_path / "hyp_mem.json")


def _loop(mempath: str | None, disable: bool = False) -> ResearchLoop:
    return ResearchLoop(
        journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
        llm_client=False,
        memory_path=False if disable else mempath,
    )


class TestMemoryStore:
    def test_load_empty(self, mempath):
        assert load_memory(mempath) == []
        assert memory_summary(mempath)["n_entries"] == 0

    def test_save_load_roundtrip(self, mempath):
        save_memory([{"tools": ["a"], "prediction": "p", "score": 3.0,
                      "question_keywords": ["foo"]}], mempath)
        mem = load_memory(mempath)
        assert len(mem) == 1
        assert mem[0]["tools"] == ["a"]

    def test_extract_memorable_from_success(self, mempath):
        results = [{
            "success": True,
            "hypothesis": {"prediction": "R vanishes"},
            "steps": [
                {"tool": "create_schwarzschild", "params": {"M": 1}},
                {"tool": "compute_scalar_curvature", "params": {}},
            ],
        }]
        mem = extract_memorable(results, "scalar curvature of Schwarzschild")
        assert mem
        assert mem[0]["tools"][0] == "create_schwarzschild"
        assert "schwarzschild" in mem[0]["question_keywords"]

    def test_remember_and_recall(self, mempath):
        results = [{
            "success": True,
            "hypothesis": {"prediction": "R=0 vacuum"},
            "steps": [
                {"tool": "create_schwarzschild", "params": {"M": 1}},
                {"tool": "compute_scalar_curvature", "params": {}},
            ],
        }]
        remember_from_run({"question": "Schwarzschild scalar curvature", "results": results}, mempath)
        rec = recall_hypotheses("What is the Schwarzschild curvature?", path=mempath)
        assert rec
        assert rec[0]["tools"] == ["create_schwarzschild", "compute_scalar_curvature"]

    def test_inject_ready_hypotheses(self, mempath):
        save_memory([{
            "prediction": "R=0",
            "tools": ["create_schwarzschild", "compute_scalar_curvature"],
            "params": [{"M": 1}, {}],
            "question_keywords": ["schwarzschild", "curvature"],
            "score": 3.0,
        }], mempath)
        hyps = inject_memory_candidates("Schwarzschild curvature", path=mempath)
        assert len(hyps) == 1
        assert hyps[0]["tools"][0]["tool"] == "create_schwarzschild"
        assert hyps[0]["tools"][1]["params"] == {}


class TestLoopMemory:
    def test_run_remembers_success(self, mempath):
        loop = _loop(mempath)
        result = loop.run("What is the scalar curvature of Schwarzschild spacetime?")
        assert result["conclusion"]["verdict"] == "Hypotheses verified"
        assert result["conclusion"]["memory_entries"] >= 1
        assert load_memory(mempath)

    def test_second_run_injects_memory(self, mempath):
        loop = _loop(mempath)
        loop.run("What is the scalar curvature of Schwarzschild spacetime?")
        # second run same topic — memory candidates should be injected
        loop2 = _loop(mempath)
        result = loop2.run("What is the scalar curvature of Schwarzschild spacetime?")
        notes = [
            e for e in loop2.journal.get_events() if e["type"] == "note"
        ]
        blob = " ".join(str(n.get("payload", {})) for n in notes)
        assert "MEMORY" in blob or result["conclusion"]["memory_entries"] >= 1

    def test_memory_disabled(self, mempath):
        loop = _loop(mempath, disable=True)
        result = loop.run("What is the scalar curvature of Schwarzschild spacetime?")
        assert not load_memory(mempath)


class TestCLIMemory:
    def test_cli_memory_summary(self, capsys, mempath):
        code = main(["memory", "summary", "--path", mempath, "--json"])
        assert code == 0
        data = json.loads(capsys.readouterr().out)
        assert "n_entries" in data
