---
feature: tool-registry-closure
status: delivered
updated: 2026-09-15
branch: feat/tool-registry-closure
commits: 1aeeaad..22c16dc
---

# 工具面闭合：23 模块接入 ResearchLoop Tool Registry

## Report

**What was built** — 统一 agent 工具面：`MetricStore` 命名交接活体 C++ Metric；`serialize_result` 保证 JSON 安全；`tool_registry.py` 注册 80 个物理 tool（25 类，对齐并扩展 skill mapping）；`tool_registry_wrappers.py` 处理工厂 put / 消费者 metric_name。ResearchLoop 改用 registry handler 表与 `openai_tools_payload()` 动态 LLM schema，执行后写入 `journal.log_tool_call`（含 result + duration）。GeometrySession.define_metric 同步写入 MetricStore。

**Verification** — `PYTHONPATH=src:build/src/bindings python3 -m pytest tests/python/ -q` → **311 passed**（含新增 `test_tool_registry.py` 22 项与 `test_tool_call_journal_event`）。实测 Hawking pattern 产生 `tool_call` 事件（result/duration 齐全）。`registry_summary()["count"] == 80`。

**Journey log**:
1. 评审 critical：`log_tool_call` 少传 `result` 且 TypeError 被吞 → 改为执行后记录，补回归测试
2. Metric 活体对象不可 JSON 过境 → MetricStore + 工厂 metadata-only 返回
3. NP Petrov 分类返回 Type I — 既有 Weyl 抽取简化限制，wrapper 已接通（非本变更引入）
4. inflation 工具原签名收 callable V → 改为 named potential（chaotic/starobinsky/higgs）
5. 误在 monorepo 建 worktree → 改到 research 子仓库 `.worktrees/tool-registry`

## [S1] Problem

`ResearchLoop` 的工具面与计算库严重不对齐：

| 层 | 现状 |
|----|------|
| 计算库 | 23 个 orchestrator 模块，~100 个公开函数（GR/宇宙学/GW/中子星/NR…） |
| Skill 映射 | `config/research-skill-mapping.json` 声明 20 skill / ~70 tool 名 |
| 活体 registry | `research_loop._get_tools()` 仅 8 个函数；`session.py` 另有 6 个几何 tool，两套互不共享 |
| LLM schema | `_hypothesize_llm` 手写 8 个 schema，与 skill 映射脱节 |
| Metric 交接 | `create_*` 返回 dict 内含活体 C++ `Metric`，不可 JSON 序列化，无法进 LLM 往返或 journal |

后果：agent 能“看见”的物理能力远小于库实际能力；ResearchLoop 模式匹配兜底只能覆盖约 6 类问题；LLM 路径即使可用也选不到 cosmology/GW/TOV 等工具。

## [S2] Design

### 架构

```
config/research-skill-mapping.json   ← 唯一 skill/tool 真相源（扩展缺失模块）
            │
            ▼
src/orchestrator/tool_registry.py    ← ToolSpec + build_registry() + schema 导出
            │
    ┌───────┴────────┐
    ▼                ▼
MetricStore     execute_tool()
(命名 Metric 池)  (懒加载 + 结果序列化)
    │                │
    └───────┬────────┘
            ▼
     ResearchLoop._get_tools()
     ResearchLoop._hypothesize_llm()  ← schema 由 registry 生成
     session.GeometrySession          ← 复用同一 registry（几何 tool 不再双份）
```

### 1. MetricStore — 命名 Metric 交接

新增 `src/orchestrator/metric_store.py`：

```python
class MetricStore:
    def put(self, name: str, metric, manifold, coord_names, params: dict | None = None) -> None
    def get(self, name: str) -> dict          # {metric, manifold, coord_names, params}
    def get_metric(self, name: str) -> Metric # 仅返回 Metric
    def list(self) -> list[str]
    def drop(self, name: str) -> None
    def resolve_or_create(self, spec: dict) -> str
        # spec: {"metric_name": "schwarzschild"}  → 已有则返回 name
        # 或   {"name": "m1", "diagonal": ["-1","1",...], "coords": [...], "params": {...}}
        #      → from_diagonal 创建并 put，返回 name
```

