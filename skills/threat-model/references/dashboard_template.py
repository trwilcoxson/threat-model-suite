#!/usr/bin/env python3
"""
Self-contained HTML template for the risk dashboard.

render(model) -> str.  Inline CSS/JS, NO external CDN/fonts/assets (offline, deterministic).
Palette echoes the claudetm-demo product family (void bg, cyan/teal accent gradient); fonts
use system stacks that approximate the demo's DM Sans / Instrument Serif / IBM Plex Mono so
the file stays offline. Content is baked server-side (grounded, visible without JS); JS only
adds motion, counters and the theme toggle. Absent data -> graceful empty state.
"""
import json, html, re
from collections import defaultdict

SEV_ORDER = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
SEV_CLASS = {"CRITICAL": "crit", "HIGH": "high", "MEDIUM": "med", "LOW": "low", "—": "none"}


def esc(s):
    return html.escape(str(s if s is not None else ""))


def empty(msg="No evidence surfaced", note=""):
    n = f'<div class="empty-note">{esc(note)}</div>' if note else ""
    return f'<div class="empty"><div class="empty-dash">—</div><div class="empty-msg">{esc(msg)}</div>{n}</div>'


def kpi(label, value, sub="", accent="cyan", suffix=""):
    return f'''<div class="kpi reveal" data-accent="{accent}">
      <div class="kpi-val"><span class="counter" data-to="{value}">0</span>{suffix}</div>
      <div class="kpi-label">{esc(label)}</div>
      <div class="kpi-sub">{esc(sub)}</div>
    </div>'''


def ev_block(evidence):
    """Embedded evidence for one finding: the build-extracted excerpt (monospace/quote), the findable
    reference (file:line), and a jump to the related diagram node. Honest no-evidence / unresolved states
    are shown explicitly — never a fabricated snippet. Returns '' when the finding has no evidence[]."""
    if not evidence:
        return ""
    rows = []
    for e in evidence:
        node = e.get("node")
        jump = (f'<button class="ev-jump jump-node" data-pivot="entity" data-entity="{esc(node)}" '
                f'title="Jump to diagram node {esc(node)}">◈ {esc(e.get("node_name") or node)}</button>'
                if node else "")
        if e.get("no_direct_evidence"):
            rows.append(f'<div class="ev-item ev-none"><div class="ev-head"><span class="ev-tag">no direct '
                        f'evidence</span></div><p class="muted">{esc(e.get("justification") or "—")}</p></div>')
            continue
        ref = e.get("ref") or "—"
        if e.get("unresolved") or (not e.get("excerpt")):
            rows.append(f'<div class="ev-item ev-unres"><div class="ev-head"><code class="ev-ref">{esc(ref)}</code>'
                        f'<span class="ev-tag warn">unresolved</span>{jump}</div></div>')
            continue
        kind = e.get("kind") or "code"
        excerpt = esc(e.get("excerpt"))
        body = (f'<blockquote class="ev-quote">{excerpt}</blockquote>' if kind in ("doc", "diagram")
                else f'<pre class="ev-code lang-{esc(kind)}"><code>{excerpt}</code></pre>')
        rows.append(f'<div class="ev-item"><div class="ev-head"><code class="ev-ref">{esc(ref)}</code>'
                    f'<span class="ev-tag">{esc(kind)}</span>{jump}</div>{body}</div>')
    return (f'<div class="f-field ev-field"><span>Evidence</span>'
            f'<div class="evidence-list">{"".join(rows)}</div></div>')


def card(title, body, sub="", cls="", tag=""):
    tagh = f'<span class="card-tag">{esc(tag)}</span>' if tag else ""
    subh = f'<div class="card-sub">{esc(sub)}</div>' if sub else ""
    return f'''<section class="card reveal {cls}">
      <div class="card-head"><h2>{esc(title)}{tagh}</h2>{subh}</div>
      <div class="card-body">{body}</div>
    </section>'''


# ---------- the RUN'S ACTUAL structural diagram (interactive, node-id-linked) ----------
# NOT a bespoke node map: the nodes are the run's recon elements (ids = C1/D1/E1/X1/R0…) and the
# edges are the run's REAL dataflows (from recon.dataflows[] or the run's structural-diagram.mmd),
# grouped by the run's own trust zones. Same nodes/edges/zones the report shows — one source of
# truth — with pan/zoom + click→cross-filter layered over it.

NODE_W, NODE_H, GAP_X, GAP_Y, PAD, LABEL_H, MARGIN = 188, 48, 18, 20, 16, 26, 26
_ROW_COLS = 5  # leaf nodes per grid row inside a band/container


def _natural_key(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(s))]


