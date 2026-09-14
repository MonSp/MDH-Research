"""Tests for the four integration layers:
1. Skill manifests
2. ResearchJournal
3. ResearchLoop
4. Agent-kernel bridge
"""

import sys
import os
import json
import tempfile
import pytest

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

rc = pytest.importorskip("_research_core")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))


# ─── Layer 1: Skill Manifests ─────────────────────────────────────

class TestSkillManifests:
    def test_skill_mapping_loads(self):
        """research-skill-mapping.json should be valid JSON."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "research-skill-mapping.json")
        with open(path) as f:
            mapping = json.load(f)
        assert len(mapping) >= 15
        assert "symbolic_compute" in mapping
        assert "differential_geometry" in mapping

    def test_skill_mapping_structure(self):
        """Each skill should have required fields."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "research-skill-mapping.json")
        with open(path) as f:
            mapping = json.load(f)
        for name, skill in mapping.items():
            if name.startswith("_"):
                continue
            assert "gameAbility" in skill, f"{name} missing gameAbility"
            assert "category" in skill, f"{name} missing category"
            assert "description" in skill, f"{name} missing description"

    def test_skill_files_exist(self):
        """Skill SKILL.md files should exist."""
        base = os.path.join(os.path.dirname(__file__), "..", "..", "skills")
        for name in ["research-compute", "research-analyze", "research-experiment", "research-report"]:
            path = os.path.join(base, name, "SKILL.md")
            assert os.path.exists(path), f"Missing {path}"


# ─── Layer 2: ResearchJournal ─────────────────────────────────────

class TestResearchJournal:
    def test_journal_creation(self):
        """Journal should create with local fallback."""
        from orchestrator.journal import ResearchJournal
        with tempfile.TemporaryDirectory() as tmpdir:
            j = ResearchJournal(log_dir=tmpdir)
            assert j._log_path is not None

    def test_log_hypothesis(self):
        """Should log hypothesis and return ID."""
        from orchestrator.journal import ResearchJournal, EventType
        with tempfile.TemporaryDirectory() as tmpdir:
            j = ResearchJournal(log_dir=tmpdir)
            h_id = j.log_hypothesis("Is R=0?", "Yes for Schwarzschild")
            assert h_id is not None
            events = j.get_events(EventType.HYPOTHESIS)
            assert len(events) == 1

    def test_log_experiment(self):
        """Should log experiment linked to hypothesis."""
        from orchestrator.journal import ResearchJournal, EventType
        with tempfile.TemporaryDirectory() as tmpdir:
            j = ResearchJournal(log_dir=tmpdir)
            h_id = j.log_hypothesis("Is R=0?", "Yes")
            e_id = j.log_experiment("compute_scalar_curvature", {"metric": "schwarzschild"}, h_id)
            assert e_id is not None
            events = j.get_events(EventType.EXPERIMENT)
            assert len(events) == 1
            assert events[0]["parent_id"] == h_id

    def test_log_observation(self):
        """Should log observation linked to experiment."""
        from orchestrator.journal import ResearchJournal, EventType
        with tempfile.TemporaryDirectory() as tmpdir:
            j = ResearchJournal(log_dir=tmpdir)
            h_id = j.log_hypothesis("test", "prediction")
            e_id = j.log_experiment("tool", {}, h_id)
            o_id = j.log_observation(e_id, {"value": 0}, duration_ms=42)
            assert o_id is not None
            events = j.get_events(EventType.OBSERVATION)
            assert events[0]["payload"]["duration_ms"] == 42

    def test_log_conclusion(self):
        """Should log conclusion linked to hypothesis."""
        from orchestrator.journal import ResearchJournal, EventType
        with tempfile.TemporaryDirectory() as tmpdir:
            j = ResearchJournal(log_dir=tmpdir)
            h_id = j.log_hypothesis("test", "prediction")
            c_id = j.log_conclusion(h_id, "confirmed", ["evidence1"])
            assert c_id is not None

    def test_hypothesis_chain(self):
        """Should retrieve full hypothesis chain."""
        from orchestrator.journal import ResearchJournal
        with tempfile.TemporaryDirectory() as tmpdir:
            j = ResearchJournal(log_dir=tmpdir)
            h_id = j.log_hypothesis("Q", "P")
            e_id = j.log_experiment("tool", {}, h_id)
            j.log_observation(e_id, "result")
            j.log_conclusion(h_id, "confirmed")

            chain = j.get_hypothesis_chain(h_id)
            assert chain["hypothesis"] is not None
            assert len(chain["experiments"]) == 1
            assert len(chain["observations"]) == 1
            assert len(chain["conclusions"]) == 1

    def test_journal_summary(self):
        """Summary should count events by type."""
        from orchestrator.journal import ResearchJournal
        with tempfile.TemporaryDirectory() as tmpdir:
            j = ResearchJournal(log_dir=tmpdir)
            j.log_hypothesis("Q", "P")
            j.log_note("a note")
            summary = j.summary()
            assert summary["total_events"] == 2

    def test_tool_call_logging(self):
        """Should log tool calls."""
        from orchestrator.journal import ResearchJournal, EventType
        with tempfile.TemporaryDirectory() as tmpdir:
            j = ResearchJournal(log_dir=tmpdir)
            j.log_tool_call("compute_christoffel", {"metric": "test"}, {"result": 42}, 15.3)
            events = j.get_events(EventType.TOOL_CALL)
            assert events[0]["payload"]["tool"] == "compute_christoffel"

    def test_error_logging(self):
        """Should log errors."""
        from orchestrator.journal import ResearchJournal, EventType
        with tempfile.TemporaryDirectory() as tmpdir:
            j = ResearchJournal(log_dir=tmpdir)
            j.log_error("experiment", "division by zero")
            events = j.get_events(EventType.ERROR)
            assert events[0]["payload"]["error"] == "division by zero"


