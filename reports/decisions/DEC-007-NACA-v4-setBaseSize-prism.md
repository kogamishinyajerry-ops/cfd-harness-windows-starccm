# NACA v4 — setBaseSize + Prism Layers (DEC-007 v4)

| Field | Value |
|---|---|
| Status | **major win** — setBaseSize working, prism layers visible, BL resolved |
| Date | 2026-06-11 |
| Branch of | DEC-007 v3 |

## TL;DR

**v4 解开了 STAR-CCM+ 2402 R8 的 setBaseSize 真实 API**：通过 introspect v34 已有
solved sim (`naca2412_v34_with_reports.sim`)，发现 BaseSize 的 class 名字是
`star.meshing.BaseSize`（不是 `star.common.BaseSize` 也不是
`AutoMeshDefaultValuesManager.setBaseSize`）。然后用同样套路解开了 prism layer
thickness + number of layers + surface size。**PNG 上现在能看到 BL**。

## v3 vs v4

| | v3 | v4.13 |
|---|---|---|
| setBaseSize 路径 | 8 条 path 全失败 (path 7 silent fail) | **`def.get(star.meshing.BaseSize).setValue(0.05)`** ✅ |
| Prism layers | 默认（相对值, 太厚, 看不到 BL） | **`PrismThickness.setAbsoluteSize(0.001 m)` + 模式 ABSOLUTE** ✅ |
| Number of prism layers | 默认 | **`NumPrismLayers.setNumLayers(10)`** ✅ |
| Mesh base size | 实际 ~0.5m (silent fail 后 default) | **0.05m (显式 set)** |
| Domain | x[-3,5] y[-5.5,5.5] | **x[-2,3] y[-3,3] (smaller for speed)** |
| Mesh time | 8.5s (default coarse) | 45s (real) |
| Run time (200 iter) | 137s (2000 iter) | 864s (200 iter, finer mesh) |
| Velocity PNG BL | 无 | **可见薄 BL 沿翼型** ✅ |
| Pressure PNG | 真实非对称（α=+4°）| 真实非对称，**stagnation + suction** 保留 |

## introspect v34 sim 找到的 2402 R8 真实 API

### AutoMeshDefaultValuesManager 的 children (v34 sim)

`IntrospectV34Mesh.java` introspect 出的 27 个 children，**`BaseSize` 类的完整
路径是 `star.meshing.BaseSize`**：

```
def children:
  BaseSize                                  ← star.meshing.BaseSize
  SurfaceGrowthRate                         ← star.resurfacer.SurfaceGrowthRate
  PartsMinimumSurfaceSize                   ← star.meshing.PartsMinimumSurfaceSize
  PartsTargetSurfaceSize                    ← star.meshing.PartsTargetSurfaceSize
  SurfaceCurvature                          ← star.meshing.SurfaceCurvature
  PartsResurfacerSurfaceProximity           ← star.meshing.PartsResurfacerSurfaceProximity
  ProjectToCadOption                        ← star.meshing.ProjectToCadOption
  PartsAutoRepairMinimumProximity           ← star.meshing.PartsAutoRepairMinimumProximity
  PartsTetPolyDensity                       ← star.meshing.PartsTetPolyDensity
  PartsCoreMeshOptimizer                    ← star.meshing.PartsCoreMeshOptimizer
  PartsTetPolyGrowthRate                    ← star.meshing.PartsTetPolyGrowthRate
  MaximumCellSize                           ← star.meshing.MaximumCellSize
  PartsPostMeshOptimizerBase                ← star.meshing.PartsPostMeshOptimizerBase
  PrismThickness                            ← star.prismmesher.PrismThickness
  NumPrismLayers                            ← star.prismmesher.NumPrismLayers
  PrismLayerStretching
  PrismLayerReductionPercentage
  PrismLayerConcaveAngleLimit
  PrismLayerConvexAngleLimit
  PrismLayerCoreLayerAspectRatio
  PrismLayerGapFillPercentage
  PrismLayerMinimumThickness
  PrismLayerBoundaryMarchAngle
```

### setBaseSize 真实 API

```java
Object def = autoOp.getDefaultValues();
Object bs = def.get(star.meshing.BaseSize);  // Class.forName
bs.setValue(0.05);  // 直接 setValue(double)
```

`BaseSize` 自身是 `ScalarValue` 子类，有 `setValue(double)` + `setDefinition(String)`。
**`AutoMeshDefaultValuesManager` 上没有 `setBaseSize()` / `getBaseSize()` / `getCustomMeshSize()` — 这些 API 在 2402 R8 已被移除。**

### PrismThickness 真实 API

`PrismThickness` 有 **`setRelativeOrAbsolute` 选项 + `setAbsoluteSize(double, Units)` + `setRelativeSize(double)`**。要设绝对值 1mm 必须先 `setRelativeOrAbsolute(ABSOLUTE)` 再 `setAbsoluteSize(0.001, m)`：

```java
Object plt = def.get(star.prismmesher.PrismThickness);
// 1) 切到 ABSOLUTE 模式
Object roa = plt.getRelativeOrAbsolute();
Object absOpt = ...; // NamedEnumeratedOption "Absolute"
roa.setSelected(absOpt);
// 2) 绝对值
plt.setAbsoluteSize(0.001, units);
```

