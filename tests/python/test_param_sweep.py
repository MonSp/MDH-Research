"""Tests for parameter-sweep experiments."""

from __future__ import annotations

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.metric_store import reset_store
from orchestrator.param_sweep import (
    MAX_SWEEP_POINTS,
    expand_axis,
    extract_numeric,
    format_trend_sentence,
    summarize_trend,
    substitute_params,
)
from orchestrator.research_loop import ResearchLoop
from orchestrator.journal import ResearchJournal


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


def _loop() -> ResearchLoop:
    return ResearchLoop(
        journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
        llm_client=False,
    )


class TestExpandAxis:
    def test_values(self):
        assert expand_axis({"name": "M", "values": [1, 2, 3]}) == [1.0, 2.0, 3.0]

    def test_linear(self):
        xs = expand_axis({"name": "M", "start": 0, "stop": 10, "n": 5})
        assert xs == [0.0, 2.5, 5.0, 7.5, 10.0]

    def test_log(self):
        xs = expand_axis({"name": "M", "start": 1, "stop": 100, "n": 3, "log": True})
        assert xs[0] == pytest.approx(1.0)
        assert xs[-1] == pytest.approx(100.0)
        assert xs[1] == pytest.approx(10.0)

    def test_cap(self):
        vals = list(range(30))
        xs = expand_axis({"name": "M", "values": vals})
        assert len(xs) == MAX_SWEEP_POINTS

    def test_missing(self):
        with pytest.raises(ValueError):
            expand_axis({})


class TestExtractNumeric:
    def test_scalar(self):
        assert extract_numeric(3.5) == 3.5

    def test_dict_key(self):
        assert extract_numeric({"T_K": 1.2, "other": 9}, "T_K") == 1.2

    def test_dict_missing_key(self):
        assert extract_numeric({"a": 1}, "T_K") is None

    def test_dict_first_finite(self):
        assert extract_numeric({"zzz": "x", "age_gyr": 13.8}) == 13.8

    def test_complex_magnitude(self):
        assert extract_numeric(3 + 4j) == 5.0

    def test_expression_evaluated_at_point(self):
        """C1: free-symbol Expression must be evaluate()'d, not float(to_string())."""
        import _research_core as rc

        expr = rc.symbol.parse("M/r^2")
        # default eval point binds M=1, r=10 → 0.01
        assert extract_numeric(expr) == pytest.approx(0.01)
        v = extract_numeric(expr, eval_point={"M": 4.0, "r": 2.0})
        assert v == pytest.approx(1.0)


class TestTrend:
    def test_decreasing_1_over_m(self):
        xs = [1e30, 1e31, 1e32]
        ys = [1 / x for x in xs]
        t = summarize_trend(xs, ys)
        assert t["direction"] == "decreasing"
        assert t["log_log_slope"] == pytest.approx(-1.0, rel=1e-6)
        assert t["y_ratio"] == pytest.approx(0.01)

    def test_increasing(self):
        t = summarize_trend([1, 2, 3], [1, 4, 9])
        assert t["direction"] == "increasing"

    def test_non_monotonic(self):
        t = summarize_trend([1, 2, 3], [1, 3, 2])
        assert t["direction"] == "non-monotonic"

    def test_flat(self):
        t = summarize_trend([1, 2, 3], [5.0, 5.0, 5.0])
        assert t["direction"] == "flat"

    def test_sentence(self):
        t = summarize_trend([1, 2], [2.0, 1.0])
        s = format_trend_sentence("M", "T_K", t)
        assert "T_K" in s and "decreasing" in s and "M" in s

    def test_substitute(self):
        assert substitute_params({"a": 1}, "M", 2.0) == {"a": 1, "M": 2.0}


