"""Reference-free verification that a run produced EXACTLY the planned team + outputs.

Layer C of deterministic run-selection (see SELECTION-DESIGN.md). Pure property over emitted facts —
file existence + set comparison against the run's own `run-plan.json`. No model, no answer key, so it
never asserts a golden verdict; it only asserts "the produced artifact set == the plan the user
confirmed". Both directions are defects: a MISSING planned artifact and an EXTRA un-planned one.

Two stages, because outputs are generated AFTER the report-analyst spawn:
  - stage="post"  (run.py check, post-hoc) — full both-directions check over every specialist + output.
  - stage="gate"  (run.py validate, the report-spawn gate) — team both-directions + only EXTRA
                  (un-planned) outputs; a planned-but-absent OUTPUT is skipped because the report-analyst
                  has not run yet (skipping it here is what prevents a gate deadlock; the post stage
                  still catches a genuinely missing output).

Inert unless `run-plan.json` is present: a run without a plan (every existing sample-run / the archived
flagship) returns no defects, so this changes nothing retroactively.
"""
from __future__ import annotations

import json
from pathlib import Path

import schema_checks

# planned token -> the artifact whose presence proves it ran / was produced.
SPECIALIST_FILE = {"privacy": "privacy-assessment.md", "grc": "compliance-gap-analysis.md",
                   "code-review": "code-security-review.md"}
CONCRETE_OUTPUT = {"report.html": "report.html", "report.docx": "report.docx",
                   "report.pdf": "report.pdf", "executive-summary.pptx": "executive-summary.pptx",
                   "dashboard": "dashboard.html"}
# analytical-visuals is a FAMILY of files (matrices, ATT&CK layer, overlay diagram); presence is proven
# by any one marker. We only check present-iff-planned in one direction (its byproducts are hard to
# forbid), so it is never used to flag "extra".
VISUAL_MARKERS = ["risk-overlay-diagram.mmd", "risk-overlay-diagram.png", "ecs-fullstack-attack-navigator-layer.json"]


def _load_plan(run_dir: Path):
    p = run_dir / "run-plan.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return "malformed"


def _has_visual(run_dir: Path) -> bool:
    if any((run_dir / m).exists() for m in VISUAL_MARKERS):
        return True
    return any(run_dir.glob("*attack-navigator-layer.json")) or any(run_dir.glob("*stride*matrix*")) \
        or any(run_dir.glob("*control-coverage*"))


def check(run_dir, stage: str = "post") -> dict:
    run_dir = Path(run_dir)
    defects: list[dict] = []

    def D(code, detail):
        defects.append({"layer": "run-plan", "code": code, "detail": detail})

    plan = _load_plan(run_dir)
    if plan is None:
        return {"defects": defects, "scores": {"run_plan_pass": True}, "stats": {"planned": False}}
    if plan == "malformed":
        D("run-plan-malformed", "run-plan.json is not valid JSON")
        return {"defects": defects, "scores": {"run_plan_pass": False}, "stats": {"planned": True}}

    for v in schema_checks.violations(schema_checks.load_schema("run-plan.schema.json"), plan):
        D("run-plan-schema", f"run-plan.json: {v}")

    team = set(plan.get("team", []) or [])
    outputs = set(plan.get("outputs", []) or [])
    if plan.get("mode") == "solo" and team:
        D("run-plan-inconsistent", f"mode=solo must carry team=[]; got {sorted(team)}")

    # SPECIALISTS — present iff planned, both directions (specialists run before the report gate).
    for token, fname in SPECIALIST_FILE.items():
        exists = (run_dir / fname).exists()
        planned = token in team
        if planned and not exists:
            D("missing-planned-specialist", f"team includes '{token}' but {fname} is absent")
        if exists and not planned:
            D("extra-unplanned-specialist", f"{fname} present but '{token}' is not in the planned team")

    # CONCRETE OUTPUTS — extra-unplanned always blocks; missing-planned only in the post stage.
    for token, fname in CONCRETE_OUTPUT.items():
        exists = (run_dir / fname).exists()
        planned = token in outputs
        if exists and not planned:
            D("extra-unplanned-output", f"{fname} present but '{token}' is not a planned output")
        if planned and not exists and stage == "post":
            D("missing-planned-output", f"outputs include '{token}' but {fname} is absent")

    # ANALYTICAL VISUALS — present-if-planned (one direction), post stage only.
    if "analytical-visuals" in outputs and stage == "post" and not _has_visual(run_dir):
        D("missing-planned-output", "outputs include 'analytical-visuals' but no analytical visual artifact is present")

    return {"defects": defects, "scores": {"run_plan_pass": not defects},
            "stats": {"planned": True, "mode": plan.get("mode"), "team": sorted(team), "outputs": sorted(outputs)}}


if __name__ == "__main__":
    import sys
    print(json.dumps(check(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "post"), indent=2))
