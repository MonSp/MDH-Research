"""L34: cli campaign --csv exports merged sweep/grid points."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))
BUILD = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD not in sys.path:
    sys.path.insert(0, BUILD)

from orchestrator.metric_store import reset_store


@pytest.fixture(autouse=True)
def _clean():
    reset_store()
    yield
    reset_store()


SWEEP_Q = (
    "How does Hawking temperature vary as a function of mass? "
    "Scan several masses."
)
CURVE_Q = "What is the scalar curvature of Schwarzschild spacetime?"


class TestCampaignCsvFlag:
    def test_campaign_csv_writes_file(self, tmp_path):
        from orchestrator.cli import main

        path = str(tmp_path / "camp.csv")
        code = main([
            "campaign", SWEEP_Q,
            "--llm", "off",
            "--csv", path,
        ])
        assert code == 0
        assert os.path.isfile(path)
        lines = open(path, encoding="utf-8").read().splitlines()
        assert lines[0] == "x,y"
        assert len(lines) >= 2

    def test_campaign_csv_no_sweep_no_file(self, tmp_path):
        from orchestrator.cli import main

        path = str(tmp_path / "none.csv")
        code = main([
            "campaign", CURVE_Q,
            "--llm", "off",
            "--csv", path,
        ])
        assert code == 0
        assert not os.path.exists(path)

    def test_campaign_csv_json_mode_still_works(self, tmp_path):
        from orchestrator.cli import main

        path = str(tmp_path / "j.csv")
        code = main([
            "campaign", SWEEP_Q,
            "--llm", "off",
            "--json",
            "--csv", path,
        ])
        assert code == 0
        assert os.path.isfile(path)
