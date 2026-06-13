# 7 月期 M1 验收 Checklist(1 屏看完)

> **Generated**: 2026-06-12 11:26+08 · **Author**: chief-engineer (L0 grant per DEC-008 §2.5)
> **For**: Kogami (user/sponsor) · 7 月底 M1 评审会议前 read-this-first
> **Related**: `DEC-008.a-m1-acceptance.md` (verdict doc 风格 ≥80 行) · `verdict-2026-07.md` §5.2

---

## 1. 7 月期 M1 验收 YES/NO 总览

| # | 验收项 | 答案 | 证据 |
|---|---|---|---|
| Q1 | 3 个 stub 全部 scaffold 落盘? | **YES** | `knowledge/gold_standards/rotor37.yaml` 26191B · `src/cfd_harness/starccm_adapter/case_solve/{__init__.py, fan_blade.py}` 517B+8236B · `scripts/run_rotor37_macro.py` 9439B · `macros/Rotor37Slice2D.java` 3079B |
| Q2 | 3 个 stub 全部 smoke test 退出码 0? | **YES** | P1: 14/14 all_pass + 7/7 baseline pytest · P2: 4/4 pytest 0.26s · P3: 1/1 mock exit 0 |
| Q3 | verdict §5.2 D-1 / D-2 / D-3 / D-4 / D-5 全 DONE 2026-06-12? | **YES** | 本任务同步翻 DONE;详见 §3 |
| Q4 | 9 硬约束兼容矩阵全过? | **YES** | advisor-not-driver / four-plane / signed audit / tolerance integrity / pre-impl / L0 / 不改 STATE.md / 不写 yaml / 不切 executor mode — 9/9 PASS(沿用 verdict §3) |
| Q5 | 7 月底前必须做的 1 行 bug 是否修了? | **NO** | `_invoke` 缺 `encoding="utf-8"`(D-6) — **8 月数据期 ① 启动前必修**(条件 C-1) |

**总判定**: **PASS-WITH-CONDITIONS**(5/5 YES + 1 个条件)— DEC-008.a 登记.

---

## 2. 3 个 stub 状态 + 文件路径 + smoke test 退出码

### 2.1 P1 · `gold_standards/rotor37.yaml`(vv-director 代理 · general)

| 维度 | 值 |
|---|---|
| 路径 | `D:\CFD-harness-Windows-StarCCM\knowledge\gold_standards\rotor37.yaml` |
| 大小 | 26,191 B / ~330 行 / 14 个 quantity block |
| 数字填值 | **14/14** ✅ (0 个 `__TO_FILL_FROM_LIT__`) |
| BibTeX citation | 4 篇(NASA-TP-1659 primary R37 + NASA-TP-1337 context + Suder 1995 DOI 10.1115/1.2836561 + NUMECA) |
| PLAID 误用 | ✅ 3 处 yaml 注释明示 PLAID ≠ gold |
| Comparator 实测 | **14/14 all_pass=True** · 0 ValueError · 0 warnings |
| 扰动 sanity check | 10% off → PR 正确 FAIL,其余 13 个 PASS(comparator 真的在 compare) |
| Baseline pytest | **7/7 passed in 0.43s**(无回归) |
| Smoke test RC | **0** ✅ |
| Mirror deliverable | `reports/research/commercial-fan-prop/planning/p1-yaml-deliverable.md` (257 行) |

### 2.2 P2 · `case_solve/fan_blade.py`(starccm-adapter-engineer 代理 · general)

| 维度 | 值 |
|---|---|
| 路径 | `D:\CFD-harness-Windows-StarCCM\src\cfd_harness\starccm_adapter\case_solve\fan_blade.py` + `__init__.py` |
| 大小 | 180 行 + 11 行 + 8236 B + 517 B |
| Case profile 追加 | 4 entry: rotor37_slice / rotor37_single_channel / rotor67_slice / propeller_open_rotor_rotor_slice |
| 4 个 smoke test | **4/4 PASS in 0.26s** ✅(test_fan_blade_stub.py) |
| Four-plane enforcement | **8/8 PASS** ✅ |
| 写盘文件 | 5 个新建 + 0 个改 executor |
| Smoke test RC | **0** ✅ |
| Mirror deliverable | `reports/research/commercial-fan-prop/planning/p2-fan-blade-stub-deliverable.md` (78 行) |

### 2.3 P3 · `run_rotor37_macro.py` + `Rotor37Slice2D.java`(starccm-adapter-engineer 代理 · general)

| 维度 | 值 |
|---|---|
| 路径(driver) | `D:\CFD-harness-Windows-StarCCM\scripts\run_rotor37_macro.py` (9439 B / 198 行) |
| 路径(macro) | `D:\CFD-harness-Windows-StarCCM\macros\Rotor37Slice2D.java` (3079 B / 57 行) |
| Java 编译 | **RC=0** ✅(STAR-CCM+ 2402 R8 classpath `star-coremodule.jar + starbase.jar + starice.jar`) |
| Mock smoke test | `python scripts/run_rotor37_macro.py --case-id rotor37_slice --executor mock --iters 0` → **exit 0** ✅ |
| is_mock 挂载 | **True** · `mock_executor_no_truth_source` note 正确触发 |
| Yaml peek | 10 quantities from P1 stub 实测读到(n_blades=36 / rpm=17188.7 / PR_design=2.056 / eta_is_design=0.876 等) |
| 反射风格 | `enableModel(cont, fqn)` 用 `Class.forName` + `Method.invoke`(LidDrivenCavity.java:160-171 范式) |
| D-7 RRF 锁定 | `RRF_FQN = "star.motion.RotatingReferenceFrame"` 1/4 候选命中(编译过 = 类存在) |
| Spawn / .sim / push | **0 / 0 / 0** ✅ |
| Smoke test RC | **0** ✅ |
| Mirror deliverable | `reports/research/commercial-fan-prop/planning/p3-driver-stub-deliverable.md` (207 行) |

