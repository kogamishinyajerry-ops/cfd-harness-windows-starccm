# NACA v3 — domain rotation 4° + mesh size API attempt (blocked)

| Field | Value |
|---|---|
| Status | **partial** — α=4° applied via geometry; mesh size stuck at default |
| Date | 2026-06-11 |
| Branch of | DEC-007 v2 |

## TL;DR

**v3 成功把 α=4° 接到流场里**（用几何旋转 cube STL，绕翼型四分之一弦长轴 4°），压
力场 PNG 里"高压力红橙块在翼型前缘下方 + 上表面深蓝 suction"明确证实 α=+4° 起作
用。**但 setBaseSize 全部 8 条路径都失败**，mesh 仍是 STAR-CCM+ 默认稀疏（看 PNG
"exceptionally blocky, control volumes clearly visible"），cell count 也拿不到。

## v2 vs v3 对比

| | v2 | v3 |
|---|---|---|
| α tilt | setMethod API（4 种全被 2402 R8 拒） | **cube STL 绕 z 轴 4° 旋转**（绕四分之一弦点 0.25,0,0） |
| 物理 α | 0° | **4°** ✅ |
| Inlet 速度 | 15 m/s scalar X | 15 m/s scalar X（cube 旋转，叠加成 α=4°） |
| Mesh size 路径 | 6 条 setBaseSize path 全 FAIL | **+2 条 path**: createPartControl + setSilently (set 调用成功但读不回来值), cv.get(String), cv.get(BaseSize.class) |
| Mesh base size | 默认（粗） | 0.005 m 设置**但可能被 silently dropped** |
| Cell count | 拿不到 | 拿不到 |
| Mesh time | 6.0 s | 7.8 s |
| 2000-iter time | 137 s | 同 |
| 压力场 PNG | 真实但**对称**（α=0） | **真实且非对称**（高压力在 LE 下侧，吸力峰在上侧 = α=+4° 物理正确） |
| Cl reported | 2.146 | 6.512 |
| Cd reported | 0.284 | 0.134 |
| 解决了吗 | ❌ 报告值可疑 + α=0 | ⚠️ α=4° 几何对，但 Cl 数字仍依赖 broken report.getValue() |

## 关键代码改动

### `gen_naca_domain_cube.py`: `--aoa` flag + 旋转函数
- 新增 `_rot_z(p, theta_rad, pivot)` 把每个 corner vertex 绕 z 轴旋转
- 默认 pivot = `(0.25, 0.0, 0.0)` = 翼型四分之一弦点
- 翼型本身不旋转（仍沿 x 轴），整个 cube 绕翼型转，所以 flow 看到 α=+aoa

### `NacaTrueE2E.java`: stepImportDomainPanels 自重生 cube
- 跑 macro 前 `python macros/gen_naca_domain_cube.py ... --aoa 4.0` 重生 STL
- 域扩到 `y[-5.5, 5.5]`（旋转后 corner 略超出 ±5）

### `NacaTrueE2E.java`: stepMesh 第 7-8 条 setBaseSize path
- 探索 `AutoMeshOperation.getCustomMeshControls() → CustomMeshControlManager.createPartControl(List) → PartCustomMeshControl.getCustomValues() → CustomMeshControlValueManager` 这条链
- 在 PartCustomMeshControl 上：`setSilently("BaseSize", 0.005)` 调用成功（无 exception），但 `getDouble("BaseSize")` 读回 **null** — 值没真的存进去
- `set("BaseSize", 0.005)` 也调用成功但同样读不回

## 真实 PNG 证据 (2402 R8 真跑)

### 速度场 (v3)

`Cases/Results/naca_v35_velocity.png` (67 KB): 翼型在右，前缘白色，**沿表面有薄
薄一条蓝色边界层**，自由流红色 15 m/s。**和 v2 一样的物理图案**，但**更细致**
（用户反馈"还是 blocky"——v3 比 v2 细一点但确实不到 industry-grade 那种密）。

### 压力场 (v3) ⭐ 这是 v3 的硬证据

`Cases/Results/naca_v35_pressure.png` (72 KB): **高压力红橙块在翼型前缘下方（α=+4°
物理正确），上表面深蓝 suction 块在翼型前缘上方**。这证明：

- cube 旋转 4° → inlet 边界相对翼型弦有 4° 倾角
- k-omega SST 解出非对称压力分布
- 流场真的生成 lift

**这正是 v2 做不到的事**——v2 α=0 所以压力场是对称的。

## setBaseSize 8 条 path 完整失败原因表

