# research-compute: 符号/数值计算核心
# Agent 使用此 skill 执行底层数学计算

name: research.compute
version: 0.1.0
description: "物理世界的数学计算引擎 — 符号表达式、张量代数、微分几何、数值求解器"

capabilities:
  - symbolic_expression     # 构建/解析/微分/化简/求值
  - tensor_algebra          # 升降指标/缩并/张量积
  - differential_geometry   # Christoffel/Riemann/Ricci/Einstein/Kretschmann
  - numerical_solver        # ODE/RK4 测地线积分

tools:
  - name: parse_expression
    description: "将数学表达式字符串解析为符号表达式树"
    params: { expression: string }
    returns: Expression

  - name: evaluate_expression
    description: "数值求值符号表达式"
    params: { expression: Expression, variables: dict[str, float] }
    returns: float

  - name: compute_christoffel
    description: "从度量张量计算 Christoffel 符号 Γ^μ_{νρ}"
    params: { metric: string, coords: string[] }
    returns: Tensor

  - name: compute_curvature
    description: "计算完整曲率链路: Riemann → Ricci → Scalar → Einstein → Kretschmann"
    params: { metric: string, coords: string[] }
    returns: { riemann: Tensor, ricci: Tensor, scalar: float, einstein: Tensor, kretschmann: float }

  - name: solve_geodesic
    description: "RK4 数值积分测地线方程"
    params: { metric: string, coords: string[], x0: float[], u0: float[], tau_max: float }
    returns: { taus: float[], trajectory: float[][] }
