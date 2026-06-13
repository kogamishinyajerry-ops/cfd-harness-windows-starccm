# Track D · 仓库缺口盘点 · starccm_adapter 五个空壳子目录 + 7-9 月可补足清单

> **任务来源**:chief-engineer 派出的仓库侦察兵(对齐 `.harness/reins/chief-engineer/agent.md`)
> **盘点时间**:2026-06-12 03:41+08
> **盘点路径**:`D:\CFD-harness-Windows-StarCCM\src\cfd_harness\starccm_adapter\`
> **本文件不写代码**;唯一允许写盘的目的是"留下盘点证据 + 优先级清单"。

---

## 0. TL;DR · 1 句话总结 + 4 行结论

| 维度 | 结论 |
|---|---|
| 5 个子目录的物理状态 | **不存在**;只在 `AGENTS.md` 行 103-107 的对照表 + `CHARTER.md` §4 的 3 行待补资产列表里**留了名字**。当前 `starccm_adapter/` 下只有 `__init__.py`、`executor.py`、`geometry/__init__.py` 三个文件。 |
| 与 cfd-harness-unified 的对照 | 5 个服务子目录在原仓是 `ui/backend/services/` 下;本仓按 AGENTS.md 行 103-107 表格 plan 到 `src/cfd_harness/starccm_adapter/<name>/`,但**目录骨架 + `__init__.py` 都没建**。 |
| 7-9 月关键路径(必须补) | (a) `case_solve/fan_blade.py` + 配套 `macros/Rotor37Slice.java` / `Rotor37SingleChannel.java`;(b) `case_extractors/fan_aero.py`(ForceCoefficientReport reader);(c) `gold_standards/rotor37.yaml` + `rotor67.yaml`(对照基线,跑无样本)— 这 4 条**挡 DEC-008.a/M1 验收**。 |
| 7-9 月可推迟到 2027-Q1 | `case_visualize/`(CHARTER 没列,STAR-CCM+ 端 PNG 复用 export-scene 即够)、`mesh_quality/`(CHARTER P2 / 9 月;3D 叶片样本出来才有 y+/skewness 真问题)、`physics/`(CHARTER 没列,gold_standard 自带 tolerance,暂不需要单列)。 |

> **诚实分层**(任务 §4 强制要求):
> - **70% 完成** — 5 个空壳的现状盘点 + 复用度评估(见 §1-§2)
> - **20% 完成** — ROI 排序(见 §3;10 条主清单 + 8 条次清单)
> - **10% 完成** — 关键路径判定(见 §4;基于 CHARTER §2 里程碑 + DEC-008.a 时间窗)
> - **总评**:本次盘点自身可信度 70-80%,因为关键路径判定需要 chief-engineer 在 milestone 评审会上签字(我没那个权限);ROI 排序里 4 条**值带"★"**的都已经过 L0 autonomy grant 内的"mock-first 一切实现"原则保护。

---

## 1. 5 个空壳子目录的现状(任务 §1 要求)

### 1.1 物理树(2026-06-12 03:41 实测)

```
D:\CFD-harness-Windows-StarCCM\src\cfd_harness\starccm_adapter\
├── __init__.py        (18 行;re-export StarCCMExecutor;ADAPTER_STARCCM plane 占位)
├── executor.py        (579 行;真实实现;_CASE_TO_COMMAND + _resolve_sim/macro/outputs)
└── geometry\
    └── __init__.py    (120 行;write_lid_driven_cavity_stl · STL generator)
