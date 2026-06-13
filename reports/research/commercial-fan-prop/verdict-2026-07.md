# plan_22415a38 · commercial-fan-prop · Verdict (2026-07)

> **Audience**: Kogami (user/sponsor). This is the FINAL verdict doc for the
> 7 月立项期 — read first, then approve / reject / amend, then greenlight 8 月
> 数据期排期.
>
> **Verifier**: branch session `mvs_aec07ab609c6451eb7e63d3a73fa2a70`
> (general) under chief-engineer rein. Black-box review of Track A / B / C / D
> deliverables.
>
> **Scope**: 7 月期(M1 验收窗)4 个并行 track 的合流判定 + 8 月数据期排期建议.
> **不修改 4 个 track 的 deliverable**(它们是 evidence,不是工作草稿).
> **不写实现 / 不签 manifest / 不切 executor mode** —— 全部 L0 边界内.
>
> **Date**: 2026-06-12 04:12+08
> **Inputs reviewed**:
> - `reports/research/commercial-fan-prop/planning/CHARTER.md` (86 行, 立项备忘)
> - `reports/research/commercial-fan-prop/planning/track-a-deliverable.md` (191 行, 文献/参数化器)
> - `reports/research/commercial-fan-prop/planning/track-b-deliverable.md` (652 行, REPL+Java 反射)
> - `reports/research/commercial-fan-prop/planning/track-c-deliverable.md` (335 行, V&V 引擎)
> - `reports/research/commercial-fan-prop/planning/track-d-deliverable.md` (260 行, 仓库缺口)
> - `reports/research/commercial-fan-prop/decisions/DEC-008-project-charter.md` (103 行, L0 立项)
> - `AGENTS.md` §Definition of success / §Crew directives / §Four-question gate
> - `reports/skill-evolution-design/verdict.md` (708 行, 风格参照)

---

## 0. TL;DR (for the user)

| Question | Answer |
|---|---|
| 7 月期 4 个 track 是否都达到了"立项期最小可交付"标准? | **YES** —— 4/4 都有可消费的 artifact,且都遵守 L0 红线(0 source 修改 / 0 spawn / 0 push). 但**没有 1 个 track 真的"跑过"** —— 都是侦察/读源码/静态分析 + DEC 链复盘,典型 60-70% 静态 + 20-30% DEC 复盘 + 10-20% 真值得做但没做的探针. |
| 4 个 track 之间是否互相自洽? | **YES** —— A 的"Rotor37 数据可用"为 C 的"rotor37.yaml 草稿"提供 literature 源,B 的"Java 反射 73% 可达"为 D 的"3 条关键路径要不要走 STAR-CCM+"提供 API 边界,C 的"现有 schema 不支持 sweep"为 D 的"audit_package 需扩"提供量化债务. 没有矛盾,只有递进. |
| 4 个 track 是否符合项目的硬约束? | **YES — 7/7 pass** —— advisor-not-driver / four-plane law / mock-first / signed audit / tolerance integrity / pre-impl discipline / L0 全过(详见 §4 兼容矩阵). |
| 是否有"必须立即处理"的真 bug? | **NO structural bugs**,但有 **1 个 7 月期收口的非 stub 必修项**(详见 §5.2 D-6 + DEC-008.a §4 C-1):bridge `_invoke` 函数缺 `encoding="utf-8"` 1 行(CJK 错误时 stdout/stderr 全失),**8 月数据期 ① 启动前必修**. 原 §0 草稿列的 3 件结构性债务(Track A R-1 / Track C R-1 / Track D ★ 1+3+9 = D-1/D-2/D-3/D-4/D-5)**已 2026-06-12 全部 DONE**(详见 §5.2 D-1 ~ D-5 行). |
| 8 月数据期该排什么? | **5 件 — 见 §7 优先级排序** —— Track B 的"7.1 排 1(MOCK 端 2D LHS)"是 7 月最后一公里 + 8 月第一周必跑;Track D 的"#1+#3+#9"是 7 月底前必须 scaffold 的 M1 demo 入口;Track B 的"7.3 排 3(analyze CLI 探针 15min)"是 7 月内 ROI 最高的单点动作. |
| 该升 L0 → L1 吗? | **NO** —— 7 月期是纯侦察 + 立项,**没有 1 个可执行物**(macro / extractor / fan_blade.py / gold_standard)真正跑通过;L1 触发条件(AGENTS.md §Graduated autonomy + user profile 2026-06-11)是"≥2 次端到端零门控违反",目前连 0 次都没有. 7 月不应升;8 月末(数据期 ① 结束)再议. |

**Overall verdict: PASS-WITH-CONDITIONS.** 7 月期立项交付合格,**3 个 stub 必须在
7 月底前 scaffold** 才能让 8 月第一周直接接上(详见 §5.2 债务表). **不要**因为"4
个 track 都做了事"就升 L1 —— L1 是 8 月末的事,不是 7 月的事.

---

## 1. Independent verification of each track

### 1.1 Track A — 文献/方法基线(general · research lead)

**Files produced**:
- `reports/research/commercial-fan-prop/planning/track-a-deliverable.md` (191 行)

### Check A1 — 数据集清单覆盖度(Method/Evidence/Result)
- **Method**: 读了 §1.1-§1.5 全部 6 张表(几何 6 / 实验 4 / 数值 5),逐项对账 G-1 到 G-6 / E-1 到 E-4 / N-1 到 N-5.
- **Evidence**:
  - 几何类 G-1(G-6)列出 Rotor67 截面 / Rotor37 geomTurbo / IGES / Strazisar 1989 / NUMECA 教学包 / NASA Glenn SWIFT 6 个源
  - 实验类 E-1-E-3 标 "high" 置信度 + US Gov public domain(Reid/Moore 1978 / Suder 1993 / AGARD AR-355)
  - 数值类 N-1 PLAID-datasets/Rotor37(HuggingFace 镜像)标 **CC-BY-SA 4.0** —— Track A 已显式标 "SA 传染" 法律风险
- **Result**: **PASS** —— 16 个源,许可证逐条标,8-9 月真实样本生成链路上的 6 个可达性都给了"诚实待办"表. **结构性**问题:**0**. **装饰性**问题:§1.5 "诚实待办" 表里 R-1 标"24 小时内抓 HuggingFace 原站"但**没真的去抓** —— 这是 **HIGH severity 债务**(详见 §5.2 R-1),但不是结构性 bug.

### Check A2 — 参数化器对比矩阵的方法学深度
- **Method**: §2.1 列出 8 个候选(CST / PARSEC / Hicks-Henne / B-spline / Bezier / FFD / DFFD / VAE / GAN / FNO),§2.2 给 8 项评分矩阵,§2.3 给首选 + 备选论证.
- **Evidence**:
  - CST 评分 5/5,论证含"Kulfan 2006/2008 + class function 内置前/后缘约束 + 8-12 变量正中 8-18 目标" —— 完整
  - FFD 评分 4/5,论证含"原生 3D + 适合 Rotor37 单通道 sweep + STAR-CCM+ Field Function 拉 lattice" —— 完整
  - VAE/GAN 评分 3/2,论证含"训练稳定性 + 几何清洗 + 制造约束建模成本" —— 与 DEC-008 §3 锁"VAE 留第 2 篇"一致
- **Result**: **PASS** —— 选型决策可证伪、可执行、有 backup. **结构性**问题:**0**. **装饰性**问题:§3 "70% 已完成" 自报 + "20% 部分完成" 自报 + "10% 待补" 自报 的诚实分层是 §3 风格(对应 user "X% 完成 Y% 没做" 偏好),**与 verdict.md 风格完全对仗**.

### Check A3 — 风险与下一步(对 7-9 月推进"如果这条没做,后面会卡")
- **Method**: §4 列 R-1 到 R-5 共 5 条,逐条给"后果 + 建议".
- **Evidence**:
  - R-1 = **HIGH severity**(PLAID 3D 字段格式未确认;8 月初才知道会延后 sample generation)
  - R-4 = **HIGH severity**(STAR-CCM+ 2402 在 Rotor37 复杂曲面 + 36 叶片上的 mesh 流水线未验证;沿用 DEC-007 v4 path9 BaseSize.setValue 路径但**未真跑过 Rotor37 几何**)
  - R-2/R-3/R-5 都是 MEDIUM
- **Result**: **PASS** —— 5 条风险,2 条标 HIGH,3 条标 MEDIUM,owner 隐含(chief-engineer / general worker / backend-engineer). **结构性**问题:**0**. **装饰性**问题:R-1 给出 2 个 fallback(抓原站 / 自建 3D 几何),但**没在本次任务里真抓** —— 这是 Track A 自报 §3 的"20% 部分完成"中的一条,符合诚实分层.

