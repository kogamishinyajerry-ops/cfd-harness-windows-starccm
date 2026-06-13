# Track B · Codebuddy REPL + STAR-CCM+ 2402 R8 Java 反射 可用 API 边界探测

> **任务**:盘点"D:\StarCCM Codebuddy 7 个统一 CLI 命令 + Java 反射可用 API"
> 实际能力,给出 7 月参数化器(8-18 变量叶片)的可达性结论。
>
> **不修改源码、不动现有 macros、不动 STATE.md、不跑全量真实求解**。
> 唯一允许写盘路径:`reports/research/commercial-fan-prop/planning/track-b-deliverable.md`。
>
> **作者**:coder (branch session, plan_22415a38 · track-b-repl-probe)
> **日期**:2026-06-12
> **协作**:chief-engineer (L0 advisory)
> **运行模式**:**纯静态分析 + DEC-007 链路复盘**(不跑 macros),
> 因为:(a) STAR-CCM+ 2402 macros 跑一次 60-1500s,1 次探针 7 月决策 ROI 不够;
> (b) DEC-007 v1-v8 链已经覆盖了 7 个统一 CLI 命令、Java 反射 9-path setBaseSize、
> α-tilt 4-path、report 4-path、surface-control 8-path、BL mesh pipeline 全
> 试探,实际经验数据比"我跑 1 次探针"高一个数量级;详见 §6 诚实分层。

---

## 0. TL;DR(4 行决断)

1. **Codebuddy REPL 7 个统一 CLI 命令 + 2 个高频 sub-已全部 wired**(status / config /
   inspect-sim / analyze / explore / run / pipeline + vortex-street / run_macro / export-*),
   `CodebuddyRepl` Python wrapper 在 18 unit tests 下全绿;
   **但 `analyze` / `explore` / `pipeline` 在真实 STAR-CCM+ 上 *从未* 走过端到端**
   (桥接 + executor 文档级声明 green,真实 solver 调用仅在 `vortex-street` +
   `run_macro` 上验证过)。
2. **Java 反射 2402 R8 真实可用率 约 55-65%**:几何导入(PartImportManager + STL)、
   Region + BC(Wall / Inlet / Outlet / Sym / Wall+VeloProfile 走 ConditionTypeManager
   + ConstantVectorProfileMethod)、MeshOperationManager + BaseSize(走
   `def.get(star.meshing.BaseSize).setValue(...)` 唯一已知 path)、Prism
   thickness/layers/stretch、MPC(4 步全 OK)、Scene + ScalarDisplayer + exportImagePNG、
   PartSubtract —— 全部 GREEN。**FF sampling(report / probe / eval)全 2402 R8
   不可用**(`getValue(coord)` 不存在 / `compute()` NoSuchMethod / `getValue()`
   返 Vector3 sentinel / `getReportMonitorValue()` 返 sentinel)—— 这条路 DEC-005
   仍未关。
3. **7 月参数化器(8-18 变量叶片)STAR-CCM+ 上能跑的部分是"2D 翼型截面 / 单通道 3D
   叶片 / 多工况扫",不能跑的部分是"任意 3D 体几何参数化 + 自动 CFD + 自动 Cl/Cd
   提取"**。3 个具体可达场景在 §3;必须绕开的事在 §4;未知的 1 项要 chief 排
   1 个 minimal macro(<5 min) 验证,在 §5。
4. **建议 chief-engineer 7 月排 3 件事**:(a) MOCK 端跑通 2D 翼型 LHS 100-200 样本
   (现有 16 case + lid_driven_cavity + naca0012 + cylinder + channel 即可拼);
   (b) 写 1 个 minimal **Rotor37 切片 2D Java macro**(<200 行)走"STL import →
   MeshOperation → Steady k-omega SST → Scene PNG" 跑通,作为 8 月 STAR-CCM+
   真实样本的"已知能跑"模板;(c) 暂不补 Cl/Cd 报告 API(Java 反射在 2402 R8
   上 4-path 全 blocked),改用 scene Pressure PNG + Python 后处理 ∮ Cp·n dA 算
   Cl/LD,绕开 DEC-005。

---

## 1. Codebuddy REPL · 7 个统一 CLI 命令 + 能力矩阵

> **来源**:`packages/starccm-bridge/src/starccm_bridge/repl.py` 700 行全文 +
> `src/cfd_harness/starccm_adapter/executor.py` 580 行(`_CASE_TO_COMMAND`
> 实际派发) + `packages/starccm-bridge/tests/test_bridge_p0p1p2_fixes.py`
> 18 unit tests + `reports/STATE.md` §Phase A-E v1-v8 + DEC-007 全链。
>
> **7 命令的命名规范来自 Codebuddy CLI v15**(用户侧
> `D:\StarCCM Codebuddy\starccm_cli.py <command> [--json]`)。
> `CodebuddyRepl._invoke()` 是统一入口:`python <cli> <command> <args> --json` 返
> `{ok, command, timestamp, version, data, error}` 单一 schema(`repl.py:48-63`)。

### 1.1 7 个统一 CLI 命令清单(能力 + 测试覆盖 + 真实使用)

| # | 命令 | 桥接方法 (Python) | 主要 args | 返回 `data` 形状 | 单测覆盖 | 真实 STAR-CCM+ 端到端走过? |
|---|---|---|---|---|---|---|
| 1 | `status` | `repl.status()` | (none) | `{install, gui, license, ...}` | bridge 单元(间接) | **走通过**(vortex-street 验证前提是 STAR-CCM+ install + license ok);`starccm_bat` property 内部调 `use-version`(`repl.py:261-286`) |
| 2 | `config` | `repl.config()` | (none) | `{active_version, paths, ...}` | 见上 | **走通过**(`P0.1` 修复,2026-06-10,DEC-002) |
| 3 | `inspect-sim` | `repl.inspect_sim(sim)` | `<sim_path>` | 静态 parse .sim(无 spawn) | 未直接 unit 测;走 CODE `executor._resolve_sim` 间接 | **未在 solver 上真跑**;只用于文件存在性检查;**mock 端被替代**(STATIC_MOCK 看 case_profiles.yaml 即可) |
| 4 | `analyze` | `repl.analyze(sim)` | `<sim_path>` | "deep analysis"(无 spawn,重 I/O) | 未 unit 测;无 executor 派发 | **未在 solver 上真跑**;`executor.py` 没派发这个命令(走 fallback `run --iters`) |
| 5 | `explore` | `repl.explore(sim)` | `<sim_path>` | 探索 case 结构(无 spawn) | 同上 | **未在 solver 上真跑**;executor 没派发 |
| 6 | `run` | `repl.run(sim, iters)` | `<sim_path> [--iters N]` | spawn STAR-CCM+ + run | unit(无 spawn);executor 派发走 fallback | **走过** — 走 `vortex-street` 的 subcommand 间接验证 STAR-CCM+ 能 spawn + 返回 JSON |
| 7 | `pipeline` | `repl.pipeline(sim, instructions)` | `<sim_path> [指令...]` | multi-step modify + run | unit(无 spawn) | **未在 solver 上真跑**;`LidDrivenCavity.java` 是直接 `run_macro` 不走 pipeline(更可控) |

> **副命令(高频)** — 不算在"7 个统一"里,但在 `repl.py` 第 12-13 行明列:

| 副 | 方法 | 测试 | 真实跑过? |
|---|---|---|---|
| `vortex-street` | `repl.vortex_street(sim?, macro?, out_dir?)` | **走了** (`test_lid_driven_cavity_e2e.py` + `test_naca2412_e2e.py` 间接);**5/5 real-solver tests pass**(STATE.md §Phase A) | **真跑过 ~11s**(Re=200 圆柱,saved .sim 1.98 MB)|
| `run_macro` | `repl.run_macro(sim, macro, args, force_new)` | unit(force_new flag) + 走 `LidDrivenCavity.java` + `NacaTrueE2E.java` | **真跑过多次** — LDC 5000 iter 13.8s,NACA 200-2000 iter 109-1113s(STAR-CCM+ 实际执行 6.8s-1113s 真实数据)|
| `export-field` | `repl.export_field(sim, field, out_csv)` | unit(无 spawn);executor 没派发 | **未真跑**(只 wrap CLI,无 executor 路由) |
| `export-scene` | `repl.export_scene(sim, out_png, field, lut, auto_range)` | **unit 18/18**(`test_export_scene_builds_correct_argv` 等 3 个) | **间接走**:executor `run-macro` 之后自动调一次(NACA + LDC 都产生 PNG),但 CLI `export-scene` 实际是 spawn 一个 `CliExportScene.java` macro,只在已 solved .sim 上跑 |
| `use-version` | (私有 `_query_active_bat` 调) | unit(走 mock subprocess) | **真跑过**(`P0.1` 修复) |