### NumPrismLayers 真实 API

`NumPrismLayers` 有 `setNumLayers(int)` / `getNumLayers()` / `setDefinition(String)`。
**`setValue(int)` 不存在**（setValue 是 ScalarValue 才有的）。

```java
Object pnl = def.get(star.prismmesher.NumPrismLayers);
pnl.setNumLayers(10);
```

### 失败过的弯路（按时间顺序）

1. ❌ `setBaseSize(Units, double)` / `setBaseSize(double, Units)` / `setBaseSize(double)` — 3 个重载全 NoSuchMethodException
2. ❌ `AutoMeshOperation.getCustomMeshSize()` / `getBaseSize()` — 不存在
3. ❌ `def.getCustomMeshSize()` — 不存在
4. ❌ `CustomMeshControlManager.createPartControl().getCustomValues()` — 0 children，无 BaseSize
5. ❌ `def.set("BaseSize", 0.05)` — InvocationTargetException null
6. ❌ `def.setSilently("BaseSize", 0.05)` — 调用成功但 read-back null（值没真存）
7. ❌ `star.common.BaseSize` — ClassNotFoundException
8. ✅ `def.get(star.meshing.BaseSize).setValue(double)` — **working** (v34 introspect 找到)
9. ❌ `PrismLayerThickness` / `PrismLayerNumber` — ClassNotFoundException
10. ✅ `PrismThickness` (without "Layer") + `NumPrismLayers` (without "Layer") — working
11. ❌ `PrismThickness.setValue(double)` / `setDefinition(String)` — 不存在
12. ✅ `PrismThickness.setAbsoluteSize(double, Units)` — working (after setRelativeOrAbsolute(ABSOLUTE))
13. ❌ `NumPrismLayers.setValue(int)` / `setLayerCount(int)` — 不存在
14. ✅ `NumPrismLayers.setNumLayers(int)` — working

## v4 macros / scripts 新增

- `D:\StarCCM Codebuddy\macros\IntrospectV34Mesh.java` (192 行) — load v34 sim
  + introspect mesh + reports
- `D:\CFD-harness-Windows-StarCCM\scripts\run_introspect_v34.py` — Python 3.11
  driver, spawns `starccm+.bat <v34 sim> -batch IntrospectV34Mesh.java`
- `D:\StarCCM Codebuddy\macros\NacaTrueE2E.java` v4 (1185 行) — 4-mesh pipeline +
  v4 base size + prism thickness absolute + num prism layers

## 真实 PNG 证据 (v4.13)

### 速度场 (v4.13)

`Cases/Results/naca_v35_velocity.png` (71 KB): 翼型右侧。**关键改进：**
vision model 看到 "a very thin, dark/blue line tracing the immediate edge" —
**沿翼型表面有可见 BL 薄层**。v3 完全看不到 BL，v4.13 有明显 BL。

### 压力场 (v4.13)

`Cases/Results/naca_v35_pressure.png` (82 KB): 仍然 blocky（因为体网格 0.05m 还
是粗），但 α=+4° 的 stagnation (高压力在 LE 下侧) + suction (深蓝在上侧) 物理
完全保留。

## 测得 timing 数据

| 配置 | Mesh | Run (200 iter) | Total |
|---|---|---|---|
| v3 default mesh (path 7 silent fail) | 8.5s | 137s (2000 iter) | ~150s |
| v4.4 0.5m + 4-mesh | 26s | 403s (200 iter) | ~440s |
| v4.7 0.05m + small domain + 4-mesh | 39s | 980s (500 iter) | ~1100s |
| v4.13 0.05m + prism 0.001m/10 + 4-mesh + small domain | 45s | 864s (200 iter) | ~930s |

## 真实交付物 (2026-06-11 15:32)

- `D:\StarCCM Codebuddy\Cases\Results\naca2412_v35_true.sim` 114 MB 200-iter solved
- `D:\StarCCM Codebuddy\Cases\Results\naca_v35_velocity.png` 71 KB 真 STAR-CCM+
  速度场 (BL 可见)
- `D:\StarCCM Codebuddy\Cases\Results\naca_v35_pressure.png` 82 KB 真 STAR-CCM+
  压力场
- `D:\StarCCM Codebuddy\Cases\Results\naca2412_summary.json` Cl=8.42, Cd=-0.40

**注**: Cl/Cd 仍依赖 broken `ForceCoefficientReport.getValue()` (DEC-005)。Cl 数字
不可信，但 **PNG 物理图案 + BL 可见** 是真 CFD 证据。

## DEC-005 状态

仍是 open。`ForceCoefficientReport.compute()` NoSuchMethodException,
`getValue()` 返回 unnamed `x/y/z` Vector3 sentinel。下一步 v5:
- 试 `getValue(ClientServerObject)` overload
- 试通过 `getReportMonitorValue()` 读 monitor
- 试 scene-based pressure integral 绕开 broken report

## v5 next steps (你指示)

- [ ] DEC-005: scene-based pressure integral 算 Cl (可信)
- [ ] v4 + 2000 iter 完整跑一次 (38 min 一次)
- [ ] 测试 0.02m 更细 (大域 + 完整 Re=6e6) — 可能 60+ min
