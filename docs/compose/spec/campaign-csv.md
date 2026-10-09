---
feature: campaign-csv
status: delivered
updated: 2026-10-08
branch: feat/campaign-csv
commits: f4bfc25..HEAD
---

# L34: Campaign CSV Export

## Goal
Symmetry with `cli run --csv` (L31): export merged sweep/grid points
from a multi-question campaign to one CSV file.

## Design
- `cli campaign --csv PATH` — after `run_campaign`, concatenate each
  question's slim `results`, then `export_run_csv(merged, path)`.
- No plottable rows → no file, stderr note (same as `run --csv`).
- Works with `--json` (export happens before print).
- `capability_map` L34 row checks `--csv` + `export_run_csv(merged`.

## Tasks
- [x] `cmd_campaign` export + `--csv` parser flag
- [x] tests (`tests/python/test_campaign_csv.py`, 3 cases)
- [x] README/AGENTS/capability row L34
- [x] full pytest + PR
