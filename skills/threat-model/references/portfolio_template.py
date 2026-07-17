#!/usr/bin/env python3
"""Portfolio / chain-of-models META-view template.

Same product family as the per-product dashboard: reuses that template's exact theme (`CSS`) so the
palette, typography, motion, and dark/light system are byte-for-byte consistent. Adds only the meta-view:
a portfolio posture header, a deterministic "map of chained models", aggregate severity, a riskiest-product
ranking, a member-card grid that drills DOWN into each product's own dashboard, grounded cross-product
analytics (shared CWE / ATT&CK / STRIDE), and the declared-relationship + dropped-edge (grounding) panels.

Presentation is deterministic; content is the members' emitted facts. Blanks are first-class.
"""
import json, os, sys, html, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # resolve dashboard_template as a sibling
from dashboard_template import CSS as DASH_CSS  # reuse the exact per-product theme

SEV_ORDER = ("CRITICAL", "HIGH", "MEDIUM", "LOW")


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def posture_class(band):
    return {"CRITICAL": "crit", "HIGH RISK": "high", "ELEVATED": "high",
            "MODERATE": "med", "LOW": "low", "NO FINDINGS": "none"}.get(band, "med")


def sev_bar(sev, total=None):
    total = total or sum(sev.values()) or 1
    segs = "".join(
        f'<span class="sb sb-{k.lower()}" style="flex:{sev[k]}" title="{k}: {sev[k]}"></span>'
        for k in SEV_ORDER if sev[k])
    return f'<div class="sevbar">{segs or "<span class=sb-empty></span>"}</div>'


# ---------------------------------------------------------------------------
# The MAP of chained models — deterministic circular layout. Product nodes sized by findings, coloured by
# posture; edges are declared structural links (solid, typed) + derived taxonomy-affinity (dashed, weighted
# by shared CWE/ATT&CK). Node ids = run ids -> click cross-filters the whole view (the meta pivot key).
# ---------------------------------------------------------------------------

def sec_map(m):
    members = m["members"]
    n = len(members)
    W, H, cx, cy = 760, 440, 380, 220
    R = 150 if n > 1 else 0
    pos = {}
    for i, mem in enumerate(members):
        ang = -math.pi / 2 + 2 * math.pi * i / max(n, 1)
        pos[mem["run_id"]] = (round(cx + R * math.cos(ang), 1), round(cy + R * math.sin(ang), 1))
    # edges
    edge_svg = []
    for e in m["map_edges"]:
        a, b = pos.get(e["a"]), pos.get(e["b"])
        if not a or not b:
            continue
        if e["kind"] == "declared":
            edge_svg.append(
                f'<line class="me me-declared" data-a="{esc(e["a"])}" data-b="{esc(e["b"])}" '
                f'x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}">'
                f'<title>{esc(e.get("type"))}: {esc(e.get("note"))}</title></line>')
        else:
            w = 1 + min(e["cwe"] + e["mitre"], 6)
            edge_svg.append(
                f'<line class="me me-affinity" data-a="{esc(e["a"])}" data-b="{esc(e["b"])}" '
                f'x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" style="stroke-width:{w}">'
                f'<title>{e["cwe"]} shared CWE · {e["mitre"]} shared ATT&amp;CK</title></line>')
    node_svg = []
    for mem in members:
        x, y = pos[mem["run_id"]]
        r = 16 + min(mem["findings_total"], 40) * 0.7
        cls = posture_class(mem["posture"]["band"])
        label = mem["label"][:22]
        node_svg.append(
            f'<g class="mnode" data-run="{esc(mem["run_id"])}" tabindex="0" '
            f'onclick="pfPick(\'{esc(mem["run_id"])}\')" transform="translate({x},{y})">'
            f'<circle class="mn mn-{cls}" r="{round(r,1)}"></circle>'
            f'<text class="mn-n" y="-{round(r+7,1)}">{esc(label)}</text>'
            f'<text class="mn-c" dy="4">{mem["findings_total"]}</text></g>')
    legend = ('<div class="maplegend"><span><i class="lg-solid"></i>declared link</span>'
              '<span><i class="lg-dash"></i>shared-weakness affinity</span>'
              '<span class="lg-hint">click a product to cross-filter · size = findings</span></div>')
    return f'''<section class="card span2" id="mapcard">
      <h2>Chain map <small>the portfolio's models and how they relate</small></h2>
      <svg id="pfmap" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid meet">
        <g id="pfedges">{"".join(edge_svg)}</g>
        <g id="pfnodes">{"".join(node_svg)}</g>
      </svg>{legend}
    </section>'''


