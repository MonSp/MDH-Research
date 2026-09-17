---
feature: known-value-gate
status: delivered
updated: 2026-09-17
branch: feat/known-value-gate
commits: 53a27d8..47505d5
---

# L8 已知物理量一致性门禁

## Report

**What was built** — `known_values.py` 对照教科书关系（Hawking T、宇宙年龄、chirp mass、Schwarzschild QNM）；`conclusion.known_value_checks` + evidence。

**Verification** — `pytest tests/python/ -q` → **444 passed**。

## [S1] Problem

验证只做恒零/残差；缺少与教科书关系的对照（Hawking T∝1/M、宇宙年龄、chirp mass 公式、Schwarzschild QNM）。

## [S2] Design

`known_values.py` 目录化检查：
- `hawking_temperature` vs 6.17e-8·(M☉/M) K（25% 容差）
- `age_of_universe` ∈ [12, 15] Gyr
- `chirp_mass` vs (m1 m2)^{3/5}/(m1+m2)^{1/5}
- `schwarzschild_qnm` vs ω≈0.3737−0.0890i (M=1,l=2,n=0)

`_analyze` → `conclusion.known_value_checks` + evidence `KNOWN-VALUE PASS/FAIL`。

## [S3] Out of Scope

- 完整观测数据表 / Planck 参数拟合
- 自动单位换算

## Tasks

- [x] T1: known_values.py
- [x] T2: _analyze 接入
- [x] T3: 回归 + 文档
