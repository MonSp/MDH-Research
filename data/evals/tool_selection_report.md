# LLM Tool-Selection Evaluation Report

**Date**: 2026-09-15  
**Model**: deepseek-v4-flash (`LLM_BASE_URL=https://api.deepseek.com`)  
**Catalog**: compact (80 tool names + descriptions) from `tool_registry`  
**Script**: `scripts/eval_tool_selection.py`  
**Raw**: `data/evals/tool_selection_compact.json`

## Results

| Metric | Value |
|--------|------:|
| Cases | 74 (69 single + 5 multi) |
| Tools in catalog | 80 |
| Parse rate | 98.6% (1 empty content = token budget) |
| **Strict top-1** | **85.1%** |
| **Chain-aware (factory→consumer)** | **98.6%** (74/74 after p08 retry) |
| Multi-step first step | **100%** (5/5) |
| Multi-step full chain | **100%** (5/5 exact order) |
| Mean latency | ~1.3 s |

Per-domain chain-aware accuracy (single-tool questions): **all domains 1.00** except ADM (2/3 due to p08 token starvation; retry OK).

## Key finding: the model already plans chains

“Failures” under strict top-1 are almost all **correct multi-step plans** scored too strictly:

| Gold expected (single) | Model predicted | Verdict |
|------------------------|-----------------|---------|
| `compute_scalar_curvature` | `create_schwarzschild` → `compute_scalar_curvature` | **Better than gold** |
| `analyze_horizon` | `create_schwarzschild` → `analyze_horizon` | **Better than gold** |
| `solve_geodesic` | `create_schwarzschild` → `solve_geodesic` | **Better than gold** |

Explicit multi-step gold cases matched **exactly** (order included):

```
m01 create_kerr → compute_scalar_curvature
m02 create_schwarzschild → classify_symmetry
m03 create_desitter → compute_kretschmann
m04 hawking_temperature → evaporation_time
m05 create_schwarzschild → solve_geodesic
```

## Implications for multi-step derivation planner

1. **Do not build a heavy symbolic planner first.**  
   Tool *selection* is solved (chain-aware ~99%). The gap is **execution orchestration**, not choice.

2. **ResearchLoop should execute returned tool lists sequentially**, threading `metric_name` from factory outputs into consumer args. Current loop treats each hypothesis as one tool call.

3. **Gold/eval convention**: metric-dependent questions should expect `create_*` + consumer, not consumer alone. Strict top-1 understates capability.

4. **Prompt**: compact name+description catalog is enough; full OpenAI schemas may waste tokens. Keep max_tokens ≥ 2048 for reasoning models.

5. **Remaining hard problems** (not selection):
   - Parameter filling (M, r, coords) from natural language
   - Intermediate artifact passing beyond MetricStore
   - Failure recovery / alternative tools
   - Multi-hypothesis search and verification (SymPy / residuals)

## Recommended next increment

**Sequential chain executor** in ResearchLoop:
- Accept `tools: [t1, t2, ...]` from LLM
- Execute t1, capture `metric_name` / outputs
- Inject into t2 params if missing
- Log each step to journal

Estimated effort: small (reuse existing `_execute` + MetricStore). Expected unlock: end-to-end “create Kerr → curvature → horizon → QNM” without hand-holding.

## Repro

```bash
cd research
PYTHONPATH=src:build/src/bindings python3 scripts/eval_tool_selection.py compact
```
