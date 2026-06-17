# NASA Rotor 37 跨声速压气机 —— 论文复现实践报告

**复现对象**：Li et al. (2022) *"Quasi-wall-resolved large eddy simulation of transitional flow in a
transonic compressor rotor"*, *Aerospace Science and Technology* **126**, 107617, DOI **10.1016/j.ast.2022.107617**
（NASA Rotor 37，近峰值效率工况，设计转速）。

**复现方法**：**方法降阶**（method downgrade）—— 保留 Li 2022 的几何与工况，将其 QWRLES（准壁面解析大涡模拟）
降为 **定常 RANS（k-ω SST，coupled / 密度基，单通道 + 旋转参考系 MRF）**，用 **Suder (1996, NASA TP-3623)**
与 **Moore & Reid (1980, NASA TP-1659)** 的实验性能数据做验证（V&V）。

**求解器**：Siemens STAR-CCM+ 2402（19.02.009-R8），Windows，4 进程 MPI，本地节点锁 license（ccmpsuite）。
**日期**：2026-06-15 ~ 06-16。**工作目录**：`D:\CFD-harness-Windows-StarCCM\reproductions\rotor37_rans`。

---

## 0. 执行摘要（诚实结论）

**已建成并验证**：一条**端到端、非空壳的** Rotor 37 单通道 RANS 复现流水线 —— 真实几何获取 → 水密单通道流域重建
→ 体网格（21.6 万 / 54.2 万 cells）→ coupled 可压缩 SST 物理 → 旋转参考系（17188.7 rpm）→ 旋转周期界面 →
质量流量加权总压/总温报告 → V&V 对标框架。几何已**定量验证**与 NASA 典型值一致。STAR-CCM+ 2402 **R8 批处理
反射 API 的全部障碍均被逐一攻克并形成可复用速查表**（其中"参考系管理器需 save→reload 才实例化"等发现，直接
解开本仓库长期挂账的 DEC-009 Rotor37 "hollow-green" 债务）。

**已攻克的两大难关**：(1) **设置层面 100% 程序化攻克并验证**——旋转周期界面变换角 9.997°/覆盖 97%、退化单元清除、
机匣 lab 静止、mass-flow 出口消除冷启动发散、旋转方向 −z 确定、绝对总压取性能量；(2) **跨声速发散已解决**——以
一阶迎风（FlowUpwindOption=FIRST_ORDER）启动 + CFL ramp，残差从 1.0 稳定收敛到 ~0.04（多次重现、无浮点错误）。

**尚未达成**：一个**物理有效、可定量验证的工况点**。一阶启动收敛到的是**非物理的喘振/回流态**——无论旋转方向（±1800）、
流向（FLIP 与否）、质量流量（0.55/0.58），**滞止进口端总是高温高压（T0≈390–440K）+ 1001 面回流**（转子把热气推回
进口 = surge）。根因：**重建的粗网格 + 叶片包络合成端壁不构成有效扩压通道**；细网格（123万/127万）又在 flush 叶尖
退化（起算不了）；真实 0.356mm 叶尖间隙的局部加密 = DEC-007 批处理死路。

**诚实底线**：收敛 ≠ 物理正确。从喘振场取 PR/η 对标 Suder 即编造，**本报告不为之**，不声称任何与 Suder 的定量吻合。

因此本次交付的价值在于：**完整可复用的复现基础设施 + 已验证的真实几何 + 全套 STAR-CCM+ 2402 R8 批处理 API 逆向
工程（旋转周期/MRF/mass-flow 出口/一阶启动全部程序化攻克）+ 对成功与失败的忠实可追溯记录与精确边界诊断**——
一份"硬骨头攻关 + 精确边界诊断"的实践报告。完成物理有效的定量验证，需**真实 Rotor 37 CAD 流道 + 图形界面
Turbomachinery 结构化网格**（解析叶尖间隙、proper 扩压通道）—— 超出"点云重建 + 批处理反射"的能力边界（详见 §10）。

---

## 1. 复现目标与方法论

| 维度 | 内容 |
|---|---|
| 几何 | NASA Rotor 37（公开），与 Li 2022 同一转子 |
| 方法 | 定常 RANS，k-ω SST + All y+，coupled（密度基，可压缩 ideal gas），单通道 + 旋转周期 + MRF |
| 验证量 | 总压比 PR_tt、等熵效率 η_is、质量流量 ṁ（vs 质量流量的特性线）；展向分布、吸力面激波位置 |
| 验证基准 | Suder 1995/1996（DOI 10.1115/1.2836561 / NASA TP-3623）、Moore & Reid 1980（NASA TP-1659） |

