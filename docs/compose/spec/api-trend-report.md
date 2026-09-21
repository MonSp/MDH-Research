---
feature: api-trend-report
status: in-progress
updated: 2026-09-21
branch: feat/api-trend-report
commits:  # filled at delivery
---

# L21 HTTP 趋势 / 报告 / 分析端点

## Report

**What was built** — POST /trend /report；GET /analytics。

**Verification** — `pytest tests/python/ -q` → **524 passed**。

## [S1] Problem

L19 API 只有 run/campaign/bench；L10/L11/L20 的报告与趋势只能 CLI。

## [S2] Design

- POST `/trend {path, markdown?}`
- POST `/report {campaign_json, output?, markdown?}`
- GET `/analytics?journal_dir=`

## [S3] Out of Scope

- 鉴权
- 异步任务

## Tasks

- [ ] T1: api endpoints
- [ ] T2: 回归 + 文档
