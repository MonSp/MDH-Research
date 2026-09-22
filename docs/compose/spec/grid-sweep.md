---
feature: grid-sweep
status: in-progress
updated: 2026-09-22
branch: feat/multi-sweep
---

# L29: 2D Grid Parameter Sweep

## Goal
Extend parameter sweeps from a single axis to a Cartesian 2D grid so
campaigns can explore interactions between two parameters (e.g. lensing M×b).

## Design
- `param_sweep.expand_grid(x_axis, y_axis)` → list of `{x, y}` cells,
  capped at `MAX_GRID_POINTS` (16).
- `param_sweep.summarize_grid(cells, x_name, y_name)` → finite z stats,
  direction along first fixed y row, min/max.
- `ResearchLoop._run_grid_hypothesis` when `sweep.grid` present:
  tool called once per cell, `extract_numeric` per cell, journal
  EXPERIMENT `grid:<tool>` + OBSERVATION.
- Analysis treats `result.grid.n >= 1` as sweep-style evidence
  (`any_confirmed` → verdict "Hypotheses verified").

## Tasks
- [x] expand_grid + summarize_grid + format_grid_sentence
- [x] `_run_grid_hypothesis` + analysis evidence path
- [x] tests (`tests/python/test_grid_sweep.py`, 7 cases)
- [x] README/AGENTS/capability row L29
- [ ] full pytest + PR
