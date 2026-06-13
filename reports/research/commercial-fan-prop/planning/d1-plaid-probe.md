# D-1 · PLAID Rotor37 3D 字段格式侦察报告

> 任务:PLAID-datasets/Rotor37 在 HuggingFace 镜像的 3D 几何字段格式确认
> 执行者:general worker · 2026-06-12 (Asia/Shanghai)
> 写入路径:本文件 (D-1 唯一允许写盘路径)
> 引用:`verdict-2026-07.md` §5.2 D-1 · `track-a-deliverable.md` §1.5 R-1

---

## 1. TL;DR

- **格式不是 `.vtp` / `.vtu` / `.pt`**,而是 **PLAID datamodel**(CGNS-based mesh + Python pickle 序列化) — HF 上以单 parquet 快照分发,整包 4.05 GB / 解压 3.3 GB
- **3D 字段 schema 100% 确认**(直接抄自 HF dataset card + Zenodo README)
- **许可证 = CC-BY-SA 4.0**(已确认,Safran 持有) — **SA 传染法律风险不变**
- **关键发现**:PLAID = Safran RANS 仿真,**不是 NASA 实验 gold**;`Compression_ratio` / `Efficiency` 是同工况下的 CFD 输出,**不能**替代 NASA-TP-1338 Table 1 / Suder 1995 实验值填入 `reference_values`(违反 AGENTS.md "Crew directives" 第 4 条)
- **结论**:track-c 的 `rotor37.yaml` 草稿设计点 scalar 路径**不受影响**,3 个 `__TO_FILL_FROM_LIT__` 仍需 vv-director 转录 NASA 文献;PLAID 改作 **surrogate 训练数据源 + 误差对照**

---

## 2. 抓取过程

| # | URL | 抓取时间 | 结果 | 失败原因 |
|---|---|---|---|---|
| 1 | `https://huggingface.co/datasets/PLAID-datasets/Rotor37` | 08:36 (UTC+8) | **PASS** — README 完整,in/out scalars + in/out fields + mesh 路径全在,样本数 1200 / 4.05 GB | n/a |
| 2 | `https://huggingface.co/datasets/PLAID-datasets/Rotor37/tree/main` | 08:37 | **PASS** — 确认 4.05 GB / 单 `data/` 目录 + `README.md` + `.gitattributes` | n/a |
| 3 | `https://hf-mirror.com/datasets/PLAID-datasets/Rotor37` | 08:36 | **REDIRECT** | 跳到主站 |
| 4 | `https://plaid-lib.readthedocs.io/en/latest/` | 08:40 | **PASS** — PLAID 库 overview,CGNS + Zarr + HF Datasets 三种后端 | n/a |
| 5 | `https://zenodo.org/records/14840190` | 08:41 | **PASS** — DOI 10.5281/zenodo.14840190,v2 / 2025-02-09 / 3.3 GB tar.gz / md5 38b569baa992b08f434299c1737f68c5 | n/a |
| 6 | `https://arxiv.org/abs/2305.12871` | 08:39 | **PASS** — MMGP 论文 v2, Casenave/Staber/Roynard 2023 | n/a |
| 7 | `https://github.com/PLAID-datasets/plaid` | 08:36 | **404** | 旧镜像组织名,真仓库在 `PLAID-lib/plaid` |

**镜像情况**:
- **HF 原站** + **hf-mirror 镜像**(中国大陆)→ 同一 dataset(redirect 一致)
- **Zenodo 镜像**:HF card 显式标 "Repository: Zenodo",DOI 10.5281/zenodo.14840190,3.3 GB tar.gz 备用源
- **GitHub 仓库**:PLAID 库源码在 `PLAID-lib/plaid` (SafranTech,Apache-style);无 dataset 单独 GitHub 仓库

---

## 3. 字段 schema(直接抄自 HF dataset_info + Zenodo README)

**样本结构**: 单 split `all_samples` = 1200 example,4.05 GB 下载,task: `regression`;train_8/16/32/64/125/250/500/1000 嵌套(测试集 ID 1000-1199 段无 output);mesh = CGNS 节点+单元,序列化 PLAID 0.1(pickle),HF 上以 parquet 快照分发,`data/all_samples-*`,特征名 `name: sample, dtype: binary`。