def sec_members(m):
    cards = []
    riskrank = {rid: i for i, rid in enumerate(m["riskiest"])}
    for mem in sorted(m["members"], key=lambda x: riskrank.get(x["run_id"], 99)):
        cls = posture_class(mem["posture"]["band"])
        cov = mem["coverage_pct"]
        cov_badge = (f'<span class="pill pill-cov">{int(cov)}% coverage</span>' if cov is not None
                     else '<span class="pill pill-unknown" title="No coverage ledger — treated as UNKNOWN, not safe">coverage: unknown</span>')
        thin = '<span class="pill pill-thin">thin data</span>' if mem["thin"] else ""
        top = "".join(
            f'<li class="tf tf-{f["sev"].lower()}"><span class="fid">{esc(f["id"])}</span>{esc(f["title"])}</li>'
            for f in mem["top_findings"]) or '<li class="tf-empty">No findings surfaced.</li>'
        drill = (f'<a class="drill" href="{esc(mem["dashboard"])}">Open product dashboard →</a>'
                 if mem.get("dashboard") else '<span class="drill drill-off">dashboard not built</span>')
        cards.append(f'''<article class="pcard" data-run="{esc(mem["run_id"])}" onclick="pfPick('{esc(mem["run_id"])}')">
          <header><span class="pdot pd-{cls}"></span>
            <div><h3>{esc(mem["label"])}</h3><span class="ptag">{esc(mem["posture"]["band"])}</span></div>
            <span class="prank">#{riskrank.get(mem["run_id"],0)+1}</span></header>
          <div class="pmeta">{cov_badge}{thin}
            <span class="pill">{mem["findings_total"]} findings</span>
            <span class="pill">{mem["counts"].get("components",0)} components</span></div>
          {sev_bar(mem["severity"])}
          <ul class="tflist">{top}</ul>
          {drill}
        </article>''')
    return f'''<section class="card span2"><h2>Products <small>ranked by risk — worst first</small></h2>
      <div class="pgrid">{"".join(cards)}</div></section>'''


def sec_shared_cwe(m):
    rows = m["cross"]["shared_cwe"]
    if not rows:
        return _empty_card("Shared weaknesses (CWE)", "No CWE appears in more than one product — no cross-product weakness overlap surfaced.")
    body = "".join(
        f'<tr class="xrow" data-runs="{esc(" ".join(r["products"]))}">'
        f'<td class="k"><a href="https://cwe.mitre.org/data/definitions/{esc(r["key"].split("-")[-1])}.html">{esc(r["key"])}</a></td>'
        f'<td class="fanout">{r["fan_out"]}×</td>'
        f'<td>{"".join(f"<span class=chip data-run={esc(p)}>{esc(p)} <b>{len(r[chr(102)+chr(105)+chr(100)+chr(115)][p])}</b></span>" for p in r["products"])}</td></tr>'
        for r in rows)
    return f'''<section class="card"><h2>Shared weaknesses <small>same CWE across ≥2 products · auto-derived</small></h2>
      <p class="prov">Grounded: a CWE id is one global taxonomy node, so this is set-equality across members — not name matching.</p>
      <table class="xtab"><thead><tr><th>CWE</th><th>fan-out</th><th>products (findings)</th></tr></thead><tbody>{body}</tbody></table></section>'''


def sec_shared_mitre(m):
    rows = m["cross"]["shared_mitre"]
    if not rows:
        return _empty_card("Portfolio kill-chain (ATT&CK)", "No ATT&CK technique spans multiple products.")
    body = "".join(
        f'<tr class="xrow" data-runs="{esc(" ".join(r["products"]))}">'
        f'<td class="k"><a href="https://attack.mitre.org/techniques/{esc(r["key"])}/">{esc(r["key"])}</a></td>'
        f'<td class="fanout">{r["fan_out"]}×</td>'
        f'<td>{"".join(f"<span class=chip data-run={esc(p)}>{esc(p)}</span>" for p in r["products"])}</td></tr>'
        for r in rows)
    return f'''<section class="card"><h2>Portfolio attack surface <small>same ATT&CK technique across ≥2 products</small></h2>
      <p class="prov">A technique shared by many products is a portfolio-wide TTP — fix once, reduce blast radius across the chain.</p>
      <table class="xtab"><thead><tr><th>Technique</th><th>fan-out</th><th>products</th></tr></thead><tbody>{body}</tbody></table></section>'''


