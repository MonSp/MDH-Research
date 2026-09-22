---
feature: capmap-ci-check
status: delivered
updated: 2026-09-22
branch: feat/l27-capmap-ci-check
commits: 32b6a1b..HEAD
---

# L27 能力表 CI 门禁

## Report

**What was built** — `capmap --check-readme` + golden-bench 步骤；detect 增加 L27 行。

**Verification** — `pytest tests/python/ -q` → **549 passed**。

## [S1] Problem

L26 可写 README，但 CI 不校验同步；能力表仍可能漂移。

## [S2] Design

- CLI `capmap --check-readme`：README/README_en 标记区与当前内省不一致则 exit 1
- golden-bench.yml 增加 `Capability README sync check` 步骤

## [S3] Out of Scope

- 自动在 CI 内改写 README
- 中英差异容忍

## Tasks

- [x] T1: --check-readme + workflow
- [x] T2: 回归 + 文档
