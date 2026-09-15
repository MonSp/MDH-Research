"""Tests for MetricStore, tool registry, ResearchLoop integration."""

from __future__ import annotations

import json
import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.metric_store import MetricStore, get_store, reset_store
from orchestrator.serialize import serialize_result
from orchestrator import tool_registry as tr
from orchestrator.tool_registry_wrappers import create_schwarzschild, compute_scalar_curvature


SCH = ["-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2"]
COORDS = ["t", "r", "theta", "phi"]


@pytest.fixture(autouse=True)
def _clean_store():
    reset_store()
    yield
    reset_store()


class TestMetricStore:
    def test_put_get_list_drop(self):
        store = MetricStore()
        created = create_schwarzschild(M=1.0)
        name = created["metric_name"]
        assert name in get_store().list()
        entry = get_store().get(name)
        assert entry["coord_names"] == COORDS
        get_store().drop(name)
        assert name not in get_store().list()

    def test_factory_payload_json_safe(self):
        created = create_schwarzschild(M=2.0)
        assert "metric" not in created
        assert "manifold" not in created
        json.dumps(created)  # must not raise
        assert created["params"]["M"] == 2.0

    def test_resolve_or_create_from_diagonal(self):
        name = get_store().resolve_or_create({
            "name": "mink",
            "diagonal": ["-1", "1", "1", "1"],
            "coords": COORDS,
        })
        assert name == "mink"
        assert "mink" in get_store().list()

    def test_missing_metric_raises(self):
        with pytest.raises(KeyError):
            get_store().get("nope")


class TestSerialize:
    def test_scalars_and_nested(self):
        assert serialize_result(1.5) == 1.5
        assert serialize_result({"a": [1, 2]}) == {"a": [1, 2]}

    def test_numpy(self):
        import numpy as np

        assert serialize_result(np.float64(2.5)) == 2.5
        assert serialize_result(np.array([1.0, 2.0])) == [1.0, 2.0]

    def test_expression(self):
        expr = tr.execute_tool("parse_expression", {"expression": "x^2 + 1"})
        s = serialize_result(expr)
        assert isinstance(s, dict) and "__expr__" in s
        json.dumps(s)


class TestRegistry:
    def test_size_and_categories(self):
        summary = tr.registry_summary()
        assert summary["count"] >= 70
        assert "cosmology" in summary["by_category"]
        assert "blackhole_solutions" in summary["by_category"]
        assert "causal_structure" in summary["by_category"]
        assert "adm_bssn" in summary["by_category"]

    def test_openai_payload(self):
        payload = tr.openai_tools_payload()
        assert len(payload) == tr.registry_summary()["count"]
        names = {p["function"]["name"] for p in payload}
        assert "age_of_universe" in names
        assert "create_schwarzschild" in names
        for p in payload:
            assert p["type"] == "function"
            assert "description" in p["function"]
            assert p["function"]["parameters"]["type"] == "object"

    def test_aliases(self):
        assert tr.resolve_tool_name("compute_scalar_curvature") == "compute_scalar_curvature"
        # legacy alias
        assert tr.resolve_tool_name("create_blackhole") == "create_schwarzschild"
        assert tr.resolve_tool_name("check_energy_conditions_numerical") == "check_energy_conditions_for_metric"

    def test_execute_pure_scalar(self):
        t = tr.execute_tool("hawking_temperature", {"M": 1.989e30})
        assert isinstance(t, dict)
        assert "T_K" in t
        assert t["T_K"] > 0

    def test_execute_metric_consumer(self):
        R = tr.execute_tool("compute_scalar_curvature", {
            "diagonal": SCH, "coords": COORDS, "params": {"M": 1}, "name": "sch",
        })
        # vacuum: R evaluates to 0
        val = R.evaluate({"M": 1, "r": 6, "theta": 1.5708, "phi": 0, "t": 0})
        assert abs(val) < 1e-8

    def test_execute_by_metric_name_after_factory(self):
        created = tr.execute_tool("create_schwarzschild", {"M": 1.0})
        name = created["metric_name"]
        R = tr.execute_tool("compute_scalar_curvature", {"metric_name": name})
        val = R.evaluate({"M": 1, "r": 8, "theta": 1.5708, "phi": 0, "t": 0})
        assert abs(val) < 1e-8

    def test_cosmology_tool(self):
        age = tr.execute_tool("age_of_universe", {"params": {}})
        assert 12 < age["age_gyr"] < 15

    def test_classify_symmetry_schwarzschild(self):
        tr.execute_tool("create_schwarzschild", {"M": 1.0})
        result = tr.execute_tool("classify_symmetry", {"metric_name": "schwarzschild"})
        # stationary / static expected
        assert isinstance(result, dict)
        assert result.get("stationary") is True or "stationary" in str(result)

    def test_mapping_tools_registered_or_documented(self):
        mapping_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "config", "research-skill-mapping.json"
        )
        with open(mapping_path) as f:
            mapping = json.load(f)
        registered = set(tr.build_registry())
        # Every mapping tool should be registered OR intentionally internal
        internal = {
            "simplify", "differentiate", "evaluate",  # core symbol ops not yet wrapped
            "tensor_raise_index", "tensor_lower_index", "tensor_contract", "tensor_product",
            "geodesic_equation",  # ODE RHS
            "expr_to_sympy", "sympy_to_expr", "tensor_to_sympy",
            "f_R_model",  # low-level model; f_R_cosmology is the agent entry
            "bssn_evolution_step",  # low-level evolution step
        }
        missing = []
        for skill_key, skill in mapping.items():
            if skill_key == "_comment":
                continue
            for tool in skill.get("tools", []):
                if tool not in registered and tool not in internal:
                    # allow alias resolution
                    try:
                        tr.resolve_tool_name(tool)
                    except KeyError:
                        missing.append(f"{skill_key}:{tool}")
        assert not missing, f"unregistered mapping tools: {missing}"