def sec_edges(m):
    edges = m["edges"]
    dropped = m["edges_dropped"]
    if edges:
        body = "".join(
            f'<tr class="xrow" data-runs="{esc(e["source"]["run"]+" "+e["target"]["run"])}">'
            f'<td class="etype">{esc(e["type"])}</td>'
            f'<td><span class=chip data-run={esc(e["source"]["run"])}>{esc(e["source"]["run"])}·{esc(e["source"]["element"])}</span> '
            f'<span class="arrow">↔</span> '
            f'<span class=chip data-run={esc(e["target"]["run"])}>{esc(e["target"]["run"])}·{esc(e["target"]["element"])}</span></td>'
            f'<td class="note">{esc(e["note"])}</td></tr>'
            for e in edges)
        etab = f'<table class="xtab"><thead><tr><th>type</th><th>endpoints (run·element)</th><th>rationale</th></tr></thead><tbody>{body}</tbody></table>'
    else:
        etab = '<p class="mt-empty">No declared cross-product relationships yet.</p>'
    drop = ""
    if dropped:
        drows = "".join(f'<li><code>{esc(d.get("id"))}</code> <b>{esc(d.get("type"))}</b> — dropped: {esc(d["reason"])}</li>'
                        for d in dropped)
        drop = f'<div class="dropped"><h3>⚠ Ungrounded edges rejected ({len(dropped)})</h3><ul>{drows}</ul>' \
               '<p>A declared edge is rendered only when BOTH endpoints resolve to a real recon element id. These did not, so they are dropped and reported — never silently drawn.</p></div>'
    return f'''<section class="card span2"><h2>Declared relationships <small>typed edges over real element ids · human/agent asserted</small></h2>
      <p class="prov">Structural cross-product links cannot be auto-derived from freeform names without fabricating. They are declared in <code>portfolio.json</code> with provenance and validated for grounding.</p>
      {etab}{drop}</section>'''


def _empty_card(title, msg):
    return f'<section class="card"><h2>{esc(title)}</h2><p class="mt-empty">{esc(msg)}</p></section>'


def kpi(label, val, sub, tone, suffix=""):
    return (f'<div class="kpi kpi-{tone}"><div class="kv">{val}{suffix}</div>'
            f'<div class="kl">{esc(label)}</div><div class="ks">{esc(sub)}</div></div>')


def render(m):
    p = m["portfolio"]
    posture = m["posture"]
    k = m["kpis"]
    cov = k["coverage_pct"]
    kpis = "".join([
        kpi("Products", k["products"], f'{k["assessed"]} with coverage ledger', "cyan"),
        kpi("Findings", k["findings"], "across the portfolio", "purple"),
        kpi("Critical", k["critical"], "worst-of rollup", "red"),
        kpi("High+", k["high"], "HIGH + CRITICAL", "amber"),
        kpi("Coverage", (int(cov) if cov is not None else "—"), "assessed-weighted", "teal",
            suffix=("<i>%</i>" if cov is not None else "")),
        kpi("Shared CWE", k["shared_cwe"], "cross-product weaknesses", "cyan"),
        kpi("Shared TTPs", k["shared_mitre"], "portfolio attack surface", "purple"),
        kpi("Declared links", k["declared_edges"], "grounded typed edges", "teal"),
    ])
    body = "".join([
        f'<div class="grid grid-2">{sec_map(m)}</div>',
        f'<div class="grid grid-2">{sec_members(m)}</div>',
        f'<div class="grid grid-2">{sec_shared_cwe(m)}{sec_shared_mitre(m)}</div>',
        f'<div class="grid grid-2">{sec_edges(m)}</div>',
    ])
    data_js = json.dumps({"riskiest": m["riskiest"]})
    repl = {
        "%%TITLE%%": esc(p["name"]), "%%DESC%%": esc(p["description"]),
        "%%POSTURE_BAND%%": esc(posture["band"]), "%%POSTURE_CLS%%": posture_class(posture["band"]),
        "%%POSTURE_SCORE%%": str(posture["score"]), "%%PID%%": esc(p["id"] or "—"),
        "%%KPIS%%": kpis, "%%BODY%%": body,
        "%%CSS%%": DASH_CSS + PF_CSS, "%%JS%%": JS.replace("__DATA__", data_js),
    }
    out = TEMPLATE
    for kk, vv in repl.items():
        out = out.replace(kk, vv)
    return out


