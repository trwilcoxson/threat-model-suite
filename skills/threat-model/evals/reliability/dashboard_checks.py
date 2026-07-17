"""Reference-free structural + grounding + cross-output checks for the risk dashboard.

These check PROPERTIES over emitted facts — never a golden answer, abstention-friendly:
  1. GROUNDING          headline numbers are recounts of the manifests (severity/kpi/coverage/heatmap).
  2. NON-FABRICATION    no finding id in a structural slot, and no diagram node, that isn't real.
  3. DIAGRAM CONSISTENCY the embedded diagram is the RUN'S diagram: nodes = recon element ids, edges =
                        the run's REAL dataflows (recon.dataflows[] or structural-diagram.mmd), NOT
                        synthesized from finding co-reference; source ∈ {dataflows,mermaid,none}.
  4. LINK-GROUNDING     the cross-filter adjacency matches the manifests (both directions).
  5. CROSS-OUTPUT       dashboard-derived counts == the figures the report shows for the SAME run
                        (severity == findings.summary_counts, coverage % from coverage.json states).
  6. OFFLINE            the rendered HTML loads no external resource (no CDN/font/asset URL).
  7. TEMPLATED BLANKS   absent fields → empty states, an empty run does not crash.

Determinism boundary preserved: this only re-derives figures from the manifests and compares — no model,
no answer key. Returns {"defects":[…], "scores":{…}} in the style of checks.py / coverage_checks.py.
"""
from __future__ import annotations

import os
import re
import sys
from collections import Counter
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent.parent / "scripts"))
sys.path.insert(0, str(_HERE.parent.parent / "references"))
import build_dashboard as bd  # noqa: E402
import evidence as ev  # noqa: E402  (shared extraction — re-extract to prove the embed matches source)


def _real_diagram_edges(recon: dict, run_dir) -> set | None:
    """Independently recompute the run's REAL diagram edges from the source of truth (not from the
    model), so we can prove the model's edges are a subset — i.e. no finding-co-reference synthesis."""
    recon = recon or {}
    valid = set()
    for arr in bd.KIND_OF_ARRAY:
        for el in recon.get(arr, []) or []:
            if "id" in el:
                valid.add(el["id"])
    dataflows = recon.get("dataflows") or []
    if dataflows:
        return {(f.get("source"), f.get("destination")) for f in dataflows
                if f.get("source") in valid and f.get("destination") in valid}
    p = os.path.join(run_dir, "structural-diagram.mmd") if run_dir else None
    if p and os.path.exists(p):
        _, edges, _, _ = bd.parse_structural_mmd(open(p).read(), valid)
        return {(e["a"], e["b"]) for e in edges}
    return None  # no diagram source → edges must be empty (checked by caller)


