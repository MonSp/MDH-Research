---
feature: research-checkpoint
status: in-progress
updated: 2026-09-21
branch: feat/research-checkpoint
commits:  # filled at delivery
---

# L23 研究检查点快照

## Report

**What was built** — checkpoint.py + CLI save/list/show。

**Verification** — `pytest tests/python/ -q` → **531 passed**。

## [S1] Problem

run 结论只能当场看；缺少可复用的 checkpoint JSON（审计 / 报告 / 趋势输入）。

## [S2] Design

`checkpoint.save_checkpoint / load_checkpoint / list_checkpoints / checkpoint_to_run_result`
- CLI `checkpoint save|list|show`
- 不重放 live C++ Metric，只存结论与 summary

## [S3] Out of Scope

- MetricStore 热恢复
- 分布式 checkpoint

## Tasks

- [ ] T1: checkpoint.py + CLI
- [ ] T2: 回归 + 文档
