"""Tests for L15 platform integration: CLI --memory + CI artifacts."""

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
from orchestrator.hypothesis_memory import load_memory
from orchestrator.metric_store import reset_store


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


class TestCLIMemoryFlag:
    def test_run_with_memory(self, capsys, tmp_path):
        mem = str(tmp_path / "m.json")
        code = main([
            "run",
            "What is the scalar curvature of Schwarzschild spacetime?",
            "--llm", "off",
            "--memory", mem,
            "--json",
        ])
        assert code == 0
        data = json.loads(capsys.readouterr().out)
        assert data.get("verdict") == "Hypotheses verified"
        assert data.get("memory_entries", 0) >= 1
        assert load_memory(mem)

    def test_run_without_memory_leaves_file_missing(self, capsys, tmp_path):
        mem = str(tmp_path / "unused.json")
        code = main([
            "run",
            "What is the scalar curvature of Schwarzschild spacetime?",
            "--llm", "off",
            "--json",
        ])
        assert code == 0
        assert not os.path.isfile(mem)

    def test_campaign_with_memory(self, capsys, tmp_path):
        mem = str(tmp_path / "camp.json")
        code = main([
            "campaign",
            "What is the scalar curvature of Schwarzschild spacetime?",
            "What is the age of the universe?",
            "--llm", "off",
            "--memory", mem,
            "--json",
        ])
        assert code == 0
        data = json.loads(capsys.readouterr().out)
        assert data["n_questions"] >= 2
        assert os.path.isfile(mem)


class TestCIWorkflow:
    def test_workflow_file_exists_and_parses(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..",
            ".github", "workflows", "golden-bench.yml",
        )
        assert os.path.isfile(path)
        try:
            import yaml  # type: ignore
        except ImportError:
            pytest.skip("PyYAML not installed")
        with open(path, encoding="utf-8") as f:
            doc = yaml.safe_load(f)
        assert doc["name"] == "golden-bench"
        steps = doc["jobs"]["test-and-bench"]["steps"]
        names = [s.get("name") for s in steps]
        assert "Python tests" in names
        assert "Golden benchmark" in names
        # memory stays off in CI (deterministic)
        bench = next(s for s in steps if s.get("name") == "Golden benchmark")
        assert "bench --llm off" in bench["run"]
