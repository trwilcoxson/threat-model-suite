#!/usr/bin/env python3
"""Risk-dashboard generator — the "ultimate artifact" product-risk view.

Deterministic transform:  recon.json + findings.json + coverage.json [+ navigator layer]
                          + the run's ACTUAL structural diagram (recon.dataflows[] OR
                            structural-diagram.mmd)
                          -->  derived analytics model  -->  single self-contained HTML.

Mirrors the suite's determinism boundary: the AGENTS emit the manifests + the structural diagram
(all reasoning/generation); this script only RESHAPES emitted facts into a template. It invents
no content and — critically — invents no diagram. Every number traces to a manifest field; every
diagram node id is a recon element id and every diagram edge is a REAL dataflow the flow already
drew (NOT a synthesized finding-co-reference edge). So the diagram the dashboard shows is the same
threat model the report shows: one source of truth. Missing/absent fields degrade to a graceful
empty state ("No evidence surfaced"), never a crash or a fabricated value.

Usage:
    python3 build_dashboard.py <run_dir> <out.html>
    python3 build_dashboard.py --thin <run_dir> <out.html>   # sparse proof (thinned data)
"""
import json, sys, os, re, html
from collections import Counter, defaultdict

SEV_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
STRIDE_NAMES = {"S": "Spoofing", "T": "Tampering", "R": "Repudiation",
                "I": "Info Disclosure", "D": "Denial of Service",
                "E": "Elevation of Priv", "LM": "Lateral Movement"}

# recon source array -> the diagram "kind" token used for node shape/lane semantics.
KIND_OF_ARRAY = {"components": "component", "data_stores": "store", "entry_points": "entry",
                 "external_deps": "external", "roles": "actor"}


def load(run_dir, name):
    p = os.path.join(run_dir, name)
    if not os.path.exists(p):
        return None
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return None


def _natural(s):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(s))]


def thin(recon, findings, coverage):
    """Deliberately thin the data to prove templated empty states hold the layout."""
    findings = json.loads(json.dumps(findings))
    findings["findings"] = findings["findings"][:2]
    findings["kill_chains"] = []
    kept = Counter(f.get("severity") for f in findings["findings"])
    findings["summary_counts"] = {k: kept.get(k, 0) for k in ("LOW", "MEDIUM", "HIGH", "CRITICAL")}
    recon = json.loads(json.dumps(recon))
    recon["external_deps"] = []
    recon["trust_boundaries"] = []
    coverage = json.loads(json.dumps(coverage))
    coverage["items"] = coverage["items"][:12]
    return recon, findings, coverage


# ---------------------------------------------------------------------------
# The RUN'S ACTUAL structural diagram (single source of truth).
#
# We never invent a bespoke node map. The graph is derived from — in priority order —
#   1. recon.dataflows[] + recon zones  (the semantic-source render, same as recon_to_d2.py), or
#   2. the run's structural-diagram.mmd (the diagram-specialist's authored diagram),
# and every node id is a real recon element id (C1/D1/E1/X1/R0…) so it links to findings natively.
# ---------------------------------------------------------------------------

# a mermaid flowchart node declaration: ID + one of the shape wrappers + a quoted-or-bare label.
_MMD_NODE = re.compile(r'^\s*([A-Za-z][\w-]*)\s*(\[\(|\(\[|\[/|\[|\(|\{)\s*"?(.*?)"?\s*(?:\)\]|\]\)|/\]|\]|\)|\})\s*(?::::[\w-]+)?\s*$')
# a mermaid edge:  A  --> | "label" |  B    (solid/dotted/thick; optional label)
_MMD_EDGE = re.compile(r'^\s*([A-Za-z][\w-]*)\s*([.=-]?[.=-]?-?[->]+)\s*(?:\|\s*"?(.*?)"?\s*\|)?\s*([A-Za-z][\w-]*)\s*$')
_MMD_SUB = re.compile(r'^\s*subgraph\s+([A-Za-z][\w-]*)\s*(?:\[\s*"?(.*?)"?\s*\])?\s*$')


