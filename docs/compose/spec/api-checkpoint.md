---
feature: api-checkpoint
status: delivered
updated: 2026-09-21
branch: feat/api-checkpoint
commits: b2ca3e4..e54245b
---

# L24 HTTP 检查点端点

## Report

**What was built** — POST /checkpoint；GET /checkpoint/list /checkpoint/show。

**Verification** — `pytest tests/python/ -q` → **534 passed**。

## [S1] Problem

L23 checkpoint 只有 CLI/Python；远程 agent 无法存取研究结论快照。

## [S2] Design

- POST `/checkpoint {question, label?, path?, llm?, memory_path?}`
- GET `/checkpoint/list`
- GET `/checkpoint/show?path=`

## [S3] Out of Scope

- 鉴权
- 分布式存储

## Tasks

- [x] T1: API endpoints
- [x] T2: 回归 + 文档
