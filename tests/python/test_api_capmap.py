"""Tests for L28 HTTP capmap endpoints + CI fastapi fix."""

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


class TestAPICapmap:
    def test_capmap_endpoint(self, client):
        r = client.get("/capmap")
        assert r.status_code == 200
        data = r.json()
        assert data["summary"]["n_ok"] >= 15
        assert data["summary"]["n_tools"] >= 70
        assert "Platform Capability Map" in data["markdown"]
        assert "L27" in data["markdown"] or "L25" in data["markdown"]

    def test_capmap_check_readme_in_sync(self, client):
        # write then check (ensures markers match current introspection)
        from orchestrator.capability_map import sync_readme

        root = os.path.join(os.path.dirname(__file__), "..", "..")
        for name in ("README.md", "README_en.md"):
            p = os.path.join(root, name)
            if os.path.isfile(p):
                sync_readme(p)
        r = client.get("/capmap/check-readme")
        assert r.status_code == 200
        data = r.json()
        assert data["in_sync"] is True
        assert data["stale"] == []


class TestCIWorkflowDeps:
    def test_workflow_installs_fastapi(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..",
            ".github", "workflows", "golden-bench.yml",
        )
        with open(path, encoding="utf-8") as f:
            text = f.read()
        assert "fastapi" in text
        assert "uvicorn" in text
        assert "capmap --check-readme" in text
