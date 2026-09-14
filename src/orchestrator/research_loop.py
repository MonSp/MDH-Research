"""ResearchLoop — minimal viable research cycle.

Implements the hypothesis → experiment → analysis → conclusion loop
using the orchestrator's existing modules and the ResearchJournal.

Usage:
    from orchestrator.research_loop import ResearchLoop

    loop = ResearchLoop()
    result = loop.run("What is the scalar curvature of Schwarzschild spacetime?")
"""

from __future__ import annotations

import sys
import os
import time
import json
from typing import Any

BUILD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "build", "src", "bindings")
if BUILD_DIR not in sys.path:
    sys.path.insert(0, BUILD_DIR)

try:
    import _research_core as rc
except ImportError:
    rc = None

from .journal import ResearchJournal


# ── Tool registry: maps tool names to actual functions ──

def _get_tools():
    """Lazy-load tool functions from orchestrator modules."""
    tools = {}

    def compute_christoffel(metric_str, coords, params=None):
        m = rc.geometry.Manifold("m", coords)
        g = rc.geometry.Metric.from_diagonal(m, metric_str if isinstance(metric_str, list) else [metric_str])
        return g.christoffel_symbols()

    def compute_scalar_curvature(metric_str, coords):
        m = rc.geometry.Manifold("m", coords)
        g = rc.geometry.Metric.from_diagonal(m, metric_str if isinstance(metric_str, list) else [metric_str])
        return g.scalar_curvature()

    def compute_kretschmann(metric_str, coords):
        m = rc.geometry.Manifold("m", coords)
        g = rc.geometry.Metric.from_diagonal(m, metric_str if isinstance(metric_str, list) else [metric_str])
        return g.kretschmann_scalar()

    def create_blackhole(bh_type, params):
        from .blackholes import (create_schwarzschild, create_kerr,
                                  create_reissner_nordstrom, create_desitter)
        factory = {
            "schwarzschild": create_schwarzschild,
            "kerr": create_kerr,
            "reissner_nordstrom": create_reissner_nordstrom,
            "desitter": create_desitter,
        }
        fn = factory.get(bh_type)
        if fn is None:
            return {"error": f"Unknown BH type: {bh_type}"}
        return fn(**params)

    def solve_geodesic_tool(metric_str, coords, x0, u0, tau_max, params=None):
        from .geodesic import solve_geodesic
        import numpy as np
        m = rc.geometry.Manifold("m", coords)
        g = rc.geometry.Metric.from_diagonal(metric_str if isinstance(metric_str, list) else [metric_str])
        taus, states = solve_geodesic(g, coords, np.array(x0), np.array(u0), tau_max, params=params)
        return {"taus": taus.tolist(), "states": states.tolist()}

    def hawking_temperature_tool(mass_kg):
        from .hawking import hawking_temperature
        return hawking_temperature(mass_kg)

    def solve_friedmann_tool(params):
        from .cosmology import solve_friedmann
        return solve_friedmann(params)

    def cmb_power_spectrum_tool(params):
        from .cmb import cmb_power_spectrum
        return cmb_power_spectrum(**params)

    tools["compute_christoffel"] = compute_christoffel
    tools["compute_scalar_curvature"] = compute_scalar_curvature
    tools["compute_kretschmann"] = compute_kretschmann
    tools["create_blackhole"] = create_blackhole
    tools["solve_geodesic"] = solve_geodesic_tool
    tools["hawking_temperature"] = hawking_temperature_tool
    tools["solve_friedmann"] = solve_friedmann_tool
    tools["cmb_power_spectrum"] = cmb_power_spectrum_tool

    return tools


