---
feature: campaign-checkpoint-sweep
status: delivered
updated: 2026-10-09
branch: feat/campaign-checkpoint-sweep
commits: ae7667e..HEAD
---

# L41: Campaign Checkpoint Sweep Results

## Goal
Extend L35's checkpoint slim-results to campaign kind: a campaign
snapshot keeps per-question slim `results` so report viz and CSV
export still work after `save_checkpoint`.

## Design
- `save_checkpoint(kind="campaign")` stores `questions: slim_qs` —
  one entry per question with verdict/evidence/ranking fields plus
  slim `{sweep}` / `{grid}` results only (no step traces).
- `checkpoint_to_run_result` restores `questions` (was `[]`).
- Non-sweep results dropped from slim lists (`[]`).
- `capability_map` L41 row checks both string anchors.

## Tasks
- [x] slim questions on campaign save + restore
- [x] tests (`tests/python/test_campaign_checkpoint_sweep.py`, 4 cases)
- [x] README/AGENTS/capability row L41
- [x] full pytest + PR
