---
feature: mvp-symbolic-geometry
status: delivered
updated: 2026-01-27
branch: main
commits: bcc64a9
---

# MVP: 符号计算引擎与基础微分几何

## Report

**What was built** — C++17 符号计算引擎（表达式树 + 自动微分 + 化简）+ 张量计算模块（指标操作、缩并、张量积）+ 微分几何核心（流形、度量、Christoffel 符号、Riemann/Ricci 张量、标量曲率）。pybind11 绑定层将 C++ 核心暴露为 Python 模块。Agent 编排层提供 OpenAI function calling 兼容的工具接口，支持有状态的几何计算会话。

**Verification** — 28 Catch2 C++ 测试（符号 14 + 张量 7 + 几何 7），16 pytest Python 测试（绑定 5 + 编排 9 + SymPy 基准 2），全部通过。Schwarzschild 度量的 Christoffel 符号和 Ricci 张量 = 0 与 SymPy 解析解完全一致。

**Journey log**:
1. 表达式头文件的工厂函数顺序问题导致编译失败 → 前置声明 + 后置定义解决
2. Christoffel 符号的 tensor index 标签硬编码4D → `safe_coord` lambda 修复任意维度
3. pybind11 绑定中 `research_core.h` 的前向声明与完整定义冲突 → 移除该头文件，直接包含实际头文件

## [S1] 问题

大荒界-科研需要一个符号计算基础设施，使 LLM 驱动的智能体能够：
1. 表示和操作微分几何对象（流形、度量、联络、曲率张量）
2. 从度量张量自动推导 Christoffel 符号、Riemann 曲率张量、Ricci 张量、标量曲率
3. 验证计算结果的正确性（与已知解析解对比）

首个验证目标：Schwarzschild 度量的完整曲率计算管线。

## [S2] 设计

### 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Layer (Python)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ 自主发现引擎  │  │  研究助手     │  │ 智能体数学基础     │  │
│  │ (Discovery)  │  │ (Assistant)  │  │ (Foundations)     │  │
│  └──────┬───────┘  └──────┬───────┘  └───────┬───────────┘  │
│         │                 │                   │              │
│         └─────────────────┼───────────────────┘              │
│                           │                                  │
│                    ┌──────▼──────┐                           │
│                    │  Orchestrator│  ← LLM 驱动的推导编排     │
│                    │  (Python)   │                           │
│                    └──────┬──────┘                           │
└───────────────────────────┼──────────────────────────────────┘
                            │ IPC / pybind11
┌───────────────────────────┼──────────────────────────────────┐
│                    Computation Layer (C++)                    │
│  ┌──────────────┐  ┌──────▼──────┐  ┌───────────────────┐   │
│  │ Symbol Engine │  │ Tensor Calc │  │ Geometry Core     │   │
│  │ (符号引擎)    │  │ (张量计算)   │  │ (几何核心)        │   │
│  └──────────────┘  └─────────────┘  └───────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 模块划分

#### 1. C++ 计算核心 (`core/`)

**符号引擎 (Symbol Engine)**
- 表达式树：节点类型包括 Number, Symbol, Add, Mul, Pow, Func, Tensor, Index
- 自动微分：对符号表达式求偏导和协变导数
- 化简规则：结合律、交换律展开、三角恒等式、张量对称性

**张量计算 (Tensor Calculator)**
- 张量表示：阶数(rank)、分量数组、指标类型(上标/下标)、对称性元数据
- 指标操作：升降指标(metric contraction)、缩并(contraction)、外积(tensor product)
- 协变导数：基于联络的协变偏导数
- 曲率计算：Christoffel 符号 → Riemann → Ricci → 标量曲率 全链路

**几何核心 (Geometry Core)**
- 流形：坐标系定义、坐标变换
- 度量：度量张量定义及其逆
- 联络：Levi-Civita 联络的自动计算
- 测地线方程：从联络推导测地线 ODE

#### 2. Python 绑定层 (`bindings/`)

- pybind11 封装 C++ 核心，暴露 Pythonic API
- 类型映射：C++ Expression → Python SymbolicExpr，C++ Tensor → Python TensorField
- 内存管理：shared_ptr 语义，避免循环引用

#### 3. Agent 编排层 (`agents/`)

**Orchestrator**
- LLM 驱动的任务分解：将"计算 Schwarzschild 度量的曲率"分解为定义度量、计算联络、计算曲率等子步骤
- 工具调用：智能体通过 function calling 调用符号计算引擎
- 结果验证：自动对比已知解析解，报告偏差

**三个功能模块**（MVP 阶段共享编排层，后续独立扩展）：
- `discovery/` — 自主发现引擎接口
- `assistant/` — 研究助手接口
- `foundations/` — 智能体数学基础接口

#### 4. 基准测试 (`benchmarks/`)

- Schwarzschild 度量：已知 Christoffel 符号和 Ricci 张量的解析解
- Friedmann-Lemaître-Robertson-Walker (FLRW) 度量：宇宙学标准模型
- Kerr 度量：旋转黑洞（进阶验证）