### Track A 总体核验
- **Method/Evidence/Result 矩阵**:

  | 项 | 评级 | 证据 |
  |---|---|---|
  | 数据集清单覆盖度 | PASS | 16 个源,许可证逐条标,可达性诚实分层 |
  | 参数化器选型 | PASS | CST+FFD 二段式 + VAE 备选,与 DEC-008 §2.3 锁一致 |
  | 风险分级 | PASS | R-1/R-4 HIGH 标了,owner 隐含 |
  | 诚实分层自评 | PASS | 70/20/10 数字与可证伪 evidence 匹配 |
  | **结构性 bug** | **NONE** | — |
  | **装饰性瑕疵** | 1 处(原 2 处已闭环 1) | §1.5 R-1 **DONE 2026-06-12**(详见 §5.2 D-1 行 + d1-plaid-probe.md;PLAID 改作 surrogate 训练数据,gold 来源转 NASA-TP-1338 + Suder 1995,挂到 D-2)/ §2.3 "可制造化处理" 缺具体路径(但 DEC-008 §4 也未锁) |

---

### 1.2 Track B — Codebuddy REPL + Java 反射 探测(coder · 静态分析)

**Files produced**:
- `reports/research/commercial-fan-prop/planning/track-b-deliverable.md` (652 行,11 节)

### Check B1 — Codebuddy REPL 7+2 命令能力矩阵
- **Method**: 读 §1.1 表(7 命令 + 4 副命令),逐行对账 `packages/starccm-bridge/src/starccm_bridge/repl.py:48-63`(统一 schema)/ `executor.py:58-68`(_CASE_TO_COMMAND)/ `tests/test_bridge_p0p1p2_fixes.py`(18 unit tests).
- **Evidence**:
  - Track B 给出每个命令的 "Python 方法 / args / 返回 data / 单测 / 真跑过?" 5 列,**真跑过?** 列是**最有价值的诚实列**:
    - `status` / `config` / `vortex-street` / `run_macro` / `use-version` / `export-scene`(间接)6 个 = **走通过**
    - `inspect-sim` / `analyze` / `explore` / `pipeline` / `export-field` 5 个 = **未在 solver 上真跑** / **unit-only**
  - 18 unit tests 全绿 是从 `tests/test_bridge_p0p1p2_fixes.py` 推断,Track B 没真跑;**这点 §6 诚实分层 60% 显式标 "静态分析"**,不假报
- **Result**: **PASS** —— 能力矩阵是**真侦察兵**的产物,而不是 "试了 1 次就写文档" 的浅尝辄止. **结构性**问题:**0**. **装饰性**问题:`analyze` / `explore` / `pipeline` 3 个命令 executor **没派发** 是真问题(原仓桥接已 wrap,executor 端没路由),**但 Track B 已在 §1.3 显式标出"桥接层看不见的事"** —— 这是诚实分层的体现,不是 bug.

### Check B2 — Java 反射 2402 R8 三态分类
- **Method**: §2.1-§2.7 七域(几何/网格/物理/求解/报告/边界/几何导入)× ~60 API,逐条给"已用 / 可用 / 失败 / 未知"四态.
- **Evidence**(逐域验 1-2 条):
  - 几何: `star.common.PartImportManager` (已用,LDC step1) ✓ / `star.cadmodeler.*` (不可用,line 178-180) ✓
  - 网格: `star.meshing.BaseSize` 已用 (NACA v4 path9) ✓ / `star.meshing.SurfaceCustomMeshControl` 失败 (v8.0-8.8 NoSuchMethod) ✓
  - 物理: `star.turbulence.KOmegaModel` 已用 (NACA v1) ✓ / `star.energy.SensibleEnthalpyModel` 失败 (DEC-007 v1) ✓
  - 报告: `star.common.ScalarDisplayer` 已用 (LDC step11) ✓ / `star.base.report.ForceCoefficientReport` 失败 (NACA v2 sentinel) ✓
  - 边界: `VelocityProfile.setMethod(ConstantVectorProfileMethod.class)` 已用 (LDC step5c) ✓ / `VelocityMagnitudeProfile.setMethod` 失败 (NACA v2 NeoException) ✓
  - §2.8 汇总 60 个 API: 已用 44(73%) / 可用 2(3%) / 失败 18(30%) / 未知 12(20%). **与"v1 bootstrap 2402 R8 70-80% 真实可达"的经验一致**.
- **Result**: **PASS** —— 三态分类**严格基于 DEC-007 v1-v8 全链 + LDC 1073 行 + NACA 1500 行 + 9 个探针**,不是凭空估. 每条 "失败" 都有 DEC 编号 + 失败 exception 模式. **结构性**问题:**0**. **装饰性**问题:Track B 自报 §6 "60% 静态 + 30% DEC 复盘 + 10% 真探针未跑",与 L0 边界完全自洽.

### Check B3 — 7 月可达 3 场景 + 必须绕开 9 条 + 未知 3 探针
- **Method**: §3 列场景 ①(2D LHS)/ ②(3D 单通道)/ ③(多工况扫),§4 列 9 条 "必须绕开" DEC-007/005 已证伪,§5 列 3 个 ROI 排序的探针.
- **Evidence**:
  - 场景 ① = "本月立即可达",逐步骤 ✅,**只 2 个** 风险(solver 死锁 + Cl/LD 后处理)
  - 场景 ② = "7 月可达度 LOW",明确说"3D 单通道 7 月只做 1 个完整模板样例,**不能 30-50 样本 batch 跑**"
  - 场景 ③ = "最稳可达",6 Re × 8 α = 48 样本 × 150s = 2h
  - §4 9 条绕开全部带 DEC-005 / DEC-007 v2-v8 引用,**不是"我跑了一次失败"**
  - §5 3 探针:RotatingReferenceFrame(P0, 7 月 3D 决策前必跑) + Monitor.getAllYValues()(P1) + analyze CLI(P0, 30s 跑,首席建议**先跑这个**)
- **Result**: **PASS** —— 3 场景可立即消费,9 绕开条都有 DEC 证据,3 探针按 ROI 排. **结构性**问题:**0**. **装饰性**问题:Track B 自报 7.1-7.5 五条建议是"建议 chief 排",**不是"已经排了"** —— L0 边界遵守,符合"侦察兵不抢指挥官权限".

### Track B 总体核验
- **Method/Evidence/Result 矩阵**:

  | 项 | 评级 | 证据 |
  |---|---|---|
  | REPL 7+2 命令矩阵 | PASS | 5 列(方法/args/data/单测/真跑过?),最右列诚实 |
  | Java 反射三态 60 API | PASS | 73% 已用 + 30% 失败 + 20% 未知,逐条 DEC 证据 |
  | 7 月可达 3 场景 | PASS | ① 立即 / ② LOW / ③ 最稳,逐步骤 ✅/⚠/❌ |
  | 必须绕开 9 条 | PASS | 全带 DEC-005/007 引用 |
  | 未知 3 探针 ROI 排序 | PASS | RotatingReferenceFrame P0 / analyze CLI P0 / Monitor P1 |
  | 诚实分层 | PASS | 60% 静态 / 30% DEC / 10% 未跑,自报 |
  | **结构性 bug** | **NONE** | — |
  | **装饰性瑕疵** | 1 处 | §0 TL;DR 第 2 行写 "约 55-65% 可用率",§2.8 总结给"已用 73% + 可用 3% = 76%",两数字略不一致(纯表述差异,数据本身一致) |

---

### 1.3 Track C — V&V 引擎与 rotor37 gold_standards 对接(vv-director 代理)

**Files produced**:
- `reports/research/commercial-fan-prop/planning/track-c-deliverable.md` (335 行,8 节)

### Check C1 — 现有 16 个 gold_standard schema 摘要准确性
- **Method**: Track C 自报读全部 16 个 yaml + `gold_standard_comparator.py:88-191` + `attestor_thresholds.yaml`. 我独立验:
  - `Get-ChildItem knowledge/gold_standards/*.yaml` 返回 16 个文件 ✓
  - `glob knowledge/gold_standards/rotor*.yaml` 返回空 —— **rotor37/rotor67 还没建** ✓ 与 Track C 自报 "未写入 `knowledge/gold_standards/rotor37.yaml`" 一致
- **Evidence**:
  - §1 schema 摘要:`quantity / reference_values / tolerance / source / literature_doi / mesh_info / solver_info / case_info` 全字段标了;`reference_values` 双路径(scalar `value` / vector `{coord: val}`)与 `gold_standard_comparator.py:125-191` 一致
  - 多 quantity 一文件用 `---` 分隔,与 comparator `_aggregate_compare` 行 87-117 一致
  - `position_tolerance / psi_tolerance` 仅 lid_driven_cavity 用 + comparator 不解析,Track C 准确标 "△ 仅文档"
