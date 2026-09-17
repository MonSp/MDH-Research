---
feature: hypo-iterate
status: delivered
updated: 2026-09-17
branch: feat/hypo-iterate
commits: de18f74..44d1a23
---

# L7 多轮迭代搜索

## Report

**What was built** — 竞赛后仍无成功路径时，最多 2 轮 `iterate_hypotheses`（工厂参数变体 + 未用 consumer）；`conclusion.iterate_rounds` + journal `ITERATE rN:`。有成功即停。

**Verification** — `pytest tests/python/ -q` → **434 passed**。

## [S1] Problem

L6 只做一轮竞争；若仍无成功路径，没有后续迭代。

## [S2] Design

- `compete.iterate_hypotheses(question, results, round_n)`：工厂参数变体（M/a/Λ）+ 未用 consumer
- `ResearchLoop._maybe_iterate`：最多 2 轮，有成功即停
- `conclusion.iterate_rounds` + journal `ITERATE rN:` note
- 强首轮 / 竞争已成功 → 不迭代

## [S3] Out of Scope

- 遗传算法 / bandit
- 无限预算

## Tasks

- [x] T1: iterate_hypotheses
- [x] T2: _maybe_iterate 接入
- [x] T3: 回归 + 文档
