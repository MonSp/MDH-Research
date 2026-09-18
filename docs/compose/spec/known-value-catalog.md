---
feature: known-value-catalog
status: delivered
updated: 2026-09-18
branch: feat/known-value-catalog
commits: da406ce..73046a5
---

# L18 可扩展已知量目录

## Report

## [S1] Problem

L8 只有 4 条硬编码教科书关系；新增关系要改代码。

## [S2] Design

- `benchmarks/known_values.json`：formula / range / near / positive
- `known_values.load_catalog` / `evaluate_catalog_entry` / `check_result_with_catalog`
- `check_chain` 默认加载目录
- CLI `known-values [--path] [--json]`

## [S3] Out of Scope

- 文献自动抓取
- 观测数据 API

## Tasks

- [x] T1: catalog JSON + evaluate
- [x] T2: CLI + 回归 + 文档