PF_CSS = r"""
.wrap{max-width:1280px;margin:0 auto;padding:0 24px 80px}
.phero{padding:56px 0 28px;border-bottom:1px solid var(--border)}
.pbadge{font:600 12px/1 var(--mono);letter-spacing:.16em;text-transform:uppercase;color:var(--text-3)}
.phero h1{font:400 clamp(34px,5vw,60px)/1.02 var(--serif);margin:10px 0 8px;letter-spacing:-.01em}
.phero p{color:var(--text-2);max-width:820px;font-size:15px}
.pmetarow{display:flex;gap:18px;align-items:center;margin-top:18px;flex-wrap:wrap}
.pring{--sz:96px;width:var(--sz);height:var(--sz);border-radius:50%;display:grid;place-items:center;
  background:conic-gradient(var(--ring) calc(var(--pct)*1%),var(--border) 0);position:relative}
.pring::before{content:"";position:absolute;inset:8px;border-radius:50%;background:var(--deep)}
.pring b{position:relative;font:600 24px var(--mono)}
.pband{font:700 14px var(--mono);letter-spacing:.1em;padding:8px 16px;border-radius:999px}
.pband.crit{background:rgba(255,77,109,.14);color:var(--crit)} .pband.high{background:rgba(251,146,60,.14);color:var(--high)}
.pband.med{background:rgba(185,140,255,.14);color:var(--med)} .pband.low{background:rgba(56,189,248,.14);color:var(--low)}
.pband.none{background:var(--border);color:var(--text-2)}
.kpirow{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:26px 0 8px}
@media(max-width:900px){.kpirow{grid-template-columns:repeat(2,1fr)}}
.kpi{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px 18px;transition:transform .3s var(--ease),border-color .3s}
.kpi:hover{transform:translateY(-3px);border-color:var(--border-hi)}
.kpi .kv{font:600 30px var(--mono);line-height:1} .kpi .kv i{font-size:16px;font-style:normal;color:var(--text-3)}
.kpi .kl{font-weight:600;margin-top:6px} .kpi .ks{color:var(--text-3);font-size:12px}
.kpi-red .kv{color:var(--crit)} .kpi-amber .kv{color:var(--high)} .kpi-cyan .kv{color:var(--cyan)}
.kpi-purple .kv{color:var(--purple)} .kpi-teal .kv{color:var(--teal)}
.grid{display:grid;gap:18px;margin-top:18px} .grid-2{grid-template-columns:1fr 1fr}
.span2{grid-column:1/-1}
@media(max-width:900px){.grid-2{grid-template-columns:1fr}}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:22px 24px}
.card h2{font:400 22px var(--serif);margin-bottom:4px;display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.card h2 small{font:400 12px var(--mono);color:var(--text-3);text-transform:none;letter-spacing:0}
.prov{color:var(--text-3);font-size:12px;margin:2px 0 12px;border-left:2px solid var(--border-hi);padding-left:10px}
/* map */
#pfmap{width:100%;height:auto;margin-top:8px}
.me{stroke-linecap:round;transition:opacity .3s,stroke .3s}
.me-affinity{stroke:var(--text-4);stroke-dasharray:2 6;opacity:.5}
.me-declared{stroke:var(--cyan);stroke-width:2.5;opacity:.75}
.mnode{cursor:pointer} .mn{stroke:var(--deep);stroke-width:2;transition:r .3s var(--ease)}
.mn-crit{fill:var(--crit)} .mn-high{fill:var(--high)} .mn-med{fill:var(--med)} .mn-low{fill:var(--low)} .mn-none{fill:var(--none)}
.mn-n{text-anchor:middle;fill:var(--text-2);font:600 11px var(--sans)}
.mn-c{text-anchor:middle;fill:#fff;font:700 13px var(--mono)}
.mnode.dim{opacity:.22} .me.dim{opacity:.06}
.maplegend{display:flex;gap:20px;flex-wrap:wrap;color:var(--text-3);font-size:12px;margin-top:10px;align-items:center}
.maplegend i{display:inline-block;width:22px;height:0;vertical-align:middle;margin-right:6px}
.lg-solid{border-top:2.5px solid var(--cyan)} .lg-dash{border-top:2px dashed var(--text-4)}
.lg-hint{margin-left:auto;font-style:italic}
/* member cards */
.pgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:12px}
@media(max-width:1000px){.pgrid{grid-template-columns:repeat(2,1fr)}}
@media(max-width:680px){.pgrid{grid-template-columns:1fr}}
.pcard{background:var(--elevated);border:1px solid var(--border);border-radius:14px;padding:16px;cursor:pointer;
  transition:transform .3s var(--ease),border-color .3s,box-shadow .3s;display:flex;flex-direction:column;gap:10px}
.pcard:hover{transform:translateY(-3px);border-color:var(--border-hi);box-shadow:var(--shadow)}
.pcard.sel{border-color:var(--cyan);box-shadow:0 0 0 1px var(--cyan)}
.pcard.dim{opacity:.4}
.pcard header{display:flex;align-items:center;gap:10px}
.pcard header>div{flex:1;min-width:0} .pcard h3{font-size:15px;font-weight:600;line-height:1.2}
.ptag{font:600 10px var(--mono);color:var(--text-3);letter-spacing:.08em}
.prank{font:700 13px var(--mono);color:var(--text-3)}
.pdot{width:11px;height:11px;border-radius:50%;flex:none}
.pd-crit{background:var(--crit)} .pd-high{background:var(--high)} .pd-med{background:var(--med)} .pd-low{background:var(--low)} .pd-none{background:var(--none)}
.pmeta{display:flex;flex-wrap:wrap;gap:6px}
.pill{font:600 11px var(--mono);padding:3px 8px;border-radius:999px;background:var(--card);border:1px solid var(--border);color:var(--text-2)}
.pill-cov{color:var(--teal);border-color:rgba(45,212,191,.3)}
.pill-unknown{color:var(--text-3);border-style:dashed}
.pill-thin{color:var(--high);border-color:rgba(251,146,60,.3)}
.sevbar{display:flex;height:8px;border-radius:5px;overflow:hidden;background:var(--border)}
.sb{display:block} .sb-critical{background:var(--crit)} .sb-high{background:var(--high)} .sb-medium{background:var(--med)} .sb-low{background:var(--low)}
.sb-empty{flex:1;background:var(--border)}
.tflist{list-style:none;display:flex;flex-direction:column;gap:4px;margin:2px 0}
.tf{font-size:12px;color:var(--text-2);display:flex;gap:7px;align-items:baseline;line-height:1.3}
.tf .fid{font:600 10px var(--mono);color:var(--text-3);flex:none}
.tf-critical .fid{color:var(--crit)} .tf-high .fid{color:var(--high)}
.tf-empty{font-size:12px;color:var(--text-3);font-style:italic}
.drill{font:600 12px var(--mono);color:var(--cyan);text-decoration:none;margin-top:auto}
.drill:hover{text-decoration:underline} .drill-off{color:var(--text-4)}
/* cross tables */
.xtab{width:100%;border-collapse:collapse;font-size:13px;margin-top:6px}
.xtab th{text-align:left;font:600 11px var(--mono);color:var(--text-3);text-transform:uppercase;letter-spacing:.06em;padding:6px 8px;border-bottom:1px solid var(--border)}
.xtab td{padding:7px 8px;border-bottom:1px solid var(--border);vertical-align:top}
.xtab td.k a{color:var(--cyan);text-decoration:none;font:600 12px var(--mono)}
.xtab .fanout{font:700 13px var(--mono);color:var(--purple)}
.chip{display:inline-block;font:600 11px var(--mono);padding:2px 7px;border-radius:6px;background:var(--elevated);border:1px solid var(--border);color:var(--text-2);margin:1px 2px}
.chip b{color:var(--text-1)} .etype{font:600 12px var(--mono);color:var(--teal)}
.arrow{color:var(--text-3)} .note{color:var(--text-3);font-size:12px}
.xrow.dim{opacity:.25} .chip.hot{border-color:var(--cyan);color:var(--cyan)}
.dropped{margin-top:16px;border:1px dashed rgba(251,146,60,.4);border-radius:12px;padding:14px 16px;background:rgba(251,146,60,.05)}
.dropped h3{font:600 13px var(--mono);color:var(--high);margin-bottom:8px}
.dropped ul{list-style:none;display:flex;flex-direction:column;gap:5px;font-size:12px;color:var(--text-2)}
.dropped code{font:600 11px var(--mono);color:var(--text-1)} .dropped p{color:var(--text-3);font-size:11px;margin-top:8px}
.mt-empty{color:var(--text-3);font-style:italic;padding:14px 0}
.selbar{position:sticky;top:0;z-index:50;display:none;align-items:center;gap:12px;padding:10px 24px;
  background:var(--elevated);border-bottom:1px solid var(--border-hi);font-size:13px}
.selbar.on{display:flex} .selbar b{color:var(--cyan);font-family:var(--mono)}
.selbar button{margin-left:auto;background:var(--card);border:1px solid var(--border);color:var(--text-2);
  border-radius:8px;padding:5px 12px;cursor:pointer;font:600 12px var(--mono)}
.foot{color:var(--text-4);font-size:11px;text-align:center;padding:40px 0 0;font-family:var(--mono)}
"""

