# 大荒界-科研 (MDH-Research)

通过 AI 智能体研究物理世界的数学解释。

## 三大模块

| 模块 | 目标 | 状态 |
|------|------|------|
| 自主发现引擎 | 智能体自主进行假设-实验-验证循环 | 规划中 |
| 研究助手 | 为人类研究者提供智能体工具链 | 规划中 |
| 智能体数学基础 | 探索 AI 智能体本身的物理/数学本质 | 规划中 |

## 首个研究领域: 微分几何与引力理论

### 已完成

- **符号计算引擎** — 表达式树、自动微分、化简、递归下降解析器、数值求值
- **张量计算** — 指标操作、缩并、张量积
- **微分几何** — 流形、度量、Christoffel 符号 → Riemann → Ricci → 标量曲率
- **测地线求解器** — RK4 数值积分、数值 Christoffel 计算
- **Python 绑定** — pybind11 暴露完整 API (运算符重载、数值求值)
- **Agent 编排层** — OpenAI function calling 兼容的工具接口

### 基准测试

| 度量 | 验证内容 | 结果 |
|------|----------|------|
| Schwarzschild | Christoffel 符号 + Ricci = 0 | ✓ 与 SymPy 解析解一致 |
| FLRW (k=0) | Christoffel + Ricci + 标量曲率 R=6(ä/a+H²) | ✓ |
| Kerr | 结构验证 + 数值 Ricci = 0 + 事件视界 | ✓ |
| Minkowski | 平坦时空, Γ=0, R=0 | ✓ |
| de Sitter | 正曲率, R=4Λ | ✓ |
| Anti-de Sitter | 负曲率 | ✓ |
| Reissner-Nordström | 带电黑洞, 非零 Ricci | ✓ |
| S² 球面 | 常正曲率 | ✓ |
| H² 双曲面 | 常负曲率 | ✓ |

**测试统计**: 59 C++ + 88 Python = 147 tests

## 快速开始

### C++ 构建

```bash
# 使用 CMake Presets (推荐)
cmake --preset default
cmake --build build
ctest --test-dir build

# 或手动构建
mkdir build && cd build
cmake .. -DBUILD_TESTS=ON -DBUILD_PYTHON_BINDINGS=ON
cmake --build .
ctest --output-on-failure
```

### Python 绑定

```bash
# 安装依赖
pip install pybind11 sympy pytest

# 构建后使用
cd build/src/bindings
python3 -c "import _research_core as rc; print(rc.version)"
```

### Python API

```python
import sys; sys.path.insert(0, "build/src/bindings")
import _research_core as rc

# 解析器 + 运算符重载
x = rc.parse("x")
expr = x**2 + 2*x + 1  # Pythonic 表达式构建
print(expr)  # ((x^2) + ((2 * x) + 1))

# 定义流形
m = rc.geometry.Manifold("spacetime", ["t", "r", "theta", "phi"])

# 对角度量一行定义
g = rc.geometry.Metric.from_diagonal(m, [
    "-(1 - 2*M/r)",
    "(1 - 2*M/r)^(-1)",
    "r^2",
    "r^2 * sin(theta)^2",
])

# 计算曲率
Gamma = g.christoffel_symbols()
print(Gamma[[0, 0, 1]])  # Christoffel 符号分量
R = g.scalar_curvature()
print(R)

# 张量 Pythonic 访问
t = g.covariant_tensor()
print(t[[0, 0]])  # g_tt
```

## 项目结构

```
research/
├── src/
│   ├── core/
│   │   ├── symbol/        # 符号引擎 (expression, parser)
│   │   ├── tensor/        # 张量计算 (tensor, operations)
│   │   └── geometry/      # 几何核心 (manifold, metric, curvature)
│   ├── bindings/          # pybind11 Python 绑定
│   └── orchestrator/      # Agent 编排层 + 测地线求解器
├── tests/
│   ├── cpp/               # Catch2 C++ 测试
│   └── python/            # pytest Python 测试
├── docs/
│   └── compose/spec/      # 功能规格文档
├── cmake/                 # CMake config 模板
├── CMakeLists.txt
├── CMakePresets.json
└── pyproject.toml
```

## 技术栈

- **C++17** — 符号计算核心 (expression trees, tensor ops, geometry)
- **pybind11** — Python ↔ C++ 绑定
- **Python 3.11+** — Agent 编排, SymPy 基准测试
- **CMake 3.16+** — 构建系统
- **Catch2 v3** — C++ 测试框架
- **pytest** — Python 测试框架

## 与大荒界生态的关系

独立 git 子模块，与 company、game、kernel 平级。研究成果可反馈到 company（研究助手 skill pack）和 game（物理模拟引擎）。
