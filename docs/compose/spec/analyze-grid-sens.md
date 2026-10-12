---
feature: analyze-grid-sens
status: delivered
updated: 2026-10-09
branch: feat/analyze-grid-sens
commits: 85089d4..HEAD
---

# L42: Grid Axis SENS Evidence

## Goal
Symmetric with L40: `_analyze` also appends axis-sensitivity evidence
for successful 2D grids so conclusions state which parameter dominates.

## Design
- In `_analyze`, when a successful result has `grid.n >= 1`, call
  `param_sweep.summarize_grid_sensitivity` and append
  `GRID-SENS: ε_x=… ε_y=… dominant=…` to `evidence`.
- Failures silent; 1D SENS path unchanged (L40).
- `capability_map` L42 row checks `GRID-SENS` + function name in
  research_loop.py.

## Tasks
- [x] GRID-SENS evidence line in `_analyze`
- [x] tests (`tests/python/test_analyze_grid_sens.py`, 3 cases)
- [x] README/AGENTS/capability row L42
- [x] full pytest + PR
