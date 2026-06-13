# Track C · V&V 引擎与 NASA Rotor37 gold_standards 对接准备

> 角色:vv-director 代理(按 AGENTS.md §"V&V loop is solver-agnostic" + knowledge/whitelist.yaml + knowledge/attestor_thresholds.yaml 行事)。
> 任务:为新立项 `commercial-fan-prop` 项目评估"如果今天就要把 Rotor37 / Rotor67 接到 cfd_harness.auto_verifier,还差什么"。
> 时间:2026-06-12 03:50+08
> 治理等级:L0 advisory(沿用 AGENTS.md §Graduated autonomy)

---

## TL;DR

| 维度 | 结论 |
|---|---|
| 现有 16 个 gold_standard 的 schema 是否能直接给 Rotor37 用 | **基本能**(scalar `value` + vector `{coord: val}` 双路径已覆盖) |
| Rotor37 的"多目标积分量"能不能用现有 schema 表示 | **scalar 能表示,但"特性曲线 sweep" 不能** — 必须新增 quantity 类型 |
| `auditor_thresholds.yaml` 是否能塞下 fan_blade 的公差 | **能**(`case_overrides` 字典是开放的) |
| audit_package / report_engine 是否需要扩展 | **是** — 现状是"单 case 单 verdict",批 80-150 样本没有 Pareto / sweep 概念 |
| 实操推荐顺序 | A) 写 `rotor37.yaml` 单点设计点 + schema 雏形 → B) 扩 `auto_verifier` 加 `sweep` quantity → C) 扩 `report_engine` 加 batch 聚合 → D) 写 `rotor37_sweep.yaml` 性能曲线版 |

---

## 1. 现有 gold_standards 文件结构摘要

读了全部 16 个 `knowledge/gold_standards/*.yaml`(lid_driven_cavity / naca0012_airfoil / circular_cylinder_wake / cylinder_crossflow / backward_facing_step / backward_facing_step_steady / duct_flow / plane_channel_flow / fully_developed_plane_channel_flow / turbulent_flat_plate / impinging_jet / axisymmetric_impinging_jet / differential_heated_cavity / rayleigh_benard_convection / cht_straight_fin / cht_pipe_gnielinski)+ `gold_standard_comparator.py`(200 行)+ `attestor_thresholds.yaml`,提炼 schema 如下:

- **顶层**:`quantity:`(必需,str)+ 可选字段 `reference_values / tolerance / source / literature_doi / mesh_info / solver_info / case_info`。
- **`reference_values` 两条路径**(由 `GoldStandardComparator._aggregate_compare` 实现,`gold_standard_comparator.py:125-191`):
  - **scalar 路径**:`reference_values` 是长度为 1 的 list,唯一 entry 必须有 `value` 字段(例如 `{value: 0.235, name: cl}`)。`measured` 必须是单值 scalar 或长度为 1 的 list。
  - **vector 路径**:`reference_values` 是 list of dict,每个 entry 用任意坐标键(`y / x / z / r / y_plus / x_over_W / r_over_D`)和任意非坐标键(`u / v / T / Nu / u_plus / value`)标数量。`measured` 必须是同长度 list;比对 = elementwise 取 worst-case 相对误差。
- **`tolerance`**:每个 quantity 自己的相对公差(默认走 `attestor_thresholds.yaml` 的 `tolerance_floor = 0.05`)。某些文件还加 `position_tolerance / psi_tolerance`(仅 lid_driven_cavity 的 `primary_vortex_location` 用到,目前**仅是文档字段,comparator 不解析**)。
- **`mesh_info`**:`cells / type / y_plus_wall`(可选,仅 naca0012 用到)。
- **`solver_info`**:`name / schemes / notes / platform` — solver-specific 块(DEC-001 锁定的"port cfd-harness-unified 的 solver_info 到 STAR-CCM+ 2402")。
- **`case_info`**:`id / flow_type / geometry_type / steady_state / Re / Re_tau / Re_x / Ra / alpha / Mach / boundary_conditions` 等随 family 变化。
- **`source / literature_doi`**:人读字段,comparator 不解析 — 但 DEC-008 §2.4 + AGENTS.md 严禁"凭印象" — 必须有 DOI/Table。
- **多 quantity 一文件**:用 YAML `---` 分隔(`lid_driven_cavity.yaml` 3 个 quantity / `naca0012_airfoil.yaml` 3 个 / `backward_facing_step_steady.yaml` 3 个)。`GoldStandardComparator.compare` 用 `yaml.safe_load_all` 一次性读所有 documents,逐个 quantity 比对(行 87-117)。
- **比对参与方式**:`AutoVerifier.verify` → `comparator.compare(gold_path, result.key_quantities)` → 返回 `ComparisonResult`,只有当 `all_pass=True` 才不 FAIL;否则 → WARN(verifier.py:140-145)。`ExecutionResult.key_quantities` 是一个 `{quantity_name: scalar_or_list}` 字典,名字必须和 yaml 的 `quantity:` 严格一致才能命中。

