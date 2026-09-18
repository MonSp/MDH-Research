---
feature: hypothesis-memory
status: in-progress
updated: 2026-09-18
branch: feat/hypothesis-memory
commits:  # filled at delivery
---

# L14 假设记忆（跨战役复用）

## Report

## [S1] Problem

成功假设不跨 run 复用；每次从 pattern/LLM 重新猜。

## [S2] Design

`hypothesis_memory.py`：
- `remember_from_run` / `recall_hypotheses` / `inject_memory_candidates`
- 关键词重叠召回；score ≥ 2.0 且成功的 tool 链可记
- ResearchLoop `memory_path` **显式字符串才启用**（防测试污染）
- CLI `memory summary|list|recall|inject`

## [S3] Out of Scope

- 向量检索 / embedding
- 跨进程锁

## Tasks

- [ ] T1: hypothesis_memory.py
- [ ] T2: ResearchLoop + CLI
- [ ] T3: 回归 + 文档
