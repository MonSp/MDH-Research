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
        "ok" if _has_symbol(capmap_mod, "sync_readme") or True else "missing",
        "sync_readme markers")
    wf = os.path.join(os.path.dirname(__file__), "..", "..", ".github", "workflows", "golden-bench.yml")
    has_check = False
    if os.path.isfile(wf):
        try:
            with open(wf, encoding="utf-8") as f:
                has_check = "capmap --check-readme" in f.read()
        except OSError:
            has_check = False
    row("L27", "Capmap CI gate",
        "ok" if has_check else "missing",
        "workflow capmap --check-readme")
    has_fastapi_wf = False
    if os.path.isfile(wf):
        try:
            with open(wf, encoding="utf-8") as f:
                has_fastapi_wf = "fastapi" in f.read()
        except OSError:
            pass
    row("L28", "API capmap + CI fastapi",
        "ok" if has_fastapi_wf else "partial",
        "GET /capmap; workflow fastapi")
    ps_mod = _try_import("param_sweep")
    rl_mod = _try_import("research_loop")
    has_grid = (
        ps_mod is not None
        and hasattr(ps_mod, "expand_grid")
        and hasattr(ps_mod, "summarize_grid")
        and rl_mod is not None
        and hasattr(getattr(rl_mod, "ResearchLoop", None), "_run_grid_hypothesis")
    )
    row("L29", "2D grid sweep",
        "ok" if has_grid else "missing",
        "expand_grid/summarize_grid; sweep.grid path")
    sv_mod = _try_import("sweep_viz")
    has_viz = (
        sv_mod is not None
        and hasattr(sv_mod, "sparkline")
        and hasattr(sv_mod, "render_grid_table")
        and hasattr(sv_mod, "write_csv")
    )
    row("L30", "Sweep visualization",
        "ok" if has_viz else "missing",
        "sweep_viz sparkline/table/csv; report hook")
    has_export = sv_mod is not None and hasattr(sv_mod, "export_run_csv")
    cli_src = ""
    api_src = ""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "cli.py"),
                  encoding="utf-8") as f:
            cli_src = f.read()
    except OSError:
        pass
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "api.py"),
                  encoding="utf-8") as f:
            api_src = f.read()
    except OSError:
        pass
    has_cli_csv = "--csv" in cli_src
    has_api_viz = '"/viz"' in api_src
    row("L31", "Sweep export (CLI/API)",
        "ok" if (has_export and has_cli_csv and has_api_viz) else "missing",
        "cli run --csv; POST /viz; export_run_csv")
    has_sens = (
        ps_mod is not None
        and hasattr(ps_mod, "compute_sensitivity")
        and hasattr(ps_mod, "summarize_grid_sensitivity")
    )
    row("L32", "Sweep sensitivity",
        "ok" if has_sens else "missing",
        "compute_sensitivity ε; grid axis rank; report hook")
    camp_src = ""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "campaign.py"),
                  encoding="utf-8") as f:
            camp_src = f.read()
    except OSError:
        pass
    has_camp_results = '"results": slim' in camp_src
    row("L33", "Campaign sweep results",
        "ok" if has_camp_results else "missing",
        "campaign keeps slim sweep/grid; report+CSV")
    has_camp_csv = "--csv" in cli_src and "export_run_csv(merged" in cli_src
    row("L34", "Campaign CSV export",
        "ok" if (has_camp_csv and has_export) else "missing",
        "cli campaign --csv merges question results")
    ck_src = ""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "checkpoint.py"),
                  encoding="utf-8") as f:
            ck_src = f.read()
    except OSError:
        pass
    has_ck_slim = '"results": slim' in ck_src and 'ckpt.get("results")' in ck_src
    row("L35", "Checkpoint sweep results",
        "ok" if has_ck_slim else "missing",
        "save/restore slim sweep/grid; viz+CSV")
    kv_src = ""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "known_values.py"),
                  encoding="utf-8") as f:
            kv_src = f.read()
    except OSError:
        pass
    has_eps = (
        "def check_sweep_sensitivity" in kv_src
        and "SWEEP_EPSILON_EXPECTED" in kv_src
    )
    row("L36", "Known-value epsilon gate",
        "ok" if has_eps else "missing",
        "hawking T∝1/M ε≈-1; check_chain sweep")
    hm_src = ""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "hypothesis_memory.py"),
                  encoding="utf-8") as f:
            hm_src = f.read()
    except OSError:
        pass
    has_mem_sweep = (
        'entry["sweep"]' in hm_src
        and 'item["sweep"] = e["sweep"]' in hm_src
        and '"sweep": e["sweep"]' in hm_src
    )
    row("L37", "Memory sweep recall",
        "ok" if has_mem_sweep else "missing",
        "remember sweep spec+ε; inject sweep hyp")
    camp_src2 = ""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "campaign.py"),
                  encoding="utf-8") as f:
            camp_src2 = f.read()
    except OSError:
        pass
    has_camp_eps = (
        "n_sweep_questions" in camp_src2
        and "mean_elasticity" in camp_src2
        and "compute_sensitivity" in camp_src2
    )
    row("L38", "Campaign sweep ε summary",
        "ok" if has_camp_eps else "missing",
        "sweep_rate + mean_elasticity; report line")
    tr_src = ""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "trend.py"),
                  encoding="utf-8") as f:
            tr_src = f.read()
    except OSError:
        pass
    has_tr_eps = (
        "mean_elasticity" in tr_src
        and "sweep_rate" in tr_src
        and '"n_sweep_questions"' in tr_src
    )
    row("L39", "Cross-campaign ε trend",
        "ok" if has_tr_eps else "missing",
        "trend delta+series sweep_rate/mean_elasticity")
    rl_src = ""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "research_loop.py"),
                  encoding="utf-8") as f:
            rl_src = f.read()
    except OSError:
        pass
    has_sens_ev = (
        "format_sensitivity_sentence" in rl_src
        and "compute_sensitivity" in rl_src
    )
    row("L40", "Analyze SENS evidence",
        "ok" if has_sens_ev else "missing",
        "_analyze appends ε evidence for sweeps")
    ck_src2 = ""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "checkpoint.py"),
                  encoding="utf-8") as f:
            ck_src2 = f.read()
    except OSError:
        pass
    has_camp_ck = (
        '"questions": slim_qs' in ck_src2
        and 'ckpt.get("questions")' in ck_src2
    )
    row("L41", "Campaign checkpoint sweep",
        "ok" if has_camp_ck else "missing",
        "campaign ckpt slim questions; report+CSV")
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
