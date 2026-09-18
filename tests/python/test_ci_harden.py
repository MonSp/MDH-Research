"""Tests for L17 CI hardening (pyyaml collection + workflow deps)."""

from __future__ import annotations

import ast
import os
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


class TestCIHarden:
    def test_platform_test_has_no_top_level_yaml_import(self):
        path = os.path.join(ROOT, "tests", "python", "test_platform_integration.py")
        with open(path, encoding="utf-8") as f:
            tree = ast.parse(f.read())
        top_imports = []
        for node in tree.body:
            if isinstance(node, ast.Import):
                top_imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                top_imports.append(node.module)
        assert "yaml" not in top_imports

    def test_workflow_installs_pyyaml(self):
        path = os.path.join(ROOT, ".github", "workflows", "golden-bench.yml")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        assert "pyyaml" in text.lower() or "PyYAML" in text

    def test_pyproject_dev_includes_pyyaml(self):
        path = os.path.join(ROOT, "pyproject.toml")
        with open(path, encoding="utf-8") as f:
            text = f.read()
        assert "pyyaml" in text.lower()
