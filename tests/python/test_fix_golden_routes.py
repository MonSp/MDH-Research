"""Failing tests for Research issues: golden-bench pattern routing + fisher zero-step."""

from __future__ import annotations

import os
import sys
import warnings

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.journal import ResearchJournal
from orchestrator.metric_store import reset_store
from orchestrator.research_loop import ResearchLoop
import tempfile


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


def _pattern_tools(question: str) -> list[str]:
    loop = ResearchLoop(
        journal=ResearchJournal(log_dir=tempfile.mkdtemp(prefix="pat-")),
        llm_client=False,
    )
    hyps = loop._hypothesize_patterns(question)
    tools: list[str] = []
    for h in hyps:
        if h.get("tool"):
            tools.append(str(h["tool"]))
        for s in h.get("tools") or []:
            tools.append(s if isinstance(s, str) else str(s.get("tool") or ""))
    return tools


class TestPatternRoutesForGoldenBench:
    def test_chirp_mass_routes_to_chirp_tool(self):
        tools = _pattern_tools(
            "What is the chirp mass of a 30+30 solar mass binary?"
        )
        assert "chirp_mass" in tools, tools

    def test_qnm_routes_to_quasinormal_tool(self):
        tools = _pattern_tools(
            "What are the Schwarzschild quasinormal mode frequencies?"
        )
        assert any(t in tools for t in ("schwarzschild_qnm", "qnm_spectrum")), tools

    def test_unknown_query_still_has_fallback(self):
        tools = _pattern_tools("something entirely unknown xyz")
        assert tools, "fallback should still produce a tool"


class TestFisherZeroParameterStep:
    def test_fisher_no_zero_denominator_warnings(self):
        from orchestrator.gw_analysis import fisher_matrix

        f = np.geomspace(20, 500, 50)
        M_c = 30 * 1.989e30
        # defaults: t_c=0, phi_c=0 → fractional step would be 0
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            result = fisher_matrix(f, M_c)
        bad = [w for w in rec if issubclass(w.category, RuntimeWarning)]
        assert not bad, [str(w.message) for w in bad]
        assert "fisher_matrix" in result

    def test_fisher_zero_phi_c_finite_derivative(self):
        from orchestrator.gw_analysis import fisher_matrix

        f = np.geomspace(20, 500, 50)
        M_c = 30 * 1.989e30
        with warnings.catch_warnings():
            warnings.simplefilter("error", RuntimeWarning)
            result = fisher_matrix(f, M_c, t_c=0.0, phi_c=0.0)
        # M_c block should be finite after zero-step fix
        assert np.isfinite(result["fisher_matrix"][0, 0])