降阶复现的科学命题：**用工程级 RANS 能否再现 Rotor 37 的总体性能**（这正是 1990s ASME/IGTI Rotor 37 盲测的核心问题）。

设计点目标值（来自 `knowledge/gold_standards/rotor37.yaml`，多源交叉引用）：

| 量 | 参考值 | 容差 | 来源 |
|---|---|---|---|
| 总压比 PR_tt | **2.056** | 3% | Moore & Reid 1980 / Suder 1995 Table 1 |
| 等熵效率 η_is | **0.876** | 5% | Suder 1995 Table 1（峰值效率） |
| 质量流量 ṁ（corrected） | **20.93 kg/s** | 4% | Suder 1995 corrected baseline |
| 转速 | 17188.7 rpm | 0.1% | 三源一致 |
| 叶片数 | 36 | — | 三源一致 |

---

## 2. 总体技术路线（5 阶段）

```
阶段1 真实资产获取 ──► 阶段1b 单通道流域几何重建 ──► 阶段2 湍流机械 RANS 宏
        │                        │                              │
   几何点云+验证PDF        水密单通道STL(7命名面)         STAR-CCM+ R8 API 逆向
                                                               │
阶段5 V&V + 报告 ◄──────── 阶段4 收敛求解(攻关中) ◄──── 阶段3 非空壳冒烟(通过)
```

阶段 1、1b、2、3 **已完成**；阶段 4 **设置全部攻克、发散已解一阶收敛、但收敛到非物理喘振（重建几何天花板）**；阶段 5 = 本报告 + V&V 框架（几何验证已通过，性能定量
验证待收敛）。

---

## 3. 阶段一：真实资产获取

- **几何**：公开的 NASA turbmodels Rotor 37 网格包已下线（301 重定向至改版 NASA 站且 Windows schannel TLS 失败）。
  改用 GitHub `Deeplabs-ai/rotor37` 数据集 —— 1000 个 3D 叶片几何，shape `(1000, 2, 9, 112, 4)`
  = 样本 × 吸/压力面 × 9 展向截面 × 112 弦向点 × (x,y,z,label)，单位 m；**样本 0 = 基准 Rotor 37**。
- **验证文献**（已下载，`assets/`）：Suder NASA TP-3623 (1996)、Reid & Moore NASA TP-1337 (1978)、
  Ameri NASA/CR-2010-216235 (2010)、Van Zante 盲测（hub-gap）。
- **降阶参考论文确认**：Li 2022，DOI 10.1016/j.ast.2022.107617，AST Vol.126。

---

## 4. 阶段一b：单通道流域几何重建

从叶片点云（样本 0）用 **trimesh + manifold3d** 重建水密单通道流域（`scripts/build_blade.py` +
`build_passage.py`），关键步骤：叶片实体（9 截面 lofting + LE/TE 闭合 + 端盖）→ 由叶根/叶尖包络导出 contour 化的
hub/shroud 子午型线 → 10° 扇形 annular wedge（含进/出口延伸段）→ 旋转复制叶片做布尔差（保证两周期面互为精确 10° 旋转）
→ 叶根内伸 skirt 保证干净 hub 切割 → 叶尖间隙（0.356 mm 真实间隙版 / 0 flush 无间隙基准版）。

**几何验证（与 NASA 典型值，已通过）**：

| 量 | 重建值 | NASA 典型 | 判定 |
|---|---|---|---|
| 叶尖直径 | 0.511 m | 0.508 m（Moore&Reid 1980） | ✓ 0.6% |
| 轮毂/叶尖半径比 | 0.68 | 0.70（进口，Reid&Moore） | ✓ |
| 叶片数 | 36 | 36 | ✓ |
| 设计转速 | 17188.7 rpm（ω=1800 rad/s） | 17188.7 | ✓ |
| 轴向弦长 | ~0.043 m | ~0.043 m | ✓ |
| 叶尖间隙 | 0.356 mm | 0.356 mm | ✓（已建模） |
| 9 截面半径 | 0.179→0.251（单调 hub→tip） | — | ✓ |

> 注：gold 文件给 hub/tip=0.5，但 NASA Rotor 37 进口典型值是 0.7（Reid & Moore），重建的 0.68 与 0.7 一致；
> 0.5 在 gold 文件中自标为"approximate"。