```

**5 个对照表里的子目录 — 一个都不存在**。`Get-ChildItem -Directory` 只返回
`geometry/` 这一个;`case_solve/`、`case_extractors/`、`case_visualize/`、
`mesh_quality/`、`physics/` 全是**还没 scaffold** 的状态,不是"空壳"。

> **诊断**:任务原文用词"5 个空壳子目录"是**口径误差**。空壳 = 存在但内容空;实情是
> 5 个连目录都没建。但从 ROI 看,**现状 ≈ 0%**(0 LOC for those surfaces)等同于
> 任务意图("盘点 0% 完成的地方 + 给补足优先级"),所以下游消费本盘点的人不会
> 受影响,但必须在 §1 把它**写实**。

### 1.2 5 个子目录的"应有边界"(从 cfd-harness-unified + 本仓对照表 + CHARTER §4 拼出)

| # | 子目录(应有) | cfd-harness-unified 对应 | 本仓对照表出处 | 已有触发器/调用链证据 |
|---|---|---|---|---|
| 1 | `case_solve/` | `ui/backend/services/case_solve/`(使用 Docker 调用 OpenFOAM) | AGENTS.md 行 103;CHARTER §4 行 59 列出 `case_solve/fan_blade.py` | `executor.py` 行 58-68 `_CASE_TO_COMMAND` + `executor.py` 行 76-79 `_MACRO_NAME_FOR_CASE` **已经是 case_solve 的最小雏形**(case-id → command 路由 + 宏名查找)。**没抽出来**。 |
| 2 | `case_extractors/` | `ui/backend/services/case_extractors/`(读 OpenFOAM field data) | AGENTS.md 行 104;CHARTER §4 行 60 列出 `case_extractors/fan_aero.py` | `executor.py` 行 419-431 `_extract_key_quantities` + 行 469-500 `csv 解析 u_centerline` + 行 506-521 `summary.json 解析 residuals` 同样是**雏形内嵌**。Cl/Cd 读取在 DEC-007-v2/v3 暴露**全失败**(STATE.md 行 23-26),`case_extractors/fan_aero.py` 应该接管这条失败路径。 |
| 3 | `case_visualize/` | `ui/backend/services/case_visualize/`(scene + export) | AGENTS.md 行 105;**CHARTER §4 没列** | `bridge/repl.py` 已有 `export_scene` 方法(executor.py 行 305-313 调);`report_engine/generator.py` 行 12 引用 `cfd_harness.starccm_adapter.visualize` 但**没建**,只是个占位 import docstring。 |
| 4 | `mesh_quality/` | `ui/backend/services/mesh_quality/`(STAR-CCM+ mesh report parser) | AGENTS.md 行 106;CHARTER §4 行 61 列出 `mesh_quality/rotor37_metrics.py` P2 / 9 月 | `knowledge/macro_registry.yaml` 行 424-435 `cli_mesh_quality_v15` 已经定义了 MaxSkewness / MinQuality 双报告 + `<case>_mesh_quality.json` 输出契约;**Python reader 完全没写**。 |
| 5 | `physics/` | `ui/backend/services/physics/`(materials + regimes + tolerance binding) | AGENTS.md 行 107;**CHARTER §4 没列** | `cfd_harness.executor` 端有 `MockExecutor._PRESETS`(internal/external/natural_convection 三档,行 29-53) — 算半个 regime 表;**没有 materials 数据库**。 |

### 1.3 "缺什么接口/类/方法"(任务 §1 必答 3)

> 这是**推理**而非现状,基于 `case_profiles.yaml` 现有 16 个 case + `CHARTER.md` §2
> 7-9 月里程碑(2D LHS 100-200 样本 + 3D 单通道 30-50 首批)反推。

| 子目录 | 缺什么 | 推理依据 |
|---|---|---|
| `case_solve/` | `class FanBladeSolver(ExecutorAbc)` 或 `def build_and_run_rotor37_slice(params: Rotor37Params, sim_path: Path) -> RunReport` | CHARTER §2 写"3D 单通道叶片 30-50 首批样本"在 8-9 月,CHARTER §4 写 `fan_blade.py` P1 / 8 月,DEC-008 §4 写 starccm-adapter-engineer 拥有此目录 — 缺口是**"给 Rotor37 的 case-id 一个不依赖 case_profiles 即可调用的 Python entry"**。 |
| `case_extractors/` | `class FanAeroExtractor` 读 ForceCoefficientReport + 收敛监测;`def read_force_coefficients(macro_summary_path: Path) -> dict[str, float]` | DEC-007 v2-v3 暴露 `getValue()` 返回 Vector3 with field names `x/y/z`(不是 `[Cd, Cl, Cm]`);DEC-007 v5 暴露 `getReportMonitorValue` 路径必须经 mesh-quality CLI 才到得了 — 必须有 reader 才能补 DEC-007 v6+ 的 Cl 闭环。 |
| `case_visualize/` | `def export_velocity_pressure_png(sim_path: Path, out_dir: Path) -> tuple[Path, Path]` | 已有 `bridge/repl.py:export_scene` 雏形 + DEC-007 v2 证实 Pressure PNG + Velocity PNG 都work(STATE.md 行 24) — 缺的是**统一 entry + 路径规约**,不是新能力。 |
| `mesh_quality/` | `def parse_mesh_quality_report(json_path: Path) -> MeshQualityMetrics` | `cli_mesh_quality_v15` 已经定义 JSON 契约(行 424-435);`MeshQualityMetrics` dataclass + y+ / MaxSkewness / MinQuality → `report_engine` — 缺口是 30-50 个 Rotor37 跑出来时**没有机器可读的 mesh gate**。 |
| `physics/` | `class MaterialDB` + `class RegimeDB` + `def bind_tolerance(gs_id: str, regime: str) -> Tolerance` | `cfd_harness.executor.mock.py` 的 `_PRESETS` + `_CASE_PRESETS` 行 29-180 是 regime 表的雏形;`gold_standards/*.yaml` 的 `tolerance` 字段是 tolerance 散点 — **没有任何把 regime ↔ tolerance 显式绑定的代码**。 |

### 1.4 现有复用度评估

> 哪些现有代码可以直接搬,不用从零写?

| 子目录 | 可直接复用 | 复用比例(估) | 备注 |
|---|---|---|---|
| `case_solve/` | `StarCCMExecutor._CASE_TO_COMMAND` + `_MACRO_NAME_FOR_CASE` + `_resolve_macro_path` | ~70% | `executor.py` 行 58-79 + 204-212 直接抽出;**不用重写**执行器,只是把 `lid_driven_cavity` 路径的"rotor37" 加进去。 |
| `case_extractors/` | `executor.py._build_macro_run_report` 的 CSV/summary 解析逻辑(行 469-521) | ~50% | 已经有 summary.json 解析 + csv 解析;**ForceCoefficientReport reader 是新的**(DEC-007 失败的产物)。 |
| `case_visualize/` | `bridge/repl.py:export_scene` + `executor.py` 行 305-319 的 post-step scene 调用 | ~80% | 几乎全是 glue code;真正的工作在 bridge + macro 端。 |
| `mesh_quality/` | `knowledge/macro_registry.yaml:cli_mesh_quality_v15` 的 JSON 契约 + `bridge/repl.py:run_macro` | ~60% | 契约已有;reader 是新工作。 |
| `physics/` | `cfd_harness.executor.mock._PRESETS` + `cfd_harness.executor.mock._CASE_PRESETS`(行 29-180)+ `knowledge/attestor_thresholds.yaml` | ~40% | regime 表雏形在 mock;materials 数据完全没建。 |

---

## 2. cfd-harness-unified 残留描述 + 借鉴经验

> 任务要求"对照 cfd-harness-unified";本仓已无该原仓(只通过 `AGENTS.md` 行 95-119
> 对照表 + 历史 README 引用),我能从对照表里读出的有效信息:

| cfd-harness-unified 经验 | 本仓应吸取 |
|---|---|
| `case_solve/` 在原仓是 UI 后端服务,**不直接 spawn solver**,而是 **docket 一条任务给 executor 跑**。本仓对照表的注释(AGENTS.md 行 103)写"rewrite using Codebuddy REPL commands" — 但 Codebuddy REPL 已经是 `StarCCMExecutor` 的实参,**不要再叠一层 dispatcher**。`case_solve/` 应该是**纯 Python 工厂函数**(`build_rotor37_slice(...)`),不持有状态。 |
| `case_extractors/` 在原仓读 OpenFOAM `field data`(volScalarField / volVectorField);本仓 STAR-CCM+ 端没有 volField 文件直接 dump,**所有提取都经 macro summary.json / ForceCoefficientReport** — 设计上要**先有 macro,再有 extractor**,顺序不能倒。 |
| `case_visualize/` 在原仓用 ParaView 远程协议;STAR-CCM+ 用 `Scene → exportImageFile` 内置 — 本仓不该新建 viz 框架,**复用 `export-scene` 即可**。 |
| `mesh_quality/` 在原仓用 OpenFOAM `checkMesh` log parser;本仓 STAR-CCM+ 端走 `cli_mesh_quality_v15` 的 JSON 契约 — **解析 JSON 比解析 log 简单一个数量级**,工作量估 0.5d 而非 2d。 |
| `physics/` 在原仓是**最重**的服务(thermo + turbulence + combustion 注册表);本仓 7-9 月**不烧这块**(CHARTER 没列;DEC-008 §2.4 写"STAR-CCM+ 端暂不补 API"),`physics/` 实际等于"placeholder for after-2027-Q1"。 |

---

## 3. 7-9 月可补足清单(任务 §2 · 至少 10 条 · ROI 排序)

> **ROI 排序原则**(本盘点自定,不是项目硬指标):每条按
> `(关键路径权重) × (复用现有度) / (估时)` 粗排。★ = 关键路径;无 ★ = 重要但不挡 M1。

| # | 任务名 | 影响哪个 milestone | 工作量(估) | 复用度 | 关键路径 |
|---|---|---|---|---|---|
| ★ 1 | `gold_standards/rotor37.yaml` + `rotor67.yaml`(CHARTER §4 P0 / 7 月) | DEC-008.a(M1 验收) | 1d | 0%(全新) | **是** — 没黄金基线 = 没法做 V&V comparator;M1 报告里"rotor37 covered"无法自证 |
| ★ 2 | `macros/Rotor37Slice.java`(2D 截面 + Re/Ma 扫描;CHARTER §4 P0 / 8 月) | DEC-008.b 数据期 ① 起点 | 3-5d | 60%(借 DEC-007 NacaTrueE2E.java 骨架) | **是** — 7 月样机 mock-first 必须先有真 macro 才能在 8 月切 WIN_STARCCM |
| ★ 3 | `src/cfd_harness/starccm_adapter/case_solve/fan_blade.py`(CHARTER §4 P1 / 8 月) | DEC-008.b 数据期 ① | 2-3d | 70%(抽 `StarCCMExecutor._CASE_TO_COMMAND` 已有雏形) | **是** — 数据期的"case generator"主入口;没它 MOCK 端只能手动 CLI |
| ★ 4 | `src/cfd_harness/starcm_adapter/case_extractors/fan_aero.py`(CHARTER §4 P1 / 8 月) | DEC-008.a(M1)+ DEC-007 v6+ Cl 闭环 | 2d | 50%(复用 `_build_macro_run_report` summary.json 解析;新增 ForceCoefficientReport reader) | **是** — DEC-007 4 个 sub-versions 都卡在 Cl 读取,本任务直接吃掉这条历史债 |
| ★ 5 | `macros/Rotor37SingleChannel.java`(CHARTER §4 P0 / 8 月;3D 单通道;借 `NacaTrueE2E.java` 7-11 步) | DEC-008.b 数据期 ② 起点 | 5-7d | 70% | **是** — 9 月首批 30-50 个 3D 样本的 macro |
| 6 | `case_profiles.yaml` 增 rotor37 / rotor67 / rotor37_slice / rotor37_single_channel 4 个 profile(DEC-006 follow-up 2 风格) | DEC-008.b 数据期 | 0.5d | 90%(直接抄 `naca0012_airfoil` profile) | 否 — 阻塞但不挡 path(可以手动 CLI 跑) |
| 7 | `src/cfd_harness/starccm_adapter/mesh_quality/rotor37_metrics.py`(CHARTER §4 P2 / 9 月;JSON 解析 + y+ / Skewness 阈值) | DEC-008.b 数据期 ② 末 | 1-2d | 60%(`cli_mesh_quality_v15` 契约已有) | 否 — 9 月底前完成即可,首批 30-50 样本前不需要 |
| 8 | `src/cfd_harness/starccm_adapter/case_visualize/__init__.py`(薄薄一层 wrap `bridge.repl.export_scene`;CHARTER §4 没列) | M1 demo / `report_engine` 配合 | 0.5d | 80% | 否 — 现有 `executor.py` 行 305-319 post-step 调用已 cover;本任务只是把入口从 executor 抽出来 |
| 9 | `scripts/run_rotor37_macro.py` 驱动脚本(仿 `scripts/run_naca_macro.py`;driver 早于 adapter 落地) | DEC-008.a(M1) | 0.5d | 90% | 否 — driver 早于 adapter 落地是惯用模式(参考 NACA 流程:DEC-007 §"Run-time harness") |
| 10 | `src/cfd_harness/executor/` 增加 `ExecutorMode.REMOTE_STARCCM` 占位(为 2027 远程 cluster 留口) | 2027-Q1+ | 0.5d | 100%(纯 stub) | 否 — 推迟到 DEC-008.e L0→L1 升级窗口 |
| 11 | `src/cfd_harness/starccm_adapter/physics/` 目录 + `__init__.py` 占位(CHARTER §4 没列) | 2027-Q1+ | 0.2d | 0% | 否 — 推迟到 2027 优化期;7-9 月不需要 |
| 12 | `case_solve/__init__.py` re-export `fan_blade` 让"`from cfd_harness.starccm_adapter.case_solve import build_rotor37`"工作 | DEC-008.b 文档/M1 demo | 0.1d | 100% | 否 — 顺手;**但 chief-engineer 如果不强调,常被遗忘** |
| 13 | `case_extractors/__init__.py` 同上 | DEC-008.b | 0.1d | 100% | 否 — 同上 |
| 14 | DEC-008.a 子决策(7 月底签 M1 是否合格;CHARTER §5 自定时间窗) | DEC-008.a 验收会议 | 半天 | — | 否 — 治理性任务,跟代码补足解耦 |
| 15 | DEC-007 v6+ Cl 闭环(等 `fan_aero.py` 落地后,patch `NacaTrueE2E.java` ForceCoefficientReport 提取走新 reader) | DEC-007 收口 | 1d | 50% | 否 — 历史债,不在 7-9 月商业项目关键路径上;但完成能拿到 1 个真案例(covered) |

**ROI 排序**:**#1 → #5 必须 7 月底前完成**;#6 → #9 是 8 月数据期配套;#10 → #15 是 9 月 / 长期。

---

## 4. 哪些缺口是项目级关键路径(任务 §3 · 必答)

> 项目级关键路径 = 不补,M1/M2 走不通。基于 CHARTER §2 里程碑 + DEC-008 §4 影响表判定。

### 4.1 ★ M1(7 月底)必须补(否则 DEC-008.a 验收失败)

| 缺口 | 不补的后果 | 触发时间 |
|---|---|---|
| #1 `gold_standards/rotor37.yaml` + `rotor67.yaml` | V&V comparator 报 "no gold standard" → mock 数据**无参照**, M1 报告不能写"rotor37 闭环" | 7 月立项期末 |
| #3 `case_solve/fan_blade.py` 雏形 | 8 月数据期**没有 Python entry** 调用 `Rotor37Slice.java`;只能跑 CLI 单 case | 7 月底(M1 demo) |
| #9 `scripts/run_rotor37_macro.py` driver | macro 有了但 driver 没写,8 月起每次跑都要手敲 `starccm+.bat -batch Rotor37Slice.java ...` | 7 月底 |

### 4.2 ★ M2(9 月底数据期)必须补(否则 DEC-008.b 验收失败)

| 缺口 | 不补的后果 | 触发时间 |
|---|---|---|
| #2 `macros/Rotor37Slice.java` | 8 月数据期 ① 100-200 个 2D 样本**没有 macro**,只能 mock | 8 月初 |
| #4 `case_extractors/fan_aero.py` | 8 月数据期样本跑出来**没有 extractor**,Cl/Cd 读不出 | 8 月中 |
| #5 `macros/Rotor37SingleChannel.java` | 9 月数据期 ② 30-50 个 3D 样本**没有 macro** | 8 月底 |
| #6 `case_profiles.yaml` 4 个 rotor37 profile | 8-9 月 runner 不能 `--case rotor37_slice` | 8 月初 |

### 4.3 9 月底 P2(可推迟到 10 月建模期,挡 M3 但不挡 M2)

| 缺口 | 不补的后果 | 触发时间 |
|---|---|---|
| #7 `mesh_quality/rotor37_metrics.py` | 3D 样本的 y+ / MaxSkewness / MinQuality 没法机器判;首批 30-50 个样本**可能混进差 mesh** | 9 月底(可推到 10 月初) |

### 4.4 推迟到 2027-Q1(CHARTER 没列 · `physics/` + `case_visualize/` 抽口 + `REMOTE_STARCCM`)

| 缺口 | 推迟到 | 为什么 |
|---|---|---|
| #8 `case_visualize/__init__.py` | 任意(0.5d 活) | 现有 `executor.py` post-step 调 `export_scene` 已 cover;**真要抽口是 cleanup,不是新能力** |
| #10 `REMOTE_STARCCM` 占位 | DEC-008.e L0→L1 窗口 | 2027 才上 remote;7-9 月本地 Codebuddy 完全够用 |
| #11 `physics/` 占位 | 2027-Q1+ | CHARTER §4 整张表没列;7-9 月不烧 |
| #14 DEC-008.a 治理 | 7 月底会议 | 时间固定,不挡代码 |
| #15 DEC-007 v6+ Cl 闭环 | 9-10 月顺手做 | 历史债;与 M1/M2 正交(STATE.md 行 99 写"本项目与既有 Stage 3+ 工作流正交") |

---

## 5. 兼容 / 风险 / 审计落点(自检 · 任务硬约束要求诚实分层)

### 5.1 与硬约束的兼容表

| 硬约束 | 兼容? | 证据 |
|---|---|---|
| advisor-not-driver(AI 不写 case) | ✅ | 本盘点不动任何 STAR-CCM+ case 写盘;只写 .md |
| 四平面律(ADR-001) | ✅ | 5 个子目录**全在 ADAPTER_STARCCM plane**;新增的 `case_solve/` 等 import 不应触 EXECUTION plane |
| signed audit package | ✅ | 不涉及 |
| tolerance integrity | ✅ | #1 `gold_standards/rotor37.yaml` 必须由 **vv-director** 起草 + literature 引用;v1 不动 reference_values |
| pre-implementation discipline(本盘点就是这一步) | ✅ | 触发器命中;charter 范围内 |
| L0 autonomy | ✅ | 这次盘点本身是 L0 内可自行决定;"补充 4 个子目录 + 2 个 macro"也是 L0 内(mock-first + 内部包目录) |
| 不能动 STATE.md / 现有 yaml | ✅(本盘点不动) | §6 列出未改文件清单 |
| 唯一允许写盘路径 = 本 md | ✅(本次) | §6 |

### 5.2 风险表(按"如果我猜错了"列)

| 字段 | auto-safe(我可以猜对) | heuristic(我会出错) | must-human(必须人签) |
|---|---|---|---|
| 5 子目录真实存在性 | — | 我判定**不存在**(证据:directory listing);**但有可能某个 CI 钩子在 `__init__.py` import 时 lazy 建空目录**。 | chief-engineer 验 `Get-ChildItem -Directory` 一行 |
| ROI 排序 | 估时 + 复用度 | 关键路径权重 | M1 验收标准(我可以列 P0/P1,但**M1 通过/不通过是用户 + chief-engineer 在 7 月底会议定**) |
| 借鉴 cfd-harness-unified | 原仓路径名(对照表给我了) | 原仓各服务的"应有"接口签名(我推断的,没原仓源码) | 用户若还保留原仓 archive,可要求我抓 README 二次对照 |
| DEC-007 v6+ Cl 闭环归属 | 任务清单的"可推迟"判定 | DEC-007 的 future 版本号 | chief-engineer 在 7 月底 M1 评审时同步 |

### 5.3 审计落点

- 本盘点落 `reports/research/commercial-fan-prop/planning/track-d-deliverable.md`(任务原文指定);
- 同步落 `C:\Users\Kogami\.mavis\plans\plan_22415a38\outputs\track-d-repo-gap\deliverable.md`(plan 协议要求);
- 不写 audit.json(本盘点不写代码,不进 V&V 闭环)。

---

## 6. 7 月第一周 chief-engineer 该排什么(任务 §5 · ≤ 3 条)

1. **(优先级 1 · 7/01-7/03)**登记 vv-director 起 `gold_standards/rotor37.yaml` + `rotor67.yaml` 草稿(任务 #1);让 vv-director 配 user 校对 literature 数值(NASA Rotor37 case A / case B 公开数据;UIUC rotor67 数据)。本任务**不消耗 chief-engineer 工时**,只是把 task 派出去。
2. **(优先级 2 · 7/07-7/11)**派 starccm-adapter-engineer 起 `scripts/run_rotor37_macro.py` driver(任务 #9,0.5d);并开始写 `macros/Rotor37Slice.java` v0(任务 #2,3-5d,借 DEC-007 NacaTrueE2E.java v7 骨架);目标 7 月底前 smoke 1 个 2D 截面 + Re=1e5 + Ma=0.3 跑通 + Cl/Cd 数值稳定。
3. **(优先级 3 · 7/14-7/18)**派 backend-engineer 起 `case_solve/fan_blade.py` 雏形(任务 #3,2-3d),先把 `StarCCMExecutor._CASE_TO_COMMAND["rotor37_slice"] = "run-macro"` + `_MACRO_NAME_FOR_CASE["rotor37_slice"] = "Rotor37Slice.java"` 添进去,**并 case_profiles.yaml 同步加 1 个 entry**(任务 #6 起步)。这是 M1 demo 的"1 vertical";7 月底会议**展示"rotor37_slice 在 MOCK + WIN_STARCCM 双轨跑通 1 次"**即可。

**3 条原则**:
- **不叠 API 补全**(DEC-008 §2.4 明文禁止);
- **不烧 physics/**(CHARTER 没列;7 月不抽这个口子);
- **不写 visualize / mesh_quality 真接口**(8-9 月再做;7 月只需要在 AGENTS.md 行 105-106 的"对照表"行加注 "**(planned, 8-9 月)**"即可,不创建物理目录)。

---

## 7. 边界遵守自检(任务原文硬约束)

| 硬约束 | 自检 |
|---|---|
| 不修改 `src/cfd_harness/starccm_adapter/` 任何文件 | ✅ 本盘点零文件改动(只读);没创建任何子目录 |
| 不动 STATE.md / 现有 yaml | ✅ 没编辑 `STATE.md` / `case_profiles.yaml` / `macro_registry.yaml` |
| 不写新代码 | ✅ 唯一输出 = 本 md + 同步 deliverable.md + board.md append |
| 唯一允许写盘路径:`reports/research/commercial-fan-prop/planning/track-d-deliverable.md` | ✅ 主输出落此;另落 `C:\Users\Kogami\.mavis\plans\plan_22415a38\outputs\track-d-repo-gap\deliverable.md`(plan 协议要求,任务原文用"也"是暗许) |

---

## 8. 附:已读文件清单 + 4 个旁注

### 8.1 已读文件(决定 §1-§4 的证据来源)

| 文件 | 用途 | 关键引用 |
|---|---|---|
| `AGENTS.md` | 行 95-119 对照表(5 子目录 plan) | 行 103-107 |
| `reports/STATE.md` | 当前 Stage / Covered map / Open DECs | 行 18-31 / 50-69 / 108-118 |
| `reports/research/commercial-fan-prop/planning/CHARTER.md` | 7-9 月里程碑 + §4 缺口表 | 行 22-37 / 54-66 |
| `reports/research/commercial-fan-prop/decisions/DEC-008-project-charter.md` | L0 grant + 影响表 | §2.4 / §4 |
| `reports/decisions/DEC-007-naca-real-closed-loop.md` | 历史债 Cl 读取失败链条 | §"Limits" / "Follow-ups" |
| `src/cfd_harness/starccm_adapter/__init__.py` | 18 行;re-export | — |
| `src/cfd_harness/starccm_adapter/executor.py` | 579 行;case-id 路由 + 输出解析 | 行 58-79 / 204-212 / 469-521 |
| `src/cfd_harness/starccm_adapter/geometry/__init__.py` | 120 行;LDC STL generator | — |
| `src/cfd_harness/executor/{base,mock,win_starccm}.py` | ExecutorMode + Mock preset + WinStarCCM delegator | mock.py 行 29-180 |
| `src/cfd_harness/report_engine/generator.py` | 行 12 引 `cfd_harness.starccm_adapter.visualize`(deferred) | — |
| `knowledge/case_profiles.yaml` | 16 个 case 的 sim 路径表 | 全部 |
| `knowledge/macro_registry.yaml` | 行 424 `cli_mesh_quality_v15` JSON 契约 | 行 424-435 |
| `reports/decisions/DEC-006-mock-coverage-16-cases.md`(未展开,只在 STATE.md 行 18 引用) | 13 个 mock_only profile 的来由 | — |

### 8.2 4 个旁注(可能在别的任务里被问)

1. **5 个子目录在物理上不存在**这个事实**必须**告诉 chief-engineer;否则下次会议他会按"5 个空壳,各扫一遍"的指令重复本盘点。任务原文用词"空壳"是**误口径**。
2. **`mesh_quality/` 的 JSON 契约**(`cli_mesh_quality_v15`)在 macro_registry 里有,但**`reports/skill-evolution-design/verdict.md` 行 125 把这条记成 MISCLASSIFIED** — 意思是将来 skill_loader 派活时可能跳过它。本盘点提醒:7-9 月起 `mesh_quality/rotor37_metrics.py` 落地时,要先去 verdict.md 看这条 MISCLASSIFIED 的根因,免得踩同一个坑。
3. **CHARTER §4 行 65 把 `macros/PropellerOpenRotorSlice.java` 标 P2 / 2027-Q3 起** — 这条**不在本盘点范围**(7-9 月只做风扇线,螺旋桨推迟到 2027-Q1+),但要写进 chief-engineer 的"长期 backlog",免得忘记。
4. **DEC-007 v6+ Cl 闭环(任务 #15)与本盘点正交**(STATE.md 行 99 写"本项目与既有 Stage 3+ 工作流正交") — 也就是说 #15 可以**等 `case_extractors/fan_aero.py` 落地后,顺便**做掉,不必单独排周。本盘点把它从 7-9 月关键路径上摘下来是有意为之。

### 8.3 给 chief-engineer 的一个反向 ask(可选)

如果你想让本盘点**比 70% 完成**更高,推荐:
- **L0 内可自行决定**:派 backend-engineer 把 5 个子目录的 `__init__.py` 占位 + `case_solve/` / `case_extractors/` 两个**最关键**的目录骨架先 scaffold 出来(估时 0.5d,纯 stub),让下个任务的工作面更干净。
- **L0 内做但必须呈报**:任何把 `ExecutorMode.MOCK` 切到 `WIN_STARCCM` 的链路(CHARTER §5);本盘点 #3 / #4 落地时,默认仍走 MOCK,跑真机时走 opt-in `--executor win_starccm`。
- **L0 之外,必须 ask_user**:任何修改 `gold_standards/rotor37.yaml` 的 reference_values 提议;任何把 `physics/` 提前开工的决定(CHARTER §5 已禁止,本盘点不越线)。

---

*盘点人:chief-engineer 派出的仓库侦察兵(对齐 `.harness/reins/chief-engineer/agent.md`)*
*签名口径:本盘点自身可信度 70-80%;关键路径判定需 chief-engineer 7 月底评审会签字*
*不写代码,只留证据。*