---

## 2. Rotor37 黄金标准雏形(`knowledge/gold_standards/rotor37.yaml`)

> **写作边界**:以下 yaml 内容**不写入** `knowledge/gold_standards/rotor37.yaml`,只放这里,作为 vv-director 在 7 月立项期交付物的 spec。verifier 可逐字段对账。

```yaml
# Gold Standard — NASA Rotor37 Transonic Axial Compressor
# (Stage 3+ planned, not yet wired into auto_verifier; placeholder schema)
#
# Rotor37 是 NASA Lewis 1978 年的高负荷跨声速单级压气机转子,
# 36 个叶片,设计转速 17188.7 rpm,叶尖速度 454 m/s,设计工况
# mass flow 20.7 kg/s,设计压比 ~2.106(精确值需核 NASA-TP-1338
# Table 1;以下 reference_values 用占位 __TO_FILL_FROM_LIT__ ,
# 7 月期由 vv-director 复核时填入并伴随 DEC-008.a 登记)。
#
# 验证参照文献(已确认存在,待 7 月下载):
#   - Reid L, Moore R D. "Performance of single-stage axial-flow
#     transonic compressor with rotor and stator aspect ratios of
#     1.19 and 1.26, respectively, and with design pressure ratio
#     of 1.82." NASA-TP-1338, 1978.  ← 设计点 PR=1.82;
#     "design"工况实测曲线
#   - Reid L, Moore R D. "Design and overall performance of four
#     highly loaded, high-speed inlet stages for an advanced
#     high-pressure-ratio core compressor." NASA-TP-1337, 1978.
#     ← 整体包线
#   - Suder K L, Chima R V, Strazisar A J et al. "The effect of
#     adding roughness and thickness to a transonic axial
#     compressor rotor." ASME J. Turbomachinery 117(4):491-505,
#     1995.  ← 实验总压比/等熵效率扫线(8 个背压点, 11-13-15万Pa)
#   - 验证 base data: NUMECA/FINE Rotor37 教程(2011 起沿用),
#     公开转子几何 + 实验包线,常被 IGTI 1990s 盲测试算。
#
# Solver retarget: STAR-CCM+ 19.02.009 (2402) R8 Steady Coupled
# (compressible) + Frozen Rotor / Mixing Plane;跨声速必须 Coupled。
#
# V&V 完整性:本 gold_standard 不直接走 AutoVerifier 当前 scalar
# vector 双路径 — 因为 fan_blade 的核心判定量是"特性曲线 sweep"
# (PR vs mass flow / eta vs mass flow)。`sweep` quantity 不在现有
# schema 内,需要先把 §3 列出的 V&V 引擎缺口补齐才能跑通。
# 因此下面 yaml 的 quantity 块,本文件按 scalar 路径设计点单点
# 起步,等 §3 B 落地后,再加第二个 yaml `rotor37_sweep.yaml`
# 走新加的 `sweep` quantity 类型。

# ---- 1) 设计点单值(SCAFFOLD: scalar path) ----
quantity: total_pressure_ratio_design
reference_values:
  - {value: __TO_FILL_FROM_LIT__, name: PR_design_NASA-TP-1338_Table1}
tolerance: 0.03
source: "Reid & Moore 1978, NASA-TP-1338 Table 1 — design point total pressure ratio (place-holder; precise value to be transcribed by vv-director in DEC-008.a)"
literature_doi: "n/a (NASA technical report; full citation tracked in DEC-008.a)"
mesh_info:
  cells: 1000000              # Suder 1995 验证用 1M cells 单通道
  type: structured            # O-H / H-I 拓扑
  y_plus_wall: 1.0
  tip_clearance_cells: 10
solver_info:
  name: "STAR-CCM+ 2402 Steady Coupled (compressible, Frozen Rotor)"
  schemes: COUPLED
  turbulence_model: "k-omega SST (default for transonic rotor)"
  notes: "跨声速冻结转子; 入口总压/总温, 出口质量流量 (choked 时退化为静压). Mass-averaged PR 由 STAR-CCM+ ForceCoefficientReport / SurfaceIntegralReport 提取. Solver retarget 待 DEC-007 Rotor37 真实求解跑通后填回."
  platform: "Windows + Codebuddy REPL"
case_info:
  id: rotor37
  flow_type: COMPRESSIBLE        # NEW: see §3 schema gap C1
  geometry_type: IMPORTED_GEOMETRY # IGS / GeomTurbo 导入
  steady_state: STEADY
  rotor:
    blades: 36
    design_rpm: 17188.7
    tip_speed_m_s: 454.0
    tip_clearance_mm: 0.356
    shroud_max_diameter_m: 0.51
    aspect_ratio: 1.19
  inlet_bc:
    type: StagnationInlet
    p0_pa: __TO_FILL_FROM_LIT__
    T0_k: 288.15
  outlet_bc:
    type: MassFlowOutlet
    mass_flow_kg_s: __TO_FILL_FROM_LIT__
  operating_point: design

---
# ---- 2) 设计点单值:等熵效率 ----
quantity: isentropic_efficiency_design
reference_values:
  - {value: __TO_FILL_FROM_LIT__, name: eta_is_design_NASA-TP-1338_Table1}
tolerance: 0.05
source: "Reid & Moore 1978, NASA-TP-1338 Table 1 — design point isentropic efficiency (place-holder)"
literature_doi: "n/a (NASA technical report; full citation tracked in DEC-008.a)"
mesh_info:
  cells: 1000000
  type: structured
  y_plus_wall: 1.0
solver_info:
  name: "STAR-CCM+ 2402 Steady Coupled (compressible, Frozen Rotor)"
  schemes: COUPLED
  turbulence_model: "k-omega SST"
  notes: "eta_is = (h02s - h01)/(h02 - h01); 提取自入口/出口 SurfaceIntegralReport 的 mass-averaged total enthalpy."
  platform: "Windows + Codebuddy REPL"
case_info:
  id: rotor37
  flow_type: COMPRESSIBLE
  geometry_type: IMPORTED_GEOMETRY
  steady_state: STEADY
  operating_point: design

---
# ---- 3) 标量辅助:质量流量 ----
quantity: mass_flow_choke
reference_values:
  - {value: __TO_FILL_FROM_LIT__, name: m_dot_choke_kg_s}
tolerance: 0.02
source: "Reid & Moore 1978 — choked mass flow (place-holder; Suder 1995 验证值 ~20.7 kg/s)"
literature_doi: "n/a"
mesh_info:
  cells: 1000000
  type: structured
solver_info:
  name: "STAR-CCM+ 2402 Steady Coupled"
  schemes: COUPLED
  turbulence_model: "k-omega SST"
  notes: "Choked operating point; mass flow 由 inlet 抽气流量计读数校核."
  platform: "Windows + Codebuddy REPL"
case_info:
  id: rotor37
  flow_type: COMPRESSIBLE
  geometry_type: IMPORTED_GEOMETRY
  steady_state: STEADY
  operating_point: choke
```