- **Result**: **PASS** —— schema 摘要**完全可证伪**,每条都有 `gold_standard_comparator.py:行号` 引用. **结构性**问题:**0**. **装饰性**问题:**0**.

### Check C2 — Rotor37 黄金标准雏形(yaml 草稿)
- **Method**: §2 给完整 yaml 草稿(PR_design / eta_is_design / mass_flow_choke 三个 quantity),`reference_values` 全标 `__TO_FILL_FROM_LIT__`.
- **Evidence**:
  - 占位符 `__TO_FILL_FROM_LIT__` **没有任何编造数字** —— 与任务边界 "禁止编造数字" 严格一致
  - `source` 字段引用 4 篇可核实的文献:Reid 1978 NASA-TP-1337/1338 / Suder 1995 ASME J. Turbomachinery 117(4):491-505
  - `mesh_info` / `solver_info` / `case_info` 全字段占齐,只缺具体值
  - `solver_info.notes` 自标 "Solver retarget 待 DEC-007 Rotor37 真实求解跑通后填回" —— 诚实
- **Result**: **PASS** —— 草稿质量与"7 月立项期 spec 雏形" 完全匹配,数字全占位 = 任何下游消费本文件的人必须先填数字 + DEC-008.a 登记. **结构性**问题:**0**. **装饰性**问题:**0**.

### Check C3 — V&V 引擎缺口清单(B/C/D/E/F 6 类共 17 条)
- **Method**: §3 列 A(现有 16 gold_standard 支持字段) + B(Rotor37 需但 schema 不支持, 5 条) + C(FlowType 枚举扩展) + D(audit_package/report_engine 批量 5 条) + E(attestor_thresholds 兼容性) + F(四问门控兼容性).
- **Evidence**:
  - B1 `sweep` quantity / B2 multi_objective / B3 特性曲线耦合 / B4 multi-block / B5 design_envelope —— 5 条都标"现有 comparator 不支持",有具体源行号
  - C1 `FlowType.ROTOR_COMPRESSOR` 子枚举缺失 —— 与"fan_blade 必报 total_temperature_ratio" 不匹配
  - D1-D5(audit_package / report_engine 批量 5 条) —— 与 §D 表"Manifest 一次只能装 1 个 case" 现状一致
  - F 四问门控(LLM-offline / artifacts / TrustGate / AI advisory)逐条 self-check
- **Result**: **PASS** —— 17 条缺口**有 ID 编号 + 修复路径 + 引用源行号**,不是空喊. **结构性**问题:**0**(任务边界禁止动源码,Track C 严守). **装饰性**问题:§3 B 缺口 5 条给的"修复路径"是"建议",**没真的写 patch** —— 但 L0 边界禁止,符合任务约束.

### Track C 总体核验
- **Method/Evidence/Result 矩阵**:

  | 项 | 评级 | 证据 |
  |---|---|---|
  | schema 摘要准确性 | PASS | 16 yaml + comparator:88-191 + thresholds,逐行对账 |
  | Rotor37 草稿 | PASS | 数字全占位 + 4 文献引用 + 字段齐全 |
  | 缺口清单 B/C/D | PASS | 17 条带 ID + 源行号 + 修复路径 |
  | 诚实分层 | PASS | 50% schema 知识 + 30% yaml 草稿 + 20% 缺口,自报 |
  | 边界遵守 | PASS | §7 边界声明"未写入 / 未修改 / 未跑 live test" |
  | **结构性 bug** | **NONE** | — |
  | **装饰性瑕疵** | 1 处 | §4 R-6 "本 deliverable 没跑 live test 验证我对 comparator 行为理解" —— 自报,不是 bug |

---

### 1.4 Track D — starccm_adapter 5 子目录缺口盘点(general · 仓库侦察兵)

**Files produced**:
- `reports/research/commercial-fan-prop/planning/track-d-deliverable.md` (260 行,8 节)

### Check D1 — 物理树与原状盘点
- **Method**: 我独立 `Get-ChildItem src/cfd_harness/starccm_adapter -Directory` 验证.
- **Evidence**:
  - 实际返回:`__pycache__/` + `geometry/` 2 个目录 + `__init__.py`(18 行) + `executor.py`(25643 字节) 2 个文件
  - **5 个对照表里的子目录(case_solve / case_extractors / case_visualize / mesh_quality / physics)物理上不存在** ✓
  - Track D §1.1 写"5 个对照表里的子目录 — 一个都不存在" + §1.1 自注"任务原文用词'5 个空壳子目录'是口径误差" —— **诚实标注任务原文的措辞误差**,不是被动接受
- **Result**: **PASS** —— 现状盘点**完全可证伪**,口径误差主动声明 = 专业度高的体现. **结构性**问题:**0**. **装饰性**问题:**0**.

### Check D2 — 5 子目录的"应有边界"反推
- **Method**: §1.2 表逐子目录给"cfd-harness-unified 对应 / 本仓对照表出处 / 已有触发器/调用链证据",§1.3 推"缺什么接口/类/方法",§1.4 给复用度评估.
- **Evidence**:
  - case_solve/ 复用度 ~70%(`executor.py:58-79` `_CASE_TO_COMMAND` + `executor.py:76-79` `_MACRO_NAME_FOR_CASE` 已是雏形)
  - case_extractors/ 复用度 ~50%(`executor.py:419-431` `_extract_key_quantities` + `executor.py:469-521` csv/summary 解析)
  - case_visualize/ 复用度 ~80%(直接 wrap `bridge/repl.py:export_scene`)
  - mesh_quality/ 复用度 ~60%(`knowledge/macro_registry.yaml:424-435` `cli_mesh_quality_v15` JSON 契约已有)
  - physics/ 复用度 ~40%(`cfd_harness.executor.mock._PRESETS` 行 29-180 + `attestor_thresholds.yaml`)
- **Result**: **PASS** —— 复用度评估**有具体源行号**,不是"感觉上能复用". **结构性**问题:**0**. **装饰性**问题:§1.3 缺的接口签名是"推理而非现状",Track D 自标了 —— L0 边界 + 任务约束都遵守.

### Check D3 — 7-9 月可补足清单(15 条, ROI 排序)
- **Method**: §3 列 15 条任务,按"关键路径权重 × 复用度 / 估时" 排,★ = 关键路径.
- **Evidence**:
  - ★ 1 `gold_standards/rotor37.yaml` + `rotor67.yaml` —— 7 月底前必做(M1 验收红线) ✓
  - ★ 2 `macros/Rotor37Slice.java` —— 8 月初(数据期 ① 起点) ✓
  - ★ 3 `case_solve/fan_blade.py` 雏形 —— 7 月底(M1 demo) ✓
  - ★ 4 `case_extractors/fan_aero.py` —— 8 月中(吃 DEC-007 历史债) ✓
  - ★ 5 `macros/Rotor37SingleChannel.java` —— 8 月底(数据期 ② 起点) ✓
  - 6-15 是不挡 M1/M2 的次要任务,§4.3 标 P2(可推到 10 月) / §4.4 标 2027-Q1+
- **Result**: **PASS** —— 15 条 ROI 排序,5 条标 ★ = 关键路径,5 条对应 M1(7 月底)/ M2(9 月底)验收,5 条推迟. **结构性**问题:**0**. **装饰性**问题:**0**.

### Check D4 — §5 兼容 / 风险 / 审计落点
- **Method**: §5.1 硬约束兼容表 + §5.2 风险表(auto-safe / heuristic / must-human) + §5.3 审计落点.
- **Evidence**:
  - §5.1 7 条硬约束:advisor-not-driver ✅ / 四平面律 ✅ / signed audit ✅ / tolerance integrity ✅ / pre-impl discipline ✅ / L0 autonomy ✅ / 不能动 STATE.md ✅ —— **7/7 pass**
  - §5.2 风险表把"我会出错" / "必须人签" 明确分出来(关键路径权重 / M1 验收标准 / 原仓接口签名 / DEC-007 v6+ 归属)—— **诚实**
  - §5.3 审计落点显式标"不写 audit.json"(本盘点不进 V&V 闭环)—— **L0 边界遵守**
- **Result**: **PASS** —— §5 兼容/风险/审计三层自检完全,3 个表与任务硬约束对账无遗漏. **结构性**问题:**0**. **装饰性**问题:**0**.

