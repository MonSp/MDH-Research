"""Tests for L19 HTTP API facade."""

from __future__ import annotations

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


class TestAPI:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is True
        assert data["n_tools"] >= 70

    def test_run_endpoint(self, client):
        r = client.post("/run", json={
            "question": "What is the scalar curvature of Schwarzschild spacetime?",
            "llm": False,
        })
        assert r.status_code == 200
        data = r.json()
        assert data.get("verdict") == "Hypotheses verified"

    def test_run_empty_question(self, client):
        r = client.post("/run", json={"question": ""})
        assert r.status_code == 400

    def test_campaign_endpoint(self, client):
        r = client.post("/campaign", json={
            "questions": [
                "What is the scalar curvature of Schwarzschild spacetime?",
                "What is the age of the universe?",
            ],
            "llm": False,
        })
        assert r.status_code == 200
        data = r.json()
        assert data.get("n_questions") == 2
        assert data.get("n_verified", 0) >= 1

    def test_known_values_endpoint(self, client):
        r = client.get("/known-values")
        assert r.status_code == 200
        data = r.json()
        assert len(data["entries"]) >= 6

    def test_memory_summary_endpoint(self, client):
        r = client.get("/memory/summary")
        assert r.status_code == 200
        assert "n_entries" in r.json()

    def test_bench_endpoint(self, client):
        r = client.post("/bench", json={"llm": False})
        assert r.status_code == 200
        data = r.json()
        assert data["n_cases"] >= 5
        assert "pass_rate" in data


class TestCreateApp:
    def test_create_app_importable(self):
        from orchestrator.api import create_app

        app = create_app()
        assert app is not None