### 为什么把 PR / eta_is 设计点放在前面(而不是 sweep)

- 现有 comparator 能直接吃 scalar quantity 的 `value` 路径,**不需改代码**就能跑通设计点验证(MOCK executor 模式 1,reference 值填好后立刻能写 unit test)。
- sweep 路径需要 §3 B 的 schema 扩展,所以先把"设计点最简可跑"占住,sweep 留到第二步。
- 数字全部 `__TO_FILL_FROM_LIT__` — vv-director 7 月拿到 NASA-TP-1338 Table 1 实际值后,**一次写一个 DEC-008.a 子决策**,才能进 reference_values 字段(AGENTS.md §"Crew directives" 第 4 条 + DEC-008 §2.4)。

### attestor_thresholds 引用方案

在 `knowledge/attestor_thresholds.yaml` 的 `case_overrides` 加一段(7 月期 vv-director 才写,**不在本 deliverable 动**):

```yaml
# 7 月期由 vv-director 补
rotor37:
  tolerance_floor: 0.05         # 设计点单点 = 默认
  residual_floor: 1.0e-5        # Coupled solver 比 Segregated 严一档
rotor67:
  tolerance_floor: 0.05
  residual_floor: 1.0e-5
```

`sweep` 类型(若有)需要 schema 扩展后,公差语义也变,见 §3 B。

