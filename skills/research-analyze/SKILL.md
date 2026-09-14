# research-analyze: 物理分析与分类
# Agent 使用此 skill 分析物理系统、分类时空结构

name: research.analyze
version: 0.1.0
description: "物理系统分析 — 对称性检测、能量条件、视界/奇点、Petrov 分类"

capabilities:
  - symmetry_analysis      # Killing 矢量场检测/分类
  - energy_conditions      # WEC/SEC/DEC/NEC 检验
  - horizon_analysis       # 视界/奇点数值检测
  - petrov_classification  # Weyl 标量 → Petrov 类型
  - causal_structure       # 光锥/因果分类

tools:
  - name: classify_symmetry
    description: "检测时空对称性: stationary/static/axisymmetric"
    params: { metric: string, coords: string[] }
    returns: { stationary: bool, static: bool, axisymmetric: bool, killing_vectors: dict }

  - name: check_energy_conditions
    description: "检验能量条件 (WEC/SEC/DEC/NEC)"
    params: { metric: string, rho: string, p: string, coords: string[] }
    returns: { WEC: string, SEC: string, DEC: string, NEC: string }

  - name: analyze_horizon
    description: "数值扫描视界位置 (g_tt 符号变化)"
    params: { metric: string, coords: string[], params: dict }
    returns: { horizon_radii: float[], types: string[] }

  - name: classify_petrov
    description: "从 Weyl 标量分类 Petrov 类型"
    params: { weyl_scalars: dict }
    returns: { type: string, description: string }

  - name: analyze_causal_structure
    description: "分析因果结构: 光锥/类时/类光/类空分类"
    params: { metric: string, coords: string[], point: float[] }
    returns: { inside_horizon: bool, light_cone_slope: float }