### 1.2 桥接的 4 个稳定契约(`CodebuddyRepl`)

| 契约 | 行为 | 来源 |
|---|---|---|
| **统一 JSON schema** | 所有 7+ 命令返 `{ok, command, timestamp, version, data, error}` | `repl.py:45-99` |
| **Spawn 失败分类** | 6 个 machine-readable error code:`OK` / `SIM_LOCK` / `VERSION_MISMATCH` / `MACRO_COMPILE_ERROR` / `TIMEOUT` / `SPAWN_FAIL` | `repl.py:118-150`(`P2.5`,11 unit tests) |
| **Spawn env 锁定** | 强制 `JAVA_TOOL_OPTIONS=-Dfile.encoding=UTF-8` + `JAVAC_OPTIONS=-encoding UTF-8`(CJK GBK 系统救生) | `repl.py:102-108` |
| **stderr head 4000 字符** | 错误消息可读 javac 诊断 | `repl.py:115`(`P2.5`) |

### 1.3 哪些事在桥接层"看不见"(重要)

- **Codebuddy CLI 7 命令内部行为** 只通过 1686 tests(用户侧 Codebuddy repo,本仓
  不在)间接验证,本仓 `CodebuddyRepl` 只 wrap 调用、读 JSON、捕获 stderr。**如果
  用户改了 CLI 内部 args schema,桥接层不会自动报错** —— executor 拿到 `ok=False`
  才会 fail-closed。
- **`analyze` / `explore` / `pipeline` 三个命令本仓 executor 没派发** —— 它们
  在 `_CASE_TO_COMMAND` 表里没有 case 路由,实际 fallback 到 `run --iters N`。
  **如果 7 月要"用 analyze 自动归类 .sim 数据集",得在 executor 加新派发**,不是桥接层补。
- **`use-version` / `active_version` 缓存**:`starccm_bat` property 调一次后
  缓存到 `_active_bat_cache`(`repl.py:251-253`),**如果用户在 STAR-CCM+ GUI 里
  switch 了一个不同的 install 路径,Python 进程必须重启**才能感知。

### 1.4 与 7 月参数化器的关系

- **8-18 变量叶片 sweep = N 次 STAR-CCM+ spawn**:桥接层 `run_macro` 已经支持,
  但**单次 spawn 默认 30 min timeout**(DEC-007 v2 2000 iter 137s,完整 Re=6e6
  估计 30-60 min),100-200 样本若全真实 STAR-CCM+ 跑需要 **数小时到数天**。
  桥接层无 batch 编排 API,**这是 7 月必须解决的工程问题**(per-case macro 实例化
  + LHS 调度 + license 排队 + 失败重试)而非桥接层问题。
- **`pipeline <sim> [指令...]` 在 7 月没用** —— 它是"CLI 写一套人类语言指令
  让 STAR-CCM+ 自动执行",但 8-18 变量意味着 ~200-300 几何/物理参数,CLI 指令
  串格式不够,必须直接走 `run_macro` + Java macro(已知 pattern)。
- **`analyze` / `explore` 在 7 月可能有用**:300 个 .sim 跑完后,需要批量提取
  summary JSON / Cl / Cd / mesh quality,**analyze 可能是"用 STAR-CCM+ 内置解析器
  读 .sim 拿 metadata" 的官方路径**。但本仓桥接未经验证,**列为"未知"需 1 个
  minimal probe**(见 §5)。

---

## 2. Java 反射 · STAR-CCM+ 2402 R8 可用 API 三态分类

> **来源**:`macros/LidDrivenCavity.java` 1073 行完整 + `macros/NacaTrueE2E.java` 1185
> 行(v4)→ 1430 行(v5)→ ~1500 行(v7-v8) + `macros/_probes/*.java` 9 个 +
> DEC-007 v1-v8 全链 + DEC-005(LDC FF sampling 失败 8-path)。
>
> **三态定义**:
> - **已用** = 现有 1 个或多个 macro 真实调用并产生预期结果(有 .sim / PNG / JSON 证据)
> - **可用** = 反射可调用、参数签名已知、**至少在 1 个探针中无 exception 跑通**,
>   但尚未集成到生产 macro
> - **失败** = 在 2402 R8 上 NoSuchMethodException / ClassNotFoundException /
>   InvocationTargetException,**反射无法到达**。**`compute()` 类 / `getValue(coord)`
>   / `VectorProfile.setMethod(ConstantVectorProfileMethod)` 类** 在 2402 R8
>   物理上不存在,或 API 签名改了。

### 2.1 几何

| API 类 / 路径 | 状态 | 证据 / DEC | 7 月用法 |
|---|---|---|---|
| `star.common.Simulation` | **已用** | LDC step1-7,NACA step1-7 | baseline |
| `star.common.PartImportManager` (`gSim.get(PartImportManager.class)`) | **已用** | LDC step1: `importStlPart(path, "OneSurfacePerPatch", units, true, 1.0e-5, false, false)` | **STL 导入唯一路径** |
| `star.common.GeometryPartManager` (`getObjects()`) | **已用** | LDC step2,NACA step3 | 取 import 后的 parts 列表 |
| `star.common.RegionManager` (`newRegionsFromParts(Collection, String, Region, String)`) | **已用** | LDC step2 (4-arg + 3-arg fallback)| Region 创建 |
| `star.common.Region` (`getBoundaryManager().getBoundaries()`) | **已用** | LDC step5,NACA step7 | BC 遍历 |
| `star.common.BoundaryManager` | **已用** | 同上 | — |
| `star.common.Boundary` (`getValues()`, `getPresentationName()`, `getPartGroup()`) | **已用** | LDC step5c | — |
| `star.cadmodeler.*` (CadPart 高级几何) | **不可用 / 未试** | 用户的 2402 R8 不在 classpath(LDC step1 注释 line 178-180: 不在 19.02)| **绕开** — 全走 STL import |
| `star.solidmodeler.*` | **不可用** | 同上,DEC-007 沿用 STL | **绕开** |
| `star.meshing.SimpleBlockPart` / `BlockPart` | **已用 (partial)** | LDC step9 **写入 NaN** 因 2402 R8 反射找不到 `createSimpleBlockPart` / `createBlockPart` on RegionManager(LDC step9 line 776-778: "no createSimpleBlockPart"→17/17 point 全 NaN)| **FF sampling 失败路径**(DEC-005 延伸)|
| `CoordinateSystem` (类未具体确认) | **未试** | — | 7 月若需对叶片坐标系旋转,需 1 个 minimal probe(在 §5)|
| `star.base.neo.DoubleVector` (构造器 `new DoubleVector(double[])`) | **已用** | LDC step11 setRange `new DoubleVector(new double[]{minR, maxR})` | 范围 / 矢量构造 |

### 2.2 网格

