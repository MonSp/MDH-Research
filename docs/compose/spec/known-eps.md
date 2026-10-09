---
feature: known-eps
status: delivered
updated: 2026-10-09
branch: feat/known-eps
commits: 0fda250..HEAD
---

# L36: Known-Value Epsilon Gate

## Goal
Extend the known-value gate (L8/L18) to power-law sweeps: a Hawking
temperature sweep must show elasticity ε ≈ −1 (T ∝ 1/M).

## Design
- `SWEEP_EPSILON_EXPECTED = {"hawking_temperature": -1.0}`,
  `SWEEP_EPSILON_TOL = 0.15`.
- `check_sweep_sensitivity(sweep, tool)` → compares
  `compute_sensitivity(...).elasticity` to the expected exponent;
  unknown tools / <2 points / undefined ε → None.
- `check_chain` also inspects `r["sweep"]` (tool from steps[0] or
  `hypothesis.sweep.tool`) and appends the check.
- Lands in `conclusion.known_value_checks` + KNOWN-VALUE evidence.

## Tasks
- [x] check_sweep_sensitivity + check_chain sweep scan
- [x] tests (`tests/python/test_known_eps.py`, 6 cases)
- [x] README/AGENTS/capability row L36
- [x] full pytest + PR
