"""L43: journal analytics tracks sweep/grid process metrics."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.journal_analytics import (
    compare_sessions,
    load_journal_dir,
    render_analytics,
    session_metrics,
)
from orchestrator.metric_store import reset_store


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


def _events_manual() -> list[dict]:
    return [
        {"id": "e1", "type": "experiment",
         "payload": {"tool": "sweep:hawking_temperature", "params": {}}},
        {"id": "o1", "type": "observation", "parent_id": "e1",
         "payload": {"duration_ms": 12.0, "success": True, "result": {}}},
        {"id": "e2", "type": "experiment",
         "payload": {"tool": "grid:deflection_angle", "params": {}}},
        {"id": "o2", "type": "observation", "parent_id": "e2",
         "payload": {"duration_ms": 30.0, "success": False, "result": {}}},
        {"id": "e3", "type": "experiment",
         "payload": {"tool": "compute_scalar_curvature", "params": {}}},
        {"id": "o3", "type": "observation", "parent_id": "e3",
         "payload": {"duration_ms": 5.0, "success": True, "result": {}}},
    ]


class TestSessionSweepMetrics:
    def test_counts_and_rates(self):
        m = session_metrics(_events_manual(), session_id="s")
        assert m["n_sweep_experiments"] == 2
        assert m["n_sweep_failures"] == 1
        assert m["sweep_failure_rate"] == pytest.approx(0.5)
        assert m["mean_sweep_duration_ms"] == pytest.approx(21.0)

    def test_no_sweep_metrics(self):
        m = session_metrics([], session_id="empty")
        assert m["n_sweep_experiments"] == 0
        assert m["sweep_failure_rate"] is None
        assert m["mean_sweep_duration_ms"] is None


class TestCompareAndRender:
    def test_compare_aggregates(self):
        summary = compare_sessions({"a": _events_manual(), "b": []})
        assert summary["n_sweep_experiments"] == 2
        assert summary["sweep_failure_rate"] == pytest.approx(0.5)
        assert summary["mean_sweep_duration_ms"] == pytest.approx(21.0)

    def test_render_has_sweep_line(self):
        summary = compare_sessions({"a": _events_manual()})
        md = render_analytics(summary)
        assert "sweep" in md.lower()
        assert "failure" in md.lower()


class TestLiveSweepRun:
    def test_live_sweep_journal(self):
        from orchestrator.journal import ResearchJournal
        from orchestrator.research_loop import ResearchLoop

        d = tempfile.mkdtemp()
        loop = ResearchLoop(
            journal=ResearchJournal(log_dir=d),
            llm_client=False,
        )
        loop.run(
            "How does Hawking temperature vary as a function of mass? "
            "Scan several masses."
        )
        sessions = load_journal_dir(d)
        m = session_metrics(next(iter(sessions.values())), session_id="live")
        assert m["n_sweep_experiments"] >= 1
        assert m["n_sweep_failures"] == 0
        assert m["mean_sweep_duration_ms"] is not None