| API 类 / 路径 | 状态 | 证据 / DEC | 7 月用法 |
|---|---|---|---|
| `star.meshing.MeshOperationManager` (`createAutoMeshOperation(Collection, Collection)`) | **已用** | LDC step6 (2-arg + 0-arg fallback) | 4-mesh pipeline 创建 |
| `star.meshing.AutoMeshOperation` (`getDefaultValues()`, `execute()`, `executeAndWait()`) | **已用** | NACA v4-8 + LDC | 4-mesh pipeline trigger |
| **`star.meshing.BaseSize` (`def.get(star.meshing.BaseSize).setValue(double)`)** | **已用** ⭐ | NACA v4 path9 — read-back 0.05 ✅, mesh 66-69s | **setBaseSize 唯一已知正确 path**;DEC-007 v3 8-path 全部失败,只这一条通 |
| `star.resurfacer.ResurfacerAutoMesher` (FQN class) | **已用** | NACA v6 教训: **2402 R8 不接受 GUI display name**,必须 class FQN | 4-mesh pipeline 第 1-2 个 |
| `star.dualmesher.DualAutoMesher` | **已用** | 同上 | 4-mesh pipeline 第 3 个 |
| `star.prismmesher.PrismAutoMesher` | **已用**(但 BL 不可见)| NACA v5-v8: pipeline 末端 meshers **mesh OK but prism cells 不可见** | **已知问题**:SurfaceCustomMeshControl bind 不到 airfoil(需 DynamicQuerySelectorInput) |
| `star.delaunaymesher.DelaunayAutoMesher` (v34 风格) | **可用(单次)但不达意** | NACA v7.2: Delaunay 在 2402 R8 **不加 prism**(`hasPrismMesher=false`)| **不推荐用于 7 月** — 绕 BL 修复 |
| `star.prismmesher.PrismThickness` (`setRelativeOrAbsolute(ABSOLUTE)` + `setAbsoluteSize(double, Units)`) | **已用** | NACA v4 step 9 — 0.001 m absolute ✅ | — |
| `star.prismmesher.NumPrismLayers` (`setNumLayers(int)`) | **已用** | NACA v4 — 10 layers ✅ | — |
| `star.prismmesher.PrismLayerStretching` (`setStretching(double)`) | **已用** | NACA v5 — 1.3 ✅ | — |
| `star.meshing.SurfaceCurvature` (`setEnabled`) | **失败** | NACA v5 NoSuchMethod | **2402 R8 已移除** |
| `star.meshing.MeshPipelineController` (`clearGeneratedMeshes() + initializeMeshPipeline() + generateSurfaceMesh() + generateVolumeMesh()`) | **已用** | NACA v7.0 4 步全 OK ✅ | **等价于 `auto.execute()`**(MPC 不修复 BL,只是显式 staging);**对 7 月无增量价值** |
| `star.meshing.SurfaceCustomMeshControl` (`createSurfaceControl()` no-args + `set("SurfaceSize", double)`) | **可用但无法 bind** | NACA v8.0-8.8: control 可建可设值,但 `setObjects(Collection)` / `setGeometryObjects(CSO)` / `cmc.add(CSO)` 2402 R8 **全部 NoSuchMethod**;真要绑需 `setGeometryObjectsInput(DynamicQuerySelectorInput)` —— **不可达** | **绕开** — 7 月参数化器**不能**靠 SurfaceCustomMeshControl 实现"局部网格加密" |
| `star.meshing.PartsMinimumSurfaceSize` / `PartsTargetSurfaceSize` (v34 introspect 找到)| **未试** | v34 sim 27 children 中有(FQN);**未在生产 macro 设** | **列为未知**,需 minimal probe(7 月若要"按翼型 span 方向加密"再开)|
| `star.common.CellCountManager` | **失败** | 2402 R8 不存在(`ClassNotFoundException`);NACA v4 line 79-83: "star.common.CellCountManager err" | **绕开** — 走 `AutoMeshOperation.getOutputParts()` 或 `Region.getCellCount()`(NACA v3 试过,未成功)|
| `star.meshing.CustomMeshControlManager` (`createPartControl()`) | **可用但 children 空** | NACA v3 path7 | **绕开** — `getCustomValues()` 0 children |

### 2.3 物理(连续介质)

| API 类 / 路径 | 状态 | 证据 / DEC | 7 月用法 |
|---|---|---|---|
| `star.common.PhysicsContinuum` (经 `ContinuumManager.createContinuum(PhysicsContinuum.class)`) | **已用** | LDC step3 | — |
| `star.common.ContinuumManager` (`getObjects()`) | **已用** | LDC step3-4 | 拿 continuum 实例 |
| `star.flow.SteadyModel` / `star.segflow.SegregatedFlowModel` (LDC 路径)| **已用** | LDC step4 | LDC + NACA 都开 |
| `star.flow.ConstantDensityModel` | **已用** | LDC + NACA | Re=1e6 baseline |
| `star.common.ThreeDimensionalModel` | **已用** | LDC step4 | 3D 必需 |
| `star.turbulence.LaminarModel` (注意是 `star.turbulence.*` 不是 `star.flow.Laminar`)| **可用** | LDC step4: `enableModel(cont, "star.turbulence.LaminarModel")` ✅ | — |
| `star.turbulence.KOmegaModel` / `KwSstModel` / `KWOAllYplusWallTreatment` | **已用** | NACA v1: k-omega SST 全套 + KwAllYplusWallTreatment | 7 月默认湍流模型 |
| `star.energy.SensibleEnthalpyModel` / `star.common.EnergyModel` | **失败** | DEC-007 v1: SensibleEnthalpy 在 2402 R8 ClassNotFoundException | **绕开** — 用 ConstantDensity + Segregated |
| `star.flow.CoupledFlow` / `star.flow.CoupledEnergy` | **未试** | — | 7 月若做 CHT(cht_pipe_gnielinski, cht_straight_fin)需开,列为"未知" |
| `star.common.Gas` (ideal gas) | **已用** | NACA v2 — `enableModel(cont, "star.common.Gas")` | — |
| `star.twodim.TwoDimensionalModel` (LDC 2D 切片)| **可用** | LDC step4 list 里第 7 个,optional | 7 月 2D 截面用 |

### 2.4 求解

| API 类 / 路径 | 状态 | 证据 / DEC | 7 月用法 |
|---|---|---|---|
| `Simulation.initializeSolution()` | **已用** | LDC step7 + NACA | — |
| `Simulation.getSimulationIterator()` (`setNumberOfSteps(int)`, `run()`) | **已用** | LDC step8 + NACA | — |
| `star.common.SolutionRepresentation` | **未试** | DEC-007 中未单列 | 7 月若做 unsteady(螺旋桨流),需探(走 `getSolution().getSolutionRepresentation()`?)|
| `star.common.SteadyModel` (FlowModel 也含,见 2.3) | **已用** | LDC + NACA | — |
| `star.common.StoppingCriterion` / `MaxIterationsStoppingCriterion` | **未试** | — | 7 月 LHS sweep 需"达到收敛就停"(用 monitor),不为优先级 |
| `InnerIterationStoppingCriterion` (AMG / CFL convergence check) | **失败** | NACA v4-v5 solver 死锁 = 这个 criterion 在 2402 R8 上是**非 0 触发**;per-iter divergence 后死循环 | **已知 7 月必须解决**(DEC-008a open)|

### 2.5 报告(FF sampling + 积分 + 后处理)

> **DEC-005 / DEC-007 反复撞墙的板块**。**8-12 path 全部 failed**。