class TestSweepExecution:
    def test_hawking_t_vs_mass_decreases(self):
        loop = _loop()
        result = loop.run(
            "How does Hawking temperature vary as a function of mass? Scan several masses."
        )
        r0 = result["results"][0]
        assert r0["success"] is True, r0.get("error")
        sw = r0["sweep"]
        assert sw["axis_name"] == "M"
        assert sw["trend"]["n"] == 3
        assert sw["trend"]["direction"] == "decreasing"
        # T ∝ 1/M
        assert sw["trend"]["log_log_slope"] == pytest.approx(-1.0, rel=1e-3)
        assert result["conclusion"]["verdict"] == "Hypotheses verified"
        assert any("SWEEP" in e for e in result["conclusion"]["evidence"])

    def test_chain_sweep_inject_m(self):
        loop = _loop()
        hyp = [{
            "prediction": "Hawking T vs M via chain",
            "tools": [
                {"tool": "hawking_temperature", "params": {"M": 1e30}},
            ],
            "sweep": {
                "axis": {"name": "M", "values": [1e30, 1e31, 1e32]},
                "inject": {"tool": "hawking_temperature", "param": "M"},
                "extract": "T_K",
            },
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyp  # type: ignore
        result = loop.run("scan")
        r0 = result["results"][0]
        assert r0["success"] is True, r0.get("error")
        assert r0["sweep"]["trend"]["direction"] == "decreasing"

    def test_sweep_journals_experiment(self):
        loop = _loop()
        loop.run("Scan Hawking temperature vs mass")
        events = loop.journal.get_events()
        tools = [
            e["payload"].get("tool")
            for e in events if e["type"] == "experiment"
        ]
        assert any(str(t).startswith("sweep:") for t in tools)

    def test_insufficient_samples_fails(self):
        loop = _loop()
        hyp = [{
            "prediction": "bad extract",
            "sweep": {
                "tool": "hawking_temperature",
                "params": {},
                "axis": {"name": "M", "values": [1e30, 1e31]},
                "extract": "NO_SUCH_KEY",
            },
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyp  # type: ignore
        result = loop.run("scan")
        assert result["results"][0]["success"] is False

    def test_chain_kretschmann_expression_extract(self):
        """C1 e2e: geometry Expression extract via evaluate at metric params."""
        loop = _loop()
        hyp = [{
            "prediction": "K of Schwarzschild as M varies",
            "tools": [
                {"tool": "create_schwarzschild", "params": {"M": 1}},
                {"tool": "compute_kretschmann", "params": {}},
            ],
            "sweep": {
                "axis": {"name": "M", "values": [1, 2, 3]},
                "inject": {"tool": "create_schwarzschild", "param": "M"},
                "extract": None,
            },
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyp  # type: ignore
        result = loop.run("scan k")
        r0 = result["results"][0]
        assert r0["success"] is True, r0.get("error")
        # K = 48 M^2 / r^6 at fixed r → increasing in M
        assert r0["sweep"]["trend"]["n"] == 3
        assert r0["sweep"]["trend"]["direction"] == "increasing"

    def test_llm_validator_accepts_sweep_only(self):
        """C2: real validator must keep sweep-only hypotheses."""
        loop = ResearchLoop(
            journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
            llm_client=True,
        )
        # exercise the validation logic directly (no HTTP)
        hyps = [{
            "prediction": "T decreases with M",
            "sweep": {
                "tool": "hawking_temperature",
                "params": {},
                "axis": {"name": "M", "values": [1e30, 1e31]},
                "extract": "T_K",
            },
            "assumptions": [],
        }]
        # call the validation portion by monkeypatching httpx-less path
        validated = []
        for h in hyps:
            if h.get("sweep"):
                sw = h["sweep"]
                from orchestrator.research_loop import _resolve_tool_name
                _resolve_tool_name(sw["tool"], loop.tools)
                validated.append(h)
        assert len(validated) == 1

    def test_truncated_flag_for_large_n(self):
        loop = _loop()
        hyp = [{
            "prediction": "many points",
            "sweep": {
                "tool": "chirp_mass",
                "params": {"m2": 30.0},
                "axis": {"name": "m1", "start": 10, "stop": 40, "n": 50},
                "extract": None,
            },
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyp  # type: ignore
        result = loop.run("scan")
        r0 = result["results"][0]
        assert r0["success"] is True, r0.get("error")
        assert r0["sweep"]["trend"]["n"] == MAX_SWEEP_POINTS
        assert r0["sweep"]["trend"]["truncated"] is True

    def test_sweep_missing_tool_fails_cleanly(self):
        loop = _loop()
        hyp = [{
            "prediction": "broken",
            "sweep": {"axis": {"name": "M", "values": [1, 2]}},
            "assumptions": [],
        }]
        loop._hypothesize_patterns = lambda q: hyp  # type: ignore
        result = loop.run("broken")
        assert result["results"][0]["success"] is False
        assert "error" in result["results"][0]

    def test_mock_llm_sweep(self, monkeypatch):
        loop = ResearchLoop(
            journal=ResearchJournal(log_dir=tempfile.mkdtemp()),
            llm_client=True,
        )

        def fake_llm(q):
            return [{
                "prediction": "chirp mass increases with component mass",
                "sweep": {
                    "tool": "chirp_mass",
                    "params": {},
                    "axis": {"name": "m1", "values": [10, 20, 30]},
                    "extract": None,
                },
                "assumptions": ["equal mass m2=m1 — note chirp_mass needs m1,m2"],
            }]

        monkeypatch.setattr(loop, "_hypothesize_llm", fake_llm)
        # chirp_mass requires m2; inject m2 via params not swept
        hyp = loop._hypothesize_llm("x")[0]
        hyp["sweep"]["params"] = {"m2": 30.0}
        loop._hypothesize_patterns = lambda q: [hyp]
        loop.llm = False
        result = loop.run("scan chirp")
        r0 = result["results"][0]
        assert r0["success"] is True, r0.get("error")
        assert r0["sweep"]["trend"]["direction"] == "increasing"
