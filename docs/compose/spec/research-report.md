---
feature: research-report
status: delivered
updated: 2026-09-17
branch: feat/research-report
commits: f0a7d69..31b43af
---

# L10 研究报告合成

## Report

**What was built** — `report.render_single_run` / `render_campaign` / `write_report` 把 run/战役结论合成 markdown。

**Verification** — `pytest tests/python/ -q` → **455 passed**。

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

- [x] T1: report.py
- [x] T2: 回归 + 文档
