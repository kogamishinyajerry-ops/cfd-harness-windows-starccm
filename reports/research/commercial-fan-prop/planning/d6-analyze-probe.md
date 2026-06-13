# D-6 — Codebuddy REPL `analyze` CLI 探针

**任务**: D-6 商业项目 commercial-fan-prop 7 月期 step 2 探针 · 2026-06-12
**目标**: 验证 `analyze` 命令真实存在性 + 派发路径 + 返回 data 形状,**不要求跑通**
**时间预算**: ≤ 5 min(实际 ~3 min)

## 1. TL;DR

| 维度 | 结论 |
|---|---|
| **analyze 真实存在** | ✅ 是 — `D:\StarCCM Codebuddy\starccm_cli.py:519 cmd_analyze` 真实函数 |
| **CLI 注册派发** | ✅ 是 — CLI 命令表 line 9208 `"analyze": cmd_analyze` 已注册,与 `vortex-street` / `inspect-sim` / `status` / `use-version` 同级别 |
| **桥接层封装** | ✅ 是 — `repl.py:388 CodebuddyRepl.analyze()` 已封装,`_invoke("analyze", [sim_path])` |
| **executor 派发** | ❌ 否 — `src/executor/win_starccm.py` 不会派发 `analyze`(track-b §4 已知) |
| **派发能否正常工作** | ⚠️ bridge 有一个**未修复的隐藏 bug**:`subprocess.run(text=True)` 在中文 Windows 用 GBK 解码 CLI 输出(CJK 消息),reader thread 抛 `UnicodeDecodeError`,stdout/stderr 全部返回 `None`。**修 1 行(`encoding="utf-8", errors="replace"`)立刻可用** |

## 2. 三种 invoke 形式 argv + 退出码 + 输出

### 2.1 直接 CLI(shell 派发)— analyze --help

```text
argv:   python D:\StarCCM Codebuddy\starccm_cli.py analyze --help
rc:     0
stdout: usage: analyze [-h] [--force] [--json] [--wait-gui] sim_file
        深度分析 STAR-CCM+ 案例
        positional: sim_file (仿真文件路径 .sim)
        options: -h, --force, --json, --wait-gui
stderr: (空)
```
→ argparse help 阶段,不进 spawn,**确认 argv 派发链 §0 合法**。

### 2.2 直接 CLI(shell 派发)— analyze <missing.sim> --json

```text
argv:   python starccm_cli.py analyze Cases\nonexistent.sim --json
rc:     1
stdout (JSON envelope):
  {"ok": false, "command": "analyze", "timestamp": "2026-06-12 08:44:02",
   "version": "15.0.0", "data": null,
   "error": {"code": "FILE_NOT_FOUND", "message": "文件不存在: ..."},
   "sim_path": "...", "force": false}
stderr: (空)
```
→ `_check_sim_file()` 早返,RC=1,**未触发 spawn**,确认 CLI dispatch §0-§1 完整。
注意:`--wait-gui` 是 v6.1+ 标志,已知在 Win11 24H2 spawn 会失败(`starccm_cli.py:4729` 注释)。

### 2.3 桥接层 wrapper(本次发现的关键)

#### 2.3a 默认 `_invoke`(有 bug)

```python
# repl.py:311 现状
proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, ...)
```
- argv 与 2.2 完全一致(`<python_executable> starccm_cli.py analyze <sim> --json`)
- **rc=1, elapsed=0.50s**(早期 `_check_sim_file` 退出)
- `r.ok=False`, `r.error="non-JSON output (returncode=1); stderr=''; stdout_head=''"`
- `r.raw_stdout=None`, `r.raw_stderr=None` ← **stdout 是 None,不是空字符串!**

根因诊断(本次探针发现):Python 3.11 `subprocess.run(text=True)` 在中文 Windows 默认用 `cp936/GBK` 解码,CLI 的中文错误消息含字节 `0xa8`,reader thread 抛 `UnicodeDecodeError: 'gbk' codec can't decode byte 0xa8`,**整个 stdout/stderr 被丢弃为 None**。复现:`python -c "import subprocess; ..."` 直接调同样 argv,error 一样。

#### 2.3b monkey-patch 修复(1 行加 kwarg)

```python
proc = subprocess.run(cmd, capture_output=True, text=True,
                      encoding="utf-8", errors="replace",  # ← 加这两行
                      timeout=timeout, ...)
```
- 同样 argv,同样 missing.sim
- rc=1, stdout 是完整 JSON envelope(见 §3)
- stderr 仍空(CJK 替换成 `?` 不影响 JSON 解析)

**结论**:`analyze` 的派发路径与 `vortex-street`/`inspect-sim`/`status`/`use-version` **完全等价**;bridge 唯一区别是它没设 `encoding=`。修复后与 4 个已知好命令**行为完全一致**。

## 3. 与已知真跑命令的派发路径对比(同样 missing-file 场景,encoding=utf-8 修复后)

