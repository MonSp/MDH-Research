"""Tests for L24 HTTP checkpoint endpoints."""

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


class TestAPICheckpoint:
    def test_checkpoint_save_show_list(self, client, tmp_path):
        path = str(tmp_path / "api_ckpt.json")
        r = client.post("/checkpoint", json={
            "question": "What is the scalar curvature of Schwarzschild spacetime?",
            "label": "api-sch",
            "path": path,
            "llm": False,
        })
        assert r.status_code == 200
        data = r.json()
        assert data["verdict"] == "Hypotheses verified"
        assert os.path.isfile(data["path"])

        r2 = client.get("/checkpoint/show", params={"path": data["path"]})
        assert r2.status_code == 200
        show = r2.json()
        assert show["checkpoint"]["verdict"] == "Hypotheses verified"
        assert "Hypotheses verified" in show["markdown"]

        r3 = client.get("/checkpoint/list", params={"path": str(tmp_path)})
        assert r3.status_code == 200
        items = r3.json()["items"]
        assert len(items) >= 1

    def test_checkpoint_save_empty_question(self, client):
        r = client.post("/checkpoint", json={"question": ""})
        assert r.status_code == 400

    def test_checkpoint_show_missing(self, client):
        r = client.get("/checkpoint/show", params={"path": "/no/such/ckpt.json"})
        assert r.status_code == 404
