---
feature: ci-pyyaml
status: delivered
updated: 2026-09-18
branch: fix/ci-pyyaml
commits: 1703a92..97f97e9
---

# L17 CI 加固：pyyaml 收集失败

## Report

## [S1] Problem

L16 过 cmake 后，pytest 在收集 `test_platform_integration.py` 时因顶层 `import yaml` 失败（CI 未装 PyYAML）。

## [S2] Design

- 测试去掉顶层 `import yaml`（函数内 try/import + skip）
- workflow `pip install ... pyyaml`
- `pyproject.toml` dev 依赖加 `pyyaml`

## [S3] Out of Scope

- 重构全部 CI 步骤

## Tasks

- [x] T1: 代码/workflow/pyproject 修复
- [x] T2: 回归 + 文档
