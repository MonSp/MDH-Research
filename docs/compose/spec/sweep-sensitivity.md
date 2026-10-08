---
feature: sweep-sensitivity
status: delivered
updated: 2026-10-08
branch: feat/sweep-sensitivity
commits: eadfaa5..HEAD
---

# L32: Sweep Sensitivity Analysis

## Goal
Quantify how strongly the response depends on each swept parameter —
elasticity ε = d ln y / d ln x for 1D sweeps, per-axis ranking for grids.

## Design
- `param_sweep.compute_sensitivity(xs, ys)` → overall log-log OLS ε
  (positive pairs), local ε list, median/max |ε_local|.
- `param_sweep.summarize_grid_sensitivity(grid)` → mean row/column
  slopes → `elasticity_x` / `elasticity_y` / `dominant_axis`
  (`x` | `y` | `tie` | None).
- `param_sweep.format_sensitivity_sentence` → `SENS: ε=… for axis`.
- `sweep_viz.render_run_sweep_viz` appends Sensitivity lines in the
  report Sweep/Grid viz sections.
- `capability_map` L32 row checks the two functions.

## Tasks
- [x] compute_sensitivity + summarize_grid_sensitivity + sentence
- [x] report/viz hook
- [x] tests (`tests/python/test_sensitivity.py`, 11 cases)
- [x] README/AGENTS/capability row L32
- [x] full pytest + PR