| 类别 | 字段名 | 类型 | 单位/范围 | 备注 |
|---|---|---|---|---|
| in_mesh | `/Base_2_3/Zone` | CGNS mesh | 3D unstructured | `in_meshes_names` 唯一;无 `out_meshes` |
| in_scalars (×2) | `Omega` | scalar | rpm(推断) | 转速;NASA Rotor37 设计 17188.7 rpm |
| in_scalars (×2) | `P` | scalar | Pa(推断) | 入口总压 |
| in_fields (×3) | `NormalsX / NormalsY / NormalsZ` | field on mesh | 节点上无量纲 | 表面法向 — 因几何随样本变,作为 GNN input feature |
| out_scalars (×3) | `Massflow` | scalar | kg/s | 质量流量 |
| out_scalars (×3) | `Compression_ratio` | scalar | 无量纲 | **即 track-c 草稿的 `total_pressure_ratio_design`**(命名差异) |
| out_scalars (×3) | `Efficiency` | scalar | 无量纲 | **即 track-c 草稿的 `isentropic_efficiency_design`** |
| out_fields (×3) | `Density` / `Pressure` / `Temperature` | field on mesh | kg/m³ / Pa / K 节点上全场 | GNN 训练 target |
| in/out_timeseries | `[]` | n/a | n/a | 无瞬态,稳态 RANS |

**加载样例**(HF card 复制):
```python
from datasets import load_dataset
from plaid.bridges.huggingface_bridge import huggingface_dataset_to_plaid
hf_dataset = load_dataset("PLAID-datasets/Rotor37", split="all_samples")
dataset, problem = huggingface_dataset_to_plaid(hf_dataset, processes_number=4)
sample = dataset[problem.get_split('train_1000')[0]]
sample.get_field('Pressure'); sample.get_scalar('Compression_ratio')
```

---

## 4. 与 track-c `rotor37.yaml` 草稿的 gap 分析

| track-c 草稿字段 | PLAID 字段 | gap | 处置 |
|---|---|---|---|
| `total_pressure_ratio_design` (NASA-TP-1338 实验,`__TO_FILL__`) | `Compression_ratio` (CFD 输出) | **同名不同源**:track-c = NASA 1978 实验设计点;PLAID = 同工况不同几何扰动下的 Safran RANS 仿真 | **PLAID 不能当 gold 填**;gold 必须从 NASA-TP-1338 Table 1 / Suder 1995 Table 1 转录 |
| `isentropic_efficiency_design` (实验值) | `Efficiency` (CFD 输出) | 同上 | 同上 |
| `mass_flow_choke` (20.7 kg/s) | `Massflow` (CFD 输出) | 同上 | 同上;但 PLAID 1000 个 `Massflow` 可作 *Suder 1995 验证对照的 surrogate 输出* |
| `mesh_info.cells = 1,000,000` (Suder 1995 结构网格) | PLAID CGNS 节点数未在 README 暴露 | 拓扑差异:PLAID 未结构化 CGNS,Suder 用 O-H/H-I 结构网格 | 2 套不冲突:gold 走 Suder 结构,PLAID 走 CGNS |
| `solver_info` 写 STAR-CCM+ Steady Coupled | PLAID 由 Safran 自家求解器(论文未公开) | **solver 不一致** | gold yaml 写 STAR-CCM+ 不变;PLAID 只作"训练数据 + 误差对照",**不在 surrogate 里硬嵌入**(原 R-3) |
| `case_info.rotor.blades: 36` (全环) | PLAID mesh 是单叶片通道(1/36 周期切片) | **单通道 vs 全环** | yaml 保留 36(指实验/全环);surrogate 训练时声明 `single_passage: True` |
| (无) | `NormalsX/Y/Z` (in_fields) | PLAID 多出 3 个法向场 | surrogate 端用作 GNN input feature,gold yaml 不出现 |
| (无) | `Density / Pressure / Temperature` (out_fields,全 3D 场) | PLAID 提供全场解 | surrogate 端用作 GNN target field;**当前 `gold_standard_comparator` 走 scalar `value` 路径,无法直接吃 field** — 与 track-c §3 B1 `sweep` 缺口同源 |

