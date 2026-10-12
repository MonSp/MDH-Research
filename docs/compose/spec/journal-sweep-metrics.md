---
feature: journal-sweep-metrics
status: delivered
updated: 2026-10-12
branch: feat/journal-sweep-metrics
commits: 03a865c..HEAD
---

# L43: Sweep Process Metrics (Journal Analytics)

## Goal
Make sweep/grid work observable: analytics report how many
`sweep:`/`grid:` experiments ran, how often they failed, and how long
they took.

## Design
- `session_metrics` finds experiments whose `tool` starts with
  `sweep:` or `grid:`, matches observations via `parent_id`, and
  returns:
  - `n_sweep_experiments`
  - `n_sweep_failures` / `sweep_failure_rate` (None if no obs)
  - `mean_sweep_duration_ms` (None if no durations)
- `compare_sessions` aggregates the same four fields.
- `render_analytics` Overview gains a `- sweep experiments: … failure
  rate: … mean duration: …` line.
- `capability_map` L43 row checks the three names in
  journal_analytics.py.

## Tasks
- [x] session_metrics sweep count/fail/duration
- [x] compare_sessions aggregate + render line
- [x] tests (`tests/python/test_journal_sweep_metrics.py`, 5 cases)
- [x] README/AGENTS/capability row L43
- [x] full pytest + PR
