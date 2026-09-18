"""ResearchLoop — hypothesis → chain of tools → analysis → conclusion.

Supports single-tool hypotheses (legacy `tool`/`params`) and sequential
tool chains (`tools` list). Factory outputs (`metric_name`) are threaded
into later metric-consuming steps automatically.
"""

from __future__ import annotations

import sys
import os
import time
import json
from dataclasses import dataclass, field
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


_LEGACY_PARAM_ALIASES = {
    "metric_str": "diagonal",
    "mass_kg": "M",
}


@dataclass
class ChainStep:
    tool: str
    params: dict[str, Any] = field(default_factory=dict)


def _get_tools():
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


def _tool_needs_metric(tool_name: str) -> bool:
    from .tool_registry import build_registry, resolve_tool_name

    try:
        resolved = resolve_tool_name(tool_name)
    except KeyError:
        return False
    spec = build_registry().get(resolved)
    return bool(spec and spec.needs_metric)


def _steps_from_hypothesis(h: dict) -> list[ChainStep]:
    """Normalize hypothesis formats into an ordered chain of steps.

    Accepted shapes:
      - {"tool": "x", "params": {...}}                    # legacy single
      - {"tools": [{"tool": "x", "params": {...}}, ...]}  # explicit chain
      - {"tools": ["x", "y"]}                             # shorthand names
      - mixed list of strings and dicts
    """
    if h.get("tools"):
        steps: list[ChainStep] = []
        for item in h["tools"]:
            if isinstance(item, str):
                steps.append(ChainStep(tool=item, params={}))
            elif isinstance(item, dict):
                tool = item.get("tool") or item.get("name")
                if not tool:
                    raise ValueError(f"chain step missing tool: {item}")
                steps.append(ChainStep(tool=str(tool), params=dict(item.get("params") or {})))
            else:
                raise ValueError(f"invalid chain step: {item!r}")
        if not steps:
            raise ValueError("hypothesis tools list is empty")
        return steps

    if h.get("tool"):
        return [ChainStep(tool=str(h["tool"]), params=dict(h.get("params") or {}))]

    raise ValueError("hypothesis needs 'tool' or 'tools'")


def _inject_context(params: dict, context: dict, tool: str) -> dict:
    """Fill metric_name from chain context when the step needs a metric."""
    out = dict(params)
    if not _tool_needs_metric(tool):
        return out
    has_metric = out.get("metric_name") or out.get("diagonal")
    if not has_metric and context.get("metric_name"):
        out["metric_name"] = context["metric_name"]
    return out