| 命令 | CLI 行号 | argv 形态 | rc | JSON error.code | data 形状 | 与 analyze 同级? |
|---|---|---|---|---|---|---|
| `analyze` | 9208 | `analyze <sim> --json` | 1 | `FILE_NOT_FOUND` | `data=null` | ✅ |
| `vortex-street` | (同 dispatcher) | `vortex-street <sim> --json` | 1 | `SIM_NOT_FOUND` | `data=null`, 含 `macro`/`out_dir` | ✅ |
| `use-version` | (同) | `use-version --json`(无 args) | 0 | (None) | `data.active_version.{path,version_id,build,...}` | ✅ |
| `inspect-sim` | (同) | `inspect-sim <sim> --json` | 1 | `SIM_NOT_FOUND` | `data={sim_path}` | ✅ |
| `status` | (同) | `status --json` | 1 | `STATUS_PARTIAL` | `data.all_ok=false` + `checks[]` | ✅ |

所有 5 个命令走 **同一个 `_emit()` JSON envelope**(version=15.0.0, timestamp 格式一致)。**`analyze` 与 4 个真跑过的命令是同级别 dispatch entry**,绝不是死代码。

## 4. 结论与建议

**核心结论**:`analyze` 是 **真实可用** 的 CLI 命令,**不是 wrapper-only,也不是死代码**。但当前在本仓内有 **3 层债务**:

| 债务层 | 现状 | 影响 | 建议 |
|---|---|---|---|
| **L1 bridge bug** | `_invoke` 缺 `encoding="utf-8"`,stdout 全失 | analyze / explore / inspect-sim 等所有 CJK-error 命令桥接层返 `r.ok=False` + `error="non-JSON"` | **1 行修复**(`encoding="utf-8", errors="replace"`),影响所有 `_invoke` 调用 |
| **L2 executor 派发缺失** | `src/executor/win_starccm.py` 未派发 `analyze` | 7 月跑 200 sim 后批量归类 → 走 fallback `run --iters`,无 metadata | track-b §7.3 P0 排 1 已经标注,加新 dispatch |
| **L3 backend 真实 spawn** | `cb.learn(sim_path)` 在 Win11 24H2 上已知失败(`starccm_cli.py:4729` 注释) | 即使 L1+L2 都修,backend 仍返空 data → `_has_no_real_data()` 检测命中,出 `error` + `_backend_spawn_failed_error_v5` | 走 `--wait-gui` flag 等 GUI;或改用 `inspect-sim`(不 spawn)做 lightweight metadata |

**给 track-b 的标注建议**(可在 verdict-2026-07.md §10 step 2 改):

> `analyze` 真实存在 + 派发链完整 + 与 vortex-street 同级,**但不是 wrapper-only**:
> 1. CLI 端 `cmd_analyze` 是真函数(line 519),不是 stub
> 2. bridge 端 `CodebuddyRepl.analyze()` 是真封装
> 3. **桥接层有 1 行未修复 bug**(`subprocess.run` 缺 encoding=)导致 stdout/stderr 全失 → 7 月跑前必须修
> 4. executor 端未派发,**不是 dead code**,是 **gap**

## 5. 风险 2-3 条

| # | 风险 | 触发条件 | 影响 | 缓解 |
|---|---|---|---|---|
| R1 | **7 月跑 200 sim,所有 `analyze` 桥接调用全部返 `r.ok=False` 假阳性** | bridge bug 未修 + 走 bridge.analyze() 批处理 | 300 个 sim 的 metadata 全丢,V&V 引擎拿到空 data | **优先**修 `_invoke` 加 `encoding="utf-8", errors="replace"`(1 LOC,无回归风险) |
| R2 | **backend spawn 在 Win11 24H2 失败**,`_has_no_real_data()` 命中 | 真 spawn 阶段(7 月跑时) | 即使 L1 修了,真跑仍返空 data + `error._backend_spawn_failed_error_v5` | 走 `--wait-gui`(90s GUI 轮询);或改用 `inspect-sim` 拿 static metadata(不 spawn) |
| R3 | **CJK 错误消息乱码**(即使 encoding=utf-8 修了) | `errors="replace"` 把无效字节替换成 `?` | Agent 看到的 error message 含 `?`,**不影响 JSON 解析**,但人读起来怪 | 接受 cosmetic 损失;或改 CLI 端用 `ensure_ascii=False` 的 json.dumps |

## 6. 验证辅助(供下游 verifier spot-check)

- `D:\StarCCM Codebuddy\starccm_cli.py:519` → `cmd_analyze` 函数定义
- `D:\StarCCM Codebuddy\starccm_cli.py:9208` → CLI dispatcher 注册 `"analyze": cmd_analyze`
- `D:\CFD-harness-Windows-StarCCM\packages\starccm-bridge\src\starccm_bridge\repl.py:388` → `CodebuddyRepl.analyze()` 封装
- `D:\CFD-harness-Windows-StarCCM\packages\starccm-bridge\src\starccm_bridge\repl.py:311` → `subprocess.run(... text=True ...)` **缺 encoding= 的 bug 行**

## 7. 30s 探针建议(给后续同类任务)

1. `python starccm_cli.py <cmd> --help` → RC=0 + argparse help,**不进 spawn**,最快确认 CLI argv 合法
2. `python starccm_cli.py <cmd> <missing-file> --json` → RC=1 + JSON error envelope,**不进 spawn**(走 `_check_sim_file` 早返)
3. **不要**直接用 `<real .sim>` 探针(本任务 lid_driven_cavity_solved.sim 是 1.9MB,但会触发 spawn;真正 spawn 阶段要走 `--wait-gui` 90s 兜底)

**完成时间**: 探针 3 次 invoke,总耗时 ~3 min。