def _grid(ids, x, y, avail_w):
    """Place a run of leaf nodes in a wrapping grid; return (positions, height_used)."""
    cols = max(1, min(_ROW_COLS, int((avail_w + GAP_X) // (NODE_W + GAP_X)) or 1))
    pos = {}
    for i, nid in enumerate(ids):
        r, c = divmod(i, cols)
        pos[nid] = (x + c * (NODE_W + GAP_X), y + r * (NODE_H + GAP_Y))
    rows = (len(ids) + cols - 1) // cols if ids else 0
    return pos, rows * (NODE_H + GAP_Y)


_DIAG_TOOLBAR = '''<div class="diag-toolbar">
        <button data-z="in" title="Zoom in">+</button>
        <button data-z="out" title="Zoom out">−</button>
        <button data-z="fit" title="Zoom to fit">⤢</button>
        <button data-z="reset" title="Reset">⟳</button>
        <span class="diag-hint">scroll to zoom · drag to pan · click a node to pivot</span>
      </div>'''


def _more_diagrams(m):
    """The OTHER rendered artifacts (L1–L3, attack trees/flows, SBOM) as SECONDARY links — a small
    expandable list under the primary diagram, NOT a front gallery. Each opens on demand (native
    <details>, offline) and mounts its exact verbatim SVG; structural/risk layers keep the node-id
    cross-filter. The primary diagram (already shown big above) is excluded so nothing is duplicated."""
    g = m["graph"]
    primary_file = g.get("svg_file")
    others = [a for a in (g.get("gallery") or []) if a.get("file") != primary_file]
    if not others:
        return ""
    items = []
    for a in others:
        linked = len(a.get("node_ids") or [])
        badge = f'<span class="more-badge">{linked} linked</span>' if linked else ""
        items.append(
            f'<details class="more-item"><summary><b>{esc(a["label"])}</b>'
            f'<span class="more-file">{esc(a["file"])}</span>{badge}</summary>'
            f'<div class="more-svg">{a["svg"]}</div></details>')
    return (f'<details class="more-diagrams"><summary>More diagrams '
            f'<span class="more-count">{len(others)}</span> — other layers, attack trees/flows, SBOM'
            f'</summary><div class="more-list">{"".join(items)}</div></details>')


# ---------- Asset Inspector: surface every selected node's agent metadata beside the map ----------
# The metadata the agents already emitted (in component_risk / links / findings_by_id / recon) is
# trapped "in the image" of the raw SVG. The Inspector lifts it OUT: for the selected recon element it
# shows id, name, kind/type, trust zone, risk band + max L×I, its findings (each scrolls to it below),
# STRIDE-LM, and the element's own evidence/annotations. Reshape only; absent field -> honest blank.

KIND_LABEL = {"component": "Component", "store": "Data store", "entry": "Entry point",
              "external": "External dependency", "actor": "Actor / role", "boundary": "Trust boundary"}
# stroke-only type glyphs (styled via CSS: fill:none; stroke:currentColor) — a small typed cue per kind.
_GLYPH = {
    "component": '<rect x="3.5" y="5" width="13" height="10" rx="1.6"/><path d="M3.5 8.5h13"/>',
    "store": '<ellipse cx="10" cy="5.5" rx="6.5" ry="2.4"/><path d="M3.5 5.5v9c0 1.3 2.9 2.4 6.5 2.4s6.5-1.1 6.5-2.4v-9"/>',
    "entry": '<path d="M11.5 3.5H4.5v13h7"/><path d="M8 10h8.5"/><path d="M13.5 6.5 17 10l-3.5 3.5"/>',
    "external": '<path d="M10 2.5 16.8 6.3v7.4L10 17.5 3.2 13.7V6.3z"/><path d="M10 2.5v15"/>',
    "actor": '<circle cx="10" cy="6.5" r="3"/><path d="M4.5 16.5c0-3 2.5-4.6 5.5-4.6s5.5 1.6 5.5 4.6"/>',
    "boundary": '<rect x="3.5" y="3.5" width="13" height="13" rx="2" stroke-dasharray="3 2.4"/>',
}


def _glyph(kind):
    return f'<svg class="ins-glyph" viewBox="0 0 20 20" aria-hidden="true">{_GLYPH.get(kind, _GLYPH["component"])}</svg>'


def _inspector_html(m, eid):
    """Server-baked Asset Inspector for one entity (grounded, visible without JS). JS re-renders the
    same shape on node click via renderInspector()."""
    em = m.get("entity_meta") or {}
    fbi = m.get("findings_by_id") or {}
    hint = ('<div class="ins-hint">Click any node on the map to inspect its risk, findings &amp; evidence '
            '· <b>showing the highest-risk asset</b></div>')
    e = em.get(eid)
    if not e:
        return (f'<aside class="inspector" id="inspector" data-eid="">{hint}'
                f'{empty("No linkable assets", "recon emitted no diagram-linked elements")}</aside>')
    sev = SEV_CLASS.get(e["sev"], "none")
    typ = f' · {esc(e["type"])}' if e.get("type") else ""
    stride = "".join(f'<span class="ins-strd">{esc(s)}</span>' for s in e["stride"]) or '<span class="muted">—</span>'
    rows = ""
    for fid in e["fids"]:
        f = fbi.get(fid) or {}
        fs = SEV_CLASS.get(f.get("sev"), "none")
        risk = (f.get("l") or 0) * (f.get("i") or 0)
        rows += (f'<button class="ins-f" data-pivot="finding" data-fid="{esc(fid)}">'
                 f'<span class="ins-f-stripe {fs}"></span><code class="ins-fid">{esc(fid)}</code>'
                 f'<span class="ins-f-title">{esc(f.get("title") or "")}</span>'
                 f'<span class="ins-f-score">L{esc(f.get("l"))}·I{esc(f.get("i"))} <b>{risk}</b></span></button>')
    flist = f'<div class="ins-flist">{rows}</div>' if rows else '<div class="ins-blank">No findings reference this asset</div>'
    ev = "".join(f'<code class="ins-ev">{esc(r)}</code>' for r in e["evidence"])
    evb = ('<div class="ins-sec"><div class="ins-lab">Evidence / annotations</div>'
           + (f'<div class="ins-evs">{ev}</div>' if ev else '<div class="ins-blank">No evidence surfaced on this element</div>')
           + '</div>')
    note = (f'<div class="ins-sec"><div class="ins-lab">Risk note</div><p class="ins-note">{esc(e["note"])}</p></div>'
            if e.get("note") else "")
    zone = esc(e["zone"]) if e.get("zone") else '<span class="muted">—</span>'
    tech = esc(e["tech"]) if e.get("tech") else '<span class="muted">—</span>'
    return f'''<aside class="inspector" id="inspector" data-eid="{esc(eid)}">
      {hint}
      <div class="ins-card">
        <div class="ins-head"><span class="ins-gwrap {sev}">{_glyph(e["kind"])}</span>
          <div class="ins-titles"><div class="ins-name">{esc(e["name"])}</div>
            <div class="ins-sub"><code class="ins-id">{esc(eid)}</code>
              <span class="ins-kind">{esc(KIND_LABEL.get(e["kind"], e["kind"]))}{typ}</span></div></div></div>
        <div class="ins-stats">
          <div class="ins-stat {sev}"><b class="ins-band">{esc(e["sev"])}</b><span>risk band</span></div>
          <div class="ins-stat"><b>{e["score"]}</b><span>max L×I</span></div>
          <div class="ins-stat"><b>{e["count"]}</b><span>findings</span></div></div>
        <div class="ins-rows">
          <div class="ins-row"><span class="ins-lab">Trust zone</span><span>{zone}</span></div>
          <div class="ins-row"><span class="ins-lab">Technology</span><span class="ins-tech">{tech}</span></div></div>
        <div class="ins-sec"><div class="ins-lab">STRIDE-LM</div><div class="ins-strds">{stride}</div></div>
        {note}
        <div class="ins-sec"><div class="ins-lab">Findings <span class="ins-n">{e["count"]}</span></div>{flist}</div>
        {evb}
      </div>
    </aside>'''


def _diag_legend():
    """Compact always-visible key so the map is self-explaining (risk ramp · flow types · trust zone)."""
    ramp = "".join(f'<span class="lg-item"><i class="lg-sw {c}"></i>{lab}</span>'
                   for c, lab in (("crit", "Critical"), ("high", "High"), ("med", "Medium"), ("low", "Low")))
    flows = "".join(f'<span class="lg-item"><i class="lg-line {c}"></i>{lab}</span>'
                    for c, lab in (("data", "Data"), ("control", "Control"), ("admin", "Admin"), ("build", "Build")))
    return (f'<div class="diag-legend"><div class="lg-grp"><span class="lg-t">Risk</span>{ramp}</div>'
            f'<div class="lg-grp"><span class="lg-t">Flow</span>{flows}</div>'
            f'<div class="lg-grp"><span class="lg-t">Zone</span>'
            f'<span class="lg-item"><i class="lg-zone"></i>Trust boundary</span></div></div>')


def sec_diagram_embed(m):
    """The SINGLE primary diagram view, now a threat-map CONSOLE: the run's ACTUAL visual-engine SVG
    (preferring the L4 risk/threat overlay; L1 fallback) embedded verbatim in a big glass viewer, paired
    with a live Asset Inspector that lifts each node's agent metadata OUT of the image. Pan/zoom +
    click→inspect+cross-filter layered on top; other artifacts demoted to secondary links below."""
    g = m["graph"]
    linked = len(g.get("svg_node_ids") or [])
    label = g.get("svg_label") or "Structural"
    is_risk = g.get("svg_kind") == "risk"
    what = ("the full L4 risk/threat overlay — risk colors, TM-NNN ids, STRIDE·L×I, CWE/MITRE, threat "
            "annotations, attack paths & trust boundaries, all in the image"
            if is_risk else "the run's structural diagram (typed shapes/icons + trust boundaries)")
    note = (f'<div class="diag-note">The run\'s actual visual-engine diagram '
            f'(<code>{esc(g.get("svg_file",""))}</code>, <b>{esc(label)}</b>) — {what}. The exact SVG the '
            f'flow embeds in the report; the Inspector surfaces each node\'s metadata beside it.</div>')
    body = f'''<div class="diagram embed">
      <div class="diag-split">
        <div class="diag-main">
          {_DIAG_TOOLBAR}
          <div class="diag-viewport" id="diagVP">
            <div id="diagView" class="embed-view">{g["svg"]}</div>
            <div class="diag-vignette" aria-hidden="true"></div>
          </div>
          {_diag_legend()}
        </div>
        {_inspector_html(m, m.get("top_entity"))}
      </div>{note}{_more_diagrams(m)}</div>'''
    return card(f"Threat-Model Diagram — {esc(label)}", body, cls="diagram-card",
                sub="The run's real visual-engine diagram, embedded verbatim — the Asset Inspector lifts "
                    "every node's risk, findings, STRIDE &amp; evidence out of the image; click to explore",
                tag=f"{linked} linked nodes · embedded SVG")


def sec_diagram(m):
    g = m["graph"]
    if g.get("svg"):
        return sec_diagram_embed(m)
    nodes = {n["id"]: n for n in g["nodes"]}
    if not nodes:
        return card("Structural Diagram", empty("No recon entities emitted"), cls="diagram-card")
    containers = g.get("containers", []) or []
    cont_by_id = {c["id"]: c for c in containers}
    subs_of = defaultdict(list)
    for c in containers:
        subs_of[c.get("parent")].append(c["id"])

    def child_items(cid):
        items = [("c", s) for s in sorted(subs_of.get(cid, []), key=_natural_key)]
        items += [("n", n) for n in cont_by_id[cid]["children"] if n in nodes]
        return items

    pos, zones = {}, []  # id -> (x,y); zones = [(x,y,w,h,label,depth)]

    def layout(items, x, y, avail_w, depth):
        cy = pending = None
        cy = y
        pending = []

        def flush():
            nonlocal cy
            if not pending:
                return
            gp, h = _grid(pending, x, cy, avail_w)
            pos.update(gp)
            cy += h
            pending.clear()

        for kind, oid in items:
            if kind == "n":
                if oid in nodes:
                    pending.append(oid)
            else:
                flush()
                inner_x, inner_y = x + PAD, cy + LABEL_H
                inner_h = layout(child_items(oid), inner_x, inner_y, avail_w - 2 * PAD, depth + 1)
                zh = inner_h + LABEL_H + PAD
                zones.append((x, cy, avail_w, zh, cont_by_id[oid]["label"], depth))
                cy += zh + GAP_Y
        flush()
        return cy - y

    root_items = [(k, i) for (k, i) in g.get("order", []) if (k == "c" and i in cont_by_id) or (k == "n" and i in nodes)]
    placed = {i for k, i in root_items if k == "n"} | {ch for c in containers for ch in c["children"]}
    root_items += [("n", i) for i in sorted(nodes, key=_natural_key) if i not in placed]  # any stragglers
    content_w = _ROW_COLS * NODE_W + (_ROW_COLS - 1) * GAP_X
    total_h = layout(root_items, MARGIN, MARGIN, content_w, 0)
    vw = content_w + 2 * MARGIN
    vh = total_h + 2 * MARGIN

    zone_svg = "".join(
        f'<g class="zone d{min(d,4)}"><rect x="{zx:.0f}" y="{zy:.0f}" width="{zw:.0f}" height="{zh:.0f}" rx="14"/>'
        f'<text class="zone-cap" x="{zx+12:.0f}" y="{zy+18:.0f}">{esc(lab)}</text></g>'
        for (zx, zy, zw, zh, lab, d) in zones)

    node_svg = []
    for nid, (nx, ny) in pos.items():
        nd = nodes[nid]
        short = esc(nd["name"][:24] + ("…" if len(nd["name"]) > 24 else ""))
        node_svg.append(
            f'<g class="node sev-{SEV_CLASS.get(nd["sev"],"none")} k-{esc(nd.get("kind",""))}" '
            f'data-entity="{nid}" data-kind="{esc(nd.get("kind",""))}" data-fids="{" ".join(nd["fids"])}" '
            f'data-name="{esc(nd["name"])}" data-tech="{esc(nd["tech"])}" data-count="{nd["count"]}" '
            f'tabindex="0" transform="translate({nx:.0f},{ny:.0f})">'
            f'<rect class="node-box" width="{NODE_W}" height="{NODE_H}" rx="10"/>'
            f'<text class="node-id" x="12" y="20">{esc(nid)}</text>'
            f'<text class="node-name" x="12" y="36">{short}</text>'
            f'<text class="node-badge" x="{NODE_W-12}" y="28" text-anchor="end">{nd["count"]}</text>'
            f'</g>')

    edge_svg = []
    for e in g["edges"]:
        if e["a"] in pos and e["b"] in pos:
            ax, ay = pos[e["a"]]; bx, by = pos[e["b"]]
            x1, y1 = ax + NODE_W / 2, ay + NODE_H / 2
            x2, y2 = bx + NODE_W / 2, by + NODE_H / 2
            my = (y1 + y2) / 2
            edge_svg.append(
                f'<path class="edge et-{esc(e.get("etype","data"))}" data-a="{e["a"]}" data-b="{e["b"]}" '
                f'data-fids="{" ".join(e.get("fids",[]))}" marker-end="url(#arh)" '
                f'd="M{x1:.0f},{y1:.0f} C{x1:.0f},{my:.0f} {x2:.0f},{my:.0f} {x2:.0f},{y2:.0f}">'
                f'<title>{esc(e.get("label") or e.get("etype","flow"))}</title></path>')

    src = g.get("source")
    if src == "none":
        note = ('<div class="diag-note">No typed <code>dataflows[]</code> or structural diagram in this '
                'run — recon entities shown ungrouped; no flow arrows invented.</div>')
    else:
        origin = "recon.dataflows[]" if src == "dataflows" else "the run's structural-diagram.mmd"
        note = (f'<div class="diag-note">The run\'s own structural diagram (nodes = recon elements, edges '
                f'from <code>{origin}</code>) — the same threat model the report embeds. '
                f'Click a node to cross-filter the dashboard.</div>')
    svg = f'''<div class="diagram">
      <div class="diag-toolbar">
        <button data-z="in" title="Zoom in">+</button>
        <button data-z="out" title="Zoom out">−</button>
        <button data-z="fit" title="Zoom to fit">⤢</button>
        <button data-z="reset" title="Reset">⟳</button>
        <span class="diag-hint">scroll to zoom · drag to pan · click a node to pivot</span>
      </div>
      <div class="diag-viewport" id="diagVP">
        <svg id="diagSVG" viewBox="0 0 {vw:.0f} {vh:.0f}" preserveAspectRatio="xMidYMid meet">
          <defs><marker id="arh" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7"
            orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="arh"/></marker></defs>
          <g id="diagView">
            <g class="zones">{zone_svg}</g>
            <g class="edges">{''.join(edge_svg)}</g>
            <g class="nodes">{''.join(node_svg)}</g>
          </g>
        </svg>
      </div>{note}</div>'''
    return card("Structural Diagram — interactive", svg, cls="diagram-card",
                sub="The run's real DFD from recon + dataflows — node ids link to findings; click to cross-filter",
                tag=f"{len(pos)} nodes · {len(edge_svg)} flows")


# ---------- section builders ----------

def sec_severity(m):
    sev = m["severity"]
    total = sum(sev.values())
    if total == 0:
        return card("Severity Distribution", empty("No findings emitted"))
    # donut via conic-gradient computed server-side (deterministic), animated mask in CSS
    colors = {"CRITICAL": "var(--crit)", "HIGH": "var(--high)", "MEDIUM": "var(--med)", "LOW": "var(--low)"}
    stops, acc = [], 0
    for s in SEV_ORDER:
        frac = sev[s] / total
        stops.append(f"{colors[s]} {acc*360:.2f}deg {(acc+frac)*360:.2f}deg")
        acc += frac
    conic = "conic-gradient(" + ",".join(stops) + ")"
    legend = "".join(
        f'<li data-sev="{s}" data-pivot="sev"><span class="dot {SEV_CLASS[s]}"></span>{s}<b>{sev[s]}</b></li>'
        for s in SEV_ORDER)
    body = f'''<div class="donut-wrap">
      <div class="donut" style="--conic:{conic}"><div class="donut-hole">
        <span class="counter" data-to="{total}">0</span><small>findings</small></div></div>
      <ul class="legend">{legend}</ul>
    </div>'''
    return card("Severity Distribution", body, sub="Bands from findings.summary_counts")


def sec_heatmap(m):
    hm = m["heatmap"]
    if not any(any(r) for r in hm):
        return card("Likelihood × Impact", empty())
    mx = max(max(r) for r in hm) or 1
    cells = ""
    # rows: likelihood 5..1 (top=high), cols impact 1..5
    for li in range(5, 0, -1):
        for im in range(1, 6):
            n = hm[li - 1][im - 1]
            risk = li * im
            band = "crit" if risk >= 20 else "high" if risk >= 12 else "med" if risk >= 6 else "low"
            intensity = 0.12 + 0.88 * (n / mx) if n else 0
            lbl = f'<span class="hm-n">{n}</span>' if n else ""
            cells += (f'<div class="hm-cell {band}" style="--i:{intensity:.2f}" '
                      f'data-delay="{(5-li)*5+im}" title="L{li}×I{im} = {n} finding(s)">{lbl}</div>')
    body = f'''<div class="heatmap">
      <div class="hm-ylabel">Likelihood →</div>
      <div class="hm-grid">{cells}</div>
      <div class="hm-xlabel">Impact →</div>
    </div>'''
    return card("Likelihood × Impact Risk Matrix", body, sub="One cell per (likelihood, impact); count = findings")


def sec_stride(m):
    st = m["stride"]
    names = m["stride_names"]
    total = sum(st.values())
    if total == 0:
        return card("STRIDE-LM Coverage", empty())
    mx = max(st.values()) or 1
    rows = ""
    for k in ["S", "T", "R", "I", "D", "E", "LM"]:
        v = st[k]
        w = 100 * v / mx
        rows += f'''<div class="bar-row" data-frame="S:{k}" data-pivot="frame">
          <div class="bar-lab"><b>{k}</b> {esc(names[k])}</div>
          <div class="bar-track"><div class="bar-fill" style="--w:{w:.1f}%"><span>{v}</span></div></div>
        </div>'''
    return card("STRIDE-LM Threat Categories", f'<div class="bars">{rows}</div>',
                sub="Findings per category (findings span multiple)")


def sec_coverage(m):
    cov = m["coverage"]
    if not cov["total"]:
        return card("Assessment Coverage", empty("No coverage ledger emitted"))
    st = cov["states"]
    order = [("present", "Present", "low"), ("partial", "Partial", "med"),
             ("absent", "Absent", "high"), ("not-applicable", "N/A", "none"),
             ("unknown", "Unknown", "none")]
    total = cov["total"]
    segs = ""
    for key, lab, cls in order:
        v = st.get(key, 0)
        if v:
            segs += f'<div class="stack-seg {cls}" style="--w:{100*v/total:.2f}%" title="{lab}: {v}"><span>{v}</span></div>'
    legend = "".join(f'<li><span class="dot {cls}"></span>{lab} <b>{st.get(key,0)}</b></li>'
                     for key, lab, cls in order if st.get(key, 0))
    # gauge for coverage %
    pct = cov["pct"] or 0
    gauge = f'''<div class="gauge" style="--pct:{pct}">
      <svg viewBox="0 0 120 120"><circle class="g-bg" cx="60" cy="60" r="52"/>
      <circle class="g-fg" cx="60" cy="60" r="52" pathLength="100"/></svg>
      <div class="gauge-c"><span class="counter" data-to="{pct}" data-dec="1">0</span><i>%</i>
        <small>weighted</small></div></div>'''
    # category mini-matrix
    cats = ""
    for c in cov["categories"]:
        p = c["pct"]
        cls = "low" if (p or 0) >= 70 else "med" if (p or 0) >= 40 else "high"
        pct_txt = f'{int(p)}%' if p is not None else "N/A"
        cats += (f'<div class="cat" title="{esc(c["name"])}: present {c["present"]} / partial {c["partial"]}'
                 f' / absent {c["absent"]} / n/a {c["na"]}">'
                 f'<div class="cat-bar {cls}" style="--p:{p or 0}%"></div>'
                 f'<div class="cat-name">{esc(c["name"].replace("-"," "))}</div>'
                 f'<div class="cat-pct">{pct_txt}</div></div>')
    body = f'''<div class="cov-top">{gauge}
      <div class="cov-right">
        <div class="cov-headline"><b>{cov["present_pct"]}%</b> of {cov["applicable"]} applicable checklist items
          carry direct evidence <span class="muted">({total} items total, {st.get("not-applicable",0)} N/A by system profile)</span></div>
        <div class="stack">{segs}</div>
        <ul class="legend legend-wrap">{legend}</ul>
      </div></div>
      <div class="cat-grid-label">Coverage by taxonomy section ({len(cov["categories"])})</div>
      <div class="cat-grid">{cats}</div>'''
    return card("Assessment Coverage Ledger", body, sub="225-item security-taxonomy completeness (reference-free)")


def sec_profile(m):
    ctx = m["coverage"]["context"]
    if not ctx:
        return ""
    labels = {"has_api": "API", "has_client": "Web Client", "has_cloud": "Cloud",
              "has_containers": "Containers", "has_cicd": "CI/CD", "has_third_party": "3rd-party",
              "multi_tenant": "Multi-tenant", "has_personal_data": "Personal Data",
              "has_regulatory": "Regulated", "has_ai_ml": "AI/ML", "has_hardware": "Hardware"}
    chips = ""
    for k, lab in labels.items():
        on = ctx.get(k)
        chips += f'<span class="chip {"on" if on else "off"}">{esc(lab)}</span>'
    return f'<div class="profile reveal"><span class="profile-lab">System profile</span>{chips}</div>'


def sec_frameworks(m):
    # MITRE + CWE side by side
    mitre = m["mitre"]
    if mitre:
        mx = max((t["score"] or t["n"]) for t in mitre) or 1
        chips = ""
        for t in mitre:
            sc = t["score"]
            inten = (sc or (t["n"] * 5)) / (mx or 1)
            chips += (f'<span class="tech reveal" style="--i:{inten:.2f}" data-frame="M:{esc(t["id"])}" '
                      f'data-pivot="frame" title="{esc(t["comment"])}">'
                      f'{esc(t["id"])}<b>{t["n"]}</b></span>')
        nav = m.get("navigator_meta")
        navtxt = f'ATT&CK {esc(nav["version"])} · {esc(nav["domain"])}' if nav else "from findings.mitre[]"
        mbody = f'<div class="techs">{chips}</div>'
        mcard = card("MITRE ATT&CK Techniques", mbody, sub=navtxt, tag=f"{len(mitre)}")
    else:
        mcard = card("MITRE ATT&CK Techniques", empty())
    cwe = m["cwe"]
    if cwe:
        mxc = max(cwe.values()) or 1
        rows = ""
        for c, n in cwe.items():
            rows += (f'<div class="bar-row sm" data-frame="W:{esc(c)}" data-pivot="frame"><div class="bar-lab">{esc(c)}</div>'
                     f'<div class="bar-track"><div class="bar-fill alt" style="--w:{100*n/mxc:.0f}%"><span>{n}</span></div></div></div>')
        ccard = card("CWE Weakness Classes", f'<div class="bars">{rows}</div>', tag=f"{len(cwe)}",
                     sub="from findings.cwe[]")
    else:
        ccard = card("CWE Weakness Classes", empty())
    return mcard + ccard


def sec_chains(m):
    ch = m["chains"]
    if not ch:
        return card("Attack Paths / Kill Chains", empty("No kill chains emitted"))
    blocks = ""
    for c in ch:
        steps = ""
        for i, s in enumerate(c["steps"]):
            arrow = '<span class="kc-arrow">→</span>' if i else ""
            steps += (f'{arrow}<span class="kc-step {SEV_CLASS.get(s["sev"],"none")}" '
                      f'data-fid="{esc(s["id"])}" data-pivot="finding" '
                      f'title="{esc(s["title"])}">{esc(s["id"])}</span>')
        blocks += f'''<div class="kc reveal" data-kc="{esc(c["id"])}" data-pivot="kc">
          <div class="kc-head"><span class="kc-id">{esc(c["id"])}</span>
            <span class="kc-goal">{esc(c["goal"])}</span></div>
          <div class="kc-flow">{steps}</div>
        </div>'''
    return card("Attack Paths / Kill Chains", blocks, sub="Ordered finding chains toward an attacker goal",
                tag=f"{len(ch)}")


def sec_components(m):
    rows = m["component_risk"]
    if not rows:
        return card("Component & Data-Store Risk", empty())
    out = ""
    mx = max(r["count"] for r in rows) or 1
    for r in rows:
        out += f'''<div class="comp-row reveal" data-entity="{esc(r["id"])}" data-pivot="entity" data-fids="{" ".join(r["ids"])}">
          <span class="sev-pill {SEV_CLASS.get(r["sev"],"none")}">{esc(r["sev"])}</span>
          <span class="comp-name">{esc(r["name"])} <i>{esc(r["id"])}</i></span>
          <span class="comp-bar"><span style="--w:{100*r["count"]/mx:.0f}%"></span></span>
          <span class="comp-n">{r["count"]}</span>
        </div>'''
    return card("Component & Data-Store Risk", f'<div class="comp-list">{out}</div>',
                sub="findings.asset_refs → recon components/data-stores (max severity · finding count)",
                tag=f"{len(rows)}")


def sec_supply(m):
    sc = m["supply_chain"]
    if not sc:
        return card("Supply-Chain / External Dependencies", empty())
    cards = ""
    for e in sc:
        man = f'<code>{esc(e["manifest"])}</code>' if e["manifest"] else '<span class="muted">no manifest</span>'
        cards += f'''<div class="dep reveal">
          <div class="dep-head"><b>{esc(e["name"])}</b><span class="dep-id">{esc(e["id"])}</span></div>
          <div class="dep-tech">{esc(e["tech"])}</div>
          <div class="dep-risk">{esc(e["risk"])}</div>
          <div class="dep-man">{man}</div>
        </div>'''
    return card("Supply-Chain / External Dependencies", f'<div class="deps">{cards}</div>', tag=f"{len(sc)}",
                sub="recon.external_deps[]")


def sec_findings(m):
    F = m["findings"]
    if not F:
        return card("Findings & Evidence", empty("No findings emitted"))
    out = ""
    for f in F:
        stride = "".join(f'<span class="mini">{esc(s)}</span>' for s in f["stride"])
        cwe = "".join(f'<span class="mini alt">{esc(c)}</span>' for c in f["cwe"])
        mitre = "".join(f'<span class="mini alt2">{esc(x)}</span>' for x in f["mitre"])
        assets = ", ".join(esc(a) for a in f["assets"][:6]) or "—"
        out += f'''<details class="finding reveal" data-fid="{esc(f["id"])}" data-pivot="finding" data-sev="{SEV_CLASS.get(f["sev"],"none")}">
          <summary>
            <span class="sev-pill {SEV_CLASS.get(f["sev"],"none")}">{esc(f["sev"])}</span>
            <span class="f-id">{esc(f["id"])}</span>
            <span class="f-title">{esc(f["title"])}</span>
            <span class="f-risk" title="likelihood×impact">L{esc(f["l"])}·I{esc(f["i"])} = {esc(f["risk"])}</span>
          </summary>
          <div class="f-body">
            <div class="f-chips">{stride}{cwe}{mitre}</div>
            <div class="f-field"><span>Attack path</span><p>{esc(f["attack"])}</p></div>
            <div class="f-field"><span>Remediation</span><p>{esc(f["remediation"])}</p></div>
            <div class="f-field"><span>Assets</span><p class="muted">{assets}</p></div>
            {ev_block(f.get("evidence") or [])}
          </div>
        </details>'''
    return card("Findings & Evidence", f'<div class="findings">{out}</div>',
                sub="Every field from findings.json — ranked by severity then likelihood×impact",
                tag=f"{len(F)}")


def sec_absent(m):
    e = m["empty"]
    blocks = []
    if e["controls"]:
        blocks.append(card("Threat → Control Coverage", empty(
            "No control mappings surfaced",
            "findings.controls[] absent in this run — remediation text is the only control signal"),
            cls="half"))
    if e["cvss"]:
        blocks.append(card("CVSS Exploitability", empty(
            "No CVSS vectors surfaced", "findings.cvss_vector absent — likelihood (1–5) is the exploitability proxy"),
            cls="half"))
    if e["atlas"]:
        blocks.append(card("MITRE ATLAS (AI/ML)", empty(
            "Not an AI/ML system", "context.has_ai_ml = false — no ATLAS layer applicable"), cls="half"))
    if e["dataflows"]:
        blocks.append(card("Data-Flow Graph", empty(
            "No typed dataflows surfaced", "recon.dataflows[] absent in this run"), cls="half"))
    if e.get("evidence"):
        blocks.append(card("Embedded Evidence", empty(
            "No per-finding evidence surfaced",
            "findings[].evidence[] absent in this run — findings ground to recon component refs only"),
            cls="half"))
    return "".join(blocks)


def render(m):
    kpis = "".join([
        kpi("Findings", m["counts"]["findings"], "identified & validated", "cyan"),
        kpi("High Severity", m["severity"]["HIGH"] + m["severity"]["CRITICAL"], "HIGH + CRITICAL", "red"),
        kpi("Coverage", int(m["coverage"]["present_pct"] or 0), "evidence-backed", "teal", suffix="<i>%</i>"),
        kpi("Attack Paths", m["counts"]["kill_chains"], "kill chains", "purple"),
        kpi("Assets Examined", m["counts"]["assets_examined"], "components + data stores", "amber"),
        kpi("Trust Boundaries", m["counts"]["trust_boundaries"], "analysed", "cyan"),
    ])
    posture = m["posture"]
    body = "".join([
        sec_profile(m),
        f'<div class="grid grid-1">{sec_diagram(m)}</div>',
        f'<div class="grid grid-2">{sec_severity(m)}{sec_heatmap(m)}</div>',
        f'<div class="grid grid-1">{sec_coverage(m)}</div>',
        f'<div class="grid grid-2">{sec_stride(m)}{sec_chains(m)}</div>',
        f'<div class="grid grid-2">{sec_frameworks(m)}</div>',
        f'<div class="grid grid-2">{sec_components(m)}{sec_supply(m)}</div>',
        f'<div class="grid grid-1">{sec_findings(m)}</div>',
        f'<div class="grid grid-2 absent-grid">{sec_absent(m)}</div>',
    ])
    data_js = json.dumps({"generated_by": m["generated_by"], "merged_by": m["merged_by"],
                          "links": m["links"], "findings": m["findings_by_id"],
                          "entities": m.get("entity_meta", {}), "top": m.get("top_entity")})
    repl = {
        "%%TITLE%%": esc(m["system_name"]), "%%DESC%%": esc(m["description"]),
        "%%PATTERN%%": esc(m["pattern"] or "system"), "%%GENERATED%%": esc(m["generated"] or "—"),
        "%%POSTURE_BAND%%": esc(posture["band"]), "%%POSTURE_CLS%%": posture_class(posture["band"]),
        "%%POSTURE_SCORE%%": str(posture["score"]), "%%KPIS%%": kpis, "%%BODY%%": body,
        "%%GEN_BY%%": esc(m["generated_by"]), "%%MERGED_BY%%": esc(m["merged_by"]),
        "%%CSS%%": CSS, "%%JS%%": JS.replace("__DATA__", data_js),
    }
    out = TEMPLATE
    for k, v in repl.items():
        out = out.replace(k, v)
    return out


def posture_class(band):
    return {"CRITICAL": "crit", "HIGH RISK": "high", "ELEVATED": "high",
            "MODERATE": "med", "LOW": "low", "NO FINDINGS": "none"}.get(band, "med")


CSS = r"""
:root{
  --void:#050709; --deep:#0b0e14; --surface:#10141c; --elevated:#161c28; --card:#1a2232;
  --border:rgba(255,255,255,.07); --border-hi:rgba(255,255,255,.12);
  --text-1:#edf0f5; --text-2:#a0aec0; --text-3:#6b7a8d; --text-4:#3a4250;
  --cyan:#22d3ee; --teal:#2dd4bf; --purple:#a78bfa; --amber:#fbbf24; --red:#f87171;
  /* severity ramp is CVD-safe: warm run broken, MEDIUM=violet, LOW=cool sky.
     order carried by hue+lightness+always-present label, never hue alone. */
  --crit:#ff4d6d; --high:#fb923c; --med:#b98cff; --low:#38bdf8; --none:#4a5568;
  --grad:linear-gradient(135deg,var(--cyan),var(--teal));
  --grad-h:linear-gradient(135deg,var(--purple),var(--cyan));
  --sans:'DM Sans',system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  --serif:'Instrument Serif',Georgia,'Times New Roman',serif;
  --mono:'IBM Plex Mono','SF Mono',ui-monospace,Consolas,monospace;
  --ease:cubic-bezier(.16,1,.3,1);
  --shadow:0 8px 40px rgba(0,0,0,.4);
}
[data-theme=light]{
  --void:#eef1f6; --deep:#e6eaf1; --surface:#ffffff; --elevated:#f7f9fc; --card:#ffffff;
  --border:rgba(10,20,40,.09); --border-hi:rgba(10,20,40,.16);
  --text-1:#0f1722; --text-2:#3a4658; --text-3:#647084; --text-4:#9aa6b6;
  --cyan:#0891b2; --teal:#0d9488; --purple:#7c3aed;
  --crit:#d91e46; --high:#d97706; --med:#7c5cff; --low:#0284c7; --none:#94a3b8;
  --shadow:0 8px 30px rgba(20,30,50,.10);
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
[hidden]{display:none!important}
html{scroll-behavior:smooth;-webkit-font-smoothing:antialiased}
body{font-family:var(--sans);background:var(--void);color:var(--text-2);line-height:1.55;
  overflow-x:hidden;transition:background .4s,color .4s}
h1,h2,h3{color:var(--text-1);font-weight:600;letter-spacing:-.02em}
b{color:var(--text-1);font-weight:600}
code{font-family:var(--mono);font-size:.82em;color:var(--cyan)}
.muted{color:var(--text-3)}
i{font-style:normal}
/* ambient bg */
.bg{position:fixed;inset:0;z-index:-2;overflow:hidden}
.bg::before{content:'';position:absolute;width:60vw;height:60vw;left:-10vw;top:-20vw;border-radius:50%;
  background:radial-gradient(circle,rgba(34,211,238,.16),transparent 65%);filter:blur(40px);
  animation:float1 24s var(--ease) infinite alternate}
.bg::after{content:'';position:absolute;width:55vw;height:55vw;right:-15vw;bottom:-15vw;border-radius:50%;
  background:radial-gradient(circle,rgba(167,139,250,.14),transparent 65%);filter:blur(40px);
  animation:float2 30s var(--ease) infinite alternate}
@keyframes float1{to{transform:translate(8vw,6vw) scale(1.15)}}
@keyframes float2{to{transform:translate(-6vw,-5vw) scale(1.1)}}
.noise{position:fixed;inset:0;z-index:-1;pointer-events:none;opacity:.02;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
/* header */
.top{position:sticky;top:0;z-index:50;backdrop-filter:blur(20px) saturate(140%);
  background:color-mix(in srgb,var(--void) 78%,transparent);border-bottom:1px solid var(--border);
  padding:14px clamp(18px,4vw,52px);display:flex;align-items:center;gap:16px}
.mark{width:34px;height:34px;border-radius:9px;background:var(--grad);display:grid;place-items:center;
  font-family:var(--mono);font-weight:700;color:var(--void);font-size:15px;box-shadow:0 0 24px var(--cyan)}
.brand{display:flex;flex-direction:column;line-height:1.15}
.brand b{font-size:14px}
.brand span{font-size:11px;color:var(--text-3);letter-spacing:.14em;text-transform:uppercase}
.top-right{margin-left:auto;display:flex;align-items:center;gap:14px}
.ground{font-size:11px;color:var(--text-3);display:flex;align-items:center;gap:6px}
.ground b{color:var(--teal)}
.theme-btn{background:var(--elevated);border:1px solid var(--border-hi);color:var(--text-1);
  width:38px;height:38px;border-radius:9px;cursor:pointer;font-size:16px;transition:.2s}
.theme-btn:hover{border-color:var(--cyan);box-shadow:0 0 16px var(--cyan)}
/* hero */
.hero{padding:clamp(36px,6vw,72px) clamp(18px,4vw,52px) 20px;max-width:1280px;margin:0 auto}
.eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.2em;text-transform:uppercase;color:var(--cyan)}
.hero h1{font-family:var(--serif);font-size:clamp(34px,6vw,60px);line-height:1.02;margin:14px 0 10px;font-weight:400}
.hero .lede{max-width:760px;font-size:15px;color:var(--text-2)}
.posture{display:inline-flex;align-items:center;gap:14px;margin-top:22px;padding:14px 22px;border-radius:14px;
  background:var(--surface);border:1px solid var(--border-hi);box-shadow:var(--shadow)}
.posture .p-band{font-family:var(--mono);font-weight:600;font-size:15px;letter-spacing:.08em}
.posture .p-meter{width:180px;height:8px;border-radius:6px;background:var(--elevated);overflow:hidden}
.posture .p-meter i{display:block;height:100%;width:0;border-radius:6px;transition:width 1.6s var(--ease) .3s}
.p-band.crit,.p-meter.crit i,.sev-pill.crit,.dot.crit{color:var(--crit)}
.posture.crit .p-meter i{background:var(--crit)} .posture.high .p-meter i{background:var(--high)}
.posture.med .p-meter i{background:var(--med)} .posture.low .p-meter i{background:var(--low)}
.p-band.high{color:var(--high)} .p-band.med{color:var(--med)} .p-band.low{color:var(--low)} .p-band.none{color:var(--none)}
/* kpi band */
.kpis{display:grid;grid-template-columns:repeat(6,1fr);gap:14px;max-width:1280px;margin:26px auto 0;
  padding:0 clamp(18px,4vw,52px)}
.kpi{background:var(--surface);border:1px solid var(--border);border-radius:14px;padding:18px 18px 16px;
  position:relative;overflow:hidden;transition:transform .3s var(--ease),border-color .3s}
.kpi::before{content:'';position:absolute;inset:0 auto auto 0;width:100%;height:3px;background:var(--grad);
  transform:scaleX(0);transform-origin:left;transition:transform .6s var(--ease)}
.kpi.in::before{transform:scaleX(1)}
.kpi:hover{transform:translateY(-4px);border-color:var(--border-hi)}
.kpi[data-accent=red]::before{background:linear-gradient(135deg,var(--crit),var(--high))}
.kpi[data-accent=teal]::before{background:linear-gradient(135deg,var(--teal),var(--low))}
.kpi[data-accent=purple]::before{background:linear-gradient(135deg,var(--purple),var(--cyan))}
.kpi[data-accent=amber]::before{background:linear-gradient(135deg,var(--amber),var(--high))}
.kpi-val{font-family:var(--serif);font-size:clamp(30px,4vw,44px);color:var(--text-1);line-height:1}
.kpi-val i{font-size:.5em;color:var(--text-3)}
.kpi-label{font-size:12.5px;font-weight:600;color:var(--text-1);margin-top:8px;letter-spacing:.02em}
.kpi-sub{font-size:11px;color:var(--text-3);margin-top:2px}
/* layout */
main{max-width:1280px;margin:0 auto;padding:34px clamp(18px,4vw,52px) 80px}
.grid{display:grid;gap:18px;margin-bottom:18px}
.grid-1{grid-template-columns:1fr}
.grid-2{grid-template-columns:1fr 1fr}
.profile{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:18px}
.profile-lab{font-size:12px;color:var(--text-3);text-transform:uppercase;letter-spacing:.12em;margin-right:6px}
.chip{font-size:12px;padding:5px 11px;border-radius:20px;border:1px solid var(--border);font-family:var(--mono)}
.chip.on{color:var(--cyan);border-color:color-mix(in srgb,var(--cyan) 40%,transparent);
  background:color-mix(in srgb,var(--cyan) 10%,transparent)}
.chip.off{color:var(--text-4);text-decoration:line-through;opacity:.6}
/* card */
.card{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:22px 24px;
  box-shadow:var(--shadow);position:relative;overflow:hidden}
.card.half{padding:20px}
.card-head{display:flex;flex-direction:column;gap:3px;margin-bottom:18px}
.card-head h2{font-size:16px;display:flex;align-items:center;gap:10px}
.card-tag{font-family:var(--mono);font-size:11px;font-weight:600;color:var(--cyan);
  background:color-mix(in srgb,var(--cyan) 12%,transparent);padding:2px 8px;border-radius:6px}
.card-sub{font-size:12px;color:var(--text-3)}
/* empty */
.empty{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;
  padding:34px 16px;text-align:center;border:1px dashed var(--border-hi);border-radius:12px;
  background:repeating-linear-gradient(45deg,transparent,transparent 10px,color-mix(in srgb,var(--text-4) 5%,transparent) 10px,color-mix(in srgb,var(--text-4) 5%,transparent) 20px)}
.empty-dash{font-family:var(--serif);font-size:38px;color:var(--text-4);line-height:1}
.empty-msg{font-size:13px;color:var(--text-3);font-weight:600}
.empty-note{font-size:11.5px;color:var(--text-4);max-width:320px}
/* donut */
.donut-wrap{display:flex;align-items:center;gap:28px;flex-wrap:wrap}
.donut{width:168px;height:168px;border-radius:50%;background:var(--conic);position:relative;
  -webkit-mask:radial-gradient(circle 52px at center,transparent 98%,#000 100%);
  mask:radial-gradient(circle 52px at center,transparent 98%,#000 100%);
  transform:rotate(-90deg) scale(.6);opacity:0;transition:transform 1.1s var(--ease),opacity .6s}
.donut.in{transform:rotate(-90deg) scale(1);opacity:1}
.donut-hole{position:absolute;inset:0;display:grid;place-content:center;text-align:center;transform:rotate(90deg)}
.donut-hole .counter{font-family:var(--serif);font-size:40px;color:var(--text-1);line-height:1}
.donut-hole small{font-size:11px;color:var(--text-3);display:block}
.legend{list-style:none;display:flex;flex-direction:column;gap:9px;font-size:13px}
.legend-wrap{flex-direction:row;flex-wrap:wrap;gap:6px 16px;margin-top:12px}
.legend li{display:flex;align-items:center;gap:9px;color:var(--text-2)}
.legend b{margin-left:auto;font-family:var(--mono)}
.legend-wrap b{margin-left:5px}
.dot{width:11px;height:11px;border-radius:3px;flex:none}
.dot.crit{background:var(--crit)} .dot.high{background:var(--high)} .dot.med{background:var(--med)}
.dot.low{background:var(--low)} .dot.none{background:var(--none)}
/* heatmap */
.heatmap{display:grid;grid-template-columns:auto 1fr;grid-template-rows:1fr auto;gap:8px;align-items:center}
.hm-grid{grid-column:2;display:grid;grid-template-columns:repeat(5,1fr);grid-template-rows:repeat(5,1fr);
  gap:5px;aspect-ratio:1.15}
.hm-ylabel{grid-row:1;writing-mode:vertical-rl;transform:rotate(180deg);font-size:11px;color:var(--text-3);
  text-transform:uppercase;letter-spacing:.1em;justify-self:center}
.hm-xlabel{grid-column:2;text-align:center;font-size:11px;color:var(--text-3);text-transform:uppercase;letter-spacing:.1em}
.hm-cell{border-radius:7px;display:grid;place-content:center;position:relative;min-height:34px;
  background:color-mix(in srgb,var(--none) calc(var(--i)*100%),var(--elevated));
  border:1px solid var(--border);opacity:0;transform:scale(.7);transition:opacity .4s,transform .4s var(--ease)}
.hm-cell.in{opacity:1;transform:scale(1)}
.hm-cell.crit{background:color-mix(in srgb,var(--crit) calc(var(--i)*100%),var(--elevated))}
.hm-cell.high{background:color-mix(in srgb,var(--high) calc(var(--i)*100%),var(--elevated))}
.hm-cell.med{background:color-mix(in srgb,var(--med) calc(var(--i)*100%),var(--elevated))}
.hm-cell.low{background:color-mix(in srgb,var(--low) calc(var(--i)*90%),var(--elevated))}
.hm-n{font-family:var(--mono);font-weight:600;color:#fff;font-size:14px;mix-blend-mode:difference}
/* bars */
.bars{display:flex;flex-direction:column;gap:11px}
.bar-row{display:grid;grid-template-columns:150px 1fr;gap:12px;align-items:center}
.bar-row.sm{grid-template-columns:90px 1fr}
.bar-lab{font-size:12.5px;color:var(--text-2)}
.bar-lab b{font-family:var(--mono);color:var(--cyan);margin-right:4px}
.bar-track{height:26px;background:var(--elevated);border-radius:7px;overflow:hidden}
.bar-fill{height:100%;width:0;background:var(--grad);border-radius:7px;display:flex;align-items:center;
  justify-content:flex-end;padding-right:9px;transition:width 1.1s var(--ease)}
.bar-fill.in{width:var(--w)}
.bar-fill.alt{background:linear-gradient(135deg,var(--purple),var(--cyan))}
.bar-fill span{font-family:var(--mono);font-size:12px;color:var(--void);font-weight:600}
/* coverage */
.cov-top{display:flex;gap:26px;align-items:center;flex-wrap:wrap}
.cov-right{flex:1;min-width:280px}
.cov-headline{font-size:14px;margin-bottom:12px}
.cov-headline b{font-family:var(--serif);font-size:22px;color:var(--teal)}
.gauge{position:relative;width:132px;height:132px;flex:none}
.gauge svg{transform:rotate(-90deg);width:100%;height:100%}
.gauge circle{fill:none;stroke-width:9}
.g-bg{stroke:var(--elevated)}
.g-fg{stroke:url(#gg);stroke-linecap:round;stroke-dasharray:100;stroke-dashoffset:100;
  transition:stroke-dashoffset 1.6s var(--ease) .3s;stroke:var(--teal)}
.gauge.in .g-fg{stroke-dashoffset:calc(100 - var(--pct))}
.gauge-c{position:absolute;inset:0;display:grid;place-content:center;text-align:center}
.gauge-c .counter{font-family:var(--serif);font-size:32px;color:var(--text-1)}
.gauge-c i{color:var(--text-3);font-size:18px} .gauge-c small{display:block;font-size:10px;color:var(--text-3)}
.stack{display:flex;height:30px;border-radius:8px;overflow:hidden;background:var(--elevated)}
.stack-seg{height:100%;width:0;display:grid;place-content:center;transition:width 1.1s var(--ease);overflow:hidden}
.stack-seg.in{width:var(--w)}
.stack-seg span{font-family:var(--mono);font-size:11px;color:var(--void);font-weight:600}
.stack-seg.low{background:var(--low)} .stack-seg.med{background:var(--med)}
.stack-seg.high{background:var(--high)} .stack-seg.none{background:var(--none)}
.cat-grid-label{font-size:12px;color:var(--text-3);margin:18px 0 10px;text-transform:uppercase;letter-spacing:.1em}
.cat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px}
.cat{background:var(--elevated);border-radius:8px;padding:9px 10px;border:1px solid var(--border)}
.cat-bar{height:5px;border-radius:4px;background:var(--none);width:0;transition:width 1s var(--ease)}
.cat-bar.in{width:var(--p)} .cat-bar.low{background:var(--low)} .cat-bar.med{background:var(--med)} .cat-bar.high{background:var(--high)}
.cat-name{font-size:10.5px;color:var(--text-2);margin-top:7px;line-height:1.25;text-transform:capitalize}
.cat-pct{font-family:var(--mono);font-size:11px;color:var(--text-3)}
/* techs */
.techs{display:flex;flex-wrap:wrap;gap:8px}
.tech{font-family:var(--mono);font-size:12px;padding:6px 10px;border-radius:8px;color:var(--text-1);
  border:1px solid var(--border-hi);
  background:color-mix(in srgb,var(--crit) calc(var(--i)*55%),var(--elevated))}
.tech b{margin-left:6px;color:var(--void);background:#fff;border-radius:5px;padding:0 5px;font-size:11px}
[data-theme=light] .tech b{background:var(--text-1);color:#fff}
/* kill chains */
.kc{background:var(--elevated);border:1px solid var(--border);border-radius:12px;padding:14px 16px;margin-bottom:12px}
.kc-head{display:flex;align-items:baseline;gap:10px;margin-bottom:11px}
.kc-id{font-family:var(--mono);font-weight:600;color:var(--cyan)}
.kc-goal{font-size:13px;color:var(--text-2)}
.kc-flow{display:flex;flex-wrap:wrap;align-items:center;gap:7px}
.kc-step{font-family:var(--mono);font-size:11.5px;padding:5px 9px;border-radius:7px;border:1px solid var(--border-hi);
  background:var(--surface);position:relative;transition:transform .2s}
.kc-step:hover{transform:translateY(-2px)}
.kc-step.crit{border-color:var(--crit);color:var(--crit)} .kc-step.high{border-color:var(--high);color:var(--high)}
.kc-step.med{border-color:var(--med);color:var(--med)} .kc-step.low{border-color:var(--low);color:var(--low)}
.kc-arrow{color:var(--text-3);font-size:14px}
/* components */
.comp-list{display:flex;flex-direction:column;gap:8px}
.comp-row{display:grid;grid-template-columns:76px 1fr 90px 28px;gap:12px;align-items:center;font-size:13px}
.comp-name i{font-family:var(--mono);font-size:11px;color:var(--text-4);margin-left:4px}
.comp-bar{height:7px;background:var(--elevated);border-radius:5px;overflow:hidden}
.comp-bar span{display:block;height:100%;width:0;background:var(--grad);border-radius:5px;transition:width 1s var(--ease)}
.comp-bar span.in{width:var(--w)}
.comp-n{font-family:var(--mono);text-align:right;color:var(--text-2)}
.sev-pill{font-family:var(--mono);font-size:10.5px;font-weight:600;padding:3px 8px;border-radius:6px;text-align:center;
  border:1px solid currentColor}
.sev-pill.crit{color:var(--crit)} .sev-pill.high{color:var(--high)} .sev-pill.med{color:var(--med)}
.sev-pill.low{color:var(--low)} .sev-pill.none{color:var(--none)}
/* deps */
.deps{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.dep{background:var(--elevated);border:1px solid var(--border);border-radius:12px;padding:14px;border-left:3px solid var(--amber)}
.dep-head{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.dep-id{font-family:var(--mono);font-size:11px;color:var(--text-4)}
.dep-tech{font-size:11.5px;color:var(--text-3);margin:3px 0 8px}
.dep-risk{font-size:12.5px;color:var(--text-2)}
.dep-man{margin-top:8px;font-size:11px}
/* findings */
.findings{display:flex;flex-direction:column;gap:8px}
.finding{background:var(--elevated);border:1px solid var(--border);border-radius:12px;overflow:hidden;
  border-left:3px solid var(--none)}
.finding[data-sev=crit]{border-left-color:var(--crit)} .finding[data-sev=high]{border-left-color:var(--high)}
.finding[data-sev=med]{border-left-color:var(--med)} .finding[data-sev=low]{border-left-color:var(--low)}
.finding summary{display:grid;grid-template-columns:76px 62px 1fr auto;gap:12px;align-items:center;
  padding:13px 16px;cursor:pointer;list-style:none}
.finding summary::-webkit-details-marker{display:none}
.finding summary:hover{background:color-mix(in srgb,var(--cyan) 5%,transparent)}
.f-id{font-family:var(--mono);font-size:12px;color:var(--cyan)}
.f-title{font-size:13.5px;color:var(--text-1);font-weight:500}
.f-risk{font-family:var(--mono);font-size:11px;color:var(--text-3);white-space:nowrap}
.f-body{padding:4px 16px 16px;border-top:1px solid var(--border)}
.f-chips{display:flex;flex-wrap:wrap;gap:6px;margin:12px 0}
.mini{font-family:var(--mono);font-size:10.5px;padding:2px 7px;border-radius:5px;background:var(--surface);
  border:1px solid var(--border-hi);color:var(--cyan)}
.mini.alt{color:var(--purple)} .mini.alt2{color:var(--amber)}
.f-field{margin-top:10px}
.f-field span{font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:var(--text-3);display:block;margin-bottom:3px}
.f-field p{font-size:13px;color:var(--text-2);line-height:1.5}
/* embedded evidence (finding -> assured proof: snippet + findable reference + jump-to-node) */
.evidence-list{display:flex;flex-direction:column;gap:8px}
.ev-item{background:var(--void,#0b0f16);border:1px solid var(--border);border-radius:9px;overflow:hidden}
.ev-head{display:flex;align-items:center;gap:8px;flex-wrap:wrap;padding:7px 10px;background:color-mix(in srgb,var(--cyan) 6%,transparent);border-bottom:1px solid var(--border)}
.ev-ref{font-family:var(--mono,ui-monospace,"IBM Plex Mono",Menlo,monospace);font-size:11.5px;color:var(--cyan);word-break:break-all}
.ev-tag{font-size:9.5px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-3);border:1px solid var(--border);border-radius:5px;padding:1px 6px}
.ev-tag.warn{color:var(--amber,#e0a);border-color:var(--amber,#e0a)}
.ev-jump{margin-left:auto;background:none;border:1px solid var(--border);border-radius:6px;color:var(--teal,#5ec8c8);font-size:11px;cursor:pointer;padding:2px 8px;font-family:inherit}
.ev-jump:hover{border-color:var(--teal,#5ec8c8);background:color-mix(in srgb,var(--teal,#5ec8c8) 12%,transparent)}
.ev-code{margin:0;padding:9px 11px;font-family:var(--mono,ui-monospace,"IBM Plex Mono",Menlo,monospace);font-size:11.5px;line-height:1.55;color:var(--text-2);overflow-x:auto;white-space:pre;tab-size:2}
.ev-code code{color:inherit}
.ev-quote{margin:0;padding:9px 12px;border-left:3px solid var(--teal,#5ec8c8);font-size:12.5px;color:var(--text-2);line-height:1.55;white-space:pre-wrap}
.ev-item.ev-none{border-style:dashed}.ev-item.ev-none p,.ev-item.ev-unres{padding:8px 11px;font-size:12px}
.ev-item.ev-unres{border-color:var(--amber,#e0a)}
/* footer */
.foot{max-width:1280px;margin:0 auto;padding:26px clamp(18px,4vw,52px) 60px;border-top:1px solid var(--border);
  font-size:12px;color:var(--text-3);display:flex;flex-wrap:wrap;gap:8px 24px}
.foot b{color:var(--teal)}
/* reveal */
.reveal{opacity:0;transform:translateY(22px);transition:opacity .7s var(--ease),transform .7s var(--ease)}
.reveal.in{opacity:1;transform:none}
@media (max-width:900px){.kpis{grid-template-columns:repeat(3,1fr)}.grid-2{grid-template-columns:1fr}
  .deps{grid-template-columns:1fr}}
@media (max-width:560px){.kpis{grid-template-columns:repeat(2,1fr)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition-duration:.01ms!important}
  .reveal{opacity:1;transform:none}.bar-fill{width:var(--w)}.stack-seg{width:var(--w)}
  .donut{opacity:1;transform:rotate(-90deg)}.hm-cell{opacity:1;transform:none}}
/* ---- interactive system-map diagram ---- */
.diagram-card .card-body{padding:0}
.diag-toolbar{display:flex;align-items:center;gap:6px;padding:4px 0 12px}
.diag-toolbar button{width:30px;height:30px;border-radius:8px;background:var(--elevated);
  border:1px solid var(--border-hi);color:var(--text-1);cursor:pointer;font-size:15px;transition:.2s}
.diag-toolbar button:hover{border-color:var(--cyan);color:var(--cyan)}
.diag-hint{font-size:11px;color:var(--text-4);margin-left:8px}
.diag-viewport{height:440px;border:1px solid var(--border);border-radius:12px;overflow:hidden;
  background:radial-gradient(circle at 30% 10%,color-mix(in srgb,var(--cyan) 6%,transparent),transparent 60%),var(--elevated);
  cursor:grab;touch-action:none}
.diag-viewport:active{cursor:grabbing}
#diagSVG{width:100%;height:100%;display:block}
#diagView{transition:transform .12s linear}
/* embedded real visual-engine SVG: keep D2's picture pixel-identical, only add behaviour */
#diagView.embed-view{transform-origin:0 0;width:100%;height:100%;will-change:transform}
/* ---- secondary "more diagrams" links (open/expand on demand — not a front gallery) ---- */
.more-diagrams{margin-top:14px;border-top:1px solid var(--border);padding-top:12px}
.more-diagrams>summary{cursor:pointer;font:600 12.5px/1.3 var(--sans);color:var(--text-2);letter-spacing:.01em;
  list-style:none;display:flex;align-items:center;gap:8px}
.more-diagrams>summary::-webkit-details-marker{display:none}
.more-diagrams>summary::before{content:"▸";color:var(--text-3);transition:.15s}
.more-diagrams[open]>summary::before{transform:rotate(90deg)}
.more-count{display:inline-grid;place-items:center;min-width:18px;height:18px;padding:0 5px;border-radius:6px;
  background:var(--surface);border:1px solid var(--border-hi);font:600 10px/1 var(--mono);color:var(--text-3)}
.more-list{display:flex;flex-direction:column;gap:6px;margin-top:10px}
.more-item{border:1px solid var(--border);border-radius:10px;background:var(--elevated);overflow:hidden}
.more-item>summary{cursor:pointer;padding:9px 12px;display:flex;align-items:center;gap:10px;
  font:600 12px/1 var(--sans);color:var(--text-2);list-style:none}
.more-item>summary::-webkit-details-marker{display:none}
.more-item>summary::before{content:"+";color:var(--cyan);font:600 14px/1 var(--mono)}
.more-item[open]>summary::before{content:"−"}
.more-item[open]>summary{border-bottom:1px solid var(--border)}
.more-file{font:500 10.5px/1 var(--mono);color:var(--text-3)}
.more-badge{margin-left:auto;font:600 10px/1 var(--mono);color:var(--text-3);
  background:var(--surface);border:1px solid var(--border-hi);border-radius:6px;padding:3px 6px}
.more-svg{max-height:70vh;overflow:auto;padding:10px;background:var(--elevated)}
.more-svg>svg{display:block;width:100%;height:auto}
.node.embed{cursor:pointer;transition:opacity .2s,filter .2s}
.node.embed:hover,.node.embed:focus{filter:drop-shadow(0 0 8px var(--cyan));outline:none}
.filtering .node.embed:not(.hot){opacity:.28}
.node.embed.hot{filter:drop-shadow(0 0 10px var(--cyan))}
.lane-cap{fill:var(--text-3);font:600 11px/1 var(--mono);text-transform:uppercase;letter-spacing:.12em}
.node{cursor:pointer}
.node .node-box{fill:var(--surface);stroke:var(--border-hi);stroke-width:1.5;transition:stroke .2s,filter .2s}
.node.sev-crit .node-box{stroke:var(--crit)} .node.sev-high .node-box{stroke:var(--high)}
.node.sev-med .node-box{stroke:var(--med)} .node.sev-low .node-box{stroke:var(--low)}
.node .node-id{fill:var(--cyan);font:600 12px/1 var(--mono)}
.node .node-name{fill:var(--text-2);font:400 10.5px/1 var(--sans)}
.node .node-badge{fill:var(--text-1);font:600 12px/1 var(--mono)}
.node:hover .node-box,.node:focus .node-box{filter:drop-shadow(0 0 8px var(--cyan));stroke:var(--cyan)}
.edge{fill:none;stroke:var(--border-hi);stroke-width:1.5;opacity:.4;transition:opacity .2s,stroke .2s}
.edge.et-control{stroke-dasharray:4 3}
.edge.et-build{stroke:var(--amber);opacity:.5} .edge.et-async{stroke:var(--teal);opacity:.5}
.edge.et-admin{stroke:var(--crit);stroke-dasharray:4 3;opacity:.55}
.arh{fill:var(--border-hi)}
/* trust zones (the run's real containers) */
.zone rect{fill:color-mix(in srgb,var(--cyan) 4%,transparent);stroke:var(--border-hi);stroke-dasharray:5 4;
  stroke-width:1}
.zone.d1 rect{fill:color-mix(in srgb,var(--purple) 5%,transparent)}
.zone.d2 rect{fill:color-mix(in srgb,var(--amber) 5%,transparent)}
.zone-cap{fill:var(--text-3);font:600 11px/1 var(--mono);letter-spacing:.06em}
/* cross-filter states (shared selection) */
.filtering .node:not(.hot) .node-box{opacity:.28}
.filtering .edge:not(.hot){opacity:.06}
.node.hot .node-box{stroke-width:2.5;filter:drop-shadow(0 0 10px currentColor)}
.edge.hot{opacity:.9;stroke:var(--cyan);stroke-width:2}
[data-pivot]{cursor:pointer}
.filtering [data-pivot]:not(.hot){opacity:.32;transition:opacity .2s}
[data-pivot].hot{outline:1px solid color-mix(in srgb,var(--cyan) 50%,transparent);outline-offset:2px;border-radius:8px}
.finding.hot{box-shadow:0 0 0 1px var(--cyan),0 0 24px -6px var(--cyan)}
.flash{animation:flash 1.1s var(--ease)}
@keyframes flash{0%,100%{box-shadow:0 0 0 0 transparent}30%{box-shadow:0 0 0 2px var(--cyan),0 0 26px -4px var(--cyan)}}
/* focus bar */
.focusbar{position:sticky;top:62px;z-index:45;display:flex;align-items:center;gap:12px;
  margin:10px clamp(14px,4vw,48px);padding:9px 16px;border-radius:12px;
  background:color-mix(in srgb,var(--surface) 92%,transparent);border:1px solid var(--cyan);
  backdrop-filter:blur(16px) saturate(140%);box-shadow:0 6px 24px -8px var(--cyan)}
.focusbar::before{content:'◈';color:var(--cyan)}
.focus-label{font-size:13px;color:var(--text-1);font-weight:600}
.focus-count{font-family:var(--mono);font-size:12px;color:var(--cyan);
  background:color-mix(in srgb,var(--cyan) 12%,transparent);padding:2px 9px;border-radius:20px}
.focus-clear{margin-left:auto;background:var(--elevated);border:1px solid var(--border-hi);
  color:var(--text-2);border-radius:7px;padding:5px 12px;font-size:12px;cursor:pointer}
.focus-clear:hover{color:var(--crit);border-color:var(--crit)}
/* tooltip */
.tooltip{position:fixed;z-index:200;pointer-events:none;max-width:300px;background:var(--card);
  border:1px solid var(--border-hi);border-radius:10px;padding:10px 12px;box-shadow:var(--shadow);
  font-size:12px;color:var(--text-2);opacity:0;transform:translateY(4px);transition:opacity .12s,transform .12s}
.tooltip.show{opacity:1;transform:none}
.tooltip b{display:block;color:var(--text-1);margin-bottom:3px}
.tooltip .tt-pill{font-family:var(--mono);font-size:10.5px;padding:1px 6px;border-radius:5px;
  border:1px solid currentColor;margin-right:5px}
.tt-pill.crit{color:var(--crit)}.tt-pill.high{color:var(--high)}.tt-pill.med{color:var(--med)}.tt-pill.low{color:var(--low)}
/* drawer */
.drawer{position:fixed;top:0;right:0;bottom:0;width:min(440px,90vw);z-index:210;background:var(--surface);
  border-left:1px solid var(--border-hi);box-shadow:-20px 0 60px rgba(0,0,0,.5);
  transform:translateX(100%);transition:transform .35s var(--ease);overflow-y:auto;padding:0}
.drawer.open{transform:none}
.drawer-head{position:sticky;top:0;background:var(--surface);display:flex;align-items:center;
  justify-content:space-between;padding:18px 22px;border-bottom:1px solid var(--border);font-weight:600;color:var(--text-1)}
.drawer-head button{background:none;border:none;color:var(--text-3);font-size:18px;cursor:pointer}
.drawer-head button:hover{color:var(--crit)}
.drawer-body{padding:18px 22px}
.drawer-scrim{position:fixed;inset:0;z-index:205;background:rgba(0,0,0,.4);backdrop-filter:blur(2px)}
.dr-f{display:grid;grid-template-columns:70px 1fr;gap:10px;align-items:center;padding:10px 0;
  border-bottom:1px solid var(--border);cursor:pointer}
.dr-f:hover{background:color-mix(in srgb,var(--cyan) 6%,transparent)}
.dr-f .f-id{font-family:var(--mono);font-size:11px}
.dr-field{margin:12px 0}
.dr-field span{font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:var(--text-3);display:block;margin-bottom:3px}
.dr-field p{font-size:13px;color:var(--text-2);line-height:1.5}
.dr-chips{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}

/* ============================ PREMIUM PASS (depth · gauge · threat-map console) ============================ */
/* depth: glass cards with a top highlight + layered shadow + faint surface gradient (theme-aware via tokens) */
.card{background:linear-gradient(180deg,color-mix(in srgb,var(--surface) 92%,var(--elevated)),var(--surface));
  box-shadow:var(--shadow),inset 0 1px 0 var(--border-hi)}
.card::after{content:'';position:absolute;inset:0 0 auto 0;height:1px;pointer-events:none;
  background:linear-gradient(90deg,transparent,var(--border-hi) 20%,var(--border-hi) 80%,transparent)}
.card-head h2{font-size:16.5px;letter-spacing:-.015em}
/* commanding hero: two columns (copy + radial posture gauge) */
.hero{display:grid;grid-template-columns:1fr auto;gap:clamp(22px,4vw,56px);align-items:center}
.hero-copy{min-width:0}
.hero h1{text-wrap:balance}
.posture-gauge{position:relative;width:clamp(168px,20vw,208px);aspect-ratio:1;flex:none;color:var(--none)}
.posture-gauge.crit{color:var(--crit)} .posture-gauge.high{color:var(--high)}
.posture-gauge.med{color:var(--med)} .posture-gauge.low{color:var(--low)} .posture-gauge.none{color:var(--none)}
.pg-halo{position:absolute;inset:6%;border-radius:50%;z-index:0;
  background:radial-gradient(circle,color-mix(in srgb,currentColor 26%,transparent),transparent 68%);filter:blur(22px);opacity:.75}
.posture-gauge svg{position:relative;z-index:1;width:100%;height:100%;transform:rotate(-90deg)}
.posture-gauge circle{fill:none;stroke-width:8}
.pg-track{stroke:var(--elevated)}
.pg-arc{stroke:currentColor;stroke-linecap:round;stroke-dasharray:100;stroke-dashoffset:100;
  transition:stroke-dashoffset 1.7s var(--ease) .35s;filter:drop-shadow(0 0 9px currentColor)}
.posture-gauge.in .pg-arc{stroke-dashoffset:calc(100 - var(--score))}
.pg-center{position:absolute;inset:0;z-index:2;display:grid;place-content:center;text-align:center;gap:1px}
.pg-score{font-family:var(--serif);font-size:clamp(40px,5vw,56px);line-height:.85;color:var(--text-1)}
.pg-band{font-family:var(--mono);font-size:11.5px;font-weight:600;letter-spacing:.09em}
.pg-cap{font-size:9.5px;color:var(--text-3);text-transform:uppercase;letter-spacing:.16em}
/* KPI: severity-tinted glow behind the number, content above it */
.kpi>*{position:relative;z-index:1}
.kpi::after{content:'';position:absolute;right:-24%;top:-64%;width:130px;height:130px;border-radius:50%;z-index:0;
  pointer-events:none;filter:blur(26px);opacity:.55;
  background:radial-gradient(circle,color-mix(in srgb,var(--cyan) 24%,transparent),transparent 70%)}
.kpi[data-accent=red]::after{background:radial-gradient(circle,color-mix(in srgb,var(--crit) 30%,transparent),transparent 70%)}
.kpi[data-accent=teal]::after{background:radial-gradient(circle,color-mix(in srgb,var(--teal) 26%,transparent),transparent 70%)}
.kpi[data-accent=purple]::after{background:radial-gradient(circle,color-mix(in srgb,var(--purple) 26%,transparent),transparent 70%)}
.kpi[data-accent=amber]::after{background:radial-gradient(circle,color-mix(in srgb,var(--amber) 26%,transparent),transparent 70%)}
.kpi-val{font-variant-numeric:tabular-nums}
/* ---- the threat-map console: big glass viewer + Asset Inspector ---- */
.diag-split{display:grid;grid-template-columns:1.62fr 1fr;gap:18px;align-items:start}
.diag-main{min-width:0;display:flex;flex-direction:column}
.diag-viewport{position:relative;height:clamp(520px,58vh,600px);border-radius:14px;
  border:1px solid var(--border-hi);
  background:
    linear-gradient(color-mix(in srgb,var(--text-2) 5%,transparent) 1px,transparent 1px) -1px -1px/30px 30px,
    linear-gradient(90deg,color-mix(in srgb,var(--text-2) 5%,transparent) 1px,transparent 1px) -1px -1px/30px 30px,
    radial-gradient(120% 90% at 50% -10%,color-mix(in srgb,var(--cyan) 9%,transparent),transparent 60%),
    var(--elevated)}
.diag-vignette{position:absolute;inset:0;pointer-events:none;border-radius:14px;
  box-shadow:inset 0 1px 0 var(--border-hi),inset 0 0 70px 6px rgba(3,6,12,.42)}
[data-theme=light] .diag-vignette{box-shadow:inset 0 1px 0 #fff,inset 0 0 60px 6px rgba(20,30,50,.08)}
#diagView.embed-view{display:flex;align-items:center;justify-content:center;transform-origin:center}
.embed-view>svg,.embed-view #diagSVG{width:100%;height:auto;max-height:100%}
/* legend */
.diag-legend{display:flex;flex-wrap:wrap;gap:8px 20px;margin-top:12px;padding:10px 14px;border-radius:10px;
  background:var(--elevated);border:1px solid var(--border);font-size:11.5px;color:var(--text-2)}
.lg-grp{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.lg-t{font:600 10px/1 var(--mono);text-transform:uppercase;letter-spacing:.12em;color:var(--text-3)}
.lg-item{display:inline-flex;align-items:center;gap:6px}
.lg-sw{width:11px;height:11px;border-radius:3px;flex:none}
.lg-sw.crit{background:var(--crit)} .lg-sw.high{background:var(--high)} .lg-sw.med{background:var(--med)} .lg-sw.low{background:var(--low)}
.lg-line{width:18px;height:0;border-top:2px solid var(--border-hi);flex:none}
.lg-line.control{border-top-style:dashed} .lg-line.admin{border-top:2px dashed var(--crit)} .lg-line.build{border-top-color:var(--amber)}
.lg-zone{width:16px;height:11px;border:1px dashed var(--border-hi);border-radius:3px;flex:none;
  background:color-mix(in srgb,var(--cyan) 6%,transparent)}
/* selected node on the embedded map */
.node.embed.sel{filter:drop-shadow(0 0 12px var(--cyan)) drop-shadow(0 0 4px var(--cyan))}
.node.sel .node-box{stroke:var(--cyan);stroke-width:2.5}
/* ---- Asset Inspector panel ---- */
.inspector{background:linear-gradient(180deg,color-mix(in srgb,var(--surface) 86%,var(--elevated)),var(--surface));
  border:1px solid var(--border-hi);border-radius:14px;padding:14px 15px;display:flex;flex-direction:column;gap:12px;
  box-shadow:inset 0 1px 0 var(--border-hi)}
.ins-hint{font-size:11.5px;color:var(--text-3);line-height:1.45}
.ins-hint b{color:var(--cyan);font-weight:600}
.ins-card{display:flex;flex-direction:column;gap:13px}
.ins-head{display:flex;align-items:center;gap:12px}
.ins-gwrap{width:44px;height:44px;flex:none;border-radius:11px;display:grid;place-items:center;color:var(--text-2);
  background:var(--elevated);border:1px solid var(--border-hi)}
.ins-gwrap.crit{color:var(--crit);border-color:color-mix(in srgb,var(--crit) 45%,transparent);background:color-mix(in srgb,var(--crit) 12%,var(--elevated))}
.ins-gwrap.high{color:var(--high);border-color:color-mix(in srgb,var(--high) 45%,transparent);background:color-mix(in srgb,var(--high) 12%,var(--elevated))}
.ins-gwrap.med{color:var(--med);border-color:color-mix(in srgb,var(--med) 45%,transparent);background:color-mix(in srgb,var(--med) 12%,var(--elevated))}
.ins-gwrap.low{color:var(--low);border-color:color-mix(in srgb,var(--low) 45%,transparent);background:color-mix(in srgb,var(--low) 12%,var(--elevated))}
.ins-glyph{width:24px;height:24px;fill:none;stroke:currentColor;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round}
.ins-titles{min-width:0}
.ins-name{font-size:15px;font-weight:600;color:var(--text-1);line-height:1.2;letter-spacing:-.01em}
.ins-sub{display:flex;align-items:center;gap:8px;margin-top:3px;flex-wrap:wrap}
.ins-id{font-family:var(--mono);font-size:12px;color:var(--cyan);background:color-mix(in srgb,var(--cyan) 12%,transparent);
  padding:1px 7px;border-radius:6px}
.ins-kind{font-size:11.5px;color:var(--text-3)}
.ins-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}
.ins-stat{background:var(--elevated);border:1px solid var(--border);border-radius:10px;padding:9px 6px;text-align:center}
.ins-stat b{display:block;font-family:var(--serif);font-size:24px;line-height:1;color:var(--text-1);font-variant-numeric:tabular-nums}
.ins-stat span{display:block;font-size:9.5px;color:var(--text-3);text-transform:uppercase;letter-spacing:.08em;margin-top:5px}
.ins-stat .ins-band{font-family:var(--mono);font-size:14px;letter-spacing:.04em}
.ins-stat.crit .ins-band{color:var(--crit)} .ins-stat.high .ins-band{color:var(--high)}
.ins-stat.med .ins-band{color:var(--med)} .ins-stat.low .ins-band{color:var(--low)} .ins-stat.none .ins-band{color:var(--none)}
.ins-rows{display:flex;flex-direction:column;gap:7px}
.ins-row{display:grid;grid-template-columns:88px 1fr;gap:10px;font-size:12.5px;color:var(--text-2);align-items:baseline}
.ins-tech{line-height:1.4}
.ins-sec{display:flex;flex-direction:column;gap:7px}
.ins-lab{font-size:10px;text-transform:uppercase;letter-spacing:.11em;color:var(--text-3);display:flex;align-items:center;gap:7px}
.ins-n{font:600 10px/1 var(--mono);color:var(--text-2);background:var(--elevated);border:1px solid var(--border-hi);
  border-radius:20px;padding:2px 7px}
.ins-strds{display:flex;flex-wrap:wrap;gap:5px}
.ins-strd{font-family:var(--mono);font-size:11px;font-weight:600;color:var(--cyan);
  background:color-mix(in srgb,var(--cyan) 10%,transparent);border:1px solid color-mix(in srgb,var(--cyan) 30%,transparent);
  border-radius:6px;padding:2px 8px}
.ins-note{font-size:12px;color:var(--text-2);line-height:1.5;padding:9px 11px;border-radius:9px;
  background:color-mix(in srgb,var(--amber) 8%,var(--elevated));border-left:3px solid var(--amber)}
.ins-flist{display:flex;flex-direction:column;gap:5px;max-height:230px;overflow-y:auto;padding-right:2px}
.ins-flist::-webkit-scrollbar{width:8px}.ins-flist::-webkit-scrollbar-thumb{background:var(--border-hi);border-radius:8px}
.ins-f{display:grid;grid-template-columns:4px 60px 1fr auto;gap:9px;align-items:center;text-align:left;width:100%;
  background:var(--elevated);border:1px solid var(--border);border-radius:9px;padding:8px 10px 8px 0;cursor:pointer;
  color:var(--text-2);font:inherit;transition:border-color .18s,transform .18s,background .18s}
.ins-f:hover{border-color:var(--cyan);transform:translateX(2px);background:color-mix(in srgb,var(--cyan) 6%,var(--elevated))}
.ins-f-stripe{align-self:stretch;border-radius:9px 0 0 9px;background:var(--none)}
.ins-f-stripe.crit{background:var(--crit)} .ins-f-stripe.high{background:var(--high)}
.ins-f-stripe.med{background:var(--med)} .ins-f-stripe.low{background:var(--low)}
.ins-fid{font-family:var(--mono);font-size:11px;color:var(--cyan)}
.ins-f-title{font-size:12px;color:var(--text-1);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ins-f-score{font-family:var(--mono);font-size:10.5px;color:var(--text-3);white-space:nowrap;padding-right:2px}
.ins-f-score b{color:var(--text-1)}
.ins-evs{display:flex;flex-direction:column;gap:4px}
.ins-ev{font-family:var(--mono);font-size:11px;color:var(--text-2);background:var(--void);border:1px solid var(--border);
  border-radius:7px;padding:5px 9px;word-break:break-all}
.ins-blank{font-size:11.5px;color:var(--text-4);font-style:italic;padding:6px 2px}
@media(max-width:980px){.diag-split{grid-template-columns:1fr}.diag-viewport{height:460px}}
/* small chart craft: filled severity pills, donut lift, component-bar gradient, kill-chain depth */
.donut{filter:drop-shadow(0 10px 30px rgba(0,0,0,.35))}
.sev-pill.crit{background:color-mix(in srgb,var(--crit) 14%,transparent)}
.sev-pill.high{background:color-mix(in srgb,var(--high) 14%,transparent)}
.sev-pill.med{background:color-mix(in srgb,var(--med) 14%,transparent)}
.sev-pill.low{background:color-mix(in srgb,var(--low) 14%,transparent)}
.comp-row{padding:3px 0;border-radius:8px;transition:background .18s}
.comp-row:hover{background:color-mix(in srgb,var(--cyan) 6%,transparent)}
.kc{background:linear-gradient(180deg,color-mix(in srgb,var(--elevated) 80%,var(--surface)),var(--elevated));
  box-shadow:inset 0 1px 0 var(--border-hi)}
.bar-fill{box-shadow:inset 0 1px 0 rgba(255,255,255,.15)}
@media (prefers-reduced-motion:reduce){.pg-arc{stroke-dashoffset:calc(100 - var(--score))!important;transition:none}}
"""

JS = r"""
const META = __DATA__;
// theme
const root=document.documentElement;
const saved=localStorage.getItem('tm-theme');
if(saved)root.setAttribute('data-theme',saved);
document.getElementById('themeBtn').onclick=()=>{
  const now=root.getAttribute('data-theme')==='light'?'':'light';
  if(now)root.setAttribute('data-theme',now);else root.removeAttribute('data-theme');
  localStorage.setItem('tm-theme',now);
  document.getElementById('themeBtn').textContent=now?'☀':'☽';
};
// reveal + trigger inner animations
const io=new IntersectionObserver((es)=>{es.forEach(e=>{
  if(!e.isIntersecting)return;
  const el=e.target;el.classList.add('in');
  el.querySelectorAll('.bar-fill,.stack-seg,.cat-bar,.comp-bar span,.donut,.gauge,.kpi').forEach(x=>x.classList.add('in'));
  el.querySelectorAll('.hm-cell').forEach(c=>{setTimeout(()=>c.classList.add('in'),(+c.dataset.delay||0)*22)});
  el.querySelectorAll('.counter').forEach(countUp);
  io.unobserve(el);
},{threshold:.18})});
document.querySelectorAll('.reveal,.kpi,.hm-grid,.donut,.gauge,.posture-gauge').forEach(el=>io.observe(el));
// count-up
function countUp(el){
  const to=parseFloat(el.dataset.to)||0, dec=+el.dataset.dec||0, dur=1100, t0=performance.now();
  function step(t){const p=Math.min(1,(t-t0)/dur);const e=1-Math.pow(1-p,3);
    el.textContent=(to*e).toFixed(dec);if(p<1)requestAnimationFrame(step);else el.textContent=to.toFixed(dec);}
  requestAnimationFrame(step);
}
// on load: sync the theme glyph + highlight the Inspector's default (highest-risk) node on the map.
window.addEventListener('load',()=>{
  const tb=document.getElementById('themeBtn');tb.textContent=root.getAttribute('data-theme')==='light'?'☀':'☽';
  if(META.top)highlightNode(META.top);});

/* ================= interactive linked-model explorer ================= */
const L=META.links||{}, FBI=META.findings||{}, ENT=META.entities||{};
const $=id=>document.getElementById(id);
/* ---- Asset Inspector: mirror of _inspector_html(), re-rendered on node selection ---- */
const GLYPH={
  component:'<rect x="3.5" y="5" width="13" height="10" rx="1.6"/><path d="M3.5 8.5h13"/>',
  store:'<ellipse cx="10" cy="5.5" rx="6.5" ry="2.4"/><path d="M3.5 5.5v9c0 1.3 2.9 2.4 6.5 2.4s6.5-1.1 6.5-2.4v-9"/>',
  entry:'<path d="M11.5 3.5H4.5v13h7"/><path d="M8 10h8.5"/><path d="M13.5 6.5 17 10l-3.5 3.5"/>',
  external:'<path d="M10 2.5 16.8 6.3v7.4L10 17.5 3.2 13.7V6.3z"/><path d="M10 2.5v15"/>',
  actor:'<circle cx="10" cy="6.5" r="3"/><path d="M4.5 16.5c0-3 2.5-4.6 5.5-4.6s5.5 1.6 5.5 4.6"/>',
  boundary:'<rect x="3.5" y="3.5" width="13" height="13" rx="2" stroke-dasharray="3 2.4"/>'};
const KL={component:'Component',store:'Data store',entry:'Entry point',external:'External dependency',actor:'Actor / role',boundary:'Trust boundary'};
function insGlyph(k){return '<svg class="ins-glyph" viewBox="0 0 20 20" aria-hidden="true">'+(GLYPH[k]||GLYPH.component)+'</svg>';}
function renderInspector(eid){
  const host=$('inspector');if(!host)return;
  const e=ENT[eid];
  const hint='<div class="ins-hint">Click any node on the map to inspect its risk, findings &amp; evidence · '
    +'<b>'+(eid?'selected asset':'highest-risk asset')+'</b></div>';
  if(!e){host.dataset.eid='';host.innerHTML=hint+'<div class="ins-blank">No metadata for this node.</div>';return;}
  const sev=sevCls(e.sev),typ=e.type?(' · '+esc(e.type)):'';
  const stride=e.stride.length?e.stride.map(s=>'<span class="ins-strd">'+esc(s)+'</span>').join(''):'<span class="muted">—</span>';
  let rows='';
  e.fids.forEach(fid=>{const f=FBI[fid]||{};const fs=sevCls(f.sev);const risk=(f.l||0)*(f.i||0);
    rows+='<button class="ins-f" data-pivot="finding" data-fid="'+esc(fid)+'"><span class="ins-f-stripe '+fs+'"></span>'
      +'<code class="ins-fid">'+esc(fid)+'</code><span class="ins-f-title">'+esc(f.title||'')+'</span>'
      +'<span class="ins-f-score">L'+esc(f.l)+'·I'+esc(f.i)+' <b>'+risk+'</b></span></button>';});
  const flist=rows?('<div class="ins-flist">'+rows+'</div>'):'<div class="ins-blank">No findings reference this asset</div>';
  const ev=e.evidence.map(r=>'<code class="ins-ev">'+esc(r)+'</code>').join('');
  const evb='<div class="ins-sec"><div class="ins-lab">Evidence / annotations</div>'
    +(ev?('<div class="ins-evs">'+ev+'</div>'):'<div class="ins-blank">No evidence surfaced on this element</div>')+'</div>';
  const note=e.note?('<div class="ins-sec"><div class="ins-lab">Risk note</div><p class="ins-note">'+esc(e.note)+'</p></div>'):'';
  const zone=e.zone?esc(e.zone):'<span class="muted">—</span>',tech=e.tech?esc(e.tech):'<span class="muted">—</span>';
  host.dataset.eid=eid;
  host.innerHTML=hint+'<div class="ins-card"><div class="ins-head"><span class="ins-gwrap '+sev+'">'+insGlyph(e.kind)+'</span>'
    +'<div class="ins-titles"><div class="ins-name">'+esc(e.name)+'</div><div class="ins-sub"><code class="ins-id">'+esc(eid)
    +'</code><span class="ins-kind">'+esc(KL[e.kind]||e.kind)+typ+'</span></div></div></div>'
    +'<div class="ins-stats"><div class="ins-stat '+sev+'"><b class="ins-band">'+esc(e.sev)+'</b><span>risk band</span></div>'
    +'<div class="ins-stat"><b>'+e.score+'</b><span>max L×I</span></div><div class="ins-stat"><b>'+e.count+'</b><span>findings</span></div></div>'
    +'<div class="ins-rows"><div class="ins-row"><span class="ins-lab">Trust zone</span><span>'+zone+'</span></div>'
    +'<div class="ins-row"><span class="ins-lab">Technology</span><span class="ins-tech">'+tech+'</span></div></div>'
    +'<div class="ins-sec"><div class="ins-lab">STRIDE-LM</div><div class="ins-strds">'+stride+'</div></div>'+note
    +'<div class="ins-sec"><div class="ins-lab">Findings <span class="ins-n">'+e.count+'</span></div>'+flist+'</div>'+evb+'</div>';
}
function highlightNode(eid){document.querySelectorAll('.node.sel').forEach(n=>n.classList.remove('sel'));
  if(!eid)return;document.querySelectorAll('[data-entity="'+(window.CSS&&CSS.escape?CSS.escape(eid):eid)+'"].node').forEach(n=>n.classList.add('sel'));}
function flashNode(eid){document.querySelectorAll('[data-entity="'+(window.CSS&&CSS.escape?CSS.escape(eid):eid)+'"]').forEach(el=>{el.classList.remove('flash');void el.offsetWidth;el.classList.add('flash');});}
function selectEntity(eid,scroll){applyFocus('entity',eid);renderInspector(eid);highlightNode(eid);
  if(scroll){const vp=$('diagVP');if(vp)vp.scrollIntoView({behavior:'smooth',block:'center'});flashNode(eid);}}
function esc(s){return (s==null?'':String(s)).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));}
function sevCls(s){return ({CRITICAL:'crit',HIGH:'high',MEDIUM:'med',LOW:'low'})[s]||'none';}
function findingsFor(kind,key){
  if(kind==='finding')return [key];
  if(kind==='entity')return L.entity_findings?.[key]||[];
  if(kind==='frame')return L.frame_findings?.[key]||[];
  if(kind==='kc')return L.kc_findings?.[key]||[];
  if(kind==='sev')return L.sev_findings?.[key]||[];
  return [];
}
// bidirectional cross-highlight / cross-filter — one shared selection the whole view reacts to
function applyFocus(kind,key){
  const fset=new Set(findingsFor(kind,key));
  const ents=new Set(); if(kind==='entity')ents.add(key);
  fset.forEach(f=>(L.finding_entities?.[f]||[]).forEach(e=>ents.add(e)));
  if(!fset.size && !ents.size)return;
  document.body.classList.add('filtering');
  document.querySelectorAll('.hot').forEach(e=>e.classList.remove('hot'));
  document.querySelectorAll('[data-fid]').forEach(el=>{if(fset.has(el.dataset.fid))el.classList.add('hot');});
  document.querySelectorAll('[data-entity]').forEach(el=>{if(ents.has(el.dataset.entity))el.classList.add('hot');});
  document.querySelectorAll('[data-frame]').forEach(el=>{if((L.frame_findings?.[el.dataset.frame]||[]).some(x=>fset.has(x)))el.classList.add('hot');});
  document.querySelectorAll('[data-kc]').forEach(el=>{if((L.kc_findings?.[el.dataset.kc]||[]).some(x=>fset.has(x)))el.classList.add('hot');});
  document.querySelectorAll('[data-sev]').forEach(el=>{if((L.sev_findings?.[el.dataset.sev]||[]).some(x=>fset.has(x)))el.classList.add('hot');});
  document.querySelectorAll('.edge').forEach(ed=>{if((ed.dataset.fids||'').split(' ').some(x=>fset.has(x)))ed.classList.add('hot');});
  const names=L.entity_names||{};
  let label=kind==='finding'?('Finding '+key):kind==='entity'?(names[key]||key):
    kind==='frame'?('Framework '+key.replace('S:','STRIDE ').replace('M:','MITRE ').replace('W:','')):
    kind==='kc'?('Kill chain '+key):(key+' severity');
  $('focusLabel').textContent=label;
  $('focusCount').textContent=fset.size+' finding'+(fset.size===1?'':'s');
  $('focusbar').hidden=false;
}
function clearFocus(){document.body.classList.remove('filtering');
  document.querySelectorAll('.hot').forEach(e=>e.classList.remove('hot'));$('focusbar').hidden=true;}
$('focusClear').onclick=clearFocus;
function flashFinding(id){const el=document.querySelector('.finding[data-fid="'+id+'"]');
  if(el){el.open=true;el.scrollIntoView({behavior:'smooth',block:'center'});el.classList.remove('flash');void el.offsetWidth;el.classList.add('flash');}}
// drawer (click-in detail / focused panel)
function openDrawer(){$('drawer').hidden=false;$('drawerScrim').hidden=false;requestAnimationFrame(()=>$('drawer').classList.add('open'));}
function closeDrawer(){$('drawer').classList.remove('open');$('drawerScrim').hidden=true;setTimeout(()=>$('drawer').hidden=true,350);}
$('drawerClose').onclick=closeDrawer;$('drawerScrim').onclick=closeDrawer;
// embedded evidence for the drawer: the extracted snippet + findable reference + jump-to-diagram-node.
// Honest no-evidence / unresolved states are shown explicitly — never a fabricated snippet.
function evHtml(evList){
  if(!evList||!evList.length)return '<div class="dr-field ev-field"><span>Evidence</span>'
    +'<p class="muted">No direct evidence embedded for this finding.</p></div>';
  let h='<div class="dr-field ev-field"><span>Evidence</span><div class="evidence-list">';
  evList.forEach(e=>{
    const node=e.node?'<button class="ev-jump jump-node" data-pivot="entity" data-entity="'+esc(e.node)
      +'" title="Jump to diagram node">◈ '+esc(e.node_name||e.node)+'</button>':'';
    if(e.no_direct_evidence){h+='<div class="ev-item ev-none"><div class="ev-head"><span class="ev-tag">no direct evidence</span></div>'
      +'<p class="muted">'+esc(e.justification||'—')+'</p></div>';return;}
    const ref='<code class="ev-ref node-id">'+esc(e.ref||'—')+'</code>';
    if(e.unresolved||!e.excerpt){h+='<div class="ev-item ev-unres"><div class="ev-head">'+ref
      +'<span class="ev-tag warn">unresolved</span>'+node+'</div></div>';return;}
    const kind=e.kind||'code';
    const body=(kind==='doc'||kind==='diagram')?'<blockquote class="ev-quote">'+esc(e.excerpt)+'</blockquote>'
      :'<pre class="ev-code lang-'+esc(kind)+'"><code>'+esc(e.excerpt)+'</code></pre>';
    h+='<div class="ev-item"><div class="ev-head">'+ref+'<span class="ev-tag">'+esc(kind)+'</span>'+node+'</div>'+body+'</div>';
  });
  return h+'</div></div>';
}
function openFindingDrawer(id){const f=FBI[id];if(!f)return;
  $('drawerTitle').textContent=id;
  const ents=(L.finding_entities?.[id]||[]).map(e=>(L.entity_names?.[e]||e)).join(', ');
  $('drawerBody').innerHTML=
    '<div class="dr-chips"><span class="sev-pill '+sevCls(f.sev)+'">'+f.sev+'</span> <span class="muted">L'+f.l+'·I'+f.i+'</span></div>'
    +'<div class="dr-field"><span>'+esc(f.title)+'</span><p>'+esc(f.brief||'')+'</p></div>'
    +'<div class="dr-field"><span>STRIDE-LM</span><p>'+(f.stride.join(', ')||'—')+'</p></div>'
    +'<div class="dr-field"><span>CWE / MITRE</span><p>'+(f.cwe.concat(f.mitre).join(', ')||'—')+'</p></div>'
    +'<div class="dr-field"><span>Touches</span><p>'+esc(ents||'—')+'</p></div>'
    +evHtml(f.evidence);
  openDrawer();
}
// unified click routing — a node (SVG or evidence jump) drives the Asset Inspector; findings flash below.
document.addEventListener('click',e=>{
  const jn=e.target.closest('.jump-node');
  if(jn){e.preventDefault();e.stopPropagation();selectEntity(jn.dataset.entity,true);return;}
  const node=e.target.closest('.node');
  if(node){selectEntity(node.dataset.entity,false);return;}
  const piv=e.target.closest('[data-pivot]');
  if(!piv)return;
  const kind=piv.dataset.pivot;
  const key=piv.dataset.fid||piv.dataset.entity||piv.dataset.frame||piv.dataset.kc||piv.dataset.sev;
  if(kind==='entity'){selectEntity(key,true);return;}
  applyFocus(kind,key);
  if(kind==='finding'){
    if(piv.classList.contains('kc-step')||piv.classList.contains('dr-f'))openFindingDrawer(key);
    else flashFinding(key);
  }
});
// hover tooltips (glance-level detail, no layout shift)
const tip=$('tooltip');
document.addEventListener('mousemove',e=>{
  const t=e.target.closest('.node,[data-fid]');
  if(!t){tip.classList.remove('show');tip.hidden=true;return;}
  let html='';
  if(t.classList.contains('node'))
    html='<b>'+esc(t.dataset.name)+' ('+t.dataset.entity+')</b>'+esc(t.dataset.tech||'')+'<br>'+t.dataset.count+' finding(s) · click to pivot';
  else{const f=FBI[t.dataset.fid];if(f)html='<b>'+f.id+' · '+esc(f.title)+'</b><span class="tt-pill '+sevCls(f.sev)+'">'+f.sev+'</span> L'+f.l+'·I'+f.i+' '+esc(f.cwe.join(', '))+'<br>'+esc(f.brief||'');}
  if(!html){tip.hidden=true;return;}
  tip.innerHTML=html;tip.hidden=false;tip.classList.add('show');
  let x=e.clientX+14,y=e.clientY+14; if(x+312>innerWidth)x=e.clientX-312; if(y+120>innerHeight)y=e.clientY-120;
  tip.style.left=x+'px';tip.style.top=y+'px';
});
document.addEventListener('keydown',e=>{if(e.key==='Escape'){clearFocus();closeDrawer();}});
// diagram pan + zoom (vanilla, over inline SVG)
(function(){
  const vp=$('diagVP');if(!vp)return;
  const view=$('diagView'),svg=$('diagSVG');
  // rerender = transform an inline SVG <g> (viewBox units); embed = transform an HTML <div> (px).
  const isSVG=view.namespaceURI==='http://www.w3.org/2000/svg';
  let scale=1,tx=0,ty=0,drag=false,startx=0,starty=0,ox=0,oy=0;
  const k=()=>isSVG?(svg.viewBox.baseVal.width/vp.clientWidth||1):1;
  const apply=()=>isSVG
    ?view.setAttribute('transform','translate('+tx+' '+ty+') scale('+scale+')')
    :view.style.transform='translate('+tx+'px,'+ty+'px) scale('+scale+')';
  vp.addEventListener('wheel',e=>{e.preventDefault();scale=Math.min(4,Math.max(.3,scale*(e.deltaY<0?1.12:0.89)));apply();},{passive:false});
  vp.addEventListener('pointerdown',e=>{drag=true;startx=e.clientX;starty=e.clientY;ox=tx;oy=ty;vp.setPointerCapture(e.pointerId);});
  vp.addEventListener('pointermove',e=>{if(!drag)return;tx=ox+(e.clientX-startx)*k();ty=oy+(e.clientY-starty)*k();apply();});
  vp.addEventListener('pointerup',()=>drag=false);vp.addEventListener('pointercancel',()=>drag=false);
  document.querySelectorAll('.diag-toolbar:not(.gal-toolbar) button').forEach(b=>b.onclick=()=>{const z=b.dataset.z;
    if(z==='fit'||z==='reset'){scale=1;tx=0;ty=0;}
    else if(z==='in')scale=Math.min(4,scale*1.2);
    else if(z==='out')scale=Math.max(.3,scale*0.83);
    apply();});
})();
"""


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en" data-theme="">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>%%TITLE%% — Risk Dashboard</title>
<style>%%CSS%%</style>
</head>
<body>
<div class="bg"></div><div class="noise"></div>
<svg width="0" height="0" style="position:absolute"><defs>
  <linearGradient id="gg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="#2dd4bf"/><stop offset="1" stop-color="#22d3ee"/></linearGradient>
</defs></svg>

<header class="top">
  <div class="mark">◆</div>
  <div class="brand"><b>claudetm</b><span>Risk Dashboard</span></div>
  <div class="top-right">
    <div class="ground">◇ Grounded in run manifests · <b>reference-free</b></div>
    <button class="theme-btn" id="themeBtn" aria-label="Toggle theme">☾</button>
  </div>
</header>

<section class="hero">
  <div class="hero-copy">
    <div class="eyebrow">Threat Model · %%PATTERN%%</div>
    <h1>%%TITLE%%</h1>
    <p class="lede">%%DESC%%</p>
  </div>
  <div class="posture-gauge %%POSTURE_CLS%%" style="--score:%%POSTURE_SCORE%%">
    <div class="pg-halo" aria-hidden="true"></div>
    <svg viewBox="0 0 120 120" aria-hidden="true">
      <circle class="pg-track" cx="60" cy="60" r="50" pathLength="100"/>
      <circle class="pg-arc" cx="60" cy="60" r="50" pathLength="100"/>
    </svg>
    <div class="pg-center">
      <span class="pg-score counter" data-to="%%POSTURE_SCORE%%">0</span>
      <span class="pg-band %%POSTURE_CLS%%">%%POSTURE_BAND%%</span>
      <span class="pg-cap">risk posture</span>
    </div>
  </div>
</section>

<div class="kpis">%%KPIS%%</div>

<div class="focusbar" id="focusbar" hidden>
  <span class="focus-label" id="focusLabel"></span>
  <span class="focus-count" id="focusCount"></span>
  <button class="focus-clear" id="focusClear">clear ✕</button>
</div>

<main>%%BODY%%</main>

<div class="tooltip" id="tooltip" hidden></div>

<aside class="drawer" id="drawer" hidden>
  <div class="drawer-head"><span id="drawerTitle">Detail</span>
    <button id="drawerClose" aria-label="Close">✕</button></div>
  <div class="drawer-body" id="drawerBody"></div>
</aside>
<div class="drawer-scrim" id="drawerScrim" hidden></div>

<footer class="foot">
  <span>Generated <b>%%GENERATED%%</b></span>
  <span>Recon &amp; analysis: <b>%%GEN_BY%%</b></span>
  <span>Coverage merge: <b>%%MERGED_BY%%</b></span>
  <span>Every value traces to recon.json / findings.json / coverage.json. Absent fields render as empty states — never fabricated.</span>
</footer>

<script>%%JS%%</script>
</body>
</html>
"""
