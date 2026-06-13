# D-7 · EnableModelProbe 编译结果 · RotatingReferenceFrame 2402 R8 探测

> **结论速读**:**`star.motion.RotatingReferenceFrame` 存在**;`star.flow.*` /
> `star.rotor.*` / `star.rotating.*` 三个候选**全部 ClassNotFoundException**。

## TL;DR

1. **编译**:`javac -encoding UTF-8 macros/EnableModelProbe.java` 退出码 **0**(无
   classpath 也 OK,加 classpath 也 OK)。
2. **运行(额外做)**:把 `star-coremodule.jar` + `starbase.jar` + `starice.jar`
   放 classpath 跑 `java EnableModelProbe`,**4 个候选 1/4 resolved**。
3. **归类**:`star.motion.RotatingReferenceFrame` = continuum-level 物理模型
   (类比 `star.turbulence.LaminarModel` 的 enable 范式)。
4. **8 月含义**:3D 单通道叶片 7 月前置条件已满足 1/2;类存在 ≠ enable 成功,
   完整 1 次 90s spawn 留 7/20-7/25 关 D-7 闭环。

## javac 编译

```bash
"C:\Program Files\Siemens\19.02.009-R8\jdk\win64\jdk17.0.8\bin\javac.exe" \
  -encoding UTF-8 macros/EnableModelProbe.java
```

- **退出码**:`0`,无 stderr,产生 `EnableModelProbe.class` 2.2 KB
- 加 STAR-CCM+ classpath 重测也退出码 0(源码不 import star.*,classpath 冗余但无害)

## 运行时探针输出(额外做的,30 行 ≤ 预算)

```bash
java -cp "...\star-coremodule.jar;...\starbase.jar;...\starice.jar;macros" EnableModelProbe
```

```
NOT_FOUND: star.flow.RotatingReferenceFrame     -> ClassNotFoundException
NOT_FOUND: star.rotor.RotatingReferenceFrame    -> ClassNotFoundException
FOUND:     star.motion.RotatingReferenceFrame   -> star.motion.RotatingReferenceFrame
NOT_FOUND: star.rotating.RotatingReferenceFrame -> ClassNotFoundException
=== SUMMARY: 1 / 4 candidate class names resolved on this classpath ===
```

> track-b §5 候选列表过时:track-b 提到 `star.rotating.*`,本次 NOT_FOUND。
> 建议 chief-engineer 通知 track-b owner 收窄到 1 个 `star.motion.*`。

## 推断(归类 → D-7 GREEN)

- track-b §2.6:"star.motion.MotionSpecification / TranslationalMotionFrame /
  MotionFrame" 全部 NOT in 2402 R8 boundary values(ProbeWallBC 实证)。
- track-b §2.3:`enableModel(cont, "<FQN>")` 路径稳定 GREEN(LDC step4 `LaminarModel`、
  NACA v1 `KOmegaSST` 全 OK)。
- 本次:`star.motion.RotatingReferenceFrame` 存在 → 极可能走
  `continuum.enableModel(cont, "star.motion.RotatingReferenceFrame")`。
- **结论**:`RotatingReferenceFrame` 是 star.motion 下 continuum-level 模型,
  与 boundary-side `MotionSpecification` 平级不同概念;**D-7 前置 GREEN**。

## 风险(2 条)

1. **类存在 ≠ enable 成功**:还需 ThreeDimensionalModel + region Rotating +
   sub-attribute (RotationAxis/AngularVelocity)。1 次 90s spawn 才能 100%
   关 D-7 闭环,本任务不要求(留 D-7 后续)。
2. **track-b 候选列表需更新**:从 5 candidate 收窄到 1 个 `star.motion.*`。

## 边界

- 唯一新增:`macros/EnableModelProbe.java`(27 行)、本文件
- 未修改 track-b / DEC-007 / verdict / STATE.md / 4 track deliverable
- 未 spawn STAR-CCM+ / 未创建 .sim / 未 git push / 未改 gold_standard / tolerance / executor mode
