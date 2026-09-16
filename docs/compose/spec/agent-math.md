---
feature: agent-math
status: delivered
updated: 2026-09-16
branch: feat/agent-math
commits: 5c0ec4c..HEAD
---

# L5 智能体数学基础（MVP）

## Report

**What was built** — `agent_math.py`：Shannon 熵、工具序列 trajectory metrics、decision pressure、MetricStore 状态 L2 距离、sweep 信息量（spread bits / certainty / 幂律可检验）。`_analyze` 在 `conclusion.foundations` 附带 run 级过程指标。registry 新增 4 个 `agent_foundations` tool。

**Verification** — `pytest tests/python/ -q` → **407 passed**（含 14 项 agent_math 测试）。

**Journey log**:
1. L5 刻意做成**编排过程诊断**，不宣称「智能/意识」
2. `foundations` 与 `verification` 并列：前者测 loop，后者测物理
3. 首版独立评审结果与实现不符（幻觉出无关领域公式），以本地测试与代码为准

## [S1] Problem

能力分层里 L5「智能体数学基础」长期为 ❌。需要一个**诚实、可测**的 MVP：度量研究闭环本身的过程，而不是宣称 agent 有意识或能发现新物理。

## [S2] Design

### `src/orchestrator/agent_math.py`

| 函数 | 含义 |
|------|------|
| `shannon_entropy(counts)` | 离散分布 Shannon 熵（bit） |
| `trajectory_metrics(tool_seq, n_success, n_fail, n_replans)` | 工具序列熵、多样性、成功率、repair load |
| `decision_pressure(n_available, n_used)` | log2(可用工具) − log2(实际用到) |
| `state_distance(s1, s2)` | MetricStore 指纹 L2 距离 |
| `sweep_information(trend)` | y 动态范围 bits、trend certainty、幂律可检验性 |
| `summarize_run(results, n_registry_tools)` | 一次 `run()` 的聚合 foundations |

**定位**：编排质量诊断，不是世界物理、不是「智能证明」。

### ResearchLoop

`_analyze` 返回增加 `foundations: summarize_run(results, n_registry_tools=...)`。

### Registry

新增 4 个 tool（category `agent_foundations`）：
`trajectory_metrics`, `shannon_entropy_bits`, `state_distance`, `sweep_information`。

### 测试边界

- 熵：均匀 / 确定 / dict
- trajectory / decision_pressure
- state_distance 相同、参数差、缺 metric
- sweep_information 1/M 与空 trend
- loop conclusion 含 foundations；registry 可调

## [S3] Out of Scope

- 变分推理 / 信息几何完整流形
- 跨 session 经验学习
- 「agent 物理」本体论

## Tasks

- [x] T1: agent_math.py — acceptance: 单元测试过 (covers: S2)
- [x] T2: ResearchLoop.foundations + registry tools — acceptance: conclusion 含 foundations (covers: S2; depends: T1)
- [x] T3: 回归 + 文档 — acceptance: pytest 全绿；README/AGENTS L5 MVP (covers: S2)
