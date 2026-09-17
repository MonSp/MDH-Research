---
feature: research-campaign
status: in-progress
updated: 2026-09-17
branch: feat/research-campaign
commits:  # filled at delivery
---

# L9 研究战役（多问题编排）

## Report

## [S1] Problem

`run()` 只处理单个问题；缺少共享 MetricStore 的多问题战役与程序级汇总。

## [S2] Design

`campaign.run_campaign(questions, loop_factory, share_store, stop_on_verified)`：
- 共享 loop/journal/MetricStore（可选）
- 逐问 `run()`，聚合 verdict / known_value / ranking / foundations
- `summarize_campaign` → verify_rate、known_value_rate、mean_best_score、store_growth/distance

## [S3] Out of Scope

- 并行战役
- 跨 campaign 记忆

## Tasks

- [ ] T1: campaign.py
- [ ] T2: 回归 + 文档
