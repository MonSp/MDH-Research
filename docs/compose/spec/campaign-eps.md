---
feature: campaign-eps
status: delivered
updated: 2026-10-09
branch: feat/campaign-eps
commits: abef7bc..HEAD
---

# L38: Campaign Sweep ε Summary

## Goal
Make campaigns comparable on their sweep work: how many questions
carried sweeps, and what the average elasticity was.

## Design
- `summarize_campaign` adds:
  - `n_sweep_questions` / `sweep_rate` (questions with ≥1 sweep)
  - `mean_elasticity` (mean of per-sweep log-log ε; None if none)
- Per-question `results` (slim, L33) drive the aggregation via
  `param_sweep.compute_sensitivity`.
- `report.render_campaign` Program summary prints
  `sweep: k/n (rate …) mean ε=…` when the fields are present.
- `capability_map` L38 row checks the three anchors in campaign.py.

## Tasks
- [x] summarize_campaign sweep/ε fields
- [x] report program summary line
- [x] tests (`tests/python/test_campaign_eps.py`, 5 cases)
- [x] README/AGENTS/capability row L38
- [x] full pytest + PR