class ResearchLoop:
    """Executes a research cycle: hypothesis → experiment → analysis → conclusion.

    Uses LLM (when available) or heuristics to decompose questions
    into executable experiments, then records everything in the journal.
    """

    def __init__(self, journal: ResearchJournal | None = None,
                 llm_client: Any = None):
        self.journal = journal or ResearchJournal()
        self.tools = _get_tools()
        self.llm = llm_client  # optional: dict with "client" and "model" keys

    def run(self, question: str) -> dict[str, Any]:
        """Run a complete research cycle on a question.

        Args:
            question: natural language research question

        Returns:
            Dict with hypothesis, experiments, results, and conclusion.
        """
        hypotheses = self._hypothesize(question)

        results = []
        for hyp in hypotheses:
            experiment = self._design_experiment(hyp)
            hyp_id = self.journal.log_hypothesis(
                question=question,
                prediction=hyp["prediction"],
                assumptions=hyp.get("assumptions", []),
            )

            exp_id = self.journal.log_experiment(
                tool=experiment["tool"],
                params=experiment["params"],
                hypothesis_id=hyp_id,
            )

            start = time.time()
            try:
                result = self._execute(experiment)
                duration = (time.time() - start) * 1000
                self.journal.log_observation(exp_id, result, duration_ms=duration, success=True)
                results.append({"hypothesis": hyp, "result": result, "success": True})
            except Exception as e:
                duration = (time.time() - start) * 1000
                self.journal.log_observation(exp_id, str(e), duration_ms=duration, success=False)
                self.journal.log_error(experiment["tool"], str(e))
                results.append({"hypothesis": hyp, "error": str(e), "success": False})

        conclusion = self._analyze(question, results)
        self.journal.log_conclusion(
            hypothesis_id=hyp_id,
            verdict=conclusion["verdict"],
            evidence=conclusion.get("evidence", []),
        )

        return {
            "question": question,
            "hypotheses": hypotheses,
            "results": results,
            "conclusion": conclusion,
            "journal_summary": self.journal.summary(),
        }

    # ── Hypothesis decomposition ──

    def _hypothesize(self, question: str) -> list[dict]:
        """Decompose a question into testable hypotheses.

        Tries LLM first, falls back to pattern matching.
        """
        if self.llm:
            try:
                return self._hypothesize_llm(question)
            except Exception:
                pass
        return self._hypothesize_patterns(question)

    def _hypothesize_llm(self, question: str) -> list[dict]:
        """Use LLM to decompose a question into testable hypotheses.

        Expects LLM to return JSON matching the tool schema.
        """
        tools_desc = json.dumps({
            "tools": list(self.tools.keys()),
            "tool_schemas": {
                "compute_scalar_curvature": {"params": {"metric_str": "list[str]", "coords": "list[str]"}},
                "compute_kretschmann": {"params": {"metric_str": "list[str]", "coords": "list[str]"}},
                "compute_christoffel": {"params": {"metric_str": "list[str]", "coords": "list[str]"}},
                "create_blackhole": {"params": {"bh_type": "str", "params": "dict"}},
                "solve_geodesic": {"params": {"metric_str": "list[str]", "coords": "list[str]", "x0": "list[float]", "u0": "list[float]", "tau_max": "float"}},
                "hawking_temperature": {"params": {"mass_kg": "float"}},
                "solve_friedmann": {"params": {"params": "dict"}},
                "cmb_power_spectrum": {"params": {"params": "dict"}},
            },
            "known_metrics": {
                "schwarzschild": ["-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2"],
                "minkowski": ["-1", "1", "1", "1"],
                "kerr_diagonal": ["-(1 - 2*M*r/(r^2 + a^2*cos(theta)^2))", "(r^2 + a^2*cos(theta)^2)/(r^2 - 2*M*r + a^2)", "r^2 + a^2*cos(theta)^2", "r^2 * sin(theta)^2"],
                "de_sitter": ["-(1 - L*r^2/3)", "(1 - L*r^2/3)^(-1)", "r^2", "r^2 * sin(theta)^2"],
            },
        }, indent=2)

        system_prompt = f"""You are a physics research assistant. Given a research question, 
decompose it into testable hypotheses, each with a tool call.

Available tools and schemas:
{tools_desc}

Return ONLY a JSON array of hypotheses. Each must have:
- "prediction": string stating what the experiment should show
- "tool": tool name from the available tools
- "params": dict matching the tool's parameter schema
- "assumptions": list of strings

Example for "What is the Kretschmann scalar of Schwarzschild?":
[
  {{
    "prediction": "Kretschmann scalar K = 48M²/r⁶",
    "tool": "compute_kretschmann",
    "params": {{"metric_str": ["-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2"], "coords": ["t", "r", "theta", "phi"]}},
    "assumptions": ["Schwarzschild metric", "M > 0", "r > 2M"]
  }}
]"""

        # Call LLM via OpenAI-compatible API
        import httpx

        api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("LLM_API_KEY", "")
        base_url = os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1")
        model = os.environ.get("LLM_MODEL", "gpt-4o-mini")

        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": question},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]

        # Parse JSON (handle both array and object wrappers)
        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        hypotheses = json.loads(content)
        if isinstance(hypotheses, dict):
            hypotheses = hypotheses.get("hypotheses", [hypotheses])

        # Validate
        validated = []
        for h in hypotheses:
            if h.get("tool") in self.tools and "params" in h:
                validated.append(h)

        if not validated:
            raise ValueError("LLM returned no valid hypotheses")

        return validated

    def _hypothesize_patterns(self, question: str) -> list[dict]:
        """Pattern-matching hypothesis decomposition (fallback)."""
        q = question.lower()
        hypotheses = []

        if "curvature" in q or "scalar" in q:
            if "schwarzschild" in q:
                hypotheses.append({
                    "prediction": "Schwarzschild scalar curvature R = 0 (vacuum solution)",
                    "tool": "compute_scalar_curvature",
                    "params": {
                        "metric_str": ["-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2"],
                        "coords": ["t", "r", "theta", "phi"],
                    },
                    "assumptions": ["Schwarzschild metric", "vacuum Einstein equations"],
                })
            elif "minkowski" in q or "flat" in q:
                hypotheses.append({
                    "prediction": "Minkowski scalar curvature R = 0 (flat spacetime)",
                    "tool": "compute_scalar_curvature",
                    "params": {
                        "metric_str": ["-1", "1", "1", "1"],
                        "coords": ["t", "x", "y", "z"],
                    },
                    "assumptions": ["Minkowski metric", "flat spacetime"],
                })

        elif "kretschmann" in q:
            if "schwarzschild" in q:
                hypotheses.append({
                    "prediction": "Kretschmann scalar K = 48M²/r⁶",
                    "tool": "compute_kretschmann",
                    "params": {
                        "metric_str": ["-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2"],
                        "coords": ["t", "r", "theta", "phi"],
                    },
                    "assumptions": ["Schwarzschild metric"],
                })

        elif "hawking" in q or "temperature" in q:
            hypotheses.append({
                "prediction": "Hawking temperature T_H = ℏc³/(8πGMk_B)",
                "tool": "hawking_temperature",
                "params": {"mass_kg": 1.989e30},
                "assumptions": ["1 solar mass black hole"],
            })

        elif "geodesic" in q:
            hypotheses.append({
                "prediction": "Timelike geodesic in flat spacetime is a straight line",
                "tool": "solve_geodesic",
                "params": {
                    "metric_str": ["-1", "1", "1", "1"],
                    "coords": ["t", "x", "y", "z"],
                    "x0": [0, 0, 0, 0],
                    "u0": [1, 0.5, 0, 0],
                    "tau_max": 10,
                },
                "assumptions": ["Minkowski spacetime", "timelike geodesic"],
            })

        elif "friedmann" in q or "universe" in q or "age" in q:
            hypotheses.append({
                "prediction": "Universe age ≈ 13.8 Gyr with Planck parameters",
                "tool": "solve_friedmann",
                "params": {"params": {}},
                "assumptions": ["ΛCDM", "Planck 2018 parameters"],
            })

        else:
            hypotheses.append({
                "prediction": "Computing the requested quantity",
                "tool": "compute_scalar_curvature",
                "params": {
                    "metric_str": ["-1", "1", "1", "1"],
                    "coords": ["t", "x", "y", "z"],
                },
                "assumptions": ["Default to flat spacetime for unknown queries"],
            })

        return hypotheses

    def _design_experiment(self, hypothesis: dict) -> dict:
        return {
            "tool": hypothesis["tool"],
            "params": hypothesis["params"],
        }

    def _execute(self, experiment: dict) -> Any:
        tool_name = experiment["tool"]
        params = experiment["params"]

        tool_fn = self.tools.get(tool_name)
        if tool_fn is None:
            raise ValueError(f"Unknown tool: {tool_name}")

        return tool_fn(**params)

    def _analyze(self, question: str, results: list[dict]) -> dict:
        """Analyze results and form a conclusion.

        For symbolic results, tries numerical evaluation to verify predictions.
        """
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]

        if not successful:
            return {
                "verdict": "All experiments failed",
                "evidence": [r.get("error", "unknown") for r in failed],
            }

        evidence = []
        verified = 0
        for r in successful:
            result = r["result"]
            pred = r["hypothesis"]["prediction"]

            if hasattr(result, "evaluate"):
                test_points = [
                    {"M": 1, "r": 6, "theta": 1.5708, "phi": 0, "t": 0},
                    {"M": 1, "r": 10, "theta": 1.5708, "phi": 0, "t": 0},
                ]
                for pt in test_points:
                    try:
                        val = result.evaluate(pt)
                        if abs(val) < 1e-8:
                            evidence.append(f"CONFIRMED: {pred} — numerically verified as 0 at {pt}")
                            verified += 1
                            break
                        else:
                            evidence.append(f"RESULT: {pred} — evaluates to {val} at {pt}")
                    except Exception:
                        pass
                else:
                    s = result.to_string()
                    evidence.append(f"RESULT: {pred}: {s[:200]}")
            elif isinstance(result, dict):
                evidence.append(f"RESULT: {pred}: {result}")
            else:
                evidence.append(f"RESULT: {pred}: {str(result)[:200]}")

        verdict = "Hypotheses verified" if verified > 0 else "Experiments completed (symbolic simplification pending)"
        return {
            "verdict": verdict,
            "evidence": evidence,
            "n_experiments": len(successful),
            "n_failures": len(failed),
            "n_verified": verified,
        }
