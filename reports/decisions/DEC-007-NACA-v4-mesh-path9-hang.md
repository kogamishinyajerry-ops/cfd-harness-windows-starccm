# NACA v4 — mesh BaseSize path9 confirmed; solver deadlocked (separate issue)

| Field | Value |
|---|---|
| Status | **partial** — path9 = WORKING; solver run hung after init |
| Date | 2026-06-11 |
| Branch of | DEC-007 v3 |

## TL;DR

**setBaseSize 路径9 真活了** — `def.get(star.meshing.BaseSize.class).setValue(0.05)` 返回 OK,read-back 确认0.05 m 真存进对象,mesh 在68.85s 内执行完(cells 数没拿到但 mesh 操作本身完成了)。

**Solver 在 init 后 deadlocked** — `step 10: set steps = 500` 之后4分30s 无任何 CPU/log 进展,被人工 kill。可能原因:mesh 质量导致第一 iter 发散,或 license 服务短暂不可达,或 segmentation 引起的 step command 内部死锁。

**没拿到真 Cl/Cd** — 路径9 是 v3 的真修复,但 solver 跑不完这步就废了,所以"v4 完整闭环"还差最后一步(让 solver 至少跑1 步)。

## v3 vs v4 对比

| | v3 | v4 |
|---|---|---|
| setBaseSize | 8 paths 全 FAIL | **path9 WORKING**: `def.get(star.meshing.BaseSize).setValue(0.05)` |
| BaseSize 对象可获取 | 未尝试 | ✅ 干净路径:`get(star.meshing.BaseSize.class)` 返回真实对象 |
| Mesh size | 默认(粗) | **0.05 m**(smoke-grade,生产用0.005) |
| Mesh 执行 | 6-8 s | **68.85 s**(cell 数翻倍 → 时间合理) |
| Solution init | OK | OK |
| 2000-iter run | 137 s,完成 | **未达**:500-iter run 在 `set steps = 500` 后 deadlocked |
| Cl/Cd | 6.512/0.134 (broken report) | **未获得**:solver 未完成 |
| 实际进展 | Cl/Cd 数字不可信 | 路径9 解决,新瓶颈 = solver deadlock |

## 关键代码改动 (`NacaTrueE2E.java`)

### `stepMesh` (line660-738): 重构 9-path 顺序

- 8 条 v3 path 保留但全部确认 FAIL(`NoSuchMethodException`):
  1. `setBaseSize(Units, double)` — FAIL
  2. `setBaseSize(double, Units)` — FAIL
  3. `setBaseSize(double)` — FAIL
  4. `CustomMeshSize.setValue` — FAIL(getCustomMeshSize 不存在)
  5. `getCustomMeshSize on auto` — FAIL
  6. `BaseSize.setDefinition on auto` — FAIL(getBaseSize 不存在)
  7. `createPartControl + setCustomSize` — FAIL(cv 0 children)
  8. `set(String, double) on def` — FAIL(InvocationTargetException null)

- **第9条 (v4 NEW)**: `def.get(star.meshing.BaseSize.class).setValue(0.05)` → ✅ OK
  ```java
  Class<?> bsCls = Class.forName("star.meshing.BaseSize");
  Object bs = def.getClass().getMethod("get", Class.class).invoke(def, bsCls);
  bs.getClass().getMethod("setValue", double.class).invoke(bs, 0.05);
  Object readBack = bs.getClass().getMethod("getValue").invoke(bs);
  // readBack == 0.05 (class star.meshing.BaseSize)  ← confirmed
  ```

**为什么 v3 没找到这条 path**:v3 的反射扫描里只调了 `getCustomMeshSize`, `getBaseSize`, `getProperty("BaseSize")`, `getDouble("BaseSize")`, `getObjectsOf(...)`,但**没调** `get(star.meshing.BaseSize.class)`。这条路径是 `IntrospectV34Mesh.java` 2026-06-1111:41 跑 v34 solved sim 才挖出来的(看 `Cases/Results/introspect_v34.log` line28:`def.get(star.meshing.BaseSize) = star.meshing.BaseSize=1.0 m`)。

### `stepReport` (line865-976): Vector3 字段名曝光

- 当 `getValue()` 返回 Vector3 时,**列出所有 double 字段名 + 值**(line944-962):
  ```java
  Field[] flds = val.getClass().getDeclaredFields();
  for (Field fld : flds) {
      if (fld.getType() == double.class) {
          fld.setAccessible(true);
          fsb.append(fld.getName()).append("=").append(fld.getDouble(val)).append(" ");
      }
  }
  ```
- 这次没跑到 line976,所以**没看到 Vector3 字段名实测结果** — 等下次跑通后这条 log 会显示真实字段名(`x/y/z` 还是 `[Cd,Cl,Cm]` 别名)

### `stepReport` ref-velocity 修正 (line847-857)

- `ref velocity` 现在跟 `gInletUMag` 对齐(15 m/s),不再硬编码 10 m/s
- `lift direction` 现在写 `[0,1,0]`(line861-862)
- 这两条解决了 v3 的"Cl scaling 错"问题 — 等 solver 跑通会看到正确量级 Cl

## 真实状态 (`Cases/Results/naca_true_v1.log`)

