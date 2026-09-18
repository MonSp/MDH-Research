"""Tests for L12 orchestrator CLI facade."""

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
from orchestrator.metric_store import reset_store


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


class TestCLI:
    def test_run_text(self, capsys):
        code = main([
            "run",
            "What is the scalar curvature of Schwarzschild spacetime?",
            "--llm", "off",
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "Question" in out
        assert "Verdict" in out

    def test_run_json(self, capsys):
        code = main([
            "run",
            "What is the scalar curvature of Schwarzschild spacetime?",
            "--llm", "off", "--json",
        ])
        assert code == 0
        data = json.loads(capsys.readouterr().out)
        assert "verdict" in data
        assert data.get("verdict") == "Hypotheses verified"

    def test_campaign_and_report_file(self, capsys, tmp_path):
        report = str(tmp_path / "c.md")
        code = main([
            "campaign",
            "What is the scalar curvature of Schwarzschild spacetime?",
            "--llm", "off",
            "--report", report,
        ])
        assert code == 0
        out = capsys.readouterr().out
        assert "Research Campaign Report" in out
        assert os.path.isfile(report)
        assert "Schwarzschild" in open(report, encoding="utf-8").read()

    def test_campaign_questions_file(self, capsys, tmp_path):
        qfile = tmp_path / "qs.txt"
        qfile.write_text(
            "# comment\nWhat is the scalar curvature of Schwarzschild spacetime?\n",
            encoding="utf-8",
        )
        code = main(["campaign", str(qfile), "--llm", "off", "--json"])
        assert code == 0
        data = json.loads(capsys.readouterr().out)
        assert data["n_questions"] >= 1
        assert data["n_verified"] >= 1

    def test_analytics(self, capsys, tmp_path):
        jdir = tmp_path / "journals"
        jdir.mkdir()
        # generate a journal via CLI run
        main([
            "run",
            "What is the scalar curvature of Schwarzschild spacetime?",
            "--llm", "off",
            "--log-dir", str(jdir),
        ])
        code = main(["analytics", "--journal-dir", str(jdir)])
        assert code == 0
        out = capsys.readouterr().out
        assert "Journal Analytics" in out
        assert "sessions" in out.lower()

    def test_report_from_saved_json(self, capsys, tmp_path):
        jp = tmp_path / "run.json"
        # save a fake single-run conclusion
        jp.write_text(json.dumps({
            "question": "q",
            "conclusion": {
                "verdict": "Hypotheses verified",
                "evidence": ["CONFIRMED: x"],
                "verification": {"numeric_confirmed": 1, "symbolic_confirmed": 0,
                                  "residual_gates": []},
                "foundations": {},
                "hypothesis_ranking": [],
                "known_value_checks": {},
            },
        }), encoding="utf-8")
        code = main(["report", "--campaign-json", str(jp)])
        assert code == 0
        out = capsys.readouterr().out
        assert "Hypotheses verified" in out

    def test_analytics_missing_dir(self, capsys):
        code = main(["analytics", "--journal-dir", "/no/such/dir"])
        assert code == 2
