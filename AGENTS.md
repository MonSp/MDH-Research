# AGENTS.md — 大荒界-科研 (MDH-Research)

## 项目概述

大荒界-科研是大荒界生态系统的第四个子项目，聚焦于通过 AI 智能体研究物理世界的数学解释。

**三大模块**：
1. **自主发现引擎** — 智能体自主进行假设-实验-验证循环，推导物理世界的数学模型
2. **研究助手** — 为人类研究者提供智能体工具链（文献分析、公式推导、数值模拟）
3. **智能体数学基础** — 探索 AI 智能体本身的物理/数学本质

**首个研究领域**：微分几何与引力理论

## 技术栈

- **C++17** — 符号计算核心（表达式树、解析器、张量运算、微分几何）
- **pybind11** — Python ↔ C++ 绑定
- **Python 3.11+** — Agent 编排、SymPy 基准测试
- **CMake 3.16+** — 构建系统（支持 presets）
- **Catch2 v3** — C++ 测试框架（FetchContent 自动获取）
- **pytest** — Python 测试框架

## 构建与测试

```bash
# C++ 构建 (使用 presets)
cmake --preset default
cmake --build build
ctest --test-dir build

# 或手动构建
mkdir -p build && cd build
cmake .. -DBUILD_TESTS=ON -DBUILD_PYTHON_BINDINGS=ON
cmake --build .
ctest --output-on-failure

# Python 测试 (需要先构建 C++ 绑定)
python3 -m pytest tests/python/ -v

# Lint
ruff check src/ tests/
```

## 目录结构