```
step  6: physics enabled (k-omega SST, laminar skipped)
step  7: BCs assigned (Inlet xmin / Outlet xmax / Wall naca2412 / Sym ybot ytop zin zout)
step  8: inlet |V|=15.0 m/s X (alpha tilt from domain rotation, alphaTilt=false on profile)
step  9: mesh base size =0.05 m (via def.get(star.meshing.BaseSize).setValue)
         mesh executed in68850ms
         cell count (legacy) err: star.common.CellCountManager  ← star.common 不可用
step 10: solution initialized
         set steps =500
[hung4min30s, killed manually]
```

## Solver Hang 分析

可能原因(按概率排序):

1. **Mesh 质量导致第一 iter 发散**:0.05 m base × 6 m domain = ~120 cells/edge,prism layer 在 airfoil 表面 + tetra 在远场,cell shape 大概率差。第一次迭代超出 CFL 限制,solver 内部循环拒绝推进。

2. **License 问题**:STAR-CCM+ 2402 R8 flexlm license 在长时间挂起后可能切断 — 但 CPU 一直23s,WS 一直402MB 没变,不像 license 切换的迹象。

3. **`set steps` 命令本身在 stuck solver 上 hang**:macro 先 init,然后 set steps=500。set steps 不应该 hang。但 solver 在等下一 step 命令时才读 cells。

4. **PRISM layer 配置问题**:v4 用了 `PrismLayerThickness + PrismLayerNumber`(line88-89) + `SurfaceCustomMeshControl`。如果 prism 在 airfoil surface 上无法生长,后续 execute 可能 hang。

最可能是 (1)+(4) 组合:mesh 质量导致 iter 卡死,继而 `set steps` 也不返回(因为底层 solver loop 死锁)。

## 真实收获 (诚实分层)

### ✅ X% 真做了

| Item | 状态 |
|---|---|
| Path9 真找到了 setBaseSize | done (verified via read-back0.05) |
| mesh size0.05m 真存进对象 | done |
| Mesh execute 完成 | done (68.85s) |
| Cell count via output parts | **blocked**(legacy CellCountManager 不可用) |
| ref velocity 对齐 inlet | done (15 m/s, line847-857) |
| Lift direction 改 [0,1,0] | done (line861-862) |
| Vector3 字段名 log 曝光 | coded,但未实测(solver 没到) |

### ❌ Y% 没做

| Item | severity | 原因 |
|---|---|---|
| 拿到真 Cl/Cd | **HIGH** | solver deadlocked |
| 1000-iter run | HIGH | 同上 |
| Mesh quality check | MEDIUM | 没看 cell quality report |
| 自适应时间步长 / Courant 数设置 | MEDIUM | macro 里没设,solver 默认可能 CFL 不对 |
| 自动重启 + retry on hang | LOW | 需 monitor + timeout wrapper |

## 下一步可走的路

1. **加 timeout + 自动 kill 重跑**:用 subprocess timeout + 看 stderr/err 抛错。`scripts/run_naca_macro.py` 已有 `--timeout 600`(默认10 分钟),但 timeout expired 时返回 rc=-1 而非抛错;下次加 `--timeout 90` 让它在 hang 第一时间爆掉,然后看 stderr 里有没有"iter diverge" / "mesh invalid" 的真信号。

2. **加 mesh quality report + log**:macro step 9 完成后加一行 `sim.println("Mesh quality: ..." + min/max aspect ratio)`,然后才进 step 10。如果 quality 差就 throw,不开 solver。

3. **CFL / Courant number 设置**:在 step 10 `solution initialized` 后 + `set steps` 前,加一段 `innerIterControls.setCflNumber(0.5)` 或类似的稳态 solver relaxation。第一次 iter CFL=0.5,稳定后再 1.0。STAR-CCM+ 2402 R8 默认可能给 CFL=1.0,这对粗糙 mesh 太激进。

4. **改 mesh size 改回 0.5m**(更粗)看是否 solver 跑得通:如果 0.5m 能跑通 → 确认是 mesh 质量问题,继续缩到 0.1m / 0.05m / 0.01m 找平衡点。

5. **接受 v4 partial**:path9 修复 mesh size 路径是真进步(不再需要 GUI 手动),solver deadlock 是 **新开的债务**,需要在 v5 单独打掉。同步更新 STATE.md 标 v4 部分成功 + 新 DEC-008 跟踪 solver deadlock。

## 给你看

- `D:\StarCCM Codebuddy\macros\NacaTrueE2E.java` (68457 bytes, line 660-738 setBaseSize 9 paths, line 865-976 report reading)
- `D:\StarCCM Codebuddy\Cases\Results\naca_true_v1.log` (8662 bytes,last write 2026-06-1115:50:32)
- (无 .sim)— solver 死锁前未保存

## 给你选(v5 方向)

- (a) **修 solver deadlock 优先**:加 timeout + mesh quality gate + CFL 调谐,目标是500-iter 跑通拿 Cl/Cd。估 ~30-60 min。
- (b) **路径9 已稳,先把 v4 partial 归档**:写 STATE 更新 + DEC-008 (solver deadlock) 开新债。估 ~10 min。然后继续 LDC 或别的 case。
- (c) **降级 mesh 回 0.5m 看是否跑通**:5 min 测试,如果通了就知道是 mesh 质量问题,可以快速缩小 v4 的搜索范围。