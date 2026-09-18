"""Tests for L18 extensible known-value catalog."""

from __future__ import annotations

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.cli import main
from orchestrator.known_values import (
    DEFAULT_CATALOG_PATH,
    check_result_with_catalog,
    evaluate_catalog_entry,
    load_catalog,
)
from orchestrator.metric_store import reset_store
from orchestrator.tool_registry import execute_tool


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


class TestCatalog:
    def test_default_catalog_loads(self):
        cat = load_catalog()
        assert os.path.isfile(DEFAULT_CATALOG_PATH)
        assert len(cat) >= 6
        ids = {e["id"] for e in cat}
        assert "deflection_angle_positive" in ids
        assert "hubble_parameter_positive" in ids

    def test_formula_deflection(self):
        # lensing tool uses SI constants; catalog uses positivity check
        entry = {
            "id": "deflection_angle_positive",
            "tool": "deflection_angle",
            "kind": "positive",
        }
        observed = execute_tool("deflection_angle", {"M": 1.0, "b": 10.0})
        c = evaluate_catalog_entry(entry, "deflection_angle", observed)
        assert c is not None
        assert c["passed"] is True, c

    def test_formula_hawking_matches_builtin(self):
        entry = {
            "id": "hawking_temperature",
            "tool": "hawking_temperature",
            "kind": "formula",
            "formula": "hawking_T",
            "extract": "T_K",
            "tol_rel": 0.25,
        }
        res = execute_tool("hawking_temperature", {"M": 1.989e30})
        c = evaluate_catalog_entry(
            entry, "hawking_temperature", res, {"M": 1.989e30}
        )
        assert c is not None
        assert c["passed"] is True, c

    def test_positive_hubble(self):
        entry = {
            "id": "hubble_parameter_positive",
            "tool": "hubble_parameter",
            "kind": "positive",
        }
        h = execute_tool("hubble_parameter", {"a": 1.0})
        c = evaluate_catalog_entry(entry, "hubble_parameter", h)
        assert c is not None
        assert c["passed"] is True, c

    def test_wrong_tool_skipped(self):
        entry = {"id": "x", "tool": "age_of_universe", "kind": "positive"}
        assert evaluate_catalog_entry(entry, "hawking_temperature", 1.0) is None

    def test_check_result_with_catalog_includes_builtin_and_new(self):
        res = execute_tool("hawking_temperature", {"M": 1.989e30})
        checks = check_result_with_catalog(
            "hawking_temperature", res, {"M": 1.989e30}
        )
        names = [c["name"] for c in checks]
        assert "hawking_temperature" in names  # builtin
        # catalog has same id — should not duplicate
        assert names.count("hawking_temperature") == 1

    def test_cli_known_values(self, capsys):
        code = main(["known-values", "--json"])
        assert code == 0
        data = json.loads(capsys.readouterr().out)
        assert len(data["entries"]) >= 6

    def test_custom_catalog_path(self, tmp_path):
        p = tmp_path / "cat.json"
        p.write_text(json.dumps([
            {"id": "my_range", "tool": "chirp_mass", "kind": "range", "min": 0, "max": 1000}
        ]), encoding="utf-8")
        cat = load_catalog(str(p))
        assert cat[0]["id"] == "my_range"
        val = execute_tool("chirp_mass", {"m1": 30.0, "m2": 30.0})
        c = evaluate_catalog_entry(cat[0], "chirp_mass", val)
        assert c["passed"] is True
