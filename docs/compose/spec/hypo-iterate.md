---
feature: hypo-iterate
status: in-progress
updated: 2026-09-17
branch: feat/hypo-iterate
commits:  # filled at delivery
---

# L7 多轮迭代搜索

## Report

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

- [ ] T1: iterate_hypotheses
- [ ] T2: _maybe_iterate 接入
- [ ] T3: 回归 + 文档
