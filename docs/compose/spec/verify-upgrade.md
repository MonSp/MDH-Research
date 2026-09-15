---
feature: verify-upgrade
status: delivered
updated: 2026-09-15
branch: feat/verify-upgrade
commits: 058c239..HEAD
---

# 验证升级：SymPy 化简 + 场方程残差门禁

## Report

**What was built** — 新增 `verification.py`：`sympy_is_zero`（经 SymPy simplify 证明表达式恒零，绕过 C++ `is_zero` 对完整 GR 失败）；`vacuum_residual_check`（Einstein 张量远场残差，拒绝 NaN/全失败假通过）；`numeric_eval_is_zero`（自由符号未绑定则拒绝 numeric 确认）。`_analyze` 流水线：SymPy → 绑定完整后的 numeric → 真空残差门禁（仅 Schwarzschild/Kerr 工厂；RN/dS 排除）。结论带 `verification` 摘要。

**Verification** — `pytest tests/python/ -q` → **351 passed**（含 19 项 verification 测试）。评审 critical 已修：NaN/evaluate 失败不再假通过；de Sitter 未绑定 L 不再 numeric 确认。

**Journey log**:
1. C++ `is_zero(Schwarzschild R)=False`，SymPy simplify → 0（~0.08s）
2. 评审 C1：`max(0.0, nan)==0` 导致残差假通过 → 显式 `math.isfinite` + 计成功次数
3. 评审 C2：C++ evaluate 将未绑定符号当 0 → 自由符号必须 ⊆ var_map
4. Kerr 为对角近似，残差随 r 衰减；门禁用远场点 + tol=1e-4
5. 真空门禁通过本身不能把「非零 Kretschmann」判为 verified

## [S1] Problem

`ResearchLoop._analyze` 的验证停在「固定采样点数值 ≈ 0」：

- C++ `Expression.is_zero()` 对完整 GR 表达式失败（Schwarzschild 标量曲率 `is_zero=False`，但恒等于 0）
- 未利用已有 `sympy_bridge.expr_to_sympy` + `sp.simplify`（实测 ~0.08s 可证 R≡0）
- 未调用 `field_equations` 对真空解做 Einstein 张量残差门禁（G_μν 应 ≈ 0）
- 结论长期停在 `"Experiments completed (symbolic simplification pending)"`

## [S2] Design

### 新模块 `src/orchestrator/verification.py`

```python
def sympy_is_zero(expr, timeout_s: float = 5.0) -> bool | None:
    """True/False if SymPy can decide; None on timeout/error."""

def vacuum_residual_check(metric, coord_names, params=None,
                          points=None, tol=1e-6) -> dict:
    """Evaluate Einstein tensor G_μν at sample points (outside horizon).
    Returns {passed, max_abs, n_points, samples:[{point, max_abs}]}
    """
```

**采样点默认**（Schwarzschild/Kerr 型）：`(t,r,θ,φ)` 在 `r∈{6,10}·(1+2M)` 量级、`θ=π/2`；仅用 `params` 里的坐标与度量参数。

**残差定义**：真空时 G_μν ≡ 0（等价 Ricci 平坦）。对角 + 非零分量取 `max |G_μν|`。

### `_analyze` 验证流水线（对每个可 evaluate 的 Expression）

```
1. 数值点检（现有）
   - 全部 |val| < tol → CONFIRMED (numeric)
2. 否则 SymPy simplify
   - 为 0 → CONFIRMED (symbolic, sympy)
   - 不为 0 → RESULT (nonzero)
3. 链上若曾 create_*/持有 metric_name 且预测含 vacuum 语义
   → vacuum_residual_check
   - passed → GATE PASS (field equation residual)
   - failed → GATE FAIL + max_abs
```

**vacuum 语义判定**（任一即可）：
- prediction 含 `vacuum` / `Ricci` / `vanish` / `R = 0` / `R=0` / `真空`
- 或链工具含 `create_schwarzschild` / `create_kerr`（已知真空解工厂）

**不做门禁**：`create_reissner_nordstrom`（有电磁源）、纯标量链。

### verdict 分级

| 条件 | verdict |
|------|---------|
| 任一 numeric/symbolic CONFIRMED 或 residual gate passed | `Hypotheses verified` |
| 有成功实验但未证明 | `Experiments completed (symbolic simplification pending)` |
| gate 失败且无其他确认 | `Experiments completed (field-equation residual nonzero)` |
| 全失败 | `All experiments failed` |

### 结果附带

`run()` 返回的 `conclusion` 增加：
```python
"verification": {
  "numeric_confirmed": n,
  "symbolic_confirmed": n,
  "residual_gates": [{"metric_name", "passed", "max_abs"}],
}
```

链成功的 result dict 附 `metric_name`（来自 chain context）供门禁复用。

### 错误行为

- SymPy 超时/解析失败 → `None`，不改变 verdict，evidence 注明 `sympy-skipped`
- MetricStore 无该 metric → 跳过门禁
- 残差计算异常 → gate 记 `passed=False, error=...`，不抛出

### 测试边界

- `sympy_is_zero`：Schwarzschild scalar R → True；`x+1` → False
- `vacuum_residual_check`：Schwarzschild → passed；Minkowski → passed
- `_analyze`：pattern Schwarzschild R 链 → symbolic 或 numeric CONFIRMED + residual gate
- 非真空（RN create）→ 不触发 vacuum gate
- 回归：现有 chain / registry 测试仍绿

## [S3] Out of Scope

- 符号恒等式的交互式证明 / 多项式理想
- 能量条件自动门禁
- 与观测数据对比
- 改 C++ `is_zero` 算法

## Tasks

- [x] T1: verification.py（sympy_is_zero + vacuum_residual_check）— acceptance: 单元测试过 (covers: S2)
- [x] T2: 链结果携带 metric_name + _analyze 流水线 — acceptance: Schwarzschild 链 verdict 为 verified 且含 residual/symbolic 证据 (covers: S2; depends: T1)
- [x] T3: verdict 分级 + verification 摘要 — acceptance: conclusion 含 verification 字段 (covers: S2; depends: T2)
- [x] T4: 回归 + 文档 — acceptance: pytest 全绿；README/AGENTS 提及验证升级 (covers: S2)