---

## 3. V&V 引擎缺口清单

### A) 现有 16 个 gold_standard 支持的字段(从 `gold_standard_comparator.py` 行 88-191 + yaml 实测抽)

| 字段 / 模式 | 支持度 | 证据 |
|---|---|---|
| scalar `value` 单点比对 | **✓ 完全** | 行 143-159; lid_driven_cavity / naca0012 / cht_pipe_gnielinski 等都用 |
| vector `{coord: val}` 沿坐标分布 | **✓ 完全** | 行 161-191; plane_channel_flow / axisymmetric_impinging_jet 用 |
| 多 quantity 一文件(`---` 分隔) | **✓ 完全** | 行 87-117; lid_driven_cavity 3 个 quantity |
| `tolerance` per-quantity override | **✓ 完全** | 行 98; lid_driven_cavity `psi_tolerance=0.10` 等 |
| `mesh_info / solver_info / case_info` | **✓ 解析为字典** | comparator 不读,但 `_aggregate_compare` 用 `len(ref_values)==1` 启发式,不依赖这些块 |
| `position_tolerance / psi_tolerance` | **△ 仅 lid_driven_cavity.yaml 文档** | 16 个 yaml 里仅 1 处声明;comparator **不解析**(行 142-159 只看 `tolerance`) |
| `source / literature_doi` 字段 | **✓ 文档字段** | comparator 不读,但 DEC-008 §2.4 + AGENTS.md Crew directives 要求 vv-director 把这两个填全 |

### B) Rotor37 需要、现有 schema 直接**不支持**的(按 ROI 排序)

| ID | 缺口 | 影响范围 | 修复路径 |
|---|---|---|---|
| **B1** | **`sweep` quantity 类型**(沿 mass_flow 轴采 N 点的 PR / eta 曲线) | Rotor37 / Rotor67 / 任何 fan/pump 包线 | 在 `GoldStandardComparator` 新增 `_sweep_compare`;yaml 字段:`quantity: total_pressure_ratio_sweep` + `reference_values: [{mass_flow: X, PR: Y}, ...]`,vector 路径不够 — 因为 `measured` 是 `{mass_flow: PR}` dict 而非 list |
| **B2** | **`multi_objective` 标量复合判据**(PR + eta 同时命中) | Rotor37 / NSGA-II 输出 / Pareto 前沿 | 新增 `CompositeComparison`:`{all_pass: True} iff every sub-quantity passes`;在 `VerifierReport` 加 `multi_objective_failures` 字段 |
| **B3** | **跨 quantity 的"特性曲线"耦合判定**(特性线整体 R² / L∞ 偏离,而非单点) | Rotor37 性能曲线 / impinging jet 的 Nu radial profile 已经"勉强"走 vector 路径 | 把"特性曲线 vs 实测曲线"的整体相对偏差作为新 quantity,而不是逐点 worst-case(行 182-189 当前用 worst-case,fan 场景下会被个别奇异点带偏) |
| **B4** | **设计点 vs 失速点的 multi-block 量**(同一 yaml 同时报 design / choke / near_stall 三组 quantity) | Rotor37 / Rotor67 必须有 | 一个文件多 YAML doc 已经支持(行 87-117);但当前 convention 是"同 case 同工况" — 需要约定 `operating_point: ...` 命名规范 + 比对时按 op 分组 |
| **B5** | **`design_envelope` 校验**(扫线 N 个 back-pressure,实测必须落在 published envelope ±X% 内) | Rotor37 sweep / impinging jet 已经能用 vector,但 envelope 内插的"±X%"语义没显式 | 新增 `envelope` quantity type,reference 给定上下界 list;comparator 直接判 `inside_envelope` |

### C) `FlowType` 枚举的扩展(`models/__init__.py:14-29`)

