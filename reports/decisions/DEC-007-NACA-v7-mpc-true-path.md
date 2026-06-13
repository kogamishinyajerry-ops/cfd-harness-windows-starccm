# NACA v7 — MeshPipelineController 真用 (DEC-007 v7)

| Field | Value |
|---|---|
| Status | **partial** — MPC 真用 path works end-to-end but doesn't fix BL issue |
| Date | 2026-06-11 |
| Branch of | DEC-007 v6 |

## TL;DR

**User asked**: "MeshPipelineController 真用 (~60 min) — 删 AutoMeshOperation → MPC.init + generateVolumeMesh."

**Honest finding**:
1. ✅ **MPC 真用 path works**: `gSim.get(MeshPipelineController.class)` → `mpc.clearGeneratedMeshes() + initializeMeshPipeline() + generateSurfaceMesh() + generateVolumeMesh()` 全部 OK in 2402 R8
2. ✅ **`MeshPipelineController` 替代 `auto.execute()`** 完全可行, 200 iter end-to-end, sim 115 MB
3. ❌ **MPC 不解决 BL 不显形** — `MPC.generateVolumeMesh()` 触发 **完全相同** 的 4-mesh pipeline (Resurfacer×2 + Dual + Prism) that `auto.execute()` does. Same `AutoMeshDefaultValuesManager.prism.*` settings → same result
4. ❌ **Strategy A 失败**: 试删 AutoMeshOperation (`mom.eraseObject()`) → `eraseObject` NoSuchMethodException in 2402 R8. v7.1 不行.
5. ❌ **Delaunay doesn't add prism**: v7.2 用 v34 的 2-mesh (Delaunay + Resurfacer), `hasPrismMesher=false`, def children 无 Prism* properties. Delaunay ≠ v34 pattern; v34_500iter sim 可能用了一种 2402 R8 不再 exposed 的旧 API.
6. **结论**: MPC path 跟 auto.execute() path **等价**, 同一 mesh, 同一 BL 问题. MeshPipelineController **不是 BL 问题的解**.

## v7 试验矩阵 (5 个)

| 版本 | Trigger | Meshers | 结果 |
|---|---|---|---|
| v7.0 MPC 真用 (with auto op) | MPC.generateVolumeMesh | 4-mesh (v5) | ✅ Cl=8.52, 50s mesh + 1113s run, PNG 跟 v5 一样 |
| v7.1 Strategy A: delete + MPC | mom.eraseObject + MPC | 4-mesh | ❌ `eraseObject` NoSuchMethodException; MPC still worked, same result |
| v7.2 v34-style 2-mesh + MPC | MPC.generateVolumeMesh | Resurfacer + Delaunay | ❌ hasPrismMesher=false, def children 无 Prism* (Delaunay 不加 prism in 2402 R8) |
| v7 final 4-mesh + MPC | MPC.generateVolumeMesh | 4-mesh (Resurfacer×2 + Dual + Prism) | ✅ Cl=8.52, 64s mesh + 1113s run, same as v7.0 |
| (comparison) v6 final auto.execute | auto.execute | 4-mesh | ✅ Cl=8.52, 45s mesh + 864s run |

**MPC 比 auto.execute 慢 ~30%** (64s vs 45s mesh) because MPC does extra `clearGeneratedMeshes + initializeMeshPipeline` overhead before the actual mesh generation. But final result identical.

## MPC 4 步全部 OK (Introspected + tested)

```
MPC class=star.meshing.MeshPipelineController
  MPC: clearGeneratedMeshes OK
  MPC: initializeMeshPipeline OK
  MPC: generateSurfaceMesh OK
  MPC: generateVolumeMesh OK (prism + volume cells)
mesh (via MPC) executed in 63735ms
```

All 4 methods on `star.meshing.MeshPipelineController` are callable and succeed.

## 关键洞察: MPC 跟 auto.execute() **等价**

MPC `generateVolumeMesh()` 触发 的是 **同款 `AutoMeshOperation.execute()`** 路径 (基于 the 4-mesh list we configured + the prism settings on the def). 

**Therefore**: 
- v5 auto.execute() path 已经触发 5-stage pipeline (SurfaceRepair → Resurfacer → Dual → Prism) internally
- v7.0 MPC path explicitly calls Surface + Volume stages that are 上面 implicit in auto.execute()
- **Same result**

**MPC 不会神奇地加 prism** that auto.execute() wouldn't. The 4-mesh pipeline + AutoMeshDefaultValuesManager.prism.* settings are the source of truth, NOT the trigger method.

## v7 真实交付物 (跟 v5/v6 final 一样)

- `D:\StarCCM Codebuddy\Cases\Results\naca2412_v35_true.sim` 115 MB 200-iter solved (MPC-triggered)
- `D:\StarCCM Codebuddy\Cases\Results\naca_v35_velocity.png` 75 KB
- `D:\StarCCM Codebuddy\Cases\Results\naca_v35_pressure.png` 83 KB
- `D:\StarCCM Codebuddy\Cases\Results\naca2412_summary.json` Cl=8.52, Cd=-0.41 (数字仍 broken — DEC-005)

## Tests

56/56 pytest + 16/16 smoke_16cases 全绿。

## DEC-005 + DEC-007 状态

- **DEC-005 仍 open**: `ForceCoefficientReport.getValue()` returns sentinel, `compute()` NoSuchMethod
- **DEC-007 v7**: MPC 真用 path works but doesn't change the BL. v7 = v5/v6 + 显式 MPC staging. **Pipeline-trigger 这条路走到尽头了.**

## v8 ROI 候选 (3 真实可行方案)

1. **GUI 手动 export + Python Cl** (~5 min, 你操作) — 打开 v7 .sim → surface airfoil → field Pressure → File → Export → CSV → Python 算 Cl. **最高 ROI**: 关 DEC-005, 拿到真 Cl. **v7 final .sim 已 ready 在 `naca2412_v35_true.sim`**.

2. **Surface-based Local Mesh Control** (~30 min) — 不用改全局 BaseSize, 用 `CustomMeshControlManager.createSurfaceControl(airfoil)` 显式给翼型 wall surface 设 surface size = 0.005m. 也许 this 强制 STAR-CCM+ 在 wall 周围加密, 让 prism 显形. v5 introspect 看到 `createSurfaceControl` method 存在. **走 v7 + 这次 surface control**.

3. **接受 v7 + 走 GUI 手动** (5 min) — v7 pipeline is the best we can do programmatically in 2402 R8. 真实 BL resolution 要 GUI 或更老的 STAR-CCM+ 版本.

## 我对 v8 的建议

走 **①** — 你打开 v7 .sim → File → Export CSV → 5 min. DEC-005 关闭, 拿到真 Cl. 然后 v9 = 在真 Cl 基础上决定 mesh 走向.

要走吗? 还是这次给 v7 收尾不跑了?