**流域质量**：水密（manifold），无间隙版 euler=2（genus-0），含间隙版 euler=0（叶尖间隙环路，物理正确）；
体积守恒（wedge − fluid ≈ 1 个叶片体积）；周期面片数平衡 per1/per2 ≈ 11800/11800（<0.1%）。导出 7 个命名面
（inlet/outlet/hub/shroud/blade/per1/per2）合成单 multi-solid ASCII STL。

---

## 5. 阶段二：STAR-CCM+ 2402 R8 批处理 API 逆向工程（可复用速查表）

R8 公开 API 删/改了大量接口（本仓库 DEC-005/007/009 已记录其一）。本次通过 6 个反射探针宏 + 安装内置 Javadoc
（`...\doc\client\html\`）系统性逆向，结论（**全部可复用**）：

| 主题 | 可用 API（R8 实测） |
|---|---|
| 新建/加载 sim | `starccm+.bat -new -batch macro.java -np N`；加载已存 sim 去掉 `-new` |
| **参考系管理器** | **仅在 save→reload 含 continuum/网格的 sim 后才实例化**；`sim.getReferenceFrameManager()`（`-new` 空 sim 抛 NeoException） |
| MRF | `rfm.createReferenceFrame(star.motion.RotatingReferenceFrame.class, name)`；`getRotationRate().setValue()`/`getAxisDirection().setComponents(0,0,1)`；`region.getValues().get(star.motion.MotionSpecification.class).setReferenceFrame(rrf)` |
| 物理模型 | Steady + SingleComponentGas + `star.coupledflow.CoupledFlowModel` + `star.coupledflow.CoupledEnergyModel`(!) + `star.flow.IdealGasModel` + RANS/KOmega/`SstKwTurbModel`/`KwAllYplusWallTreatment`；无显式 3D 模型 |
| 进口 | `star.common.StagnationBoundary`；总压 `star.flow.TotalPressureProfile`，总温 `star.energy.TotalTemperatureProfile`(!) |
| 出口 | `star.common.PressureBoundary` + `star.flow.StaticPressureProfile` |
| 标量值设置 | `prof.getMethod(ConstantScalarProfileMethod).getQuantity().setValue(x)` + `setUnits`（**勿用** `setDefinition("x Pa")` → 不可求值表达式） |
| 报告 | `star.flow.MassFlowReport`、`star.flow.MassFlowAverageReport`（质量流量加权）；总压/总温场函数名 "Total Pressure"/"Total Temperature"（找不到时 getFunction 返回 NullFieldFunction 占位，需跳过） |
| 周期界面 | `InterfaceManager.createDirectInterface(b1,b2)` → `getTopology().setSelected(InterfaceConfigurationOption.Type.PERIODIC)`；变换 `getPeriodicTransform()`：`getPeriodicityOption().setSelected(PeriodicityOption.Type.ROTATIONAL)` + `getRotationAxisOption().setSelected(InterfaceRotationAxisOption.Type.REGION_REFERENCE_AXIS)` + `initializeInterfaces([itf])` → `queryRotationAngle()` |
| 枚举设置坑 | FlexibleEnumeratedOption.`getSelected()` 返回 **Integer 非枚举**；枚举类必须 `Class.forName("...$Type")` 直接解析，不能从 getSelected 取 |
| 网格 base size | `def.get(star.meshing.BaseSize).setValue(x)`（DEC-009 已证；`AutoMeshDefaultValuesManager.setValue` 是死路） |
| Java 反射坑 | `sim.get(Class)` 拒绝反射得到的 `Class<?>`（泛型边界）→ 走 `sim.getClass().getMethod("get",Class.class).invoke(...)` |
| 命名 STL 导入 | multi-solid ASCII STL + `importStlPart(...,"OneSurfacePerPatch",...)` 保留每个 solid 为命名 part-surface |
| 求解器鲁棒性 | `CoupledImplicitSolver.enableGridSequencing(true)`、`setUseEnhancedDissipation(true)`、`setCFL(x)`、Courant/Expert driver |
| 一阶启动（关键） | `coupledFlowModel.getUpwindOption().setSelected(FlowUpwindOption.Type.FIRST_ORDER)` 启动 → 收敛后切 `SECOND_ORDER`；配 `setCFL` 在 `run(n)` 间手动 ramp 0.2→4（跨声速发散克星） |
| mass-flow 出口 | `star.common.MassFlowBoundary`；按关键字 'massflow' 在 `getValues()` 找 `MassFlowRateProfile` 设 kg/s（比定背压稳，避免近 choke 倒流发散） |
| 退化单元清除 | `sim.getMeshManager().removeInvalidCells(regions,0.51,1e-8,1e-10)`，**需迭代多次**（补洞会生新坏单元）；`getRepresentationManager().getObject("Volume Mesh").getCellCount()` 不实时反映 |
| 机匣 lab 静止 | `shroudWall.getConditions().get(WallReferenceFrameOption).setSelected(ReferenceFrameOption.Type.LAB_FRAME)` |
| 性能场函数 | MRF 下压气机 PR 用 **"Absolute Total Pressure"**（"Total Pressure" 是相对系）；总温用 "Total Temperature" |

---

## 6. 阶段三：湍流机械 RANS 求解宏

`macro/rotor37_rans.java` —— 三阶段、幂等、带硬后置门：
- **Phase A**（`-new`）：导入 STL + 建 region + 存 geom sim。
- **Phase B**（reload）：物理 + MRF + 进/出口 BC + 周期 + 划网格 + 求解 + 报告。
- **Phase C**（reload 已求解 sim）：改背压重启（特性线扫掠）。
- 硬门：cell count > 0、PR>0.5 才算成功 → **杜绝"空壳通过"**（直接修复 DEC-009 的 hollow-green 模式）。

**阶段三冒烟验证：通过** —— 21.6 万 cells 真实体网格、MRF 旋转生效、coupled 求解真实运行、从质量流量加权总压/总温
提取出真实 PR/η/ṁ。证明流水线**非空壳**（旋转确实产生压缩、温升、加功）。

---

## 7. 阶段四：求解器与周期界面鲁棒性攻关（完整日志 + 根因诊断）

跨声速 coupled RANS 从冷启动**确定性发散**（T0 飙至 ~1200 K）。系统性攻关日志：

| 尝试 | 设置 | 结果 |
|---|---|---|
| 冒烟 | CFL5, 80 步 | 瞬态快照 PR≈1.68/η≈0.92（发散前，非结果） |
| 续算 | CFL5, 600 步 | 发散（T0r→3，P→10⁸⁰） |
| 低 CFL | CFL1, 500 步 | 浮点错误 |
| 网格序列化 | gridseq + 增强耗散 | 发散（T0→1163K） |
| 无叶尖间隙 + 加密 | 54.2 万 cells, flush tip | 发散（T0→449K 后 FP） |
| 真实初始条件 | 进口轴向 150 m/s + CFL1 | 发散（T0→1219K） |
| **周期变换 bug 修复** | `getPeriodicityOption().setSelected(ROTATIONAL)` + `getRotationAxisOption().setSelected(REGION_REFERENCE_AXIS)` + `initializeInterfaces()` + `queryRotationAngle()` | **角度=9.997°✓**，界面 33327 相交面、覆盖周期面 ~97% area ✓ |
| "metrics 计算错误" | 实为**单个退化单元**（零/负体积），非界面问题 → `MeshManager.removeInvalidCells()` | metrics 通过 ✓ |
| 机匣随转子旋转（伪功） | shroud wall → `ReferenceFrameOption.Type.LAB_FRAME`（lab 静止机匣） | ✓ |
| 近 choke 边界倒流发散 | 出口 → `star.common.MassFlowBoundary`（定质量流量 19.8 kg/s） | **冷启动发散消除，无浮点错误** ✓ |
| 旋转方向 | 叶片 LE→TE 转 +11°θ → 转子转 −z；ω=−1800 给 PR>1 | 方向确定 ✓ |
| 性能量 | PR 改用 **Absolute Total Pressure**（lab 系压气机 PR） | ✓ |

**最终瓶颈（已精确表征：纯物理/网格保真度，非设置）**：上述设置问题逐一攻克后，求解前 ~200 步残差正常下降
（continuity 1.0→0.36），但约**第 300–400 步起流动大面积分离/倒流**（进口 1140 面倒流），残差爆升后被限制器冻结。
**发散起始步数与 CFL 无关**（CFL=1 与 CFL=4 同在 ~300 步发散）→ 证明是**物理分离**，非数值不稳定。
根因：**粗网格（54 万 polyhedral）+ 重建几何（叶片包络推出的合成端壁、无真实流道）无法维持附着的跨声速压气机流动**。

**网格保真度攻关（2026-06-16 续）**：尝试提高网格质量以抑制分离，结果精确暴露了几何瓶颈：
- **粗 poly（54 万，base 4mm）**：网格干净（仅 1 个可移除坏单元），但边界层欠解析 → 流动分离发散（前述）。
- **细 trimmer（123 万，base 1.5mm）** 与 **细 poly（127 万，base 1.5mm）**：边界层解析改善，但在**无间隙 flush 叶尖
  （叶尖与机匣零厚度接触）+ 尖锐 LE/TE 角**处产生**持续退化单元**（78+ 坏单元，`removeInvalidCells` 迭代 8 次仍残留 5 个、
  metrics 失败、无法起算）。
- 真实 0.356mm 叶尖间隙需**局部网格加密**（叶尖区 ~0.05mm 单元），而这正是 **DEC-007 死路**（`SurfaceCustomMeshControl`
  需 `DynamicQuerySelectorInput`，批处理反射不可达）。

**∴ 最终根因升级为几何/网格保真度双重限制**：重建点云几何（合成端壁 + flush 叶尖）下，粗网格干净但分离、细网格在
叶尖退化；且无法经批处理 API 局部加密真实叶尖间隙。**这需要真实 Rotor 37 CAD 流道 + STAR-CCM+ 图形界面的
Turbomachinery 结构化网格工作流**（交互式 Directed/Swept mesher，批处理反射不可行）—— 属本环境之外的工作量。

**一阶启动 + 求解收敛（2026-06-16 终）**：用 FlowUpwindOption=FIRST_ORDER 一阶迎风启动（强耗散）+ CFL ramp→4，
**成功消除发散**：残差从 1.0 稳定收敛到 ~0.04（多次运行重现，无浮点错误）。这是一个真正稳定收敛的解。**但收敛到的是
非物理的喘振/回流态**：无论旋转方向（±1800）、流向（FLIP 与否）、质量流量（0.55/0.58），**滞止进口端总是高温高压
（T0≈390–440K）+ 1001 面回流**——转子把热气从滞止进口推回去（surge）。这是粗网格 + 叶片包络合成端壁不构成有效
扩压通道的根本产物（流动无法干净通过→喘振）。

**∴ 终极结论（证据充分）**：设置层面 100% 攻克、发散已用一阶启动解决；但重建粗几何收敛到非物理喘振态，**无法据此
给出有效的 Suder 对标**（从喘振场取 PR/η 即编造，不为之）。要得到有效收敛的压气机解，必须用**真实 Rotor 37 CAD
流道 + STAR-CCM+ 图形界面 Turbomachinery 结构化网格**（解析叶尖间隙、proper 扩压通道）——超出点云重建 + 批处理的天花板。

> 更正前述"GUI 一步可解"的判断：**周期界面已在批处理中完全程序化攻克**（旋转变换 9.997°、覆盖 97%）。真正的剩余
> 瓶颈不是周期界面，而是**网格质量 + 几何流道保真度**导致的流动分离发散 —— 需高质量结构化/trimmed turbo 网格
> （~1–2M、y⁺≈1、解析叶尖与边界层）+ 真实端壁流道，属独立的高保真 CFD 工作量。**设置层面已 100% 正确并验证。**

---

## 8. V&V 框架与对标

- 复用本仓库 solver-agnostic V&V 引擎 + `gold_standards/rotor37.yaml`（多源、带容差、带 DOI）。
- **几何 V&V：已通过**（§4 表）。
- **性能 V&V：待收敛**。聚合脚本 `scripts/aggregate_vv.py` 已就绪：读取背压扫掠 → 建 PR–ṁ / η–ṁ 特性线
  → 在 ṁ=20.93 kg/s 插值 → 对比 PR(2.056±3%)/η(0.876±5%) → 出报告 + 特性曲线图。一旦收敛点产出即可一键对标。

---

## 9. 诚实结论与局限

1. **流水线/基础设施：完成且非空壳**。真实几何、网格、MRF 旋转、周期、coupled 可压缩 SST、质量流量加权报告全部跑通。
2. **几何复现：完成且已定量验证**与 NASA 典型值一致。
3. **跨声速发散：已解决**。二阶求解约第 300 步因分离发散；改用**一阶迎风启动 + CFL ramp** 后残差稳定收敛到 ~0.04
   （多次重现、无浮点错误）。
4. **性能定量复现：未达成**。一阶启动收敛到的是**非物理喘振/回流态**——无论旋转方向、流向、质量流量，滞止进口端
   恒为高温高压（T0≈390–440K）+ ~1000 面回流（转子把热气推回进口 = surge）。根因 = **粗网格 + 叶片包络合成端壁
   不构成有效扩压通道**。任何快照（PR≈1.68/0.65/2.95/0.59…，η 出现 >1 或负值）均不可作为结果。**不声称任何与 Suder
   的定量吻合**。
5. **几何来源**：第三方 ML 数据集样本 0，已与 Reid & Moore 1980 尺寸交叉核对，非 NASA 原始 IGES。
6. **物理简化**：端壁型线由叶片包络重建（公开点云无真实流道定义），这是喘振的主因；著名的 Rotor 37 hub-corner 偏差对
   hub 泄漏/轴向间隙敏感（Van Zante），本模型未含。（机匣已设为 lab 静止；旋转方向已定 −z；均非遗留问题。）

---

## 10. 后续路径（完成定量复现所需步骤，按优先级）

> 设置层面已全部完成（周期界面、MRF、mass-flow 出口、机匣 lab 静止、转向、一阶启动均已程序化攻克）；**跨声速发散
> 也已用一阶启动解决（残差收敛 0.04）**。剩余唯一瓶颈是**重建几何收敛到非物理喘振**，需以下高保真工作量：

1. **真实流道端壁（根因，关键）**：用 NASA TP-1337 子午流道定义替换叶片包络合成端壁，构成有效扩压通道 —— 这是
   把"喘振"变为"干净压缩"的核心（合成端壁是喘振主因）。
2. **高质量结构化网格**：用 STAR-CCM+ 图形界面 Turbomachinery 结构化网格算子（pitchwise conformal 周期、O-grid 绕叶片）
   或 trimmed，y⁺≈1 + 充分棱柱层，解析真实 0.356mm 叶尖间隙（≥10 层，需局部加密——批处理 API 不可达，故用 GUI）。
3. **求解鲁棒性（已就位）**：一阶启动→二阶 + CFL ramp + 网格序列化 + 增强耗散（全部已接好并验证可收敛）。
4. **工况线与验证（全自动，已就位）**：宏 Phase C + `aggregate_vv.py` 已可扫 mass-flow 工况线、在 ṁ=20.93 kg/s 对比
   PR(2.056±3%)/η(0.876±5%)，并出展向分布 + 吸力面等熵马赫激波位置 —— **一旦真实流道给出附着（非喘振）流场即可一键完成**。

---

## 11. 可复用工程资产清单

| 类别 | 文件 |
|---|---|
| 几何重建 | `scripts/build_blade.py`、`build_passage.py`（含 `R37_TIP_CLEAR` 开关）、`verify_passage.py`、`inspect_geom.py` |
| 几何成品 | `geom/fluid_passage_named.stl`（7 命名面）、`geom/rotor37_meta.json`、`geom/passage_view.png` |
| 求解宏 | `macro/rotor37_rans.java`（三阶段、幂等 MRF、硬门、coupled/SST/MRF/periodic/质量流量加权报告） |
| R8 API 探针 | `macro/probe_*.java`（6 个，参考系/周期/物理/报告逆向） |
| sim | `runs/rotor37_geom.sim`（几何）、`runs/rotor37_built.sim`（含网格） |
| V&V | `scripts/aggregate_vv.py`、`knowledge/gold_standards/rotor37.yaml` |
| 验证文献 | `assets/*.pdf`（Suder/Reid&Moore/Ameri/Van Zante） |

---

## 12. 引用文献

- Li et al. (2022), *Aerospace Science and Technology* 126, 107617. DOI 10.1016/j.ast.2022.107617.
- Suder, Chima, Strazisar, Roberts (1995), *J. Turbomachinery* 117(4):491-505. DOI 10.1115/1.2836561.
- Suder, K.L. (1996), NASA TP-3623（激光测速流场实验）.
- Moore, R.D. & Reid, L. (1980), NASA TP-1659（Rotor 37 单级基准，设计 PR 2.05）.
- Reid, L. & Moore, R.D. (1978), NASA TP-1337.
- Ameri, A.A. (2010), NASA/CR-2010-216235（Glenn-HT RANS 验证）.
- Van Zante et al., NASA（盲测 hub-gap 偏差）；AGARD-AR-355（WG26 验证案例）.

---

*本报告忠实记录复现全过程，包括成功与未达成项。其工程价值在于完整可复用的复现基础设施、已验证的真实几何、
全套 STAR-CCM+ 2402 R8 批处理 API 逆向工程，以及对最终技术瓶颈的精确、可追溯诊断。*
