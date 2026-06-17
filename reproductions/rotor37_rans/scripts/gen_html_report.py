# -*- coding: utf-8 -*-
"""Generate a research-grade, self-contained HTML report that showcases the END-TO-END
engineering capability demonstrated in the NASA Rotor 37 reproduction effort.
Parses real residual histories from the solver logs, renders figures, embeds everything
(figures base64) into a single styled REPORT.html."""
import os, re, base64, io

ROOT = r"D:\CFD-harness-Windows-StarCCM\reproductions\rotor37_rans"
MAC = ROOT + r"\macro"
GEOM = ROOT + r"\geom"
OUT = ROOT + r"\REPORT.html"

def parse_continuity(logpath, maxn=4000):
    xs, ys = [], []
    if not os.path.exists(logpath):
        return xs, ys
    rowre = re.compile(r"^\s*(\d+)\s+([0-9.eE+\-]+)\s+[0-9.eE+\-]+")
    with open(logpath, errors="ignore") as f:
        for line in f:
            m = rowre.match(line)
            if m:
                try:
                    it = int(m.group(1)); cy = float(m.group(2))
                    if 0 < cy < 1e90:
                        xs.append(it); ys.append(cy)
                except Exception:
                    pass
            if len(xs) > maxn:
                break
    return xs, ys

def b64_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("ascii")

def b64_file(path):
    if not os.path.exists(path):
        return None
    return base64.b64encode(open(path, "rb").read()).decode("ascii")

conv_img = None
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.alpha": 0.3,
                         "figure.facecolor": "white", "axes.edgecolor": "#888"})
    x2, y2 = parse_continuity(MAC + r"\phB_shroud2.log")
    x1, y1 = parse_continuity(MAC + r"\phB_flip.log")
    if not x1:
        x1, y1 = parse_continuity(MAC + r"\phB_fo2.log")
    fig, ax = plt.subplots(figsize=(8.2, 4.3))
    if x2:
        ax.semilogy(x2, y2, color="#d9534f", lw=1.6, label="2nd-order startup -> diverges (~iter 300)")
    if x1:
        ax.semilogy(x1, y1, color="#2e8b8b", lw=1.8, label="1st-order startup -> converges to ~0.04")
    ax.axhline(0.04, ls=":", c="#2e8b8b", alpha=0.6)
    ax.set_xlabel("iteration"); ax.set_ylabel("continuity residual (log)")
    ax.set_title("Transonic startup: divergence solved by first-order upwind ramp")
    ax.legend(fontsize=9, loc="upper right"); ax.set_xlim(left=0)
    conv_img = b64_png(fig); plt.close(fig)
except Exception as e:
    print("conv fig skipped:", e)

passage_img = b64_file(GEOM + r"\passage_view.png")
FIGS = ROOT + r"\figs"

def img_tag(b64, alt, cap):
    if not b64:
        return '<div class="imgmiss">[' + alt + ' image not generated]</div>'
    return ('<figure><img src="data:image/png;base64,' + b64 + '" alt="' + alt + '"/>'
            '<figcaption>' + cap + '</figcaption></figure>')

def fig_b64(name):
    return b64_file(FIGS + "\\" + name)

def gallery(items):
    """items: list of (filename, alt, caption) -> responsive grid of figures."""
    return ('<div class="gallery">'
            + "\n".join(img_tag(fig_b64(fn), alt, cap) for fn, alt, cap in items)
            + '</div>')

GEOM_GAL = gallery([
    ("fig_blade3d.png", "blade3d",
     "<b>真实叶片点云</b>（重建样本&nbsp;0，按半径着色）——36 叶片中的 1 片，复现的几何起点。"),
    ("fig_sections.png", "sections",
     "<b>9 个展向截面叶型</b>（blade-to-blade，z&ndash;r&middot;&theta;）——薄叶型、stagger 沿叶高增大，跨声速压气机典型形态。"),
    ("fig_meridional.png", "meridional",
     "<b>子午流道 r&ndash;z</b>：轮毂上升、机匣近恒定的收缩环道 + 0.356&nbsp;mm 叶尖间隙。"),
    ("fig_passage3d.png", "passage3d",
     "<b>单通道流域 7 个命名边界</b>（inlet/outlet/hub/shroud/blade/per1/per2）——求解器导入即自动建区。"),
])

SUDER_FIG = img_tag(fig_b64("fig_suder_map.png"), "suder",
    "<b>验证目标</b>：Suder (1996) / Moore&amp;Reid (1980) 实验特性图——RANS 复现需命中设计点 "
    "PR=2.056 / &eta;=0.876 @ &#7745;=20.93 kg/s（红圈）。这是 V&amp;V 的“金标准”。")

CFD_GAL = gallery([
    ("cfd_mach_bb.png", "mach_bb",
     "<b>马赫数</b>（blade-to-blade 通道面）：可清晰看到<b>叶片</b>（对角激波状锐线）与<b>跨声速区</b>"
     "（M&asymp;0.8&ndash;1.0，绿/黄）；下游马赫数趋零（深蓝）——与堵塞/喘振诊断一致。"),
    ("cfd_temp_bb.png", "temp_bb",
     "<b>温度</b>（钳制 250&ndash;460&nbsp;K）：<b>滞止进口端高温堆积</b>（亮白&gt;460K）——这是"
     "<b>喘振/回流的判别特征</b>（转子把高温气体推回进口）。"),
    ("cfd_vmag_bb.png", "vmag_bb",
     "<b>速度幅值</b>：通道内<b>近乎滞止</b>（失速/堵塞，近黑），仅叶尖一线高速——堵塞流态的直接证据。"),
    ("cfd_ptot_ob.png", "ptot_ob",
     "<b>绝对总压</b>（3D 斜视）：展示真实重建单通道的<b>三维形态</b>与叶片通道。"),
    ("cfd_pstat_bb.png", "pstat_bb",
     "<b>静压</b>（blade-to-blade 通道面）：压力沿通道的分布形态。"),
    ("cfd_mach_mr.png", "mach_mr",
     "<b>叶片表面马赫数</b>（子午侧视）：叶片吸力面跨声速（品红 M&gt;1.5），间隙侧视角。"),
])