# ─── Layer 3: ResearchLoop ────────────────────────────────────────

class TestResearchLoop:
    def test_loop_creation(self):
        """ResearchLoop should initialize with tools."""
        from orchestrator.research_loop import ResearchLoop
        loop = ResearchLoop()
        assert len(loop.tools) >= 5

    def test_loop_flat_curvature(self):
        """Loop should answer 'What is the scalar curvature of flat spacetime?'"""
        from orchestrator.research_loop import ResearchLoop
        with tempfile.TemporaryDirectory() as tmpdir:
            from orchestrator.journal import ResearchJournal
            j = ResearchJournal(log_dir=tmpdir)
            loop = ResearchLoop(journal=j)
            result = loop.run("What is the scalar curvature of Minkowski spacetime?")
            assert result["question"] is not None
            assert len(result["results"]) > 0

    def test_loop_hawking(self):
        """Loop should handle Hawking temperature question."""
        from orchestrator.research_loop import ResearchLoop
        with tempfile.TemporaryDirectory() as tmpdir:
            from orchestrator.journal import ResearchJournal
            j = ResearchJournal(log_dir=tmpdir)
            loop = ResearchLoop(journal=j)
            result = loop.run("What is the Hawking temperature?")
            assert len(result["results"]) > 0

    def test_loop_records_journal(self):
        """Loop should record all events to journal."""
        from orchestrator.research_loop import ResearchLoop
        from orchestrator.journal import ResearchJournal
        with tempfile.TemporaryDirectory() as tmpdir:
            j = ResearchJournal(log_dir=tmpdir)
            loop = ResearchLoop(journal=j)
            loop.run("What is the curvature of flat spacetime?")
            summary = j.summary()
            assert summary["total_events"] >= 3  # hypothesis + experiment + conclusion


# ─── Layer 4: Agent-kernel bridge ─────────────────────────────────

class TestKernelBridge:
    def test_bridge_import(self):
        """Bridge module should import without error."""
        from orchestrator.kernel_bridge import AgentKernelBridge
        bridge = AgentKernelBridge("/tmp/nonexistent.sock")
        assert bridge.socket_path == "/tmp/nonexistent.sock"

    def test_bridge_connect_fails_gracefully(self):
        """Connection to nonexistent socket should raise."""
        from orchestrator.kernel_bridge import AgentKernelBridge
        bridge = AgentKernelBridge("/tmp/nonexistent-kernel.sock")
        with pytest.raises(Exception):
            bridge.connect()

    def test_skill_mapping_path_exists(self):
        """Skill mapping JSON should exist at expected path."""
        path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "research-skill-mapping.json")
        assert os.path.exists(path)
        with open(path) as f:
            data = json.load(f)
        assert "symbolic_compute" in data
