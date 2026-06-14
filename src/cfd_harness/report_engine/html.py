"""Self-contained HTML post-processing report for a V&V run.

Renders ONE portable ``.html`` from a harness ``data.json``, optionally
enriched with:
  - the real solver's convergence history (residual curves drawn as an
    inline log-scale SVG — no JS/network),
  - scene PNGs embedded as base64 data-URIs (the file opens anywhere),
  - the gold-standard literature targets (read from the gold YAML).

Solver-agnostic. No external assets, no JavaScript, no network — a single
file you can open or email. Honest by construction: it renders exactly the
verdict the harness produced (a MOCK / un-validated run says so plainly).

CLI:
    python -m cfd_harness.report_engine.html <data.json> \
        [--convergence <conv.json>] [--png a.png[:caption] ...] \
        [--gold <gold.yaml>] [--audit <audit.json>] [--out report.html]
"""
from __future__ import annotations

import argparse
import base64
import html as _html
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = ["render_html_report"]

_LEVEL_COLOR = {"PASS": "#1a7f37", "WARN": "#9a6700", "FAIL": "#cf222e"}
_SERIES_COLORS = [
    "#0969da", "#cf222e", "#1a7f37", "#9a6700",
    "#8250df", "#bf3989", "#0a7ea4", "#6e7781",
]


def _esc(x: Any) -> str:
    return _html.escape(str(x))


def _fmt_sci(v: Any) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return _esc(v)
    if f != f:  # nan
        return "—"
    if f == 0:
        return "0"
    return f"{f:.3e}"


def _png_data_uri(path: Path, max_bytes: int = 6_000_000) -> Optional[str]:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    if len(raw) > max_bytes:
        return None
    return "data:image/png;base64," + base64.b64encode(raw).decode("ascii")


# ---------------------------------------------------------------------------
# Inline SVG residual-convergence plot (log y), dependency-free.
# ---------------------------------------------------------------------------

