# NACA v8 — LocalSurfaceMeshControl + Surface-level BL refinement (DEC-007 v8)

| Field | Value |
|---|---|
| Status | **partial** — SurfaceCustomMeshControl 在 2402 R8 不能用 Java 反射绑定到 airfoil; Java-side BL refinement 走到尽头 |
| Date | 2026-06-11 |
| Branch of | DEC-007 v7 |

## TL;DR

**User said "继续"** — 我走 ② Surface-based Local Mesh Control 路径 (那条 ROI 排序里 Java 端唯一能跑的路).

**Honest finding**:
1. ✅ **`createSurfaceControl()` no-args works** (return SurfaceCustomMeshControl)
2. ✅ **`cv.set("SurfaceSize", 0.005)` sets the SurfaceSize value** on the custom values bag
3. ❌ **`setObjects(Collection)` / `setGeometryObjects(ClientServerObject)` / `cmc.add(surfCtrl)` / `cmc.addObjects(surfCtrl)` / `cmc.setObjects(airfoil)` 全部失败** — can't bind the control to the airfoil
4. ❌ **`setApplyOnlyToContact(false)` doesn't help** — control's GeometryObjectGroup still 0 members
5. ❌ **2402 R8 binding 需要 `setGeometryObjectsInput(DynamicQuerySelectorInput)` 复杂 query system** — beyond Java reflection
6. ❌ **Result: 控制 unbound, 不影响 mesh** — Cl 仍 8.52, PNG 跟 v5/v6/v7 一样

**v8 是 8 次 Java-side 试探的终点** — 真 BL resolution 需 GUI 手动 export + 用户操作 (⑤ 路径).

## v8 试验矩阵 (7 个)

| 版本 | 尝试 | 结果 |
|---|---|---|
| v8.0 修正 airfoil search | match "naca" or "airfoil" | ✅ matched `naca2412 (part Airfoil)` |
| v8.1 `createSurfaceControl(Collection)` | wrong sig | ❌ NoSuchMethod |
| v8.2 `createSurfaceControl()` no-args | correct sig | ✅ returns SurfaceCustomMeshControl |
| v8.3 `setObjects` on control | wrong API | ❌ NoSuchMethod |
| v8.4 `cmc.setObjects` / `addObjects` | cmc.setObjects needs ClientServerObject[] | ❌ InvocationTarget null |
| v8.5 `setGeometryObjects(CSO)` / `cmc.add(CSO)` | not on this class | ❌ NoSuchMethod |
| v8.6 introspect surfCtrl methods | — | revealed 28+ methods including `setGeometryObjectsInput(DynamicQuerySelectorInput)` |
| v8.7 `setEnableControl(true)` + `setApplyOnlyToContact(false)` | controls enabled but GeometryObjectGroup empty | ❌ still no effect |
| v8.8 enumerate existing controls in cmc | cmc.getObjects() returns Object not Collection | ❌ 0 existing controls (we're the only one) |

## 3 个 v8 新洞察

1. **`createSurfaceControl()` 是 no-args, not Collection** — `Collection` overload 不存在 in 2402 R8. 找到正确 sig 通过 introspect.
2. **`cv.set(String, double)` works** for setting named properties (e.g. "SurfaceSize") — `getSurfaceSize` + `setValue` pattern 失败, 但 `set(String, double)` works.
3. **2402 R8 SurfaceCustomMeshControl binding needs `setGeometryObjectsInput(DynamicQuerySelectorInput)`** — a complex query system, requires creating a query selector with class+property+value+operator. **不可行 via Java reflection** in reasonable time.

## v8 真实交付物 (跟 v5/v6/v7 一样)

- `D:\StarCCM Codebuddy\Cases\Results\naca2412_v35_true.sim` 115 MB 200-iter solved
- `D:\StarCCM Codebuddy\Cases\Results\naca_v35_velocity.png` 75 KB
- `D:\StarCCM Codebuddy\Cases\Results\naca_v35_pressure.png` 83 KB
- `D:\StarCCM Codebuddy\Cases\Results\naca2412_summary.json` Cl=8.52, Cd=-0.41

## Tests

56/56 pytest + 16/16 smoke_16cases 全绿。

## 8 次 Java-side 试探总结 (DEC-007 v1 → v8)

| Version | 关键 attempt | 真实进展 |
|---|---|---|
| v1 | NACA pipeline end-to-end | Cl=0.01 (默认), pipeline green |
| v2 | α-tilt via API | 4 种 path 全被 2402 R8 拒 |
| v3 | cube 旋转 4° | α=4° 几何生效 (PNG 证实), 8 setBaseSize path 全失败 |
| v4 | introspect v34 sim → `def.get(star.meshing.BaseSize).setValue(0.05)` | ✅ BL 可见 (vision: "thin dark/blue line") |
| v5 | `PrismLayerStretching.setStretching(1.3)` + SurfaceIntegralReport 试 | ✅ stretch 生效, SurfaceIntegral 绑到 airfoil OK, 但 `getValue()=null` |
| v6 | MPC + 各种 mesh config 试 | 9 个 config 全撞墙 (mostly mesh FAIL), 最终回 v5 |
| v7 | `MPC.generateVolumeMesh()` 真用 | ✅ 4 步全 OK, **但等价于 auto.execute** (same result) |
| v8 | LocalSurfaceMeshControl 绑 airfoil | ✅ Control 创建 + SurfaceSize set, ❌ 不能绑 (2402 R8 需 DynamicQuerySelectorInput) |

**Pipeline 触发 (auto.execute / MPC.generateVolumeMesh) 都不解决 BL 不显形** — 同样 4-mesh pipeline, 同样 def.prism.* settings, 同样 result. 触发 method 不是问题.

**PrismAutoMesher 在 2402 R8 4-mesh pipeline 末端不生成 visible prism cells** — bulk polyhedral cells 接触 wall. **这可能是 2402 R8 的 bug 或 limited feature**, 需 GUI 验证.

**SurfaceCustomMeshControl binding 在 2402 R8 需 DynamicQuerySelectorInput** — Java 反射做不了, GUI 可手动.

## DEC-005 + DEC-007 状态

- **DEC-005 仍 open**: Cl/Cd 数字仍 broken
- **DEC-007 v8**: Java-side 试探到尽头. **真实 BL + 真实 Cl 这两条路都需要 GUI**.

## v9 候选 (只能 GUI)

1. **GUI 手动 export airfoil surface Pressure CSV** (~5 min, 你操作) — 打开 v8 .sim → Derived Parts → airfoil wall → Field Function Pressure → File → Export → CSV → 我 Python 算 Cl. **关 DEC-005**
2. **GUI 手动改 mesh + 看 BL** (~10 min, 你操作) — 打开 v8 .sim → Mesh → set BaseSize 0.005m + CustomMeshControl on airfoil = 0.002m → 重 run. **真正 BL 显形**

## 我的建议 (v8 final)

走 **① GUI 手动 export** + **② GUI 手动改 mesh** (两步都 5-10 min). 一旦拿到真 Cl + 真 BL, DEC-005 + DEC-007 都能 close.

如果你现在没法 5-10 min 操作 GUI, 我可以停在这里, 把 v8 当 final 收尾, 你明天再做 GUI 步骤. 你说哪个?

要继续 GUI 操作 ①, 还是停在这里, 等你明天 GUI 操作?
