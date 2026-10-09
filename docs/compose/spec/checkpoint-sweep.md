---
feature: checkpoint-sweep
status: delivered
updated: 2026-10-09
branch: feat/checkpoint-sweep
commits: a79f847..HEAD
---

# L35: Checkpoint Sweep Results

## Goal
Last link in the L30–L34 chain: checkpoints dropped `results`, so a
saved snapshot could not re-render sweep/grid viz or export CSV.

## Design
- `save_checkpoint` (kind=run) stores slim `results` — only
  `{sweep}` / `{grid}` slices (serialized), never full step traces.
- `checkpoint_to_run_result` restores `results` so
  `render_single_run` / `export_run_csv` work on the pseudo run.
- Non-sweep runs save `results: []` (no junk).
- `capability_map` L35 row checks both string anchors.

## Tasks
- [x] slim results in save + restore
- [x] tests (`tests/python/test_checkpoint_sweep.py`, 4 cases)
- [x] README/AGENTS/capability row L35
- [x] full pytest + PR
