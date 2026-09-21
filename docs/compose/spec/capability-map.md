---
feature: capability-map
status: delivered
updated: 2026-09-21
branch: feat/capability-map
commits: 1c8935a..3447be7
---

# L25 平台能力地图生成器

## Report

**What was built** — capability_map.py + CLI capmap。

**Verification** — `pytest tests/python/ -q` → **538 passed**。

## [S1] Problem

README 能力表手工维护，易与代码漂移。

## [S2] Design

`capability_map.detect_capabilities / render_capability_map / capability_summary`
- 内省 registry / 模块符号 / CLI 子命令 / 文件存在性
- CLI `capmap [--json]`

## [S3] Out of Scope

- 自动改写 README
- CI 门禁断言

## Tasks

- [x] T1: capability_map.py + CLI
- [x] T2: 回归 + 文档
