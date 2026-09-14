# research-experiment: 实验设计与执行
# Agent 使用此 skill 设计计算实验、运行数值模拟、收集数据

name: research.experiment
version: 0.1.0
description: "计算实验 — 黑洞解生成、宇宙学模拟、引力波信号、数值相对论"

capabilities:
  - blackhole_factory     # 生成标准黑洞解 (Schwarzschild/Kerr/RN/dS)
  - cosmology_simulation  # Friedmann 方程求解、宇宙演化
  - gw_simulation         # 引力波信号生成 (inspiral/merger/ringdown)
  - neutron_star_model    # TOV 方程求解、质量-半径关系
  - inflation_simulation  # 暴胀参数扫描、功率谱生成

tools:
  - name: generate_blackhole
    description: "生成标准黑洞解并计算完整属性"
    params: { type: string, params: dict }
    returns: { metric: string, horizons: dict, kretschmann: string, petrov_type: string }

  - name: run_cosmology
    description: "运行宇宙学模拟 (Friedmann 方程)"
    params: { Omega_m: float, Omega_L: float, H0: float, a_range: float[] }
    returns: { a: float[], t: float[], H: float[], age_gyr: float }

  - name: generate_gw_signal
    description: "生成引力波信号 (inspiral + merger + ringdown)"
    params: { m1: float, m2: float, distance_Mpc: float }
    returns: { t: float[], h_plus: float[], h_cross: float[] }

  - name: solve_neutron_star
    description: "求解 TOV 方程得到中子星模型"
    params: { rho_c: float, eos: string }
    returns: { M_solar: float, R_km: float, compactness: float }

  - name: run_inflation_scan
    description: "扫描暴胀参数空间"
    params: { potential: string, phi_range: float[] }
    returns: { n_s: float, r: float, N_efolds: float, alpha_s: float }
