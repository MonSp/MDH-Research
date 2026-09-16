---
feature: hypo-compete
status: delivered
updated: 2026-09-16
branch: feat/hypo-compete
commits: 41a255f..db16b62
---

# L6 假设竞争与再生成

## Report

**What was built** — 首轮全失败时：`compete.should_compete` → `heuristic_alternatives`（曲率/分析 sibling tool）或 LLM 再生成 → 再执行 + replan → 合并结果重排。`conclusion.competed` + journal `COMPETE:` note。

**Verification** — `pytest tests/python/ -q` → **428 passed**。

## [S1] Problem

首轮假设选错 tool / 写错链时，没有自动换假设再试；L5 ranking 只排序不生成。

## [S2] Design

- `should_compete`: 仅当**无成功结果**时竞争（有工作路径不抢跑）
- `heuristic_alternatives`: 曲率 sibling / 分析 sibling / 兜底 Schwarzschild 链
- `llm_alternatives`: 可选，有 API key 时
- `_maybe_compete`: 执行 alt，失败走 `_try_replan`，journal 记 hypothesis + COMPETE note
- 重新 `_analyze` 排序

## [S3] Out of Scope

- 多轮迭代进化
- 贝叶斯优化 / bandit

## Tasks

- [x] T1: compete.py — acceptance: 单元测试过
- [x] T2: ResearchLoop._maybe_compete — acceptance: 弱首轮 e2e 变 verified
- [x] T3: 回归 + 文档
