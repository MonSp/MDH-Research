"""Tests for L25 platform capability map."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.capability_map import (
    capability_summary,
    detect_capabilities,
    render_capability_map,
)
from orchestrator.cli import main


class TestCapabilityMap:
    def test_detect_rows(self):
        rows = detect_capabilities()
        levels = {r["level"] for r in rows}
        assert "L1" in levels
        assert "L13" in levels
        assert "L24" in levels
        assert len(rows) >= 20

    def test_core_layers_ok(self):
        rows = {r["level"]: r for r in detect_capabilities()}
        assert rows["L1"]["status"] == "ok"
        assert rows["L4"]["status"] == "ok"
        assert rows["L12"]["status"] == "ok"
        assert rows["L19"]["status"] == "ok"

    def test_render_contains_levels(self):
        md = render_capability_map()
        assert "Platform Capability Map" in md
        assert "L1" in md
        assert "HTTP API" in md or "L19" in md

    def test_cli_capmap(self, capsys):
        code = main(["capmap", "--json"])
        assert code == 0
        data = json.loads(capsys.readouterr().out)
        assert data["n_ok"] >= 15
        assert data["n_tools"] >= 70
        assert data["n_golden"] >= 8
