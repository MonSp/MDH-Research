"""Tests for L23 research checkpoint snapshots."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.checkpoint import (
    checkpoint_to_run_result,
    list_checkpoints,
    load_checkpoint,
    render_checkpoint,
    save_checkpoint,
)
from orchestrator.cli import main
from orchestrator.journal import ResearchJournal
from orchestrator.metric_store import reset_store
from orchestrator.report import render_single_run
from orchestrator.research_loop import ResearchLoop


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


def _run():
    loop = ResearchLoop(
        journal=ResearchJournal(log_dir=tempfile.mkdtemp() if False else __import__("tempfile").mkdtemp()),
        llm_client=False,
    )
    return loop.run("What is the scalar curvature of Schwarzschild spacetime?")


class TestCheckpoint:
    def test_save_load_run(self, tmp_path):
        result = _run()
        p = save_checkpoint(result, path=str(tmp_path / "c.json"), label="schwarzschild")
        assert os.path.isfile(p)
        ckpt = load_checkpoint(p)
        assert ckpt["kind"] == "run"
        assert ckpt["verdict"] == "Hypotheses verified"
        md = render_checkpoint(ckpt)
        assert "Hypotheses verified" in md

    def test_checkpoint_to_report(self, tmp_path):
        result = _run()
        p = save_checkpoint(result, path=str(tmp_path / "c2.json"))
        ckpt = load_checkpoint(p)
        pseudo = checkpoint_to_run_result(ckpt)
        md = render_single_run(pseudo)
        assert "Hypotheses verified" in md

    def test_list_checkpoints(self, tmp_path):
        result = _run()
        save_checkpoint(result, path=str(tmp_path / "a.json"), label="a")
        items = list_checkpoints(str(tmp_path))
        assert len(items) == 1
        assert items[0]["label"] == "a"

    def test_cli_checkpoint_save_and_show(self, tmp_path, capsys):
        out = str(tmp_path / "cli_ckpt.json")
        code = main([
            "checkpoint", "save",
            "--question", "What is the scalar curvature of Schwarzschild spacetime?",
            "--llm", "off",
            "--path", out,
            "--label", "cli",
            "--json",
        ])
        assert code == 0
        data = json.loads(capsys.readouterr().out)
        assert os.path.isfile(data["path"])
        code2 = main(["checkpoint", "show", "--path", data["path"], "--json"])
        assert code2 == 0
        ckpt = json.loads(capsys.readouterr().out)
        assert ckpt["verdict"] == "Hypotheses verified"