- 进程内单例（`get_store()`），ResearchLoop / session / 各 wrapper 共享。
- 工厂类 tool（`create_schwarzschild` 等）执行后：dict 中的 `metric`/`manifold` 不进 JSON；改为 `store.put(result["name"].lower(), ...)`，返回给调用方的是 **metadata-only** payload（`name`/`coord_names`/`params`/`horizons`/`singularities`/解析式字符串）。
- 消费类 tool 参数统一接受 `metric_name: str`，从 store 取活体对象；若 store 未命中且提供 `diagonal`+`coords`，则现场创建。

### 2. 结果序列化

`tool_registry.serialize_result(obj)`：

| 输入 | JSON 形态 |
|------|-----------|
| `Expression` | `{"__expr__": expr.to_string()}` |
| `Tensor` | 嵌套 list of `{"__expr__": ...}`（或对数值分量直接 float） |
| `Metric` / `Manifold` | 丢弃（不应出现在 tool 返回值中；工厂已走 store） |
| `np.floating` / `np.ndarray` | float / list |
| dict / list / 标量 | 递归转换 |
| 其他 | `str(obj)` 截断 |

`ResearchLoop._analyze` 对 `{"__expr__": ...}` 可选择再 parse 做数值点检（兼容现有 `hasattr(result, "evaluate")` 路径：wrapper 在返回前保留表达式对象供本地验证，同时提供 `to_json()` 视图给 journal/LLM）。

**实现约定**：wrapper 返回 `(result_for_llm, result_for_analyze)` 或统一 dict 带 `_raw` 私有键在 journal 写入前剥离；优先前者（显式）。

### 3. ToolSpec 与 registry

`src/orchestrator/tool_registry.py`：

```python
@dataclass(frozen=True)
class ToolSpec:
    name: str                 # 全局唯一，snake_case
    category: str             # skill key，如 "cosmology"
    game_ability: str         # 炼算|参悟|推演|观象
    description: str
    params_schema: dict       # JSON Schema (OpenAI function 兼容)
    returns: str
    handler: str              # "module:function" 或 "wrapper:special"
    needs_metric: bool        # 是否依赖 MetricStore
    side_effect: str          # "none" | "store_put" | "store_read" | "file"

REGISTRY: dict[str, ToolSpec]           # build_registry() 懒加载
def get_tool_specs() -> list[ToolSpec]
def openai_tools_payload() -> list[dict]  # ResearchLoop LLM 用
def execute_tool(name: str, arguments: dict) -> Any
```

- handler **懒加载** import，避免 `research_loop` ↔ 物理模块循环依赖（与现 `_get_tools` 策略一致）。
- `openai_tools_payload()` 由 `ToolSpec.params_schema` 生成，删除 `_hypothesize_llm` 内手写 schema 块。

### 4. 工具面范围（Skill 映射驱动精选）

以 `research-skill-mapping.json` 的 20 skill 为骨架，补齐映射未覆盖但库中已有、且适合 agent 调用的模块。

**A. 保留/对齐现有映射（约 60 tool）** — 名称以 mapping 为准，handler 指到真实函数：

