---
feature: http-api
status: delivered
updated: 2026-09-18
branch: feat/http-api
commits: e2c643f..4dd5f4e
---

# L19 HTTP API 门面

## Report

## [S1] Problem

平台只能 CLI/Python 调用；远程 agent 需要 HTTP。

## [S2] Design

`api.create_app()`：
- GET `/health` `/known-values` `/memory/summary`
- POST `/run` `/campaign` `/bench`
- CLI `serve --host --port`
- 注意：不用 `from __future__ import annotations`，避免 FastAPI 把 body 模型误判为 query

## [S3] Out of Scope

- 鉴权 / TLS
- 异步任务队列

## Tasks

- [x] T1: api.py + CLI serve
- [x] T2: 回归 + 文档