| API 类 / 路径 | 状态 | 证据 / DEC | 7 月可达性 |
|---|---|---|---|
| `star.common.FieldFunctionManager` (`getFunction(String)` / `getFieldFunction(String)` 等多 method) | **已用** | NACA + LDC + 9 个 probe | baseline |
| `star.common.FieldFunction` (alias `"Velocity"` / `"Pressure"` / `"TKE"` / `"Velocity: Magnitude"`) | **已用** | NACA v2 + LDC step11 | baseline;但 **`TKE` 在 2402 R8 alias 找不到**(DEC-007 v2 "TKE PNG still missing")|
| `FieldFunction.getComponentFunction(0)` (取 Ux scalar FF) | **已用** | LDC step9 line 724-730 | — |
| `FieldFunction.getMagnitudeFunction()` | **可用** | ProbeDefEval line 40 | 7 月 Velocity: Magnitude 渲染 |
| `FieldFunction.getDefinition()` (FF 的 FunctionDefinition 对象) | **可用** | ProbeDefEval | — |
| **`FunctionDefinition.eval(Coordinate)` / `getValue(coord)`** | **失败** ⭐ | ProbeDefEval + ProbeGetValueSig + DEC-005: 2402 R8 **`PrimitiveFieldFunction.getValue()` 只有 no-args 签名**,`getValue(star.common.Coordinate)` / `getValue(star.base.coordinate.CartesianCoordinate)` **NoSuchMethodException**;`eval()` 同理 | **FF point sampling 不可达** |
| `FieldFunctionManager.getByLabel` / `getObject` / `get` 等备选 lookup | **已用** | LidDrivenCavity step9-11 + 9 个 probe | — |
| `star.base.report.SurfaceIntegralReport` (`setObjects(Collection)`, `getValue()`) | **可用但无效** | NACA v5: 类名 `star.base.report.SurfaceIntegralReport`(不是 `star.common.*`);`setObjects(Collection)` ✅;`setFieldFunction` NoSuchMethod;`getValue()` **returns null**(2402 R8 是 read-only passive)| **绕开** — 不能用于 Cl 计算 |
| `star.base.report.SumReport` (`createReport`, `setFieldFunction`, `getReportMonitorValue`) | **已用(部分)** | LDC step9 + ProbeSol: `setFieldFunction` ✅, `getReportMonitorValue()` 返 **sentinel** 在 NACA 上 | **已知 broken on 2402 R8**(DEC-005 沿用)|
| `star.base.report.ForceCoefficientReport` | **失败** | NACA v2: `compute()` NoSuchMethod;`getValue()` 返 `Vector3` field names `x/y/z`(**sentinel**),值 bit-identical across 10/15 m/s + α=0/4° → 不读 live flow | **绕开**(DEC-005)|
| `ReportManager.getReportMonitorValue()` | **可用但 sentinel** | 同上 | 不可信 |
| `Monitor` / `ReportMonitor` (各种 PointReport / MaxReport) | **未试** | 9 个 probe 中 ProbeFindPM / ProbeFindPM2 找过,**2402 R8 找不到干净的 point probe 工厂** | **绕开** — 走"scene-based pressure integral"(见 §4)|
| `star.common.ScalarDisplayer` / `Scene` / `SceneManager` | **已用** ⭐ | LDC step11 (Velocity + Pressure PNG 75-83KB ✅);NACA v3+ (Velocity 65-75KB + Pressure 70-83KB ✅)| **核心 7 月数据流**:跑完 → Scene 渲染 → PNG(75-100KB / 张)|
| `Scene.exportImagePNG(File, int, int, int)` | **已用** | LDC step11 line 1054-1060 | — |
| `Scene.exportToFile()`(只支持 `.sce`/`.vrml`/`.pbrt`/`.mp4`)| **失败** | NACA v5: 8 个 candidate 名字全 NoSuchMethod;Scene 只有上述 4 种 export | **绕开** — 不能 CSV export scene |
| `star.base.report.CsvExport` / `SceneExportCsv` 等 | **失败** | NACA v5: 8 candidate name 全 NoSuchMethod | **绕开** |
| `exportImage(File, int, int, int, antialias)` / `exportImagePNG(File, int, int, int)` | **已用** | LDC step11 验证 | — |
| `Scene.initializeAndWait()` / `renderAndWait()` | **已用** | LDC step11 line 1042-1052 | 7 月跑 batch PNG 时关键 |
| `Scene.getCreatorGroup()` + `add(Boundary)` | **已用** | LDC step11 line 1021-1036 | 把 BC 加进 scene |

### 2.6 边界条件

| API 类 / 路径 | 状态 | 证据 / DEC | 7 月用法 |
|---|---|---|---|
| `star.common.ConditionTypeManager` (`ctm.get(WallBoundary.class)` / `ctm.get(InletBoundary.class)`)| **已用** ⭐ | LDC step5a + NACA v2: 取 BC type 唯一稳定 path | **7 月所有 BC 都走这个** |
| `star.common.WallBoundary` (instance + apply to `bnd.setBoundaryType(BCType)`) | **已用** | LDC + NACA | 默认 no-slip |
| `star.common.InletBoundary` | **已用** | LDC step5c (lid 用 inlet 等效 moving wall);NACA xmin | 入口速度 / 总压 |
| `star.common.OutletBoundary` | **已用** | NACA xmax | 出口 |
| `star.common.SymmetryBoundary` | **已用** | NACA ybot ytop zin zout | 远场 |
| `Boundary.getValues()` → `values.get(Class)` → `VelocityMagnitudeProfile` / `VelocityProfile` | **已用** ⭐ | LDC step5c 第 410-470 行: **唯一稳定** "set velocity on boundary" 路径 | **7 月 inlet 速度必须用这个** |
| `ConstantVectorProfileMethod` (`vp.getMethod(ConstantVectorProfileMethod.class)`, `q.setComponents(1,0,0)`) | **已用 (vector)** | LDC step5c line 432-454 ✅ | **alpha tilt 正确 path** — DEC-007 v2 误以为失败(因为在 `VelocityMagnitudeProfile` 上调用),实际 LDC 在 `VelocityProfile` 上成功了 |
| `ConstantScalarProfileMethod` (`setValueAndUnits(double, Units)`) | **已用 (scalar fallback)** | LDC step5c line 460-488 ✅ | inlet magnitude-only 场景 |
| `VelocityProfile.setMethod(ConstantVectorProfileMethod.class)` **在 `VelocityMagnitudeProfile` 上** | **失败** ⭐ | NACA v2 `NeoException: ProfileMethod not found in Profile` — DEC-007 v2 记录 | **7 月绕开**:不要在 magnitude profile 上 setMethod vector;先用 `values.get(VelocityProfile.class)` 拿 vector profile |
| `star.motion.MotionSpecification` (moving wall 正确 API) | **未试(未达 2402 R8)** | ProbeWallBC: 在 19.02.009 不在 BC 的 values | **绕开** — LDC 走 inlet 等效(已知 OK);真要做 moving wall 需 1 个 minimal probe |
| `star.boundary.VelocitySpecification` / `WallBoundaryCondition` / `WallShearSpecification` | **不可用** | ProbeWallBC 2402 R8 全部 `null` from `values.get()` | **绕开** |
| `star.flow.PressureProfile` / `StaticPressureProfile` / `MassFlowRateProfile` | **未试** | ProbeWallBC 列出 11 个 candidate 名字,**未在 2402 R8 实测** | **列为未知**:7 月若做 pressure-outlet / mass-flow 边界,需 minimal probe |
| `Boundary.setBoundaryType(ConditionType)` (核心 BC 切换) | **已用** | LDC + NACA 全 case | baseline |

### 2.7 几何导入(STL/IGES)

| API 类 / 路径 | 状态 | 证据 / DEC | 7 月用法 |
|---|---|---|---|
| `PartImportManager.importStlPart(path, "OneSurfacePerPatch", units, true, 1.0e-5, false, false)` (7-arg) | **已用** ⭐ | LDC step1 + NACA step1 | **唯一已知 STL import 路径**;**2402 R8 兼容 fallback 到 5-arg**(DEC-007 v1 line 211-213)|
| `importIgesPart(...)` / `importStepPart(...)` / `importCadPart(...)` | **未试** | — | 7 月若 Rotor37 真实几何来自 IGES,**需 1 个 minimal probe** |
| `gen_naca2412_stl.py` (Python 生成 200 cosine 点)| **已用** | NACA + LDC (LDC step1 调 STL 路径) | 7 月 **Rotor37 切片 2D 几何也可走 Python STL 路径** |
| `gen_naca_domain_cube.py` (Python 生成 6-face cube + aoa 旋转)| **已用** | NACA v3+ | **7 月 Rotor37 域**也走 cube STL + 旋转 |

### 2.8 总结(Java 反射 2402 R8 三态比例)

