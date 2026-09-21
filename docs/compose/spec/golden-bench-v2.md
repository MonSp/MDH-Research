---
feature: golden-bench-v2
status: in-progress
updated: 2026-09-21
branch: feat/golden-bench-v2
commits:  # filled at delivery
---

# L22 黄金基准扩展

## Report

**What was built** — 黄金 suite 扩展到 10 题。

**Verification** — `pytest tests/python/ -q` → **527 passed**。

## [S1] Problem

黄金问题只有 5 个，覆盖不了 Kretschmann / 蒸发链 / QNM / chirp 等常用路径。

## [S2] Design

扩展 `benchmarks/golden_questions.json` 至 ≥8 条，期望仍以 pattern 可稳定达成为准。

## [S3] Out of Scope

- LLM 路径断言
- 性能计时

## Tasks

- [ ] T1: 扩展 suite
- [ ] T2: 回归 + 文档