```
research/
├── src/
│   ├── core/                  # C++ 计算核心
│   │   ├── symbol/            # 符号引擎 (expression, parser)
│   │   ├── tensor/            # 张量计算 (tensor, operations)
│   │   └── geometry/          # 几何核心 (manifold, metric, curvature)
│   ├── bindings/              # pybind11 Python 绑定
│   └── orchestrator/          # Agent 编排层 (function calling)
├── tests/
│   ├── cpp/                   # Catch2 C++ 测试 (59 tests)
│   └── python/                # pytest Python 测试 (23 tests)
├── docs/
│   └── compose/spec/          # 功能规格文档
├── cmake/                     # CMake config 模板
├── CMakeLists.txt
├── CMakePresets.json
├── pyproject.toml
├── README.md
└── AGENTS.md
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

### 提交规范
- `feat(scope):` 新功能
- `fix(scope):` 修复
- `refactor(scope):` 重构
- `test(scope):` 测试
- `docs(scope):` 文档
- scope: `symbol`, `tensor`, `geometry`, `bindings`, `agents`, `orchestrator`, `tests`, `cmake`

## Agent 工具面（tool registry）

- 真相源：`config/research-skill-mapping.json` + `src/orchestrator/tool_registry.py`
- 新增物理能力：orchestrator 模块实现函数 → mapping 增加 tool 名 → registry 注册 `ToolSpec`（必要时写 wrapper）
- Metric 交接：工厂 put 进 `MetricStore`，消费者用 `metric_name`；禁止把活体 C++ Metric 塞进 JSON 返回值
- ResearchLoop / GeometrySession / LLM schema 均从 registry 取工具，不要在 research_loop 里再写死 tool 表
- **顺序链**：hypothesis 支持 `tools: [t1, t2, ...]`；`_execute_chain` 串行执行，`create_*` 的 `metric_name` 自动注入后续 `needs_metric` 步骤；缺 metric 时显式失败
- **验证升级**：`verification.sympy_is_zero` / `vacuum_residual_check`；`_analyze` 流水线 = 数值点检 → SymPy 恒零 → 真空残差门禁；结论带 `verification` 字段。Kerr 为对角近似，残差门禁 tol=1e-4、远场采样
- **参数扫描**：hypothesis 可带 `sweep`（axis values 或 start/stop/n/log；extract dict key；链式 inject）。单点失败不中断；有限样本 < 2 则失败；MAX 12 点；Expression 在参考点 evaluate
- **失败重规划**：`replan.diagnose_failure` + `heuristic_repair`；缺 metric 前置 factory / 注入 diagonal；缺参填默认；同义词与坏 kwargs 修复；journal note 记 `REPLAN(...)`；不可修则保持失败
- **智能体数学基础**：`agent_math.py` 研究轨迹 Shannon 熵 / decision pressure / MetricStore 状态 L2 距离 / sweep 信息量；`conclusion.foundations` 附带 run 级过程指标
- **假设排序**：`score_hypothesis` / `rank_hypotheses`；`conclusion.hypothesis_ranking` + `best_hypothesis`；journal conclusion 带 foundations/ranking extra
- **假设竞争（L6）**：首轮无成功结果时 `compete.should_compete` → heuristic/LLM 备选 → 再执行（含 replan）→ 重排；`conclusion.competed` + journal `COMPETE:` note
- **多轮迭代（L7）**：竞争后仍无成功 → `iterate_hypotheses` 参数变体/未用 consumer，最多 2 轮；`conclusion.iterate_rounds` + journal `ITERATE rN:`
- **已知量门禁（L8）**：`known_values.py` 对照 Hawking T / 宇宙年龄 / chirp mass / Schwarzschild QNM；`conclusion.known_value_checks` + evidence `KNOWN-VALUE PASS/FAIL`
- **研究战役（L9）**：`campaign.run_campaign(questions)` 共享 MetricStore/journal；`summarize_campaign` 输出 verify_rate / known_value_rate / store_growth / store_distance
- **研究报告（L10）**：`report.render_single_run` / `render_campaign` / `write_report` 把结论合成 markdown（纯文本，无绘图）
- **Journal 分析（L11）**：`journal_analytics.load_journal_dir` / `session_metrics` / `compare_sessions` / `render_analytics` 跨会话过程指标
- **CLI（L12）**：`python -m orchestrator.cli run|campaign|report|analytics|bench` 统一入口；`--llm auto|on|off`、`--json`、`--report/-o`
- **黄金基准（L13）**：`benchmarks/golden_questions.json` + `benchmark.run_benchmark`；`cli bench` 校验 verdict/tools/sweep/known-value，失败 exit 1
- **假设记忆（L14）**：`hypothesis_memory` 持久化成功链；`ResearchLoop(memory_path=...)` **显式路径才启用**；run 前 inject、run 后 remember；`cli memory summary|list|recall|inject`；CLI `run|campaign --memory PATH`
- **平台集成（L15）**：`.github/workflows/golden-bench.yml` 在 push/PR 上跑 C++ build + pytest + `cli bench --llm off`（CI 关闭 LLM 与 memory 保证确定性）
- **CI 修复（L16）**：workflow 先 `pip install pybind11`，再 `-Dpybind11_DIR=$(python3 -c 'import pybind11; print(pybind11.get_cmake_dir())')`
- **CI 加固（L17）**：workflow 安装 `pyyaml`；测试文件不得顶层 `import yaml`（函数内 try/skip）；dev 依赖含 pyyaml
- **已知量目录（L18）**：`benchmarks/known_values.json` + `known_values.evaluate_catalog_entry`；`check_chain` 默认加载；`cli known-values`
- **HTTP API（L19）**：`api.create_app()`；GET health/known-values/memory/summary；POST run/campaign/bench；`cli serve`；模块勿用 `from __future__ import annotations`（FastAPI body 误判为 query）
- **战役趋势（L20）**：`trend.aggregate_campaigns(path)` 对多份 campaign JSON 算 first→last delta（verify_rate / known_value_rate / mean_best_score）；`cli trend PATH [--json]`
- **API 趋势/报告（L21）**：POST `/trend` `/report`；GET `/analytics?journal_dir=`；远程可查报告与跨会话指标
- **基准扩展（L22）**：`benchmarks/golden_questions.json` 扩至 10 题；`cli bench --llm off` 仍为 CI 门禁
- **检查点快照（L23）**：`checkpoint.save_checkpoint` 将 run/campaign 结论落盘；`checkpoint_to_run_result` 可喂给 report；`cli checkpoint save|list|show`
- **API 检查点（L24）**：POST `/checkpoint`；GET `/checkpoint/list` `/checkpoint/show?path=`；远程存取研究结论快照
- **能力地图（L25）**：`capability_map.detect_capabilities` 内省模块/CLI/文件；`cli capmap [--json]` 输出 L0–L27 状态表
- **能力表同步（L26）**：`cli capmap --write-readme` 用 `capability-map:begin/end` 标记刷新 README/README_en
- **能力表 CI 门禁（L27）**：`cli capmap --check-readme` 不一致 exit 1；golden-bench workflow 含该步骤

## 与大荒界生态的关系

- 独立 git 子模块，与 company、game、kernel 平级
- 通过 IPC/API 复用 agent-kernel 的 ECS 智能体架构和 LLM 推理能力
- 研究成果可反馈到 company（研究助手 skill pack）和 game（物理模拟引擎）
