# 大荒界-科研 (MDH-Research)

[![Tests](https://img.shields.io/badge/tests-347%20passed-brightgreen)]()
[![C++17](https://img.shields.io/badge/C%2B%2B-17-blue)]()
[![Python](https://img.shields.io/badge/Python-3.11+-yellow)]()

通过 AI 智能体研究物理世界的数学解释。大荒界生态系统的第四个子项目，聚焦于广义相对论、宇宙学、量子场论的符号与数值计算。

## 核心能力

| 领域 | 能力 | 状态 |
|------|------|------|
| **符号计算** | 表达式树、自动微分、化简、递归下降解析器、数值求值 | ✅ |
| **张量代数** | 升降指标、缩并、张量积、协变导数 | ✅ |
| **微分几何** | Christoffel → Riemann → Ricci → Einstein → Kretschmann | ✅ |
| **黑洞物理** | Schwarzschild/Kerr/RN/dS 生成、视界/奇点分析、Hawking 辐射 | ✅ |
| **引力波** | RW/Zerilli 求解器、QNM 频率、后牛顿近似、双星演化、Fisher/SNR | ✅ |
| **宇宙学** | Friedmann 方程、增长因子、功率谱、暴胀、CMB 各向异性 | ✅ |
| **数值相对论** | ADM 3+1、BSSN 分解、黑洞合并波形 | ✅ |
| **粒子天体** | 引力透镜、中子星 TOV、潮汐形变、能量条件 | ✅ |
| **理论框架** | Tetrads、Newman-Penrose、Killing 矢量、线性化引力 | ✅ |
| **暗能量** | 状态方程、f(R) 修正引力、ΛCDM 参数 | ✅ |

## 快速开始

```bash
# 克隆
git clone --recursive https://github.com/MonSp/MatrixDahuang.git
cd MatrixDahuang/research

# C++ 构建 + 测试
cmake --preset default && cmake --build build
ctest --test-dir build                    # 59 C++ tests

# Python 测试
pip install sympy scipy matplotlib numpy pytest
python3 -m pytest tests/python/ -v       # 245+ Python tests
```

## Python API 示例

```python
import sys; sys.path.insert(0, "build/src/bindings")
import _research_core as rc

# 符号计算
x = rc.parse("x")
expr = x**2 + 2*x + 1  # Pythonic 运算符重载

# 微分几何
m = rc.geometry.Manifold("spacetime", ["t", "r", "theta", "phi"])
g = rc.geometry.Metric.from_diagonal(m, [
    "-(1 - 2*M/r)", "(1 - 2*M/r)^(-1)", "r^2", "r^2 * sin(theta)^2",
])
K = g.kretschmann_scalar()  # Kretschmann 标量
E = g.einstein_tensor()     # Einstein 张量

# 测地线积分
from orchestrator.geodesic import solve_geodesic
import numpy as np
taus, states = solve_geodesic(g, ["t","r","theta","phi"],
    x0=np.array([0, 10, 1.57, 0]),
    u0=np.array([1, 0, 0, 0.03]),
    tau_max=200, params={"M": 1})

# 宇宙学
from orchestrator.cosmology import age_of_universe
print(f"宇宙年龄: {age_of_universe()['age_gyr']:.1f} Gyr")
```

## 物理模块总览

### 广义相对论与黑洞
- **度量工具** — 对角/非角度量构建、Kretschmann 标量、Einstein 张量
- **黑洞解** — Schwarzschild、Kerr、Reissner-Nordström、de Sitter 自动生成
- **视界分析** — 数值 g_tt 符号变化检测、Kretschmann 发散定位
- **Hawking 辐射** — 温度 T_H、蒸发时间、Bekenstein-Hawking 熵、Unruh 效应
- **因果结构** — 光锥分析、类时/类光/类空分类

### 引力波与致密天体
- **准正规模** — Schwarzschild/Kerr QNM 频率（Leaver 数值表）、波形生成
- **RW/Zerilli** — 微扰方程 RK45 求解、引力波应变 h₊/h×
- **双星演化** — chirp mass、轨道衰减、merger time
- **GW 数据分析** — Fisher 矩阵、匹配滤波 SNR、探测距离
- **后牛顿近似** — 1PN/2PN 能量、近日点进动、GW 四极矩通量
- **中子星** — TOV 方程（BDF 求解器）、质量-半径关系、SLy4 EOS、潮汐形变度

### 宇宙学
- **FLRW** — Friedmann 方程数值求解、宇宙年龄、角直径/光度距离
- **微扰理论** — 增长因子 D(a)、BBKS 传递函数、物质功率谱、BAO 标度
- **暴胀** — 慢滚参数 ε/η、n_s、r、原初标量/张量功率谱
- **CMB 各向异性** — 角功率谱 C_ℓ、声峰位置、Silk 阻尼
- **暗能量** — w(z) 状态方程、ΛCDM、f(R) 修正引力、CPL 参数化

### 数值相对论
- **ADM 3+1** — lapse/shift、空间度量、外曲率、哈密顿/动量约束
- **BSSN** — 共形因子 φ、共形度量 γ̃_ij、联络函数 Γ̃^i
- **黑洞合并** — 准正弦铃荡波形、chirp 信号、能量辐射

### 理论框架
- **Tetrads/Vielbein** — 正交标架、自旋联络、标架↔度量转换
- **Newman-Penrose** — 零标架、Weyl 标量 Ψ₀...Ψ₄、Petrov 分类（O/I/II/D/III/N）
- **Killing 矢量** — 自动检测、stationary/static/axisymmetric 分类
- **线性化引力** — 微扰 Riemann/Ricci、TT 规范引力波
- **能量条件** — WEC/SEC/DEC/NEC 符号+数值验证

## 基准测试

| 度量 | 验证内容 | 结果 |
|------|----------|------|
| Schwarzschild | Christoffel + Ricci=0 + K=48M²/r⁶ | ✓ SymPy |
| FLRW (k=0) | Christoffel + R=6(ä/a+H²) | ✓ |
| Kerr | 结构 + 数值 Ricci=0 + 视界 | ✓ |
| Minkowski | Γ=0, R=0, K=0 | ✓ |
| de Sitter | R=4Λ | ✓ |
| Reissner-Nordström | 非零 Ricci（电磁源） | ✓ |
| S² / H² | R=±2 | ✓ |

## 技术栈

- **C++17** — 符号计算核心（表达式树、张量运算、微分几何）
- **pybind11** — Python ↔ C++ 绑定（运算符重载、数值求值、clone）
- **Python 3.11+** — Agent 编排、SymPy/SciPy/NumPy/Matplotlib
- **CMake 3.16+** — 构建系统（presets 支持）
- **Catch2 v3** — C++ 测试框架（FetchContent）
- **pytest** — Python 测试框架

## 项目结构

```
research/
├── src/
│   ├── core/
│   │   ├── symbol/        # 符号引擎 (expression, parser)
│   │   ├── tensor/        # 张量计算 (tensor, operations)
│   │   └── geometry/      # 几何核心 (manifold, metric, curvature)
│   ├── bindings/          # pybind11 Python 绑定
│   └── orchestrator/      # 23 个 Python 物理/天文模块
│       ├── geodesic.py        # 测地线 ODE 求解器
│       ├── killing.py         # Killing 矢量场检测
│       ├── perturbation.py    # 线性化引力 + 引力波
│       ├── perturbation_eqns.py # RW/Zerilli 求解器
│       ├── blackholes.py      # 黑洞解工厂
│       ├── hawking.py         # Hawking 辐射
│       ├── quasinormal.py     # 准正规模
│       ├── binary.py          # 双星演化
│       ├── gw_analysis.py     # GW 数据分析
│       ├── post_newtonian.py  # 后牛顿近似
│       ├── lensing.py         # 引力透镜
│       ├── neutron_star.py    # 中子星 TOV
│       ├── inflation.py       # 宇宙暴胀
│       ├── cosmology.py       # FLRW 宇宙学
│       ├── cosmo_perturbation.py # 宇宙学微扰
│       ├── cmb.py             # CMB 各向异性
│       ├── dark_energy.py     # 暗能量模型
│       ├── numerical_relativity.py # 数值相对论
│       ├── tetrad.py          # Tetrads/Vielbein
│       ├── newman_penrose.py  # Newman-Penrose
│       ├── adm.py             # ADM 3+1 分解
│       ├── bssn.py            # BSSN 分解
│       ├── causal.py          # 因果结构
│       ├── energy_conditions.py # 能量条件
│       ├── field_equations.py # 场方程
│       ├── sympy_bridge.py    # SymPy 双向转换
│       ├── journal.py         # 研究日志 (append-only)
│       ├── research_loop.py   # 研究闭环 (假设→实验→分析→结论)
│       ├── kernel_bridge.py   # agent-kernel IPC 桥接
│       ├── session.py         # Agent 编排层
│       └── visualization.py   # 3D 可视化
├── config/
│   └── research-skill-mapping.json  # 20 个 skill → 修仙能力映射
├── skills/
│   ├── research-compute/SKILL.md    # 计算核心 skill
│   ├── research-analyze/SKILL.md    # 分析分类 skill
│   ├── research-experiment/SKILL.md # 实验执行 skill
│   └── research-report/SKILL.md     # 报告生成 skill
├── tests/
│   ├── cpp/               # 59 Catch2 C++ 测试
│   └── python/            # 288+ pytest Python 测试
├── CMakeLists.txt
├── CMakePresets.json
└── pyproject.toml
```

## Agent-Kernel 集成

四层架构连接研究智能体与 agent-kernel ECS：

```
┌─────────────────────────────────────┐
│  ResearchLoop (研究闭环)              │
│  假设 → 实验 → 分析 → 结论           │
├─────────────────────────────────────┤
│  ResearchJournal (研究日志)           │
│  append-only, harness 可观测         │
├─────────────────────────────────────┤
│  Skill Manifests (技能定义)           │
│  20 个 skill → 修仙能力映射           │
├─────────────────────────────────────┤
│  AgentKernelBridge (IPC 桥接)        │
│  Unix socket, JSON-RPC              │
└─────────────────────────────────────┘
         ↕ agent-kernel (ECS)
```

- **4 个 skill 类别**: compute / analyze / experiment / report
- **27 个研究 skill** 映射到修仙能力 (炼算/参悟/推演/观象)
- **研究日志**: 每次假设/实验/结论/工具调用都记录为结构化 event
- **研究闭环**: `ResearchLoop.run("question")` 自动分解→执行→记录
- **80+ agent tools**: `tool_registry.py` 统一注册，ResearchLoop / LLM schema / GeometrySession 共用
- **顺序链执行**: LLM 可返回 `tools: [t1, t2, ...]`；工厂 `metric_name` 自动注入后续 consumer

## Agent 工具面

`src/orchestrator/tool_registry.py` 是 agent 可调用物理工具的唯一注册表（与 `config/research-skill-mapping.json` 对齐）：

- **MetricStore**（`metric_store.py`）命名交接活体 C++ Metric；工厂 `create_*` 写入 store，消费者收 `metric_name` 或 `diagonal`+`coords`
- **ResearchLoop** 使用 registry handler 表与 `openai_tools_payload()` 动态 LLM schema
- **GeometrySession.define_metric** 同步注册到 MetricStore
- **顺序链**：hypothesis 可含 `tools` 数组；执行器串行调用并把上一步 `metric_name` 注入下一步

```python
from orchestrator.research_loop import ResearchLoop
loop = ResearchLoop()
# pattern 路径自动走链：create_schwarzschild → compute_scalar_curvature
loop.run("What is the scalar curvature of Schwarzschild spacetime?")

from orchestrator.tool_registry import execute_tool, registry_summary
print(registry_summary()["count"])  # 80
execute_tool("create_schwarzschild", {"M": 1})
execute_tool("compute_scalar_curvature", {"metric_name": "schwarzschild"})
```

## 与大荒界生态的关系

独立 git 子模块，与 company、game、kernel 平级。研究成果可反馈到：
- **company** — 研究助手 skill pack、数值计算工具
- **game** — 物理模拟引擎、引力波信号生成
- **kernel** — 共享 ECS 智能体架构