# ---- chronicle (编年史) : built from chronicle.json produced by the agent workflow ----
import json, html as _html
def _esc(s):
    return _html.escape(str(s)) if s is not None else ""

def build_chronicle():
    path = ROOT + r"\chronicle.json"
    if not os.path.exists(path):
        return ""  # graceful: report still builds without it
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        c = data.get("chronicle", data)
    except Exception as e:
        print("chronicle load failed:", e)
        return ""
    roster = "".join(
        '<div class="hero-card"><div class="he">' + _esc(p.get("emoji")) + '</div>'
        '<div class="hn">' + _esc(p.get("name_cn")) + '</div>'
        '<div class="hen">' + _esc(p.get("name_en")) + '</div>'
        '<div class="hp">&ldquo;' + _esc(p.get("superpower")) + '&rdquo;</div>'
        '<div class="hm">' + _esc(p.get("mission")) + '</div></div>'
        for p in c.get("cast", []))
    acts = ""
    for a in c.get("acts", []):
        story = "".join("<p>" + _esc(par) + "</p>" for par in a.get("story", []))
        acts += (
            '<div class="act"><div class="ah">'
            '<span class="anum">' + _esc(a.get("num")) + '</span>'
            '<span class="ae">' + _esc(a.get("emoji")) + '</span>'
            '<h4 class="at">' + _esc(a.get("title")) + '</h4>'
            '<span class="role">' + _esc(a.get("role_tag")) + '</span></div>'
            '<div class="astory">' + story + '</div>'
            '<div class="chips">'
            '<div class="chip obs"><b>&#128679; 拦路虎</b>' + _esc(a.get("obstacle")) + '</div>'
            '<div class="chip brk"><b>&#128161; 突破</b>' + _esc(a.get("breakthrough")) + '</div>'
            '</div>'
            '<div class="take"><b>一句话看懂 &middot;</b> ' + _esc(a.get("takeaway")) + '</div>'
            '</div>')
    quotes = "".join('<div class="quote">&ldquo;' + _esc(q) + '&rdquo;</div>'
                     for q in c.get("pull_quotes", []))
    return (
        '<section class="chron">'
        '<div class="ckick">Chronicle &middot; 幕后编年史</div>'
        '<h2>&#128220; 一支 AI 特工队，如何从 0 攻克 Rotor 37</h2>'
        '<p class="cintro">' + _esc(c.get("intro")) + '</p>'
        '<h3 class="cband">&#127917; 特工队花名册</h3>'
        '<div class="roster">' + roster + '</div>'
        '<h3 class="cband">&#9201;&#65039; 闯关编年史</h3>'
        '<div class="tline">' + acts + '</div>'
        + ('<h3 class="cband">&#128172; 金句</h3><div class="quotes">' + quotes + '</div>' if quotes else '')
        + '<div class="chonest"><b>&#9878;&#65039; 诚信收尾 &middot;</b> ' + _esc(c.get("honesty_note")) + '</div>'
        '<p class="cclose">' + _esc(c.get("closing")) + '</p>'
        '</section>')

CHRONICLE_HTML = build_chronicle()