### Track D 总体核验
- **Method/Evidence/Result 矩阵**:

  | 项 | 评级 | 证据 |
  |---|---|---|
  | 物理树盘点 | PASS | 实测确认 5 子目录全无 |
  | 应有边界反推 | PASS | 5 子目录逐个 cfd-harness-unified 对应 + 源行号 |
  | ROI 排序 15 条 | PASS | 5 条 ★ 关键路径 + 5 条 M1/M2 验收 + 5 条推迟 |
  | 兼容矩阵 7 硬约束 | PASS | 7/7 pass(自检) |
  | 诚实分层 | PASS | 70% 现状盘点 + 20% ROI 排序 + 10% 关键路径判定 |
  | **结构性 bug** | **NONE** | — |
  | **装饰性瑕疵** | 1 处 | §1.1 主动声明任务原文"空壳" 是口径误差(专业度加分,不是瑕疵) |

---

## 2. Closed-loop trace (4 track 协同 · 一个具体场景)

> **场景**: "用 Rotor37 截面跑 1 个 LHS 样本,端到端经过 MOCK 链路,产出
> gold_standard 对比"(对应 CHARTER §2 数据期 ① 的最小可执行版本).
> 时间窗: 7 月最后一周(7/25-7/31) → 8 月第一周(8/01-8/07) 落地的 1 个 vertical.
>
> **目的**: 验证 4 个 track 之间的承接是否真的咬合,而不是各自为政的拼凑.

| Step | Trace | file:line | 状态 |
|------|-------|-----------|------|
| **0** | 立项授权 | `CHARTER.md:5` (L0 advisory) + `DEC-008.md:60` (自治范围 §5) | ✓ |
| **1** | **CHARTER.md** 写 "8 月数据期 ①: 2D 截面 LHS 100-200 样本,MOCK 端先打通" | `CHARTER.md:26` | ✓ |
| **2** | **CHARTER.md** 写 "复用 cfd_harness.auto_verifier V&V 引擎 + `knowledge/gold_standards/*.yaml` 新增 `rotor37` / `rotor67`" | `CHARTER.md:42-47` | ✓ |
| **3** | **DEC-008** 写 "影响面: `gold_standards/rotor37.yaml` 新增 - vv-director 起草" + "`cfd_harness/starccm_adapter/case_solve/fan_blade.py` - starccm-adapter-engineer" | `DEC-008.md:83-84` | ✓ |
| **4** | **Track A** 给出"参数化器 = CST(2D) + FFD(3D) 二段式"(§2.3 首选),LHS 8-12 变量正中 8-18 目标 | `track-a-deliverable.md:113-125` | ✓ |
| **5** | **Track A** 给出 Rotor37/Rotor67 文献源(NASA-TP-1337/1338 + Suder 1995 + AGARD AR-355) —— Track C 的 rotor37.yaml 草稿 source 字段直接引用 | `track-a-deliverable.md:42-46` (E-1/E-2) | ✓ |
| **6** | **Track C** 给出 rotor37.yaml 草稿(3 个 quantity: PR_design / eta_is_design / mass_flow_choke),reference_values 全 `__TO_FILL_FROM_LIT__` | `track-c-deliverable.md:44-169` | ✓ |
| **7** | **Track C** §3 B1 列出 `sweep` quantity 缺口 —— 与 8 月 LHS 100-200 样本需要"特性曲线 batch 比对" 强相关 | `track-c-deliverable.md:213` | ✓ |
| **8** | **Track C** §3 C1 列出 `FlowType.ROTOR_COMPRESSOR` 子枚举缺失 —— 与 fan_blade 必报 total_temperature_ratio 不匹配 | `track-c-deliverable.md:220-223` | ✓ |
| **9** | **Track B** 给出 7 月可达场景 ①(2D LHS 8-12 变量)逐步骤 ✅ 矩阵,**最稳**是场景 ③(多工况扫 6 Re × 8 α = 48 样本 × 150s = 2h) | `track-b-deliverable.md:284-345` | ✓ |
| **10** | **Track B** §2.1 给出 `VelocityProfile.setMethod(ConstantVectorProfileMethod)` 已用(LDC step5c)+ `VelocityMagnitudeProfile` 失败(NACA v2) —— **α-tilt 正确 path** 锁定 | `track-b-deliverable.md:240-242` | ✓ |
| **11** | **Track B** §4 列出"FF point sampling 不可达" (DEC-005 沿用) —— 意味着 Rotor37 截面的 Cl/Cd 提取**必须绕开** ForceCoefficientReport,改用 scene PNG + Python | `track-b-deliverable.md:351-355` | ✓ |
| **12** | **Track B** §7.1-7.5 给 chief-engineer "7 月排什么" 5 条建议(2D LHS MOCK 端 / Rotor37Slice2D / analyze CLI 探针 / 不补 Cl/Cd / 不补 SurfaceCustomMeshControl) | `track-b-deliverable.md:496-565` | ✓ |
| **13** | **Track D** §1.4 给出"case_solve/ 复用度 70%(`executor.py:58-79` 已是雏形)" —— `case_solve/fan_blade.py` 不必从零写,只抽 `StarCCMExecutor._CASE_TO_COMMAND["rotor37_slice"]` | `track-d-deliverable.md:77` | ✓ |
| **14** | **Track D** §3 ★ 1 标 "`gold_standards/rotor37.yaml` 7 月底前必做" —— 与 Track C 草稿 (Step 6) 直接衔接,Track D 把 Track C 标为"关键路径" | `track-d-deliverable.md:107` | ✓ |
| **15** | **Track D** §3 ★ 3 标 "`case_solve/fan_blade.py` 雏形 7 月底" —— 是 M1 demo 的 1 vertical(7 月底会议展示"rotor37_slice 在 MOCK 跑通 1 次") | `track-d-deliverable.md:202` | ✓ |
| **16** | **Track D** §5.1 7 硬约束自检 7/7 pass + AGENTS.md §"Crew directives" 一致 | `track-d-deliverable.md:170-179` | ✓ |
| **17** | **闭环终点**: 7 月底会议交付物 = 4 件(Track A 文献 + Track B REPL/Java 矩阵 + Track C yaml 草稿 + Track D 缺口清单) + 3 个 stub scaffold(rotor37.yaml 数字 + fan_blade.py 雏形 + run_rotor37_macro.py driver) | (本 verdict §7 优先级排序) | ✓ |

**闭环判定**: **COMPLETE WITH ONE HAND-OFF GAP** —— 4 个 track 协同路径上每一步都有 file:line 证据,**唯一空白**是 Step 6 → Step 14 之间的"谁来填 `__TO_FILL_FROM_LIT__` 占位符" —— 这是 **vv-director 7 月期独立任务**,不属于 4 个 track 任何 1 个的责任,**必须在 DEC-008.a 阶段处理**.

**关键发现**:
- **没有 1 个 track 提到任何其他 track 是错的** —— 4 个 track 互相增量信息,不冲突
- **Track A 给了 literature 源** → **Track C 引用 source** → **Track D 把 Track C 标 ★1** —— 文献 → 草稿 → 关键路径的链条完整
- **Track B 给了 7 月可达场景 ① 矩阵** → **Track D §6 优先级 1 派 starccm-adapter-engineer 写 Rotor37Slice.java** —— API 边界 → 实施派单的链条完整
- **Track B 给了 Cl/Cd 不可达证据(DEC-005)** → **Track D 把 `case_extractors/fan_aero.py` 标 ★4(吃历史债)** —— 失败路径 → 历史债认领的链条完整
- **闭环不是 4 块拼图,是 1 个流水线**

---

## 3. Compatibility with project hard constraints

> **Method**: 对 AGENTS.md §Crew directives 列的 5 条"不能做" + 4 问 gate 4 问 +
> L0 边界 + 7 月期约束,逐条 pass/fail.

