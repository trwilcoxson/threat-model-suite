"""Reference-free structural verification of the coverage ledger.

Generalizes the visual-completeness pattern to the whole production-grade taxonomy. The skill attempts
every applicable item and records a terminal state; this checks STRUCTURE only:
  - every applicable item reached a terminal state (the agent tried — `pending`/missing is a defect),
  - `present`/`partial` cite a source that resolves in the target (grounded),
  - `unknown` carries a note (honest gap, never a failure),
  - applicability matches the skill-declared context (no answer key).
It computes a coverage profile (counts by state, present-with-evidence fraction). Whether a state is
*correct* is the coverage judge's job, not this.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import checks  # reuse _resolves_in_repo (the same grounding resolver the diagram/structure checks use)

TAXONOMY = Path(__file__).resolve().parent.parent.parent / "references" / "coverage-taxonomy.json"
STATES = {"present", "partial", "absent", "not-applicable", "unknown"}
GROUNDED = {"present", "partial"}
NOTED = {"absent", "not-applicable", "unknown"}


def load_taxonomy(path: Path = TAXONOMY) -> list[dict]:
    return json.loads(Path(path).read_text())["items"]


def applicable(item: dict, context: dict) -> bool:
    if item.get("tier") == 1:
        return True
    pre = item.get("precondition")
    return bool(pre) and bool(context.get(pre, False))


def check(coverage: dict | None, repo: Path, taxonomy: list[dict] | None = None) -> dict[str, Any]:
    taxonomy = taxonomy if taxonomy is not None else load_taxonomy()
    defects: list[dict[str, str]] = []
    warnings: list[str] = []

    def D(code: str, detail: str) -> None:
        defects.append({"layer": "coverage", "code": code, "detail": detail})

    if not coverage:
        D("no-coverage-ledger", "run produced no coverage.json ledger")
        return {"defects": defects, "warnings": warnings,
                "stats": {"applicable": 0, "by_state": {}, "present_with_evidence": None},
                "scores": {"coverage_pass": False, "coverage_present_frac": None}}

    context = coverage.get("context", {})
    by_id = {i["id"]: i for i in coverage.get("items", []) if isinstance(i, dict) and "id" in i}
    tax_by_id = {t["id"]: t for t in taxonomy}

    app_items = [t for t in taxonomy if applicable(t, context)]
    by_state: dict[str, int] = {s: 0 for s in STATES}
    grounded_ok = 0

    for t in app_items:
        led = by_id.get(t["id"])
        if not led or led.get("state") not in STATES:
            D("item-unassessed", f"applicable item '{t['id']}' ({t.get('section','')}) has no terminal state — not attempted")
            continue
        st = led["state"]
        by_state[st] += 1
        if st in GROUNDED:
            src = led.get("source") or []
            if not src:
                D("present-without-source", f"'{t['id']}' is {st} but cites no source")
            elif not any(checks._resolves_in_repo(repo, s) for s in src):
                D("present-ungrounded", f"'{t['id']}' is {st} but no source resolves in the target: {src[:3]}")
            else:
                grounded_ok += 1
        elif st == "unknown" and not (led.get("note") or "").strip():
            D("unknown-without-note", f"'{t['id']}' is unknown but carries no note (what was searched / why undetermined)")
        elif st in ("absent", "not-applicable") and not (led.get("note") or "").strip():
            warnings.append(f"'{t['id']}' is {st} without a reason note")

    # applicability consistency vs declared context
    for led in coverage.get("items", []):
        t = tax_by_id.get(led.get("id"))
        if not t or t.get("tier") != 2:
            continue
        pre = t.get("precondition")
        flag = bool(context.get(pre, False))
        if not flag and led.get("state") in GROUNDED:
            D("applicability-mismatch", f"'{led['id']}' is {led['state']} but its precondition '{pre}' is false in context")
        if flag and led.get("state") == "not-applicable":
            D("wrongly-not-applicable", f"'{led['id']}' marked not-applicable but precondition '{pre}' is true")

    n = len(app_items)
    present_frac = round((by_state["present"] + by_state["partial"]) / n, 3) if n else None
    return {
        "defects": defects,
        "warnings": warnings,
        "stats": {"applicable": n, "by_state": by_state, "grounded_ok": grounded_ok,
                  "present_with_evidence": present_frac, "context": context},
        "scores": {"coverage_pass": not defects, "coverage_present_frac": present_frac},
    }


if __name__ == "__main__":
    import sys
    cov = json.loads(Path(sys.argv[1]).read_text())
    print(json.dumps(check(cov, Path(sys.argv[2])), indent=2))
