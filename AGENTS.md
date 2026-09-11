# AGENTS.md — 大荒界-科研 (MDH-Research)

## 项目概述

大荒界-科研是大荒界生态系统的第四个子项目，聚焦于通过 AI 智能体研究物理世界的数学解释。

**三大模块**：
1. **自主发现引擎** — 智能体自主进行假设-实验-验证循环，推导物理世界的数学模型
2. **研究助手** — 为人类研究者提供智能体工具链（文献分析、公式推导、数值模拟）
3. **智能体数学基础** — 探索 AI 智能体本身的物理/数学本质

**首个研究领域**：微分几何与引力理论

## 技术栈

- **Python 3.11+** — 科学计算（NumPy/SciPy/SymPy）、Agent 编排、FastAPI 服务
- **C++17** — 高性能符号计算核心（表达式树、张量运算、几何计算）
- **pybind11** — Python ↔ C++ 绑定
- **CMake** — C++ 构建系统
- **scikit-build-core** — Python 包含 C++ 扩展的构建

## 构建与测试

```bash
# C++ 构建
mkdir -p build && cd build
cmake .. -DBUILD_TESTS=ON
cmake --build .
ctest --output-on-failure

# Python 环境
pip install -e ".[dev]"

# Python 测试
pytest tests/python/ -v

# Lint
ruff check src/ tests/
```

## 目录结构

```
research/
├── src/
│   ├── core/                  # C++ 计算核心
│   │   ├── symbol/            # 符号引擎（表达式树、化简、微分）
│   │   ├── tensor/            # 张量计算（指标、缩并、协变导数）
│   │   ├── geometry/          # 几何核心（流形、度量、联络、曲率）
│   │   ├── research_core.h    # 公共头文件
│   │   └── research_core.cpp  # 库入口
│   ├── bindings/              # pybind11 绑定层
│   ├── agents/                # Agent 功能模块
│   │   ├── discovery/         # 自主发现引擎
│   │   ├── assistant/         # 研究助手
│   │   └── foundations/       # 智能体数学基础
│   └── orchestrator/          # LLM 驱动的推导编排
├── tests/
│   ├── cpp/                   # Catch2 C++ 测试
│   ├── python/                # pytest Python 测试
│   └── integration/           # 集成测试（mock LLM → 全链路）
├── benchmarks/                # 基准测试（Schwarzschild, FLRW, Kerr）
├── docs/
│   ├── compose/spec/          # 功能规格
│   └── design/                # 设计文档
├── CMakeLists.txt             # C++ 构建配置
└── pyproject.toml             # Python 项目配置
```

## 代码规范

### C++
- Google C++ Style（命名空间小写，类名 PascalCase，函数 snake_case）
- 使用 `std::shared_ptr` 管理表达式和张量的生命周期
- 异常而非错误码
- 头文件用 `#pragma once`

### Python
- PEP 8 + ruff 格式化
- 类型注解（pyright 兼容）
- 文档字符串：Google 风格
- 异步优先（FastAPI + asyncio）

### 提交规范
- `feat(scope):` 新功能
- `fix(scope):` 修复
- `test(scope):` 测试
- `docs(scope):` 文档
- scope: `core`, `tensor`, `geometry`, `bindings`, `agents`, `orchestrator`, `tests`

## 与大荒界生态的关系

- 独立 git 子模块，与 company、game、kernel 平级
- 通过 IPC/API 复用 agent-kernel 的 ECS 智能体架构和 LLM 推理能力
- 研究成果可反馈到 company（研究助手 skill pack）和 game（物理模拟引擎）

## 首个里程碑

**MVP: 符号计算引擎与基础微分几何**
- 验证目标：Schwarzschild 度量的完整曲率计算管线
- 详见 `docs/compose/spec/mvp-symbolic-geometry.md`