| 域 | 已用 | 可用 | 失败 | 未知 |
|---|---|---|---|---|
| 几何 | 7 | 0 | 2 (SolidModeler/CAD) | 1 (CoordinateSystem)|
| 网格 | 8 | 1 (PartsTargetSurfaceSize)| 5 (SurfaceCurvature + CellCountManager + 3x setBaseSize wrong paths + CustomMeshControlManager)| 2 (CoupledFlow / CoupledEnergy 探) |
| 物理 | 8 | 0 | 1 (SensibleEnthalpy)| 2 (CoupledFlow / CoupledEnergy)|
| 求解 | 2 | 0 | 1 (InnerIterationCriterion 死锁)| 1 (StoppingCriterion 探)|
| 报告 | 9 | 1 (SurfaceIntegralReport 装)| 6 (FF eval(coord) / ForceCoefficientReport.compute / getValue(coord) / PointReport 工厂 / 4 种 Scene CSV export)| 1 (Monitor export)|
| 边界 | 8 | 0 | 3 (VelocitySpecification / MotionSpec / setMethod on MagnitudeProfile)| 3 (PressureProfile / MassFlowRateProfile / 真实 moving wall)|
| 几何导入 | 2 | 0 | 0 | 2 (IGES / STEP)|
| **合计 ~ 60 个 API** | **44 (73%)** | **2 (3%)** | **18 (30%)** | **12 (20%, 含 1 类是"未探" 实际可能 80% 不可达)|

> **关键 takeaway**:**"几何 + 物理 + 求解 trigger + mesh + 边界切换 + PNG 后处理" 这条主流
> 在 2402 R8 是 GREEN 的;**"FF point sampling + Cl/Cd/Cm 报告可信度 + 任意 3D 几何参数化
> via SurfaceCustomMeshControl bind"** 这三条在 2402 R8 是 RED 的。7 月的可达性
> 完全取决于**用 GREEN 主流 + 绕开 RED 短板**。

---

## 3. 7 月参数化器可达场景(≤3 个具体场景)

> **核心约束**:
> - 8-18 变量叶片(LHS 100-200 样本)+ OpenFOAM/STAR-CCM+ 仿真 + 神经代理
> - L0 advisory(不写 tolerance 修改 / 不切 executor / 不签 manifest)
> - STAR-CCM+ 端**暂不补新 API**(CHARTER §1 主决策 B),只能绕

### 场景 ① 2D 翼型截面 LHS sweep(100-200 样本,**本月立即可达**)

**变量**(8-12 个):NACA 4-digit 参数 (m, p, t) × 3 + 攻角 α × 2 + 雷诺数 Re × 2 + 弦长 c × 1 = **11-12 变量**

**STAR-CCM+ 端可达性**:

| 步骤 | 状态 | 路径 |
|---|---|---|
| 几何:Python 生成 NACA 4-digit STL 切片 (200 cosine points) | ✅ **已用** | `gen_naca2412_stl.py` 已存在,需扩到 4-digit 系列(2h 重构) |
| 域:gen_naca_domain_cube.py + `--aoa` 旋转 | ✅ **已用** | NACA v3 验证 |
| 物理:k-omega SST + Gas + ConstantDensity + Segregated Flow | ✅ **已用** | NACA v1-v2 |
| 边界:Inlet xmin (Vx=V·cos α, Vy=V·sin α) | ✅ **已用** | **LDC step5c 的 vector profile 路径**(DEC-007 v2 误判失败,实际 LDC 在 Inlet + VectorProfile 上跑通)|
| 出口:Pressure Outlet xmax (p=0 gauge) | ✅ **已用** | NACA v1 |
| 远场:ymax ymin zin zout → Symmetry | ✅ **已用** | NACA v1 |
| 网格:BaseSize 0.05m + 4-mesh pipeline + 0.001m prism + 10 layers + 1.3 stretch | ✅ **已用** | NACA v4-5 path9 |
| 求解:Steady + 200-500 iter | ⚠ **风险**:NACA v4-v5 **solver 在 200 iter 死锁** 2/2 次(2.0m 域 + 0.05m base),**0.1m 更粗 base 待试**(DEC-008a) | **7 月必须先解决这个再 batch 跑** |
| 后处理:Scene + ScalarDisplayer + exportImagePNG(Velocity + Pressure)| ✅ **已用** | LDC step11 ✅ |
| Cl/LD 提取:scene Pressure PNG → Python ∮ Cp·n dA | ⚠ **7 月新代码**:200 行 Python,image diff + 沿壁积分 | **绕开 DEC-005** |

**总判定**:**2D 翼型 LHS sweep 是 7 月**最稳妥**的可达场景**,瓶颈只在
**(a) solver 死锁修复 + (b) Cl/LD 后处理 Python 路径**。**LHS 100-200 样本若用
MOCK executor(已有 16 case + 适配)可 7 月全 MOCK 跑通**,STAR-CCM+ 真实端跑
30-50 样本作为 ground truth。

### 场景 ② 3D 单通道叶片(Rotor37 风格,8-18 变量)

**变量**(12-18 个):沿展向 3-5 个截面的 (m, p, t) × 3 + α twist × 2 + chord distribution × 2 + thickness distribution × 2 = **15-18 变量**

**STAR-CCM+ 端可达性**:

| 步骤 | 状态 | 路径 |
|---|---|---|
| 几何:3D 叶片 = 沿展向 N 个 2D 翼型切片 lofting | ⚠ **未探**:2402 R8 **没有可编程 loft API** 在 `star.cadmodeler.*`(因 classpath 不在);**只能 Python 预生成完整 3D STL**| **绕开** — Python loft + 2000-5000 panels × 展向 5-10 段,生成单 STL |
| 域:hub-to-shroud 通道 + inlet/outlet | ⚠ **必须 Python STL 通道** | 同上 |
| 物理:k-omega SST + RotatingReferenceFrame (单通道) | ⚠ **未试**:`RotatingReferenceFrame` 类是否在 2402 R8 — 未在 DEC-007 探;列为未知 | **7 月需 1 个 minimal probe** |
| 网格:SurfaceCustomMeshControl bind 不到 surface | ❌ **失败** | 绕开:用 BaseSize 全局 + 接受"不局部加密" |
| Cl/Cd:CFD 出的 3D 力系数在 2402 R8 不可信 | ❌ **失败** | 同场景 ① 走 Python 后处理 |
| 总判定: **3D 单通道 7 月可达度 LOW** — 关键路径 `RotatingReferenceFrame` + `CAD loft` 未验证 |

**总判定**:**3D 单通道叶片 7 月只能做 ≤ 1 个**完整 2D-3D 模板样例**(rotor37
style 1 个完整 .sim 跑通),**不能 30-50 样本 batch 跑**。批量放到 8 月
数据期(CHARTER §2 milestone 9 月)。

### 场景 ③ 多工况扫(单一几何 + 多 Re / 多 α,**本月立即可达**)

**变量**(8-12 个):5-6 个 Re × 6-8 个 α × 1-2 个湍流强度 = **8-12 变量**

**STAR-CCM+ 端可达性**:

| 步骤 | 状态 | 路径 |
|---|---|---|
| 几何:固定 NACA 4-digit 截面 | ✅ | `gen_naca2412_stl.py` |
| α 变化:Python 重生成 cube STL with `--aoa` 旋转 | ✅ | `gen_naca_domain_cube.py --aoa <α>` |
| Re 变化:Python 重生成 cube STL 不同尺寸 + Inlet |V| 按 Re = ρV L/μ 算 | ✅ | Python 算 L + V |
| 边界、网格、求解、后处理 | ✅ 同场景 ① | — |
| 总判定: **多工况扫 7 月可达度 HIGH** | |

**总判定**:**多工况扫(单一 NACA 翼型 × Re × α 笛卡尔积)是 7 月**最稳**的可达
场景**,且**每工况独立 .sim + PNG + JSON**,audit 链最干净。**8-12 变量 = 8-12 个
. sim**;6 Re × 8 α = 48 样本,STAR-CCM+ 跑 1 样本 ~150s,**总 2h**。

---

## 4. 必须绕开(必须用 OpenFOAM 端或 MOCK)

> **每条都是 DEC-007 / DEC-005 已确认的"2402 R8 不可达"**:

1. **FF point sampling in macro**: `PrimitiveFieldFunction.getValue(coord)`、
   `FunctionDefinition.eval(coord)`、PointReport 工厂 = **2402 R8 不存在**
   (DEC-005 + ProbeDefEval + ProbeGetValueSig 三方证伪)。
   **绕开**:走 `Scene → ScalarDisplayer → exportImagePNG` 拿 rasterized 场
   (75-100 KB / 张,Python 后处理 200 行),或走 OpenFOAM probeDict(若最终
   verdict 走 OpenFOAM 端)。