| skill | module | tools（示意，以 mapping 文件为准） |
|-------|--------|-------------------------------------|
| symbolic_compute | session/core | parse_expression, evaluate_expression, simplify, differentiate |
| tensor_algebra | core via session | raise/lower/contract/product（若 C++ 绑定未暴露则标 `unavailable` 并测试 skip） |
| differential_geometry | session | compute_christoffel/riemann/ricci/einstein/kretschmann |
| geodesic_solver | geodesic.py | solve_geodesic, christoffel_at_point |
| blackhole_solutions | blackholes.py | create_schwarzschild/kerr/RN/desitter, analyze_horizon, compute_kretschmann_numerical |
| hawking_radiation | hawking.py | hawking_temperature, evaporation_time, bekenstein_hawking_entropy, unruh_temperature |
| gravitational_lensing | lensing.py | deflection_angle, einstein_radius, image_positions, microlensing_light_curve |
| wave_analysis | gw_analysis.py | fisher_matrix, matched_filter_snr, compute_horizon_distance, inspiral_waveform_fd |
| binary_evolution | binary.py | chirp_mass, orbital_decay_rate, merger_time, evolve_binary |
| quasinormal_modes | quasinormal.py | schwarzschild_qnm, kerr_qnm, qnm_spectrum, ringdown_waveform |
| numerical_relativity | numerical_relativity.py | binary_merger_waveform, simulate_merger_ringdown |
| cosmology | cosmology.py | solve_friedmann, age_of_universe, cosmological_distances, hubble_parameter, flrw_metric_symbolic |
| inflation | inflation.py | slow_roll_parameters, number_of_efolds, inflationary_observables, primordial_scalar_power_spectrum |
| cmb_anisotropy | cmb.py | cmb_power_spectrum, acoustic_scale, peak_positions, cmb_observables |
| dark_energy | dark_energy.py | w_cpl, dark_energy_density, deceleration_parameter, f_R_cosmology |
| perturbation_theory | perturbation_eqns + cosmo_perturbation | solve_regge_wheeler, solve_zerilli, compute_gw_strain, growth_factor, matter_power_spectrum |
| killing_symmetry | killing.py | is_killing_vector, detect_coordinate_killing_vectors, classify_symmetry |
| energy_conditions | energy_conditions.py | check_energy_conditions_for_metric, check_energy_conditions_numerical |
| neutron_star | neutron_star.py | solve_tov, mass_radius_relation, tidal_deformability |
| sympy_bridge | sympy_bridge.py | expr_to_sympy（仅本地；不进 LLM schema 时可标 `internal`） |

**B. 新增 skill 条目（映射未覆盖的高价值模块）** — 扩写 `research-skill-mapping.json`：

| 新 skill key | module | tools | ability |
|--------------|--------|-------|---------|
| causal_structure | causal.py | classify_vector, light_cone_at_point, causal_classification, horizon_causal_transition, singularity_analysis | 观象 |
| field_equations | field_equations.py | einstein_tensor, stress_energy_perfect_fluid, field_equation_residual_symbolic, field_equation_residual_numerical | 参悟 |
| tetrad | tetrad.py | build_tetrad_diagonal, compute_spin_connection | 炼算 |
| newman_penrose | newman_penrose.py | build_null_tetrad_diagonal, classify_petrov_type | 参悟 |
| post_newtonian | post_newtonian.py | pn_energy_1pn, perihelion_advance, gravitational_wave_flux_quadrupole, pn_binding_energy_2pn | 推演 |
| linearized_gravity | perturbation.py | linearized_riemann, linearized_ricci, gravitational_wave_tt | 推演 |
| adm_bssn | adm.py + bssn.py | extract_adm_static, hamiltonian_constraint_static, bssn_variables | 推演 |

**C. 明确不进 agent 工具面**（库函数保留，不注册）：

- `visualization.plot_*`（文件副作用；后续 report skill）
- `journal.*` / `kernel_bridge.*` / `research_loop.*`（基础设施）
- `geodesic.geodesic_equation`（ODE RHS，内部）
- `blackholes.compute_kretschmann_numerical` 若仅接受活体 bh dict → 薄包装为 `metric_name + r`
- inflation/hawking/lensing 等 **纯标量捷径函数** 可注册但可标 `low_value`；首批 **必注册** 以 mapping 列表为准，不为“全”而塞 120 个

目标规模：**约 75–85 个 tool**（mapping 约 70 去重 + B 新增约 15，去掉不可用/内部项）。

### 5. Metric 依赖分类

| 类型 | 例子 | 参数约定 |
|------|------|----------|
| **纯标量** | hawking_temperature, chirp_mass, age_of_universe | 原函数签名 → JSON Schema |
| **工厂 (store_put)** | create_schwarzschild, create_kerr, flrw_metric_symbolic | 返回 metadata；`store_name` 可选参数（默认用解名） |
| **Metric 消费 (store_read)** | solve_geodesic, classify_symmetry, check_energy_conditions_for_metric, analyze_horizon | 必有 `metric_name`；可选 `diagonal`+`coords` 兜底创建 |
| **有状态会话** | session.define_manifold/define_metric/compute_* | 保留，与 MetricStore 打通：define_metric 即 put |

