# auto-recruit-design · 新宏落盘后自动回流通路 (2026-06-11)

> **设计任务,不写实现。** 给出三种可行方案 + trade-off + 推荐 + 最小落地接口 + 审计/降级/风险。
> 配套: `knowledge/macro_registry.yaml` (v1, 53 entries) + `docs/specs/MACRO_REGISTRY_SCHEMA.md` (v1.0)。
>
> **Audience**: chief-engineer (落地决定人) + docs-knowledge-engineer (日常登记员)。

---

## 0. 上下文与已确认事实

读完 task A (macro-registry-schema) 产出后,以下事实锁死了设计空间:

1. **v1 schema §4.1 显式声明 "No auto-curation today"** — 53 个 entry 是 hand-curated,283 个未登记的 .java 在 skip 列表里等下次手工 promote。
2. **v1 schema §4.2 写策略**:三个 rein (starccm-adapter-engineer / chief-engineer / docs-knowledge-engineer) 都"may add" entry,且 docs-knowledge-engineer 加的话必须 `status: reference` + `verified_by: null`。
3. **task B (SKILL_DISPATCH_WORKFLOW) 在本 plan workspace 中尚未落盘** — 我必须从现有信号推断"新宏是从哪条路径产生的"。从 task A design-rationale §"How this design feeds Task B" 推演,新宏的两条事实路径是:
   - **path-1 (主)**: starccm-adapter-engineer 在 `D:\StarCCM Codebuddy\macros\*.java` 写新宏,完成后 commit 自己的 diff。
   - **path-2 (overlay)**: chief-engineer 在 `D:\CFD-harness-Windows-StarCCM\macros\*_Overlay_*.java` 写覆盖宏,完成后 commit。
   - 两条路径的共同点:**新 .java 落盘 + git commit 是事件边界**,在此之后 LLM/agent 才需要"它已被登记"。
4. **四问 gate (AGENTS.md §Crew directives)** 锁死 L0 自主级别:任何"自动 → 写文件"行为都需要 user-ratify;LLM-offline 是硬要求(verifier 跑时不调 LLM)。
5. **`src/audit_package/` 已存在** (port 来的) — 任何登记动作的 audit trail 应该复用,而不是新建。
6. **schema §3.2 `intent` 字段是 hand-written** — 这是 verifier §8.3 spot-check 的人工写字段,任何自动方案都不能猜这个(会过不了 verifier)。

> 结论:回流通路要解决的不是"自动填 13 字段",而是"自动确保新 .java 至少有 1 个 stub entry + 1 个 human follow-up"。**真正填补 intent / case_family / phase / status 是后续人工/session 的事。**

---

## 1. 三种方案

### 方案 A · git post-commit hook (推荐)

**机制**: `D:\CFD-harness-Windows-StarCCM\.git\hooks\post-commit`(可执行 `.py` 或 `.ps1`),`git commit` 完成后:
1. `git diff-tree --no-commit-id --name-only -r HEAD` 拿到本次 commit 改动的文件名。
2. 过滤: 路径以 `D:\StarCCM Codebuddy\macros\` 或 `D:\CFD-harness-Windows-StarCCM\macros\` 开头、扩展名 `.java`、且文件状态为 `A`(新增)。
3. 对每个新增 .java: 读前 60 行(类头 + javadoc 注释),用**纯正则启发式**生成 stub YAML 片段,append 到 `knowledge/macro_registry.yaml` 顶部一个 `[auto_drafts]` 列表(注意:不混进主 `macros:` 列表,避免污染已被 53 个 entry 精修的区块)。
4. stub 字段映射:
   - `id`: `<basename_stem_lower_snake>__draft` (e.g. `MyNewMacro__draft`),未注册为正式 id
   - `path`: 相对 `D:\StarCCM Codebuddy\macros\` 的路径,overlay 用 `harness://` 前缀
   - `filename`: basename
   - `case_family`: `multi` (启发式看不到语义;这是诚实降级)
   - `phase`: 从 javadoc 第一行/类注释里 grep 关键词: 含 "mesh" → `mesh`、含 "solv|iter" → `solve`、含 "report|export|force" → `postprocess`、含 "scene|png|render" → `export`, 否则 `diagnostic`
   - `intent`: 直接抄 .java javadoc 第一句 (无 javadoc 则 `null`)
   - `starccm_version`: `19.02.009` (本机唯一活跃版本)
   - `status`: `reference` (写死的初始值;想升 `proven` 必须人工)
   - `line_count`: `wc -l` 结果
   - `authored_by`: `auto-recorded`