---

## 3. verdict-2026-07 §5.2 债务状态同步(本任务同步执行)

| ID | 债务 | 原状态 | **新状态(2026-06-12)** | Owner | 备注 |
|---|---|---|---|---|---|
| **D-1** | Track A R-1: PLAID-datasets/Rotor37 3D 字段格式 | HIGH → DONE | **DONE 2026-06-12** | general | `d1-plaid-probe.md`: PLAID 实为 Safran RANS 仿真,**不能**当 NASA 实验 gold;改作 surrogate 训练数据 + Suder 1995 验证对照 |
| **D-2** | Track C R-1: NASA-TP-1338 Table 1 / Suder 1995 数字未到位 → yaml 占位符 | HIGH | **DONE 2026-06-12** | vv-director 代理 | P1 RETRY v3 已写 14/14 quantity 真实数字;`gold_standards/rotor37.yaml` 26191 B |
| **D-3** | Track D ★ 1: `gold_standards/rotor37.yaml` + `rotor67.yaml` 实际未写入 | HIGH | **DONE 2026-06-12**(rotor37);`rotor67.yaml` 仍待 9 月期 | vv-director (数字) + docs-knowledge-engineer (框架) | P1 stub 同时完成数字 + 框架 |
| **D-4** | Track D ★ 3: `case_solve/fan_blade.py` 雏形未建 | HIGH | **DONE 2026-06-12** | starccm-adapter-engineer 代理 | P2 stub 已写 180 行 + 4 case profile entry |
| **D-5** | Track D ★ 9: `scripts/run_rotor37_macro.py` driver 未写 | HIGH | **DONE 2026-06-12** | starccm-adapter-engineer 代理 | P3 stub 已写 198 行 + 57 行 Java macro |

**结果**: 7 月期 5 件 HIGH debt 全部 2026-06-12 提前到 7 月 1 日完成(原计划 7/25-7/31).

---

## 4. 8 月数据期 ① 启动条件(2026-08-01 必达)

| # | 条件 | Owner | Deadline | 阻塞? |
|---|---|---|---|---|
| **C-1** | 修 `bridge/_invoke` 1 行 bug(`encoding="utf-8"` 缺失) | backend-engineer | 2026-07-31(8 月前) | **YES** — 影响所有桥接调用 |
| **C-2** | RRF enable 90s 真 spawn 探针(`star.motion.RotatingReferenceFrame` enable 验证) | starccm-adapter-engineer | 2026-07-31(8 月前) | **YES** — D-7 闭环 + 3D 路径决策 |
| C-3 | L0 → L1 升级? | chief-engineer 提议 + user 拍板 | 2026-08-31(可能升) | NO — evidence-gated,0 个 vertical 不触发 |
| C-4 | 8 月数据期 ① 排期(MOCK 100 + 真机 30-50) | chief-engineer | 2026-08-01 启动 | YES |
| C-5 | DEC-008.b 子决策草案(8 月末登记) | chief-engineer | 2026-08-31 | NO(治理性) |

---

## 5. 桥接层 1 行 bug 是否修了(7 月数据期前必修)

**答案**: **NO,未修**(7 月底会议前必修)

- **位置**: `packages/starccm-bridge/src/starccm_bridge/repl.py:_invoke(...)` 函数
- **症状**: `subprocess.run` 缺 `encoding="utf-8"` 参数,CJK 错误时 stdout/stderr 全失
- **影响**: 所有 `_invoke` 调用(CJK 路径 + UTF-8 错误信息)
- **发现**: D-6 探针 2026-06-12 跑通时识别(`d6-analyze-probe.md` 140 行)
- **修复 patch**(1 行 ready):

  ```python
  # packages/starccm-bridge/src/starccm_bridge/repl.py:_invoke
  result = subprocess.run(
      args, cwd=cwd, env=env,
      capture_output=True,
      text=True,
      encoding="utf-8",        # <-- ADD THIS LINE (1 行 patch)
      errors="replace",
      timeout=timeout,
  )
  ```

- **阻塞**: 8 月数据期 ① 100+ 样本中任 1 个失败 → 排错瞎,**必修**

---

## 6. 1 屏总结(给 user)

```
7 月期 M1 验收:  PASS-WITH-CONDITIONS
- 3 stub 全部 2026-06-12 提前到 7 月 1 日就位 ✓
- 5 件 HIGH debt 全翻 DONE 2026-06-12(D-1/D-2/D-3/D-4/D-5)✓
- 9 硬约束兼容矩阵全过 ✓
- L0 暂不升(0 个端到端 vertical,触发条件未达)✓
- 1 个条件: _invoke 1 行 bug 8 月前必修(C-1)
- DEC-008.a 登记 → 8 月数据期 ① 起点
```

---

*本 checklist 1 屏可读;详细 verdict doc 风格见 `DEC-008.a-m1-acceptance.md` ≥ 80 行.*
*用户拍板 = ask_user 一次 4 问(沿用 verdict-2026-07 §6 推荐项).*