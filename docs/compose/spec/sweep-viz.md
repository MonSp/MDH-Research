---
feature: sweep-viz
status: delivered
updated: 2026-09-22
branch: feat/sweep-viz
commits: 68bf498..HEAD
---

# L30: Sweep Visualization (ASCII + table + CSV)

## Goal
Visualize 1D sweep trends and 2D grid results as text artifacts —
no new heavy dependencies (no matplotlib/PNG/HTML).

## Design
- `sweep_viz.sparkline(ys)` → block-char sparkline (`▁▂▃▄▅▆▇█`),
  non-finite samples skipped; constant series → single repeated char.
- `sweep_viz.render_trend_table(trend)` → markdown `| x | y |` table.
- `sweep_viz.render_grid_table(grid)` → text matrix `x\y` header +
  one line per y row.
- `sweep_viz.write_csv(path, rows, headers)` → CSV with fixed header
  (`x,y` / `x,y,z`); parent dirs created.
- `sweep_viz.render_run_sweep_viz(result)` → sections for report.
- `report.render_single_run` appends "Sweep viz" / "Grid viz" when
  run results contain `sweep` / `grid`.
- `capability_map` L30 row detects `sweep_viz` symbols.

## Tasks
- [x] sparkline + trend table + grid table + write_csv
- [x] report hook (`render_run_sweep_viz`)
- [x] tests (`tests/python/test_sweep_viz.py`, 11 cases + report viz)
- [x] README/AGENTS/capability row L30
- [x] full pytest + PR
