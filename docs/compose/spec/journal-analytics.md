---
feature: journal-analytics
status: in-progress
updated: 2026-09-18
branch: feat/journal-analytics
commits:  # filled at delivery
---

# L11 跨会话 Journal 分析

## Report

## [S1] Problem

Journal JSONL 分散在会话目录；缺少跨会话过程指标对比。

## [S2] Design

`journal_analytics.py`：
- `load_journal_file` / `load_journal_dir`
- `session_metrics`：event mix、COMPETE/ITERATE/REPLAN 计数、observation 成功率、best score
- `compare_sessions` + `render_analytics` markdown

## [S3] Out of Scope

- 时序可视化
- 自动回归告警

## Tasks

- [ ] T1: journal_analytics.py
- [ ] T2: 回归 + 文档
