"""L35: checkpoints keep slim sweep/grid for report viz + CSV."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.checkpoint import (
    checkpoint_to_run_result,
    load_checkpoint,
    save_checkpoint,
)
from orchestrator.metric_store import reset_store


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


SWEEP_RUN = {
    "question": (
        "How does Hawking temperature vary as a function of mass? "
        "Scan several masses."
    ),
    "conclusion": {"verdict": "Hypotheses verified", "evidence": []},
    "results": [{
        "success": True,
        "steps": [{"tool": "hawking_temperature", "success": True}],
        "sweep": {
            "axis_name": "M",
            "points": [
                {"x": 1e30, "y": 1e-8},
                {"x": 1e31, "y": 1e-9},
            ],
            "trend": {
                "direction": "decreasing", "n": 2,
                "points": [
                    {"x": 1e30, "y": 1e-8},
                    {"x": 1e31, "y": 1e-9},
                ],
            },
        },
    }],
}


class TestCheckpointKeepsSweep:
    def test_saved_checkpoint_has_slim_results(self, tmp_path):
        p = save_checkpoint(SWEEP_RUN, path=str(tmp_path / "s.json"), label="sweep")
        ckpt = load_checkpoint(p)
        results = ckpt.get("results")
        assert results, "checkpoint must carry slim results"
        assert any(r.get("sweep") for r in results)
        # slim: no full step traces
        assert all("steps" not in r for r in results)

    def test_pseudo_run_renders_viz(self, tmp_path):
        from orchestrator.report import render_single_run

        p = save_checkpoint(SWEEP_RUN, path=str(tmp_path / "s.json"))
        ckpt = load_checkpoint(p)
        pseudo = checkpoint_to_run_result(ckpt)
        assert pseudo.get("results")
        md = render_single_run(pseudo)
        assert "Sweep viz" in md or "Sensitivity" in md

    def test_pseudo_run_export_csv(self, tmp_path):
        from orchestrator.sweep_viz import export_run_csv

        p = save_checkpoint(SWEEP_RUN, path=str(tmp_path / "s.json"))
        ckpt = load_checkpoint(p)
        pseudo = checkpoint_to_run_result(ckpt)
        out = str(tmp_path / "x.csv")
        got = export_run_csv(pseudo, out)
        assert got == out
        lines = open(out, encoding="utf-8").read().splitlines()
        assert lines[0] == "x,y"
        assert len(lines) >= 3

    def test_checkpoint_without_sweep_ok(self, tmp_path):
        run = {
            "question": "What is R?",
            "conclusion": {"verdict": "Hypotheses verified"},
            "results": [{"success": True, "steps": [{"tool": "compute_scalar_curvature"}]}],
        }
        p = save_checkpoint(run, path=str(tmp_path / "n.json"))
        ckpt = load_checkpoint(p)
        # non-sweep results dropped (slim only)
        assert ckpt.get("results") in (None, [])