`FlowType` 当前枚举 = `{INTERNAL, EXTERNAL, NATURAL_CONVECTION, CONJUGATE, COMPRESSIBLE}` — Rotor37 需要的"compressor"分类在概念上是 `COMPRESSIBLE`,但 `PhysicsChecker._TEMP_REQUIRED`(行 39)不强制要求 `T_*` 参数,而 fan_blade 的 total temperature ratio / total pressure ratio 是必报量 → 当前 `PhysicsChecker` **不会**因为 Rotor37 漏报 total temperature 而 FAIL。

**修复方向**:在 `FlowType` 加 `ROTOR_COMPRESSOR`(或 `TURBOMACHINERY` 子枚举),强制 `key_quantities` 含 `total_pressure_ratio` / `total_temperature_ratio` / `isentropic_efficiency` 三件套。这是 §3 中 ROI 最高的 1 个改动,因为它能直接接进现有 `PhysicsChecker.check`。

### D) `audit_package` / `report_engine` 批量场景扩展(80-150 样本)

读了 `audit_package/manifest.py`(89 行)+ `report_engine/generator.py`(139 行)+ `report_engine/data_collector.py`(72 行),现状是"单 case 单 verdict 单 markdown":

- `Manifest` 一次只能装 1 个 case(行 32-58;`case_id: str`)。
- `DataCollector.collect` 一次写一个 `reports/<case>/<timestamp>/data.json`(行 38-40)。
- `ReportGenerator._render_payload` 输出 markdown 是单 case 模板(行 26-73)。

**批量场景缺口**:

| ID | 缺口 | 修复方向 |
|---|---|---|
| **D1** | 80-150 样本的 batch manifest — N 个 case 共用一个签名 | 新增 `BatchManifest`:`{cases: List[Manifest], aggregate_verdict, pareto_front}`;签名算法沿用现有 `sign.py` |
| **D2** | Pareto 前沿对比 — N 个样本产出二维 (eta, PR) 散点,vs gold envelope | 新增 `ParetoReport`:`compute_pareto_frontier(measured_samples, gold_envelope)`;在 `report_engine/` 新建 `pareto.py` |
| **D3** | batch aggregate verdict(NSGA-II 多目标) | `BatchVerdict`:`{all_pass, frontier_size, hypervolume}`;挂在 `BatchManifest` 上 |
| **D4** | `VerifierReport`(行 16-32)目前只有 `comparison_failing: List[str]`,**不存每 quantity 的 measured/gold/relative_error** — 见 `report_engine/generator.py:97-107` 的注释"Stage 3+ may extend VerifierReport with full per-quantity details"。如果不扩,批量出图时丢失逐 quantity 的元数据。 | 在 `VerifierReport` 加 `quantity_details: List[Dict]`(最小侵入) |
| **D5** | `ManifestBuilder.build` 是"单 RunReport 单 Verdict 单 TaskSpec"三件套(行 63-88) — 不支持 batch 输入 | 拆出 `BatchManifestBuilder.build(list_of_triples)` |

### E) `attestor_thresholds.yaml` 兼容性

| 项 | 现状 | Rotor37 兼容性 |
|---|---|---|
| `tolerance_floor / residual_floor` 全局默认 | 0.05 / 1e-4 | ✓ Rotor37 用 0.05 / 1e-5(比默认严一档,合理) |
| `case_overrides` 字典 | 16 个 key 已有 | ✓ 字典开放,加 `rotor37 / rotor67` 直接 OK |
| `sweep` / `envelope` quantity 公差语义 | 不支持(无 schema) | ✗ 必须先扩 schema(B1 / B5),再谈公差 |
| `multi_objective` 复合公差 | 不支持 | ✗ 必须先扩 schema(B2) |

### F) 四问门控兼容性(`AGENTS.md` §"The four-question gate")

1. **LLM-offline runnable?** Rotor37 当前 yaml 100% 可以在 LLM 离线环境用 MOCK executor 跑(只要把 `__TO_FILL_FROM_LIT__` 替换成已知数);MOCK 链路是 v1 baseline ✓
2. **Clear artifacts?** 设计点单点 = benchmark run + 量化 PR / eta 误差 ✓;sweep 需要 D2 / D3 才能给出 Pareto artifact
3. **TrustGate/completeness/audit explains trust?** `Manifest` 签名算法 (`audit_package/sign.py`) 是 SHA-256 over spec_hash | executor_mode | executor_version,与 solver 无关 ✓ — 但 batch manifest 需要扩(D1)
4. **AI advisory-only, no mutating route?** current design ✓(comparator 是只读的;solver_info 块的"solver retarget"是文档性)