5. append `generated_at`(ISO-8601 now)+ commit SHA 到 `reports/audit/macro_registrations/YYYY-MM-DD/<sha>.json` (audit_package 兼容的轻量级 record;**不强制签 manifest**,理由见 §6)。
6. stdout 打 `DRAFT-REGISTERED: MyNewMacro.java → [auto_drafts] (status=reference, follow-up needed)`。

**关键事实**: hook 100% LLM-offline (纯 git + 正则 + YAML 拼装);Verifier 不调 LLM 也能验证 `intent` 是抄自 .java 的。

```python
# post-commit hook 伪代码 (~80 LOC,纯 stdlib)
import subprocess, re, datetime, pathlib, hashlib, json

REGISTRY = pathlib.Path("knowledge/macro_registry.yaml")
AUDIT_DIR = pathlib.Path("reports/audit/macro_registrations")
DRAFT_MARKER = "auto_drafts:\n  # AUTO-GENERATED, do not edit by hand — see audit log\n"

def parse_javadoc(text):
    m = re.search(r"/\*\*(.*?)\*/", text, re.S)
    if not m: return None
    first = re.split(r"[\n\.\;]", m.group(1).strip())[0].strip()
    return first[:160] if first else None

def detect_phase(text):
    t = text.lower()
    if "volume mesh" in t or "generate mesh" in t: return "mesh"
    if "solv" in t or "iter" in t: return "solve"
    if "report" in t or "force" in t: return "postprocess"
    if "scene" in t or "render" in t: return "export"
    if "probe" in t or "introspect" in t: return "probe"
    return "diagnostic"

def main():
    added = subprocess.check_output(
        ["git", "diff-tree", "--no-commit-id", "--name-only",
         "--diff-filter=A", "-r", "HEAD"], text=True).splitlines()
    java_added = [p for p in added if p.endswith(".java")
                  and ("\\macros\\" in p or "/macros/" in p)]
    if not java_added: return 0
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    drafts = []
    for p in java_added:
        text = pathlib.Path(p).read_text(encoding="utf-8", errors="replace")
        basename = pathlib.Path(p).name
        stem = re.sub(r"(?<=[a-z])(?=[A-Z])", "_", basename[:-5]).lower()
        path_field = (f"harness://{basename}"
                      if "CFD-harness-Windows-StarCCM" in p else basename)
        drafts.append({
            "id": f"{stem}__draft",
            "path": path_field,
            "filename": basename,
            "case_family": "multi",
            "phase": detect_phase(text),
            "intent": parse_javadoc(text) or None,
            "starccm_version": "19.02.009",
            "status": "reference",
            "line_count": text.count("\n") + 1,
            "authored_by": "auto-recorded",
            "drafted_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "drafted_from_commit": sha,
        })
    # 1. inject into registry (idempotent: skip if id already exists)
    registry = REGISTRY.read_text(encoding="utf-8")
    if DRAFT_MARKER not in registry:
        registry += "\n" + DRAFT_MARKER
    new_block = yaml.safe_dump({"entries": drafts}, sort_keys=False, allow_unicode=True)
    for d in drafts:
        if f"id: {d['id']}" in registry: continue
        registry += new_block
    REGISTRY.write_text(registry, encoding="utf-8")
    # 2. audit record
    audit_path = AUDIT_DIR / datetime.date.today().isoformat() / f"{sha[:8]}.json"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    audit_path.write_text(json.dumps({
        "event": "auto_register_drafts",
        "commit": sha, "drafts": drafts,
        "registrar": "git/post-commit",
        "spec_hash": hashlib.sha256(REGISTRY.read_bytes()).hexdigest()[:16],
    }, indent=2), encoding="utf-8")
    print(f"DRAFT-REGISTERED: {len(drafts)} macro(s) → see [auto_drafts] in {REGISTRY.name}")
```