JS = r"""
const PF = __DATA__;
let sel = null;
function pfPick(run){ sel = (sel===run)? null : run; pfApply(); }
function pfApply(){
  const bar = document.getElementById('selbar');
  document.querySelectorAll('.pcard').forEach(c=>{
    c.classList.toggle('sel', c.dataset.run===sel);
    c.classList.toggle('dim', !!sel && c.dataset.run!==sel);
  });
  document.querySelectorAll('.mnode').forEach(g=>{
    g.classList.toggle('dim', !!sel && g.dataset.run!==sel);
  });
  document.querySelectorAll('.me').forEach(l=>{
    const hit = !sel || l.dataset.a===sel || l.dataset.b===sel;
    l.classList.toggle('dim', !hit);
  });
  document.querySelectorAll('.xrow').forEach(r=>{
    const runs=(r.dataset.runs||'').split(' ');
    r.classList.toggle('dim', !!sel && !runs.includes(sel));
  });
  document.querySelectorAll('.chip').forEach(c=> c.classList.toggle('hot', !!sel && c.dataset.run===sel));
  if(bar){ bar.classList.toggle('on', !!sel);
    if(sel) bar.querySelector('b').textContent = sel; }
}
function pfClear(){ sel=null; pfApply(); }
// theme toggle (same behaviour as the per-product dashboard)
function pfTheme(){ const b=document.body; const t=b.getAttribute('data-theme')==='light'?'':'light';
  if(t) b.setAttribute('data-theme',t); else b.removeAttribute('data-theme'); }
document.addEventListener('keydown',e=>{ if(e.key==='Escape') pfClear(); });
"""

TEMPLATE = r"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%%TITLE%% — Portfolio Risk</title>
<style>%%CSS%%</style></head>
<body>
<div class="selbar" id="selbar">Filtering to <b>—</b> · click again or Esc to clear
  <button onclick="pfClear()">clear</button></div>
<div class="wrap">
  <header class="phero">
    <div class="pbadge">Chain of Models · %%PID%%</div>
    <h1>%%TITLE%%</h1>
    <p>%%DESC%%</p>
    <div class="pmetarow">
      <div class="pring" style="--pct:%%POSTURE_SCORE%%;--ring:var(--crit)"><b>%%POSTURE_SCORE%%</b></div>
      <span class="pband %%POSTURE_CLS%%">%%POSTURE_BAND%%</span>
      <button onclick="pfTheme()" style="margin-left:auto;background:var(--card);border:1px solid var(--border);color:var(--text-2);border-radius:8px;padding:7px 12px;cursor:pointer;font:600 12px var(--mono)">◐ theme</button>
    </div>
    <div class="kpirow">%%KPIS%%</div>
  </header>
  %%BODY%%
  <div class="foot">Deterministic portfolio view · derived only from member manifests + declared edges · offline · blanks are honest</div>
</div>
<script>%%JS%%</script>
</body></html>"""
