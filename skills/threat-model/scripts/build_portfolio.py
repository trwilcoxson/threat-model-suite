#!/usr/bin/env python3
"""Portfolio / chain-of-models META-view generator — the layer ABOVE the per-product dashboard.

Deterministic transform:  portfolio.json (membership + DECLARED typed edges)
                          + each member run's canonical manifests (via build_dashboard.model_for_run)
                          -->  aggregate posture + grounded cross-product analytics
                          -->  a single self-contained HTML meta-view + per-member dashboards to drill into.

Determinism boundary (same discipline as build_dashboard.py, one level up):
  - The AGENTS emit each member's manifests; a human/agent DECLARES structural cross-product edges in
    portfolio.json. This script only RESHAPES + AGGREGATES emitted facts. It invents no finding, no
    number, and — critically — no cross-product edge.
  - AUTO-DERIVED cross links are computed ONLY over controlled GLOBAL vocabularies (CWE ids, MITRE ATT&CK
    technique ids, STRIDE-LM categories). A `CWE-306` in product A IS the same taxonomy node as `CWE-306`
    in product B — that join is set-equality on a shared namespace, not name matching, so it is grounded
    and reproducible. Freeform names (external-dep text, component tech) are NEVER auto-joined.
  - DECLARED edges (shared_component / upstream_trust / ...) reference real (run_id, element_id) pairs on
    BOTH ends. An edge whose endpoint does not resolve to a real recon element id is DROPPED and reported
    (never silently rendered) — the STIX/SPDX/OSCAL dangling-ref rule.
  - Every aggregate reconciles to the members: portfolio severity == sum of member severities, etc.
  - Uncovered data is `unknown`, never `green`: a member with no coverage.json contributes to neither the
    numerator nor the "assessed" count — absence of assessment is not safety.

Usage:
    python3 build_portfolio.py <portfolio.json> <out.html> [--repo <src_root>]

`href`/`path` in portfolio.json are resolved relative to <src_root> (default: the portfolio file's dir).
"""
import json, os, sys, html, re
from collections import Counter, defaultdict

# Reuse the MERGED per-product generator verbatim — one source of truth for member models.
_SCRIPTS = os.path.dirname(os.path.abspath(__file__))          # skills/threat-model/scripts
_SKILL = os.path.dirname(_SCRIPTS)                             # skills/threat-model
_REPO = os.path.dirname(os.path.dirname(_SKILL))              # repo root (default member-path root)
sys.path.insert(0, _SCRIPTS)                                  # build_dashboard is a sibling
sys.path.insert(0, os.path.join(_SKILL, "references"))        # portfolio_template + dashboard_template
import build_dashboard as bd  # noqa: E402

SEV_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
SEV_ORDER = ("CRITICAL", "HIGH", "MEDIUM", "LOW")
STRIDE_NAMES = bd.STRIDE_NAMES

# The DECLARED-edge vocabulary (typed edge over two resolvable ids; STIX-SRO / SPDX-Relationship shape).
EDGE_TYPES = {"shared_component", "shared_datastore", "shared_dependency", "upstream_trust",
              "downstream_trust", "shared_risk", "shared_killchain", "common_control"}


def _recon_element_ids(run_dir):
    """The real recon element ids of a member run (C*/D*/E*/X*/R*/TB*) -> name, for edge grounding."""
    recon = bd.load(run_dir, "recon.json") or {}
    out = {}
    for arr in ("components", "data_stores", "entry_points", "external_deps", "roles", "trust_boundaries"):
        for el in recon.get(arr, []) or []:
            if "id" in el:
                out[el["id"]] = el.get("name", el["id"])
    return out


def _posture_score(sev):
    n = sum(sev.values())
    if n == 0:
        return ("NO FINDINGS", 0)
    if sev["CRITICAL"] > 0:
        return ("CRITICAL", 95)
    if sev["HIGH"] >= 5:
        return ("HIGH RISK", 78)
    if sev["HIGH"] > 0:
        return ("ELEVATED", 60)
    if sev["MEDIUM"] > 0:
        return ("MODERATE", 40)
    return ("LOW", 20)


