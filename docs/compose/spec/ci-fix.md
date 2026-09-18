---
feature: ci-fix
status: delivered
updated: 2026-09-18
branch: fix/golden-bench-ci
commits: 7a527b3..99d5c32
---

# L16 修复 golden-bench CI

## Report

## [S1] Problem

L15 工作流首次跑挂：`find_package(pybind11)` 失败——CI 未安装 pybind11，也未传 `pybind11_DIR`。

## [S2] Design

`.github/workflows/golden-bench.yml`：
- `pip install ... pybind11`
- `pybind11_DIR=$(python3 -c 'import pybind11; print(pybind11.get_cmake_dir())')`
- cmake `-Dpybind11_DIR=...`

## [S3] Out of Scope

- FetchContent 化 pybind11
- 多 Python 版本矩阵

## Tasks

- [x] T1: workflow fix
- [x] T2: 回归 + 文档
