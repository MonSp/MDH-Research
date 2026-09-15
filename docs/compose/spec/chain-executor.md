---
feature: chain-executor
status: delivered
updated: 2026-09-15
branch: feat/chain-executor
commits: 8b6e44f..49e56a1
---

# ResearchLoop 顺序链执行器

## Report

**What was built** — ResearchLoop 支持顺序 tool 链：hypothesis 可用 `tools` 数组（dict 或字符串简写），`_execute_chain` 串行执行；工厂 `create_*` 返回的 `metric_name` 自动注入后续 `needs_metric` 步骤；缺 metric 显式失败；中途异常保留 `partial_steps`。LLM prompt 引导多步返回；`_analyze` 扫描链上各步结果。附带 74 题 LLM 选 tool 评测（链式准确率 ~99%）作为设计依据。

**Verification** — `pytest tests/python/ -q` → **332 passed**（含 21 项 chain 测试）。Live LLM e2e（deepseek-v4-flash）：Kerr R=0 问题返回 `create_kerr → compute_scalar_curvature`，`metric_name=kerr` 自动注入，journal 含 2× tool_call。

**Journey log**:
1. 评审 critical：Hawking 蒸发 pattern 链缺 `M`（schema default 不会被执行器应用）→ 补显式 params + 回归测试
2. `llm_client=False` 必须显式传入，否则 env 里的 LLM_API_KEY 会劫持 pattern 测试
3. `"symmetry" in "symmetries"` 为 False；用 `"killing"` 兜底
4. monorepo 误建 worktree → 改到 research 子仓库

## [S1] Problem

LLM tool-selection 评测（74 题，deepseek-v4-flash）显示：模型 **已能** 给出正确的多步 tool 链（`create_kerr` → `compute_scalar_curvature` 等，5/5 顺序全对），链式准确率 ~99%。但 `ResearchLoop` 仍把每个 hypothesis 当成 **单次** tool 调用：

- LLM 返回的 `tools: [t1, t2]` 被丢弃或只取第一个
- 工厂产出的 `metric_name` 不会自动注入后续 consumer
- 多步问题需要用户手工拆成多次 `run()`

评测报告：`data/evals/tool_selection_report.md`。

## [S2] Design

### Hypothesis 形态（兼容旧格式）

```json
// 旧：单步
{"tool": "hawking_temperature", "params": {"M": 1.989e30}, "prediction": "..."}

// 新：显式链
{
  "prediction": "Kerr 为真空解，R=0",
  "tools": [
    {"tool": "create_kerr", "params": {"M": 1, "a": 0.7}},
    {"tool": "compute_scalar_curvature", "params": {}}
  ]
}

// 新：简写（无 params，靠 metric_name 注入）
{"tools": ["create_schwarzschild", "classify_symmetry"], "prediction": "..."}
```

`_normalize_hypothesis(h) -> list[Step]` 统一为步骤列表；旧 `tool`/`params` 变成单元素链。

### 执行语义

```
context = {}  # 跨步骤共享
for step in steps:
    params = merge(step.params, inject_from(context, step.tool))
    result = execute(step.tool, params)
    if isinstance(result, dict) and "metric_name" in result:
        context["metric_name"] = result["metric_name"]
    journal.log_tool_call(...)  # 已有
```

**注入规则**（仅当参数缺失时）：
1. ToolSpec.`needs_metric` 且 params 无 `metric_name` → 注入 `context["metric_name"]`
2. 若 context 无 metric 且 step 需要 metric → 该步失败并 journal error（不静默用 flat 默认）

**不注入**：纯标量 tool（hawking_temperature 等）。

### ResearchLoop 变更

| 位置 | 变更 |
|------|------|
| `_hypothesize_llm` system prompt | 明确：多步问题返回 `tools` 数组（执行顺序）；metric 消费者可省略 metric_name，执行器会串联 |
| `_hypothesize_patterns` | 单步假设仍用 `tool`+`params`（兼容） |
| `_execute` | 改为 `_execute_chain(steps)`；返回逐步结果列表 |
| `_analyze` | 对链：检查最后一步结果；若任一步 `evaluate≈0` 也算 evidence |
| `run()` | hypothesis 可含 `steps`；journal 仍 log 一次 experiment（tool=链摘要或第一步） |

### 数据结构

```python
@dataclass
class ChainStep:
    tool: str
    params: dict

def _steps_from_hypothesis(h: dict) -> list[ChainStep]
```

`run()` 返回的 `results[i]`：
```python
{
  "hypothesis": ...,
  "steps": [{"tool": ..., "params": ..., "result": ...}, ...],
  "result": <last step result>,  # 兼容旧 _analyze
  "success": bool,
}
```

### 错误行为

- 链中途异常：记录已完成步，`success=False`，不再继续后续步
- 未知 tool：整条链失败（与现状一致）
- LLM 返回空 `tools`：回落 pattern

### 测试边界

- 单元：`_steps_from_hypothesis` 三种形态
- 单元：metric_name 自动注入（create → classify_symmetry）
- 单元：纯标量链不注入
- 单元：中途失败停止且 journal 含 error
- 集成：mock LLM 返回 `tools` 链，ResearchLoop 跑通并 produce R≈0
- 回归：现有 pattern 单步测试仍绿

## [S3] Out of Scope

- 参数 NL 填充（M/r 从句子里抽）
- 备选 tool / 失败重规划
- 并行步骤、DAG
- 验证升级（SymPy / 残差门禁）
- 全量 OpenAI tool-calling API 格式

## Tasks

- [x] T1: ChainStep + _steps_from_hypothesis — acceptance: 旧 tool 字段与新 tools 数组/简写均可归一 (covers: S2)
- [x] T2: _execute_chain + metric_name 注入 — acceptance: create→consumer 测试过；缺 metric 时明确失败 (covers: S2)
- [x] T3: LLM prompt + _analyze 链感知 — acceptance: mock LLM 链路径端到端测试过 (covers: S2; depends: T1, T2)
- [x] T4: 回归 + 文档 — acceptance: pytest 全绿；README/AGENTS 提及链执行 (covers: S2)