def _mmd_edge_type(label):
    lab = (label or "").upper()
    for tok, t in (("[BUILD]", "build"), ("[ADMIN]", "admin"), ("[ASYNC]", "async"), ("[CTRL]", "control")):
        if tok in lab:
            return t
    return "data"


def parse_structural_mmd(text, valid_ids):
    """Parse the flowchart subset the diagram-specialist emits. Returns (nodes, edges, containers).

    Only nodes whose id is a real recon element id are kept (no invented nodes); the Legend subgraph
    is skipped. Containers preserve declaration order + nesting so the dashboard reproduces the same
    trust-zone grouping the report shows."""
    node_labels = {}            # id -> first label line (display)
    edges = []                  # {a,b,label,etype}
    containers = []             # {id,label,children:[ids],parent}
    order = []                  # declaration order of top-level items (container id or node id)
    stack = []                  # open subgraph ids (nesting)
    members = defaultdict(list)  # container id -> child node ids (direct)
    subparent = {}              # container id -> parent container id or None
    sublabel = {}

    def _skip_container(cid, clabel):
        return cid.lower().startswith("legend") or (clabel or "").lower().startswith("legend")

    for raw in text.splitlines():
        line = raw.rstrip()
        s = line.strip()
        if not s or s.startswith("%%") or s.startswith("linkStyle") or s.startswith("classDef") \
                or s.startswith("style ") or s.startswith("flowchart") or s.startswith("graph "):
            continue
        msub = _MMD_SUB.match(line)
        if msub:
            cid, clabel = msub.group(1), (msub.group(2) or msub.group(1))
            parent = stack[-1] if stack else None
            if not _skip_container(cid, clabel):
                subparent[cid] = parent
                sublabel[cid] = clabel
                if parent is None:
                    order.append(("c", cid))
            stack.append(cid)
            continue
        if s == "end":
            if stack:
                stack.pop()
            continue
        medge = _MMD_EDGE.match(line)
        if medge and "-" in medge.group(2):
            a, lab, b = medge.group(1), medge.group(3), medge.group(4)
            if a in valid_ids and b in valid_ids:
                edges.append({"a": a, "b": b, "label": (lab or "").strip(), "etype": _mmd_edge_type(lab)})
            continue
        mnode = _MMD_NODE.match(line)
        if mnode:
            nid, label = mnode.group(1), mnode.group(3)
            if nid not in valid_ids:
                continue  # invented / legend node — never drawn
            node_labels[nid] = (label or nid).split("\\n")[0].strip()
            # attribute to the innermost OPEN kept container (Legend is never a kept container).
            parent = stack[-1] if stack and stack[-1] in subparent else None
            if parent:
                members[parent].append(nid)
            else:
                order.append(("n", nid))
    for cid in subparent:
        containers.append({"id": cid, "label": sublabel.get(cid, cid),
                           "children": members.get(cid, []), "parent": subparent.get(cid)})
    return node_labels, edges, containers, order