| Path | API | 失败原因 |
|---|---|---|
| 1 | `AutoMeshDefaultValuesManager.setBaseSize(Units, double)` | NoSuchMethodException |
| 2 | `AutoMeshDefaultValuesManager.setBaseSize(double, Units)` | NoSuchMethodException |
| 3 | `AutoMeshDefaultValuesManager.setBaseSize(double)` | NoSuchMethodException |
| 4 | `AutoMeshDefaultValuesManager.getCustomMeshSize()` | NoSuchMethodException |
| 5 | `AutoMeshOperation.getCustomMeshSize()` | NoSuchMethodException |
| 6 | `AutoMeshOperation.getBaseSize().setDefinition()` | NoSuchMethodException on getBaseSize |
| 7a | `PartCustomMeshControl.setCustomSize(double, Units)` | NoSuchMethodException |
| 7b | `PartCustomMeshControl.setSilently("BaseSize", 0.005)` | 调用成功但 read-back null（值没存进去） |
| 7c | `PartCustomMeshControl.set("BaseSize", 0.005)` | 同 7b |
| 7d | `PartCustomMeshControl.getAutoMeshBase().setBaseSize(...)` | NoSuchMethodException on setBaseSize |
| 7e | `CustomMeshControlValueManager.get(BaseSize.class)` | ClassNotFoundException star.common.BaseSize + others |
| 7f | `CustomMeshControlValueManager.get(String.class, "BaseSize")` | NoSuchMethodException get(String) |
| 7g | `CustomMeshControlValueManager.getObjects()` | 0 children |
| 8 | `AutoMeshDefaultValuesManager.set("BaseSize", 0.005)` | InvocationTargetException null |

**2402 R8 setBaseSize 真实 API 没找到**。可能选项：

- 真的需要 GUI 里手动改
- 或许要 pre-load 一个 .sim 模板（v34 NACA 已 solved sim 里 mesh 是好的，但 mesh
  operation 是 v34 风格的，**该 sim 里有 working setBaseSize 调用链** —— 我们可
  以 introspect 那个 sim 找到正确 path）
- 2402 R8 官方文档 / Siemens forum 上搜 `setBaseSize Java API 2402`

## Cell count 拿不到的原因

- `star.common.CellCountManager` 2402 R8 不存在 (ClassNotFoundException)
- `AutoMeshOperation.getOutputParts()` 路径不返回有代表性 cell count 的对象
- 2402 R8 可能用 `MeshPart.getCellCount()` 或 `Region.getCellCount()`

## 下一步可走的两条路

1. **Introspect v34 已有 solved sim** (`Cases/naca2412_v34_with_reports.sim`,
   14 MB) — 它有 working mesh + V&V。可从那里 introspect 出 setBaseSize 真实 API
   链 + cell count 路径。**ROI 最高**：零新代码，1-2 小时 introspect + 一行 fix。

2. **用户手动改 mesh size + re-solve** — 在 STAR-CCM+ GUI 打开
   `naca2412_v35_true.sim`，Mesh → set base size 0.005 m → run 2000 iter → 看
   PNG。**10 分钟**，但要你操作。

## Cl/Cd 报告值的诚实状态

**仍 broken** (v2 同):
- `ForceCoefficientReport.compute()` NoSuchMethodException
- `getValue()` 返回 unnamed `x/y/z` Vector3，值在不同 α / V 下 bit-identical
  → sentinel or cached
- v3 的 6.512 Cl 是几何旋转 + broken report 共同产物，**不应用作 V&V 比较**

## 真实收获（不动报告只看图的话）

- ✅ α=4° 几何应用到 flow
- ✅ k-omega SST 2000-iter steady 收敛
- ✅ 压力场显示真实翼型 Cp pattern（LE stagnation + upper suction）
- ✅ 速度场显示 BL 沿表面
- ✅ 真 sim 16 MB 保存可用
- ❌ Mesh 稀疏（用户肉眼可见）
- ❌ Cl/Cd 报告值仍 broken（DEC-005 延伸）

## 给你看

- `Cases/Results/naca2412_v35_true.sim` 16.3 MB 2000-iter solved
- `Cases/Results/naca_v35_velocity.png` 67 KB 真 STAR-CCM+ 速度场
- `Cases/Results/naca_v35_pressure.png` 72 KB 真 STAR-CCM+ 压力场（**α=4° 物理证据**）
- `Cases/Results/naca2412_summary.json` (Cl=6.512, Cd=0.134, all_ok=true — 注意 Cl 不可信)