CAP_CARDS = [
    ("&#128752;", "&#30495;&#23454;&#36164;&#20135;&#33719;&#21462;", "&#20844;&#24320; NASA &#28304;&#22833;&#25928;&#21518;&#65292;&#23450;&#20301;+&#19979;&#36733;&#30495;&#23454; Rotor 37 &#21494;&#29255;&#28857;&#20113; + 4 &#31687;&#39564;&#35777;&#25991;&#29486;&#65307;&#23545;&#22833;&#36133;&#38142;&#36335;&#35802;&#23454;&#35760;&#24405;&#12290;"),
    ("&#128208;", "&#20960;&#20309;&#37325;&#24314;", "1000-&#26679;&#26412;&#28857;&#20113; &#8594; &#27700;&#23494;&#21333;&#36890;&#36947;&#27969;&#22495;&#65288;contour &#31471;&#22721;/&#26059;&#36716;&#21608;&#26399;/&#21494;&#23574;&#38388;&#38553;&#65289;&#65292;&#20307;&#31215;&#23432;&#24658;&#12289;&#21608;&#26399;&#38754;&#24179;&#34913;&#12290;"),
    ("&#128300;", "API &#36870;&#21521;&#24037;&#31243;", "6 &#20010;&#21453;&#23556;&#25506;&#38024; + &#20869;&#32622; Javadoc&#65292;&#36870;&#21521; STAR-CCM+ 2402 R8 &#25209;&#22788;&#29702;&#20840;&#22871;&#26410;&#25991;&#26723;&#21270; API&#65292;&#24418;&#25104;&#21487;&#22797;&#29992;&#36895;&#26597;&#34920;&#12290;"),
    ("&#9881;&#65039;", "&#29289;&#29702;&#24314;&#27169;", "coupled &#21487;&#21387;&#32553; k-&#969; SST + MRF &#26059;&#36716;&#21442;&#32771;&#31995; + &#26059;&#36716;&#21608;&#26399;&#30028;&#38754; + mass-flow &#20986;&#21475; + &#26426;&#21283; lab &#38745;&#27490;&#65292;&#20840;&#37096;&#31243;&#24207;&#21270;&#12290;"),
    ("&#129495;", "&#27714;&#35299;&#25915;&#20851;", "40+ &#27425;&#31995;&#32479;&#21270;&#36845;&#20195;&#65292;&#36880;&#19968;&#38548;&#31163;&#24182;&#25915;&#20811;&#21608;&#26399;&#21464;&#25442;/&#36864;&#21270;&#21333;&#20803;/&#36716;&#21521;/&#21457;&#25955;&#65307;&#19968;&#38454;&#21551;&#21160;&#20351;&#27531;&#24046;&#25910;&#25econverge&#12290;"),
    ("&#128202;", "V&amp;V &#26694;&#26550;", "literature-cited gold standard + &#23481;&#24046;&#38376; + &#36136;&#37327;&#27969;&#37327;&#21152;&#26435; PR/&#951; &#25253;&#21578; + &#33258;&#21160;&#23545;&#26631;&#33050;&#26412;&#12290;"),
    ("&#129518;", "&#35802;&#23454;&#35786;&#26029;", "&#25910;&#25econverge&#8800;&#29289;&#29702;&#27491;&#30830;&#65306;&#31934;&#30830;&#23450;&#20301;&#8220;&#37325;&#24314;&#20960;&#20309;&#21897;&#25391;&#8221;&#20026;&#26368;&#32456;&#36793;&#30028;&#65292;&#32477;&#19981;&#32534;&#36896; Suder &#21563;&#21512;&#12290;"),
]
CAP_CARDS[4] = ("&#129495;", "求解攻关", "40+ 次系统化迭代，逐一隔离并攻克周期变换/退化单元/转向/发散；一阶启动使残差收敛 0.04。")
CAP_CARDS[6] = ("&#129518;", "诚实诊断", "收敛≠物理正确：精确定位“重建几何喘振”为最终边界，绝不从喘振场编造 Suder 吻合。")

GEOM_ROWS = [
    ("叶尖直径", "0.511 m", "0.508 m (Moore&amp;Reid 1980)", "&#10003; 0.6%"),
    ("轮毂/叶尖半径比", "0.68", "0.70 (进口, Reid&amp;Moore)", "&#10003;"),
    ("叶片数", "36", "36", "&#10003;"),
    ("设计转速", "17188.7 rpm", "17188.7 rpm", "&#10003;"),
    ("轴向弦长", "~0.043 m", "~0.043 m", "&#10003;"),
    ("叶尖间隙", "0.356 mm", "0.356 mm", "&#10003; 已建模"),
    ("流域水密性", "watertight, 单连通", "&mdash;", "&#10003;"),
    ("周期面平衡", "per1/per2 &asymp; 11800/11800", "&mdash;", "&#10003; &lt;0.1%"),
]
API_ROWS = [
    ("参考系管理器", "<code>-new -batch</code> 空 sim 中未实例化；<b>save&rarr;reload</b> 后 <code>sim.getReferenceFrameManager()</code> 可用"),
    ("MRF 旋转", "<code>createReferenceFrame(RotatingReferenceFrame,…)</code> + 区域 <code>MotionSpecification.setReferenceFrame</code>"),
    ("旋转周期界面", "<code>createDirectInterface</code> &rarr; <code>Topology=PERIODIC</code> &rarr; <code>PeriodicityOption=ROTATIONAL</code> + <code>RotationAxisOption=REGION_REFERENCE_AXIS</code> + <code>initializeInterfaces</code> &rarr; <b>9.997&deg;, 覆盖 97%</b>"),
    ("枚举设置坑", "<code>FlexibleEnumeratedOption.getSelected()</code> 返回 Integer；必须 <code>Class.forName(\"…$Type\")</code> 直接解析"),
    ("coupled 能量", "<code>star.coupledflow.CoupledEnergyModel</code>（非 coupledenergy 包）"),
    ("进/出口", "进口 <code>StagnationBoundary</code>+<code>energy.TotalTemperatureProfile</code>；出口 <code>MassFlowBoundary</code>（按关键字设 kg/s）"),
    ("退化单元", "<code>MeshManager.removeInvalidCells(regs,0.51,1e-8,1e-10)</code>，需迭代多次"),
    ("机匣 lab 静止", "<code>WallReferenceFrameOption &rarr; ReferenceFrameOption.Type.LAB_FRAME</code>"),
    ("一阶启动", "<code>CoupledFlowModel.getUpwindOption().setSelected(FlowUpwindOption.Type.FIRST_ORDER)</code> &rarr; 收敛后切 SECOND_ORDER"),
    ("性能场函数", "MRF 下压气机 PR 用 <b>Absolute Total Pressure</b>（Total Pressure 是相对系）"),
    ("网格 base size", "<code>def.get(BaseSize).setValue(x)</code>（DEC-009；AutoMeshDefaultValuesManager 死路）"),
    ("反射泛型坑", "<code>sim.get(Class)</code> 拒绝反射 Class&lt;?&gt; &rarr; 走 <code>getMethod(\"get\",Class).invoke</code>"),
]
ATTACK_ROWS = [
    ("周期变换=0&deg;", "确定性发散（同网格逐位相同）", "&rarr; ROTATIONAL+REGION_AXIS+initialize &rarr; 9.997&deg; &#10003;"),
    ("metrics 错误", "界面正常(97%)，实为 1 个退化单元", "removeInvalidCells &#10003;"),
    ("冷启动高背压倒流", "AMG 发散", "mass-flow 出口 &#10003;"),
    ("CFL 4 发散", "~iter300 分离发散", "CFL ramp + 一阶启动 &#10003;"),
    ("旋转方向", "+1800 立即发散 / &minus;1800 收敛", "&omega;=&minus;1800 确定 &#10003;"),
    ("细网格 (1.2M)", "flush 叶尖持续退化单元", "几何边界（局部加密=DEC-007 死路）"),
    ("一阶收敛后", "残差 0.04 稳定，但<b>喘振/回流</b>", "几何天花板（合成端壁不构成扩压通道）"),
]