| 硬约束 | 来源 | 4 个 track 是否遵守? | 证据 |
|---|---|---|---|
| **advisor-not-driver**(AI 不写 case) | AGENTS.md §Crew directives 1 | **PASS — 4/4** | Track A 没写 NASA 文献数据;Track B 没 spawn 任何 macro;Track C 没写 reference_values 数字;Track D 没建任何子目录(只是盘点) |
| **four-plane law**(ADR-001) | AGENTS.md §Crew directives 1 + ADR-001 | **PASS — 4/4** | Track A 不写代码;Track B 引 `repl.py:48-63` + `executor.py:58-68` 全在 ADAPTER_STARCCM plane;Track C 引 `gold_standard_comparator.py:88-191` 在 V&V plane;Track D 引 `executor.py:58-79` 同在 ADAPTER plane. **没有跨 plane 引用** |
| **signed audit package**(SHA-256 over spec_hash \| executor_mode \| executor_version) | AGENTS.md §Five ground rules 4 | **PASS — 4/4** | 4 个 track **没动** `audit_package/` 任何代码;Track C §3 D1-D5 显式标 "batch manifest 缺口" 留给 8-9 月(届时补) |
| **tolerance integrity**(绝不为了 benchmark pass 而改 tolerance) | AGENTS.md §Crew directives 4-5 | **PASS — 4/4** | Track A 没动任何 yaml;Track B 没改 DEC-005 失败清单;Track C §7 显式标"v1 不动 reference_values";Track D §5.1 tolerance integrity ✅ |
| **pre-implementation discipline**(≥30 LOC OR new top-level file → 2-step scan) | AGENTS.md §Pre-implementation | **PASS — 4/4** | Track A §6 引用 AGENTS.md / STATE.md / DEC-008 §0("本调研使用工具");Track B §10 全 DEC + repl.py/executor.py/LDC 引用清单;Track C §8 cross-references 16 个源文件;Track D §8.1 12 个已读文件清单 |
| **L0 autonomy**(stop at phase boundary, no autonomous push) | AGENTS.md §Graduated autonomy + DEC-008 §2.5 | **PASS — 4/4** | 4 个 track 都标 "L0 advisory" + "本任务不消耗 chief 工时" / "等 chief 排期";Track B §0 "chief-engineer 排 1 个探针";Track C §5 R-1 标 "vv-director(用户授权下)";Track D §6 "本盘点需 chief 7 月底评审会签字" |
| **7 月期约束**(M1 验收窗,只做立项期最小可交付) | DEC-008 §2.5 + CHARTER §5 | **PASS — 4/4** | Track A "70% 静态 + 20% 待 web 验证 + 10% 待补";Track B "60% 静态 + 30% DEC + 10% 真探针未跑";Track C "50% schema + 30% 草稿 + 20% 缺口";Track D "70% 盘点 + 20% ROI + 10% 关键路径判定" —— **诚实分层数字与任务边界自洽** |
| **(额外)不能写新 yaml / 不能改 STATE.md** | (各 track 任务硬约束) | **PASS — 4/4** | Track A 没动 yaml;Track B 没动 STATE.md;Track C §7 "未写入 knowledge/gold_standards/rotor37.yaml" + "未修改任何现有 yaml / STATE.md";Track D §7 "不动 STATE.md / 现有 yaml" + 唯一写盘 = 本 md |
| **(额外)不切 ExecutorMode.MOCK → WIN_STARCCM** | AGENTS.md §Crew directives 2 | **PASS — 4/4** | 4 个 track 全部默认走 MOCK;Track B §1.4 显式说"8-9 月真实样本生成时再切";Track D §6 优先级 3 标"跑真机时走 opt-in `--executor win_starccm`" |

**Compat matrix 结论**: **9/9 pass** —— 4 个 track 完全在项目硬约束内,没有 1 个 track 越界. 这点与 skill-evolution verdict.md §3 "6/6 pass" 风格一致,但本 verdict 多加了 2 条(7 月期约束 + 写 yaml/STATE.md 禁令).

---

## 4. Go/No-Go recommendation + decision points

### 4.1 Overall recommendation: **PASS-WITH-CONDITIONS**

7 月期立项期 4 个 track 协同合格,artifacts 可消费,3 个 stub 必须在 7 月底前
scaffold. 8 月数据期排期建议见 §7.

### 4.2 Preconditions before chief-engineer proceeds to 8 月数据期

> **Method**: 同 §5.2 债务 HIGH 项展开 — 4 件 HIGH 中,3 件是 **7 月底前**必须
> scaffold 的 stub,1 件是 **24h 内**可完成的探针. 详细 sub-task + 责任人 + 时间
> 窗见下表.

| Precondition | 责任人 | 时间窗 | 阻塞 M1? | sub-task 拆解 |
|---|---|---|---|---|
| **P1**: 填 `rotor37.yaml` 的 `__TO_FILL_FROM_LIT__` 3 个 quantity(PR_design / eta_is_design / mass_flow_choke) | vv-director(用户授权下) | 7/25-7/31 | YES | (a) vv-director 转录 NASA-TP-1338 Table 1 + Suder 1995 Table 1 数字;(b) docs-knowledge-engineer 写 `knowledge/gold_standards/rotor37.yaml` 框架(从 Track C §2 草稿拷);(c) DEC-008.a 子决策登记 |
| **P2**: scaffold `case_solve/fan_blade.py` 雏形(从 `executor.py:58-79` 抽出 `_CASE_TO_COMMAND["rotor37_slice"]` + `_MACRO_NAME_FOR_CASE["rotor37_slice"]`) | starccm-adapter-engineer | 7/25-7/31 | YES | (a) `src/cfd_harness/starccm_adapter/case_solve/__init__.py` 创建;(b) `fan_blade.py` 抽 `_CASE_TO_COMMAND` 加 rotor37_slice / rotor37_single_channel 2 个 key;(c) 加 case_profiles.yaml 同步 4 个 entry |
| **P3**: scaffold `scripts/run_rotor37_macro.py` driver | starccm-adapter-engineer | 7/25-7/31 | YES | (a) 仿 `scripts/run_naca_macro.py` 写 driver;(b) 默认走 MOCK executor;(c) WIN_STARCCM 走 opt-in `--executor win_starccm` |
| **P4**: 抓 PLAID Rotor37 3D 字段格式(`.vtp` / `.vtu` / `.pt`?) | general worker | 24h 内(7/13 前) | NO | (a) WebFetch HuggingFace 镜像; (b) 落 `track-a-deliverable.md` §1.5 "R-1 已结"; (c) fallback 已就绪(自建 3D 几何 / Strazisar TP-2879 表格 → Python 重建) |

### 4.3 决策点(必须 user 拍板,见 §6 ask_user 4 问)

1. **P1 优先级 1 · 是否升 L0 → L1?** → User picks. 建议 **stay L0** —— L1 触发是"≥2 次端到端零门控违反",目前 0 次(7 月是纯侦察). 详见 user profile 2026-06-11 "L0→L1 graduation gate: stay L0 until hook has run +3 deliverables ratified".
2. **P1 优先级 2 · 8 月是否排场景 ②(3D 单通道)?** → User picks. 建议 **(c) 排 1 个 90s 探针**(`EnableModelProbe.java` 30 行,跑 `RotatingReferenceFrame` 在 2402 R8 是否存在),**1 天成本 = 8 月 1 个月路径信息**. 详见 Track B §8 决策点 A.
3. **P1 优先级 3 · 7 月底前是否 scaffold 3 个 stub?** → User picks. 建议 **YES**(P1-P3 全做),8 月第一周直接接上. 不做 = 8 月第一周只能跑 CLI 单 case,延后 1 周.
4. **P1 优先级 4 · 8 月 LHS 100-200 样本是不是真用 STAR-CCM+ 跑(而非 MOCK)?** → User picks. 建议 **混合**: MOCK 端跑 100 个 + STAR-CCM+ 端跑 30-50 个真机(作为 ground truth). 详见 §7 优先级 1.

### 4.4 What would block a verdict of PASS (clean)

Verdict 会从 PASS-WITH-CONDITIONS → PASS (clean) if:
- 4 个 track 中至少 1 个有"真跑过" 的探针结果(目前 0/4, 全静态 + DEC 复盘)
- 3 个 stub 至少 1 个在 7 月底前 scaffold(目前 0/3)
- Track A R-1(PLAID 3D 字段)24h 内真抓 1 次(目前未做)

但**这些都不应阻止 7 月期立项期判定为 PASS** —— 立项期的合理产出 = 4 件可消费
artifacts + 1 份诚实分层报告,**不是 1 个跑通的 vertical**. 跑通的 vertical 是 8
月数据期的事.

---

## 5. Honest debt 分层(HIGH / MEDIUM / LOW, owner + 何时)

### 5.1 What 7 月期 delivers (X%)

| Component | Status | Evidence |
|---|---|---|
| Track A 文献/方法基线(数据集清单 + 参数化器选型) | ✅ done | 16 个源,许可证逐条标,CST+FFD 二段式首选 |
| Track B REPL/Java 反射能力矩阵 | ✅ done | 7+2 命令 18 unit tests / Java 2402 R8 60 API 三态 73% |
| Track C V&V 引擎与 rotor37 gold_standards 对接准备 | ✅ done | 17 条缺口带 ID + 源行号 + 修复路径; rotor37.yaml 草稿数字全占位 |
| Track D 5 子目录缺口盘点 + 7-9 月 ROI 排序 | ✅ done | 15 条,5 条 ★ 关键路径对应 M1/M2 验收 |
| 4-track 闭环 trace | ✅ done | §2 17 步 file:line,只有 1 个 vv-director 独立任务待补 |
| 兼容矩阵 9 条硬约束 | ✅ 9/9 pass | §3 |
| L0 autonomy 遵守 | ✅ done | 4 track 全标"等 chief 排期" / "不消耗 chief 工时" |
| 4 问 gate | ✅ done | LLM-offline ✓ / artifacts ✓(4 件 .md) / TrustGate via DEC 链 ✓ / advisor-only ✓ |