def build_member(spec, repo, member_out_dir):
    """One member: reuse build_dashboard.model_for_run for the FULL per-product model, then also render
    the member's real per-product dashboard so the meta-view can drill INTO it (offline)."""
    run_dir = os.path.join(repo, spec["path"])
    thin = bool(spec.get("thin"))
    model = bd.model_for_run(run_dir, thin_mode=thin, repo=run_dir if os.path.isdir(run_dir) else None)

    # render the member's own dashboard (the drill-down target) — same generator the flow uses.
    dash_rel = None
    try:
        from dashboard_template import render as render_dash
        os.makedirs(member_out_dir, exist_ok=True)
        dash_path = os.path.join(member_out_dir, spec["run_id"] + ".html")
        with open(dash_path, "w") as f:
            f.write(render_dash(model))
        dash_rel = os.path.relpath(dash_path, os.path.dirname(member_out_dir.rstrip("/")))
        dash_rel = os.path.join(os.path.basename(member_out_dir), spec["run_id"] + ".html")
    except Exception as e:  # drill-down link degrades to none; meta-view still renders
        sys.stderr.write(f"[warn] member dashboard render failed for {spec['run_id']}: {e}\n")

    sev = {k: model["severity"].get(k, 0) for k in SEV_ORDER}
    band, score = _posture_score(sev)
    cwe = set(model["cwe"].keys())
    mitre = {m["id"] for m in model["mitre"]}
    stride = {k for k, v in model["stride"].items() if v}
    return {
        "run_id": spec["run_id"], "label": spec.get("label") or model["system_name"],
        "system_name": model["system_name"], "path": spec["path"], "thin": thin,
        "dashboard": dash_rel, "posture": {"band": band, "score": score},
        "severity": sev, "findings_total": sum(sev.values()),
        "counts": model["counts"], "coverage_pct": model["coverage"]["present_pct"],
        "coverage_applicable": model["coverage"]["applicable"], "chains": len(model["chains"]),
        "cwe": sorted(cwe), "mitre": sorted(mitre), "stride": sorted(stride),
        # finding-id sets per taxonomy key, grounded, for the cross-product drill:
        "cwe_fids": {c: [f["id"] for f in model["findings"] if c in f["cwe"]] for c in cwe},
        "mitre_fids": {m: [f["id"] for f in model["findings"] if m in f["mitre"]] for m in mitre},
        "element_ids": sorted(_recon_element_ids(run_dir)) if os.path.isdir(run_dir) else [],
        "_element_names": _recon_element_ids(run_dir) if os.path.isdir(run_dir) else {},
        "top_findings": [{"id": f["id"], "title": f["title"], "sev": f["sev"]}
                         for f in model["findings"][:6]],
    }


def cross_links(members):
    """AUTO-DERIVED cross-product links — ONLY over controlled global vocabularies. A key appears here
    iff >=2 members share it (a genuine cross-product weakness/technique, same taxonomy node)."""
    def shared(attr, fids_attr):
        by_key = defaultdict(dict)  # key -> {run_id: [fids]}
        for m in members:
            for k in m[attr]:
                by_key[k][m["run_id"]] = m[fids_attr].get(k, [])
        rows = []
        for k, prod in by_key.items():
            if len(prod) >= 2:  # cross-product only
                rows.append({"key": k, "products": sorted(prod),
                             "fids": prod, "fan_out": len(prod),
                             "total": sum(len(v) for v in prod.values())})
        rows.sort(key=lambda r: (-r["fan_out"], -r["total"], r["key"]))
        return rows

    shared_stride = defaultdict(list)
    for m in members:
        for s in m["stride"]:
            shared_stride[s].append(m["run_id"])
    stride_rows = [{"key": k, "name": STRIDE_NAMES.get(k, k), "products": sorted(v), "fan_out": len(v)}
                   for k, v in shared_stride.items() if len(v) >= 2]
    stride_rows.sort(key=lambda r: (-r["fan_out"], r["key"]))

    return {
        "shared_cwe": shared("cwe", "cwe_fids"),
        "shared_mitre": shared("mitre", "mitre_fids"),
        "shared_stride": stride_rows,
    }


def resolve_edges(portfolio, members):
    """Validate DECLARED typed edges. Keep only edges whose BOTH endpoints resolve to a real element id in
    a real member (dangling-ref rule). Return (valid_edges, dropped_edges). Auto-derived edges are NEVER
    read from the manifest — they are computed in cross_links()."""
    by_run = {m["run_id"]: m for m in members}
    valid, dropped = [], []
    for e in portfolio.get("relationships", []) or []:
        etype = e.get("type")
        src, tgt = e.get("source") or {}, e.get("target") or {}
        reason = None
        if etype not in EDGE_TYPES:
            reason = f"unknown type '{etype}'"
        elif e.get("origin", "declared") != "declared":
            reason = "only 'declared' edges are persisted; derived links are computed, not stored"
        elif not e.get("provenance"):
            reason = "declared edge missing provenance"
        else:
            for side, ref in (("source", src), ("target", tgt)):
                m = by_run.get(ref.get("run"))
                if not m:
                    reason = f"{side} run '{ref.get('run')}' not a member"
                    break
                if ref.get("element") not in m["_element_names"]:
                    reason = f"{side} element '{ref.get('element')}' not a real recon id in '{ref.get('run')}'"
                    break
        rec = {"id": e.get("id"), "type": etype, "source": src, "target": tgt,
               "note": e.get("provenance", {}).get("rationale", ""), "provenance": e.get("provenance")}
        if reason:
            rec["reason"] = reason
            dropped.append(rec)
        else:
            rec["source_name"] = by_run[src["run"]]["_element_names"].get(src["element"], src.get("element"))
            rec["target_name"] = by_run[tgt["run"]]["_element_names"].get(tgt["element"], tgt.get("element"))
            valid.append(rec)
    return valid, dropped