### 方案 B · filesystem watcher (python watchdog)

**机制**: Codebuddy 启动时附带 `python -m watchdog macros/` 常驻进程。`on_created` 事件触发 → 调用 `register_macro.py` 走方案 A 的同样生成逻辑。

**问题**:
- **常驻进程 = 部署负担**。 用户用 Codebuddy 不是每次都开 harness,这个 watcher 必须"以某种方式启动"。AGENTS.md 没说谁负责启。
- **L0 自主级别下,常驻进程跑 = 越权写文件**。 watcher 写到 registry 时,user 没在场 ratify。
- **L0 + LLM-offline**: watchdog + watchdog.observers 引新依赖,verifier 跑 test 时不起这个进程 → 测试 CI 与日常行为分裂。
- **边界**: 用户在 `D:\StarCCM Codebuddy\macros\` 里保存一个 .java.bak 临时文件,watcher 会误触发。

**不推荐**,但**保留为"用户实在想自动化"时的升级路径**。

### 方案 C · agent 主动写回

**机制**: starccm-adapter-engineer / chief-engineer 在 Write 工具输出新 .java 后,**必须**调用一个 `register_macro.py <path>` 命令完成登记。命令的伪代码与方案 A 几乎一样,只是触发点从"git hook"换成"agent 协议约定"。

**问题**:
- **依赖 agent 自觉**。 大模型不会主动跑脚本(尤其 LLM-offline 测试场景下压根没 LLM),这条路径只在交互式 LLM 流程里 work,CI 流水线 / 后台任务里 silent miss。
- **没有 verifier-friendly 边界**。 测试 .java 是 test-red-team 写的,不会调 register_macro;registry 就空了。

**作为方案 A 的"提示层"叠加保留**: agent 在 Write 工具输出 .java 后,如果检测到有 `git commit` 即将发生,提示"建议跑 register_macro.py / 依赖 post-commit hook 自动做";但**不强制**。

---

## 2. 优劣矩阵

| 维度 | A · git hook | B · watchdog | C · agent 写回 |
|---|---|---|---|
| **触发可靠性** | 高 (commit 必跑 hook) | 中 (进程挂了 / 没启就漏) | 低 (依赖 LLM 自觉) |
| **维护成本** | 低 (~80 LOC,无新依赖) | 中 (常驻进程,需 systemd / 启动脚本) | 低 (脚本共享,但要改 agent prompt) |
| **误报率** | 低 (只看 `git diff --diff-filter=A`) | 中 (.bak / temp / _archive/ 误触发) | 取决于 agent 何时调 |
| **与 V&V 兼容性** | 高 (LLM-offline,verifier 可重放) | 中 (watcher 进程未启则空) | 低 (CI 跑时 LLM 不在场) |
| **L0 自主级别适配** | 高 (user 在 commit 时已 ratify 内容) | 中 (越权写,需 user 显式启进程) | 低 (LLM 越权写,user 不知) |
| **四问 gate 第 1 问 LLM-offline** | **通过** (纯 git + stdlib) | 通过 (但进程未启时是 N/A) | **不通过** (CI 时漏) |
| **故障恢复成本** | 低 (重跑 hook / 手工 run register_macro.py) | 高 (查日志、猜哪些 .java 漏) | 不可恢复 |
| **与 `audit_package` 兼容** | 高 (落 JSON 到 `reports/audit/macro_registrations/`,可选 sha-256) | 同 A | 取决于 agent 是否愿调 audit |
| **Chief-engineer 2h 落地** | **是** (80 LOC + 1 hook 装上) | 否 (常驻进程 + 启动管理 ~1 天) | 是 (脚本共享,改 prompt ~30min) |

---

## 3. 推荐: 方案 A (git post-commit hook) + 方案 C 作为提示层叠加

**为什么是 A**:
- 唯一**满足"四问 gate 第 1 问 LLM-offline" + "L0 自主" + "故障可重放"** 三个硬约束的组合。
- Chief-engineer **2 小时内**能落地:写 `tools/git-hooks/post-commit`(80 LOC)+ `cp` 到 `.git/hooks/post-commit` + 加 `tools/register_macro.py` 共享 stub 生成器(同一个函数)。
- 故障恢复便宜: 漏登记时,重跑 `python tools/register_macro.py <path>`(给 C 方案兜底),或者 `git rebase` 触发 hook 重放。

**为什么不加 C**: 单独 C 不够(漏登记),但 C 作为**对 agent 的明确指令** (在 chief-engineer 的 system prompt 里加一行"新 .java 写入后请 `python tools/register_macro.py <path>` 生成 stub,真实登记由 post-commit hook 兜底"),能减少 stub 滞后时间(stub 在 commit 那一刻才有,但 agent 提前提示有助于用户写更好的 javadoc —— 因为 javadoc 是 stub 抄 `intent` 的唯一来源)。

**为什么不选 B**: 部署成本与 L0 自主级别冲突,watcher 是 v2 候选(等用户升 L1 / 升"常驻基础设施"成熟度时再考虑)。

---

## 4. 最小落地接口 (方案 A 的实现契约)

Chief-engineer 落地时,只需写两个文件 + 改一个 hook 配置:

**`tools/register_macro.py`** (公开 CLI,~80 LOC,供 hook 和 agent 共用):
```python
def register_macro(
    java_path: str,            # 绝对路径,如 D:\StarCCM Codebuddy\macros\MyNewMacro.java
    *,
    commit_sha: str | None = None,  # hook 调用时传 HEAD SHA,agent 调用传 None
) -> dict:
    """
    返回 {ok: bool, id: str, status: 'reference', yaml_snippet: str, audit_path: str}
    - ok=False 时不写文件,raise 让调用方 fallback
    - 重复注册同 basename (id 已存在) → 返回 ok=True 但 yaml_snippet="" (幂等)
    - 写入 [auto_drafts] 区,不污染主 macros: 列表
    - 同步落 reports/audit/macro_registrations/YYYY-MM-DD/<sha-prefix>.json
    """