### 数据流

```
1. 用户/智能体 提出问题: "计算 Schwarzschild 度量的曲率"
2. Orchestrator (LLM) 解析意图，生成工具调用序列:
   a. define_metric("schwarzschild", coords=[t,r,θ,φ], g=diag(...))
   b. compute_christoffel("schwarzschild")
   c. compute_riemann("schwarzschild")
   d. compute_ricci("schwarzschild")
   e. compute_scalar_curvature("schwarzschild")
3. 每一步调用 C++ 核心执行符号计算
4. 结果返回 Orchestrator，格式化为 LaTeX + 物理解释
5. 验证模块对比已知结果，报告 PASS/FAIL
```

### 接口契约

**Python API**:
```python
from research_core import Manifold, Metric, SymbolicEngine

# 定义 4D 流形
m = Manifold(name="spacetime", coords=["t", "r", "theta", "phi"])

# 定义 Schwarzschild 度量
g = Metric(m, components=[
    [-(1 - 2*M/r), 0, 0, 0],
    [0, 1/(1 - 2*M/r), 0, 0],
    [0, 0, r**2, 0],
    [0, 0, 0, r**2 * sin(theta)**2]
])

# 计算链路
Gamma = g.christoffel()       # Christoffel 符号 (3阶张量)
R = g.riemann()               # Riemann 曲率张量 (4阶张量)
Ric = g.ricci()               # Ricci 张量 (2阶张量)
S = g.scalar_curvature()      # 标量曲率 (0阶张量 = 标量)

# LaTeX 输出
print(Gamma.to_latex())       # \Gamma^{\mu}_{\nu\rho} = ...
```

**C++ API**:
```cpp
#include "research_core/symbol.h"
#include "research_core/tensor.h"
#include "research_core/geometry.h"

using namespace rc;

auto expr = SymbolicEngine();
auto coords = expr.define_coords({"t", "r", "theta", "phi"});

// 定义度量分量
auto M = expr.symbol("M");
auto r = coords[1];
auto g = Metric(coords, {
    {-(1 - 2*M/r), 0, 0, 0},
    {0, 1/(1 - 2*M/r), 0, 0},
    {0, 0, r*r, 0},
    {0, 0, 0, r*r * pow(sin(coords[2]), 2)}
});

auto Gamma = g.christoffel_symbols();
auto Riemann = g.riemann_tensor();
auto Ricci = g.ricci_tensor();
auto Scalar = g.scalar_curvature();
```

### 错误行为

- 未定义的符号/坐标：抛出 `UndefinedSymbolError`
- 维度不匹配的张量运算：抛出 `TensorDimensionError`
- 计算超时（表达式过于复杂）：抛出 `ComputationTimeoutError`，默认 30s
- 度量矩阵奇异（行列式为零）：抛出 `SingularMetricError`

### 测试边界

- Python 测试：pytest，覆盖 API 完整链路 + 与已知解析解对比
- C++ 测试：Catch2，覆盖符号引擎 + 张量计算 + 几何核心
- 集成测试：LLM → Orchestrator → C++ 全链路（mock LLM 调用）
- 不测试：LLM 的推理质量（那是模型能力，不是代码正确性）

## [S3] 不在范围内

- 数值 PDE 求解器（未来里程碑）
- 可视化/图形渲染
- 与 company/game 的直接集成
- 量子场论计算
- 自动论文生成
- GPU 加速（初始版本纯 CPU）

## Tasks

- [x] T1: 初始化项目结构 — acceptance: `cmake --build` 和 `pytest` 均可执行空测试 (covers: S2)
- [x] T2: C++ 符号引擎核心 — acceptance: 能创建符号表达式、求偏导、化简，Catch2 测试全过 (covers: S2.1; depends: T1)
- [x] T3: C++ 张量计算模块 — acceptance: 能定义张量、升降指标、缩并，Catch2 测试全过 (covers: S2.2; depends: T2)
- [x] T4: C++ 几何核心 — acceptance: 从度量自动计算 Christoffel 符号、Riemann、Ricci、标量曲率，Catch2 测试全过 (covers: S2.3; depends: T3)
- [x] T5: pybind11 绑定层 — acceptance: Python 能调用 C++ 全链路 API，pytest 测试全过 (covers: S2.4; depends: T4)
- [x] T6: Schwarzschild 基准测试（C++ 绑定版） — acceptance: 计算结果与已知解析解完全一致（符号等价），pytest 测试全过 (covers: S2.6; depends: T5)
- [x] T7: Agent 编排层基础 — acceptance: 能通过 function calling 接口驱动符号计算引擎，mock LLM 测试全过 (covers: S2.5; depends: T5)
- [x] T8: AGENTS.md 和项目文档 — acceptance: 新开发者能按文档从零构建和运行测试 (covers: S2; depends: T1)
