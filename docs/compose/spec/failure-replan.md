---
feature: failure-replan
status: delivered
updated: 2026-09-16
branch: feat/failure-replan
commits: 6d63fda..4b83cbf
---

# L4c 失败重规划（Failure Replan）

## Report

**What was built** — `replan.py`：`diagnose_failure` 分类 missing_metric / unknown_tool / missing_param（含复数参数）/ bad_kwarg；`heuristic_repair` 前置 factory 或注入 minkowski diagonal、填默认参、同义词、剥坏 kwargs。ResearchLoop 链失败后 `_try_replan` 一次修复重跑；journal note 记 `REPLAN(...)`。

**Verification** — `pytest tests/python/ -q` → **393 passed**（含 15 项 failure-replan 测试）。评审 pass-with-minors；无 critical。

**Journey log**:
1. 缺 metric 链（只给 consumer）→ 自动前置 create_schwarzschild/kerr
2. Hawking 缺 M → 填 1.989e30
3. `_call_tool` 已会剥 unexpected kwargs，bad_kwarg 诊断多为单元层
4. 扫描路径故意不 replan（保持单点失败语义）

## [S1] Problem

顺序链执行器遇错即停（`partial_steps` 保留已完成步）。常见可修错误仍需人工改 hypothesis：

- consumer 缺 metric（链里没有 factory）
- 工具签名缺必填参（如 `hawking_temperature(M)`）
- 未知工具名 / 同义词
- 多余 kwargs

这挡住了 L4c「失败后自动换路径」。

## [S2] Design

### 模块 `src/orchestrator/replan.py`

```python
diagnose_failure(error, partial) -> {kind, tool, error}
# kind: missing_metric | unknown_tool | missing_param | bad_kwarg | execution_error | unknown

heuristic_repair(steps, diagnosis, question, step_cls) -> list[Step] | None
```

**启发式修复（无 LLM）**

| kind | 修复 |
|------|------|
| `missing_metric` | 无 factory 时：按问题关键词前置 `create_kerr/RN/dS/schwarzschild`；minkowski/flat 则注入 diagonal |
| `missing_param` | 从 `_PARAM_DEFAULTS` / `_GENERIC_DEFAULTS` 填 `M`/`m1`/`m2`/`a`… |
| `unknown_tool` | 同义词表映射（`compute_scalar`→`compute_scalar_curvature` 等） |
| `bad_kwarg` | 剥离 unexpected keyword |

已有 factory 时不重复前置；修复与原链相同则视为 no-op。

### ResearchLoop 接入

`run()` 链路径 `except` 中：

1. `diagnose` + `heuristic_repair`
2. 修复成功 → 重跑 `_execute_chain`；observation 带 `replan` 字段；结果标 `success=True` + `replan` note
3. 再失败或不可修 → 维持原失败语义
4. journal `log_note(REPLAN: ...)` 留痕

### 测试边界

- diagnose 四类 kind
- repair：前置 factory / minkowski diagonal / 填 M / 剥 kwarg / 同义词
- e2e：缺 metric 链自动修复；Hawking 缺 M 自动修复；journal 有 REPLAN note；不可修仍失败

## [S3] Out of Scope

- LLM 多候选重规划
- 扫描级失败恢复
- 跨假设学习

## Tasks

- [x] T1: replan.py diagnose + heuristic_repair — acceptance: 单元测试过 (covers: S2)
- [x] T2: ResearchLoop._try_replan 接入 — acceptance: e2e 自动修复链 (covers: S2; depends: T1)
- [x] T3: 回归 + 文档 — acceptance: pytest 全绿；README/AGENTS 提及 L4c (covers: S2)
