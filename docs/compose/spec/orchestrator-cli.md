---
feature: orchestrator-cli
status: delivered
updated: 2026-09-18
branch: feat/orchestrator-cli
commits: 73e8176..bcbc051
---

# L12 Orchestrator CLI 门面

## Report

## [S1] Problem

L0–L11 能力只能在 Python API 里调用；缺少统一命令行入口。

## [S2] Design

`python -m orchestrator.cli`：
- `run QUESTION [--json] [--llm auto|on|off] [--log-dir]`
- `campaign Q... [--report PATH] [--json] [--fresh-store] [--stop-on-verified]`
- `report --campaign-json FILE [-o PATH]`
- `analytics --journal-dir DIR [--json]`

## [S3] Out of Scope

- HTTP API
- 交互式 TUI

## Tasks

- [x] T1: cli.py
- [x] T2: 回归 + 文档