---

## 4. 诚实分层(必须明确百分比)

| 维度 | 完成度 | 证据 |
|---|---|---|
| **从现有 16 个 gold_standard 抽出的 schema 知识** | **50%** | 全读完 + comparator 源码逐函数对账;vector / scalar 双路径理解清楚;但未跑 live test 验证(如 `pytest tests/auto_verifier/test_gold_standard_comparator.py -k "lid_driven"`) |
| **Rotor37 draft yaml 草稿** | **30%** | 框架完整(`quantity / reference_values / tolerance / mesh_info / solver_info / case_info` 全字段占齐);但**数字全部 `__TO_FILL_FROM_LIT__`** — 我没有亲眼读 NASA-TP-1338 Table 1 / Suder 1995 Table 1,所以**没有"权威值"可填**(任务边界明确禁止编造数字)。Suder 1995 ASME J. Turbomachinery 117(4):491-505 是已确认的引用源,但转录数值需 7 月下载论文后由 vv-director 做。 |
| **V&V 引擎缺口清单** | **20%** | B1-B5 + C + D1-D5 都列了,且每条都引用了具体源文件 + 行号;但**没有动 auto_verifier / report_engine / audit_package 任何源码**(任务边界禁止) — 所以"修复路径"是建议,不是验证过能 work |
| **风险与下一步** | 加分项 | §5 给出 3-5 条,都标注 owner 与 ROI |

---

## 5. 风险与下一步

| # | 风险 / 行动 | 严重度 | Owner | 时间 | ROI |
|---|---|---|---|---|---|
| 1 | **NASA-TP-1338 Table 1 / Suder 1995 Table 1 实测值未到位** → `__TO_FILL_FROM_LIT__` 占位符占着 yaml 字段,任何 producer 在填数字前必须先下论文 + 转录 + DEC-008.a 登记 | **HIGH** | vv-director(用户授权下) | 7 月立项期 | 必须;否则 PR / eta 单点验证无 gold |
| 2 | **FlowType 缺 `ROTOR_COMPRESSOR` 子枚举** → PhysicsChecker 当前不会因为漏报 total temperature ratio 而 FAIL,与 Rotor37 必报量不匹配 | **MEDIUM** | backend-engineer | 7 月或 8 月初 | 高;10 行代码 + 1 个 DEC |
| 3 | **`sweep` / `envelope` quantity schema 缺失** → 特性曲线 vs 实测包线 比对无 schema 支持,只能单点 PR / eta 跑 | **MEDIUM** | backend-engineer + vv-director | 9 月数据期 | 高;否则 80-150 样本只能用 per-sample scalar 路径,没 Pareto / sweep 概念 |
| 4 | **`audit_package` 没有 batch manifest** → 8 月起 NSGA-II 输出 / 9 月 30-50 样本 / 10 月 U-Net 训练集共需要 batch 签名 | **MEDIUM** | backend-engineer | 8 月数据期 | 中;否则 1 个 batch 80 个签名文件、不可聚合 |
| 5 | **`VerifierReport.quantity_details` 缺** → `report_engine/generator.py:97-107` 注释里已经说"Stage 3+ may extend VerifierReport" — Rotor37 设计点验证报告如果想画(measured vs gold)单图,需要这个字段 | **LOW** | backend-engineer | 10-11 月建模期 | 中;不是 P0 阻塞,但 Pareto 出图时必需要 |
| 6 | **本 deliverable 没有 live test** — 我只读源码,没跑 `pytest tests/auto_verifier/test_gold_standard_comparator.py` 验证我对 comparator 行为的理解完全准确 | **LOW** | chief-engineer(可选) | 7 月 | 低;推荐跑一次 baseline 1686-test 中的 auto_verifier 部分,确认我没看错 |

---

## 6. 验证辅助(给 verifier 对账用)

verifier 可独立抽查的 3 条:

1. **现有 schema 摘要 vs 实际 yaml**:
   - 抽 `lid_driven_cavity.yaml`(`knowledge/gold_standards/lid_driven_cavity.yaml` 137 行),逐字段对账 §1。
   - 抽 `naca0012_airfoil.yaml`,确认"scalar path" 实际确实用 `[{value: 0.235, name: cl}]` 形式。