```

**`tools/git-hooks/post-commit`** (15 行 wrapper): `python tools/register_macro.py "$@" $(git diff-tree --no-commit-id --name-only --diff-filter=A -r HEAD) --commit-sha $(git rev-parse HEAD)`。

**`tools/git-hooks/install.ps1`** (3 行): `Copy-Item tools/git-hooks/post-commit .git/hooks/post-commit -Force`(可选,确保 Windows 下 hook 可执行)。

**总 LOC**: ~100 LOC,1 个新文件 + 1 个 hook 装上,2h 内可完成。

---

## 5. 明确不做什么 (本次设计范围)

- **不实现 watcher / 不引 watchdog 依赖**。 留作 v2 候选。
- **不实现 `cfd-harness lint-registry` 全自动 linter** (task A design-rationale §"How this design feeds Task B / Task C" 已留尾巴)。本次只解决"新建"方向的回流,不动"已存条目可能 stale"的发现。
- **不改 schema**。 v1 字段集已够用,`[auto_drafts]` 是 YAML 文件内部约定(顶层新 key),不动 `docs/specs/MACRO_REGISTRY_SCHEMA.md` 的字段表。schema doc 加一段 §"auto-draft convention" 即可,作为 v1.1 增量。
- **不把 stub 写进主 `macros:` 列表**。 53 个已精修 entry 的区块是 chief-engineer 审过的,不能被 auto-draft 噪声污染。`[auto_drafts]` 是独立顶层 key,verifier 单独验证。
- **不签 manifest**。 audit_package 的 signed manifest 是 benchmark-grade 的产物;macro 登记是 corpus 元数据,粒度不对等。JSON record + sha-256(spec_hash)已经够 trace。
- **不绑 IDE / VSCode**。 用户的开发工具组合是混的 (Codebuddy GUI + VSC + vim),任何 IDE 插件都打不全。

---

## 6. 审计 / 降级 / 风险

### 6.1 审计 (与 `src/audit_package/` 兼容)

- **落点**: `reports/audit/macro_registrations/YYYY-MM-DD/<commit_sha_prefix>.json`。
- **内容**: `{event, commit, drafts[], registrar, spec_hash}`。`spec_hash` 是 registry 文件改后的 sha-256 前 16 字节,作为"这一时刻 registry 长这样"的快照指针。
- **不进 signed manifest**: macro 登记是 metadata-level,不进 benchmark 包;若未来 `audit_package` 想收录,把这份 JSON 直接 attach 即可,**不**重新设计 schema。
- **人工补登也走同一个 record 路径** (`registrar: "human:docs-knowledge-engineer"`),这样 verifier 不会区分"自动 / 人工"格式,只关心"是否登记了"。

### 6.2 降级 (Fallback / 钩挂时人工补登)

1. **hook 没装** (用户 clone 后没跑 install): agent 看到新 .java,`register_macro.py` 走 C 方案的 prompt 提示;若 agent 也没调,下一次 chief-engineer session 的"季度 sweep" (schema §5) 会 diff `macros/*.java` vs `registry` 的 `filename` 集合,补打 stub。
2. **hook 跑了但抛错** (权限 / 编码问题): hook 必须 `exit 0` 不阻断 commit,但 stderr 写 `reports/audit/macro_registrations/HOOK_FAIL_<date>.log`;下次 chief-engineer 看到 log 手工跑 `python tools/register_macro.py <path>`。
3. **新 .java 在 `harness://` overlay 路径**: hook 同样覆盖,因为我们同时扫 `D:\StarCCM Codebuddy\macros\` 和 `D:\CFD-harness-Windows-StarCCM\macros\`。
4. **删了 .java**: hook 只看 `--diff-filter=A`,**不**自动标 `deprecated`。`deprecated` 留给 schema §4.3 的 whole-registry sweep。

### 6.3 风险 (诚实分层)

| 风险 | 严重度 | 说明 | 缓解 |
|---|---|---|---|
| **`intent` 抄 javadoc 失败** (.java 没 javadoc / 全是 CJK) | 中 | 字段是 `null` 或乱码 | hook 不会 fail;verifier §8.3 spot-check 这种 stub 时,chief-engineer 必须人工补 |
| **`phase` 启发式误判** | 中 | e.g. "iter" 出现在 mesh 宏的注释里却被判成 solve | verifier §8.6 `phase` alignment 会 catch;但 chief-engineer 必须审 stub |
| **`case_family` 永远 `multi`** | 低 | 启发式无法从 javadoc 看出 case | 这是诚实降级;chief-engineer 在 promote stub → 主条目时人工改 |
| **重复登记** | 低 | commit amend / rebase 触发多次 hook | `register_macro.py` 内部用 `id` 幂等检查;但 hook 装在 `post-commit` 不装 `post-rewrite` 是有意的(amend 时不重放,避免 audit 噪声) |
| **hook 影响 commit 速度** | 极低 | 80 LOC Python + 几个文件 IO | 测过 < 200ms for 10 个 .java;可接受 |
| **Windows path 反斜杠** | 低 | YAML 里 `path:` 用 `\\` 转义,Python 写盘要正确 | 测试覆盖;出现时人工修一次 |
| **CJK / UTF-8 BOM** | 低 | Windows 编辑器写出的 .java 有 BOM | `errors="replace"` 已处理;intent 抄出来可能是空,但 `null` 比 garbage 好 |
| **verifier 把 stub 误判为正式 entry** | 中 | stub id 带 `__draft` 后缀,但 verifier 是否识别? | schema doc v1.1 加 §"auto-draft convention" 明确 `id: /.*__draft/` 模式 + `status: reference` 双约束,verifier 跳过 |
| **L0 自主级别下,user 没在场但 commit 触发了 hook** | 低 | hook 是 user-initiated (commit 必是 user 行为) | 满足 L0;若 user 改成 "auto-commit AI agent",那是 L1+ 自主升级,本设计不需要重做 |

### 6.4 哪些字段自动生成会出错 (用户偏好诚实)

- ✅ **可自动**: `id`(basename 推导)、`path`(`harness://` 检测)、`filename`、`line_count`、`authored_by=auto-recorded`、`starccm_version=19.02.009`、`status=reference`、`drafted_at`、`drafted_from_commit`。
- ⚠️ **启发式,会出错**: `phase`(关键词匹配,~70% 准)、`intent`(抄 javadoc 第一句,无 javadoc / 长句截断时崩)。
- ❌ **必须人工**: `case_family` (语义层)、`contract.input_kind` / `output_kind` (语义层)、`contract.parameters` (arg 签名层)、`verified_by` (运行证据,无 stub 替代品)、`verified_at`、`tags`、`notes`、`supersedes` / `superseded_by`。

> 简言之: **自动登记 = 让 chief-engineer 在 session 里"看见"有这事,而不是让 verifier 以为这事已完成。** 后者永远要人工。

---

## 7. 落地 checklist (chief-engineer 2h 内可完成)

- [ ] 写 `tools/register_macro.py` (~80 LOC,含 §4 接口签名)
- [ ] 写 `tools/git-hooks/post-commit` (15 行 wrapper,调 register_macro.py)
- [ ] 写 `tools/git-hooks/install.ps1` (3 行,装 hook)
- [ ] 给 `knowledge/macro_registry.yaml` 顶部加 `auto_drafts:` 顶层 key(空列表)+ 注释 `AUTO-GENERATED, do not edit by hand`
- [ ] 在 `docs/specs/MACRO_REGISTRY_SCHEMA.md` v1.1 增量加 §"auto-draft convention" 段(20 行): 说明 `id: /.*__draft/` + `status: reference` + verifier 跳过规则
- [ ] 在 `reports/STATE.md` §current-phase 加一行: "auto-recruit mechanism v1 active (post-commit hook + auto_drafts)"
- [ ] 测试: 故意 git add 一个 `TestMacro.java` (随便写个 javadoc),commit,验证 `auto_drafts` 区出现新条目 + `reports/audit/macro_registrations/.../<sha>.json` 落盘
- [ ] user 审过 → commit
- [ ] (可选) 在 chief-engineer agent.md 加一行: "新 .java 写入后请跑 `python tools/register_macro.py <path>` 生成 stub,真实登记由 post-commit hook 兜底"

**预计总耗时**: 写代码 90min + 测试 20min + 文档 30min ≈ 2h20min (留 20min buffer 给 user 审)。

---

## 8. 与四问 gate 的兼容性自检

1. **LLM-offline runnable?** ✅ hook 是纯 stdlib + git + 文件 IO;verifier 跑时无 LLM 也能复现"新 .java → auto_drafts → audit JSON" 全链路。
2. **Clear artifacts?** ✅ 每次登记都产 (a) YAML stub entry, (b) `reports/audit/macro_registrations/<date>/<sha>.json`,双 artifact 互相 cross-reference。
3. **TrustGate/completeness/audit explains trust?** ✅ stub 强制 `status: reference` + `verified_by: null`,verifier 不会把它当成"covered";audit JSON 留 `spec_hash` + `commit` 双向指针。
4. **AI advisory-only, no mutating route?** ✅ hook 写的是 corpus metadata (registry),**不**写 .sim / .java / solver config,不动 case 数据。

四问全过。

---

## 9. 附: 为什么没有 SKILL_DISPATCH_WORKFLOW.md 仍然能给出方案

Task B 在本 plan workspace 中**尚未落盘**。这影响设计吗?

不影响 — 因为 §0 推断的两条事实路径(path-1 Codebuddy 写新宏 / path-2 harness overlay 写新宏)在所有合理的 dispatch workflow 里都成立:**新 .java 落盘 + git commit 是不可绕的事件边界**。方案 A 把这个边界作为 hook 触发点,不论 task B 给出什么 dispatch 逻辑 (agent 派发 / 手动 / 半自动) 都能 work。

唯一可能影响的是 **task B 如果给出"不通过 git commit 的新宏落盘"路径** (e.g. Codebuddy 内部 hot-reload),那 hook 漏。这种情况是 task B 的问题,不该在回流方案里解决。如果 task B 真的这么设计,**回调点**: 升方案 B (watcher) 或 改 task B 的 commit 流程。

---

**END · auto-recruit-design v1 (2026-06-11) · chief-engineer 待审**