### 6. ResearchLoop 接入

1. `_get_tools()` → `tool_registry.get_handler_map()`（按 name → callable）。
2. `_hypothesize_llm` 的 `tools_desc` / 手写 `tool_schemas` → `openai_tools_payload()` + 精简 known_metrics 示例（保留 Schwarzschild 等 few-shot）。
3. `_hypothesize_patterns`：**保留**为无 LLM 兜底；可将 pattern 命中的 tool 名改为 registry 中同义名（`compute_scalar_curvature` 别名 → `compute_scalar_curvature` 或 `differential_geometry.compute_scalar`）。**别名表**放 mapping 或 registry，避免破坏现有测试。
4. 每次 `_execute` 前后：`journal.log_tool_call`（已有接口；若当前未调用则补上）。
5. 假设校验：LLM 返回的 `tool` 必须在 registry 中，否则丢弃（现有逻辑已做，保持）。

### 7. 错误行为

- 未知 tool 名 → `ValueError` + journal `ERROR`
- `metric_name` 不在 store → 返回 `{"error": "metric not found", "available": [...]}`，不抛到 loop 外（与 session 风格一致）
- 底层物理函数异常 → 捕获，journal observation `success=False`（现有 ResearchLoop 行为）
- schema 非法 / LLM 返回坏 JSON → 回落 pattern 路径

### 8. 测试边界

- **注册完整性**：mapping 中每个 `tools[]` 名在 registry 有对应或显式 `UNAVAILABLE` 列表
- **可调用性烟雾**：每个 `side_effect != file` 的 tool 用默认/最小参数调一次，断言无异常（慢工具如 evolve_binary/cmb 用退化参数）
- **MetricStore**：put/get/list/drop；工厂 metadata 不含 C++ 对象；metric_name 消费路径
- **序列化**：Expression/np/dict 往返为 JSON
- **schema**：`openai_tools_payload()` 每项含 name/description/parameters；LLM mock 返回 registry 内 tool 可执行
- **ResearchLoop**：无 LLM pattern 路径回归（现有测试）；扩展一条“新 tool 可被 loop 调用”用例
- **不测**：LLM 理智选择 tool 的质量；C++ 数值正确性（已有库测试）

## [S3] Out of Scope

- 验证升级（SymPy 化简嵌入、场方程残差门禁）— 独立后续
- 多步推导规划 / 自主假设搜索
- visualization → report skill 挂载
- kernel_bridge 端到端 daemon 联调
- 改动 C++ 核心或 pybind11 绑定
- 性能/GPU

## Tasks

- [x] T1: MetricStore + serialize_result — acceptance: put/get/list/drop 单测过；工厂 dict 剥离 metric 后可 json.dumps (covers: S2.1, S2.2)
- [x] T2: tool_registry.py（ToolSpec/build_registry/execute_tool/openai_tools_payload）— acceptance: 可按 name 执行已注册 handler；schema payload 合法 (covers: S2.3)
- [x] T3: 扩展 research-skill-mapping.json（新增 causal/field_eq/tetrad/NP/PN/linearized/adm_bssn）— acceptance: JSON 合法且与 registry category 对齐 (covers: S2.4B)
- [x] T4: 按 mapping 批量注册 A+B 全部 tool（懒加载 + Metric 分类）— acceptance: 注册数 ≥ 70；完整性测试过；烟雾测试过 (covers: S2.4, S2.5; depends: T1, T2)
- [x] T5: ResearchLoop 接入 registry + 动态 LLM schema + journal.log_tool_call — acceptance: 无 LLM 现有测试过；mock LLM 返回 cosmology tool 可执行 (covers: S2.6; depends: T2, T4)
- [x] T6: session.py 与 MetricStore 打通（define_metric 即 put，几何 tool 走 registry）— acceptance: define → compute_* 链式测试过 (covers: S2.5; depends: T1, T2)
- [x] T7: 回归与文档 — acceptance: pytest 全绿；README/AGENTS 工具面描述与 mapping 一致 (covers: S2; depends: T4, T5, T6)
