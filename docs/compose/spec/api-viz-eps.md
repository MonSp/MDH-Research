---
feature: api-viz-eps
status: delivered
updated: 2026-10-12
branch: feat/api-viz-eps
commits: 6ff24f5..HEAD
---

# L44: API Viz Sensitivity

## Goal
Make ε readable over HTTP: `POST /viz` returns structured sensitivity
alongside markdown/csv.

## Design
- After `loop.run`, scan `result.results[*].sweep.points` and compute
  `param_sweep.compute_sensitivity`; first finite ε wins.
- Response adds `sensitivity: {axis, elasticity, n,
  median_abs_local}` (empty dict when no sweep / undefined ε).
- Existing `markdown` / `csv` / `verdict` fields unchanged.
- `capability_map` L44 row checks `"sensitivity": sensitivity`.

## Tasks
- [x] /viz sensitivity field
- [x] tests (`tests/python/test_api_viz_eps.py`, 3 cases)
- [x] README/AGENTS/capability row L44
- [x] full pytest + PR