**核心结论**:
- PLAID = Safran 仿真数据,**不是 NASA 实验 gold**;`Compression_ratio` / `Efficiency` / `Massflow` **不能**进 `reference_values`
- track-c 草稿 3 个 `__TO_FILL_FROM_LIT__` 仍需 vv-director 转录 NASA-TP-1338 / Suder 1995,**PLAID 不替代**
- PLAID 的 field outputs 走 track-c §3 B `sweep` / `multi_objective` schema 扩展才能被 comparator 吃 — 进一步确认 B1-B3 缺口是**真阻塞**

---

## 5. 诚实分层 50 / 30 / 20

**50% LLM-offline 确认**(README 公开内容):
- URL / 许可证 / 引用格式 / 样本数(1200) / 单 split 结构
- in/out 字段名 + 类型 + 维度类别(README `dataset_info` YAML 直接给出)
- PLAID 库身份 + SafranTech 归属 + Apache-style license
- 与 track-c 草稿的字段命名差异分析(semantic gap)

**30% 需下载/真跑验证**(不下载只能推断):
- 单 sample 节点数(README 未给) — 需 `load_dataset` 后 `sample.get_nodes().shape`
- `Omega` 单位(rpm 还是 rad/s)— NASA Rotor37 设计 17188.7 rpm,可推断 rpm,但 PLAID 是否归一化未明
- `P` 单位(总压 Pa 还是无量纲)— 同上,需论文/代码核
- `Compression_ratio` 是 total-to-total 还是 total-to-static — 论文 §4.1 应有
- mesh 实际尺寸 / 节点密度 / wall y+ — 需 `Muscat` 转换后看

**20% 外部依赖/未做**:
- **未下载 4.05 GB 数据**(耗时 + 磁盘,超 2h 任务预算)
- **未跑 `load_dataset` 验真**(依赖 §30% 验证)
- **PLAID 库 v0.1 vs 最新版 API 兼容性**(MMGP 论文用 v0.1,`bridges/huggingface_bridge` API 稳定性未验证)

---

## 6. 风险(3 条,各 1 行)

1. **PLAID 仿真 ≠ NASA 实验 gold**;若误把 `Compression_ratio` / `Efficiency` 当 gold 填 `reference_values`,触发 AGENTS.md "Crew directives" 第 4 条红线 — **owner: vv-director**
2. **CC-BY-SA 4.0 传染**:复现包 + 派生 surrogate 一旦发布,下游衍生作品必须同协议;8 月论文草稿期前需 user 拍板商业发布兼容性 — **owner: chief-engineer + user**
3. **PLAID 4.05 GB + `pyplaid` 库依赖**:本机磁盘 + Python 依赖未到位,真实消费 1 sample 需 30+ 分钟 pip install + 4 GB 下载 — **owner: backend-engineer**(8 月数据期 ① 起点)

---

## 7. 引用格式(直接给 vv-director / docs-knowledge-engineer 抄)

```bibtex
@misc{casenave2023mmgp,
  title  = {MMGP: a Mesh Morphing Gaussian Process-based machine learning method
            for regression of physical problems under non-parameterized geometrical variability},
  author = {Casenave, Fabien and Staber, Brian and Roynard, Xavier},
  year   = {2023},
  month  = oct,
  eprint = {2305.12871},
  archivePrefix = {arXiv},
  primaryClass  = {cs.LG},
  doi    = {10.48550/arXiv.2305.12871},
  note   = {v2, 22 Oct 2023; Rotor37 dataset described in §4.1 and Appendix A.1}
}
```

**数据集本体引用**(HF card 显式声明 Owner: Safran, License: CC-BY-SA 4.0):
```
PLAID-datasets/Rotor37: 3D CFD RANS simulations of the NASA Rotor 37 compressor blade.
Hugging Face, 2024-. Owner: Safran. License: CC-BY-SA 4.0.
URL: https://huggingface.co/datasets/PLAID-datasets/Rotor37
DOI (Zenodo mirror): 10.5281/zenodo.14840190
```

---

**Status**: DONE · 1h 抓取 + 0h 下载 · schema 100% 确认 · gap 5 行定位 · 诚实分层 50/30/20 · 风险 3 条带 owner
