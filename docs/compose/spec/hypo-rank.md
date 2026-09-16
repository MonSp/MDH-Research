---
feature: hypo-rank
status: delivered
updated: 2026-09-16
branch: feat/hypo-rank
commits: 626e61c..4e3b379
---

# L5 完善：假设排序 + Journal 固化 foundations

## Report

**What was built** — `score_hypothesis` / `rank_hypotheses`（成功、可 evaluate 步、sweep certainty、replan 惩罚）；`conclusion.hypothesis_ranking` + `best_hypothesis`；`log_conclusion(extra=...)` 把 foundations/ranking 写入 journal；registry 增加 `rank_hypotheses`。

**Verification** — `pytest tests/python/ -q` → **416 passed**（含 9 项 hypo_rank 测试）。

## [S1] Problem

L5 MVP 只有 run 级 foundations；多假设并存时没有择优，journal conclusion 也不含 L5 载荷。

## [S2] Design

见 `agent_math.score_hypothesis`（2.0 success + eval 步 + certainty − 0.5 replan）与 `ResearchLoop._analyze` / `log_conclusion(extra=)`。

## [S3] Out of Scope

- LLM 重生成竞争假设
- 贝叶斯后验

## Tasks

- [x] T1: score/rank — acceptance: 单元测试过
- [x] T2: conclusion + journal extra — acceptance: ranking 字段与 journal L5 载荷
- [x] T3: 回归 + 文档
