---
feature: param-sweep
status: delivered
updated: 2026-09-16
branch: feat/param-sweep
commits: feefb29..dac0f5c
---

# 参数扫描实验：LLM 多组参数假设搜索 + 趋势汇总

## Report

**What was built** — hypothesis 可带 `sweep`：单 tool 或链式 `inject` 轴值；`param_sweep.expand_axis` / `extract_numeric`（Expression 在参考点 evaluate，合并 metric 参数）/ `summarize_trend`（方向、Spearman、log-log 斜率）。`_run_sweep_hypothesis` 逐点执行、单点失败不中断；`_analyze` 追加 `SWEEP:` 趋势句。LLM 校验接受 sweep-only 假设。

**Verification** — `pytest tests/python/ -q` → **377 passed**（含 26 项 param_sweep 测试）。Hawking T vs M：decreasing，log-log slope≈-1。链式 Kretschmann Expression extract 递增。评审 critical 已修。

**Journey log**:
1. C1 Expression `float(to_string())` 失败 → `evaluate({**DEFAULT_EVAL_POINT, **params})`
2. C2 `_hypothesize_llm` 仍要求 top-level tool/tools → sweep-only 分支放行
3. MetricStore 同名覆盖：链扫描各点写同一 `schwarzschild` 名，Expression 仍随新 metric 计算
4. eval_point 只含 M 时 r 默认 0 → K 发散；改为与 DEFAULT 合并

## [S1] Problem

链执行器一次只跑一组参数。物理问题常需「扫 M 看 T_H 如何变」「扫 a 看 QNM」——当前要用户手工多次 `run()`，无法由 LLM 一次编排多组参数并给出趋势结论。

评测与链执行已证明：tool 选择与顺序编排可靠；缺的是 **参数轴展开 + 结果表 + 趋势摘要**。

## [S2] Design

### Hypothesis 形态（兼容既有 tool/tools）

```json
{
  "prediction": "Hawking temperature decreases as 1/M",
  "assumptions": ["Schwarzschild BH"],
  "sweep": {
    "tool": "hawking_temperature",
    "params": {},
    "axis": {"name": "M", "values": [1e30, 1e31, 1e32]},
    "extract": "T_K"
  }
}
```

链式扫描（把轴值注入链中某步）：

```json
{
  "prediction": "K stays nonzero for Schwarzschild as M varies",
  "tools": [
    {"tool": "create_schwarzschild", "params": {"M": 1}},
    {"tool": "compute_kretschmann", "params": {}}
  ],
  "sweep": {
    "axis": {"name": "M", "start": 1, "stop": 4, "n": 4},
    "inject": {"tool": "create_schwarzschild", "param": "M"},
    "extract": null
  }
}
```

**axis**（二选一）：
- `values`: 显式列表  
- `start`/`stop`/`n`: 线性（`log: true` 时对数）

**extract**：
- 字典 key（如 `T_K`, `age_gyr`, `omega_R`）
- `null`/缺省：标量直接用；Expression 在参考点求值；dict 无 key 时取第一个有限 float

**inject**：链扫描时指定 `{tool, param}`，把 axis 值写入该步 params。

### 模块 `src/orchestrator/param_sweep.py`

```python
def expand_axis(axis: dict) -> list[float]
def extract_numeric(result, key: str | None) -> float | None
def summarize_trend(xs, ys) -> dict
    # {n, y_min, y_max, direction: increasing|decreasing|non-monotonic|flat,
    #  spearman_rho, log_log_slope, y_ratio}
def substitute_params(params: dict, name: str, value: float) -> dict
```

趋势规则：
- `flat`: 所有 |Δy| < 1e-12 * max(|y|,1)
- `increasing` / `decreasing`: 相邻差分符号一致（允许 eps）
- 否则 `non-monotonic`
- `log_log_slope`: 对 x>0,y>0 用 log-log 最小二乘
- `y_ratio`: y[-1]/y[0]（y0≠0）

### ResearchLoop

1. `_steps_from_hypothesis` 不变；`run()` 检测 `hyp["sweep"]`
2. `_execute_sweep(hyp)`：
   - 展开 axis（默认最多 **12** 点，防爆）
   - 每点：替换 params / inject → `_execute_chain` 或 `_call_tool`
   - 收集 `{x, y, error?}`，单点失败不中断
3. 成功结果：`results[i]["sweep"] = {axis_name, points, trend}`
4. `_analyze`：有 sweep 时 evidence 追加趋势摘要句；verdict 仍走验证流水线（链 Expression）
5. LLM prompt 增加 sweep 语法与 2 个例子（Hawking T vs M；链式 M vs 无关量）
6. journal：experiment tool 记 `sweep:<tool>`；observation 含 points 表

### 错误行为

- axis 非法 / 空 → 假设失败
- extract 全失败 → sweep success=False
- n>12 → 截断到 12 并在 trend 里标 `truncated`

### 测试边界

- expand_axis values / linear / log
- extract_numeric float / dict key / Expression / 无 key
- summarize_trend 1/M 递减、递增、非单调
- ResearchLoop pattern：Hawking T vs M 三点递减
- 链式 sweep inject M
- 回归：现有 chain/verify 测试仍绿

## [S3] Out of Scope

- 二维参数网格
- 贝叶斯优化 / 自适应采样
- 并行执行
- 绘图（visualization 后续 report skill）

## Tasks

- [x] T1: param_sweep.py（expand/extract/summarize/substitute）— acceptance: 单元测试过 (covers: S2)
- [x] T2: ResearchLoop._run_sweep_hypothesis + 结果/analysis 接入 — acceptance: pattern Hawking 扫描递减趋势 (covers: S2; depends: T1)
- [x] T3: LLM prompt sweep 语法 — acceptance: 文档化格式，validator 接受 sweep-only (covers: S2; depends: T2)
- [x] T4: 回归 + 文档 — acceptance: pytest 全绿；README/AGENTS 提及参数扫描 (covers: S2)
