"""Tests for L21 HTTP API trend + report endpoints."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.metric_store import reset_store


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


@pytest.fixture
def client():
    try:
        from fastapi.testclient import TestClient
    except ImportError:
        pytest.skip("fastapi/httpx test client not installed")
    from orchestrator.api import create_app

    return TestClient(create_app())


def _write_campaign(path, verify_rate, n_verified=1, n_questions=2):
    data = {
        "summary": {
            "n_questions": n_questions,
            "n_verified": n_verified,
            "verify_rate": verify_rate,
            "known_value_passed": 1,
            "known_value_total": 1,
            "known_value_rate": 1.0,
            "mean_best_score": 3.0,
            "n_competed": 0,
            "n_iterated": 0,
        },
        "questions": [{"index": 0, "verdict": "Hypotheses verified"}],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


class TestAPIExt:
    def test_trend_endpoint(self, client, tmp_path):
        _write_campaign(tmp_path / "r1.json", 0.5)
        _write_campaign(tmp_path / "r2.json", 1.0)
        r = client.post("/trend", json={"path": str(tmp_path)})
        assert r.status_code == 200
        data = r.json()
        assert data["n_files"] == 2
        assert data["verify_rate_improved"] is True

    def test_trend_markdown(self, client, tmp_path):
        _write_campaign(tmp_path / "a.json", 0.2)
        _write_campaign(tmp_path / "b.json", 0.9)
        r = client.post("/trend", json={"path": str(tmp_path), "markdown": True})
        assert r.status_code == 200
        data = r.json()
        assert "Campaign Trend" in data["markdown"]
        assert data["summary"]["verify_rate_improved"] is True

    def test_trend_missing_path(self, client):
        r = client.post("/trend", json={"path": ""})
        assert r.status_code == 400

    def test_report_endpoint_markdown(self, client, tmp_path):
        p = tmp_path / "c.json"
        _write_campaign(p, 1.0)
        r = client.post("/report", json={"campaign_json": str(p)})
        assert r.status_code == 200
        data = r.json()
        assert "Research Campaign Report" in data["markdown"]

    def test_report_write_file(self, client, tmp_path):
        p = tmp_path / "c.json"
        out = tmp_path / "out.md"
        _write_campaign(p, 0.8)
        r = client.post("/report", json={
            "campaign_json": str(p),
            "output": str(out),
            "markdown": False,
        })
        assert r.status_code == 200
        assert r.json()["written"] is True
        assert os.path.isfile(out)

    def test_report_missing_file(self, client):
        r = client.post("/report", json={"campaign_json": "/no/such/file.json"})
        assert r.status_code == 404

    def test_analytics_endpoint(self, client, tmp_path):
        from orchestrator.journal import ResearchJournal
        from orchestrator.research_loop import ResearchLoop

        jdir = tmp_path / "j"
        jdir.mkdir()
        loop = ResearchLoop(
            journal=ResearchJournal(log_dir=str(jdir)),
            llm_client=False,
        )
        loop.run("What is the scalar curvature of Schwarzschild spacetime?")
        r = client.get("/analytics", params={"journal_dir": str(jdir)})
        assert r.status_code == 200
        data = r.json()
        assert data["n_sessions"] >= 1
        assert data["total_events"] > 0
