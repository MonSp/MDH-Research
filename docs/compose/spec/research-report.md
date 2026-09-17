---
feature: research-report
status: in-progress
updated: 2026-09-17
branch: feat/research-report
commits:  # filled at delivery
---

# L10 研究报告合成

## Report

## [S1] Problem

战役/单次 run 的结论是结构化 dict，缺少可读 markdown 报告。

## [S2] Design

`report.render_single_run` / `render_campaign` / `write_report`：
- Verdict、verification、known-value、L5 foundations、hypothesis ranking、evidence
- 战役：程序摘要表 + 逐问详节

## [S3] Out of Scope

- 图表 / PDF
- LLM 润色

## Tasks

- [ ] T1: report.py
- [ ] T2: 回归 + 文档
