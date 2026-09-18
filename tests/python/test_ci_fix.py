"""Tests for L16: golden-bench CI workflow fix (pybind11_DIR)."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)


class TestGoldenBenchWorkflow:
    def _load(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "..",
            ".github", "workflows", "golden-bench.yml",
        )
        with open(path, encoding="utf-8") as f:
            text = f.read()
        try:
            import yaml

            return text, yaml.safe_load(text)
        except ImportError:
            return text, None

    def test_installs_pybind11(self):
        text, _ = self._load()
        assert "pybind11" in text
        assert "pip install" in text

    def test_passes_pybind11_dir_to_cmake(self):
        text, _ = self._load()
        assert "pybind11_DIR" in text
        assert "get_cmake_dir" in text or "--cmakedir" in text

    def test_steps_order(self):
        _, doc = self._load()
        if doc is None:
            pytest.skip("PyYAML missing")
        names = [s.get("name") for s in doc["jobs"]["test-and-bench"]["steps"]]
        assert "Install Python deps" in names
        assert "Configure C++ core" in names
        assert "Build" in names
        assert "Python tests" in names
        assert "Golden benchmark" in names
        # install must come before configure
        assert names.index("Install Python deps") < names.index("Configure C++ core")

    def test_bench_llm_off(self):
        text, _ = self._load()
        assert "bench --llm off" in text
