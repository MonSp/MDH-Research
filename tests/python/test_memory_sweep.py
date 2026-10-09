"""L37: hypothesis memory stores and recalls sweep chains."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.hypothesis_memory import (
    extract_memorable,
    inject_memory_candidates,
    load_memory,
    recall_hypotheses,
    remember_from_run,
)
from orchestrator.metric_store import reset_store


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


def _sweep_run_result() -> dict:
    hyp_sweep = {
        "tool": "hawking_temperature",
        "params": {},
        "axis": {"name": "M", "values": [1e30, 1e31, 1e32]},
        "extract": "T_K",
    }
    xs = [1e30, 1e31, 1e32]
    ys = [6.17e-8, 6.17e-9, 6.17e-10]
    return {
        "question": (
            "How does Hawking temperature vary as a function of mass? "
            "Scan several masses."
        ),
        "results": [{
            "success": True,
            "hypothesis": {
                "prediction": "T decreases as M increases",
                "sweep": hyp_sweep,
            },
            "steps": [{
                "tool": "hawking_temperature",
                "params": {},
                "result": {},
            }],
            "sweep": {
                "axis_name": "M",
                "extract": "T_K",
                "points": [
                    {"x": x, "y": y} for x, y in zip(xs, ys)
                ],
            },
        }],
    }


class TestRememberSweep:
    def test_entry_has_sweep_spec(self, tmp_path):
        path = str(tmp_path / "m.json")
        remember_from_run(_sweep_run_result(), path=path)
        mem = load_memory(path)
        assert mem, "sweep success must be remembered"
        e = mem[0]
        assert e.get("sweep"), e
        assert e["sweep"].get("tool") == "hawking_temperature"
        assert e["sweep"].get("axis", {}).get("name") == "M"
        assert e.get("sensitivity") is not None

    def test_recall_returns_sweep_hyp(self, tmp_path):
        path = str(tmp_path / "m.json")
        remember_from_run(_sweep_run_result(), path=path)
        rec = recall_hypotheses(
            "How does Hawking temperature vary as a function of mass?",
            path=path,
        )
        assert rec
        assert rec[0].get("sweep")

    def test_inject_produces_sweep_hypothesis(self, tmp_path):
        path = str(tmp_path / "m.json")
        remember_from_run(_sweep_run_result(), path=path)
        hyps = inject_memory_candidates(
            "How does Hawking temperature vary as a function of mass?",
            path=path,
        )
        assert hyps
        assert hyps[0].get("sweep")
        assert hyps[0]["sweep"].get("tool") == "hawking_temperature"
        # not a plain tools-only chain
        assert hyps[0].get("tools") in (None, [], [{"tool": "hawking_temperature", "params": {}}])

    def test_non_sweep_still_tools_only(self, tmp_path):
        path = str(tmp_path / "m.json")
        result = {
            "question": "What is the scalar curvature of Schwarzschild spacetime?",
            "results": [{
                "success": True,
                "hypothesis": {"prediction": "R=0"},
                "steps": [
                    {"tool": "create_schwarzschild", "params": {"M": 1}},
                    {"tool": "compute_scalar_curvature", "params": {}},
                ],
            }],
        }
        remember_from_run(result, path=path)
        mem = load_memory(path)
        assert mem
        assert not mem[0].get("sweep")
