# DEC-008 · 民机风扇/螺旋桨 AI-CFD 项目立项(L0)

**Date**: 2026-06-12 03:36+08
**Status**: accepted
**Driver**: user (top-level approval)
**Coordinator**: Mavis (root session mvs_0424b8e3e95b4e96a50ced2f1206f915)
**Scope**: project-charter (cross-module, defines a new research stream under the
existing cfd-harness-windows-starccm umbrella)

## 1. Context

用户提交了一份 2.5 万字的研究分析报告("民机风扇与螺旋桨叶片参数化建模
与 AI-CFD 优化设计研究分析报告",2026-06-12),涵盖近 5 年公开文献综述、6 个
可行研究课题、12 个月路线图、软硬件预算与开放问题。报告由用户主笔,
我方(团队)对真实可实施性负责。

## 2. Decision

按用户最终指示 `1C + 2B + 全权`,立项如下:

### 2.1 项目

- **代号**:`commercial-fan-prop`
- **目录**:`D:\CFD-harness-Windows-StarCCM\reports\research\commercial-fan-prop\`
- **周期**:12 个月(2026-07 → 2027-06)
- **形态**:不独立建仓,作为主仓的 `reports/research/` 子项目

### 2.2 目标几何

两条线,先风扇后螺旋桨:

| 序 | 类别 | 目标 | 验证基线 |
|---|---|---|---|
| 1 | 风扇 | NASA Rotor37 / Rotor67 单通道叶片 + 2D 截面 | 公开 Rotor37 实验/数值数据 |
| 2 | 螺旋桨 | 开放转子(对转) | Wang 2024 infilling 文献 + UIUC 翼型库 |

不锁死叶片厂商/IP,沿用 NASA/UIUC 开源参照系。

### 2.3 主线技术路线

报告 §"综合优先级 = 最高" 的方案:

> 参数化叶片几何(8-18 变量)+ 神经代理模型(U-Net/FNO/DeepONet 选一)
> + 主动学习加点 + 多目标优化(NSGA-II / EGO)

STAR-CCM+ 端只跑它做得到的部分(单 case 生成样本),OpenFOAM 端
做对照与多保真验证(报告 4-plane law 不允许混)。

### 2.4 STAR-CCM+ API 补全策略

`B · 暂不补`。理由:

- 报告 4-6 月才需要三维批量样本
- 二维截面/单通道 → 现有 Codebuddy REPL 已可
- 不让 chief-engineer 在 7 月就掉进 API 探坑,先走 MOCK 闭环
- DEC-007 v3-v5 已暴露 solver deadlock 风险,不应同时再叠新 API

### 2.5 治理

- 等级:**L0 advisory** (沿用 AGENTS.md §Graduated autonomy)
- 升级 L1 触发:本项目至少 2 次端到端里程碑(milestone-1 + milestone-2)零门控违反
- 自治范围见 `planning/CHARTER.md` §5

## 3. Rationale (为什么这样定)

- **1C 而非 1A**:用户回复原话"两个都做,A 先 B 后",直接对齐。
- **2B 而非 2A**:用户回复"暂不补";同时报告第 7 页"如果预算有限,最强 CPU/RAM
  比最顶配 GPU 更决定论文质量" — 投入应集中在样本生成端,而 STAR-CCM+ API 补全
  对 7-9 月数据期 ROI 偏低。
- **不切 WIN_STARCCM 默认**:MOCK 链路是 v1 基准;`WIN_STARCCM` 显式 opt-in
  (沿用 DEC-001 + EXECUTOR_ABSTRACTION §6.1)。
- **不立项 VAE/GAN 为主线**:报告虽列"较高"优先级,但工程落地需要大量
  几何清洗 + 制造约束建模;首篇论文应优先 surrogate + 优化主线,
  VAE/GAN 留作第 2 篇或本论文扩展章节。

## 4. Consequences (影响面)

| 影响 | 区域 | 负责人 |
|---|---|---|
| STATE.md 新增 1 个项目 + 1 个 L0 grant | `reports/STATE.md` | Mavis (root) |
| AGENTS.md 增补本项目约束 | `AGENTS.md` | chief-engineer 提议 |
| 4 份立项/规划文档落地 | `reports/research/commercial-fan-prop/` | chief-engineer |
| `gold_standards/rotor37.yaml` 新增 | `knowledge/gold_standards/` | vv-director 起草 |
| `cfd_harness/starccm_adapter/case_solve/fan_blade.py` | `src/cfd_harness/starccm_adapter/` | starccm-adapter-engineer |
| `cfd_harness/surrogate/`(U-Net/FNO/DeepONet) | `src/cfd_harness/` | backend-engineer |
| Codebuddy REPL 验证 | `packages/starccm-bridge/` | starccm-adapter-engineer |
| 多 agent 协作:起 mavis-team plan | — | Mavis (root) |
| 不影响:Stage 3+ / DEC-005 / DEC-007 v3-v5 既有债务 | — | — |

## 5. Open follow-ups (在本决策下需进一步登记的子决策)

- **DEC-008.a**:立项期(7 月)结束后,判定里程碑 1 是否合格,登记为 DEC-008.a
- **DEC-008.b**:数据期(8-9 月)结束后,判定首批样本是否够,登记为 DEC-008.b
- **DEC-008.c**:建模期(10-11 月)结束后,判定 surrogate 误差是否收敛,登记为 DEC-008.c
- **DEC-008.d**:优化期(12-1 月)结束后,判定 Pareto 前沿是否优于基线,登记为 DEC-008.d
- **DEC-008.e**:L0→L1 升级 ask(若用户在 2027-Q1 之后提出)

## 6. Cross-references

- 上游决策:无
- 并行决策:DEC-007(NACA 闭环)、DEC-005(LDC FF 采样)— 不冲突,本项目与之解耦
- 用户偏好:"分层诚实报告" / "X% 完成 Y% 没做" / L0→L1 必须 evidence-gated
  (见 user profile 2026-06-11)
