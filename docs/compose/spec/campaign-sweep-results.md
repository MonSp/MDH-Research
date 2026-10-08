---
feature: campaign-sweep-results
status: delivered
updated: 2026-10-08
branch: feat/campaign-sweep-results
commits: a382d4a..HEAD
---

# L33: Campaign Sweep Results

## Goal
Close the campaign gap in the L30–L32 chain: `run_campaign` used to
drop per-question `results`, so campaign reports could not render
sweep/grid viz and CSV export had nothing to read.

## Design
- `campaign.run_campaign` keeps a slim `results` slice per question —
  only `{sweep}` / `{grid}` keys, not full step traces.
- `report.render_campaign` passes `results` into the pseudo run so
  `render_single_run` emits Sweep/Grid viz + sensitivity lines.
- `export_run_csv` works on concatenated question results.
- `capability_map` L33 row checks `"results": slim` in campaign.py.

## Tasks
- [x] slim results on campaign questions
- [x] report pseudo carries results
- [x] tests (`tests/python/test_campaign_sweep_results.py`, 3 cases)
- [x] README/AGENTS/capability row L33
- [x] full pytest + PR