def build_structural_graph(recon, findings, run_dir):
    """The single-source-of-truth structural graph: real recon nodes + real diagram edges + zones.

    Returns {"nodes":[…], "edges":[…], "containers":[…], "order":[…], "source": "dataflows|mermaid|none"}.
    Node metadata (severity rollup, finding count, fids) is grounded in findings.asset_refs/surface_refs.
    """
    recon = recon or {}
    F = (findings or {}).get("findings", []) or []

    # id -> (kind, element) for every drawable recon entity.
    ent = {}
    names = {}
    for arr, kind in KIND_OF_ARRAY.items():
        for el in recon.get(arr, []) or []:
            if "id" in el:
                ent[el["id"]] = (kind, el)
                names[el["id"]] = el.get("name", el["id"])
    valid_ids = set(ent)

    # finding rollups per entity (grounded — same joins the report uses).
    fsev = {f["id"]: f.get("severity", "") for f in F}
    ent_fids = defaultdict(list)
    for f in F:
        for a in (f.get("asset_refs") or []) + (f.get("surface_refs") or []):
            if a in valid_ids:
                ent_fids[a].append(f["id"])

    def _sevname(ids):
        mx = max((SEV_RANK.get(fsev.get(i), 0) for i in ids), default=0)
        return next((k for k, v in SEV_RANK.items() if v == mx), "—")

    # ---- edges + containers from the single source of truth ----
    dataflows = recon.get("dataflows") or []
    node_labels, edges, containers, order = {}, [], [], []
    source = "none"
    if dataflows:
        source = "dataflows"
        for fl in dataflows:
            a, b = fl.get("source"), fl.get("destination")
            if a in valid_ids and b in valid_ids:
                lab = " ".join(p for p in [(fl.get("protocol") or "").strip(), (fl.get("label") or "").strip()] if p)
                edges.append({"a": a, "b": b, "label": lab, "etype": fl.get("type") or "data"})
        # containers from recon zones (element.zone -> trust boundary) + declared trust_boundaries
        tb = {b["id"]: b for b in recon.get("trust_boundaries", []) or [] if "id" in b}
        zmembers = defaultdict(list)
        for eid, (kind, el) in ent.items():
            z = el.get("zone")
            if z in tb:
                zmembers[z].append(eid)
        drawn_ids = {ep for e in edges for ep in (e["a"], e["b"])} or valid_ids
        for eid in sorted(drawn_ids, key=_natural):
            z = ent[eid][1].get("zone")
            if z not in tb:
                order.append(("n", eid))
        for zid in sorted(tb, key=_natural):
            if zmembers.get(zid):
                containers.append({"id": zid, "label": tb[zid].get("name", zid),
                                   "children": sorted(zmembers[zid], key=_natural), "parent": tb[zid].get("zone")})
                order.append(("c", zid))
    else:
        mmd = None
        for fn in ("structural-diagram.mmd",):
            p = os.path.join(run_dir, fn) if run_dir else None
            if p and os.path.exists(p):
                mmd = open(p).read()
                break
        if mmd:
            source = "mermaid"
            node_labels, edges, containers, order = parse_structural_mmd(mmd, valid_ids)

    drawn = set(node_labels)
    for _, cid in [o for o in order if o[0] == "c"]:
        pass
    for c in containers:
        drawn.update(c["children"])
    for kind, oid in order:
        if kind == "n":
            drawn.add(oid)
    if source == "none":
        # no dataflows, no mermaid -> draw every recon entity, ungrouped (still real nodes, no edges).
        drawn = set(valid_ids)
        order = [("n", i) for i in sorted(valid_ids, key=_natural)]

    nodes = []
    for eid in sorted(drawn, key=_natural):
        if eid not in ent:
            continue
        kind, el = ent[eid]
        ids = sorted(set(ent_fids.get(eid, [])))
        nodes.append({"id": eid, "name": names.get(eid, eid), "tech": el.get("tech", ""),
                      "kind": kind, "sev": _sevname(ids), "count": len(ids), "fids": ids,
                      "label": node_labels.get(eid, names.get(eid, eid)),
                      "evidence": len(el.get("evidence", []) or [])})
    # edge fids = findings referencing EITHER endpoint (for the cross-filter pivot). The edge itself
    # is a real dataflow, so this is metadata-on-a-real-edge, never a fabricated edge.
    node_fids = {n["id"]: set(n["fids"]) for n in nodes}
    for e in edges:
        e["fids"] = sorted(node_fids.get(e["a"], set()) | node_fids.get(e["b"], set()))
    drawn_ids = {n["id"] for n in nodes}
    edges = [e for e in edges if e["a"] in drawn_ids and e["b"] in drawn_ids]
    # keep a container iff it (transitively) holds a drawn leaf — but retain ancestors of kept
    # containers so nesting (VPC > PUB/PRIV) survives and no band is orphaned.
    subs = defaultdict(list)
    for c in containers:
        subs[c.get("parent")].append(c["id"])
    by_id = {c["id"]: c for c in containers}

    def has_drawn(cid, seen=frozenset()):
        if cid in seen:
            return False
        c = by_id[cid]
        return any(ch in drawn_ids for ch in c["children"]) or any(has_drawn(s, seen | {cid}) for s in subs.get(cid, []))
    containers = [c for c in containers if has_drawn(c["id"])]
    return {"nodes": nodes, "edges": edges, "containers": containers, "order": order, "source": source}