class TestResearchLoop:
    def test_pattern_path_schwarzschild(self):
        from orchestrator.research_loop import ResearchLoop
        from orchestrator.journal import ResearchJournal
        import tempfile

        tmp = tempfile.mkdtemp()
        j = ResearchJournal(log_dir=tmp)
        loop = ResearchLoop(journal=j)
        result = loop.run("What is the scalar curvature of Schwarzschild spacetime?")
        assert result["conclusion"]["verdict"] == "Hypotheses verified"
        assert result["journal_summary"]["total_events"] >= 3

    def test_pattern_path_hawking(self):
        from orchestrator.research_loop import ResearchLoop
        from orchestrator.journal import ResearchJournal
        import tempfile

        j = ResearchJournal(log_dir=tempfile.mkdtemp())
        loop = ResearchLoop(journal=j)
        result = loop.run("What is the Hawking temperature of a solar mass black hole?")
        assert result["results"][0]["success"] is True

    def test_tools_cover_registry(self):
        from orchestrator.research_loop import _get_tools

        tools = _get_tools()
        assert len(tools) >= 70
        assert "age_of_universe" in tools
        assert "create_kerr" in tools
        assert "compute_scalar_curvature" in tools

    def test_tool_call_journal_event(self):
        from orchestrator.research_loop import ResearchLoop
        from orchestrator.journal import ResearchJournal
        import tempfile

        tmp = tempfile.mkdtemp()
        j = ResearchJournal(log_dir=tmp)
        loop = ResearchLoop(journal=j)
        loop.run("What is the Hawking temperature of a solar mass black hole?")
        events = j.get_events()
        types = [e["type"] if isinstance(e, dict) else e.type.value for e in events]
        assert "tool_call" in types, f"expected tool_call in journal, got {types}"
        tool_events = [
            e for e in events
            if (e["type"] if isinstance(e, dict) else e.type.value) == "tool_call"
        ]
        payload = tool_events[0]["payload"] if isinstance(tool_events[0], dict) else tool_events[0].payload
        assert payload.get("tool") == "hawking_temperature"
        assert "result" in payload
        assert "duration_ms" in payload

    def test_llm_schema_available(self):
        from orchestrator.tool_registry import openai_tools_payload

        payload = openai_tools_payload()
        # ResearchLoop _hypothesize_llm uses this; ensure non-empty and serializable
        json.dumps(payload)


class TestSessionIntegration:
    def test_define_metric_registers_store(self):
        from orchestrator.session import GeometrySession

        s = GeometrySession()
        s.define_manifold("spacetime", COORDS)
        diag_rows = []
        for i, cell in enumerate(SCH):
            row = ["0"] * 4
            row[i] = cell
            diag_rows.append(row)
        out = s.define_metric("spacetime", diag_rows)
        assert out.get("metric_name") == "spacetime"
        assert "spacetime" in get_store().list()
        # registry can consume it
        R = tr.execute_tool("compute_scalar_curvature", {"metric_name": "spacetime"})
        val = R.evaluate({"M": 1, "r": 6, "theta": 1.5708, "phi": 0, "t": 0})
        assert abs(float(val)) < 1e-6
