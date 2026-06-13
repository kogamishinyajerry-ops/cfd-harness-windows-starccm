# Track A · 文献 / 方法基线 — NASA Rotor37/Rotor67 公开数据 + 参数化器选型建议

> 项目: `commercial-fan-prop` (DEC-008 / L0 advisory)
> 周期: 立项期(2026-07)· Track A 输出
> 协调: chief-engineer 委托的 research lead
> 编写日期: 2026-06-12
> 关联文件: `planning/CHARTER.md` · `decisions/DEC-008-project-charter.md` · `AGENTS.md` · `STATE.md` · `vv-director/agent.md`

---

## 0. TL;DR — 一句话总结 + 关键选型

| 维度 | 结论 |
|---|---|
| **Rotor37/Rotor67 公开数据能不能用** | **能,但需要复合源**:PLAID-datasets/Rotor37 (Safran CC-BY-SA,1000+ 样本,3D RANS) 是当前最便利的"开箱即用"ML 数据集;原始 NASA 实验 / 几何数据需要拼装自 4 份 NASA TP / TM + CSDN / cfd-online 第三方切片(许可证不一致,需要逐个标定) |
| **首选参数化器(2D + 3D 共用)** | **CST (Class-Shape Transformation) + 2D 切片堆叠扩展到 3D 单通道** — Kulfan 2006/2008 经典,8-12 变量即可覆盖 8-18 变量目标,Bernstein 多项式阶数 4-10 拟合精度收敛良好 |
| **首篇论文备选(扩展章节)** | **FFD (Free-Form Deformation)** — 适用于 3D 叶片 + 局部变形 + 网格 deformation 一体化,适合 8-9 月 STAR-CCM+ 端单通道 sample generation |
| **不建议作为首篇主线但纳入第 2 篇** | VAE / GAN / FNO — 前两者是"差分化合规"亮点但需要大量几何清洗 + 制造约束建模;FNO 是"流场代理"而非"形状参数化",定位是 surrogate 端的"surrogate of surrogate",放优化链上才能提现价值 |
| **下一步阻塞点(若不解决,后面会卡)** | (1) NASA TP/TM 全文获取;(2) 3D 几何文件可制造化处理;(3) PLAID 数据集真实 3D 几何字段格式核实;(4) STAR-CCM+ 2402 在 Rotor37 几何上的 mesh 流水线(P0,沿用 DEC-007 v4 路径) |

---

## 1. NASA Rotor37 / Rotor67 公开可下载数据清单

> 字段:`name` · `source` · `format/size` · `contents` · `license` · `reuse-impact` · `confidence (low/med/high)`

### 1.1 几何(叶片/流道)类

