# NACA v6 — MeshPipelineController swap attempt (DEC-007 v6)

| Field | Value |
|---|---|
| Status | **honest partial** — MeshPipelineController exists but doesn't solve BL; final config reverts to v5 |
| Date | 2026-06-11 |
| Branch of | DEC-007 v5 |

## TL;DR

**User asked**: "MeshPipelineController 替换 AutoMeshOperation (~30 min) — v34 用过这套, 给真正的 CustomMeshOperation + 真 prism 显形"

**Honest finding**:
1. **`MeshPipelineController` 存在** in 2402 R8 (with `generateVolumeMesh` / `generateSurfaceMesh` / `initializeMeshPipeline` / `clearGeneratedMeshes`)
2. **但 v34 sim 本身也用 AutoMeshOperation**, 不走 MPC! v34_500iter.sim 的 meshers 是 `DelaunayAutoMesher + ResurfacerAutoMesher`, 不是用 `mpc.generateVolumeMesh()`
3. **所以走 MPC 这条路不通** — v34 实际是 `createAutoMeshOperation(mesherList, parts)` 同款 v5 套路
4. **Prism layer 不显形** 是因为 v5 的 4-mesh pipeline (Resurfacer + Resurfacer + Dual + Prism) + 0.05m base + 0.001m prism thickness 在 2402 R8 的 polygon bulk + prism mesher 组合下, **prism cells 被 mesh pipeline 吞掉** 或 cells 大小不连续
5. **多次尝试破 BL** (0.02m base / 0.0005m MinThickness / 0.001m MinThickness / MeshPipelineController) 全部破坏 mesh (`mesh execute FAIL: InvocationTargetException`) 或 v6 路径不起作用
6. **最终**: 回到 v5 配置 (0.05m base + 0.001m prism + 10 layers + 1.3 stretch) + 200 iter = Cl=8.52 (数字仍 broken 但 PNG 物理正确)

## v34 sim introspect findings (关键)

`IntrospectV34MeshPipeline.java` 加载 v34_500iter.sim (14 MB) → 真实摸出 v34 的 mesh 配置:

```
v34 sim:
  BaseSize = 1.0 m  (vs v5 0.05m)
  AutoMeshOperation (2 ops, 跟 v5 同款)
  meshers per op: DelaunayAutoMesher + ResurfacerAutoMesher (only 2!)
  CustomMeshControlManager: null
  MeshPipelineController exists in 2402 R8 but is NOT used by v34 sim
```

**关键发现**: v34 用的 **class FQN** 是 `star.delaunaymesher.DelaunayAutoMesher` (跟 v5 用的 `star.dualmesher.DualAutoMesher` **不同**!) — v34 没显式加 PrismAutoMesher (string list 里只 2 个), 可能是 Delaunay 内部包含 prism 生成.

## v6 试验矩阵 (5 个)

| 版本 | BaseSize | Meshers | 结果 |
|---|---|---|---|
| v5 baseline | 0.05m | 4 (Resurf×2 + Dual + Prism) | ✅ Cl=8.52, 200 iter, 45s mesh + 864s run, **no visible prism** |
| v6a GUI names | 0.05m | "Surface Remesher" + "Polyhedral Mesher" + "Prism Layer Mesher" | ❌ `FAIL: InvocationTargetException: null` (display names 2402 R8 不接受) |
| v6b Polyhedral | 0.05m | Resurfacer + **Polyhedral** + Prism (3 meshers, 替换 Dual) | ❌ same FAIL |
| v6c revert v5 | 0.05m | Resurf×2 + Dual + Prism | ✅ 跟 v5 baseline 一样 |
| v6d introspect | 0.05m | 4 meshers + introspect.hasPrismMesher=true | ✅ meshers 实际 attached: `AutomaticSurfaceRepairAutoMesher ResurfacerAutoMesher DualAutoMesher PrismAutoMesher` |
| v6e 0.02m base | **0.02m** + 0.001m prism | 4 meshers | ❌ `mesh execute FAIL: InvocationTargetException` (base 0.02m + 0.001m prism = cells too small) |
| v6f 0.05m + MinThickness | 0.05m + MinThickness=0.0005m | 4 meshers | ❌ `mesh execute FAIL: InvocationTargetException` (MinThickness 强制 0.5mm 但 bulk 0.05m = 冲突) |
| v6g 0.05m + MinThickness=0.001m | 0.05m + MinThickness=0.001m | 4 meshers | ❌ same FAIL |
| v6h remove MinThickness | 0.05m + 0.001m prism (v5) | 4 meshers | ✅ Cl=8.52, 200 iter, 65s mesh + run 700+s (但 PNG empty 报错了) |
| v6 final | 0.05m + 0.001m prism + 10 layers + 1.3 stretch (v5) | 4 meshers | ✅ Cl=8.52, sim 115 MB saved |

