"""ResearchLoop — minimal viable research cycle.

Implements the hypothesis → experiment → analysis → conclusion loop
using the central tool registry and the ResearchJournal.

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
from .serialize import serialize_result


# Legacy pattern params → registry conventions
_LEGACY_PARAM_ALIASES = {
    "metric_str": "diagonal",
    "mass_kg": "M",
}


def _get_tools():
    """Handler map from the central tool registry (names + aliases)."""
    from .tool_registry import get_handler_map

    return get_handler_map()


def _normalize_params(params: dict) -> dict:
    p = {}
    for k, v in (params or {}).items():
        p[_LEGACY_PARAM_ALIASES.get(k, k)] = v
    return p


def _resolve_tool_name(name: str, tools: dict[str, Any]) -> str:
    if name in tools:
        return name
    from .tool_registry import resolve_tool_name

    return resolve_tool_name(name)


class ResearchLoop:
    """Executes a research cycle: hypothesis → experiment → analysis → conclusion.

    Uses LLM (when available) or heuristics to decompose questions
    into executable experiments, then records everything in the journal.
    """

    def __init__(self, journal: ResearchJournal | None = None,
                 llm_client: Any = None):
        self.journal = journal or ResearchJournal()
        self.tools = _get_tools()
        # Auto-detect LLM from environment
        if llm_client is None and os.environ.get("LLM_API_KEY"):
            llm_client = True  # signal to use env-configured LLM
        self.llm = llm_client

    def run(self, question: str) -> dict[str, Any]:
        """Run a complete research cycle on a question.

        Args:
            question: natural language research question

        Returns:
            Dict with hypothesis, experiments, results, and conclusion.
        """
        hypotheses = self._hypothesize(question)

        results = []
        hyp_id = None
        for hyp in hypotheses:
            experiment = self._design_experiment(hyp)
            hyp_id = self.journal.log_hypothesis(
                question=question,
                prediction=hyp["prediction"],
                assumptions=hyp.get("assumptions", []),
            )

            exp_id = self.journal.log_experiment(
                tool=experiment["tool"],
                params=serialize_result(experiment["params"]),
                hypothesis_id=hyp_id,
            )

            start = time.time()
            try:
                result = self._execute(experiment)
                duration = (time.time() - start) * 1000
                self.journal.log_observation(
                    exp_id, serialize_result(result), duration_ms=duration, success=True
                )
                results.append({"hypothesis": hyp, "result": result, "success": True})
            except Exception as e:
                duration = (time.time() - start) * 1000
                self.journal.log_observation(
                    exp_id, str(e), duration_ms=duration, success=False
                )
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

        Tool schemas come from the central registry.
        """
        from .tool_registry import openai_tools_payload, registry_summary

        summary = registry_summary()
        tools_payload = openai_tools_payload()
        # Keep the system prompt bounded: include names + a compact schema dump
        tools_desc = json.dumps({
            "tool_names": summary["names"],
            "n_tools": summary["count"],
            "by_category": summary["by_category"],
            "tools": tools_payload,
            "known_metrics": {
                "schwarzschild": {
                    "diagonal": ["-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2"],
                    "coords": ["t", "r", "theta", "phi"],
                },
                "minkowski": {"diagonal": ["-1", "1", "1", "1"], "coords": ["t", "x", "y", "z"]},
            },
            "metric_handoff": (
                "Factories (create_*) store a MetricStore entry and return metric_name. "
                "Consumers accept metric_name, or diagonal+coords to create on the fly."
            ),
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
    "params": {{"diagonal": ["-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2"], "coords": ["t", "r", "theta", "phi"], "params": {{"M": 1}}}},
    "assumptions": ["Schwarzschild metric", "M > 0", "r > 2M"]
  }}
]"""

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

        content = content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        hypotheses = json.loads(content)
        if isinstance(hypotheses, dict):
            hypotheses = hypotheses.get("hypotheses", [hypotheses])

        validated = []
        for h in hypotheses:
            tool = h.get("tool")
            if not tool or "params" not in h:
                continue
            try:
                _resolve_tool_name(tool, self.tools)
            except KeyError:
                continue
            validated.append(h)

        if not validated:
            raise ValueError("LLM returned no valid hypotheses")

        return validated

    def _hypothesize_patterns(self, question: str) -> list[dict]:
        """Pattern-matching hypothesis decomposition (fallback)."""
        q = question.lower()
        hypotheses = []

        schwarzschild_diag = [
            "-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2"
        ]
        schwarzschild_coords = ["t", "r", "theta", "phi"]

        if "curvature" in q or "scalar" in q:
            if "schwarzschild" in q:
                hypotheses.append({
                    "prediction": "Schwarzschild scalar curvature R = 0 (vacuum solution)",
                    "tool": "compute_scalar_curvature",
                    "params": {
                        "diagonal": schwarzschild_diag,
                        "coords": schwarzschild_coords,
                        "params": {"M": 1},
                        "name": "schwarzschild",
                    },
                    "assumptions": ["Schwarzschild metric", "vacuum Einstein equations"],
                })
            elif "minkowski" in q or "flat" in q:
                hypotheses.append({
                    "prediction": "Minkowski scalar curvature R = 0 (flat spacetime)",
                    "tool": "compute_scalar_curvature",
                    "params": {
                        "diagonal": ["-1", "1", "1", "1"],
                        "coords": ["t", "x", "y", "z"],
                        "name": "minkowski",
                    },
                    "assumptions": ["Minkowski metric", "flat spacetime"],
                })

        elif "kretschmann" in q:
            if "schwarzschild" in q:
                hypotheses.append({
                    "prediction": "Kretschmann scalar K = 48M²/r⁶",
                    "tool": "compute_kretschmann",
                    "params": {
                        "diagonal": schwarzschild_diag,
                        "coords": schwarzschild_coords,
                        "params": {"M": 1},
                        "name": "schwarzschild",
                    },
                    "assumptions": ["Schwarzschild metric"],
                })

        elif "hawking" in q or "temperature" in q:
            hypotheses.append({
                "prediction": "Hawking temperature T_H = ℏc³/(8πGMk_B)",
                "tool": "hawking_temperature",
                "params": {"M": 1.989e30},
                "assumptions": ["1 solar mass black hole"],
            })

        elif "geodesic" in q:
            hypotheses.append({
                "prediction": "Timelike geodesic in flat spacetime is a straight line",
                "tool": "solve_geodesic",
                "params": {
                    "diagonal": ["-1", "1", "1", "1"],
                    "coords": ["t", "x", "y", "z"],
                    "name": "minkowski_geo",
                    "x0": [0, 0, 0, 0],
                    "u0": [1, 0.5, 0, 0],
                    "tau_max": 10,
                },
                "assumptions": ["Minkowski spacetime", "timelike geodesic"],
            })

        elif "friedmann" in q or "universe" in q or "age" in q:
            hypotheses.append({
                "prediction": "Universe age ≈ 13.8 Gyr with Planck parameters",
                "tool": "age_of_universe",
                "params": {"params": {}},
                "assumptions": ["ΛCDM", "Planck 2018 parameters"],
            })

        else:
            hypotheses.append({
                "prediction": "Computing the requested quantity",
                "tool": "compute_scalar_curvature",
                "params": {
                    "diagonal": ["-1", "1", "1", "1"],
                    "coords": ["t", "x", "y", "z"],
                    "name": "minkowski_default",
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
        params = _normalize_params(experiment["params"])

        try:
            resolved = _resolve_tool_name(tool_name, self.tools)
        except KeyError as e:
            raise ValueError(f"Unknown tool: {tool_name}") from e

        tool_fn = self.tools[resolved]
        start = time.time()
        try:
            try:
                result = tool_fn(**params)
            except TypeError:
                import inspect

                sig = inspect.signature(tool_fn)
                if any(
                    p.kind is inspect.Parameter.VAR_KEYWORD
                    for p in sig.parameters.values()
                ):
                    raise
                filtered = {k: v for k, v in params.items() if k in sig.parameters}
                result = tool_fn(**filtered)
        except Exception as e:
            duration = (time.time() - start) * 1000
            try:
                self.journal.log_tool_call(
                    resolved,
                    serialize_result(params),
                    {"error": str(e)},
                    duration_ms=duration,
                )
            except Exception:
                pass
            raise

        duration = (time.time() - start) * 1000
        try:
            self.journal.log_tool_call(
                resolved,
                serialize_result(params),
                serialize_result(result),
                duration_ms=duration,
            )
        except Exception:
            pass
        return result

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
                            evidence.append(
                                f"CONFIRMED: {pred} — numerically verified as 0 at {pt}"
                            )
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
                evidence.append(f"RESULT: {pred}: {serialize_result(result)}")
            else:
                evidence.append(f"RESULT: {pred}: {str(serialize_result(result))[:200]}")

        verdict = (
            "Hypotheses verified"
            if verified > 0
            else "Experiments completed (symbolic simplification pending)"
        )
        return {
            "verdict": verdict,
            "evidence": evidence,
            "n_experiments": len(successful),
            "n_failures": len(failed),
            "n_verified": verified,
        }
