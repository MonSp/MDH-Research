# MDH-Research (大荒界-科研)

[![Tests](https://img.shields.io/badge/tests-377%20passed-brightgreen)]()
[![C++17](https://img.shields.io/badge/C%2B%2B-17-blue)]()
[![Python](https://img.shields.io/badge/Python-3.11+-yellow)]()
[![中文](https://img.shields.io/badge/README-中文-orange)](README.md)

**Physics computation that agents can call, orchestrate, verify, and sweep.**

MDH-Research is the fourth subproject of the MatrixDahuang ecosystem: an **agent-native physics experiment platform**. A C++17 symbolic geometry core and 23 Python physics modules are exposed as **80 orchestratable tools**, with sequential chains, SymPy / field-equation residual verification, and multi-point parameter sweeps that summarize trends.

> **One-line positioning:** a physics computation experiment platform that agents can call, chain, sweep, and verify symbolically/residually.  
> *Assisted* theory calculation is closed-loop; *autonomous* discovery is the next layer.

中文: [README.md](README.md)

---

## The problem this solves

Physics libraries are plentiful but hostile to agents:

| Pain point | What we do |
|------------|------------|
| LLMs don't know which functions exist or how to fill params | Unified `tool_registry` (80 tools) + OpenAI function schemas |
| Metric / tensor objects can't cross JSON | `MetricStore` named handoff; factories return metadata, consumers take `metric_name` |
| One function call at a time | Sequential `tools[]` chains; factory outputs auto-inject into later steps |
| “Computed” ≠ “correct” | SymPy identically-zero proofs + vacuum Einstein residual gate + bound numeric checks |
| Parameter studies need hand-written loops | `sweep` axis expansion + trend summary (direction / log-log slope / Spearman) |

---

## Architecture at a glance

```
Natural-language question
    │
    ▼
ResearchLoop  ── LLM / pattern  ──►  hypothesis (tool | tools chain | sweep)
    │
    ▼
tool_registry (80 tools)  +  MetricStore
    │  sequential execution; create_* metric_name injected into consumers
    ▼
Verification  ── SymPy simplify → bound numeric → G_μν residual gate
    │
    ▼
ResearchJournal  ── hypothesis → experiment → tool_call* → observation → conclusion
    │
    ▼
Outcome: Hypotheses verified / SWEEP trend / evidence list
```

### Live end-to-end (main)

```text
Q: What is the scalar curvature of Schwarzschild spacetime?
   → create_schwarzschild → compute_scalar_curvature
   → CONFIRMED (SymPy simplify → 0)
   → GATE PASS  max|G_μν| ≈ 2.5e-16
   → verdict: Hypotheses verified

Q: How does Hawking temperature vary as a function of mass?
   → sweep M ∈ {1e30, 1e31, 1e32}, extract T_K
   → SWEEP: T_K vs M → decreasing, log-log slope ≈ -1.0   # T ∝ 1/M
```

---

## Quick start

```bash
git clone --recursive https://github.com/MonSp/MatrixDahuang.git
cd MatrixDahuang/research

# C++ build + tests
cmake --preset default && cmake --build build
ctest --test-dir build                    # 59 C++ tests

# Python tests
pip install sympy scipy matplotlib numpy pytest
python3 -m pytest tests/python/ -v       # 318+ Python tests
```

### Try it in three minutes

```python
import sys
sys.path.insert(0, "src")
sys.path.insert(0, "build/src/bindings")

from orchestrator.research_loop import ResearchLoop

loop = ResearchLoop()  # set LLM_API_KEY for a real LLM; otherwise pattern fallback

# 1) Compute + verify
r = loop.run("What is the scalar curvature of Schwarzschild spacetime?")
print(r["conclusion"]["verdict"])
# → Hypotheses verified

# 2) Parameter sweep + trend
r = loop.run("How does Hawking temperature vary as a function of mass? Scan several masses.")
t = r["results"][0]["sweep"]["trend"]
print(t["direction"], t["log_log_slope"])
# → decreasing  -1.0
```

### Call tools directly

```python
from orchestrator.tool_registry import execute_tool, registry_summary

print(registry_summary()["count"])  # 80
execute_tool("create_schwarzschild", {"M": 1})
R = execute_tool("compute_scalar_curvature", {"metric_name": "schwarzschild"})
print(R.evaluate({"M": 1, "r": 6, "theta": 1.5708, "phi": 0, "t": 0}))  # ~0
print(execute_tool("age_of_universe", {})["age_gyr"])  # ~13.8
```

---

## Agent capability layers

Grounded in code and evals, not vision slides:

| Layer | What | Status |
|-------|------|--------|
| **L0 Compute library** | C++ symbolic core + 23 Python physics modules, 377 tests | ✅ |
| **L1 Agent tool surface** | 80 tools in one registry; MetricStore handoff | ✅ |
| **L2 Experiment ledger** | ResearchJournal full event chain | ✅ |
| **L3 Multi-step orchestration** | LLM `tools[]` sequential chains; `metric_name` injection | ✅ |
| **L4 Verification** | SymPy zero + bound numeric + vacuum residual gate | ✅ |
| **L4b Parameter sweep** | Axis expansion + trend summary | ✅ |
| **L4c Failure replanning** | Diagnose + heuristic repair (missing metric/param, synonyms, bad kwargs) then retry | ✅ |
| **L5 Agent foundations** | Trajectory entropy, state distance, sweep info + **hypothesis ranking** (journaled) | ✅ |
| **L6 Hypothesis competition** | When the first round fails, regenerate alternatives (heuristic/LLM) and re-rank | ✅ |
| **L7 Multi-round iterate** | After competition, up to 2 more rounds of param mutations / unused consumers | ✅ |
| **L8 Known-value gate** | Textbook checks: Hawking T∝1/M, universe age, chirp mass, Schwarzschild QNM | ✅ |
| **L9 Research campaign** | Multi-question runs with shared MetricStore; program-level verify/score summary | ✅ |
| **L10 Research report** | Campaign/single run → structured markdown (verdict/verify/ranking/evidence) | ✅ |
| **L11 Journal analytics** | Cross-session JSONL metrics: COMPETE/ITERATE/REPLAN, success rate, top tools | ✅ |
| **L12 CLI facade** | `python -m orchestrator.cli` run/campaign/report/analytics/bench | ✅ |
| **L13 Golden benchmark** | 5 standard questions + expects; `cli bench` one-shot regression | ✅ |
| **L14 Hypothesis memory** | Remember successful tool chains; keyword recall + inject; `cli memory` / `--memory` | ✅ |
| **L15 Platform integration** | CLI `--memory` flag + GitHub Actions golden-bench gate | ✅ |
| **L16 CI fix** | Install pybind11 and pass `pybind11_DIR` so golden-bench configures | ✅ |

### Compute / reason / verify

| Capability | Level | Notes |
|------------|-------|-------|
| **Compute** | Mature | 80 tools; named Metric handoff; factory → consumer chains |
| **Reasoning (orchestration)** | Multi-step + sweep | Tool selection ~99% chain-aware; sequential exec; axis trends |
| **Reasoning (theory)** | Assist, not replace | Can orchestrate “Kerr vacuum / T_H vs M”; no open hypothesis search or literature grounding |
| **Verify** | Symbolic + residual + trend | SymPy proves R≡0; G_μν gate; rejects unbound/NaN false passes |

---

## Agent tool surface

`src/orchestrator/tool_registry.py` is the single source of truth (aligned with `config/research-skill-mapping.json`).

| Mechanism | Module | Role |
|-----------|--------|------|
| **MetricStore** | `metric_store.py` | Named handoff of live C++ Metrics |
| **Sequential chains** | `research_loop.py` | `tools[]` in order; factory → consumer inject |
| **Verification** | `verification.py` | SymPy / numeric / vacuum residual |
| **Parameter sweep** | `param_sweep.py` | Axis expand + trend summary |

### Sequential chain

```json
{
  "prediction": "Kerr is a vacuum solution so R=0",
  "tools": [
    {"tool": "create_kerr", "params": {"M": 1, "a": 0.5}},
    {"tool": "compute_scalar_curvature", "params": {}}
  ]
}
```

### Parameter sweep

```json
{
  "prediction": "Hawking temperature decreases as 1/M",
  "sweep": {
    "tool": "hawking_temperature",
    "axis": {"name": "M", "values": [1e30, 1e31, 1e32]},
    "extract": "T_K"
  }
}
```

Chain sweep (inject axis into a factory step):

```json
{
  "tools": [
    {"tool": "create_schwarzschild", "params": {"M": 1}},
    {"tool": "compute_kretschmann", "params": {}}
  ],
  "sweep": {
    "axis": {"name": "M", "values": [1, 2, 3]},
    "inject": {"tool": "create_schwarzschild", "param": "M"},
    "extract": null
  }
}
```

| Trend field | Meaning |
|-------------|---------|
| `direction` | increasing / decreasing / non-monotonic / flat |
| `spearman_rho` | Rank correlation (n≥3) |
| `log_log_slope` | Log-log least-squares slope (power-law check; T∝M⁻¹ → −1) |
| `y_ratio` | y[-1]/y[0] |
| `points` | `{x, y}` or `{x, error}` rows |

Limits: max 12 axis points; a failed point does not abort the sweep; fewer than 2 finite samples fail the hypothesis.

**Verified trends**

| Sweep | Axis | Result |
|-------|------|--------|
| Hawking T | M = 1e30…1e32 | `decreasing`, log-log slope ≈ **−1** |
| Schwarzschild K | M = 1…3 (chain) | `increasing` (K∝M² at fixed r) |

### Verification pipeline

1. **SymPy** `simplify` proves the expression identically zero (C++ `is_zero` fails on full GR)
2. **Numeric** point checks only when free symbols are fully bound (rejects false zeros from unbound L/a)
3. **Vacuum residual** Einstein tensor G_μν≈0 at far-field points for Schwarzschild/Kerr factories (RN/dS excluded)

Conclusions carry a `verification` summary. Kerr is a diagonal approximation: gate uses tol=1e-4 and far-field samples.

---

## Physics capabilities

### GR & black holes
- Metrics; Christoffel → Riemann → Ricci → Einstein → Kretschmann
- Schwarzschild / Kerr / Reissner-Nordström / de Sitter
- Horizon & singularity analysis; Hawking T / evaporation / entropy; Unruh
- Causal structure: light cones, timelike/null/spacelike

### Gravitational waves & compact objects
- QNMs (Schwarzschild/Kerr); RW/Zerilli; strain h₊/h×
- Binary evolution, chirp mass, Fisher/SNR, horizon distance
- 1PN/2PN, quadrupole flux
- Neutron star TOV, M–R relation, SLy4 EOS, tidal deformability

### Cosmology
- FLRW / Friedmann, age of the universe, angular & luminosity distances
- Growth factor, BBKS, power spectrum, BAO
- Inflation slow-roll, n_s, r, primordial spectra
- CMB C_ℓ, acoustic peaks, Silk damping
- Dark energy CPL, f(R), ΛCDM

### Numerical relativity & formalisms
- ADM 3+1, BSSN, merger waveforms
- Tetrads, Newman-Penrose, Petrov types
- Killing vectors, linearized gravity, energy conditions

### Benchmarks

| Metric | Check | Result |
|--------|-------|--------|
| Schwarzschild | Christoffel + Ricci=0 + K=48M²/r⁶ | ✓ SymPy |
| FLRW (k=0) | Christoffel + R=6(ä/a+H²) | ✓ |
| Kerr | structure + numerical Ricci=0 + horizons | ✓ |
| Minkowski | Γ=0, R=0, K=0 | ✓ |
| de Sitter | R=4Λ | ✓ |
| Reissner-Nordström | nonzero Ricci (EM source) | ✓ |
| S² / H² | R=±2 | ✓ |

---

## Stack & layout

- **C++17** symbolic core (expression trees, tensors, differential geometry)
- **pybind11** Python bindings
- **Python 3.11+** orchestration, SymPy/SciPy/NumPy
- **CMake / Catch2 / pytest**

```
research/
├── src/core/           # C++ symbol / tensor / geometry
├── src/bindings/       # pybind11
├── src/orchestrator/   # 23 physics modules + registry / loop / verify / sweep
├── config/             # research-skill-mapping.json
├── skills/             # compute / analyze / experiment / report
├── scripts/            # eval_tool_selection.py
├── tests/              # 59 C++ + 318+ Python
└── docs/compose/spec/  # feature specs
```

---

## Agent-kernel integration

```
ResearchLoop → ResearchJournal → Skill Manifests → AgentKernelBridge
                                              ↕ unix socket / JSON-RPC
                                         agent-kernel (ECS)
```

- 27 research skills mapped to xianxia abilities (compute / insight / simulate / observe)
- Journal dual backend: kernel EventJournal or local JSONL

---

## Ecosystem

| Subproject | Feedback path |
|------------|---------------|
| **company** | Research assistant skill packs, numeric backends |
| **game** | Physics simulation, GW signal generation |
| **kernel** | Shared ECS agents, journal consumers |

Specs: `docs/compose/spec/` (mvp-symbolic-geometry, tool-registry-closure, chain-executor, verify-upgrade, param-sweep)

## License

Apache 2.0