class ResearchLoop:
    """Hypothesis → experiment (tool chain) → analysis → conclusion."""

    def __init__(self, journal: ResearchJournal | None = None,
                 llm_client: Any = None,
                 memory_path: str | bool | None = None):
        self.journal = journal or ResearchJournal()
        self.tools = _get_tools()
        # llm_client=False disables LLM; None auto-detects from env
        if llm_client is None and os.environ.get("LLM_API_KEY"):
            llm_client = True
        self.llm = llm_client
        # memory_path: str → enable store at that path; None/False → disabled
        self.memory_path = memory_path

    def run(self, question: str) -> dict[str, Any]:
        hypotheses = self._hypothesize(question)

        # ── L14: inject recalled hypotheses from memory as extra candidates ──
        if self.memory_path:
            try:
                from .hypothesis_memory import inject_memory_candidates

                recalled = inject_memory_candidates(
                    question, path=self.memory_path, limit=2
                )
                if recalled:
                    hypotheses = hypotheses + recalled
                    try:
                        self.journal.log_note(
                            f"MEMORY: injected {len(recalled)} recalled hypotheses"
                        )
                    except Exception:
                        pass
            except Exception:
                pass

        results = []
        hyp_id = None
        for hyp in hypotheses:
            hyp_id = self.journal.log_hypothesis(
                question=question,
                prediction=hyp["prediction"],
                assumptions=hyp.get("assumptions", []),
            )

            if hyp.get("sweep"):
                results.append(self._run_sweep_hypothesis(hyp, hyp_id))
                continue

            steps = _steps_from_hypothesis(hyp)
            chain_label = " → ".join(s.tool for s in steps)
            exp_id = self.journal.log_experiment(
                tool=steps[0].tool if len(steps) == 1 else chain_label,
                params=serialize_result(
                    steps[0].params if len(steps) == 1
                    else [{"tool": s.tool, "params": s.params} for s in steps]
                ),
                hypothesis_id=hyp_id,
            )

            start = time.time()
            try:
                step_results = self._execute_chain(steps)
                duration = (time.time() - start) * 1000
                last = step_results[-1]["result"]
                metric_name = None
                for s in step_results:
                    res = s.get("result")
                    if isinstance(res, dict) and res.get("metric_name"):
                        metric_name = res["metric_name"]
                    elif s.get("params", {}).get("metric_name"):
                        metric_name = s["params"]["metric_name"]
                self.journal.log_observation(
                    exp_id,
                    serialize_result({
                        "steps": [
                            {"tool": s["tool"], "result": serialize_result(s["result"])}
                            for s in step_results
                        ],
                        "result": serialize_result(last),
                    }),
                    duration_ms=duration,
                    success=True,
                )
                results.append({
                    "hypothesis": hyp,
                    "steps": step_results,
                    "result": last,
                    "metric_name": metric_name,
                    "success": True,
                })
            except Exception as e:
                duration = (time.time() - start) * 1000
                partial = getattr(e, "partial_steps", None) or []

                # ── L4c failure replan ──
                repaired, replan_note = self._try_replan(
                    steps, str(e), partial, question
                )
                if repaired is not None:
                    try:
                        step_results = self._execute_chain(repaired)
                        duration = (time.time() - start) * 1000
                        last = step_results[-1]["result"]
                        metric_name = None
                        for s in step_results:
                            res = s.get("result")
                            if isinstance(res, dict) and res.get("metric_name"):
                                metric_name = res["metric_name"]
                            elif s.get("params", {}).get("metric_name"):
                                metric_name = s["params"]["metric_name"]
                        self.journal.log_observation(
                            exp_id,
                            serialize_result({
                                "replan": replan_note,
                                "steps": [
                                    {"tool": s["tool"],
                                     "result": serialize_result(s["result"])}
                                    for s in step_results
                                ],
                                "result": serialize_result(last),
                            }),
                            duration_ms=duration,
                            success=True,
                        )
                        results.append({
                            "hypothesis": hyp,
                            "steps": step_results,
                            "result": last,
                            "metric_name": metric_name,
                            "replan": replan_note,
                            "success": True,
                        })
                        continue
                    except Exception as e2:
                        e = e2
                        partial = getattr(e2, "partial_steps", None) or partial
                        duration = (time.time() - start) * 1000

                self.journal.log_observation(
                    exp_id,
                    serialize_result({
                        "error": str(e),
                        "steps": [
                            {"tool": s.get("tool"), "error": s.get("error")}
                            if "error" in s else
                            {"tool": s.get("tool"), "result": serialize_result(s.get("result"))}
                            for s in partial
                        ],
                    }),
                    duration_ms=duration,
                    success=False,
                )
                failed_tool = (
                    partial[-1].get("tool") if partial and "error" in partial[-1]
                    else (partial[-1].get("tool") if partial else steps[0].tool)
                )
                self.journal.log_error(failed_tool or steps[0].tool, str(e))
                results.append({
                    "hypothesis": hyp,
                    "steps": partial,
                    "error": str(e),
                    "success": False,
                })

        # ── L6: competition / regeneration when first round is weak ──
        pre_ranking = None
        try:
            from .agent_math import rank_hypotheses

            pre_ranking = rank_hypotheses(results)
        except Exception:
            pre_ranking = None
        results, competed = self._maybe_compete(question, results, pre_ranking, hyp_id)

        # ── L7: iterative rounds while still no working path ──
        iterate_rounds = 0
        if not any(r.get("success") for r in results):
            for _round in range(2):
                results, added = self._maybe_iterate(question, results, _round + 1)
                if not added:
                    break
                iterate_rounds += 1
                if any(r.get("success") for r in results):
                    break

        # ── L14: remember successful hypotheses for future recall ──
        remembered_n = 0
        if self.memory_path:
            try:
                from .hypothesis_memory import remember_from_run

                mem = remember_from_run(
                    {"question": question, "results": results},
                    path=self.memory_path,
                )
                remembered_n = len(mem)
            except Exception:
                remembered_n = 0

        conclusion = self._analyze(question, results)
        conclusion["competed"] = bool(competed)
        conclusion["iterate_rounds"] = iterate_rounds
        conclusion["memory_entries"] = remembered_n
        if competed:
            n_comp = sum(
                1 for r in results
                if r.get("round") == "competition"
            )
            conclusion.setdefault("evidence", []).append(
                f"COMPETE: first-round weak; evaluated {n_comp} alternatives"
            )
        if iterate_rounds:
            n_it = sum(1 for r in results if str(r.get("round", "")).startswith("iterate"))
            conclusion.setdefault("evidence", []).append(
                f"ITERATE: {iterate_rounds} extra round(s), +{n_it} hypotheses"
            )
        self.journal.log_conclusion(
            hypothesis_id=hyp_id,
            verdict=conclusion["verdict"],
            evidence=conclusion.get("evidence", []),
            extra={
                "foundations": serialize_result(conclusion.get("foundations") or {}),
                "hypothesis_ranking": serialize_result(
                    conclusion.get("hypothesis_ranking") or []
                ),
                "best_hypothesis": serialize_result(
                    conclusion.get("best_hypothesis") or {}
                ),
                "competed": bool(competed),
                "iterate_rounds": iterate_rounds,
            },
        )

        return {
            "question": question,
            "hypotheses": hypotheses,
            "results": results,
            "conclusion": conclusion,
            "journal_summary": self.journal.summary(),
        }

    # ── Hypothesis decomposition ──

    def _maybe_compete(
        self,
        question: str,
        results: list[dict],
        ranking: list[dict] | None,
        hyp_id: str | None,
    ) -> tuple[list[dict], bool]:
        """L6: run alternative hypotheses when the first round is weak."""
        from .compete import heuristic_alternatives, llm_alternatives, should_compete

        try:
            if not should_compete(results, ranking):
                return results, False
        except Exception:
            return results, False

        alts: list[dict] = []
        if self.llm:
            try:
                from .tool_registry import openai_tools_payload

                alts = llm_alternatives(
                    question, results, openai_tools_payload(), limit=3
                )
            except Exception:
                alts = []
        if not alts:
            alts = heuristic_alternatives(question, results, limit=3)
        if not alts:
            return results, False

        new_results: list[dict] = []
        for alt in alts:
            try:
                steps = _steps_from_hypothesis(alt)
            except ValueError:
                continue
            ok = True
            for s in steps:
                try:
                    _resolve_tool_name(s.tool, self.tools)
                except KeyError:
                    ok = False
                    break
            if not ok:
                continue

            self.journal.log_hypothesis(
                question=question,
                prediction=alt.get("prediction", ""),
                assumptions=alt.get("assumptions") or ["competition"],
            )
            try:
                step_results = self._execute_chain(steps)
                last = step_results[-1]["result"]
                metric_name = None
                for s in step_results:
                    res = s.get("result")
                    if isinstance(res, dict) and res.get("metric_name"):
                        metric_name = res["metric_name"]
                new_results.append({
                    "hypothesis": alt,
                    "steps": step_results,
                    "result": last,
                    "metric_name": metric_name,
                    "success": True,
                    "round": "competition",
                })
            except Exception as e:
                partial = getattr(e, "partial_steps", None) or []
                repaired, replan_note = self._try_replan(
                    steps, str(e), partial, question
                )
                if repaired is not None:
                    try:
                        step_results = self._execute_chain(repaired)
                        last = step_results[-1]["result"]
                        new_results.append({
                            "hypothesis": alt,
                            "steps": step_results,
                            "result": last,
                            "replan": replan_note,
                            "success": True,
                            "round": "competition",
                        })
                        continue
                    except Exception as e2:
                        e = e2
                new_results.append({
                    "hypothesis": alt,
                    "steps": partial,
                    "error": str(e),
                    "success": False,
                    "round": "competition",
                })

        if not new_results:
            return results, False
        try:
            self.journal.log_note(
                f"COMPETE: +{len(new_results)} alternative hypotheses after weak first round"
            )
        except Exception:
            pass
        return results + new_results, True

    def _maybe_iterate(
        self,
        question: str,
        results: list[dict],
        round_n: int,
    ) -> tuple[list[dict], bool]:
        """L7: one extra iteration of parameter-mutated / unused-consumer hypotheses."""
        from .compete import iterate_hypotheses

        if any(r.get("success") for r in results):
            return results, False

        alts = iterate_hypotheses(question, results, round_n=round_n, limit=2)
        if not alts:
            return results, False

        new_results: list[dict] = []
        for alt in alts:
            try:
                steps = _steps_from_hypothesis(alt)
            except ValueError:
                continue
            ok = True
            for s in steps:
                try:
                    _resolve_tool_name(s.tool, self.tools)
                except KeyError:
                    ok = False
                    break
            if not ok:
                continue

            self.journal.log_hypothesis(
                question=question,
                prediction=alt.get("prediction", ""),
                assumptions=alt.get("assumptions") or [f"iterate-{round_n}"],
            )
            try:
                step_results = self._execute_chain(steps)
                last = step_results[-1]["result"]
                metric_name = None
                for s in step_results:
                    res = s.get("result")
                    if isinstance(res, dict) and res.get("metric_name"):
                        metric_name = res["metric_name"]
                new_results.append({
                    "hypothesis": alt,
                    "steps": step_results,
                    "result": last,
                    "metric_name": metric_name,
                    "success": True,
                    "round": f"iterate{round_n}",
                })
            except Exception as e:
                partial = getattr(e, "partial_steps", None) or []
                repaired, replan_note = self._try_replan(
                    steps, str(e), partial, question
                )
                if repaired is not None:
                    try:
                        step_results = self._execute_chain(repaired)
                        last = step_results[-1]["result"]
                        new_results.append({
                            "hypothesis": alt,
                            "steps": step_results,
                            "result": last,
                            "replan": replan_note,
                            "success": True,
                            "round": f"iterate{round_n}",
                        })
                        continue
                    except Exception as e2:
                        e = e2
                new_results.append({
                    "hypothesis": alt,
                    "steps": partial,
                    "error": str(e),
                    "success": False,
                    "round": f"iterate{round_n}",
                })

        if not new_results:
            return results, False
        try:
            self.journal.log_note(
                f"ITERATE r{round_n}: +{len(new_results)} hypotheses"
            )
        except Exception:
            pass
        return results + new_results, True

    def _try_replan(
        self,
        steps: list[ChainStep],
        error: str,
        partial: list[dict],
        question: str,
    ) -> tuple[list[ChainStep] | None, str | None]:
        """Attempt heuristic repair of a failed chain. Returns (new_steps, note)."""
        from .replan import describe_repair, diagnose_failure, heuristic_repair

        diagnosis = diagnose_failure(error, partial)
        repaired = heuristic_repair(
            steps, diagnosis, question=question, step_cls=ChainStep
        )
        if repaired is None:
            return None, None
        # avoid no-op repair
        same = (
            len(repaired) == len(steps)
            and all(
                a.tool == b.tool and a.params == b.params
                for a, b in zip(repaired, steps)
            )
        )
        if same:
            return None, None
        note = describe_repair(steps, repaired, str(diagnosis.get("kind")))
        try:
            self.journal.log_note(
                f"{note} | diagnosis={diagnosis.get('kind')} | {error[:120]}"
            )
        except Exception:
            pass
        return repaired, note

    def _hypothesize(self, question: str) -> list[dict]:
        if self.llm:
            try:
                return self._hypothesize_llm(question)
            except Exception:
                pass
        return self._hypothesize_patterns(question)

    def _hypothesize_llm(self, question: str) -> list[dict]:
        from .tool_registry import openai_tools_payload, registry_summary

        summary = registry_summary()
        tools_payload = openai_tools_payload()
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
            "chain_execution": (
                "The executor runs your tools SEQUENTIALLY. "
                "If step 1 is a create_* factory, later metric consumers "
                "automatically receive its metric_name — omit metric_name in later params. "
                "For multi-step questions use the 'tools' array in execution order."
            ),
            "parameter_sweep": (
                "For 'how does Y change with X' questions add a 'sweep' object: "
                '{"tool": "...", "params": {...}, "axis": {"name": "X", "values": [...]}, '
                '"extract": "dict_key_or_null"} '
                "or for chains: axis + inject {\"tool\": \"...\", \"param\": \"X\"}. "
                "Max 12 axis points."
            ),
        }, indent=2)

        system_prompt = f"""You are a physics research assistant. Given a research question,
decompose it into testable hypotheses.

Available tools and schemas:
{tools_desc}

Return ONLY a JSON array of hypotheses. Each must have:
- "prediction": string stating what the experiment should show
- "assumptions": list of strings
- EITHER "tool" + "params" for a single call
- OR "tools": an ordered array of steps for multi-step work.
  Each step is {{"tool": "...", "params": {{...}}}} or just a tool-name string.
  After a create_* factory, leave metric_name empty on later steps.
- OPTIONAL "sweep" to vary one parameter and measure a trend:
  {{"tool": "...", "params": {{}}, "axis": {{"name": "M", "values": [1e30, 1e31, 1e32]}}, "extract": "T_K"}}
  Chain form: same axis plus "inject": {{"tool": "create_...", "param": "M"}}.

Example single-step:
[
  {{
    "prediction": "Universe age ≈ 13.8 Gyr",
    "tool": "age_of_universe",
    "params": {{"params": {{}}}},
    "assumptions": ["ΛCDM"]
  }}
]

Example multi-step chain:
[
  {{
    "prediction": "Kerr is a vacuum solution so R=0",
    "tools": [
      {{"tool": "create_kerr", "params": {{"M": 1, "a": 0.5}}}},
      {{"tool": "compute_scalar_curvature", "params": {{}}}}
    ],
    "assumptions": ["Kerr metric"]
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
                "max_tokens": 2048,
            },
            timeout=60,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"].get("content") or ""

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
            if "prediction" not in h:
                continue
            # sweep-only hypotheses are valid (tool lives under sweep.tool / tools)
            if h.get("sweep"):
                sw = h["sweep"] or {}
                names: list[str] = []
                if sw.get("tool"):
                    names.append(str(sw["tool"]))
                for step in (h.get("tools") or []):
                    names.append(step if isinstance(step, str) else str((step or {}).get("tool") or ""))
                if not names:
                    continue
                ok = True
                for n in names:
                    try:
                        _resolve_tool_name(n, self.tools)
                    except KeyError:
                        ok = False
                        break
                if ok:
                    validated.append(h)
                continue
            try:
                steps = _steps_from_hypothesis(h)
            except ValueError:
                continue
            ok = True
            for step in steps:
                try:
                    _resolve_tool_name(step.tool, self.tools)
                except KeyError:
                    ok = False
                    break
            if ok:
                validated.append(h)

        if not validated:
            raise ValueError("LLM returned no valid hypotheses")

        return validated

    def _hypothesize_patterns(self, question: str) -> list[dict]:
        q = question.lower()
        hypotheses = []

        if "kretschmann" in q:
            if "schwarzschild" in q:
                hypotheses.append({
                    "prediction": "Kretschmann scalar K = 48M²/r⁶",
                    "tools": [
                        {"tool": "create_schwarzschild", "params": {"M": 1}},
                        {"tool": "compute_kretschmann", "params": {}},
                    ],
                    "assumptions": ["Schwarzschild metric"],
                })

        elif "curvature" in q or "scalar" in q:
            if "schwarzschild" in q:
                hypotheses.append({
                    "prediction": "Schwarzschild scalar curvature R = 0 (vacuum solution)",
                    "tools": [
                        {"tool": "create_schwarzschild", "params": {"M": 1}},
                        {"tool": "compute_scalar_curvature", "params": {}},
                    ],
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

        elif "hawking" in q or "temperature" in q or "evapor" in q:
            if ("evapor" in q) or ("entropy" in q and "temperature" in q):
                solar_mass = 1.989e30
                hypotheses.append({
                    "prediction": "Hawking temperature and evaporation time for 1 M☉",
                    "tools": [
                        {"tool": "hawking_temperature", "params": {"M": solar_mass}},
                        {"tool": "evaporation_time", "params": {"M": solar_mass}},
                    ],
                    "assumptions": ["1 solar mass black hole"],
                })
            elif ("scan" in q) or ("sweep" in q) or ("vary" in q) or ("vs" in q and "mass" in q) or ("as a function of" in q and "mass" in q):
                hypotheses.append({
                    "prediction": "Hawking temperature decreases as mass increases (∝ 1/M)",
                    "sweep": {
                        "tool": "hawking_temperature",
                        "params": {},
                        "axis": {
                            "name": "M",
                            "values": [1e30, 1e31, 1e32],
                        },
                        "extract": "T_K",
                    },
                    "assumptions": ["Schwarzschild black holes"],
                })
            else:
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

        elif "symmetry" in q or "killing" in q:
            hypotheses.append({
                "prediction": "Schwarzschild is static and stationary",
                "tools": [
                    {"tool": "create_schwarzschild", "params": {"M": 1}},
                    {"tool": "classify_symmetry", "params": {}},
                ],
                "assumptions": ["Schwarzschild metric"],
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

    def _run_sweep_hypothesis(self, hyp: dict, hyp_id: str) -> dict:
        """Execute a parameter-sweep hypothesis and summarize the trend."""
        from .param_sweep import (
            MAX_SWEEP_POINTS,
            expand_axis,
            extract_numeric,
            format_trend_sentence,
            summarize_trend,
            substitute_params,
        )

        sweep = hyp["sweep"] or {}
        axis = sweep.get("axis") or {}
        axis_name = str(axis.get("name") or "x")
        extract_key = sweep.get("extract")
        inject = sweep.get("inject")  # chain mode: {"tool","param"}

        try:
            xs = expand_axis(axis)
        except Exception as e:
            self.journal.log_error("sweep", f"bad axis: {e}")
            return {
                "hypothesis": hyp,
                "steps": [],
                "error": f"bad sweep axis: {e}",
                "success": False,
            }

        requested_n = None
        if axis.get("values"):
            requested_n = len(axis["values"])
        elif axis.get("n") is not None:
            requested_n = int(axis["n"])
        truncated = bool(requested_n and requested_n > MAX_SWEEP_POINTS)

        if not sweep.get("tool") and not hyp.get("tools") and not hyp.get("tool"):
            err = "sweep hypothesis needs sweep.tool or tools"
            self.journal.log_error("sweep", err)
            return {
                "hypothesis": hyp,
                "steps": [],
                "error": err,
                "success": False,
            }

        # single-tool sweep
        if sweep.get("tool") and not hyp.get("tools"):
            tool = str(sweep["tool"])
            base_params = dict(sweep.get("params") or {})
            exp_label = f"sweep:{tool}"
            exp_id = self.journal.log_experiment(
                tool=exp_label,
                params=serialize_result({
                    "axis": axis_name,
                    "values": xs,
                    "extract": extract_key,
                }),
                hypothesis_id=hyp_id,
            )
            # bind metric params into Expression eval point when present
            eval_point = dict(base_params)
            points = []
            start = time.time()
            for x in xs:
                params = substitute_params(base_params, axis_name, x)
                eval_pt = {**eval_point, axis_name: x}
                try:
                    raw = self._call_tool(tool, params)
                    y = extract_numeric(raw, extract_key, eval_point=eval_pt)
                    if y is None:
                        points.append({"x": x, "error": f"no numeric extract key={extract_key}"})
                    else:
                        points.append({"x": x, "y": y})
                except Exception as e:
                    points.append({"x": x, "error": str(e)})
            duration = (time.time() - start) * 1000
        else:
            # chain sweep with inject
            steps = _steps_from_hypothesis(hyp)
            if not inject:
                inject = {"tool": steps[0].tool, "param": axis_name}
            inj_tool = str(inject.get("tool") or steps[0].tool)
            inj_param = str(inject.get("param") or axis_name)

            def _same_tool(a: str, b: str) -> bool:
                if a == b:
                    return True
                try:
                    return _resolve_tool_name(a, self.tools) == _resolve_tool_name(b, self.tools)
                except KeyError:
                    return a.split(":")[-1] == b.split(":")[-1]

            exp_label = f"sweep:{' → '.join(s.tool for s in steps)}"
            exp_id = self.journal.log_experiment(
                tool=exp_label,
                params=serialize_result({
                    "axis": axis_name,
                    "values": xs,
                    "inject": inject,
                    "extract": extract_key,
                }),
                hypothesis_id=hyp_id,
            )
            points = []
            start = time.time()
            for x in xs:
                new_steps = []
                for s in steps:
                    params = dict(s.params)
                    if _same_tool(s.tool, inj_tool):
                        params = substitute_params(params, inj_param, x)
                    new_steps.append(ChainStep(tool=s.tool, params=params))
                try:
                    step_results = self._execute_chain(new_steps)
                    last = step_results[-1]["result"]
                    # bind metric params for Expression evaluation
                    eval_pt: dict[str, float] = {}
                    for s in step_results:
                        eval_pt.update({
                            k: float(v) for k, v in (s.get("params") or {}).items()
                            if isinstance(v, (int, float)) and not isinstance(v, bool)
                        })
                        res = s.get("result")
                        if isinstance(res, dict) and isinstance(res.get("params"), dict):
                            eval_pt.update({
                                k: float(v) for k, v in res["params"].items()
                                if isinstance(v, (int, float)) and not isinstance(v, bool)
                            })
                    y = extract_numeric(last, extract_key, eval_point=eval_pt or None)
                    if y is None:
                        points.append({"x": x, "error": f"no numeric extract key={extract_key}"})
                    else:
                        points.append({"x": x, "y": y})
                except Exception as e:
                    points.append({"x": x, "error": str(e)})
            duration = (time.time() - start) * 1000

        ok_ys = [(p["x"], p["y"]) for p in points if "y" in p]
        if len(ok_ys) < 2:
            self.journal.log_observation(
                exp_id,
                serialize_result({"sweep": {"points": points}, "error": "insufficient finite samples"}),
                duration_ms=duration,
                success=False,
            )
            return {
                "hypothesis": hyp,
                "steps": [],
                "sweep": {"axis_name": axis_name, "points": points,
                          "trend": summarize_trend([], [])},
                "error": "sweep produced <2 finite samples",
                "success": False,
            }

        xs_ok = [p[0] for p in ok_ys]
        ys_ok = [p[1] for p in ok_ys]
        trend = summarize_trend(xs_ok, ys_ok, truncated=truncated)
        sentence = format_trend_sentence(axis_name, extract_key, trend)
        self.journal.log_observation(
            exp_id,
            serialize_result({
                "sweep": {
                    "axis_name": axis_name,
                    "extract": extract_key,
                    "points": points,
                    "trend": trend,
                },
                "summary": sentence,
            }),
            duration_ms=duration,
            success=True,
        )
        return {
            "hypothesis": hyp,
            "steps": [{"tool": sweep.get("tool") or "chain", "params": {}, "result": trend}],
            "sweep": {
                "axis_name": axis_name,
                "extract": extract_key,
                "points": points,
                "trend": trend,
                "summary": sentence,
            },
            "result": trend,
            "success": True,
        }

    def _execute_chain(self, steps: list[ChainStep]) -> list[dict]:
        """Run steps sequentially, threading metric_name through context."""
        context: dict[str, Any] = {}
        out: list[dict] = []

        for i, step in enumerate(steps):
            params = _normalize_params(step.params)
            params = _inject_context(params, context, step.tool)

            if _tool_needs_metric(step.tool) and not (
                params.get("metric_name") or params.get("diagonal")
            ):
                err = (
                    f"step {i} ({step.tool}) needs a metric but none provided "
                    f"and chain context has no metric_name"
                )
                rec = {"tool": step.tool, "params": params, "error": err}
                out.append(rec)
                exc = RuntimeError(err)
                exc.partial_steps = out
                raise exc

            try:
                result = self._call_tool(step.tool, params)
            except Exception as e:
                rec = {"tool": step.tool, "params": params, "error": str(e)}
                out.append(rec)
                exc = RuntimeError(f"step {i} ({step.tool}) failed: {e}")
                exc.partial_steps = out
                raise exc from e

            out.append({"tool": step.tool, "params": params, "result": result})
            if isinstance(result, dict) and result.get("metric_name"):
                context["metric_name"] = result["metric_name"]

        return out

    def _call_tool(self, tool_name: str, params: dict) -> Any:
        resolved = _resolve_tool_name(tool_name, self.tools)
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
        from .verification import (
            gate_counts_as_verified,
            numeric_eval_is_zero,
            should_run_vacuum_gate,
            sympy_is_zero,
            vacuum_residual_check,
        )
        from .metric_store import get_store

        empty_verification = {
            "numeric_confirmed": 0,
            "symbolic_confirmed": 0,
            "residual_gates": [],
        }

        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]

        if not successful:
            return {
                "verdict": "All experiments failed",
                "evidence": [r.get("error", "unknown") for r in failed],
                "verification": dict(empty_verification),
            }

        evidence: list[str] = []
        numeric_confirmed = 0
        symbolic_confirmed = 0
        residual_gates: list[dict] = []
        any_confirmed = False
        gate_failed = False

        for r in successful:
            pred = r["hypothesis"]["prediction"]
            tools = [s.get("tool") for s in (r.get("steps") or [])]
            metric_name = r.get("metric_name")

            # parameter-sweep evidence
            sw = r.get("sweep")
            if sw and sw.get("trend") and sw["trend"].get("n", 0) >= 2:
                evidence.append(sw.get("summary") or str(sw["trend"]))
                # a completed multi-point sweep is experimental evidence
                any_confirmed = True

            extra_params: dict[str, float] = {}
            if metric_name:
                try:
                    extra_params = dict(get_store().get(metric_name).get("params") or {})
                except Exception:
                    extra_params = {}

            # numeric points: coords + metric params bound
            test_points = [
                {"t": 0, "r": 8, "theta": 1.5708, "phi": 0,
                 "x": 3, "y": 4, "z": 0, **extra_params},
                {"t": 0, "r": 15, "theta": 1.2, "phi": 0.4,
                 "x": 1, "y": 2, "z": 2, **extra_params},
            ]

            candidates = []
            if r.get("steps"):
                candidates = [s.get("result") for s in r["steps"] if "result" in s]
            if not candidates and "result" in r:
                candidates = [r["result"]]

            for result in candidates:
                if not hasattr(result, "evaluate"):
                    if isinstance(result, dict):
                        continue
                    evidence.append(
                        f"RESULT: {pred}: {str(serialize_result(result))[:200]}"
                    )
                    continue

                # 1) SymPy first (authoritative for identically zero)
                is_zero = sympy_is_zero(result, timeout_s=5.0)
                if is_zero is True:
                    symbolic_confirmed += 1
                    any_confirmed = True
                    evidence.append(
                        f"CONFIRMED: {pred} — symbolically simplified to 0 (SymPy)"
                    )
                    continue

                # 2) Numeric only when free symbols are fully bound
                num_zero, sample, note = numeric_eval_is_zero(
                    result, test_points, extra_params=extra_params
                )
                if num_zero is True:
                    numeric_confirmed += 1
                    any_confirmed = True
                    evidence.append(
                        f"CONFIRMED: {pred} — numerically verified as 0 (sample={sample})"
                    )
                elif num_zero is False:
                    evidence.append(
                        f"RESULT: {pred} — nonzero (numeric sample={sample})"
                    )
                elif is_zero is False:
                    evidence.append(f"RESULT: {pred} — nonzero (sympy)")
                else:
                    evidence.append(
                        f"RESULT: {pred} — undecidable numeric ({note}); sympy-skipped"
                    )

            # 3) vacuum residual gate (known vacuum factories only)
            if metric_name and should_run_vacuum_gate(pred, tools):
                store = get_store()
                try:
                    entry = store.get(metric_name)
                    gate = vacuum_residual_check(
                        entry["metric"],
                        entry["coord_names"],
                        params=entry.get("params") or {},
                        points=None,
                        tol=1e-4,
                    )
                except KeyError:
                    # spec: MetricStore miss → skip gate, do not fail verdict
                    continue
                except Exception as e:
                    gate = {"passed": False, "error": str(e), "max_abs": None}

                gate["metric_name"] = metric_name
                residual_gates.append(gate)
                if gate.get("passed"):
                    if gate_counts_as_verified(pred):
                        any_confirmed = True
                    evidence.append(
                        f"GATE PASS: {pred} — field-equation residual "
                        f"max|G_μν|={gate.get('max_abs')}"
                    )
                else:
                    if gate_counts_as_verified(pred):
                        gate_failed = True
                    evidence.append(
                        f"GATE FAIL: {pred} — residual max|G_μν|="
                        f"{gate.get('max_abs')} ({gate.get('error') or ''})"
                    )

        if any_confirmed:
            verdict = "Hypotheses verified"
        elif gate_failed:
            verdict = "Experiments completed (field-equation residual nonzero)"
        else:
            verdict = "Experiments completed (symbolic simplification pending)"

        # L5: process metrics + multi-hypothesis ranking (not world physics)
        try:
            from .agent_math import rank_hypotheses, summarize_run
            from .tool_registry import registry_summary

            n_tools = registry_summary().get("count")
            foundations = summarize_run(results, n_registry_tools=n_tools)
            ranking = rank_hypotheses(results)
        except Exception:
            foundations = {}
            ranking = []

        best = ranking[0] if ranking else None
        if ranking and len(ranking) > 1:
            top = ranking[0]
            evidence.append(
                f"RANK: best hypothesis #{top['index']} score={top['score']:.2f} "
                f"— {top.get('prediction', '')[:80]}"
            )

        # L8: known-value consistency gate
        try:
            from .known_values import check_chain, summarize_checks

            kv = summarize_checks(check_chain(results))
        except Exception:
            kv = {"n_checks": 0, "n_passed": 0, "n_failed": 0, "all_passed": False, "checks": []}
        if kv.get("n_checks"):
            if kv.get("all_passed"):
                evidence.append(
                    f"KNOWN-VALUE PASS: {kv['n_passed']}/{kv['n_checks']} textbook relations"
                )
            elif kv.get("n_failed"):
                evidence.append(
                    f"KNOWN-VALUE FAIL: {kv['n_failed']}/{kv['n_checks']} relations mismatched"
                )

        return {
            "verdict": verdict,
            "evidence": evidence,
            "n_experiments": len(successful),
            "n_failures": len(failed),
            "n_verified": numeric_confirmed + symbolic_confirmed,
            "verification": {
                "numeric_confirmed": numeric_confirmed,
                "symbolic_confirmed": symbolic_confirmed,
                "residual_gates": residual_gates,
            },
            "foundations": foundations,
            "hypothesis_ranking": ranking,
            "best_hypothesis": best,
            "known_value_checks": kv,
        }
