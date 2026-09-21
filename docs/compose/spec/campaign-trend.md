---
feature: campaign-trend
status: delivered
updated: 2026-09-21
branch: feat/campaign-trend
commits: 8afb078..16a95d3
---

# L20 战役趋势聚合

## Report

**What was built** — trend.py + CLI `trend`；campaign JSON first→last 趋势。

**Verification** — `pytest tests/python/ -q` → **517 passed**。

## [S1] Problem

多次 campaign JSON 报告分散，无法看 verify/known-value 是否随时间改善。

## [S2] Design

`trend.load_campaign_summaries` / `compute_trend` / `render_trend` / `aggregate_campaigns`
- CLI `trend PATH [--json]`
- first→last delta + series 表

## [S3] Out of Scope

- 时序图
- 多指标统计检验

## Tasks

- [x] T1: trend.py + CLI
- [x] T2: 回归 + 文档
