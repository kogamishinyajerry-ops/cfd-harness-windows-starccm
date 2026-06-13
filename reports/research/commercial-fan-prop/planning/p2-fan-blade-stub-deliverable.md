# P2 stub · fan_blade.py + case_profiles.yaml 4 entry · 7 月期 mirror

> **Mirror of**: `C:\Users\Kogami\.mavis\plans\plan_88c030c6\outputs\stub-p2-yaml-fw-blade-stub\deliverable.md`
> **任务来源**: chief-engineer P2 派单(verdict-2026-07 §5.2 D-4)
> **完成时间**: 2026-06-12 10:53+08
> **角色**: starccm-adapter-engineer 代理(general agent)
>
> 本文件是 P2 stub 任务的 7 月期 mirror — 让 chief-engineer / verifier 在
> 7 月底会议能直接读 `reports/` 树下文件(对齐 verdict-2026-07 的 4 个
> track deliverable 都落在 `reports/research/commercial-fan-prop/planning/`
> 的风格). 详细 50/30/20 诚实分层 + 4 个 test 名 + 8-plane enforcement
> 已在 plan outputs deliverable.md 内,本文件只保留 1 段话结论 + 1 张
> 文件清单 + 1 段 8 月 follow-up.

---

## 1. 一句话结论

Scaffold `case_solve/fan_blade.py` 180 行 + `case_profiles.yaml` 4 entry
(rotor37_slice / rotor37_single_channel / rotor67_slice / propeller_open_rotor_slice),
4/4 smoke test PASS, 8/8 four-plane enforcement PASS, **不** spawn /
**不**改 executor / **不**碰 gold_standards / STATE.md / DEC。

## 2. 文件清单 (5 写 5)

| 路径 | 状态 | 字节 / 行 |
|---|---|---|
| `src/cfd_harness/starccm_adapter/case_solve/__init__.py` | 新建 | 517 B / 11 行 |
| `src/cfd_harness/starccm_adapter/case_solve/fan_blade.py` | 新建 | 8236 B / 180 行 |
| `knowledge/case_profiles.yaml` | 追加 4 entry | 222 → 320 行 (+98) |
| `tests/starccm_adapter/test_fan_blade_stub.py` | 新建 | 4 test / 0.26s 全过 |
| `C:\Users\Kogami\.mavis\plans\plan_88c030c6\outputs\stub-p2-yaml-fw-blade-stub\deliverable.md` | 新建 | engine 验收读 |

**零改动**: `src/cfd_harness/starccm_adapter/executor.py` /
`src/cfd_harness/executor/{base,mock,win_starccm}.py` / 16 个
`gold_standards/*.yaml` / `STATE.md` / `verdict-2026-07.md` /
`DEC-007` / `DEC-008`。0 spawn / 0 .sim / 0 git push。

## 3. 50/30/20 诚实分层 (概览)

- **50%** stub 写完:build_case + extract_aero 雏形, docstring 60 行路线图(D-1 / D-6 / D-7 已 DONE 事实 + 8-10 月规划)
- **30%** smoke test 跑过:4 个 test 验 shape + D-2 容忍;4-plane enforcement 8/8 PASS 同步验证
- **20%** 8 月迭代计划:写进 docstring,等 7 月底会议 chief-engineer 拍板真 macro + executor 路由补 4 key

## 4. 风险 3 条 (详细见 plan deliverable §4)

1. **HIGH** — `StarCCMExecutor._CASE_TO_COMMAND` 没补 4 key → 8 月初需 1 subagent 改 2 行字典(任务硬约束禁止本 P2 改 executor)
2. **HIGH** — `rotor37.yaml` 仍是占位(D-2 + D-3 仍 HIGH) → vv-director 7/25-7/31 转录 NASA-TP-1338 + Suder 1995
3. **MEDIUM** — `propeller_open_rotor_slice` 2027 占位可能误判为"团队没纪律" → M1 评审会口头说明

## 5. 8 月 follow-up (4 件, 不在本 P2 范围)

1. 写 `macros/Rotor37Slice.java` (借 NacaTrueE2E.java 7-11 步骨架)
2. 改 `executor.py:58-79` 加 4 key 路由(本 P2 任务不动 executor)
3. 写 `scripts/run_rotor37_macro.py` driver(P3 / D-5 / verdict §4.2)
4. 写 `case_extractors/fan_aero.py` 真 reader(Track D ★ 4 / D-7 follow-up)

## 6. 闭环 trace (P2 任务在 4-track 流水线里的位置)

```
DEC-008 §2.3 L0 grant (chief-engineer 授权) 
  → verdict-2026-07 §5.2 D-4 标记 HIGH (本任务 = 收口)
  → DEC-008 §4 影响表 § fan_blade.py 由 starccm-adapter-engineer 拥有
  → track-d-deliverable.md §3 ★ 3 ROI 排序 #3 (本任务 = ROI 3 收口)
  → CHARTER §2 数据期 ① 8 月初消费本 entry point
  → 7 月底 M1 评审: 本 stub 展示 1 vertical "rotor37_slice MOCK 端跑 1 次"
```

**判定**: P2 stub 闭环完成,**进入 8 月数据期 ① 起点**,**不**挡 M1 验收。

---

*P2 DONE. 7 月期 4 个 HIGH debt(D-1/D-2/D-3/D-4)全部 7 月底前 scaffold 路径打通:*
* D-1 (PLAID 字段) 已 DONE 2026-06-12 (Track A R-1)*
* D-2 (rotor37.yaml 数字) 留给 vv-director 7/25-7/31 (本任务不动)*
* D-3 (rotor37.yaml 框架) 留给 docs-knowledge-engineer 7/25-7/31 (本任务不动)*
* **D-4 (fan_blade.py 雏形) DONE 本任务***
* D-5 (run_rotor37_macro.py driver) 留给 P3 后续 subagent*