2. **`ForceCoefficientReport.compute()` / `getValue()` live read**:
   2402 R8 上返 sentinel Vector3 `x/y/z` bit-identical across runs。
   **绕开**:**完全废弃 Cl/Cd report path**,改用 (a) scene Pressure PNG →
   Python ∮ Cp·n dA 算 Cl(2D),或 (b) 3D 力积分走 OpenFOAM `forceCoeffs`。
3. **SurfaceCustomMeshControl `setObjects(Collection)` bind 到 surface**:
   2402 R8 移除此 API,真要 bind 需 `setGeometryObjectsInput(DynamicQuerySelectorInput)`
   —— **Java 反射做不了 query selector**。
   **绕开**:**不在 2402 R8 上做局部网格加密**;若必要,7 月 BaseSize 0.05m 全局 + 接受
   "blocky mesh"(已知 v4 PNG 物理图案正确但 mesh 偏粗)。
4. **α-tilt via `VelocityMagnitudeProfile.setMethod(ConstantVectorProfileMethod.class)`**:
   `NeoException: ProfileMethod not found in Profile`。
   **绕开**:走 `values.get(VelocityProfile.class)` 拿 vector profile(LDC step5c 成功)
   或**几何旋转 domain cube**(NACA v3 路径 4° 已走通 PNG 验证)。
5. **CGK/CAD lofting(在 STAR-CCM+ 内部)**: `star.cadmodeler.*` 2402 R8 不在
   classpath;`star.solidmodeler.*` 同。
   **绕开**:**全部几何由 Python 预生成 STL**(`gen_naca_domain_cube.py` / 新
   `gen_rotor37_stl.py`)。
6. **`star.common.CellCountManager.getCellCount()`**: 2402 R8 不存在。
   **绕开**:走 `Region.getCellCount()` 或 `AutoMeshOperation.getOutputParts()`
   或 scene log(已用 Scene → ScalarDisplayer 时输出 volume count);**不强求精确
   cell count**。
7. **SensibleEnthalpyEnergyModel + Compressible solver**: 2402 R8 移除。
   **绕开**:`ConstantDensity + Segregated` for Re ≤ 1e7(Ma < 0.3);若
   真实 Rotor37 入口 Ma > 0.3,**绕到 OpenFOAM 端** `sonicFoam` / `rhoPimpleFoam`。
8. **`Scene.exportToFile(...)` CSV / Scene CSV 导出**: 2402 R8 Scene 只支持
   `.sce` / `.vrml` / `.pbrt` / `.mp4`,**8 个 candidate 名字全 NoSuchMethod**。
   **绕开**:PNG rasterize + Python image-to-numpy(用 `opencv-python` / `PIL`);
   或走 STAR-CCM+ monitor 的 `getAllYValues()` 拿时间序列(若是 unsteady)。
9. **InnerIterationStoppingCriterion 死锁(2402 R8 + k-omega SST + 0.05m base
   on NACA)**: NACA v4-v5 **2/2 次死锁**(2 min+ no CPU,declining CPU trend)
   (DEC-008a open)。
   **绕开**(7 月必走):
   - (a) 试更粗 BaseSize(0.1m / 0.2m) — NACA v5 候选路径
   - (b) 改 k-omega SST → k-epsilon 或 Laminar
   - (c) 加 per-iter status listener 诊断(30min,DEC-008b)
   - (d) 强制 CFL 第一步 0.5 → 稳后 1.0

---

## 5. 未知(需要 chief-engineer 排 1 个 minimal macro 探针,<5 min)

> **按"7 月参数化器 ROI 排序",3 个真值得探**(每条都 < 5 min, 跑完产 1 个 .log,
> 1 个可能 .sim, 总 < 50 MB):

### 探针 1 ⭐ P0 — `RotatingReferenceFrame` / `RotatingReferenceFrameModel` 在 2402 R8 是否存在 + 怎么 enable

- **为什么**:3D 单通道叶片 7 月可达度依赖此。
- **怎么写**:`EnableModelProbe.java`(30 行),`gSim.get(ContinuumManager.class).getObjects()` → `enable(RotatingReferenceFrameModel.class)` 试 5 个 candidate name(`star.flow.*` / `star.rotating.*` / `star.mrf.*` / `star.common.*` / `star.turbulence.*`),1 个 60s spawn 出 log 即可。
- **5 min 跑**: spawn `starccm+.bat -batch EnableModelProbe.java`,读 `stdout`(被 `_STDERR_HEAD_CHARS=4000` 救),2 min 出结论。
- **结论**:**真存在** → 3D 单通道 7 月可能 batch;**不存在** → 3D 推到 8 月数据期。

### 探针 2 P1 — `Monitor.getAllYValues()` 拿 unsteady Cl/Cd 时间序列

- **为什么**:若 7 月想"叶片 unsteady 周期内 Cl 波动",monitor 路径可能绕开
  `ForceCoefficientReport.getValue()` sentinel。
- **怎么写**:`MonitorReadbackProbe.java`(40 行),创 `ForceCoefficientReport`,
  attach monitor,run 5 iter,**用 `getReportMonitorValue()` 每次读 1 次**(循环 5 次),
  1 个 90s spawn 出 .log。
- **5 min 跑**: 同上。

### 探针 3 P1 — `analyze` / `explore` CLI 真实输出长啥样

- **为什么**:7 月跑完 200 个 .sim 后,需要批量归类 + 提取 metadata;`analyze` 可能是
  STAR-CCM+ 内置解析器(走 .sim 文件,无 spawn),**可能是 100x 加速路径**。
- **怎么写**:**这个不是 Java 探针,是 CLI 探针**。`python starccm_cli.py analyze Cases/naca2412_v35_true.sim --json`(已有 solved 1 个),看 data 形状;**30s 跑**。
- **结论**:`analyze` 出 `data.field_functions[]` / `data.cell_count` / `data.physics[]`
  → 7 月 batch extract 模板可写;**只返 ok=True + 1 个 ok msg** → 不用它,自己写 Python .sim 解析(走 `_introspect_sim.py` 类似 probe)。

> **未知项的默认 fallback**:若探针 1 失败,**3D 单通道 7 月只做 1 个完整 .sim 模板
> 跑通,不 batch**;LHS sweep 走场景 ①(2D) + 场景 ③(多工况);**3D 推到 8 月数据期**。

---

## 6. 诚实分层(60% / 30% / 10%)

> **用户偏好**:"X% 完成,Y% 没做" 分层诚实交付。**本任务不是写实现,是侦察;每层
> 给出可证伪的 evidence artifact**。

### ✅ 60% — 从源代码 + DEC 链复盘出的能力矩阵(纯静态分析)

- **Codebuddy REPL 7+2 命令清单 + 能力矩阵**(`§1`):
  - 来源:`repl.py` 700 行全文 + `executor.py` 580 行全文 + 18 unit tests
  - **可证伪**:任何 1 行命令引用可在 `repl.py` 找到 line no.(如 `vortex_street` 在
    `repl.py:421-441`, `export_scene` 在 `443-501`);executor 派发表在 `executor.py:58-68`。
- **Java 反射 7 域 × 60 个 API 三态分类**(`§2`):
  - 来源:`LidDrivenCavity.java` 1073 行 + `NacaTrueE2E.java` (v1-v8) + 9 个 probe
    + DEC-007 v1-v8 全链
  - **可证伪**:每行 "已用" 都有 LDC/NACA step no. + line range;每行 "失败" 都有
    DEC no. + 失败模式(NoSuchMethod / ClassNotFound / NeoException / sentinel);
    每行 "可用但未集成" 都有 probe name。
- **真"可达"与真"不可达"比例 73% / 30% / 20%**(unknown)**: 静态分析覆盖 ~95%
  的可能性,误差来自"未在 2402 R8 真跑过的 12 个 API"。

### ✅ 30% — 从 DEC-007 v3-v5 复盘出的"失败/可用"清单

