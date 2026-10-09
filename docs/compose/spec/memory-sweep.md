---
feature: memory-sweep
status: delivered
updated: 2026-10-09
branch: feat/memory-sweep
commits: 2fda01f..HEAD
---

# L37: Memory Sweep Recall

## Goal
L14 extension: remember successful sweep hypotheses with their scan
spec (and elasticity), and re-inject them as sweep hypotheses instead
of plain tool chains.

## Design
- `extract_memorable` attaches slim `sweep` (`tool`, `params`,
  `axis`, `extract`) from `hypothesis.sweep` (or reconstructs from
  `r["sweep"]`) plus `sensitivity` (log-log ε when points allow).
- `recall_hypotheses` passes `sweep` / `memory_sensitivity` through.
- `inject_memory_candidates` emits `{prediction, sweep,
  assumptions:[memory-recall]}` for sweep entries; non-sweep entries
  stay tools-only chains.
- `capability_map` L37 row checks the three string anchors.

## Tasks
- [x] remember sweep spec + ε
- [x] recall + inject as sweep hypothesis
- [x] tests (`tests/python/test_memory_sweep.py`, 4 cases)
- [x] README/AGENTS/capability row L37
- [x] full pytest + PR
