---
feature: capmap-readme-sync
status: delivered
updated: 2026-09-21
branch: feat/capmap-readme-sync
commits: ade1d73..HEAD
---

# L26 能力表 README 同步

## Report

**What was built** — sync_readme 标记区 + CLI `capmap --write-readme`。

**Verification** — `pytest tests/python/ -q` → **544 passed**；README 内省 28/28 OK。

## [S1] Problem

L25 capmap 只打印表格；README 手工表仍会漂移。

## [S2] Design

- `render_level_table` / `sync_readme` / `readme_capability_synced`
- 标记 `<!-- capability-map:begin|end -->`
- CLI `capmap --write-readme`

## [S3] Out of Scope

- CI 强制 dirty check（后续可加）

## Tasks

- [x] T1: sync functions + CLI
- [x] T2: 回归 + 文档
