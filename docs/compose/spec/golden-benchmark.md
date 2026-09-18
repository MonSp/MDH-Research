---
feature: golden-benchmark
status: in-progress
updated: 2026-09-18
branch: feat/golden-benchmark
commits:  # filled at delivery
---

# L13 黄金基准套件

## Report

## [S1] Problem

缺少固定期望的端到端回归：无法一键验证 L0–L12 平台在标准问题上仍正确。

## [S2] Design

- `benchmarks/golden_questions.json`：5 个黄金问题 + expect（verdict/tools/sweep/known-value）
- `benchmark.run_benchmark` / `check_expectation` / `render_benchmark`
- CLI：`python -m orchestrator.cli bench [--suite] [--json] [--llm ...]`，失败时 exit 1

## [S3] Out of Scope

- 性能基准计时
- CI 门禁接入

## Tasks

- [ ] T1: benchmark.py + suite
- [ ] T2: CLI bench
- [ ] T3: 回归 + 文档
