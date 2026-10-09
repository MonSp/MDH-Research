---
feature: analyze-sens
status: delivered
updated: 2026-10-09
branch: feat/analyze-sens
commits: 7d06d30..HEAD
---

# L40: Analyze SENS Evidence

## Goal
Make elasticity visible in the research conclusion itself: `_analyze`
appends a `SENS: ε=…` evidence line for successful 1D sweeps, alongside
the existing SWEEP trend sentence and KNOWN-VALUE gate lines.

## Design
- In `_analyze`, when a successful result has `sweep.trend.n >= 2`,
  compute `param_sweep.compute_sensitivity` from sweep points and
  append `format_sensitivity_sentence(axis, sens)` to `evidence`.
- Failures to compute are silent (no SENS line); grid path unchanged
  (grid ε already lives in viz sections).
- `capability_map` L40 row checks both function names in research_loop.py.

## Tasks
- [x] SENS evidence line in `_analyze`
- [x] tests (`tests/python/test_analyze_sens.py`, 3 cases)
- [x] README/AGENTS/capability row L40
- [x] full pytest + PR
