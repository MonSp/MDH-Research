# research-report: 研究报告生成
# Agent 使用此 skill 整理实验结果、生成研究报告、可视化

name: research.report
version: 0.1.0
description: "研究报告 — 结果整理、可视化、报告生成、假设验证"

capabilities:
  - result_synthesis     # 实验结果整理与综合
  - visualization        # 3D 轨迹/光变曲线/功率谱可视化
  - hypothesis_testing   # 假设验证与统计检验
  - report_generation    # 结构化研究报告生成

tools:
  - name: plot_geodesic_3d
    description: "3D 测地线轨迹渲染"
    params: { metric: string, trajectory: float[][], save_path: string }
    returns: image

  - name: plot_waveform
    description: "引力波应变波形图"
    params: { t: float[], h_plus: float[], h_cross: float[], save_path: string }
    returns: image

  - name: plot_power_spectrum
    description: "CMB/物质功率谱图"
    params: { ell: float[], D_ell: float[], save_path: string }
    returns: image

  - name: validate_result
    description: "将计算结果与已知解析解/文献值对比"
    params: { computed: dict, expected: dict, tolerance: float }
    returns: { match: bool, deviations: dict }

  - name: generate_report
    description: "生成结构化研究报告"
    params: { hypothesis: string, experiments: list, results: dict, conclusion: string }
    returns: markdown
