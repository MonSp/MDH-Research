---
feature: api-capmap
status: delivered
updated: 2026-09-22
branch: feat/api-capmap
commits: 56d37ab..HEAD
---

# L28 HTTP 能力地图 + CI fastapi 修复

## Report

**What was built** — CI 装 fastapi；`create_app` 测试可 skip；GET `/capmap` + `/capmap/check-readme`。

**Verification** — `pytest tests/python/ -q` → **552 passed**。

## [S1] Problem

1. CI 缺 `fastapi` 导致 `test_create_app_importable` 失败  
2. 远程无法查询能力地图 / README 同步状态

## [S2] Design

- CI 安装 `fastapi uvicorn`；缺包时测试 skip
- GET `/capmap`（summary + markdown）
- GET `/capmap/check-readme`（`{in_sync, stale[]}`）

## [S3] Out of Scope

- 鉴权
- 在 API 内改写 README

## Tasks

- [x] T1: CI fix + API endpoints
- [x] T2: 回归 + 文档