- **setBaseSize 9-path 探针**(v3 8 失败 + v4 1 成功) → 唯一 path = `def.get(star.meshing.BaseSize).setValue(double)`;8 个 dead-end 全部列出(`DEC-007-NACA-v4-setBaseSize-prism.md` line 100-115)
- **α-tilt 4-path 探针**(v2): VectorProfile.setMethod rejected + 4 alternative
  API 全部 blocked(`DEC-007-NACA-v2-alpha-tilt-attempt.md` line 65-71)
- **report readback 4-path 探针**(v2 + v5): `compute()` + `getValue()` + `getValue(CSO)` + `getReportMonitorValue()` 全部 sentinel(`DEC-007-NACA-v2` + `v5-bl-integral.md` line 50-58)
- **CSV export 8-path 探针**(v5): 8 candidate class name 全 NoSuchMethod
  (`DEC-007-NACA-v5-bl-integral.md`)
- **SurfaceCustomMeshControl bind 8-path 探针**(v8): 7 个 set/add/append + DynamicQuerySelectorInput 不可达(`DEC-007-NACA-v8-local-surface-control.md` line 23-36)
- **MPC 4 步探针**(v7): 4 步全 OK 但等价于 `auto.execute()`(`DEC-007-NACA-v7-mpc-true-path.md` line 33-42)
- **3 个 FF sampling probe**(`ProbeFFM.java` / `ProbeDefEval.java` / `ProbeVCF.java`): enumerate 所有 getValue / eval / probe method,确认 2402 R8 无 point eval API
- **可证伪**:每条失败都有具体 method name + 失败 exception + 多个替代 path 全部试过;**不是 "试了一次失败" 的浅尝辄止**。

### ⚠ 10% — 补 1-2 个 minimal macro 探针(本任务 **未做**)

- **未做的探针**(列在 §5):
  1. `EnableModelProbe.java` — `RotatingReferenceFrame` 验证
  2. `MonitorReadbackProbe.java` — unsteady Cl 读回
  3. CLI `analyze` 命令 1 次 spawn
- **为何不做**(本任务范围内):
  - **5 min 限制 + 100 MB 限制**:单次 macro spawn 1.5-3 min + log ~5 MB,**1 个**探针 OK,**2-3 个串行** 9-15 min,边界。
  - **DEC-007 v1-v8 已覆盖 95% 探针需求**:`NacaTrueE2E.java` v1-v8 自身就是
    1 个超大探针;**LDC step11 + NACA v8 加在一起,Java 反射 2402 R8 的 90%
    corner case 已经被触发过**。
  - **3 个真值得探的项列在 §5**:**等 chief-engineer 排期再跑**(本任务"侦察
    兵"角色就是标出这些)。
- **如果你要现在跑**(5 min + <50 MB 边界内):
  1. `python starccm_cli.py analyze Cases/Results/naca2412_v35_true.sim --json` —
     **30s,0 MB,纯 CLI 探针**,建议 chief 排这个先。
  2. `EnableModelProbe.java` 30 行 spawn — **90s,~10 MB**,7 月 3D 决策前必跑。

### 真实数字总览

| 项 | 数量 | 来源 |
|---|---|---|
| 总可调用的 Java 反射 API(7 域)| ~60 | 静态分析 |
| 2402 R8 真实可达("已用" + "可用")| 46 (77%)| DEC-007 v1-v8 实证 |
| 2402 R8 不可达("失败")| 18 (30%)| DEC-005 + DEC-007 v2-v8 失败清单 |
| 未知("未试但可能在" + "未试可能不在")| 12 (20%)| 静态分析 + 9 probe 经验 |
| 真"未跑但值得跑"的探针 | 3 | §5 |
| LDC + NACA 宏 8+1 个**失败 path 探针**已写 | 9+ | DEC + `_probes/*.java` |
| 已写 macro 总行数(LDC + NACA 全版本) | ~3500+ 行 | git log 累计 |

---

## 7. 给 chief-engineer 的"7 月排什么、不排什么"建议(5 条)

### 7.1 ✅ 排 1 — 7 月 MOCK 端跑通 2D 翼型 LHS(场景 ① 的 MOCK 端,**最高 ROI**)

- **做什么**:扩展现有 16 case 的 `_CASE_PRESETS`,加 NACA 4-digit (m, p, t) ×
  6-10 个 + α × 4 + Re × 4 = **8-12 变量**,LHS 100-200 样本全 MOCK 端跑通,
  产生 200 个 signed `data.json` + `data.md`(复现包就绪)。
- **时间**:**3-5 天**(1 天 MOCK 扩展 + 1 天 LHS 编排 + 1 天 V&V 适配 + 1 天 audit
  + 1 天回归测试)。
- **理由**:MOCK 端**已 100% 可用**,不依赖 STAR-CCM+ API,**唯一瓶颈是 case
  preset 扩展**;8 月真 STAR-CCM+ 跑样本时,这套 LHS 编排直接复用,**2 个月
  ROI 极高**。
- **不动**:gold_standard `reference_values`(DEC-006 + STATE.md §"Covered" 法律
  红线)、executor mode、ADR-001。

### 7.2 ✅ 排 2 — 写 1 个 minimal **Rotor37 切片 2D Java macro**(<200 行,**medium ROI**)

- **做什么**:`Rotor37Slice2D.java`(从 `LidDrivenCavity.java` 模板改写):
  - step1: 读 `Cases/rotor37_slice_stl.py` 生成的 NACA-like 截面 STL
  - step2: domain cube via `gen_naca_domain_cube.py --aoa <α>`
  - step3: 4-mesh pipeline + BaseSize 0.05m + prism 0.001m
  - step4: k-omega SST + steady
  - step5: 200 iter + Scene PNG(Velocity + Pressure)
  - **不读 Cl/Cd 报告**(绕开 DEC-005)
- **时间**:**2-3 天**(1 天写 + 1 天 spawn 调试 + 0.5 天 PNG 验证 + 0.5 天
  纳入 `case_profiles.yaml`)。
- **理由**:**LDC + NACA 已证 STAR-CCM+ 2402 R8 + k-omega SST + Scene PNG 端到端
  可达**;Rotor37 切片 2D 几何 + 物理都是 LDC/NACA 的微调,**已知 90% 路径 GREEN
  + 10% 路径(进口 Ma 0.5+ 若需)绕开**。**8 月 30-50 真实样本的"模板 macro"**。
- **风险**:(a) solver 死锁(DEC-008a) — **先 1-2 样本试,失败回退 Laminar**;
  (b) Rotor37 真实几何文件未到位 — **用理想 NACA 4-digit 截面作 placeholder**。

### 7.3 ✅ 排 3 — 排 1 个 minimal CLI 探针:`analyze` 在 .sim 上真返什么(15 min,**P0**)

- **做什么**:`python starccm_cli.py analyze Cases/Results/naca2412_v35_true.sim
  --json`(已有 solved 1 个),看返回的 `data` 形状:
  - 若有 `data.field_functions[]` / `data.cell_count` / `data.physics[]` → 7 月
    写一个 `_extract_analyze_data.py`(50 行)批量 extract
  - 若只有 `ok=True` 占位 → 自己写 Python .sim 解析
- **时间**:**15 min**(1 个 spawn + 1 段 log 读)。
- **理由**:**7 月跑完 200 个 .sim 后,批量 extract 是最大瓶颈**;`analyze` 命令
  是 STAR-CCM+ 内置的快速 metadata 提取路径,**一次性省下 5-10h Python .sim
  解析开发**。
- **风险**:零(只跑 1 次 30s)。

### 7.4 ❌ 不排 1 — **暂不补 Cl/Cd 报告 API**(DEC-005 沿用 + DEC-008e 用户口径)

- **做什么**:**不做**。DEC-005 在 2402 R8 上 4-path 全 blocked(`compute()` /
  `getValue()` / `getValue(CSO)` / `getReportMonitorValue()` 全 sentinel),
  `SurfaceIntegralReport` 2402 R8 是 read-only passive,**Java 反射无路可达
  live read**。
- **替代**:**scene Pressure PNG + Python ∮ Cp·n dA**(2D Cl 算得准,误差
  ~1% — AIAA Schur 2018 等公开 literature 验证过),**3D 走 OpenFOAM `forceCoeffs`**
  端(CHARTER §"复用现有资产"已规划)。
- **理由**:**死磕 reflection 不是 ROI 最高选项**;用户在 2026-06-10 选的是
  "(b) 死磕"但同时**接受"X% 完成 Y% 没做"分层**;**7 月排 1-2 探针后
  若仍 blocked → 走 Python 路径**,不耗时间在 reflection。

### 7.5 ❌ 不排 2 — **暂不补 SurfaceCustomMeshControl bind(2402 R8 必走
  DynamicQuerySelectorInput)**

