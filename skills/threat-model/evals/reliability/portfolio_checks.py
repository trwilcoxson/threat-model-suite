"""Reference-free reconciliation checks for the portfolio / chain-of-models meta-view.

Property checks over emitted facts — no answer key, mirroring the suite's determinism boundary. We assert
the aggregate RECONCILES to the members and that every cross-product link is GROUNDED, never that a specific
security judgment is "right". Ported from the prototype's `test_portfolio.py` into the repo's
`DEFECT [layer] code: detail` reporting shape.

Inert unless a `portfolio.json` is present: a run/dir without one returns no defects (skips), so this
changes nothing retroactively for every existing single-product run and the flagship gate.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent.parent / "scripts"
_REFERENCES = _HERE.parent.parent / "references"
_REPO_ROOT = _HERE.parents[4]
for _p in (str(_SCRIPTS), str(_REFERENCES)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

SEV = ("CRITICAL", "HIGH", "MEDIUM", "LOW")


def _portfolio_path(target: Path) -> Path | None:
    """`target` is a portfolio.json file, or a dir that may contain one. None => nothing to check."""
    if target.is_file() and target.name.endswith(".json"):
        return target
    p = target / "portfolio.json"
    return p if p.exists() else None


def check(target, repo=None) -> dict:
    """Return {"defects": [...]} — empty when no portfolio.json is present (honest abstention)."""
    target = Path(target)
    defects: list[dict] = []

    def D(code, detail):
        defects.append({"layer": "portfolio", "code": code, "detail": detail})

    pf_path = _portfolio_path(target)
    if pf_path is None:
        return {"defects": []}  # inert: no portfolio here

    try:
        portfolio = json.loads(pf_path.read_text())
    except (OSError, ValueError) as e:
        D("portfolio-malformed", f"{pf_path.name} is not valid JSON ({e})")
        return {"defects": defects}

    repo = str(repo) if repo else str(_REPO_ROOT)
    import build_portfolio as bp

    # build the derived model in a throwaway dir (member-dashboard render is a side effect we discard)
    with tempfile.TemporaryDirectory() as d:
        try:
            m = bp.build_portfolio_model(portfolio, repo, os.path.join(d, "member-dashboards"))
        except Exception as e:  # a member path that won't resolve is a real defect, not a crash
            D("portfolio-build-failed", f"could not build portfolio model: {e}")
            return {"defects": defects}

    defects += reconcile(m)
    return {"defects": defects}


def reconcile(m: dict) -> list[dict]:
    """Pure property check over a built portfolio model — no I/O. Every defect is a reconciliation or
    grounding violation over the emitted facts (reference-free)."""
    defects: list[dict] = []

    def D(code, detail):
        defects.append({"layer": "portfolio", "code": code, "detail": detail})

    # 1. Severity reconciles: portfolio == exact sum of members (no invented numbers).
    agg = {k: sum(mem["severity"][k] for mem in m["members"]) for k in SEV}
    if agg != m["severity"]:
        D("severity-drift", f"portfolio severity {m['severity']} != member sum {agg}")
    if m["findings_total"] != sum(agg.values()):
        D("severity-drift", f"findings_total {m['findings_total']} != {sum(agg.values())}")

    # 2. Worst-of posture: any member CRITICAL => portfolio CRITICAL (never hide a bad product).
    if any(mem["severity"]["CRITICAL"] for mem in m["members"]) and m["posture"]["band"] != "CRITICAL":
        D("posture-not-worst-of", f"a member is CRITICAL but portfolio band is {m['posture']['band']!r}")

    # 3. Auto-derived taxonomy links are cross-product and member-grounded (no fabricated membership).
    cwe_by_run = {mem["run_id"]: set(mem["cwe"]) for mem in m["members"]}
    mitre_by_run = {mem["run_id"]: set(mem["mitre"]) for mem in m["members"]}
    for kind, carrier in (("shared_cwe", cwe_by_run), ("shared_mitre", mitre_by_run)):
        for r in m["cross"][kind]:
            if r["fan_out"] < 2 or len(r["products"]) != r["fan_out"]:
                D("link-not-cross-product", f"{kind} {r['key']} fan_out={r['fan_out']} products={r['products']}")
            for p in r["products"]:
                if r["key"] not in carrier.get(p, set()):
                    D("link-ungrounded", f"{p} listed under {kind} {r['key']} but does not carry it")

    # 4. Declared edges: every KEPT edge resolves on both ends; every DROPPED edge is reported with a
    #    reason (grounding — a dangling edge is never silently rendered).
    elems = {mem["run_id"]: set(mem["element_ids"]) for mem in m["members"]}
    for e in m["edges"]:
        for side in ("source", "target"):
            run, el = e[side]["run"], e[side]["element"]
            if el not in elems.get(run, set()):
                D("edge-dangling-rendered", f"kept edge {e.get('id')} {side} {run}.{el} is not a real element id")
    for de in m["edges_dropped"]:
        if not de.get("reason"):
            D("edge-dropped-no-reason", f"dropped edge {de.get('id')} has no rejection reason")

    # 5. Uncovered is unknown, never green: a member with no ledger inflates neither assessed nor coverage.
    assessed = [mem for mem in m["members"] if mem["coverage_applicable"]]
    if m["kpis"]["assessed"] != len(assessed):
        D("coverage-miscount", f"kpis.assessed {m['kpis']['assessed']} != members-with-ledger {len(assessed)}")
    for mem in m["members"]:
        if not mem["coverage_applicable"] and mem["coverage_pct"] is not None:
            D("uncovered-not-unknown", f"member {mem['run_id']} has no ledger but coverage_pct={mem['coverage_pct']}")

    return defects


if __name__ == "__main__":
    tgt = sys.argv[1] if len(sys.argv) > 1 else "."
    rp = sys.argv[2] if len(sys.argv) > 2 else None
    res = check(tgt, rp)
    for d in res["defects"]:
        print(f"DEFECT [{d['layer']}] {d['code']}: {d['detail']}")
    print("PASS: portfolio reconciles + all links grounded." if not res["defects"]
          else f"\nFAIL: {len(res['defects'])} portfolio defect(s).")
    sys.exit(1 if res["defects"] else 0)
