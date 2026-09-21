"""Tests for L26 capmap README sync."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.capability_map import (
    BEGIN_MARK,
    END_MARK,
    detect_capabilities,
    readme_capability_synced,
    render_level_table,
    sync_readme,
)
from orchestrator.cli import main


class TestRenderLevelTable:
    def test_table_has_levels(self):
        t = render_level_table()
        assert "| Level | Name | Status |" in t
        assert "L1" in t
        assert "L25" in t


class TestSyncReadme:
    def test_sync_creates_markers(self, tmp_path):
        p = tmp_path / "README.md"
        p.write_text("# Demo\n\ntext\n", encoding="utf-8")
        sync_readme(str(p))
        text = p.read_text(encoding="utf-8")
        assert BEGIN_MARK in text
        assert END_MARK in text
        assert readme_capability_synced(str(p)) is True

    def test_sync_updates_in_place(self, tmp_path):
        p = tmp_path / "README.md"
        p.write_text(
            f"# T\n\n{BEGIN_MARK}\nSTALE_MARKER_XYZ\n{END_MARK}\n\nend\n",
            encoding="utf-8",
        )
        sync_readme(str(p))
        text = p.read_text(encoding="utf-8")
        assert "STALE_MARKER_XYZ" not in text
        assert "| Level |" in text
        assert text.rstrip().endswith("end")
        assert readme_capability_synced(str(p)) is True

    def test_not_synced_when_stale(self, tmp_path):
        p = tmp_path / "README.md"
        p.write_text(
            f"{BEGIN_MARK}\n| stale |\n{END_MARK}\n",
            encoding="utf-8",
        )
        assert readme_capability_synced(str(p)) is False

    def test_cli_write_readme(self, capsys):
        code = main(["capmap", "--write-readme", "--json"])
        assert code == 0
        import json

        data = json.loads(capsys.readouterr().out)
        assert "README.md" in data["written"]
        root = os.path.join(os.path.dirname(__file__), "..", "..")
        assert readme_capability_synced(os.path.join(root, "README.md"))
        assert readme_capability_synced(os.path.join(root, "README_en.md"))


class TestCoreLayersStillOk:
    def test_no_core_missing(self):
        rows = {r["level"]: r["status"] for r in detect_capabilities()}
        for lvl in ("L1", "L4", "L12", "L13", "L19", "L23", "L25"):
            assert rows[lvl] == "ok", f"{lvl}={rows[lvl]}"