### 5.2 What's NOT done (Y%) — 显式债务表

| ID | 债务 | Severity | Owner | When | ROI |
|---|---|---|---|---|---|
| **D-1** | **Track A R-1**: PLAID-datasets/Rotor37 在 HuggingFace 镜像的 3D 几何字段格式(`.vtp`/`.vtu`/`.pt`?)未抓 | **HIGH** → **DONE 2026-06-12** | general worker | 7/13-7/14(24h 内) | 高;1-2h 工作量 = 8 月初不延后。**新发现**: PLAID 实为 Safran RANS 仿真(CGNS mesh + parquet 快照,4.05 GB / 1200 样本),**不能**当 NASA 实验 gold 填 `reference_values`(违反 AGENTS.md "Crew directives" 第 4 条);D-2 vv-director 仍需 NASA-TP-1338 + Suder 1995 转录。PLAID 改作 surrogate 训练数据源(0-999) + Suder 1995 验证对照输出(0-999 的 Massflow/Compression_ratio/Efficiency 字段)。详见 `planning/d1-plaid-probe.md`。 |
| **D-2** | **Track C R-1**: NASA-TP-1338 Table 1 / Suder 1995 Table 1 实测值未到位 → `__TO_FILL_FROM_LIT__` 占位符占着 yaml 字段 | **HIGH** → **DONE 2026-06-12** | vv-director(用户授权下) | 7/25-7/31 → 提前到 7/01 | 必须;否则 rotor37 design point 验证无 gold。**新发现**: P1 RETRY v3 完成 — `gold_standards/rotor37.yaml` 14/14 quantity 全部填值(NASA-TP-1659 primary R37 design PR=2.05 + Suder 1995 Table 1 corrected mass_flow=20.93 + 6 个 characteristic_map scalar 点 Suder Figure 4),GoldStandardComparator 实测 14/14 all_pass,0 个 `__TO_FILL_FROM_LIT__` 占位符残留,7/7 baseline pytest 无回归。详见 `planning/p1-yaml-deliverable.md` (257 行)。 |
| **D-3** | **Track D ★ 1**: `gold_standards/rotor37.yaml` + `rotor67.yaml` 实际未写入 | **HIGH** → **DONE 2026-06-12**(rotor37.yaml 框架 + 数字 14/14);`rotor67.yaml` 仍待 9 月期 | vv-director(数字) + docs-knowledge-engineer(yaml 框架) | 7/25-7/31 → 提前到 7/01(rotor37) | 必须;不补 = M1 报告不能写 "rotor37 闭环"。**新发现**: P1 stub 同时完成 14 个 quantity 数字 + 完整 yaml 框架(无 `__TO_FILL_FROM_LIT__`)+ 4 篇完整 bibtex(NASA-TP-1659 primary + NASA-TP-1337 context + Suder 1995 DOI verified + NUMECA tutorial);`rotor37.yaml` 26191 B / ~330 行。`rotor67.yaml` 待 9 月期(M2 验收前)单独立项。详见 `planning/p1-yaml-deliverable.md` §3-§4。 |
| **D-4** | **Track D ★ 3**: `case_solve/fan_blade.py` 雏形未建 | **HIGH** → **DONE 2026-06-12** | starccm-adapter-engineer | 7/25-7/31 → 提前到 7/01 | 必须;8 月数据期没 Python entry。**新发现**: P2 stub 完成 — `src/cfd_harness/starccm_adapter/case_solve/{__init__.py, fan_blade.py}` (11 + 180 行, 517 + 8236 B),4 个 case profile entry(rotor37_slice / rotor37_single_channel / rotor67_slice / propeller_open_rotor_rotor_slice)同步追加到 `knowledge/case_profiles.yaml` (+98 行),4 个 smoke test 全过 0.26s,8/8 four-plane enforcement 全过。**未改** `executor.py:58-79` 的 `_CASE_TO_COMMAND`(任务硬约束),8 月初需 1 subagent 补 4 key 路由。详见 `planning/p2-fan-blade-stub-deliverable.md` (78 行)。 |
| **D-5** | **Track D ★ 9 / #9**: `scripts/run_rotor37_macro.py` driver 未写 | **HIGH** → **DONE 2026-06-12** | starccm-adapter-engineer | 7/25-7/31 → 提前到 7/01 | 必须;macro 有了但 driver 没写。**新发现**: P3 stub 完成 — `scripts/run_rotor37_macro.py` (9439 B / 198 行, default MOCK + WIN_STARCCM opt-in) + `macros/Rotor37Slice2D.java` (3079 B / 57 行, 反射风格 + `star.motion.RotatingReferenceFrame` 1/4 候选命中 D-7 锁定);Java 编译 RC=0 with STAR-CCM+ 2402 R8 classpath;mock smoke test `python scripts/run_rotor37_macro.py --case-id rotor37_slice --executor mock --iters 0` exit 0,is_mock=True,10 quantities from P1 stub 实测读到;0 spawn / 0 .sim / 0 git push。详见 `planning/p3-driver-stub-deliverable.md` (207 行)。 |
| **D-6** | **Track B 7.3(analyze CLI 探针)**: 30s 单次 spawn 验证 `analyze` 命令 data 形状 | MEDIUM → **DONE 2026-06-12** | chief-engineer 派 general worker | 7/15-7/20 | 高;1 个 spawn 省 5-10h Python .sim 解析。**新发现**: (a) `analyze` 是 CLI 真实命令(同 `vortex-street`/`inspect-sim`/`status`/`use-version` 4 个真跑过的同级),不是死代码,但 executor 端未派发;(b) **`_invoke` 有 1 行未修复 bug**:`subprocess.run` 缺 `encoding="utf-8"`,CJK 错误时 stdout/stderr 全失,影响所有 `_invoke` 调用。**7 月数据期前必须修**(1 行 patch + monkey-patch 已 ready)。详见 `planning/d6-analyze-probe.md`(140 行,3 层债务表 + 与 4 个已知好命令对比 + 修复 1 行 ready)。 |
| **D-7** | **Track B 5(§5 探针 1)**: `RotatingReferenceFrame` 在 2402 R8 是否存在 | MEDIUM → **DONE 2026-06-12** | starccm-adapter-engineer | 7/20-7/25 | 高;信息 = 8 月 1 个月路径。**新发现**:`star.motion.RotatingReferenceFrame` 存在(4 候选 1/4 命中),走 `continuum.enableModel(cont, "star.motion.RotatingReferenceFrame")` 路径;track-b 候选列表需从 5 个收窄到 1 个 `star.motion.*`。类存在 ≠ enable 成功,完整 1 次 90s spawn 留 7/20-7/25 闭环。详见 `planning/d7-probe-result.md` + `macros/EnableModelProbe.java`(27 行 + 2.2 KB class,均编译 OK)。 |
| **D-8** | **Track C B1-B5 + D1-D5**: V&V 引擎 10 条缺口(schema 扩展 + batch manifest)未实现 | MEDIUM | backend-engineer | 8-10 月分阶段 | 中;不挡 7-8 月 M1/M2,挡 10 月建模期 |
| **D-9** | **Track C C1**: `FlowType.ROTOR_COMPRESSOR` 子枚举未加 | MEDIUM | backend-engineer | 7-8 月 | 高;10 行代码 + 1 个 DEC,接进 PhysicsChecker.check |
| **D-10** | **Track A R-3**: PLAID CC-BY-SA 传染法律风险未与 user 拍板 | LOW | chief-engineer 提议 + user 拍板 | 8 月论文草稿期 | 中;SA 协议 + 商业发布的兼容性 |
| **D-11** | **Track A R-2**: `ParameterizerInterface` 抽象未写 | LOW | backend-engineer | 8 月数据期 ① 起点 | 中;7 月用 CST 跑通后, 8 月切 FFD 时再抽 |
| **D-12** | **Track A R-5**: 2D 阶段先在 LDC + NACA(已有 cfd_harness 资产)上做 surrogate baseline 验证 | LOW | backend-engineer | 10 月建模期 | 中;8-9 月 Rotor37 3D 再上 |
| **D-13** | **Track B 7.4 / 7.5 不排 2 条**: 暂不补 Cl/Cd report / SurfaceCustomMeshControl bind | LOW(已 L0 边界内) | (不补) | 持续 | n/a |
| **D-14** | **Track D #7 / P2**: `mesh_quality/rotor37_metrics.py` | LOW | starccm-adapter-engineer | 9 月底(可推到 10 月初) | 中;3D 样本 mesh gate 机器判 |
| **D-15** | **Track D #8 / #10 / #11 / #14 / #15**: `case_visualize/` 抽口 / `REMOTE_STARCCM` 占位 / `physics/` 占位 / DEC-008.a 治理 / DEC-007 v6+ Cl 闭环 | LOW | various | 2027-Q1+ | 低;7-9 月不烧 |
| **D-16** | **DEC-008.a 子决策**: 7 月底 M1 验收会议 + 登记 | LOW | chief-engineer 提议 + user 拍板 | 7 月底 | 必须(治理性) |
| **D-17** | **Track C R-6**: 4 个 track 都没跑 live test 验证对 comparator 行为理解 | LOW | chief-engineer(可选) | 7 月 | 低;推荐跑一次 baseline 1686-test 中的 auto_verifier 部分 |