def build_model(recon, findings, coverage, navigator, run_dir=None):
    """All derived analytics. Everything defensive: absent -> None/[] -> empty state."""
    recon = recon or {}
    findings = findings or {}
    coverage = coverage or {}
    F = findings.get("findings", []) or []

    # asset/surface name maps for grounding joins
    assets = {}
    for c in recon.get("components", []) or []:
        assets[c["id"]] = c["name"]
    for d in recon.get("data_stores", []) or []:
        assets[d["id"]] = d["name"]
    surfaces = {}
    for key in ("entry_points", "trust_boundaries", "external_deps"):
        for s in recon.get(key, []) or []:
            surfaces[s["id"]] = s["name"]
    for r in recon.get("roles", []) or []:
        surfaces[r["id"]] = r["name"]

    # severity
    sev = findings.get("summary_counts") or Counter(f.get("severity") for f in F)
    sev = {k: sev.get(k, 0) for k in ("CRITICAL", "HIGH", "MEDIUM", "LOW")}

    # L x I heatmap 5x5
    heat = defaultdict(int)
    for f in F:
        li = (f.get("likelihood"), f.get("impact"))
        if isinstance(li[0], int) and isinstance(li[1], int):
            heat[(li[0], li[1])] += 1
    heatmap = [[heat.get((l, i), 0) for i in range(1, 6)] for l in range(1, 6)]

    # STRIDE-LM
    stride = Counter()
    for f in F:
        for t in f.get("stride_lm", []) or []:
            stride[t] += 1

    # CWE / MITRE
    cwe = Counter()
    mitre = Counter()
    for f in F:
        for c in (f.get("cwe") or []):
            cwe[c] += 1
        for m in (f.get("mitre") or []):
            mitre[m] += 1

    # navigator technique scores (optional, for coloring)
    nav_scores = {}
    nav_comments = {}
    if navigator:
        for t in navigator.get("techniques", []) or []:
            nav_scores[t["techniqueID"]] = t.get("score")
            nav_comments[t["techniqueID"]] = t.get("comment", "")

    # coverage ledger
    cov_items = coverage.get("items", []) or []
    cov_states = Counter(i.get("state") for i in cov_items)
    applicable = sum(1 for i in cov_items if i.get("state") != "not-applicable")
    present = cov_states.get("present", 0)
    partial = cov_states.get("partial", 0)
    cov_pct = round(100 * (present + 0.5 * partial) / applicable, 1) if applicable else None
    cov_present_pct = round(100 * present / applicable, 1) if applicable else None
    cats = defaultdict(Counter)
    for i in cov_items:
        cats[i.get("id", "").split(".")[0]][i.get("state")] += 1
    cat_rows = []
    for name in sorted(cats):
        c = cats[name]
        total = sum(c.values())
        applic = total - c.get("not-applicable", 0)
        pct = round(100 * (c.get("present", 0) + 0.5 * c.get("partial", 0)) / applic, 0) if applic else None
        cat_rows.append({"name": name, "present": c.get("present", 0), "partial": c.get("partial", 0),
                         "absent": c.get("absent", 0), "na": c.get("not-applicable", 0),
                         "unknown": c.get("unknown", 0), "pct": pct})
    context = coverage.get("context") or {}

    # component / trust-zone risk rollup (join asset_refs -> assets, max severity + count)
    comp_risk = defaultdict(lambda: {"count": 0, "max": 0, "ids": []})
    for f in F:
        for a in f.get("asset_refs", []) or []:
            r = comp_risk[a]
            r["count"] += 1
            r["max"] = max(r["max"], SEV_RANK.get(f.get("severity"), 0))
            r["ids"].append(f["id"])
    comp_rows = []
    for aid, r in comp_risk.items():
        comp_rows.append({"id": aid, "name": assets.get(aid, aid), "count": r["count"],
                          "sev": next((k for k, v in SEV_RANK.items() if v == r["max"]), "—"),
                          "ids": r["ids"]})
    comp_rows.sort(key=lambda x: (-SEV_RANK.get(x["sev"], 0), -x["count"]))

    # kill chains (resolve steps to titles)
    ftitle = {f["id"]: f.get("title", "") for f in F}
    fsev = {f["id"]: f.get("severity", "") for f in F}
    chains = []
    for kc in findings.get("kill_chains", []) or []:
        chains.append({"id": kc.get("id"), "goal": kc.get("goal", ""),
                       "steps": [{"id": s, "title": ftitle.get(s, s), "sev": fsev.get(s, "")}
                                 for s in kc.get("steps", []) or []]})

    ext = recon.get("external_deps", []) or []

    def risk_of(f):
        return (f.get("likelihood") or 0) * (f.get("impact") or 0)
    findings_sorted = sorted(F, key=lambda f: (-SEV_RANK.get(f.get("severity"), 0), -risk_of(f)))
    top = []
    for f in findings_sorted:
        top.append({
            "id": f.get("id"), "title": f.get("title"), "sev": f.get("severity"),
            "l": f.get("likelihood"), "i": f.get("impact"), "risk": risk_of(f),
            "stride": f.get("stride_lm", []) or [], "cwe": f.get("cwe") or [],
            "mitre": f.get("mitre") or [], "attack": f.get("attack_path", ""),
            "remediation": f.get("remediation", ""),
            "assets": [assets.get(a, a) for a in (f.get("asset_refs") or [])],
            "surfaces": [surfaces.get(s, s) for s in (f.get("surface_refs") or [])],
        })

    has_controls = any(f.get("controls") for f in F)
    has_cvss = any(f.get("cvss_vector") for f in F)
    has_atlas = any(f.get("atlas") for f in F)
    has_dataflows = bool(recon.get("dataflows"))

    # ---- the RUN'S structural diagram (single source of truth) ----
    graph = build_structural_graph(recon, findings, run_dir)

    # ---- linked adjacency for the cross-filter pivots (grounded, real ids only) ----
    entity_findings = defaultdict(list)
    for f in F:
        for a in f.get("asset_refs", []) or []:
            entity_findings[a].append(f["id"])
        for s in f.get("surface_refs", []) or []:
            entity_findings[s].append(f["id"])
    frame_find = defaultdict(list)
    for f in F:
        for t in f.get("stride_lm", []) or []:
            frame_find[f"S:{t}"].append(f["id"])
        for mm in f.get("mitre", []) or []:
            frame_find[f"M:{mm}"].append(f["id"])
        for c in f.get("cwe", []) or []:
            frame_find[f"W:{c}"].append(f["id"])
    kc_find = {kc.get("id"): list(kc.get("steps") or []) for kc in findings.get("kill_chains", []) or []}
    sev_find = defaultdict(list)
    for f in F:
        sev_find[f.get("severity")].append(f["id"])

    links = {
        "entity_findings": {k: sorted(set(v)) for k, v in entity_findings.items()},
        "finding_entities": {f["id"]: list((f.get("asset_refs") or []) + (f.get("surface_refs") or []))
                             for f in F},
        "frame_findings": {k: sorted(set(v)) for k, v in frame_find.items()},
        "kc_findings": kc_find,
        "sev_findings": {k: v for k, v in sev_find.items()},
        "entity_names": {**{c["id"]: c["name"] for c in recon.get("components", []) or []},
                         **{d["id"]: d["name"] for d in recon.get("data_stores", []) or []},
                         **{e["id"]: e["name"] for e in recon.get("entry_points", []) or []},
                         **{x["id"]: x["name"] for x in recon.get("external_deps", []) or []},
                         **{t["id"]: t["name"] for t in recon.get("trust_boundaries", []) or []},
                         **{r["id"]: r["name"] for r in recon.get("roles", []) or []}},
    }
    findings_by_id = {f["id"]: {"id": f["id"], "sev": f.get("severity"), "title": f.get("title"),
                                "l": f.get("likelihood"), "i": f.get("impact"),
                                "stride": f.get("stride_lm", []) or [], "cwe": f.get("cwe") or [],
                                "mitre": f.get("mitre") or [],
                                "brief": (f.get("attack_path", "") or "").split(". ")[0]}
                      for f in F}

    n = len(F)
    if n == 0:
        posture = ("NO FINDINGS", 0)
    elif sev["CRITICAL"] > 0:
        posture = ("CRITICAL", 95)
    elif sev["HIGH"] >= 5:
        posture = ("HIGH RISK", 78)
    elif sev["HIGH"] > 0:
        posture = ("ELEVATED", 60)
    elif sev["MEDIUM"] > 0:
        posture = ("MODERATE", 40)
    else:
        posture = ("LOW", 20)

    return {
        "system_name": recon.get("system_name") or findings.get("system_name") or coverage.get("system_name") or "Untitled System",
        "description": recon.get("description", ""),
        "pattern": recon.get("detected_pattern", ""),
        "generated": coverage.get("generated") or "",
        "generated_by": coverage.get("generated_by") or "",
        "merged_by": coverage.get("merged_by") or "",
        "counts": {
            "findings": n,
            "components": len(recon.get("components", []) or []),
            "data_stores": len(recon.get("data_stores", []) or []),
            "entry_points": len(recon.get("entry_points", []) or []),
            "trust_boundaries": len(recon.get("trust_boundaries", []) or []),
            "external_deps": len(ext), "roles": len(recon.get("roles", []) or []),
            "kill_chains": len(chains),
            "assets_examined": len(assets),
        },
        "posture": {"band": posture[0], "score": posture[1]},
        "severity": sev,
        "heatmap": heatmap,
        "stride": {k: stride.get(k, 0) for k in STRIDE_NAMES},
        "stride_names": STRIDE_NAMES,
        "cwe": dict(cwe.most_common()),
        "mitre": [{"id": m, "n": c, "score": nav_scores.get(m), "comment": nav_comments.get(m, "")}
                  for m, c in mitre.most_common()],
        "navigator_meta": {"domain": (navigator or {}).get("domain"),
                           "version": ((navigator or {}).get("versions") or {}).get("attack")} if navigator else None,
        "coverage": {"pct": cov_pct, "present_pct": cov_present_pct, "states": dict(cov_states),
                     "applicable": applicable, "total": len(cov_items), "categories": cat_rows,
                     "context": context},
        "component_risk": comp_rows,
        "chains": chains,
        "supply_chain": [{"id": e.get("id"), "name": e.get("name"), "tech": e.get("tech", ""),
                          "risk": e.get("risk", ""), "manifest": e.get("manifest")} for e in ext],
        "findings": top,
        "empty": {"controls": not has_controls, "cvss": not has_cvss,
                  "atlas": not has_atlas, "dataflows": not has_dataflows},
        "graph": graph,
        "links": links,
        "findings_by_id": findings_by_id,
    }


