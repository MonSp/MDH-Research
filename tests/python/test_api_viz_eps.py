"""L44: POST /viz returns sensitivity alongside markdown/csv."""

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


SWEEP_Q = (
    "How does Hawking temperature vary as a function of mass? "
    "Scan several masses."
)


class TestVizSensitivity:
    def test_sweep_returns_sensitivity(self, client):
        r = client.post("/viz", json={"question": SWEEP_Q, "llm": False})
        assert r.status_code == 200
        data = r.json()
        assert "sensitivity" in data
        sens = data["sensitivity"]
        assert isinstance(sens, dict)
        assert sens.get("elasticity") == pytest.approx(-1.0, rel=1e-3)

    def test_non_sweep_sensitivity_none(self, client):
        r = client.post("/viz", json={
            "question": "What is the scalar curvature of Schwarzschild spacetime?",
            "llm": False,
        })
        assert r.status_code == 200
        data = r.json()
        assert "sensitivity" in data
        # no sweep → null/empty elasticity
        sens = data["sensitivity"]
        if sens:
            assert sens.get("elasticity") in (None, "")

    def test_existing_fields_preserved(self, client):
        r = client.post("/viz", json={"question": SWEEP_Q, "llm": False})
        data = r.json()
        assert "markdown" in data
        assert "csv" in data
        assert "verdict" in data