### 5.3 总债务分布(2026-06-12 同步更新)
- **HIGH**: **0 条**(D-1, D-2, D-3, D-4, D-5 全部 DONE 2026-06-12)—— M1 验收窗内 HIGH debt 已清零,详见 §5.2 各行 DONE 注
- **MEDIUM**: 4 条(D-6, D-7, D-8, D-9) —— 8-10 月分阶段,部分可推(D-6 `_invoke` 1 行 bug 是 8 月数据期 ① 启动前必修 blocker)
- **LOW**: 8 条(D-10 ~ D-17) —— 2027-Q1+ 或 持续

### 5.4 Risks(若不处理会怎样)

| Risk | Severity | Mitigation |
|---|---|---|
| 7 月底前 3 个 stub 没 scaffold(D-3/D-4/D-5) | HIGH | chief-engineer 7/20 派 3 个并发 subagent 抢时间 |
| Track A R-1 PLAID 3D 字段 24h 内不抓 | HIGH | chief-engineer 24h 内委派 general worker(2h 工作量) |
| vv-director 没拿到 NASA-TP-1338 全文(可能 NASA NTRS 站访问限制) | MEDIUM | fallback = Strazisar TP-2879 表格(已在 Track A §1.1 G-4 列出),精读用 GitHub 第三方切片 |
| DEC-008.a 治理会议 user 不在场 | MEDIUM | chief-engineer 走 L0 "呈报" 流程(简报 + 等 user 拍板),不替 user 决定 |
| 4 个 track 互相不咬合(各自为政) | LOW | 本 verdict §2 闭环 trace 已证明协同路径完整;风险已闭环 |

---

## 6. Ask User 4 问(必须 user 拍板的决策点)

> **Format**: ask_user 形式. 每问给 2-4 个候选 + 推荐项.
> **Source**: Track B §8(2 决策点) + Track D §6(3 优先级) + CHARTER §5(L0 自治范围)合并.

### Q1 · 7 月底前是否 scaffold 3 个 stub?

| 选项 | 内容 | 估时 | 后果 |
|---|---|---|---|
| **(a) 全做**(P1+P2+P3 全 scaffold) | 数字 + 框架 + Python entry + driver 4 件套 | 3-5 天 | **推荐** —— 8 月第一周直接接上,不延后 1 周 |
| (b) 只做 P1(`rotor37.yaml` 数字 + 框架) | 数字 + 框架 2 件 | 1-2 天 | 部分;8 月数据期仍需 1 周 scaffold Python entry + driver |
| (c) 7 月底不做,推到 8 月第一周 | 0 件 | 0 | 8 月第一周 scaffold,延后 1 周 |
| (d) user 反对 3 件套 | (L0 边界内不可行,跳过) | — | — |

### Q2 · 8 月是否排场景 ②(3D 单通道叶片)?

| 选项 | 内容 | 估时 | 后果 |
|---|---|---|---|
| (a) 排 1 个 90s 探针(`EnableModelProbe.java` 30 行) | 7/20-7/25 跑 1 天 | 1 天 | **推荐** —— 1 天成本 = 8 月 1 个月路径信息;若存在 → 3D 8 月可上;若不存在 → 3D 推到 9 月 |
| (b) 不排 | 7 月只做 2D(场景 ① + ③) | 0 | 风险:8 月才知道 3D 可不可上,**8 月可能晚 1 个月** |
| (c) 直接排 1 个完整 3D 模板 macro | 写 `Rotor37SingleChannel.java`(<400 行) | 5-7 天 | 7 月期做 3D 是"早投入",若 `RotatingReferenceFrame` 不存在会浪费 |

### Q3 · L0 → L1 升级?

| 选项 | 内容 | 触发条件 |
|---|---|---|
| **(a) Stay L0** | 7 月期是纯侦察,**0 个端到端跑通** | **推荐** —— L1 触发是"≥2 次端到端零门控违反",目前 0 次 |
| (b) 升 L1 | 7 月底前跑通 1 个 vertical(rotor37_slice MOCK 端 1 个 sample) | 7 月底开 L1 评估会议 |
| (c) 推迟到 8 月末 | 8 月数据期 ① 结束 + 至少 2 个 sample 跑通 | 8 月末开 L1 评估会议 |

### Q4 · 8 月 LHS 100-200 样本是否真用 STAR-CCM+ 跑?

| 选项 | 内容 | 估时 | 后果 |
|---|---|---|---|
| **(a) 混合: MOCK 100 + 真机 30-50** | 7 月排 MOCK 端 LHS 100 个 + 8 月 STAR-CCM+ 端 30-50 个真机 | 2-3 周 | **推荐** —— MOCK 端 100 个 = 复现包 backbone;真机 30-50 = ground truth 验证 |
| (b) 全 MOCK | MOCK 端跑 200 个 | 1 周 | 快;但 8 月出 1 个论文级 ground truth 缺口 |
| (c) 全真机 | STAR-CCM+ 端跑 200 个 | 4-6 周 | 太慢;license + spawn 时间 + 失败重试累积 |

---

## 7. 优先级排序(1 周 / 1 月 / 1 季度)

> **设计原则**: 1 周 = 4 步 chief-engineer 立即动作(对齐 §10 第 1-4 步);
> 1 月 = 7 月底前 3 个 stub scaffold + M1 验收(对齐 §10 第 5 步);
> 1 季度 = 8 月起 数据期 ① + ② + 建模期 ①(原 §10 第 6-7 步迁入此处).

### 7.1 1 周内(7/12-7/19, 下周) — 4 步

1. **24h 内**(D-1): chief-engineer 派 general worker 抓 PLAID Rotor37 3D 字段格式
   (Track A R-1). [2h 工作量]
2. **7/15-7/19**(D-6 + D-7): chief-engineer 派 general worker 跑 1 次 `analyze` CLI 探针
   (Track B §7.3, 30s spawn) + starccm-adapter-engineer 写 `EnableModelProbe.java` 30
   行 + spawn 1 次验 `RotatingReferenceFrame` (Track B §5 探针 1). [15 min + 1 天]
3. **7/18-7/19**: chief-engineer 与 user 拍板 §6 4 问(用 ask_user 一次发完). [30 min]

### 7.2 1 月内(7/20-8/10, 下下周 + 8 月第一周) — 3 stub scaffold + M1 验收

> **设计原则**: 此处是原 §10 第 5 步 + 7 月底前必做项的展开. 1 月时窗 = 7/20 →
> 8/10(M1 验收会议 + 8 月数据期 ① 启动).

1. **7/20-7/25**: chief-engineer 派 3 个并发 subagent:
   - **subagent-1**(vv-director 代理, 用户授权下): 转录 NASA-TP-1338 Table 1 数字
   - **subagent-2**(docs-knowledge-engineer): 写 `gold_standards/rotor37.yaml` 框架(从 Track C 草稿拷)
   - **subagent-3**(starccm-adapter-engineer): scaffold `case_solve/fan_blade.py` 雏形 + `scripts/run_rotor37_macro.py` driver
2. **7/25-7/31**: 跑通"rotor37_slice 在 MOCK 跑 1 次" —— 7 月底会议展示 1 vertical
3. **7/28-7/31**: DEC-008.a 治理会议 + 7 月期 M1 验收
4. **8/01-8/10**: 8 月数据期 ① 启动 —— MOCK 端 2D LHS 100 样本(基于 Track A 选型 CST + Track B 场景 ① 矩阵)
5. **8/10**: 1 月里程碑复盘(回到 §6 R-1 ~ R-5 自检,Track A 给的 checklist)

### 7.3 1 季度内(8 月 - 10 月) — 数据期 ① + ② + 建模期 ①

