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

- **符号计算引擎** — 表达式树、自动微分、化简、递归下降解析器
- **张量计算** — 指标操作、缩并、张量积
- **微分几何** — 流形、度量、Christoffel 符号 → Riemann → Ricci → 标量曲率
- **Python 绑定** — pybind11 暴露完整 API
- **Agent 编排层** — OpenAI function calling 兼容的工具接口

### 基准测试

| 度量 | 验证内容 | 结果 |
|------|----------|------|
| Schwarzschild | Christoffel 符号 + Ricci = 0 | ✓ 与 SymPy 解析解一致 |
| FLRW (k=0) | Christoffel + Ricci + 标量曲率 R=6(ä/a+H²) | ✓ |
| Kerr | 结构验证 + 数值 Ricci = 0 + 事件视界 | ✓ |

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

sym = rc.symbol
geom = rc.geometry

# 使用解析器
expr = sym.parse("1 - 2*M/r")
print(expr.to_string())  # (1 - ((2 * M) * r^(-1)))

# 定义流形和度量
m = geom.Manifold("spacetime", ["t", "r", "theta", "phi"])
M = sym.symbol("M"); r = sym.symbol("r")

g = geom.Metric(m, [
    [sym.parse("-(1 - 2*M/r)"), sym.number(0), sym.number(0), sym.number(0)],
    [sym.number(0), sym.parse("(1 - 2*M/r)^(-1)"), sym.number(0), sym.number(0)],
    [sym.number(0), sym.number(0), sym.mul(r, r), sym.number(0)],
    [sym.number(0), sym.number(0), sym.number(0), sym.mul(r, r)],
])

# 计算曲率
Gamma = g.christoffel_symbols()
Ric = g.ricci_tensor()
R = g.scalar_curvature()
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
│   └── orchestrator/      # Agent 编排层 (function calling)
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