def _load_all(run_dir):
    recon = load(run_dir, "recon.json")
    findings = load(run_dir, "findings.json")
    coverage = load(run_dir, "coverage.json")
    navigator = None
    if os.path.isdir(run_dir):
        for fn in sorted(os.listdir(run_dir)):
            if fn.endswith("attack-navigator-layer.json"):
                navigator = load(run_dir, fn)
                break
    return recon, findings, coverage, navigator


def model_for_run(run_dir, thin_mode=False):
    recon, findings, coverage, navigator = _load_all(run_dir)
    if thin_mode:
        recon, findings, coverage = thin(recon, findings, coverage)
        navigator = None
        return build_model(recon, findings, coverage, navigator, run_dir=None)
    return build_model(recon, findings, coverage, navigator, run_dir=run_dir)


def main():
    args = sys.argv[1:]
    thin_mode = False
    if args and args[0] == "--thin":
        thin_mode = True
        args = args[1:]
    if len(args) != 2:
        print(__doc__)
        sys.exit(1)
    run_dir, out = args
    model = model_for_run(run_dir, thin_mode)
    with open(os.path.splitext(out)[0] + ".model.json", "w") as f:
        json.dump(model, f, indent=2)
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references"))
    from dashboard_template import render
    with open(out, "w") as f:
        f.write(render(model))
    print("wrote", out, "and", os.path.splitext(out)[0] + ".model.json")


if __name__ == "__main__":
    main()
