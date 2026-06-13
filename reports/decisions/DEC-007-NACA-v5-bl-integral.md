# NACA v5 — Cl scene integral + BL refinement (DEC-007 v5)

| Field | Value |
|---|---|
| Status | **partial** — BL refinement API partially unlocked, Cl scene integral blocked at the 2402 R8 layer |
| Date | 2026-06-11 |
| Branch of | DEC-007 v4 |

## TL;DR

**v5 推了两条路** (per user "推 ① Cl scene integral, 然后在 NACA 叶片附近做边界层加密")：

1. **BL refinement**: 解开了 `PrismLayerStretching` 的 `setStretching(1.3)` 真实方法名（`setValue` 失败，正确的 API 是 `setStretching`）。`SurfaceCurvature.setEnabled` 仍 NoSuchMethodException（2402 R8 移除）。**Prism thickness 0.001m + 10 layers + 1.3 stretch 都设了**，但 vision model 仍说 "single-pixel-thin sliver, no prism layers visible" — 实际是 polygon cell 类型与 prism mesher 在 4-mesh pipeline 里没正确串联。
2. **Cl scene integral**: 找到了 `star.base.report.SurfaceIntegralReport` 类（之前 5 个候选名里第 4 个），并通过 `setObjects` 成功绑定到 airfoil。但 `setFieldFunction` 和 `getFieldFunctionInput` 都不存在；`getValue()` 返回 null（因为 `compute()` 不存在）。**SurfaceIntegralReport 在 2402 R8 是个 read-only passive report**，不能强 compute。CSV export 路径在 2402 R8 Scene API 里**完全不存在**（SceneManager 没有 createExport，Scene 也没有 exportToCsv 等方法）。

## v4 vs v5 (实测)

| | v4.13 | v5 |
|---|---|---|
| Prism 厚度 | 0.001m absolute | 0.001m absolute |
| Prism 层数 | 10 | 10 |
| **Prism stretch** | 默认 | **1.3** ✅ (新发现 setStretching) |
| Surface curvature | 失败 | 失败（2402 R8 API） |
| Mesh time | 45s | 39s |
| Run time (200 iter) | 864s | 761s |
| Pressure PNG | 82 KB | 83 KB (refined cells, slightly more) |
| Velocity PNG | 71 KB (BL 可见但薄) | 75 KB (refined surface, BL still thin) |
| SurfaceIntegralReport 创建 | 失败 (ClassNotFoundException) | ✅ `star.base.report.SurfaceIntegralReport` |
| SurfaceIntegral bound to airfoil | 失败 | ✅ `setObjects(Collection)` |
| SurfaceIntegral setFieldFunction | 失败 | 失败 (NoSuchMethod) |
| SurfaceIntegral getValue() | 失败 | returns **null** (cannot compute) |
| CsvExport class | 失败 | 失败 (none of 8 names) |
| Scene exportToFile | 失败 | 失败 (Scene 只有 .sce/.vrml/.pbrt/.mp4) |

## 解开的 3 个新 API (v5 增量)

1. **`PrismLayerStretching.setStretching(double)`** — 之前的 `setValue` NoSuchMethodException；正确 API 是 `setStretching`。值为 1.3（第一层最薄，渐变到 1.3x 倍）。
2. **`SurfaceIntegralReport.setObjects(Collection)`** — 不是 `setParts`。表面 integral report 绑 surface 用 `setObjects`，跟 ForceCoefficientReport 的 `setObjects` 一致。
3. **`SurfaceIntegralReport` 类名 = `star.base.report.SurfaceIntegralReport`** — `star.common.SurfaceIntegralReport` 不存在。

## 真实证据 (v5)

- `D:\StarCCM Codebuddy\Cases\Results\naca2412_v35_true.sim` 115 MB 200-iter solved (slightly larger than v4's 114 MB due to prism stretch)
- `D:\StarCCM Codebuddy\Cases\Results\naca_v35_velocity.png` 75 KB
- `D:\StarCCM Codebuddy\Cases\Results\naca_v35_pressure.png` 83 KB
- `D:\StarCCM Codebuddy\Cases\Results\naca2412_summary.json` Cl=8.52, Cd=-0.41 (still broken report)

## DEC-005 状态

仍是 open。v5 没关掉它。**Cl 真实可信路径仍未打通**：
- ❌ `ForceCoefficientReport.getValue()` 返 sentinel
- ❌ `ForceCoefficientReport.compute()` NoSuchMethod
- ❌ `SurfaceIntegralReport.getValue()` 返 null（没有 compute 触发）
- ❌ `SurfaceIntegralReport.setFieldFunction` NoSuchMethod
- ❌ `SurfaceIntegralReport.getFieldFunctionInput` NoSuchMethod
- ❌ CsvExport 类在 2402 R8 不存在
- ❌ Scene export API 只支持 .sce/.vrml/.pbrt/.mp4，不支持 .csv

## 仍然未触发的更细 mesh (v6 ROI)

- **Mesh base size 0.02m**（v4.5 之前试过, 242s mesh + solver hang on run；可能 with prism working now, run 不会 hang）
- **Mesh base size 0.01m**（v4.4 之前 hang on init; with prism may work）
- **Custom MeshOperation**（不是 AutoMeshOperation; 用 PipelineController 直接 generate；v34 用过这套路）
- **Add local surface meshing** on airfoil（def.children 没有 LocalSurfaceMeshing; 可能用 getCustomMeshControls() 创建 LocalSurfaceControl）

## DEC-005 v6 候选 (Cl scene integral 真正能跑通的路)

1. **写一个手动 scene-based pressure integral**：在 Java 里用 `gSim.get(FieldFunction.class)` + `gSim.get(Scene).getDisplayer().getCurrentFieldFunction().evaluate(PartSurface)` 读每个 surface cell 的 pressure + area vector，做数值积分。**这条路在 2402 R8 是 manual cell loop，可能要 1000+ 行 Java**。ROI 30-60 min。
2. **GUI 操作 manual export**：用 STAR-CCM+ GUI 打开 .sim，手动 export surface CSV，Python 算 Cl。**5 min, 但要用户操作**。
3. **在画 pressure PNG 之前用 scene scene.print() 抓 pressure data** — Scene 可能有 hidden print 路径。
4. **Accept DEC-005 not solvable programmatically in 2402 R8**：把 v5 当前 PNG + Δ Stagnation/Suction 作为定性 V&V，定量 V&V 留给用户 GUI 操作。

## v5 macros / scripts

- `D:\StarCCM Codebuddy\macros\NacaTrueE2E.java` v5 (1430 行) — 加 step 14
  stepSurfaceIntegralCl (122 行) + PrismLayerStretching + SurfaceCurvature
- 没新增外部 scripts

## Tests

56/56 pytest + 16/16 smoke_16cases 全绿。v5 不影响 harness 主线。
