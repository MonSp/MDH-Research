---
feature: platform-integration
status: delivered
updated: 2026-09-18
branch: feat/platform-integration
commits: fcafad5..eb53cc1
---

# L15 平台集成：CLI memory 挂接 + CI 基准门禁

## Report

## [S1] Problem

L14 memory 只能 API 启用；CLI 无 `--memory`；无 CI 一键跑 pytest + golden bench。

## [S2] Design

- CLI `run|campaign --memory PATH`（opt-in，缺省关闭）
- `.github/workflows/golden-bench.yml`：C++ build + ctest + pytest + `cli bench --llm off`

## [S3] Out of Scope

- 矩阵多 OS
- 缓存 / 产物上传

## Tasks

- [x] T1: CLI --memory
- [x] T2: CI workflow
- [x] T3: 回归 + 文档