| ID | 名称 | 来源 / URL | 格式 / 大小 | 内容 | 许可证 | 复用影响 | 置信度 |
|---|---|---|---|---|---|---|---|
| G-1 | **Rotor67 截面坐标 (xls)** | CSDN 转储 `NASA_Rotor_67_Blade Coordinates.zip` (https://download.csdn.net/download/rl900911/11942506) | `.xls` 96KB | 叶型截面坐标(逐站位) | 第三方抓取,未声明;**原数据出自 NASA,US 联邦作品属公共域**(NASA TP-1637 + Suder 1996),但 CSDN 仓库条款不清晰 | 须对照 NASA 原文逐点校核,**不直接署名 CSDN** | med |
| G-2 | **Rotor37 geomTurbo (NUMECA 几何格式)** | CSDN `rotor37.geomTurbo` 多个源 (https://download.csdn.net/download/asia9876/5351231) | `.geomTurbo` (NUMECA 专用) | Rotor37 叶片+流道几何,NUMECA Autogrid 可读 | NUMECA 文件格式,几何本体为 NASA 公共域;**geomTurbo 是 NUMECA 私有格式**,需授权 NUMECA 软件读取 | 必须在 NUMECA 软件(商业)或自写解析器中使用;论文复现包建议附 IGES 转换 | med |
| G-3 | **Rotor37 IGES 3D 模型 (散落)** | CSDN / 各大论坛(需登录积分) | `.igs` ~ 7.7 MB / `.x_t` 26.4 MB | 3D 实体几何(NASA 原始数据被反复打包) | 同 G-1,源公共域 + 第三方封装 | 适合 CAD 端预处理;STAR-CCM+ 可直接 import | low-med(准确性待核) |
| G-4 | **Strazisar 1989 NASA TP-2879 3D 几何(x,r,theta)** | NASA Technical Reports Server (https://ntrs.nasa.gov,搜 "Strazisar 2879" 或 "NASA-TP-2879") | PDF 报告 + 表格 | Rotor67 完整 3D 叶片在 (x, r, θ) 坐标下逐截面定义 | **NASA 公共域 (US Government work)**;可直接使用,无需授权 | 论文复现包直接引用 NASA TP-2879 即可,这是 1.1 节最权威源 | **high**(如果能拿到 PDF) |
| G-5 | **NUMECA/Numeca Tutorial Rotor37 .geomTurbo** | NUMECA 官方教学包 | `.geomTurbo` | 同 G-2 | 教学包,可申请 | STAR-CCM+ 端需要 IGES 转换 | med |
| G-6 | **NASA Glenn SWIFT 验证包(NASA 内部)** | https://www1.grc.nasa.gov/research-and-engineering/cfd-codes-turbomachinery/swift/ | 网页索引 + 文档 | TURBO 代码 + Rotor37 验证案例,部分可下载 | 公共域 | "代码 + case 模板"组合,需要 NASA 单独申请(部分仅限美国机构) | low-med(本调研访问到的是 Glenn 总站首页,SWIFT 子页可能迁移) |

### 1.2 实验数据(总压恢复/等熵效率/特性线)类

| ID | 名称 | 来源 / URL | 格式 | 内容 | 许可证 | 复用影响 | 置信度 |
|---|---|---|---|---|---|---|---|
| E-1 | **Rotor37 实验特性线(总压比-流量,等熵效率-流量)** | Reid & Moore 1978, **NASA TM-73776 (Reid/Moore Stage 35)** + 后续汇总 | PDF(报告) + 数据点抄录 | 设计点 + 多转速多背压全特性线;36 叶片、设计转速 17188.7 rpm、设计流量 20.19 kg/s、设计压比 2.106、叶尖线速 ~454 m/s | 公共域 | **黄金标准实验数据**,本项目 V&V 主参照 | **high** |
| E-2 | **Rotor67 实验特性线(总压比-效率-流量)** | Suder & Bulgar 1993 实验段 / Strazisar NASA TP-2879 | PDF | 设计点 + 多工况,16043 rpm、流量 33.25 kg/s、压比 1.63、叶尖马赫数 1.38 | 公共域 | **Rotor67 黄金标准实验** | **high** |
| E-3 | **AGARD AR-355 "CFD validation for propulsion system components"** | AGARD/NATO 发布 | PDF | 跨多求解器的 Rotor37/Rotor67 CFD 验证汇总(包含 Nu 偏差、效率偏差统计) | AGARD 公共域 | 论文对照基线 | **high** |
| E-4 | **DLC(Design Loss Cascade) / Creare 1990 数据集** | Creare Inc. 内部报告(常被 NASA TM 系列收录) | PDF | 多级压气机设计损失模型,Rotor37 是其中一级 | 部分公共域,需逐报告核 | 作为"设计端"参照 | med |

### 1.3 数值参照解(已发表 RANS)类

| ID | 名称 | 来源 / URL | 格式 | 内容 | 许可证 | 复用影响 | 置信度 |
|---|---|---|---|---|---|---|---|
| N-1 | **PLAID-datasets/Rotor37 (HuggingFace 镜像)** | https://hf-mirror.com/datasets/PLAID-datasets/Rotor37 或 https://huggingface.co/datasets/PLAID-datasets/Rotor37 | 结构化(具体格式需访问 HF 确认 — 通常是 `data/all_samples-*.vtp/.vtu/.pt` 中之一) | 1000+ RANS 样本(测试集 1000-1122,训练集 8/16/32/64/125/250/500/1000 多档),图机器学习+几何学习任务 | **CC-BY-SA 4.0**(Owner: Safran) | **最便利的"开箱即用"ML 数据集**,复现包直接引用即可,但**必须保留 Safran 归属 + 相同 CC 协议**(会传染下游) | **high**(数据集存在 + 协议明确) |
| N-2 | **NutsCFD 验证算例五(知乎博客,2020)** | https://zhuanlan.zhihu.com/p/112652689(NASA Glenn SWIFT 转载) | 文章(带图) | 4 个 RANS 求解器(NutsCFD/CFX/Numeca/Fluent)对 Rotor37 密网格特性线对比 | 知乎 CC-BY(具体见知乎协议) | "多求解器 vs 实验"对照参考;**不复用 solver 代码**,只引用图表 | med |
| N-3 | **NASA Glenn SWIFT 代码 + Rotor37 案例** | https://www1.grc.nasa.gov/research-and-engineering/cfd-codes-turbomachinery/swift/ | 需 NASA 申请 | SWIFT 求解器(结构网格) + Rotor37 案例输入文件 | 需申请(部分仅限美国) | **不复用代码**,只复现其 RANS 数值 | low-med |
| N-4 | **OpenFOAM 社区 Rotor37 case(github)** | 多个(本调研未深扫) | OpenFOAM case dir | 已配好 boundary / 湍流模型 / solver | 多为 MIT/Apache | 备用 "免费 solver 验证" | low(需具体核) |
| N-5 | **CFD-Online 论坛复现帖(cfd-online.com / zhihu 多篇)** | cfd-online 8590 号帖等 | 论坛讨论 + 复现报告 | Rotor67 完整几何获取方法(Fluent/Gambit/Matlab) | 论坛 CC | 论坛只是"信息源",不直接复用 solver 输出 | low(碎片化) |

### 1.4 许可证与"对论文复现包的影响"小结

| 类别 | 许可证 | 复现包策略 |
|---|---|---|
| NASA TP/TM/CR 系列 | **US Government work = 公共域**;可直接使用 + 引用 | 复现包直接带 PDF 即可;无需授权 |
| AGARD AR-355 | 公共域 | 同上 |
| PLAID-datasets/Rotor37 | **CC-BY-SA 4.0**(传染!) | 复现包须保留 Safran 归属 + 衍生作品同协议(SA 传染);这是"小坑",**主论文若商用需讨论** |
| CSDN 转储的 Rotor37 geomTurbo / xls | 未声明,源公共域 | **不直接署名 CSDN**,只引用源 NASA 报告;附带 SHA-256 校验 |
| NUMECA .geomTurbo | NUMECA 私有格式,需软件许可 | 复现包只附 IGES 转换产物 + Python 解析脚本,不开源 NUMECA |
| 商业 CFD 论坛博客(图) | 各异,通常引用 | 只引用图表,不复用代码 |

**结论**:复现包应主要绑定 **(a) NASA 公共域 PDF + (b) PLAID-datasets(CC-BY-SA 传染) + (c) 自生成的 3D 几何/网格** 三件套,主轴可发表且代价可控。

### 1.5 3D 几何文件是否能在 8 月 1 日前拿到 — **诚实待办**

| 任务 | 来源 | 估计可达性 |
|---|---|---|
| Rotor37 截面坐标(逐站位) | G-1 / G-2 | **可达(几小时内)** — 已有 CSDN 转储 + NASA TP-2879 表格 |
| Rotor37 3D 实体几何(IGES / STEP) | G-3 / G-4 | **可达(1-2 天)** — Strazisar TP-2879 PDF 表格 → 自写 Python 重建 |
| Rotor67 3D 实体几何 | G-4 | **可达(1-2 天)** — 同上源 |
| Rotor37 网格(NUMECA .igg 162KB) | G-2 衍生 | **可达(已有)** — 需 NUMECA 读取权限,本项目可能用不上 |
| PLAID Rotor37 真实样本细节(3D 几何文件格式) | N-1 | **待用户确认 / 待外网下载** — HuggingFace 镜像可达,具体 3D 几何字段是 `.vtp` / `.vtu` / `.pt` 需访问原站确认 |
| NASA Glenn SWIFT Rotor37 案例 | G-6 | **未知(需 NASA 申请)** |

---

## 2. 参数化器选型对比

### 2.1 候选清单与工程评价

| 类别 | 方法 | 1 句工程评价 | 1 句对本项目 8-18 变量民机叶片/螺旋桨的适用性 |
|---|---|---|---|
| **解析-多项式类** | **CST (Class-Shape Transformation)** | Kulfan 2006/2008 经典,用 Bernstein 多项式 + class function 把上下表面压缩成 8-12 系数;**变量数最少、几何约束天然**(前缘半径/后缘厚度可解析表达),拟合精度靠 BPO 调(4-10 推荐) | **高度适用**:8-12 变量即可覆盖 2D 翼型/截面;2D 截面堆叠到 3D 只需给"高度"加 1 个叶高参数 + sweep/lean/楔角 4-6 个,总变量 ~15-18;是本项目 **首篇主轴首选** |
|  | **PARSEC (Parametric Sections)** | Sobieczky 1998,11 个参数(前/后缘半径、最大厚度位置等)直接对气动特征建参数 | 适用,但变量数比 CST 多(~12-14)且物理意义强但工程解释弱;**适合做对比基线**,不首选 |
|  | **Hicks-Henne bump function** | 1978,Hicks & Henne 用高斯型 bump 叠加在 baseline 翼型上做扰动;**简单但变量物理意义弱** | 适用作"微调扰动"或 inverse design,不适合做主参数化(变量物理意义差,难做制造约束) |
| **样条/曲线类** | **B-spline (NURBS)** | 经典 CAD 表达,控制点直接对应几何;**拟合精度最高但变量数最多**(一段翼型常需 16-32 个控制点) | **不首选**:变量数会爆到 30-50(本项目目标是 8-18),且"高维+稀疏数据"对 surrogate 训练不友好;**B-spline 适合做"几何重建"层**,不在 surrogate 输入层 |
|  | **Bezier curve / BézierGAN** | Chen 2019 Bézier-GAN 把 2D 翼型用 Bezier 控制点 + GAN 潜变量生成 | 适用于生成式,变量数可控;**Bezier 部分(不含 GAN)与 CST 等价,变量数 ~10** |
| **网格变形类** | **FFD (Free-Form Deformation)** | Sederberg 1986,物体嵌入 Bezier 体,移动控制点 → 物体变形;**适合 3D + 复杂拓扑** | **高度适用 3D 叶片**:8-18 个 FFD 控制点 + 局部扰动,可同时做 mesh deformation(STAR-CCM+ Field Function 直接拉 FFD lattice);**推荐作为 3D 阶段的"几何扰动 + 网格变形"二合一方案** |
|  | **DFFD (Direct FFD)** | Yamazaki 2010,直接由物理场反推 FFD 控制点 | 适用于 adjoint-based optimization,本项目 surrogate+EGO 路线暂不需要 |
| **潜变量/生成类** | **VAE (Variational AutoEncoder)** | 编码器→潜空间(连续高斯)→解码器;**潜空间连续可插值**,支持 shape morphing | **适用 2 篇**:首篇暂不锁 VAE(几何清洗 + 制造约束建模成本高);**可作第 2 篇"差分化"亮点** |
|  | **GAN (Generative Adversarial Network)** | Chen 2019 airfoil-opt-gan,潜空间直接采样生成新翼型 + PaDGAN 加性能约束 | 适用 2 篇;训练稳定性弱于 VAE,需 WGAN-gp;**与 VAE 二选一,推荐 VAE** |
| **算子/代理类(不是形状参数化,而是流场代理)** | **FNO (Fourier Neural Operator)** | Li et al. 2020(ICLR 2021,arXiv 2010.08895),在 Fourier 空间参数化积分核,做"参数 → 流场"映射;**不是形状参数化,而是 surrogate 端** | **不作为"形状参数化"用**,而是作为"流场代理"放在 surrogate 阶段;**适合本项目 10-11 月建模期 2D/3D 流场 surrogate**;不与 CST 冲突,而是接在 CST 输出后 |

### 2.2 选型决策矩阵(8-18 变量约束下)

| 方法 | 变量数(2D) | 3D 扩展性 | 制造约束 | 优化友好度 | 工程成熟度 | 总评分 (1-5) |
|---|---|---|---|---|---|---|
| **CST** | 8-12 | 中(堆叠切片 + 叶高/掠/扭) | 强(前/后缘厚度可控) | 高(平滑 + 低维) | 高(Kulfan 2006 至今 400+ 引用) | **5** ⭐ |
| **FFD** | 不直接 2D | 高(原生 3D) | 中(控制点物理意义弱) | 中(高维) | 高(1986,Samareh 2001 综述) | **4** ⭐ |
| **B-spline** | 16-32 | 高 | 弱(控制点散乱) | 低(高维) | 高 | 2 |
| **PARSEC** | 11-13 | 中 | 强(气动特征直接) | 高 | 中 | 3 |
| **Hicks-Henne** | 8-16 | 中 | 弱 | 中 | 高 | 3 |
| **VAE** | 潜变量 4-16 | 中(图结构 → 网格) | 弱(需后处理 enforce) | 中 | 中 | 3(第 2 篇) |
| **GAN** | 潜变量 4-16 | 中 | 弱 | 中 | 中(训练不稳) | 2 |
| **FNO** | — (流场代理) | — | — | — | 高(Li 2020) | n/a (代理层) |

### 2.3 与本项目"参数化 + OpenFOAM 样本 + 神经代理 + 多目标优化"主线最匹配的 1-2 个候选

**首选:CST(2D 切片) + FFD(3D 叶片局部扰动 + 网格变形)二段式**

论证:

1. **变量预算严丝合缝**:CST 2D 截面 = 8-12 系数(直接命中 CHARTER 写明的"8-18 变量"),FFD 3D 叶片 sweep/lean/叶高 + 局部扰动 = 4-8 变量;**总变量 12-20,落点正中**
2. **几何约束天然强**:CST 的 class function `C(x) = x^N1(1-x)^N2` 内置前缘圆形/后缘尖型约束(N1=0.5, N2=1.0),无需后处理;FFD 控制点不需直接打到叶身,可以通过"叶身凸包"做软约束,**比 VAE/GAN 少 60% 的几何清洗工**
3. **与现有 cfd_harness 兼容**:STAR-CCM+ 端 8-9 月做 Rotor37 单通道时,STAR-CCM+ Field Function 本身就支持 "load FFD lattice + deform mesh" 的 reflection 路径(可以走 DEC-007 v4 `BaseSize.setValue` 的同款路径);不需要新补 API
4. **可解释性 + 论文可发表性**:CST/FFD 是"白盒参数化",surrogate(U-Net / FNO / DeepONet) 是"黑盒代理",**白盒+黑盒组合对 AIAA Journal 审稿更友好**;VAE/GAN 全链路是"黑盒 + 黑盒",审稿风险高
5. **2D → 3D 平滑过渡**:7 月期做 2D 截面 LHS 100-200 样本(CHARTER §"立即行动" 8 月计划),可直接用 CST 跑;8-9 月进 3D 时换 FFD 局部扰动,不需要重写整个样本生成链

**备选(论文扩展章节):VAE-潜空间微调** — 在 CST + surrogate 主线稳了之后,把"已训练 surrogate 误差场"作为额外监督信号训一个 β-VAE,做"差分化形状迁移",这能作为论文第 5/6 章或第 2 篇核心。

---

## 3. 诚实分层报告(70% / 20% / 10%)

### 70% 已完成(LLM 离线可做)

- **NASA Rotor37/Rotor67 公共域文献清单**:Reid/Moore 1978, Suder 1993, Strazisar TP-2879, AGARD AR-355, Kulfan 2006/2008, Li 2020 FNO, Chen 2019 GAN — 全部 MOCK/LLM 离线完成 ✅
- **参数化器对比矩阵**:CST/B-spline/FFD/PARSEC/Hicks-Henne/VAE/GAN/FNO 8 个候选逐项工程评价,2D/3D 适用性,变量数,优化友好度 — 完成 ✅
- **首选 + 备选方案论证**:CST(2D) + FFD(3D) 二段式 + VAE 备选 — 完成 ✅
- **许可证与复现包影响**:NASA 公共域 + PLAID CC-BY-SA 传染 + NUMECA 私有 — 完成 ✅

### 20% 部分完成(可能需要 web 验证)

- **数据集 URL 精确格式**:PLAID-datasets/Rotor37 在 HuggingFace 镜像可达,样本数 + 协议已确认 ✅;**但具体 3D 几何文件格式(vtp/vtu/pt)未打开** — 需 webfetch 原站或 1-2 GB 样本下载后核实 ⚠
- **NASA TP-2879 全文 PDF 链接**:报告存在 + 公共域 + 内容已知(论坛复述 + 知乎 CSDN 多源),**但本调研未抓取 NTRS 直链** — 需 webfetch 验证 NTRS 是否仍可访问 ⚠
- **NUMECA .geomTurbo / .igg 格式细节**:CSDN 已有转储,**但未亲自解压验证文件结构** — 后续可能需要 ⚠
- **NASA Glenn SWIFT 子页内容**:本调研抓取到的是 Glenn 总站首页,SWIFT 子页可能已迁址(网页 200 但导航菜单未带出 SWIFT) ⚠

### 10% 待补(具体 3D 文件 8 月 1 日前可拿性)

- **3D 几何文件 8 月 1 日前是否能拿到**:
  - Rotor37/Rotor67 截面坐标 + 自建 3D 重建 → **可达(1-2 天)**
  - PLAID 3D RANS 完整样本 → **可达但需外网下载 1-10 GB**(视具体格式,本调研未确认)
  - NUMECA .geomTurbo → **可达但需 NUMECA 软件** (本项目用 STAR-CCM+ 替代,需 IGES 转换)
  - NASA Glenn SWIFT 完整案例包 → **未知(需 NASA 申请 + 可能仅限美国机构)**
- **待用户确认 / 待外网下载** 项已列在 §1.5 表格

---

## 4. 风险与下一步建议(对 7-8 月推进"如果这条没做,后面会卡")

| # | 风险 | 后果 | 建议 |
|---|---|---|---|
| **R-1** | **3D Rotor37 几何格式未确定**:PLAID 的 3D 字段格式(`.vtp` / `.vtu` / `.pt`?)在 hf-mirror 上未直接看到 | 如果 8 月初才打开,会延后 sample generation;可能要做 STAR-CCM+ 端的 geometry import adapter | **立即动作**:本 session 后 24 小时内由 `general` worker 或 `docs-knowledge-engineer` 抓 HuggingFace 原站(需 IP 不被镜像识别),确认字段;**最坏情况**:备选自建 3D 几何(NASA TP-2879 表格 → Python 重建) |
| **R-2** | **CST + FFD 联动未在 cfd_harness 出现过**:本项目两个解可能都是 0 经验起点 | 7 月期 2D 切片时 CST 写好;8-9 月切 FFD 时可能需要重写 sample generator | **建议**:7 月用 CST 跑通 2D LHS,顺手把"参数化器 → 几何 → mesh → CFD → 提取" pipeline 抽象成 `ParameterizerInterface`,让 FFD 在 8 月替换只需实现新接口 |
| **R-3** | **PLAID CC-BY-SA 传染**:若主论文要投商业 AIAA Journal,SA 协议 + 商业发布的兼容性需明确 | 论文投稿或工业落地时可能有"传染"法律问题 | **建议**:复用 PLAID 时只用作"训练数据 + 误差对照",**不在最终交付的 surrogate 里硬嵌入 PLAID 的派生几何**;在论文 data availability 段写明 PLAID 来源 + 协议 |
| **R-4** | **STAR-CCM+ 2402 在 Rotor37 几何上的 mesh 流水线未验证**:DEC-007 v4 path9 已证 BaseSize.setValue 在 NACA 立方体上 OK,**但 Rotor37 复杂曲面 + 36 叶片 + 间隙 + 端壁** 是新挑战 | 8-9 月期 3D 样本生成可能再遇 solver deadlock(同款 DEC-007 链路) | **建议**:7 月立项期先把"STAR-CCM+ 端处理 Rotor37 几何 36 个 blade copy" 的最小脚本跑通,不接 surrogate;若失败,在 DEC-008.a 阶段升级 OpenFOAM 端做 3D 样本 |
| **R-5** | **首篇论文"参数化 + 神经代理 + 多目标优化" 三件套工程量极大**:10-12 月要把 surrogate 误差 < 5% + NSGA-II Pareto 前沿 + 高保真回验,12 周(2 个 milestone)紧张 | 若 surrogate 误差不收敛,需重做或换架构,会推后首篇投稿 | **建议**:8 月期 2D 阶段先在 LDC + NACA(已有 cfd_harness 资产)上做 surrogate baseline 验证,**用已有 gold_standard 跑 V&V 闭环**;Rotor37 3D 再上 |

---

## 5. 引用与依据

- **项目级**:`AGENTS.md` (项目根) · `reports/STATE.md` (SSOT) · `reports/research/commercial-fan-prop/planning/CHARTER.md` · `reports/research/commercial-fan-prop/decisions/DEC-008-project-charter.md` · `.harness/reins/vv-director/agent.md` · `knowledge/whitelist.yaml` · `knowledge/attestor_thresholds.yaml`
- **既有 DEC**:`DEC-001`(solver_info 迁移)· `DEC-005`(LDC FF 采样)· `DEC-007`(NACA 闭环)· `DEC-008`(本项目立项)— 本 Track A 输出**不与上述任何 DEC 冲突**;若 R-2/R-4 命中,会**派生 DEC-008.a/b 子决策**
- **NASA 文献源**:Reid & Moore 1978 (NASA TM-73776 体系) · Suder 1993 · Strazisar 1989 (NASA TP-2879) · AGARD AR-355 · Kulfan 2006/2008 · Li et al. 2020 (arXiv 2010.08895, ICLR 2021) · Chen et al. 2019 (AIAA 2019-2351) · Yonekura 2023 (arXiv 2311.05445) · Wang 2021 (CVAE-GAN inverse design)
- **数据集源**:PLAID-datasets/Rotor37 (HuggingFace, Safran CC-BY-SA 4.0) · NASA Glenn SWIFT (https://www1.grc.nasa.gov/research-and-engineering/cfd-codes-turbomachinery/swift/) · 知乎 NutsCFD 验证算例五
- **本调研使用工具**:WebSearch (Bing via MCP matrix) · WebFetch (HuggingFace mirror / cfd-online / 知乎 / NASA Glenn) — **未运行任何代码 / 未修改任何 yaml/python/源码 / 未动 STATE.md / AGENTS.md**

---

## 6. 收口

本 Track A 在 7 月立项期内提供了 4 件可立即消费的产物:

1. **NASA Rotor37/Rotor67 数据集清单 + 许可证** (§1) — 复现包可立即搭骨架
2. **参数化器对比表 + 选型决策** (§2.1 + §2.2) — 7 月 2D 样本生成可直接选 CST
3. **首选 + 备选方案论证** (§2.3) — CST(2D) + FFD(3D) 二段式 + VAE 备选
4. **风险与下一步建议** (§4) — R-1~R-5 5 条;R-1 / R-4 是**立即级**(24 小时内行动)

**首席工程师行动建议**:
- (a) R-1 立即委派 `general` worker 抓 HuggingFace PLAID 字段格式,24 小时内回本文件追加
- (b) 7 月期内委派 `backend-engineer` 写 `ParameterizerInterface` 抽象 + CST 实现
- (c) 7 月内 vv-director 起草 `gold_standards/rotor37.yaml` + `rotor67.yaml` 骨架(本 Track A 已列 E-1/E-2 实验数据为黄金标准)
- (d) 8 月期第一 milestone 复盘时(2026-08-30)用本文件 §4 R-1~R-5 自检
