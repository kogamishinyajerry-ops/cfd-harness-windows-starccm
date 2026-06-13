# 立项备忘 · 民机风扇与螺旋桨叶片参数化建模与 AI-CFD 优化设计

> 创建于 2026-06-12 03:36+08,主理:Mavis (root)
> 上游输入:用户提供的"民机风扇与螺旋桨叶片参数化建模与 AI-CFD 优化设计研究分析报告"
> 治理等级:L0 advisory(沿用 AGENTS.md §Graduated autonomy,等审过 2 次端到端再讨论 L1)
> 协作授权:用户授权"完全批准多 agent 协作科研"

## 1. 决策摘要(全本遵循)

| 维度 | 选定方案 | 理由 |
|---|---|---|
| 目标几何 | **C · 风扇 + 螺旋桨两条线都做,风扇先、螺旋桨后** | 报告 §"可行研究课题"主线 = 风扇(Rotor37/67),螺旋桨作为第 2 篇差异化素材;两条线共用一套参数化器+surrogate 流水线,边际成本低 |
| STAR-CCM+ 端补 API | **B · 暂不补,先绕开** | 报告 4-6 月才需要三维批量,8-9 月前二维为主;Codebuddy REPL 现状已够跑二维截面+单通道基线 |
| 首篇论文主轴 | "参数化 + OpenFOAM/STAR-CCM+ 样本 + 神经代理 + 多目标优化" | 报告"综合优先级 = 最高",与 L0 advisory 的工程稳态叙事一致 |
| 备选 1 | VAE/GAN 神经形状参数化(差异化) | 报告"较高"优先级,作为论文"扩展章节"或第 2 篇核心 |
| 备选 2 | 多保真气动-结构 MDO | 报告"较高"优先级,需结构求解条件;本项目暂不锁 |
| 排除 | PINN 边界层建模 / 可微 solver 内循环 | 报告判定工程风险高、稳定性弱;留作第 2 篇方法学扩展 |
| 时间跨度 | **12 个月**(2026-07 → 2027-06) | 报告路线图;里程碑:3 月 2D surrogate / 6-7 月 3D 叶片 / 9-10 月回验 |
| 目标期刊(首篇) | AIAA Journal / Computers & Fluids / Aerospace Science & Technology | 报告"发表潜力"评估 |
| 验证参照 | NASA Rotor37/Rotor67(风扇)+ UIUC 翼型库(2D) + 自建数据集(3D 叶片) | 报告"公共参照"建议 |

## 2. 12 个月里程碑(从报告路线图细化)

```
2026-07  ─── 立项收口:参数化器选型、Rotor37 数据集清单、case generator
2026-08  ─── 数据期 ① :2D 截面 LHS 100-200 样本,MOCK 端先打通
2026-09  ─── 数据期 ② :3D 单通道叶片 30-50 首批样本
2026-10  ─── 建模期 ① :U-Net/FNO/DeepONet 三选一 baseline
2026-11  ─── 建模期 ② :Surrogate 误差统计 + 消融
2026-12  ─── 优化期 ① :NSGA-II + 主动学习加点
2027-01  ─── 优化期 ② :Pareto 前沿 + 高保真回验
2027-02  ─── 写作期 ① :draft v1 + 图表库
2027-03  ─── 写作期 ② :消融 + 复现包封装
2027-04  ─── 内部审稿 + 改稿
2027-05  ─── 投预印本(arXiv/AIAA SciTech)
2027-06  ─── 投正刊(AIAA Journal / Computers & Fluids)
```

## 3. 复用现有资产(SSOT:STATE.md §"Covered map")

| 已有 | 用在哪 |
|---|---|
| `cfd_harness.auto_verifier` V&V 引擎 | 样本真实/虚拟值对比、`gold_standard` 验证 |
| `cfd_harness.executor` MOCK + WIN_STARCCM 双轨 | 7 月 MOCK 跑通、8 月起 WIN_STARCCM 跑真实样本 |
| `cfd_harness.audit_package` 签名 manifest | 复现包/数据集的"任何一行可追责" |
| `cfd_harness.report_engine` | 误差/校准/覆盖率自动出表 |
| `knowledge/gold_standards/*.yaml` | 新增 `rotor37` / `rotor67` 黄金标准文件 |
| `packages/starccm-bridge/` Codebuddy REPL | 8-9 月起在二维/单通道调用 |
| `.harness/reins/chief-engineer/` 编排 | 多 agent 主理 |
| `.harness/reins/vv-director/` | V&V 与"covered"判定 |
| `.harness/reins/system-architect/` | 四平面律 + 边界 |
| `.harness/reins/starccm-adapter-engineer/` | STAR-CCM+ 端 Java 反射实现 |

## 4. 待补资产(在 chief-engineer 协调下分阶段落实)

| 缺口 | 优先级 | 触发时机 |
|---|---|---|
| `gold_standards/rotor37.yaml` + `rotor67.yaml` | P0 | 7 月立项期 |
| `src/cfd_harness/starccm_adapter/case_solve/fan_blade.py` | P1 | 8 月数据期 |
| `src/cfd_harness/starccm_adapter/case_extractors/fan_aero.py` | P1 | 8 月数据期 |
| `src/cfd_harness/starccm_adapter/mesh_quality/rotor37_metrics.py` | P2 | 9 月 |
| `src/cfd_harness/surrogate/`(U-Net/FNO/DeepONet 三选一) | P0 | 10 月建模期 |
| `src/cfd_harness/optimization/nsga2_loop.py` | P1 | 12 月优化期 |
| `src/cfd_harness/active_learning/ei_acquisition.py` | P2 | 12 月 |
| `macros/Rotor37Slice.java` + `Rotor37SingleChannel.java` | P0 | 8 月 |
| `macros/PropellerOpenRotorSlice.java` | P2 | 2027-Q3 起(螺旋桨线) |

## 5. 自治范围与边界(L0)

- **L0 内可自行决定**:四问门控应用、DEC 起草与登记、track 内任务分派、mock-first 一切实现、helper 脚本、内部包目录布局、case 模板。
- **L0 内做但必须呈报**(根 session 走 LLM 直答 / 简短汇报):任何修改 `gold_standards/*.yaml` 已有 `reference_values` 的提议;任何把 `ExecutorMode.MOCK` 切到 `WIN_STARCCM` 的链路;任何修改 `ADR-001-four-plane` 的尝试;任何向 `Cases/` 写 >100MB 大文件;任何 `git push`。
- **L0 之外,必须 ask_user**:删文件(>10MB)/清理磁盘、扩缩 L0→L1 等级、决定本项目是否合并到主仓(目前判定:独立子项目,但产物在主仓 `reports/research/commercial-fan-prop/`)、对外公开(arXiv/期刊)/延期/放弃。

## 6. 引用与依据

- 上游报告(用户粘贴) — 2026-06-12
- AGENTS.md §"Definition of success" / §"Crew directives" — 项目级不变量
- STATE.md §"Open DECs" / §"Stage 3+ optimization pass" — 当前已锁路径
- 报告 §"可行研究课题" 6 个候选 — 已被本备忘收敛到 1+2 备选
- 报告 §"软硬件、预算与数据策略" — 资源估算(本项目用 32-64 核 + 1×24GB GPU 量级)

## 7. 立即行动(本 session 内)

1. [DONE] 登记本备忘到 STATE.md
2. [IN PROGRESS] 起 mavis-team plan,3-4 个并行 track
3. [PENDING] 各 track 在 7 月期内出最小可交付(milestone-1)
