"""Tests for L27 capmap README CI gate."""

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
    readme_capability_synced,
    sync_readme,
)
from orchestrator.cli import main


class TestCheckReadme:
    def test_check_passes_when_synced(self, capsys, tmp_path):
        # write current table then check
        code = main(["capmap", "--write-readme"])
        assert code == 0
        code = main(["capmap", "--check-readme"])
        assert code == 0
        assert "in sync" in capsys.readouterr().out

    def test_check_fails_when_stale(self, tmp_path):
        # create a stale marker block in a temp file and verify helper
        p = tmp_path / "README.md"
        p.write_text(
            f"{BEGIN_MARK}\nSTALE_XYZ\n{END_MARK}\n",
            encoding="utf-8",
        )
        assert readme_capability_synced(str(p)) is False
        sync_readme(str(p))
        assert readme_capability_synced(str(p)) is True

    def test_check_cli_flags_present(self):
        from orchestrator.cli import build_parser

        parser = build_parser()
        for action in parser._actions:
            if getattr(action, "choices", None) and "capmap" in action.choices:
                cap = action.choices["capmap"]
                flags = [a for a in cap._actions if getattr(a, "option_strings", None)]
                opts = [o for f in flags for o in f.option_strings]
                assert "--check-readme" in opts
                assert "--write-readme" in opts
                return
        raise AssertionError("capmap subcommand not found")

    def test_workflow_has_check_step(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..",
            ".github", "workflows", "golden-bench.yml",
        )
        with open(path, encoding="utf-8") as f:
            text = f.read()
        assert "capmap --check-readme" in text


class TestCoreLayersStillOk:
    def test_no_core_missing(self):
        from orchestrator.capability_map import detect_capabilities

        rows = {r["level"]: r["status"] for r in detect_capabilities()}
        for lvl in ("L1", "L4", "L12", "L13", "L19", "L23", "L25"):
            assert rows[lvl] == "ok", f"{lvl}={rows[lvl]}"