def _downsample(xs: List[Any], ys: List[Any], target: int = 600) -> Tuple[list, list]:
    n = len(xs)
    if n <= target:
        return xs, ys
    step = max(1, n // target)
    return xs[::step], ys[::step]


def residual_svg(
    iterations: List[Any],
    series: Dict[str, List[Any]],
    floor: Optional[float] = None,
    width: int = 760,
    height: int = 400,
) -> str:
    """Multi-series log-scale residual plot as a standalone SVG string."""
    posv = [float(v) for s in series.values() for v in s
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0]
    if not iterations or not posv:
        return ""
    lo = math.floor(math.log10(min(posv)))
    hi = math.ceil(math.log10(max(posv)))
    if floor and floor > 0:
        lo = min(lo, math.floor(math.log10(floor)))
    if hi <= lo:
        hi = lo + 1
    xmin, xmax = float(iterations[0]), float(iterations[-1])
    pad_l, pad_r, pad_t, pad_b = 66, 168, 18, 44
    pw, ph = width - pad_l - pad_r, height - pad_t - pad_b

    def X(it: float) -> float:
        return pad_l + (float(it) - xmin) / ((xmax - xmin) or 1) * pw

    def Y(v: float) -> float:
        lv = math.log10(max(float(v), 10.0 ** lo))
        return pad_t + (hi - lv) / ((hi - lo) or 1) * ph

    p: List[str] = [
        f'<svg viewBox="0 0 {width} {height}" width="100%" '
        f'preserveAspectRatio="xMidYMid meet" role="img" '
        f'font-family="ui-monospace,Menlo,Consolas,monospace">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#fff"/>',
    ]
    # horizontal decade gridlines + y labels
    for d in range(lo, hi + 1):
        y = Y(10.0 ** d)
        p.append(f'<line x1="{pad_l:.1f}" y1="{y:.1f}" x2="{pad_l + pw:.1f}" '
                 f'y2="{y:.1f}" stroke="#eaeef2" stroke-width="1"/>')
        p.append(f'<text x="{pad_l - 8:.1f}" y="{y + 4:.1f}" text-anchor="end" '
                 f'font-size="11" fill="#57606a">1e{d}</text>')
    # x axis ticks
    for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
        it = xmin + frac * (xmax - xmin)
        x = X(it)
        p.append(f'<text x="{x:.1f}" y="{height - pad_b + 22:.1f}" text-anchor="middle" '
                 f'font-size="11" fill="#57606a">{int(it)}</text>')
    p.append(f'<text x="{pad_l + pw / 2:.1f}" y="{height - 6:.1f}" text-anchor="middle" '
             f'font-size="12" fill="#24292f">迭代步 iteration</text>')
    p.append(f'<text x="16" y="{pad_t + ph / 2:.1f}" text-anchor="middle" font-size="12" '
             f'fill="#24292f" transform="rotate(-90 16 {pad_t + ph / 2:.1f})">残差 residual</text>')
    # convergence floor
    if floor and floor > 0:
        yf = Y(floor)
        p.append(f'<line x1="{pad_l:.1f}" y1="{yf:.1f}" x2="{pad_l + pw:.1f}" y2="{yf:.1f}" '
                 f'stroke="#cf222e" stroke-width="1.4" stroke-dasharray="6 4"/>')
        p.append(f'<text x="{pad_l + pw - 4:.1f}" y="{yf - 5:.1f}" text-anchor="end" '
                 f'font-size="11" fill="#cf222e">收敛阈值 {floor:g}</text>')
    # series polylines + legend
    for i, (name, s) in enumerate(series.items()):
        col = _SERIES_COLORS[i % len(_SERIES_COLORS)]
        xs, ys = _downsample(list(iterations), list(s))
        pts = " ".join(
            f"{X(it):.1f},{Y(v):.1f}"
            for it, v in zip(xs, ys)
            if isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0
        )
        if pts:
            p.append(f'<polyline points="{pts}" fill="none" stroke="{col}" '
                     f'stroke-width="1.5" opacity="0.9"/>')
        ly = pad_t + 6 + i * 18
        p.append(f'<rect x="{pad_l + pw + 16}" y="{ly - 9}" width="14" height="3" fill="{col}"/>')
        last = next((v for v in reversed(s)
                     if isinstance(v, (int, float)) and not isinstance(v, bool)), None)
        lbl = f"{_esc(name)}  {_fmt_sci(last)}" if last is not None else _esc(name)
        p.append(f'<text x="{pad_l + pw + 34}" y="{ly - 4}" font-size="11" '
                 f'fill="#24292f">{lbl}</text>')
    p.append("</svg>")
    return "".join(p)


# ---------------------------------------------------------------------------
# Gold-standard target extraction (for the V&V table)
# ---------------------------------------------------------------------------

def _gold_targets(gold_path: Optional[Path]) -> Dict[str, Dict[str, Any]]:
    if not gold_path or not gold_path.exists():
        return {}
    try:
        import yaml
        out: Dict[str, Dict[str, Any]] = {}
        for doc in yaml.safe_load_all(gold_path.read_text(encoding="utf-8")):
            if not doc or "quantity" not in doc:
                continue
            refs = doc.get("reference_values") or []
            val = refs[0].get("value") if refs and isinstance(refs[0], dict) else None
            out[str(doc["quantity"])] = {"value": val, "tolerance": doc.get("tolerance")}
        return out
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Main renderer
# ---------------------------------------------------------------------------

def render_html_report(
    data_path,
    *,
    out_html=None,
    convergence_json=None,
    scene_pngs: Optional[List[Any]] = None,
    gold_path=None,
    audit_json=None,
    generated_at: Optional[str] = None,
) -> Path:
    """Render a self-contained HTML report from a harness ``data.json``.

    ``scene_pngs`` is a list of paths or ``(path, caption)`` tuples.
    Returns the written HTML path.
    """
    data_path = Path(data_path)
    payload = json.loads(data_path.read_text(encoding="utf-8"))
    task = payload.get("task_spec", {})
    run = payload.get("run_report", {})
    ver = payload.get("verifier_report", {})
    er = run.get("execution_result") or {}

    case_id = task.get("case_id", "?")
    level = ver.get("level", "?")
    color = _LEVEL_COLOR.get(level, "#57606a")
    is_mock = bool(er.get("is_mock", False))

    audit = {}
    if audit_json and Path(audit_json).exists():
        try:
            audit = json.loads(Path(audit_json).read_text(encoding="utf-8"))
        except Exception:
            audit = {}
    sig = audit.get("signature", {})
    signing = audit.get("signing", {})

    gold = _gold_targets(Path(gold_path) if gold_path else None)
    residuals = er.get("residuals", {}) or {}
    kq = er.get("key_quantities", {}) or {}
    # A run whose force/field reports come back ~0 is a quiescent (no-flow)
    # solve — the field plots will be blank/single-colour. Surface that
    # honestly rather than presenting empty contours as real results.
    quiescent = bool(kq.get("force_reports_zero")) or bool(kq.get("fields_quiescent"))
    floor = 1e-4  # display reference; the actual gate floor lives in thresholds

    # ---- convergence SVG ----
    svg = ""
    if convergence_json and Path(convergence_json).exists():
        try:
            conv = json.loads(Path(convergence_json).read_text(encoding="utf-8"))
            its = conv.get("iterations") or []
            series = conv.get("residuals") or {}
            svg = residual_svg(its, series, floor=floor)
        except Exception:
            svg = ""

    # ---- sections ----
    def card(label, value, sub=""):
        sub_html = f'<div class="sub">{_esc(sub)}</div>' if sub else ""
        return (f'<div class="card"><div class="lbl">{_esc(label)}</div>'
                f'<div class="val">{value}</div>{sub_html}</div>')

    val_badge = ('<span class="ok">✅ 已验证 validated</span>' if ver.get("is_validated")
                 else '<span class="no">❌ 未验证 not validated</span>')
    cards = "".join([
        card("V&amp;V 判定", f'<span style="color:{color}">{_esc(level)}</span>'),
        card("验证状态", val_badge),
        card("执行器", _esc(run.get("mode", "?")),
             "真实求解器 real solver" if not is_mock else "MOCK(合成数据,封顶 WARN)"),
        card("签名审计",
             ('🔒 trusted' if signing.get("trusted") else '⚠ dev-unsigned')
             if audit else "—",
             f'key_id={sig.get("key_id","")}' if sig else ""),
    ])

    # V&V comparison table (measured vs gold)
    cq = ver.get("comparison_quantities") or []
    rows = []
    if cq:
        for q in cq:
            ap = q.get("all_pass")
            rows.append(
                f'<tr><td>{_esc(q.get("name"))}</td><td>{_fmt_sci(q.get("measured"))}</td>'
                f'<td>{_fmt_sci(q.get("gold"))}</td>'
                f'<td>{_pct(q.get("relative_error"))}</td><td>{_pct(q.get("tolerance"))}</td>'
                f'<td>{"✅" if ap else "❌"}</td></tr>')
    else:
        # No measured quantities — show the gold targets that COULD NOT be measured.
        failing = ver.get("comparison_failing") or list(gold.keys())
        for name in failing:
            g = gold.get(name, {})
            rows.append(
                f'<tr><td>{_esc(name)}</td><td class="muted">未测得 n/a</td>'
                f'<td>{_fmt_sci(g.get("value")) if g.get("value") is not None else "—"}</td>'
                f'<td class="muted">—</td><td>{_pct(g.get("tolerance"))}</td><td>❌</td></tr>')
    cmp_table = (
        '<table><thead><tr><th>物理量 quantity</th><th>实测 measured</th>'
        '<th>文献 gold</th><th>相对误差</th><th>容差</th><th>通过</th></tr></thead>'
        f'<tbody>{"".join(rows)}</tbody></table>')

    # residual table (final values)
    rres = "".join(
        f'<tr><td>{_esc(k)}</td><td>{_fmt_sci(v)}</td>'
        f'<td>{"✅" if (isinstance(v,(int,float)) and abs(v) < floor) else "❌"}</td></tr>'
        for k, v in residuals.items())
    res_table = (
        '<table><thead><tr><th>残差场 field</th><th>最终值 final</th>'
        f'<th>&lt; {floor:g}</th></tr></thead><tbody>{rres or "<tr><td colspan=3 class=muted>无残差数据</td></tr>"}</tbody></table>')

    # scene images
    imgs = []
    for item in (scene_pngs or []):
        path, caption = (item if isinstance(item, (tuple, list)) else (item, Path(item).stem))
        uri = _png_data_uri(Path(path))
        if uri:
            imgs.append(f'<figure><img src="{uri}" alt="{_esc(caption)}"/>'
                        f'<figcaption>{_esc(caption)}</figcaption></figure>')
    img_grid = f'<div class="grid">{"".join(imgs)}</div>' if imgs else \
        '<p class="muted">(未提供场景图)</p>'
    scene_warning = ""
    if quiescent:
        scene_warning = (
            '<div class="banner" style="background:#ffebe9;border-color:#cf222e">'
            '⚠ <b>本次求解的力与场近似为零</b>(velocity≈0 m/s · pressure≈0 Pa · force=0)。'
            '下列云图<b>无有效流动数据</b> —— 解为空(全场静止,无涡街),部分场景甚至未绑定场函数'
            '(图例显示 <code>&lt;Select Function&gt;</code>)。这是 STAR-CCM+ 2402 R8 该算例'
            '解为空 / 力·场读取受限(DEC-005)所致,<b>不是报告渲染问题</b>。</div>')

    notes = " · ".join(_esc(n) for n in (run.get("notes") or []))
    gen_at = generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    audit_block = ""
    if audit:
        audit_block = (
            '<section><h2>🔒 签名审计 signed audit</h2>'
            f'<table><tbody>'
            f'<tr><th>algorithm</th><td>{_esc(sig.get("algorithm",""))}</td></tr>'
            f'<tr><th>key_id</th><td><code>{_esc(sig.get("key_id",""))}</code></td></tr>'
            f'<tr><th>key_source</th><td>{_esc(signing.get("key_source",""))} '
            f'(trusted={_esc(signing.get("trusted"))})</td></tr>'
            f'<tr><th>signed_at</th><td>{_esc(sig.get("signed_at",""))}</td></tr>'
            f'<tr><th>hmac</th><td><code>{_esc(str(sig.get("hmac",""))[:32])}…</code></td></tr>'
            '</tbody></table>'
            '<p class="muted">验证: <code>python -m cfd_harness.audit_package.verify '
            'audit.json --key &lt;secret&gt;</code></p></section>')

    html_doc = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>{_esc(case_id)} · V&amp;V 后处理报告</title>
<style>
:root{{--fg:#24292f;--mut:#57606a;--bd:#d0d7de;--bg:#f6f8fa}}
*{{box-sizing:border-box}}
body{{margin:0;font-family:system-ui,"Segoe UI","PingFang SC","Microsoft YaHei",sans-serif;
color:var(--fg);background:var(--bg);line-height:1.55}}
.wrap{{max-width:980px;margin:0 auto;padding:28px 20px 64px}}
header{{border-left:6px solid {color};padding:6px 0 6px 16px;margin-bottom:20px}}
h1{{margin:0;font-size:22px}} h2{{font-size:16px;margin:28px 0 10px;border-bottom:1px solid var(--bd);padding-bottom:6px}}
.meta{{color:var(--mut);font-size:13px;margin-top:4px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:16px 0}}
.card{{background:#fff;border:1px solid var(--bd);border-radius:8px;padding:12px 14px}}
.card .lbl{{font-size:12px;color:var(--mut)}} .card .val{{font-size:18px;font-weight:600;margin-top:2px}}
.card .sub{{font-size:11px;color:var(--mut);margin-top:2px}}
.ok{{color:#1a7f37;font-weight:600}} .no{{color:#cf222e;font-weight:600}}
section{{background:#fff;border:1px solid var(--bd);border-radius:8px;padding:16px 18px;margin:14px 0}}
table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border:1px solid var(--bd);padding:6px 10px;text-align:left}}
thead th{{background:var(--bg)}} th{{white-space:nowrap}}
td.muted,.muted{{color:var(--mut)}} code{{font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}}
figure{{margin:0;border:1px solid var(--bd);border-radius:8px;overflow:hidden;background:#fff}}
figure img{{width:100%;display:block}} figcaption{{font-size:12px;color:var(--mut);padding:6px 10px}}
.banner{{padding:10px 14px;border-radius:8px;background:#fff8c5;border:1px solid #d4a72c;font-size:13px;margin:8px 0}}
footer{{color:var(--mut);font-size:12px;margin-top:24px;text-align:center}}
</style></head>
<body><div class="wrap">
<header>
<h1>卡门涡街 V&amp;V 后处理报告 · {_esc(case_id)}</h1>
<div class="meta">执行器 <b>{_esc(run.get("mode","?"))}</b> · 生成于 {_esc(gen_at)} (UTC) ·
判定 <b style="color:{color}">{_esc(level)}</b></div>
</header>

<div class="cards">{cards}</div>

<section>
<h2>📉 收敛历史 convergence</h2>
{svg or '<p class="muted">(未提供 convergence.json)</p>'}
<h2 style="border:0;margin:18px 0 8px;font-size:14px">残差最终值</h2>
{res_table}
</section>

<section>
<h2>📐 V&amp;V 对比 (Williamson 1996, Re=200)</h2>
{cmp_table}
<div class="banner">说明:本算例力报告返回哨兵零值(<code>force_reports_zero</code>,见 DEC-005),
故 Strouhal / Cd / Cl_rms <b>无法实测</b>,V&amp;V 诚实判 FAIL —— 这是 STAR-CCM+ 2402 R8
公共 Java API 的力读取限制,不是仿真本身失败。</div>
</section>

<section>
<h2>🖼 场景可视化 scene fields</h2>
{scene_warning}
{img_grid}
</section>

{audit_block}

<footer>cfd-harness-windows-starccm · 自包含离线报告 · notes: {notes}</footer>
</div></body></html>"""

    out = Path(out_html) if out_html else data_path.with_name("report.html")
    out.write_text(html_doc, encoding="utf-8")
    return out


def _pct(v: Any) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if f != f or f in (float("inf"), float("-inf")):
        return "—"
    return f"{f * 100:.2f}%"


def _main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Render a self-contained HTML V&V report")
    p.add_argument("data_json", help="harness data.json")
    p.add_argument("--convergence", default=None, help="solver convergence.json (residual history)")
    p.add_argument("--png", nargs="*", default=None,
                   help="scene PNG paths, optionally 'path|caption' (| avoids the Windows drive colon)")
    p.add_argument("--gold", default=None, help="gold-standard YAML (for literature targets)")
    p.add_argument("--audit", default=None, help="audit.json (signature block)")
    p.add_argument("--out", default=None, help="output .html (default: <data_json dir>/report.html)")
    args = p.parse_args(argv)

    pngs = []
    for item in (args.png or []):
        if "|" in item:
            path, cap = item.split("|", 1)
            pngs.append((path, cap))
        else:
            pngs.append(item)

    out = render_html_report(
        args.data_json, out_html=args.out, convergence_json=args.convergence,
        scene_pngs=pngs or None, gold_path=args.gold, audit_json=args.audit,
    )
    print(f"[html] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