def build_portfolio_model(portfolio, repo, member_out_dir):
    members = [build_member(s, repo, member_out_dir) for s in portfolio.get("members", [])]

    # aggregate severity == exact sum of member severities (reconciles by construction)
    agg = {k: sum(m["severity"][k] for m in members) for k in SEV_ORDER}
    band, score = _posture_score(agg)  # worst-of: any member CRITICAL => portfolio CRITICAL

    # coverage-of-coverage: only members with a real ledger count; the rest are UNKNOWN, never green.
    with_cov = [m for m in members if m["coverage_applicable"]]
    if with_cov:
        num = sum((m["coverage_pct"] or 0) * m["coverage_applicable"] for m in with_cov)
        den = sum(m["coverage_applicable"] for m in with_cov)
        cov_pct = round(num / den, 1) if den else None
    else:
        cov_pct = None

    riskiest = sorted(members, key=lambda m: (-m["severity"]["CRITICAL"], -m["severity"]["HIGH"],
                                              -m["severity"]["MEDIUM"], -m["findings_total"]))
    cross = cross_links(members)
    edges, dropped = resolve_edges(portfolio, members)

    # framework coverage union (which frameworks are exercised anywhere in the portfolio)
    all_cwe = sorted({c for m in members for c in m["cwe"]})
    all_mitre = sorted({t for m in members for t in m["mitre"]})

    # the map: product nodes + edges (declared structural edges, plus derived taxonomy-affinity weights).
    affinity = defaultdict(lambda: {"cwe": 0, "mitre": 0})
    for row in cross["shared_cwe"]:
        for a, b in _pairs(row["products"]):
            affinity[(a, b)]["cwe"] += 1
    for row in cross["shared_mitre"]:
        for a, b in _pairs(row["products"]):
            affinity[(a, b)]["mitre"] += 1
    map_edges = [{"a": a, "b": b, "cwe": v["cwe"], "mitre": v["mitre"], "kind": "affinity"}
                 for (a, b), v in sorted(affinity.items())]
    for e in edges:
        map_edges.append({"a": e["source"]["run"], "b": e["target"]["run"], "kind": "declared",
                          "type": e["type"], "note": e["note"]})

    return {
        "portfolio": {"id": portfolio.get("id"), "name": portfolio.get("name", "Untitled Portfolio"),
                      "description": portfolio.get("description", ""),
                      "schema": portfolio.get("schema", "portfolio/v1")},
        "posture": {"band": band, "score": score},
        "severity": agg, "findings_total": sum(agg.values()),
        "kpis": {"products": len(members), "assessed": len(with_cov),
                 "findings": sum(agg.values()), "critical": agg["CRITICAL"],
                 "high": agg["HIGH"] + agg["CRITICAL"], "coverage_pct": cov_pct,
                 "shared_cwe": len(cross["shared_cwe"]), "shared_mitre": len(cross["shared_mitre"]),
                 "declared_edges": len(edges)},
        "members": [{k: v for k, v in m.items() if not k.startswith("_")} for m in members],
        "riskiest": [m["run_id"] for m in riskiest],
        "cross": cross, "edges": edges, "edges_dropped": dropped, "map_edges": map_edges,
        "frameworks": {"cwe": all_cwe, "mitre": all_mitre},
        "empty": {"edges": not edges, "shared_cwe": not cross["shared_cwe"],
                  "shared_mitre": not cross["shared_mitre"], "coverage": cov_pct is None},
    }


def _pairs(xs):
    for i in range(len(xs)):
        for j in range(i + 1, len(xs)):
            yield xs[i], xs[j]


def main():
    args = sys.argv[1:]
    repo = _REPO
    if "--repo" in args:
        i = args.index("--repo")
        repo = args[i + 1]
        args = args[:i] + args[i + 2:]
    if len(args) != 2:
        print(__doc__)
        sys.exit(1)
    pf_path, out = args
    portfolio = json.load(open(pf_path))
    # member `path`s resolve against `repo` (default: repo root); absolute member paths override it.
    out_dir = os.path.dirname(os.path.abspath(out)) or "."
    member_out_dir = os.path.join(out_dir, "member-dashboards")
    model = build_portfolio_model(portfolio, repo, member_out_dir)
    with open(os.path.splitext(out)[0] + ".model.json", "w") as f:
        json.dump(model, f, indent=2)
    from portfolio_template import render
    with open(out, "w") as f:
        f.write(render(model))
    print("wrote", out, "and", os.path.splitext(out)[0] + ".model.json",
          f"({model['kpis']['products']} products, {model['findings_total']} findings, "
          f"{len(model['edges'])} declared edges, {len(model['edges_dropped'])} dropped)")


if __name__ == "__main__":
    main()