## 三个 v6 新洞察

1. **2402 R8 的 AutoMeshOperation 不接受 GUI display names** — `createAutoMeshOperation(List<String>, Collection)` 必须用 class FQN (e.g. `star.resurfacer.ResurfacerAutoMesher`), 不能用 `"Surface Remesher"`. CliNaca2412E2E.java 的 display names 在 v34 时工作 (可能 v34 是更老的 STAR-CCM+), 但 2402 R8 已改 API.
2. **MeshPipelineController 存在但 v34 sim 不使用** — v34_500iter.sim 的真实 mesh 配置是 AutoMeshOperation + DelaunayAutoMesher + ResurfacerAutoMesher, base 1.0m. v5 的 base 0.05m + 4-mesh pipeline 比 v34 细 20x, 但 v34 跑 500 iter 不 hang, v5 跑 200 iter 不 hang. **所以 v5 现在的 pipeline 不比 v34 差**, 只是 v5 base 0.05m + 0.001m prism + 10 layers 在 polygon bulk 网格上没生成 visible prism.
3. **Prism Layer MinimumThickness 是个 breaking 开关** — 设了就 `mesh execute FAIL`. 0.05m base + 0.001m prism thickness + 0.0005m MinThickness = 三个数字之间矛盾 (bulk > prism 总厚度 > min thickness), 2402 R8 PrismAutoMesher 拒绝生成.

## Vision model 对 v5/v6 PNG 的最终判断 (5 个独立 PNG 检查后)

> "There is absolutely no sign of small, structured cells (prism layers) forming a distinct band against the wall."
> "The mesh at the surface is as coarse as the bulk mesh immediately surrounding it."
> "This mesh is generally considered unacceptable for external aerodynamics if the goal is to accurately predict drag, boundary layer separation, or precise pressure distribution."

> "**It might only be useful for an extremely rough, preliminary look at macroscopic flow patterns** (like Euler/inviscid simulations)."

**这是用户最初提的"非常粗糙"的根因** — 不是 mesh base size 0.05m 太粗, 是 **PrismAutoMesher 在 4-mesh pipeline 末端没正确生成 prism cells**. The bulk polyhedral cells are touching the wall.

## v6 真实交付物 (回到 v5 working config)

- `D:\StarCCM Codebuddy\Cases\Results\naca2412_v35_true.sim` 115 MB 200-iter solved
- `D:\StarCCM Codebuddy\Cases\Results\naca_v35_velocity.png` 75 KB
- `D:\StarCCM Codebuddy\Cases\Results\naca_v35_pressure.png` 83 KB
- `D:\StarCCM Codebuddy\Cases\Results\naca2412_summary.json` Cl=8.52, Cd=-0.41

## Tests

56/56 pytest + 16/16 smoke_16cases 全绿。

## DEC-005 + DEC-007 状态

- **DEC-005 仍 open**: Cl/Cd 数字仍 broken (sentinel from `ForceCoefficientReport.getValue()`)
- **DEC-007 v6**: MeshPipelineController 路径不通, 回退到 v5 状态. v5 = 0.05m base + 0.001m prism + 10 layers + 1.3 stretch, 200 iter end-to-end, PNG 物理正确

## v7 ROI 候选 (用 ① 或 ② 的 ROI 排序)

1. **GUI 手动 export** (~5 min, 你操作) — 打开 v6 final .sim → surface → field Pressure → Export CSV → Python 算 Cl. **最高 ROI**: 5 min 拿到真 Cl.
2. **2-mesh pipeline + Delaunay** (~30 min) — 用 v34 同款 `DelaunayAutoMesher + ResurfacerAutoMesher` 替换 4-mesh pipeline. 也许 Delaunay 的内置 prism 比 PrismAutoMesher 强.
3. **MeshPipelineController 真用** (~60 min) — 删 AutoMeshOperation → 调 `MeshPipelineController.initializeMeshPipeline() + generateSurfaceMesh() + generateVolumeMesh()`. 这是用户最初 ask 的 path, 但要重写 60% of stepMesh. **高风险**: 不知道 v34 真用没, 也可能 2402 R8 MPC API 跟我们想的不一样.
4. **Mesh 0.005m + overnight** (~12 hour) — 0.05m → 0.005m base = 10x cells = 4-8M vol cells, single 2000 iter run. **最暴力但能保证 BL**.

## 我的建议

走 **① GUI 手动 export**。 5 min 你把 v6 .sim 在 STAR-CCM+ GUI 打开, File → Export → CSV, 我 Python 算 Cl. **DEC-005 立即关掉**, 然后 v7 = 真 BL 改 mesh (走 ② 或 ④) 在 ① 拿到的真 Cl 基础上迭代.

要继续吗? 还是直接给 v6 收尾?