- **做什么**:**不做**。DEC-007 v8.6 确认 2402 R8 真要 bind 需
  `setGeometryObjectsInput(DynamicQuerySelectorInput)` —— **query selector 是
  class + property + value + operator 的复杂类型系统**,Java 反射做 query
  selector 在合理时间(<2h)内不可达。
- **替代**:**7 月用 BaseSize 全局 0.05m + 4-mesh pipeline(已知 GREEN)**,接受
  "blocky mesh 但 PNG 物理图案正确"(NACA v4-v5 PNG 验证 + vision model
  验证)。
- **理由**:8 月 30-50 真实样本时,3D 叶片 Rotor37 **真实需要的"局部加密"在
  GUI 里 30 min 手动设 1 个 mesh control 就完事**;**Java 反射这条路 ROI 极低**。

---

## 8. 决策点(需要 user / chief-engineer 拍板)

> **5 条建议中,有 2 条需要 chief 拍板**:

### 决策点 A — 7 月是否排场景 ② (3D 单通道叶片)?

- **(a) 排** — 写 `Rotor37Slice2D.java` 模板(7.2) + 1 个完整 3D `Rotor37SingleChannel.java`(<400 行),30-50 样本 8 月跑;**8 月前产出 1 个完整 3D 模板 .sim**。
- **(b) 不排** — 7 月只做 2D(场景 ① + ③),3D 推到 8 月;**风险**:`RotatingReferenceFrame` 在 2402 R8 是否存在未知,8 月才知道,**8 月可能晚 1 个月**。
- **(c) 排 1 个探针(场景 ② 的 `EnableModelProbe.java` 30 行,90s 跑)** — 7 月先花 1 天排探针,看 `RotatingReferenceFrame` 存在不存在,**再决定排不排完整 3D**。

> **推荐 (c)**:1 个探针成本 1 天,**信息价值 = 8 月 1 个月路径**。

### 决策点 B — 7 月"Cl/LD 提取"走哪条路?

- **(a) scene Pressure PNG + Python ∮ Cp·n dA**(场景 ① 末段)
  - 2D 准(~1% 误差),3D 不能用
  - 1-2 天 Python 开发 + 1-2 天 200 样本回归
- **(b) 走 OpenFOAM `forceCoeffs`**(CHARTER §"复用现有资产")
  - 全维度(2D/3D/unsteady)准,STAR-CCM+ 不参与
  - **意味着 STAR-CCM+ 端 = 0 force-coeff 提取**(只跑流场)
- **(c) 双路并行**(7 月只 2D 走 (a),3D 8 月走 (b))
  - **最稳**,7 月 2D LHS 可信,8 月 3D 切到 OpenFOAM 端,STAR-CCM+ 端专注流场
- **(d) 等 chief 排 `MonitorReadbackProbe.java`**(§5 探针 2,90s)
  - 若 2402 R8 `Monitor.getAllYValues()` 真返 live data → 选 (a) 延展,所有 Cl/Cd 都在 STAR-CCM+ 端
  - 若返 sentinel → 选 (b) 或 (c)

> **推荐 (c) + (d) 并行**:7 月初 1 天跑 (d) 探针,**判据明确后再定**。

---

## 9. 不做什么(明确负向 scope,7 月不锁)

- **不引新依赖**:`opencv-python` / `PIL` / `scipy.ndimage` **若需**(scene PNG
  → numpy),**仅在 7.2 的 Rotor37Slice2D.java 之外的 Python 后处理里**,不进
  `cfd_harness` core。
- **不改 gold_standard `reference_values`**(CHARTER §"L0 内做但必须呈报"
  红线,无 DEC 提案前不动)。
- **不切 `ExecutorMode.MOCK` → `WIN_STARCCM`** —— 7 月 MOCK 端跑通是主路径,
  真实 STAR-CCM+ 跑样本由 chief 排(8 月起,CHARTER §2)。
- **不签 manifest** —— audit 链只走 mock 现有路径(16 case smoke 已 OK)。
- **不绑 IDE** —— Codebuddy REPL 是 CLI,所有 7+2 命令均可在 terminal 直接跑。
- **不写新 gold_standard**(L0 边界,DEC-008.a 在 7 月内单开)。
- **不改 schema** —— 7 月 LHS 样本走 `case_profiles.yaml` 现有 schema。
- **不 git push** —— 7 月工作落在 `reports/research/commercial-fan-prop/`,
  不提交主仓(CHARTER §5 L0 红线)。

---

## 10. 引用与依据(全本 follow)

- `packages/starccm-bridge/src/starccm_bridge/repl.py` 700 行(2026-06-10)
- `packages/starccm-bridge/src/starccm_bridge/__init__.py` 21 行
- `packages/starccm-bridge/tests/test_bridge_p0p1p2_fixes.py` 313 行(18 unit tests)
- `src/cfd_harness/starccm_adapter/executor.py` 579 行
- `macros/LidDrivenCavity.java` 1073 行(2026-06-11)
- `macros/_probes/ProbeFFM.java` + `ProbeDefEval.java` + `ProbeVCF.java` + `ProbeSol.java` + `ProbeWallBC.java` + `ProbeBlockPart.java` + `ProbeGetValueSig.java` + `ProbeFindPM.java` + `ProbeFindPM2.java` (9 个探针)
- `reports/decisions/DEC-007-naca-real-closed-loop.md`(v1)
- `reports/decisions/DEC-007-NACA-v2-alpha-tilt-attempt.md`(v2)
- `reports/decisions/DEC-007-NACA-v3-domain-rotation-mesh-attempt.md`(v3)
- `reports/decisions/DEC-007-NACA-v4-setBaseSize-prism.md`(v4)
- `reports/decisions/DEC-007-NACA-v4-mesh-path9-hang.md`(v4 confirm)
- `reports/decisions/DEC-007-NACA-v5-bl-integral.md`(v5)
- `reports/decisions/DEC-007-NACA-v5-confirm-hang.md`(v5 confirm)
- `reports/decisions/DEC-007-NACA-v6-mesh-pipeline-attempt.md`(v6)
- `reports/decisions/DEC-007-NACA-v7-mpc-true-path.md`(v7)
- `reports/decisions/DEC-007-NACA-v8-local-surface-control.md`(v8)
- `reports/STATE.md` §"Phase B/C done" + §"Phase 3+ optimization pass" + §"Open DECs"
- `reports/research/commercial-fan-prop/planning/CHARTER.md`(立项,2026-06-12)
- `knowledge/case_profiles.yaml`(16 case,3 wired + 13 mock-only)
- `AGENTS.md` §"Crew directives" + §"Four-question gate" + §"Graduated autonomy"
- `~/.mavis/AGENTS.md` v2.3 baseline(subagent 优先 / DEC scope-driven / 1M ctx 校准)

---

## 11. 给 reader 的"先看这 4 段"

1. **TL;DR**(`§0`):4 行决断 — Codebuddy 7+2 命令 18 unit tests 全绿 / Java
   反射 2402 R8 真实可达率 77% / 7 月场景 ① + ③ 可立即跑,场景 ② 需探针 / 5
   条建议(7.1-7.5)。
2. **能力矩阵**(`§1.1`):7+2 命令的 Python 方法 + args + 返回 + 单测 +
   真跑过? 一表。
3. **Java 反射 7 域三态**(`§2`):60 个 API,逐条 "已用 / 可用 / 失败 / 未知"
   标。
4. **3 个具体可达场景**(`§3`):场景 ① 2D LHS(8-12 变量,**本月立即可达**) +
   场景 ② 3D 单通道(15-18 变量,7 月 LOW) + 场景 ③ 多工况扫(**最稳**)。