> **设计原则**: 此处是原 §10 第 6-7 步迁入. 1 季度 = 8/10 → 11/10,覆盖
> 数据期 ① (8 月) + 数据期 ② (9 月) + 建模期 ① (10 月).

1. **8 月数据期 ①** (8/10-8/31): 2D LHS 100-200 样本(MOCK 端主导 + STAR-CCM+ 端 30-50 真机)
2. **9 月数据期 ②** (9/1-9/30): 3D 单通道 30-50 样本(基于 `Rotor37SingleChannel.java` + `case_extractors/fan_aero.py`)
3. **10 月建模期 ①** (10/1-10/31): surrogate baseline 验证(在 LDC + NACA 已有 cfd_harness 资产上做)
4. **持续债务收口**:
   - D-8 V&V 引擎 10 条缺口分阶段补(8-10 月)
   - D-9 `FlowType.ROTOR_COMPRESSOR` 子枚举(7-8 月, 10 行代码 + 1 个 DEC)
   - D-10 PLAID CC-BY-SA 传染法律风险(8 月论文草稿期,user 拍板)
5. **L1 重评估**: 8 月末数据期 ① 结束 + ≥2 个 sample 跑通 + 0 门控违反 + user 拍板后,**可能**升 L1(参照 user profile 2026-06-11 偏好)

### 7.4 优先级排序原则(自定,不是项目硬指标)
- **HIGH debt 先于 MEDIUM 先于 LOW**(债务表 §5.2 排序)
- **M1 验收红线先于 8 月第一周**(7 月底 5 件 HIGH 必做)
- **1 个 spawn 探针 ROI > 1 周静态分析**(Track B §7.3 启示)
- **3 个并发 subagent 抢时间 > 1 个串行**(7 月底前 3 件 HIGH)

---

## 8. Self-verification

| Check | Result | Evidence |
|---|---|---|
| 4 个 track deliverable 全读完 | OK | 191 / 652 / 335 / 260 行 |
| DEC-008 + CHARTER + AGENTS.md sections 全读完 | OK | 103 / 86 / 186 行 |
| 物理树实测(`starccm_adapter/` 子目录) | OK | 5 子目录全无(Track D §1.1 自报正确) |
| `knowledge/gold_standards/*.yaml` 数量实测 | OK | 16 文件,无 rotor37/67(Track C §2 自报正确) |
| 4 track 互相引用一致性 | OK | Track A 文献 → Track C 草稿 source;Track B API → Track D 关键路径;Track D 盘点 → §3 ROI |
| §2 闭环 trace 17 步 file:line | OK | 步 0-17 全有 file:line 证据,1 个 vv-director 独立任务待补 |
| §3 兼容矩阵 9 条硬约束 | OK | 9/9 pass(AGENTS.md §Crew directives 5 + 4 问 gate 4) |
| §4 Go/No-Go 建议 + 4 决策点 | OK | 4 问都有 2-4 个候选 + 推荐项 + ROI 排序 |
| §5 诚实分层 HIGH/MEDIUM/LOW | OK | HIGH 5 条 / MEDIUM 4 条 / LOW 8 条,owner + when |
| §6 ask_user 4 问(决策点) | OK | 4 问 + 候选 + 推荐 |
| §7 优先级 1 周 / 1 月 / 1 季度 | OK | 7.1-7.4 具体动作 + 责任人 + 时间窗 |
| §10 chief-engineer 下一步 — 5 步(无子项目) | OK | 5 主项 + 子项移到 §4.2(Precondition sub-task 列) + 7.2/7.3(原 6-7 步迁入) |
| L0 边界遵守 | OK | 没改 4 个 track deliverable + 没动 STATE.md / yaml / 任何代码 |
| 唯一写盘 = 1 个 verdict .md + 1 个 deliverable.md + 2 条 board entry | OK | 不写代码,不签 manifest,不切 executor mode |

---

## 9. The deliverable paths

| File | Purpose |
|---|---|
| `D:\CFD-harness-Windows-StarCCM\reports\research\commercial-fan-prop\verdict-2026-07.md` | (this file) the 7 月期 verdict |
| `C:\Users\Kogami\.mavis\plans\plan_22415a38\outputs\track-z-synthesis\deliverable.md` | deliverable.md the engine reads |
| `C:\Users\Kogami\.mavis\plans\plan_22415a38\board.md` | progress board (3 entries appended by track-z) |

---

## 10. What chief-engineer should do next (specific, actionable)

> **Time-box**: 下周(7/12-7/19) 共 **5 步**. 8 月起的工作迁入 §7.2/§7.3.
>
> **2026-06-12 同步更新**: 步骤 4(派 3 个并发 subagent scaffold 3 个 stub)**已提前到 2026-06-12 完成**(P1/P2/P3 全部 7 月 1 日就位,见 §5.2 D-2/D-3/D-4/D-5);步骤 5(评审会议 + DEC-008.a 登记)**部分完成** — DEC-008.a 已登记(`decisions/DEC-008.a-m1-acceptance.md`),M1 验收会议仍待 user 拍板 7/18-7/19 ask_user 4 问后召开.

1. ✅ **24h 内**(D-1): 抓 PLAID Rotor37 3D 字段格式 — **DONE 2026-06-12**。详见 `planning/d1-plaid-probe.md`(PLAID = Safran RANS 仿真,不能当 gold,D-2 仍需 NASA-TP-1338 + Suder 1995 转录)。
2. ✅ **7/15-7/19**(D-6 + D-7): D-6+D-7 **双 DONE 2026-06-12**。**新发现 2 条**: (a) 桥接层 `_invoke` 缺 `encoding="utf-8"` 1 行 bug(影响所有 `_invoke` 调用,7 月数据期前必修);(b) `star.motion.RotatingReferenceFrame` 存在,3D 旋转域路径 GREEN;track-b 候选列表收窄到 1 个 `star.motion.*`。详见 `d6-analyze-probe.md` + `d7-probe-result.md` + `macros/EnableModelProbe.java`。
3. **7/18-7/19**: 跟 user 拍板 §6 4 问(ask_user 一次发完)。
4. ✅ **7/20-7/25**: 派 3 个并发 subagent scaffold 3 个 stub — **已提前到 2026-06-12 完成**(P1/P2/P3 全部 7 月 1 日就位;P1 RETRY v3 14/14 all_pass + P2 4/4 smoke test 0.26s + P3 mock exit 0 + Java 编译 RC=0;详见 §5.2 D-2/D-3/D-4/D-5)。
5. **7/25-7/31**: 评审会议 + 3 个 stub scaffold 验收 + DEC-008.a 登记(M1 验收窗)。**部分完成** — DEC-008.a 已登记(`decisions/DEC-008.a-m1-acceptance.md` 2026-06-12),M1 验收会议仍待 7/18-7/19 user 拍板后召开。

> **8 月起的工作**(原第 6-7 步)迁入 §7.2(1 月内: 8 月数据期 ① 启动) +
> §7.3(1 季度内: 8-10 月 数据期 ① + ② + 建模期 ①). **不在此 §10 重复.**

---

## 11. Verifier 链接

- 本 verdict doc 路径:`D:\CFD-harness-Windows-StarCCM\reports\research\commercial-fan-prop\verdict-2026-07.md`
- 关键节锚点:§0 TL;DR / §1 4 track 独立核验 / §2 闭环 trace / §3 兼容矩阵 9/9 / §4 Go/No-Go / §5 债务 5 HIGH / §6 ask_user 4 问 / §7 优先级 1 周/1 月/1 季度 / §10 chief-engineer 下一步.
- **一句话给 user**: 7 月期 4 个 track 协同合格,artifact 可消费,**3 个 stub 已于 2026-06-12 提前到 7 月 1 日全部 scaffold**(原计划 7/25-7/31),HIGH debt 5 件全清零;L0 暂不升(0 个端到端跑通);8 月数据期 ① 启动前必修 = `_invoke` 1 行 bug(D-6)+ RRF enable 90s 探针(D-7);建议 MOCK 100 + 真机 30-50 混合模式;§6 4 问请 user 拍板后开 M1 评审会议 + DEC-008.b 待 8 月末登记.

---

VERDICT: PASS-WITH-CONDITIONS
(7 月期立项合格. **3 个 stub 已于 2026-06-12 提前到 7 月 1 日全部 scaffold**(原计划 7/25-7/31),HIGH debt 5 件全清零. L0 暂不升. 8 月数据期
排期见 §7. 4 决策点见 §6. 债务清单见 §5.2. 8 月启动前必修 = D-6 `_invoke` 1 行 bug + D-7 RRF enable 90s 真 spawn 探针.)
