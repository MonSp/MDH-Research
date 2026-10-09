---
feature: trend-eps
status: delivered
updated: 2026-10-09
branch: feat/trend-eps
commits: 53b4405..HEAD
---

# L39: Cross-Campaign ε Trend

## Goal
Extend L20 campaign trend so multi-campaign JSON archives show how
sweep coverage and mean elasticity moved first → last (L38 fields).

## Design
- `compute_trend` delta keys += `n_sweep_questions`, `sweep_rate`,
  `mean_elasticity` (None on either end → omitted from delta).
- `series` entries carry `sweep_rate` / `mean_elasticity`.
- `render_trend` series table adds `sweep` and `ε` columns;
  delta table already prints any keys present.
- `capability_map` L39 row checks the three anchors in trend.py.

## Tasks
- [x] delta + series sweep/ε fields
- [x] render_trend columns
- [x] tests (`tests/python/test_trend_eps.py`, 5 cases)
- [x] README/AGENTS/capability row L39
- [x] full pytest + PR