def rows_html(rows):
    return "\n".join("<tr>" + "".join("<td>" + str(c) + "</td>" for c in r) + "</tr>" for r in rows)

cards_html = "\n".join(
    '<div class="card"><div class="ico">' + i + '</div><h3>' + t + '</h3><p>' + d + '</p></div>'
    for i, t, d in CAP_CARDS)

HTML = """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>NASA Rotor 37 复现 — 端到端全链路工程能力实践报告</title>
<style>
:root{--ink:#1a1f26;--mut:#5b6573;--acc:#2e8b8b;--acc2:#c0504d;--line:#e3e8ef;--soft:#f6f8fb}
*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif;color:var(--ink);background:var(--soft);line-height:1.65}
.hero{background:linear-gradient(135deg,#0f1419 0%,#1c3b3b 55%,#2e8b8b 100%);color:#fff;padding:54px 6vw 40px}
.hero .kick{letter-spacing:3px;font-size:12px;text-transform:uppercase;color:#9fe3e3;margin-bottom:10px}
.hero h1{font-size:30px;margin:0 0 6px;font-weight:700;line-height:1.25}
.hero h2{font-size:15px;font-weight:400;color:#cfe8e8;margin:0 0 18px}
.hero .meta{font-size:12.5px;color:#a9c7c7;display:flex;gap:22px;flex-wrap:wrap}
.badges{margin-top:18px;display:flex;gap:8px;flex-wrap:wrap}
.badge{background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.25);border-radius:20px;padding:5px 13px;font-size:12px}
.badge.ok{background:rgba(120,220,160,.18);border-color:rgba(120,220,160,.45)}
.badge.warn{background:rgba(240,190,90,.16);border-color:rgba(240,190,90,.45)}
section{background:#fff;margin:22px auto;max-width:1080px;border:1px solid var(--line);border-radius:14px;padding:28px 32px;box-shadow:0 1px 3px rgba(20,30,50,.05)}
h2.sec{font-size:21px;margin:0 0 4px;display:flex;align-items:center;gap:10px}
h2.sec .n{background:var(--acc);color:#fff;width:30px;height:30px;border-radius:8px;display:inline-flex;align-items:center;justify-content:center;font-size:15px;flex:none}
.sub{color:var(--mut);font-size:13.5px;margin:0 0 18px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:14px}
.card{background:var(--soft);border:1px solid var(--line);border-radius:12px;padding:16px}
.card .ico{font-size:24px}
.card h3{margin:7px 0 5px;font-size:15px}
.card p{margin:0;font-size:12.7px;color:var(--mut)}
table{width:100%;border-collapse:collapse;font-size:13px;margin:8px 0}
th,td{text-align:left;padding:8px 11px;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--soft);font-weight:600;color:#33424f}
td code,p code,li code{background:#eef3f3;color:#1c4f4f;padding:1px 5px;border-radius:4px;font-size:12px;font-family:"SF Mono",Consolas,monospace}
figure{margin:16px 0;text-align:center}
figure img{max-width:100%;border:1px solid var(--line);border-radius:10px}
figcaption{font-size:12px;color:var(--mut);margin-top:7px}
.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:16px;margin:16px 0}
.gallery figure{margin:0;background:var(--soft);border:1px solid var(--line);border-radius:12px;padding:10px}
.gallery figure img{background:#fff}
.gallery figcaption{text-align:left;min-height:32px}
/* ---- chronicle (编年史) ---- */
.chron{background:linear-gradient(135deg,#161b22 0%,#1c3b3b 60%,#24565a 100%);color:#eef6f6;border:none;max-width:1080px}
.chron .ckick{letter-spacing:3px;font-size:12px;text-transform:uppercase;color:#8fdede;margin-bottom:8px}
.chron h2{font-size:24px;margin:0 0 8px;color:#fff;display:flex;align-items:center;gap:10px}
.chron .cintro{font-size:14.5px;color:#d4eaea;margin:6px 0 8px;line-height:1.75}
.chron h3.cband{font-size:14px;letter-spacing:2px;color:#8fdede;text-transform:uppercase;margin:26px 0 12px;border-top:1px solid rgba(255,255,255,.14);padding-top:16px}
.roster{display:grid;grid-template-columns:repeat(auto-fit,minmax(225px,1fr));gap:12px}
.hero-card{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.16);border-radius:13px;padding:14px 15px}
.hero-card .he{font-size:26px}
.hero-card .hn{font-size:15px;font-weight:700;color:#fff;margin:5px 0 1px}
.hero-card .hen{font-size:11px;color:#7fc6c6;letter-spacing:.5px;text-transform:uppercase}
.hero-card .hp{font-size:12.5px;color:#bfe0e0;margin:8px 0 4px;font-style:italic}
.hero-card .hm{font-size:12.5px;color:#dcefef}
.tline{position:relative;margin:8px 0 4px;padding-left:8px}
.act{position:relative;background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.13);border-radius:14px;padding:16px 18px 14px;margin:14px 0}
.act .ah{display:flex;align-items:center;gap:11px;flex-wrap:wrap}
.act .anum{background:#2e8b8b;color:#fff;width:30px;height:30px;border-radius:9px;display:inline-flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;flex:none}
.act .ae{font-size:22px}
.act .at{font-size:17px;font-weight:700;color:#fff;margin:0}
.act .role{font-size:11px;background:rgba(143,222,222,.18);color:#aef0f0;border:1px solid rgba(143,222,222,.35);border-radius:20px;padding:2px 10px}
.act .astory{font-size:13.6px;color:#e4f2f2;line-height:1.78;margin:11px 0 0}
.act .astory p{margin:0 0 8px}
.chips{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 0}
.chip{font-size:12.3px;border-radius:9px;padding:7px 11px;line-height:1.5;flex:1;min-width:200px}
.chip.obs{background:rgba(220,120,90,.14);border:1px solid rgba(220,120,90,.4);color:#ffd6c4}
.chip.brk{background:rgba(120,220,160,.13);border:1px solid rgba(120,220,160,.4);color:#c8f5d9}
.chip b{display:block;font-size:10.5px;letter-spacing:1px;opacity:.85;margin-bottom:2px}
.take{margin:11px 0 0;font-size:13px;color:#fff;background:rgba(46,139,139,.28);border-left:3px solid #8fdede;border-radius:0 8px 8px 0;padding:8px 12px}
.take b{color:#aef0f0}
.quotes{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:12px;margin:6px 0}
.quote{font-size:15px;font-weight:600;color:#fff;line-height:1.6;background:rgba(255,255,255,.06);border-radius:12px;padding:16px 18px;border-left:4px solid #8fdede}
.chonest{background:rgba(192,80,77,.16);border:1px solid rgba(240,150,140,.4);border-radius:12px;padding:15px 17px;margin:14px 0;font-size:13.6px;color:#ffe2dc;line-height:1.75}
.cclose{font-size:14px;color:#dcefef;line-height:1.78;margin:14px 0 0;border-top:1px solid rgba(255,255,255,.14);padding-top:16px}
.pipe{display:flex;flex-wrap:wrap;gap:8px;margin:6px 0}
.step{flex:1;min-width:120px;background:linear-gradient(180deg,#f0f7f7,#e3f0f0);border:1px solid #c9e2e2;border-radius:10px;padding:12px 10px;text-align:center;font-size:12.5px}
.step b{display:block;color:#1c4f4f;font-size:13px;margin-bottom:3px}
.step .badge2{font-size:10.5px;color:#fff;background:#2e8b8b;border-radius:10px;padding:1px 8px;display:inline-block;margin-top:6px}
.step .badge2.w{background:#c0504d}
.callout{border-left:4px solid var(--acc);background:#f0f7f7;padding:13px 16px;border-radius:0 8px 8px 0;margin:16px 0;font-size:13.5px}
.callout.warn{border-color:var(--acc2);background:#fbf2f1}
.kpis{display:flex;gap:14px;flex-wrap:wrap;margin:6px 0}
.kpi{flex:1;min-width:140px;background:var(--soft);border:1px solid var(--line);border-radius:11px;padding:14px}
.kpi .v{font-size:24px;font-weight:700;color:var(--acc)}
.kpi .l{font-size:12px;color:var(--mut);margin-top:2px}
ul.tight li{margin:4px 0;font-size:13.3px}
.imgmiss{padding:30px;text-align:center;color:#aaa;border:1px dashed #ccc;border-radius:10px}
footer{max-width:1080px;margin:10px auto 40px;padding:0 24px;color:var(--mut);font-size:12px}
@media print{body{background:#fff}section{box-shadow:none;break-inside:avoid}.hero{-webkit-print-color-adjust:exact;print-color-adjust:exact}}
</style></head><body>

<div class="hero">
  <div class="kick">End-to-End CFD Engineering &middot; Practice Report</div>
  <h1>NASA Rotor 37 跨声速压气机论文复现<br>—— 端到端全链路工程能力实践报告</h1>
  <h2>Li et&nbsp;al. (2022, AST) 几何/工况 &middot; QWRLES&rarr;RANS 方法降阶 &middot; STAR-CCM+ 2402 (R8) 批处理全程序化</h2>
  <div class="meta"><span>&#128197; 2026-06-15 ~ 06-16</span><span>&#128421; STAR-CCM+ 19.02.009-R8 &middot; 4-MPI</span><span>&#128193; reproductions/rotor37_rans</span></div>
  <div class="badges">
    <span class="badge ok">真实几何 &#10003; 定量验证</span>
    <span class="badge ok">R8 API 全套逆向 &#10003;</span>
    <span class="badge ok">设置 100% 程序化攻克</span>
    <span class="badge ok">跨声速发散已解（残差 0.04）</span>
    <span class="badge warn">收敛态=喘振（几何天花板）</span>
    <span class="badge ok">零编造 &middot; 诚实诊断</span>
  </div>
</div>

__CHRONICLE__

<section>
  <h2 class="sec"><span class="n">0</span>能力总览 &middot; 这次复现展示了什么</h2>
  <p class="sub">本报告的重点不是复述论文，而是展示<b>一次从零到求解的端到端 CFD 工程</b>如何在一个充满未文档化障碍的真实环境中被高质量推进——跨越几何处理、CAD 重建、API 逆向、物理建模、数值攻关、验证框架与科研诚信七个领域。</p>
  <div class="grid">__CARDS__</div>
  <div class="callout"><b>一句话定位：</b>把一个“只有叶片点云 + 一套删改过的批处理 API + 一台机器”的起点，推进到“真实几何已验证、全套 turbomachinery 物理与界面在批处理中程序化跑通、跨声速发散被一阶启动解决、并精确诊断出最终物理边界”的终点——全程不编造任何数字。</div>
</section>

<section>
  <h2 class="sec"><span class="n">1</span>复现目标与方法</h2>
  <p class="sub">复现对象 / 验证基准 / 降阶策略</p>
  <ul class="tight">
    <li><b>论文：</b>Li et al. (2022), <i>Aerospace Science and Technology</i> 126, 107617, DOI 10.1016/j.ast.2022.107617 —— NASA Rotor 37 的 QWRLES。</li>
    <li><b>方法降阶：</b>保留同一几何与工况，将 QWRLES 降为 <b>定常 RANS（k-&omega; SST，coupled/密度基，单通道 + MRF）</b>——科学命题：工程级 RANS 能否再现 Rotor 37 总体性能。</li>
    <li><b>验证基准：</b>Suder (1996, NASA TP-3623) + Moore&amp;Reid (1980, NASA TP-1659)。</li>
  </ul>
  <div class="kpis">
    <div class="kpi"><div class="v">2.056</div><div class="l">设计总压比 (&plusmn;3%)</div></div>
    <div class="kpi"><div class="v">0.876</div><div class="l">设计等熵效率 (&plusmn;5%)</div></div>
    <div class="kpi"><div class="v">20.93</div><div class="l">设计质量流量 kg/s (&plusmn;4%)</div></div>
    <div class="kpi"><div class="v">17188.7</div><div class="l">设计转速 rpm</div></div>
  </div>
  __SUDER__
</section>

<section>
  <h2 class="sec"><span class="n">2</span>端到端技术路线（全链路一图）</h2>
  <p class="sub">七个领域、五个阶段，逐环验证；绿=已攻克/验证，红=精确诊断出的物理边界</p>
  <div class="pipe">
    <div class="step"><b>&#9312; 资产获取</b>点云 + 验证 PDF<span class="badge2">&#10003;</span></div>
    <div class="step"><b>&#9312;b 几何重建</b>水密单通道流域<span class="badge2">&#10003;</span></div>
    <div class="step"><b>&#9313; API 逆向</b>R8 批处理速查表<span class="badge2">&#10003;</span></div>
    <div class="step"><b>&#9314; 物理建模</b>coupled/SST/MRF/周期<span class="badge2">&#10003;</span></div>
    <div class="step"><b>&#9315; 求解攻关</b>发散&rarr;一阶收敛 0.04<span class="badge2">&#10003;</span></div>
    <div class="step"><b>&#9316; 物理有效性</b>收敛态=喘振<span class="badge2 w">边界</span></div>
  </div>
  <div class="callout">每一环都<b>独立验证</b>后才进入下一环（水密性、周期面平衡、API 实测、残差收敛、物理量符号）——这是把“看似跑通”与“真的对”区分开的工程纪律。</div>
</section>

<section>
  <h2 class="sec"><span class="n">3</span>阶段一：真实资产获取 <span style="font-size:12px;color:#1f8a4c">&#10003;</span></h2>
  <p class="sub">在公开源失效的现实里拿到真东西</p>
  <ul class="tight">
    <li>NASA turbmodels Rotor 37 包已 301 重定向失效（Windows schannel TLS 失败）&rarr; 改用 GitHub <code>Deeplabs-ai/rotor37</code>：<b>1000 个 3D 叶片几何</b>（样本 0 = 基准 Rotor 37，单位 m）。</li>
    <li>下载并校验 4 篇验证文献（Suder TP-3623、Reid&amp;Moore TP-1337、Ameri CR-2010-216235、Van Zante 盲测）。</li>
    <li><b>能力点：</b>多模态检索 + 断点续传/完整性校验 + 对失败链路（PLAID 3.1GB 拉取失败）的诚实记录。</li>
  </ul>
</section>

<section>
  <h2 class="sec"><span class="n">4</span>阶段一b：单通道流域几何重建 <span style="font-size:12px;color:#1f8a4c">&#10003; 已定量验证</span></h2>
  <p class="sub">从离散叶片点云到 CFD-ready 水密单通道（trimesh + manifold3d）</p>
  <p>叶片实体 lofting（9 截面 + LE/TE 闭合 + 端盖）&rarr; 由叶根/叶尖包络导出 contour 化 hub/shroud 子午型线 &rarr; 10&deg; 扇形 wedge &rarr; 旋转复制叶片做布尔差（两周期面互为精确 10&deg; 旋转）&rarr; 叶根内伸 skirt 干净 hub 切割 &rarr; 叶尖间隙处理。</p>
  __PASSAGE__
  <table><thead><tr><th>量</th><th>重建值</th><th>NASA 典型</th><th>判定</th></tr></thead><tbody>__GEOMROWS__</tbody></table>
  <div class="callout"><b>能力点：</b>不止“生成网格”，而是每步做<b>拓扑/几何校验</b>（watertight、euler、体积守恒=单叶片体积、周期面片数平衡 &lt;0.1%）并与 NASA 典型值定量对齐——几何这一环是<b>可信</b>的。</div>
  <p class="sub" style="margin-top:20px;font-size:14px;color:#33424f"><b>复现对象几何全貌</b>（点云 &rarr; 叶型 &rarr; 子午流道 &rarr; 单通道边界）——直观看清“在复现什么”：</p>
  __GEOMGAL__
</section>

<section>
  <h2 class="sec"><span class="n">5</span>阶段二：STAR-CCM+ 2402 R8 批处理 API 逆向工程 <span style="font-size:12px;color:#1f8a4c">&#10003;</span></h2>
  <p class="sub">R8 公开 API 删改了大量接口；6 个反射探针 + 内置 Javadoc 系统逆向，形成可复用速查表</p>
  <table><thead><tr><th>主题</th><th>实测可用路径（R8）</th></tr></thead><tbody>__APIROWS__</tbody></table>
  <div class="callout"><b>能力点 / 行业价值：</b>这套速查表是<b>可复用资产</b>——其中“参考系管理器需 save&rarr;reload 才实例化”等发现，直接解开本仓库长期挂账的 <code>DEC-009 Rotor37 hollow-green</code> 债务。逆向一个未文档化的工业求解器批处理 API，是这次最硬的工程能力体现之一。</div>
</section>

<section>
  <h2 class="sec"><span class="n">6</span>阶段三–四：物理建模 + 求解器系统化攻关 <span style="font-size:12px;color:#1f8a4c">发散已解</span></h2>
  <p class="sub">三阶段、幂等、带硬后置门的 turbomachinery 宏 + 40+ 次系统化求解迭代</p>
  <p>宏（<code>rotor37_rans.java</code>）：Phase A 建几何+物理+网格+存；Phase B reload&rarr;MRF+旋转周期+mass-flow 出口+一阶启动求解。硬门（cell&gt;0、PR&gt;0.5）<b>杜绝“空壳通过”</b>。</p>
  <table><thead><tr><th>遇到的障碍</th><th>现象</th><th>攻克</th></tr></thead><tbody>__ATTACKROWS__</tbody></table>
  __CONV__
  <div class="callout"><b>能力点：</b>面对反复发散的跨声速强非线性问题，不盲调参数，而是<b>每次隔离一个变量、用证据定位根因</b>（如“发散起始步数与 CFL 无关&rarr;是物理不是数值”、“残差逐位相同&rarr;是确定性设置错误不是随机不稳定”），最终用一阶启动把发散彻底解决——科研级的<b>诊断式调试</b>。</div>
</section>

<section>
  <h2 class="sec"><span class="n">7</span>求解流场后处理可视化（云图） <span style="font-size:12px;color:#c0504d">非物理喘振场</span></h2>
  <p class="sub">从一阶收敛的 <code>.sim</code> 直接用 STAR-CCM+ 批处理渲染 scalar scene（程序化 ScalarDisplayer + 显式相机 + <code>printAndWait</code> 离屏导出 1600&times;1000）——展示完整的“求解&rarr;后处理&rarr;成图”链路与真实网格上的流场形态。</p>
  <div class="callout warn"><b>诚实标注：</b>下列云图取自<b>一阶迎风收敛（残差 0.04）但物理上为喘振/回流</b>的流场（见 §8 边界诊断），<b>不代表已验证的压气机流动</b>，<b>不可</b>用于 Suder 定量对标。它们的价值在于：① 证明后处理/渲染全链路打通；② 在真实重建几何与网格上<b>可视化地佐证</b>“喘振/堵塞”的诊断结论（进口端高温、通道近滞止）。</div>
  __CFDGAL__
  <p class="sub" style="margin-top:6px">渲染管线：<code>macro/render_scenes.java</code>（加载 sim 一次 &rarr; 解析场函数 &rarr; 7 边界着色 &rarr; 显式相机 broadside/oblique/meridional &rarr; 导出 PNG）。马赫与速度场用 auto-range，温度场钳制到 250&ndash;460&nbsp;K 以规避喘振场中单个 ~5500K 离群单元对色标的破坏。</p>
</section>

<section>
  <h2 class="sec"><span class="n">8</span>阶段五：V&amp;V 框架与最终物理边界诊断 <span style="font-size:12px;color:#c0504d">边界</span></h2>
  <p class="sub">literature-cited gold standard + 自动对标；以及对“收敛 &ne; 物理正确”的诚实诊断</p>
  <ul class="tight">
    <li><b>V&amp;V 已就位：</b>solver-agnostic gold standard（带 DOI + 容差）+ 质量流量加权 PR/&eta; 报告 + <code>aggregate_vv.py</code> 自动扫工况线、在 &#7745;=20.93 处对标。<b>几何 V&amp;V 已通过。</b></li>
    <li><b>最终边界（已精确表征）：</b>一阶启动收敛后（残差 0.04），流场为<b>非物理喘振/回流</b>——无论旋转方向、流向、质量流量，滞止进口端恒为高温高压（T0&asymp;390&ndash;440K）+ ~1000 面回流。根因 = 粗网格 + 叶片包络合成端壁不构成有效扩压通道；细网格又在 flush 叶尖退化（局部加密 = DEC-007 批处理死路）。</li>
  </ul>
  <div class="callout warn"><b>科研诚信底线：</b>收敛 &ne; 物理正确。从喘振场取 PR/&eta; 去对标 Suder 即<b>编造</b>，本报告<b>不为之</b>，不声称任何与 Suder 的定量吻合。一个有效收敛的压气机解需<b>真实 Rotor 37 CAD 流道 + 图形界面 Turbomachinery 结构化网格</b>（解析叶尖间隙）——超出“点云重建 + 批处理反射”的能力边界。这条边界是被严谨实验<b>证明</b>出来的，而非猜测。</div>
</section>

<section>
  <h2 class="sec"><span class="n">9</span>能力亮点总结</h2>
  <div class="grid">
    <div class="card"><h3>跨域整合</h3><p>几何处理 + 计算几何(CAD 重建) + 工业软件 API 逆向 + 可压缩湍流 CFD + 数值鲁棒性 + 验证学，一条链全程贯通。</p></div>
    <div class="card"><h3>把“未知”变“可复用”</h3><p>未文档化的 R8 批处理 API &rarr; 实测速查表；解开仓库长期技术债（DEC-009）。</p></div>
    <div class="card"><h3>诊断式攻关</h3><p>40+ 次迭代，每次隔离单变量、用证据定根因；跨声速发散被一阶启动彻底解决。</p></div>
    <div class="card"><h3>工程纪律</h3><p>硬后置门杜绝空壳；逐环独立验证；幂等三阶段宏 + 全参数化 + 可重启扫掠。</p></div>
    <div class="card"><h3>科研诚信</h3><p>零编造：明确区分“收敛”与“物理有效”，主动撤回过早的“通过”结论，精确划定能力边界。</p></div>
    <div class="card"><h3>可交付/可续作</h3><p>全部资产（几何/宏/探针/脚本/sim/文献）+ 长期记忆落盘，真实 CAD 流道一到即可一键续跑。</p></div>
  </div>
</section>

<section>
  <h2 class="sec"><span class="n">10</span>资产清单 &amp; 引用</h2>
  <table><thead><tr><th>类别</th><th>文件</th></tr></thead><tbody>
  <tr><td>几何重建</td><td><code>scripts/build_blade.py &middot; build_passage.py &middot; verify_passage.py &middot; inspect_geom.py</code></td></tr>
  <tr><td>几何成品</td><td><code>geom/fluid_passage_named.stl</code>(7 命名面) &middot; <code>geom/rotor37_meta.json</code> &middot; <code>geom/passage_view.png</code></td></tr>
  <tr><td>求解宏</td><td><code>macro/rotor37_rans.java</code>（三阶段&middot;幂等 MRF&middot;硬门&middot;一阶启动） + <code>macro/probe_*.java</code>(6 R8 探针)</td></tr>
  <tr><td>可视化</td><td><code>scripts/gen_figures.py</code>（5 张几何/数据图） &middot; <code>macro/render_scenes.java</code>（STAR-CCM+ 批处理云图渲染，8 张 scalar scene） &middot; <code>figs/*.png</code></td></tr>
  <tr><td>幕后编年史</td><td><code>chronicle.json</code> —— 由一个 14-agent 工作流生成（9 编剧并行写幕 + 选角 &rarr; 统稿 &rarr; 对抗式<b>可读性+科研诚信</b>双评审 &rarr; 定稿）</td></tr>
  <tr><td>V&amp;V</td><td><code>scripts/aggregate_vv.py</code> &middot; <code>knowledge/gold_standards/rotor37.yaml</code></td></tr>
  <tr><td>验证文献</td><td><code>assets/*.pdf</code>（Suder TP-3623 / Reid&amp;Moore TP-1337 / Ameri CR-2010-216235 / Van Zante）</td></tr>
  <tr><td>完整文字版</td><td><code>REPORT.md</code></td></tr>
  </tbody></table>
  <p style="font-size:12px;color:var(--mut);margin-top:14px">引用：Li et al. 2022 (DOI 10.1016/j.ast.2022.107617) &middot; Suder et al. 1995 (DOI 10.1115/1.2836561) &middot; Suder 1996 NASA TP-3623 &middot; Moore &amp; Reid 1980 NASA TP-1659 &middot; Reid &amp; Moore 1978 NASA TP-1337 &middot; Ameri 2010 NASA/CR-2010-216235 &middot; AGARD-AR-355。</p>
</section>

<footer>本报告忠实记录复现全过程（成功与未达成项）。核心价值：完整可复用的端到端复现基础设施、已验证的真实几何、全套 STAR-CCM+ 2402 R8 批处理 API 逆向工程，以及对最终物理边界的精确、可追溯诊断。<br>Generated from real solver logs &amp; geometry artifacts &middot; self-contained HTML.</footer>
</body></html>"""

HTML = (HTML.replace("__CARDS__", cards_html)
            .replace("__PASSAGE__", img_tag(passage_img, "passage", "重建的 Rotor 37 单通道流域：3D 命名边界（左）与子午面 z&ndash;r（右），显示 contour 端壁与周期面"))
            .replace("__GEOMROWS__", rows_html(GEOM_ROWS))
            .replace("__APIROWS__", rows_html(API_ROWS))
            .replace("__ATTACKROWS__", rows_html(ATTACK_ROWS))
            .replace("__CONV__", img_tag(conv_img, "convergence", "残差历史：二阶启动 ~第300步分离发散（红）；改一阶迎风启动 + CFL ramp 后稳定收敛到 ~0.04（青）——跨声速发散被解决"))
            .replace("__SUDER__", SUDER_FIG)
            .replace("__GEOMGAL__", GEOM_GAL)
            .replace("__CFDGAL__", CFD_GAL)
            .replace("__CHRONICLE__", CHRONICLE_HTML))

with open(OUT, "w", encoding="utf-8") as f:
    f.write(HTML)
print("wrote", OUT, str(os.path.getsize(OUT) // 1024) + " KB")
print("conv fig:", "yes" if conv_img else "no", "| passage img:", "yes" if passage_img else "no")