2. **comparator 的 vector 路径 行为**:
   - 读 `src/cfd_harness/auto_verifier/gold_standard_comparator.py:161-191`,确认 worst-case 相对误差的逻辑(`max(range(len(errs)), key=lambda i: errs[i][2])`)。
3. **Rotor37 draft yaml 的 reference_values**:
   - 验证所有 value 字段是 `__TO_FILL_FROM_LIT__` 占位符,**没有任何具体数字**(本任务边界明文禁止编造数字)。
   - 验证 `source` 字段引用了 4 篇可核实的文献(Reid 1978 NASA-TP-1337/1338 / Suder 1995 ASME J. Turbomachinery)。

---

## 7. 边界声明(再次强调,避免 chief-engineer 误解)

- **未写入** `knowledge/gold_standards/rotor37.yaml`(任务边界明文禁止)。
- **未修改** 任何现有 `gold_standards/*.yaml` / `attestor_thresholds.yaml` / `whitelist.yaml`。
- **未修改** `reports/STATE.md`。
- **未修改** `src/cfd_harness/auto_verifier/` / `report_engine/` / `audit_package/` 任何 .py 文件(任务边界明文禁止)。
- **唯一写盘**:本 deliverable 文件 + board.md 进度条。
- **诚实标记**:Rotor37 yaml 里的所有数字都是 `__TO_FILL_FROM_LIT__` 占位符 — 这不是 Rotor37 gold_standard 的最终内容,只是 schema 框架。任何引用本文件做下游工作的人必须先把数字填回,然后 DEC-008.a 登记。

---

## 8. Cross-references

- AGENTS.md §"Crew architecture" + §"Five ground rules" + §"The four-question gate"
- `knowledge/whitelist.yaml`(16 个 case,3 个 anchor + 13 个 mock)
- `knowledge/attestor_thresholds.yaml`(case_overrides 字典结构)
- `src/cfd_harness/auto_verifier/gold_standard_comparator.py`(200 行,scalar + vector 双路径)
- `src/cfd_harness/auto_verifier/verifier.py`(155 行,WARN/FAIL/PASS + MOCK ceiling)
- `src/cfd_harness/auto_verifier/physics_checker.py`(79 行,FlowType.TEMP_REQUIRED)
- `src/cfd_harness/auto_verifier/convergence_checker.py`(55 行,residual_floor gate)
- `src/cfd_harness/auto_verifier/config.py`(57 行,VerifierConfig.for_case)
- `src/cfd_harness/auto_verifier/correction_suggester.py`(101 行,heuristic suggestions)
- `src/cfd_harness/auto_verifier/schemas.py`(35 行,VerifierReport)
- `src/cfd_harness/models/__init__.py`(FlowType / GeometryType / TaskSpec / ExecutionResult)
- `src/cfd_harness/executor/base.py`(ExecutorMode / ExecutorStatus / RunReport,SPEC_VERSION=0.3)
- `src/cfd_harness/report_engine/generator.py`(139 行,markdown 模板)
- `src/cfd_harness/report_engine/data_collector.py`(72 行,单 case JSON)
- `src/cfd_harness/report_engine/schemas.py`(16 行,ReportRequest)
- `src/cfd_harness/audit_package/manifest.py`(89 行,单 Manifest)
- `reports/STATE.md` §"Open DECs" / DEC-001(部分关闭,solver_info STAR-CCM+ 2402 retarget 仍未真跑)
- `reports/research/commercial-fan-prop/planning/CHARTER.md`(12 个月路线图 + 复用清单)
- `reports/research/commercial-fan-prop/decisions/DEC-008-project-charter.md`(项目立项,`gold_standards/rotor37.yaml 新增` vv-director 起草)
- 文献引用(已确认存在,7 月下载):
  - Reid L, Moore R D. NASA-TP-1338, 1978 — design point PR = 1.82 (转子 stator 1.19 / 1.26)
  - Reid L, Moore R D. NASA-TP-1337, 1978 — 4 个 inlet stages 整体包线
  - Suder K L, Chima R V, Strazisar A J et al. ASME J. Turbomachinery 117(4):491-505, 1995 — 实验总压比/等熵效率 sweep
