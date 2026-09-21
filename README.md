# 大荒界-科研 (MDH-Research)

[![Tests](https://img.shields.io/badge/tests-377%20passed-brightgreen)]()
[![C++17](https://img.shields.io/badge/C%2B%2B-17-blue)]()
[![Python](https://img.shields.io/badge/Python-3.11+-yellow)]()
[![English](https://img.shields.io/badge/README-English-blue)](README_en.md)

**让智能体可靠地算物理、验结果、扫参数。**

MDH-Research 是大荒界生态的第四个子项目：一个面向 AI 智能体的**物理计算实验平台**。底层是 C++17 符号几何核心与 23 个 Python 物理模块；上层把它们暴露为 80 个可编排 tool，支持多步链执行、SymPy/场方程残差验证，以及一次假设下的参数扫描与趋势汇总。

> **定位一句话**：可被 agent 调用、可多步编排、可参数扫描、结果可符号/残差核验的物理计算实验平台。  
> 「辅助理论计算」已闭环；「自主发现」仍是下一层。

English: [README_en.md](README_en.md)

---

## 它解决什么问题

物理计算库很多，但对 agent 不友好：

| 痛点 | 本项目做法 |
|------|------------|
| LLM 不知道有哪些函数、参数怎么填 | 统一 `tool_registry`（80 tools）+ OpenAI function schema |
| Metric / 张量对象无法 JSON 过境 | `MetricStore` 命名交接；工厂返回 metadata，消费者收 `metric_name` |
| 一次只能调一个函数 | 顺序链 `tools[]`，工厂输出自动注入下一步 |
| 「算完了」≠「算对了」 | SymPy 恒零证明 + 真空场方程残差门禁 + 数值绑定检查 |
| 扫参数要手工循环 | `sweep` 轴展开 + 趋势汇总（方向 / log-log 斜率 / Spearman） |

---

## 一张图看懂

```
自然语言问题
    │
    ▼
ResearchLoop  ── LLM / pattern  ──►  hypothesis（tool / tools 链 / sweep）
    │
    ▼
tool_registry（80 tools） + MetricStore
    │  顺序执行；create_* 的 metric_name 注入后续 consumer
    ▼
Verification  ── SymPy simplify → 绑定 numeric → G_μν 残差门禁
    │
    ▼
ResearchJournal  ── hypothesis → experiment → tool_call* → observation → conclusion
    │
    ▼
结论：Hypotheses verified / SWEEP 趋势 / 证据列表
```

### 实测端到端（main）

```text
Q: What is the scalar curvature of Schwarzschild spacetime?
   → create_schwarzschild → compute_scalar_curvature
   → CONFIRMED (SymPy simplify → 0)
   → GATE PASS  max|G_μν| ≈ 2.5e-16
   → verdict: Hypotheses verified

Q: How does Hawking temperature vary as a function of mass?
   → sweep M ∈ {1e30, 1e31, 1e32}, extract T_K
   → SWEEP: T_K vs M → decreasing, log-log slope ≈ -1.0   # T ∝ 1/M
```

---

## 快速开始

```bash
# 克隆（含全部子模块）
git clone --recursive https://github.com/MonSp/MatrixDahuang.git
cd MatrixDahuang/research

# C++ 构建 + 测试
cmake --preset default && cmake --build build
ctest --test-dir build                    # 59 C++ tests

# Python 测试
pip install sympy scipy matplotlib numpy pytest
python3 -m pytest tests/python/ -v       # 318+ Python tests
```

### 三分钟体验

```python
import sys
sys.path.insert(0, "src")
sys.path.insert(0, "build/src/bindings")

from orchestrator.research_loop import ResearchLoop

loop = ResearchLoop()  # 设置 LLM_API_KEY 可走真 LLM；否则 pattern 兜底

# 1) 计算 + 验证
r = loop.run("What is the scalar curvature of Schwarzschild spacetime?")
print(r["conclusion"]["verdict"])
# → Hypotheses verified

# 2) 参数扫描 + 趋势
r = loop.run("How does Hawking temperature vary as a function of mass? Scan several masses.")
print(r["results"][0]["sweep"]["trend"]["direction"],
      r["results"][0]["sweep"]["trend"]["log_log_slope"])
# → decreasing  -1.0
```

### 直接调 tool

```python
from orchestrator.tool_registry import execute_tool, registry_summary

print(registry_summary()["count"])  # 80
execute_tool("create_schwarzschild", {"M": 1})
R = execute_tool("compute_scalar_curvature", {"metric_name": "schwarzschild"})
print(R.evaluate({"M": 1, "r": 6, "theta": 1.5708, "phi": 0, "t": 0}))  # ~0
print(execute_tool("age_of_universe", {})["age_gyr"])  # ~13.8
```

---

## 智能体能力分层

以代码与评测为准，而非愿景标签：

| 层 | 内容 | 状态 |
|----|------|------|
| **L0 计算库** | C++ 符号核心 + 23 个 Python 物理模块，377 tests | ✅ |
| **L1 Agent 工具面** | 80 tools 统一 registry；MetricStore 命名交接 | ✅ |
| **L2 实验台账** | ResearchJournal 全链路 event | ✅ |
| **L3 多步编排** | LLM `tools[]` 顺序链；`metric_name` 自动注入 | ✅ |
| **L4 验证** | SymPy 恒零 + 绑定 numeric + 真空残差门禁 | ✅ |
| **L4b 参数扫描** | `sweep` 轴 + 趋势汇总 | ✅ |
| **L4c 失败重规划** | 诊断 + 启发式修复（缺 metric / 缺参 / 同义词 / 坏 kwargs）后重跑 | ✅ |
| **L5 智能体数学基础** | 轨迹熵 / 状态距离 / sweep 信息量 + **假设排序**（journal 固化） | ✅ |
| **L6 假设竞争** | 首轮全失败时启发式/LLM 再生成备选假设并重排 | ✅ |
| **L7 多轮迭代** | 竞争后仍失败时最多 2 轮参数变体/未用 consumer 迭代 | ✅ |
| **L8 已知量门禁** | Hawking T∝1/M、宇宙年龄、chirp mass、Schwarzschild QNM 教科书对照 | ✅ |
| **L9 研究战役** | 多问题共享 MetricStore；程序级 verify/known-value/score 汇总 | ✅ |
| **L10 研究报告** | 战役/单次 run → 结构化 markdown（verdict/验证/ranking/证据） | ✅ |
| **L11 Journal 分析** | 跨会话 JSONL 过程指标：COMPETE/ITERATE/REPLAN、成功率、top tools | ✅ |
| **L12 CLI 门面** | `python -m orchestrator.cli` run/campaign/report/analytics/bench | ✅ |
| **L13 黄金基准** | 5 个标准问题 + expect；`cli bench` 一键回归（失败 exit 1） | ✅ |
| **L14 假设记忆** | 成功 tool 链按关键词召回并注入后续 run；`cli memory` / `--memory` | ✅ |
| **L15 平台集成** | CLI `--memory` 挂接 + GitHub Actions 黄金基准门禁 | ✅ |
| **L16 CI 修复** | 安装 pybind11 并传 `pybind11_DIR`，使 golden-bench 工作流可配置/构建 | ✅ |
| **L17 CI 加固** | 安装 pyyaml；测试顶层不 import yaml（可选 skip） | ✅ |
| **L18 已知量目录** | JSON 可扩展目录（formula/range/near/positive）；`cli known-values` | ✅ |
| **L19 HTTP API** | FastAPI `/run` `/campaign` `/bench` `/health`；`cli serve` | ✅ |
| **L20 战役趋势** | 多份 campaign JSON → verify/kv/score first→last 趋势；`cli trend` | ✅ |
| **L21 API 趋势/报告** | HTTP `/trend` `/report` `/analytics` 接通 L10/L11/L20 | ✅ |
| **L22 基准扩展** | 黄金 suite 扩至 10 题（Kretschmann/蒸发/QNM/chirp 等） | ✅ |

### 计算 / 推理 / 验证

| 能力 | 水平 | 说明 |
|------|------|------|
| **计算** | 成熟 | 80 tool；Metric 命名交接；链式 create→consumer |
| **推理（编排）** | 多步 + 扫描 | LLM 选 tool（链式感知）~99%；顺序执行；扫轴出趋势 |
| **推理（理论）** | 辅助，非替代 | 能编排「Kerr 真空 / T_H vs M」；不能开放假设搜索、文献 grounding |
| **验证** | 符号 + 残差 + 趋势 | SymPy 证 R≡0；G_μν 门禁；拒绝未绑定/NaN 假通过 |

---

## Agent 工具面

`src/orchestrator/tool_registry.py` 是唯一真相源（与 `config/research-skill-mapping.json` 对齐）。

| 机制 | 模块 | 作用 |
|------|------|------|
| **MetricStore** | `metric_store.py` | 命名交接活体 C++ Metric |
| **顺序链** | `research_loop.py` | `tools[]` 串行；工厂 → consumer 注入 |
| **验证** | `verification.py` | SymPy / numeric / 真空残差 |
| **参数扫描** | `param_sweep.py` | 轴展开 + 趋势汇总 |

### 顺序链

```json
{
  "prediction": "Kerr is a vacuum solution so R=0",
  "tools": [
    {"tool": "create_kerr", "params": {"M": 1, "a": 0.5}},
    {"tool": "compute_scalar_curvature", "params": {}}
  ]
}
```

### 参数扫描

```json
{
  "prediction": "Hawking temperature decreases as 1/M",
  "sweep": {
    "tool": "hawking_temperature",
    "axis": {"name": "M", "values": [1e30, 1e31, 1e32]},
    "extract": "T_K"
  }
}
```

链式扫描（把轴值注入工厂）：

```json
{
  "tools": [
    {"tool": "create_schwarzschild", "params": {"M": 1}},
    {"tool": "compute_kretschmann", "params": {}}
  ],
  "sweep": {
    "axis": {"name": "M", "values": [1, 2, 3]},
    "inject": {"tool": "create_schwarzschild", "param": "M"},
    "extract": null
  }
}
```

| 趋势字段 | 含义 |
|----------|------|
| `direction` | increasing / decreasing / non-monotonic / flat |
| `spearman_rho` | 秩相关（n≥3） |
| `log_log_slope` | log-log 最小二乘斜率（幂律检验，T∝M⁻¹ → −1） |
| `y_ratio` | y[-1]/y[0] |
| `points` | `{x, y}` 或 `{x, error}` |

约束：最多 12 点；单点失败不中断；有限样本少于 2 则该假设失败。

**已验证趋势**

| 扫描 | 轴 | 结果 |
|------|-----|------|
| Hawking T | M = 1e30…1e32 | decreasing，log-log slope ≈ **−1** |
| Schwarzschild K | M = 1…3（链式） | increasing（K∝M² @ 固定 r） |

### 验证流水线

1. **SymPy** `simplify` 证明表达式恒为 0（绕过 C++ `is_zero` 对完整 GR 的失败）
2. **Numeric** 仅在自由符号完全绑定时做点检（拒绝未绑定 L/a 等假零）
3. **真空残差** 对 Schwarzschild/Kerr 工厂链检查远场 G_μν≈0（RN/dS 不进门禁）

结论带 `verification` 摘要；Kerr 为对角近似，门禁 tol=1e-4、远场采样。

---

## 物理能力总览

### 广义相对论与黑洞
- 度量构建、Christoffel → Riemann → Ricci → Einstein → Kretschmann
- Schwarzschild / Kerr / Reissner-Nordström / de Sitter
- 视界与奇点分析、Hawking 温度/蒸发/熵、Unruh
- 因果结构：光锥、类时/类光/类空

### 引力波与致密天体
- QNM（Schwarzschild/Kerr）、RW/Zerilli、应变 h₊/h×
- 双星演化、chirp mass、Fisher/SNR、探测距离
- 后牛顿 1PN/2PN、四极矩通量
- 中子星 TOV、质量-半径、SLy4 EOS、潮汐形变

### 宇宙学
- FLRW / Friedmann、宇宙年龄、角直径与光度距离
- 增长因子、BBKS、功率谱、BAO
- 暴胀慢滚、n_s、r、原初功率谱
- CMB 角功率谱、声峰、Silk 阻尼
- 暗能量 CPL、f(R)、ΛCDM

### 数值相对论与理论框架
- ADM 3+1、BSSN、合并波形
- Tetrads、Newman-Penrose、Petrov 分类
- Killing 矢量、线性化引力、能量条件

### 基准测试

| 度量 | 验证 | 结果 |
|------|------|------|
| Schwarzschild | Christoffel + Ricci=0 + K=48M²/r⁶ | ✓ SymPy |
| FLRW (k=0) | Christoffel + R=6(ä/a+H²) | ✓ |
| Kerr | 结构 + 数值 Ricci=0 + 视界 | ✓ |
| Minkowski | Γ=0, R=0, K=0 | ✓ |
| de Sitter | R=4Λ | ✓ |
| Reissner-Nordström | 非零 Ricci（电磁源） | ✓ |
| S² / H² | R=±2 | ✓ |

---

## 技术栈与结构

- **C++17** 符号核心（表达式树、张量、微分几何）
- **pybind11** Python 绑定
- **Python 3.11+** 编排、SymPy/SciPy/NumPy
- **CMake / Catch2 / pytest**

```
research/
├── src/core/           # C++ 符号 / 张量 / 几何
├── src/bindings/       # pybind11
├── src/orchestrator/   # 23 物理模块 + registry / loop / verify / sweep
├── config/             # research-skill-mapping.json
├── skills/             # compute / analyze / experiment / report
├── scripts/            # eval_tool_selection.py
├── tests/              # 59 C++ + 318+ Python
└── docs/compose/spec/  # 功能规格
```

---

## Agent-Kernel 集成

```
ResearchLoop → ResearchJournal → Skill Manifests → AgentKernelBridge
                                              ↕ unix socket / JSON-RPC
                                         agent-kernel (ECS)
```

- 27 个研究 skill → 修仙能力（炼算 / 参悟 / 推演 / 观象）
- Journal 双后端：kernel EventJournal 或本地 JSONL

---

## 与大荒界生态

| 子项目 | 反馈方向 |
|--------|----------|
| **company** | 研究助手 skill pack、数值计算后端 |
| **game** | 物理模拟、引力波信号生成 |
| **kernel** | 共享 ECS 智能体、Journal 消费 |

规格文档：`docs/compose/spec/`（mvp-symbolic-geometry、tool-registry-closure、chain-executor、verify-upgrade、param-sweep）

## License

Apache 2.0
