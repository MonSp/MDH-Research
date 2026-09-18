"""Tests for L11 cross-session journal analytics."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.journal import ResearchJournal
from orchestrator.journal_analytics import (
    compare_sessions,
    load_journal_dir,
    load_journal_file,
    render_analytics,
    session_metrics,
)
from orchestrator.metric_store import reset_store
from orchestrator.research_loop import ResearchLoop


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


def _run_to_dir(question: str) -> str:
    tmp = tempfile.mkdtemp()
    loop = ResearchLoop(
        journal=ResearchJournal(log_dir=tmp),
        llm_client=False,
    )
    loop.run(question)
    return tmp


class TestLoad:
    def test_load_missing(self):
        assert load_journal_file("/no/such/file.jsonl") == []
        assert load_journal_dir("/no/such/dir") == {}

    def test_load_dir_from_live_runs(self):
        d = _run_to_dir("What is the scalar curvature of Schwarzschild spacetime?")
        sessions = load_journal_dir(d)
        assert len(sessions) == 1
        sid, events = next(iter(sessions.items()))
        assert events
        assert any(e.get("type") == "hypothesis" for e in events)


class TestSessionMetrics:
    def test_metrics_from_live_run(self):
        d = _run_to_dir("What is the scalar curvature of Schwarzschild spacetime?")
        events = next(iter(load_journal_dir(d).values()))
        m = session_metrics(events, session_id="test")
        assert m["n_events"] > 0
        assert m["n_hypothesis"] >= 1
        assert m["n_conclusion"] >= 1
        assert m["session_id"] == "test"

    def test_empty(self):
        m = session_metrics([], session_id="empty")
        assert m["n_events"] == 0
        assert m["observation_success_rate"] is None


class TestCompareAndRender:
    def test_compare_two_sessions(self):
        d1 = _run_to_dir("What is the scalar curvature of Schwarzschild spacetime?")
        d2 = _run_to_dir("What is the age of the universe?")
        # merge into one virtual dir by loading both
        s1 = load_journal_dir(d1)
        s2 = load_journal_dir(d2)
        merged = {}
        merged.update(s1)
        merged.update(s2)
        # ensure distinct keys
        if len(merged) < 2:
            k = next(iter(merged))
            merged[k + "_b"] = merged[k]
        summary = compare_sessions(merged)
        assert summary["n_sessions"] >= 2
        assert summary["total_events"] > 0
        md = render_analytics(summary)
        assert "Journal Analytics" in md
        assert "sessions" in md.lower()

    def test_compete_counts(self):
        d = _run_to_dir("What is the scalar curvature of Schwarzschild spacetime?")
        events = next(iter(load_journal_dir(d).values()))
        m = session_metrics(events)
        assert "n_compete" in m
        assert m["n_compete"] >= 0