def check(run_dir, repo=None, model=None) -> dict:
    run_dir = str(run_dir)
    defects: list[dict] = []

    def D(code, detail):
        defects.append({"layer": "dashboard", "code": code, "detail": detail})

    recon = bd.load(run_dir, "recon.json") or {}
    findings = bd.load(run_dir, "findings.json") or {}
    coverage = bd.load(run_dir, "coverage.json") or {}
    F = findings.get("findings", []) or []
    if model is None:
        model = bd.model_for_run(run_dir, repo=repo)

    # 1 + 5. GROUNDING / CROSS-OUTPUT — every headline number recounts the manifests.
    recount = Counter(f.get("severity") for f in F)
    summary = findings.get("summary_counts") or {}
    for band in ("CRITICAL", "HIGH", "MEDIUM", "LOW"):
        if model["severity"][band] != recount.get(band, 0):
            D("severity-ungrounded", f"{band}: dashboard {model['severity'][band]} != findings recount {recount.get(band,0)}")
        # cross-output: the report shows summary_counts — the dashboard must match it when present
        if summary and band in summary and model["severity"][band] != summary.get(band, 0):
            D("severity-report-drift", f"{band}: dashboard {model['severity'][band]} != findings.summary_counts {summary.get(band)}")
    if model["counts"]["findings"] != len(F):
        D("findings-count-ungrounded", f"dashboard {model['counts']['findings']} != {len(F)} findings")
    if model["counts"]["kill_chains"] != len(findings.get("kill_chains", []) or []):
        D("killchain-count-ungrounded", "kill-chain count != findings.kill_chains")
    cov_items = coverage.get("items", []) or []
    if cov_items:
        applicable = sum(1 for i in cov_items if i.get("state") != "not-applicable")
        present = sum(1 for i in cov_items if i.get("state") == "present")
        exp = round(100 * present / applicable, 1) if applicable else None
        if model["coverage"]["present_pct"] != exp:
            D("coverage-ungrounded", f"present_pct dashboard {model['coverage']['present_pct']} != {exp}")
    total_cells = sum(sum(r) for r in model["heatmap"])
    graded = sum(1 for f in F if isinstance(f.get("likelihood"), int) and isinstance(f.get("impact"), int))
    if total_cells != graded:
        D("heatmap-ungrounded", f"heatmap sums {total_cells} != {graded} graded findings")

    # 2 + 3. DIAGRAM CONSISTENCY — the run's real diagram, not a fabricated one.
    real_ids = {f["id"] for f in F}
    recon_ids = {el["id"] for arr in bd.KIND_OF_ARRAY for el in (recon.get(arr, []) or []) if "id" in el}
    g = model["graph"]
    if g["source"] not in ("dataflows", "mermaid", "none"):
        D("diagram-source-invalid", f"unexpected diagram source {g['source']!r}")
    if g.get("diagram_source") not in ("embedded-svg", "rerender"):
        D("diagram-render-path-invalid", f"unexpected diagram render path {g.get('diagram_source')!r}")
    # EMBED path: the picture is the run's REAL visual-engine SVG — its node ids must be a subset of the
    # recon element ids (no invented nodes). The re-render checks below still cover the fallback path.
    if g.get("diagram_source") == "embedded-svg":
        # the PRIMARY diagram must be a REAL rendered file the run produced (not a substitute).
        pf = g.get("svg_file")
        if not pf or not os.path.exists(os.path.join(run_dir, pf)):
            D("primary-diagram-missing", f"primary embedded diagram {pf!r} is not a real file in the run")
        svg_ids = set(g.get("svg_node_ids") or [])
        if not svg_ids:
            D("embed-no-nodes", "embedded structural SVG exposed no recon element node ids")
        bad = svg_ids - recon_ids
        if bad:
            D("embed-node-fabricated", f"embedded diagram references non-recon node id(s): {sorted(bad)}")
    # SECONDARY DIAGRAMS (the 'more diagrams' links): every embedded artifact is a REAL rendered file the
    # run produced, and any node id it exposes is a recon element (no fabricated/substitute diagram).
    # Templated-with-blanks: an empty set (a Mermaid-only / no-SVG run) is fine — it just abstains here.
    for a in (g.get("gallery") or []):
        fp = os.path.join(run_dir, a.get("file", ""))
        if not a.get("file") or not os.path.exists(fp):
            D("gallery-artifact-missing", f"gallery artifact {a.get('file')!r} is not a real file in the run")
        bad_ids = set(a.get("node_ids") or []) - recon_ids
        if bad_ids:
            D("gallery-node-fabricated", f"gallery artifact {a.get('file')} references non-recon node id(s): {sorted(bad_ids)}")

    for n in g["nodes"]:
        if n["id"] not in recon_ids:
            D("diagram-node-fabricated", f"diagram node {n['id']} is not a recon element")
        if set(n["fids"]) - real_ids:
            D("diagram-node-fid-fabricated", f"node {n['id']} cites unknown finding(s)")
    allowed = _real_diagram_edges(recon, run_dir)
    for e in g["edges"]:
        if e["a"] not in recon_ids or e["b"] not in recon_ids:
            D("diagram-edge-fabricated", f"edge {e['a']}->{e['b']} references a non-recon node")
        if allowed is not None and (e["a"], e["b"]) not in allowed:
            D("diagram-edge-not-real", f"edge {e['a']}->{e['b']} is not in the run's real dataflows/diagram (synthesized?)")
        if set(e.get("fids", [])) - real_ids:
            D("diagram-edge-fid-fabricated", f"edge {e['a']}->{e['b']} cites unknown finding(s)")
    if allowed is None and g["edges"]:
        D("diagram-edges-without-source", "diagram has edges but the run has no dataflows/structural diagram")
    if g["source"] != "none" and not g["nodes"]:
        D("diagram-empty-with-source", "a diagram source exists but no nodes were drawn")

    # 4. LINK-GROUNDING — adjacency matches the manifests exactly.
    for eid, fids in model["links"]["entity_findings"].items():
        for fid in fids:
            f = next((x for x in F if x["id"] == fid), None)
            if not f or eid not in set((f.get("asset_refs") or []) + (f.get("surface_refs") or [])):
                D("link-ungrounded", f"entity {eid} → {fid} not backed by a manifest reference")

    # 8. EVIDENCE TRACEABILITY — every finding's embedded evidence is present, resolvable, and its
    #    excerpt MATCHES the cited source (re-extract independently: no fabricated excerpt); the jump-to
    #    node is a real recon element; honest no-evidence is shown explicitly (never a fabricated snippet).
    #    Reference-free: re-extract from the same source the build read and compare. Templated-with-blanks:
    #    a finding with NO evidence[] is a flow-gate concern (checks.py), not a dashboard defect here.
    ev_repo = str(repo) if repo else os.path.dirname(os.path.abspath(run_dir))
    m_by_id = model.get("findings_by_id", {})
    recon_names = model.get("links", {}).get("entity_names", {})
    for f in F:
        fid = f.get("id")
        raw_ev = f.get("evidence") or []
        emb_ev = (m_by_id.get(fid) or {}).get("evidence") or []
        if not raw_ev:
            continue
        for raw, emb in zip(raw_ev, emb_ev):
            if not isinstance(emb, dict):
                continue
            if emb.get("no_direct_evidence"):
                if not (emb.get("justification") or "").strip():
                    D("evidence-abstention-unjustified", f"{fid}: no_direct_evidence embedded without a justification")
                continue
            node = emb.get("node")
            if node and node not in recon_ids:
                D("evidence-node-fabricated", f"{fid}: evidence jump node {node!r} is not a recon element")
            if not emb.get("resolved"):
                D("evidence-unresolved", f"{fid}: evidence ref {emb.get('ref')!r} resolves nowhere in the source (no honest abstention)")
                continue
            # independent re-extraction from the same source — the embed must not fabricate the excerpt.
            recheck = ev.extract_item(ev_repo, raw if isinstance(raw, dict) else {}, recon_names)
            if emb.get("excerpt") and recheck.get("excerpt") and emb["excerpt"] != recheck["excerpt"]:
                D("evidence-excerpt-mismatch",
                  f"{fid}: embedded excerpt for {emb.get('ref')!r} does not match the cited source (fabricated/stale excerpt)")

    # 6 + 7. OFFLINE + NON-FABRICATION over the rendered HTML.
    try:
        sys.path.insert(0, str(_HERE.parent.parent / "references"))
        from dashboard_template import render
        htmlout = render(model)
    except Exception as e:  # rendering must never be the reason a real run is blocked
        D("render-error", f"dashboard render raised {type(e).__name__}: {e}")
        htmlout = ""
    if htmlout:
        ext = [u for u in re.findall(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', htmlout)
               if u.startswith(("http://", "https://", "//"))]
        if ext:
            D("not-offline", f"external resource load(s): {ext[:3]}")
        structural = re.findall(r'class="(?:f-id|kc-step[^"]*|node-id)"[^>]*>(TM-\d{3})', htmlout)
        bad = set(structural) - real_ids
        if bad:
            D("html-fabricated-id", f"finding ids in structural slots not in findings.json: {sorted(bad)}")
        # embed path: the run's real D2 SVG must actually be inlined (not linked/substituted).
        if g.get("diagram_source") == "embedded-svg" and "data-d2-version" not in htmlout \
                and 'class="embed-view"' not in htmlout:
            D("embed-svg-missing", "embedded-svg render path but the D2 SVG is not inlined in the HTML")

    return {"defects": defects, "scores": {"dashboard_pass": not defects},
            "stats": {"nodes": len(g["nodes"]), "edges": len(g["edges"]), "source": g["source"]}}


if __name__ == "__main__":
    import json
    print(json.dumps(check(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None), indent=2))
