---
feature: sweep-export
status: delivered
updated: 2026-10-08
branch: feat/sweep-export
commits: c238e78..HEAD
---

# L31: Sweep Export (CLI / API)

## Goal
Close the L30 loop: get sweep/grid visualization out of the process —
CSV on disk via CLI, markdown+CSV over HTTP.

## Design
- `sweep_viz.export_run_csv(result, path)` → writes first grid
  (x,y,z) or sweep (x,y) rows; returns path or None if nothing.
- `cli run --csv PATH` → export after run; stderr notes written /
  "no sweep/grid rows".
- `POST /viz` body `{question, llm?, memory_path?}` →
  `{markdown, csv, verdict}`; empty question → 400.
- `capability_map` L31 row checks `export_run_csv`, `--csv`, `"/viz"`.

## Tasks
- [x] export_run_csv + tests
- [x] cli run --csv + tests
- [x] POST /viz + tests
- [x] README/AGENTS/capability row L31
- [x] full pytest + PR
