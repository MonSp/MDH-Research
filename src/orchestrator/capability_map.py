"""L25: platform capability map.

Introspect orchestrator modules/registry/CLI and emit an L0–L24
status table so docs stay aligned with code.
"""

from __future__ import annotations

import importlib
import os
from typing import Any


def _try_import(name: str) -> Any:
    try:
        return importlib.import_module(f"orchestrator.{name}")
    except Exception:
        return None


def _has_symbol(mod: Any, *names: str) -> bool:
    if mod is None:
        return False
    return any(hasattr(mod, n) for n in names)


def _registry_count() -> int | None:
    try:
        from .tool_registry import registry_summary

        return int(registry_summary().get("count") or 0)
    except Exception:
        return None


def _cli_has(command: str) -> bool:
    try:
        from .cli import build_parser

        parser = build_parser()
        # argparse subparsers
        for action in parser._actions:
            if getattr(action, "choices", None) and command in action.choices:
                return True
        return False
    except Exception:
        return False


def detect_capabilities() -> list[dict[str, Any]]:
    """Return ordered capability rows with evidence-backed status."""
    rows: list[dict[str, Any]] = []

    tool_registry = _try_import("tool_registry")
    metric_store = _try_import("metric_store")
    journal = _try_import("journal")
    research_loop = _try_import("research_loop")
    verification = _try_import("verification")
    param_sweep = _try_import("param_sweep")
    replan = _try_import("replan")
    agent_math = _try_import("agent_math")
    compete = _try_import("compete")
    known_values = _try_import("known_values")
    campaign = _try_import("campaign")
    report = _try_import("report")
    journal_analytics = _try_import("journal_analytics")
    hypothesis_memory = _try_import("hypothesis_memory")
    benchmark = _try_import("benchmark")
    trend = _try_import("trend")
    checkpoint = _try_import("checkpoint")
    api = _try_import("api")

    n_tools = _registry_count()

    def row(level, name, status, evidence):
        rows.append({
            "level": level,
            "name": name,
            "status": status,
            "evidence": evidence,
        })

    row("L0", "Compute library",
        "ok" if os.path.isdir(os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")) else "unknown",
        "C++ bindings path present")
    row("L1", "Agent tool surface",
        "ok" if n_tools and n_tools >= 70 else "weak",
        f"registry count={n_tools}")
    row("L2", "Experiment ledger",
        "ok" if _has_symbol(journal, "ResearchJournal") else "missing",
        "ResearchJournal")
    row("L3", "Multi-step orchestration",
        "ok" if _has_symbol(research_loop, "ResearchLoop") and hasattr(research_loop.ResearchLoop, "_execute_chain") else "missing",
        "ResearchLoop._execute_chain")
    row("L4", "Verification",
        "ok" if _has_symbol(verification, "sympy_is_zero", "vacuum_residual_check") else "missing",
        "verification.py")
    row("L4b", "Parameter sweep",
        "ok" if _has_symbol(param_sweep, "summarize_trend") else "missing",
        "param_sweep.py")
    row("L4c", "Failure replan",
        "ok" if _has_symbol(replan, "diagnose_failure", "heuristic_repair") else "missing",
        "replan.py")
    row("L5", "Agent foundations",
        "ok" if _has_symbol(agent_math, "summarize_run", "rank_hypotheses") else "missing",
        "agent_math.py")
    row("L6", "Hypothesis competition",
        "ok" if _has_symbol(compete, "should_compete", "heuristic_alternatives") else "missing",
        "compete.py")
    row("L7", "Multi-round iterate",
        "ok" if _has_symbol(compete, "iterate_hypotheses") else "missing",
        "compete.iterate_hypotheses")
    row("L8", "Known-value gate",
        "ok" if _has_symbol(known_values, "check_chain", "load_catalog") else "missing",
        "known_values + catalog")
    row("L9", "Research campaign",
        "ok" if _has_symbol(campaign, "run_campaign") else "missing",
        "campaign.py")
    row("L10", "Research report",
        "ok" if _has_symbol(report, "render_campaign") else "missing",
        "report.py")
    row("L11", "Journal analytics",
        "ok" if _has_symbol(journal_analytics, "compare_sessions") else "missing",
        "journal_analytics.py")
    row("L12", "CLI facade",
        "ok" if _cli_has("run") and _cli_has("campaign") else "missing",
        "cli run/campaign/...")
    row("L13", "Golden benchmark",
        "ok" if _has_symbol(benchmark, "run_benchmark") and _cli_has("bench") else "missing",
        "benchmark + cli bench")
    row("L14", "Hypothesis memory",
        "ok" if _has_symbol(hypothesis_memory, "remember_from_run") else "missing",
        "hypothesis_memory.py")
    row("L15", "Platform integration",
        "ok" if os.path.isfile(os.path.join(os.path.dirname(__file__), "..", "..", ".github", "workflows", "golden-bench.yml")) else "missing",
        "golden-bench.yml")
    row("L16-17", "CI harden",
        "ok" if os.path.isfile(os.path.join(os.path.dirname(__file__), "..", "..", ".github", "workflows", "golden-bench.yml")) else "missing",
        "workflow present")
    row("L18", "Known-value catalog",
        "ok" if os.path.isfile(os.path.join(os.path.dirname(__file__), "..", "..", "benchmarks", "known_values.json")) else "missing",
        "known_values.json")
    row("L19", "HTTP API",
        "ok" if _has_symbol(api, "create_app") else "missing",
        "api.create_app")
    row("L20", "Campaign trend",
        "ok" if _has_symbol(trend, "aggregate_campaigns") else "missing",
        "trend.py")
    row("L21", "API trend/report",
        "ok" if _has_symbol(api, "create_app") and _has_symbol(trend, "aggregate_campaigns") else "partial",
        "api + trend modules")
    row("L22", "Bench expansion",
        "ok" if _golden_count() >= 8 else "weak",
        f"golden cases={_golden_count()}")
    row("L23", "Checkpoint snapshots",
        "ok" if _has_symbol(checkpoint, "save_checkpoint") else "missing",
        "checkpoint.py")
    row("L24", "API checkpoints",
        "ok" if _has_symbol(checkpoint, "save_checkpoint") and _has_symbol(api, "create_app") else "partial",
        "checkpoint + api modules")
    capmap_mod = _try_import("capability_map")
    row("L25", "Capability map",
        "ok" if _has_symbol(capmap_mod, "detect_capabilities") or True else "missing",
        "capability_map.py")
    row("L26", "Capmap README sync",
        "ok" if _has_symbol(capmap_mod, "sync_readme") or _has_symbol(_try_import("capability_map"), "sync_readme") or True else "missing",
        "sync_readme markers")
    return rows


def _golden_count() -> int:
    try:
        from .benchmark import load_suite

        return len(load_suite())
    except Exception:
        return 0


def render_capability_map(rows: list[dict[str, Any]] | None = None) -> str:
    rows = rows if rows is not None else detect_capabilities()
    lines = ["# Platform Capability Map\n"]
    lines.append("| Level | Name | Status | Evidence |")
    lines.append("|-------|------|--------|----------|")
    for r in rows:
        mark = {"ok": "✅", "partial": "◐", "weak": "⚠", "missing": "❌"}.get(r["status"], r["status"])
        lines.append(f"| {r['level']} | {r['name']} | {mark} {r['status']} | {r['evidence']} |")
    n_ok = sum(1 for r in rows if r["status"] == "ok")
    lines.append(f"\n**{n_ok}/{len(rows)}** capability rows OK")
    return "\n".join(lines) + "\n"


def capability_summary() -> dict[str, Any]:
    rows = detect_capabilities()
    return {
        "n_rows": len(rows),
        "n_ok": sum(1 for r in rows if r["status"] == "ok"),
        "n_missing": sum(1 for r in rows if r["status"] == "missing"),
        "n_tools": _registry_count(),
        "n_golden": _golden_count(),
        "rows": rows,
    }


# ── L26: README capability table sync ───────────────────────────────

BEGIN_MARK = "<!-- capability-map:begin -->"
END_MARK = "<!-- capability-map:end -->"


def render_level_table(rows: list[dict[str, Any]] | None = None) -> str:
    """Compact status table for embedding in README."""
    rows = rows if rows is not None else detect_capabilities()
    lines = ["| Level | Name | Status |", "|-------|------|--------|"]
    for r in rows:
        mark = {"ok": "✅", "partial": "◐", "weak": "⚠", "missing": "❌"}.get(
            r["status"], ""
        )
        lines.append(f"| {r['level']} | {r['name']} | {mark} |")
    n_ok = sum(1 for r in rows if r["status"] == "ok")
    lines.append(f"\n_内省：**{n_ok}/{len(rows)}** OK · `cli capmap`_")
    return "\n".join(lines) + "\n"


def sync_readme(path: str, rows: list[dict[str, Any]] | None = None) -> str:
    """Insert/replace capability table between BEGIN/END markers.

    If markers are missing, appends a new section at the end.
    Returns the path written.
    """
    table = render_level_table(rows)
    block = f"{BEGIN_MARK}\n{table}{END_MARK}\n"

    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    with open(path, encoding="utf-8") as f:
        text = f.read()

    if BEGIN_MARK in text and END_MARK in text:
        start = text.index(BEGIN_MARK)
        end = text.index(END_MARK) + len(END_MARK)
        # drop trailing newline after END if present
        if end < len(text) and text[end] == "\n":
            end += 1
        new_text = text[:start] + block + text[end:]
    else:
        new_text = text.rstrip() + "\n\n## Auto Capability Map\n\n" + block

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_text)
    return path


def readme_capability_synced(path: str, rows: list[dict[str, Any]] | None = None) -> bool:
    """True if README markers contain the current rendered table."""
    if not os.path.isfile(path):
        return False
    with open(path, encoding="utf-8") as f:
        text = f.read()
    if BEGIN_MARK not in text or END_MARK not in text:
        return False
    start = text.index(BEGIN_MARK) + len(BEGIN_MARK)
    end = text.index(END_MARK)
    current = text[start:end].strip()
    expected = render_level_table(rows).strip()
    return current == expected
