"""Reference-free deterministic checks over one threat-model run.

Everything here is derived from (target repo, emitted manifests) — there is no
per-target answer key. A check either passes for any well-formed, faithful threat
model or it flags a concrete defect.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

import diagram_checks
import schema_checks

STRIDE_LM = {"S", "T", "R", "I", "D", "E", "LM"}
SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

# Report-template sections expected in any complete model (matched loosely on heading text).
REPORT_SECTIONS = ["executive summary", "system overview", "architecture", "findings", "remediation"]


def band(score: int) -> str:
    if score <= 4:
        return "LOW"
    if score <= 9:
        return "MEDIUM"
    if score <= 16:
        return "HIGH"
    return "CRITICAL"


# CVSS v3.1 exploitability sub-score = 8.22 * AV * AC * PR * UI (FIRST.org v3.1 spec). Frozen metric
# weights; PR uses the Scope-Unchanged column because the suite does not adopt CVSS Scope. These weights,
# the normalizer, and the exploitability->1-5 thresholds are published as one table in
# references/frameworks.md — this is the single implementation of that table, no second scheme.
_CVSS_AV = {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20}
_CVSS_AC = {"L": 0.77, "H": 0.44}
_CVSS_PR = {"N": 0.85, "L": 0.62, "H": 0.27}  # Scope-Unchanged
_CVSS_UI = {"N": 0.85, "R": 0.62}
EXPLOIT_MAX = 3.887043  # 8.22 * 0.85 * 0.77 * 0.85 * 0.85 — the fixed maximum sub-score
_CVSS_VECTOR_RE = re.compile(r"^AV:([NALP])/AC:([LH])/PR:([NLH])/UI:([NR])$")
# Control id + normalized framework-ref shapes. Format-only (the offline eval never asserts a control
# is the *right* one — that is agent-verified against frameworks.md). NIST-800-53 (AC-3, SC-7(5)) or
# D3FEND (D3-NTA); a framework_ref that is present but unshaped is flagged, mirroring malformed-cwe.
_CTL_ID_RE = re.compile(r"^CTL-[0-9]{3}$")
_FRAMEWORK_REF_RE = re.compile(r"^([A-Z]{2}-[0-9]+(\([0-9]+\))?|D3-[A-Z]+)$")
# OWASP-LLM Top-10 id vocabulary (LLM01:2025 .. LLM10:2025). The loose shape captures an authored id in
# the checklist table (the DECLARED framework field); the strict shape validates it. The distinctive LLM
# prefix cannot collide with ATT&CK T#### / ATLAS AML.T#### ids, so the guardrail is keyed on the
# framework unambiguously — a bare `T3` OWASP-Agentic token is never read as an ATT&CK technique.
_OWASP_LLM_LOOSE = re.compile(r"LLM\d+(?::\d+)?")
_OWASP_LLM_STRICT = re.compile(r"LLM(0[1-9]|10):2025")


def exploitability_band(vector: str) -> int:
    """Map a CVSS v3.1 exploitability vector to a 1-5 Likelihood band via normalized quintiles.
    Raises ValueError on an unparseable vector.
    # ponytail: v1 uniform quintile split; upgrade path = recalibrate the five thresholds in
    # frameworks.md from a corpus of scored runs (a data edit, not a code change)."""
    m = _CVSS_VECTOR_RE.match((vector or "").strip())
    if not m:
        raise ValueError(f"unparseable CVSS exploitability vector {vector!r}")
    av, ac, pr, ui = m.groups()
    sub = 8.22 * _CVSS_AV[av] * _CVSS_AC[ac] * _CVSS_PR[pr] * _CVSS_UI[ui]
    return min(5, int(sub / EXPLOIT_MAX * 5) + 1)


class Defects:
    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def add(self, layer: str, code: str, detail: str) -> None:
        self.items.append({"layer": layer, "code": code, "detail": detail})

    def by_layer(self, layer: str) -> list[dict]:
        return [d for d in self.items if d["layer"] == layer]


def _load_json(path: Path, d: Defects, label: str):
    if not path.exists():
        d.add("structure", "missing-artifact", f"{label} not produced ({path.name})")
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        d.add("structure", "invalid-json", f"{label} is not valid JSON: {e}")
        return None


def _require(obj: dict, keys: list[str], d: Defects, where: str) -> bool:
    ok = True
    for k in keys:
        if k not in obj:
            d.add("structure", "missing-field", f"{where}: missing '{k}'")
            ok = False
    return ok


# -- grounding against the real repo ----------------------------------------

def _resolves_in_repo(repo: Path, evidence: str) -> bool:
    ev = (evidence or "").strip()
    # Reject up front: empty/whitespace (`repo / ""` is the repo dir → always "exists") and absolute
    # paths (`repo / "/etc/passwd"` escapes the repo to `/etc/passwd`). Neither is repo-relative evidence.
    if not ev or Path(ev).is_absolute():
        return False
    # A `path:line` / `path:line:col` reference grounds via its path — try with a trailing :NN(:NN) stripped.
    stripped = re.sub(r":\d+(?::\d+)?$", "", ev)
    # 1. FULL relative path or glob must resolve (no bare-basename fallback — a common basename like
    #    `package.json` must not ground an invented path such as `made/up/package.json`).
    for cand in [ev] if stripped == ev else [ev, stripped]:
        if (repo / cand).exists():
            return True
        try:
            if any(repo.glob(cand)):
                return True
        except (ValueError, OSError):
            pass
    # 2. literal source string present somewhere in the tree (cheap grep, skip .git)
    try:
        r = subprocess.run(
            ["grep", "-rqIF", "--exclude-dir=.git", ev, str(repo)],
            capture_output=True, timeout=20,
        )
        if r.returncode == 0:
            return True
    except (subprocess.TimeoutExpired, OSError):
        pass
    return False


def run_checks(run_dir: Path, repo: Path) -> dict[str, Any]:
    d = Defects()
    recon = _load_json(run_dir / "recon.json", d, "recon manifest")
    findings_doc = _load_json(run_dir / "findings.json", d, "findings manifest")
    report = run_dir / "report.md"

    # ---- structure: validate each manifest against its JSON-Schema contract (schema/*.json).
    # This is the file-based analog of a strict tool schema — enforced post-hoc because the agent
    # writes the manifests as files (no constrained decoding). Structure only; the consistency,
    # grounding, and coverage checks below are the semantic layer over the validated structure.
    for doc, schema_name, label in (
        (recon, "recon.schema.json", "recon"),
        (findings_doc, "findings.schema.json", "findings"),
    ):
        if doc is not None:
            try:
                for v in schema_checks.violations(schema_checks.load_schema(schema_name), doc):
                    d.add("structure", "schema-violation", f"{label}.json: {v}")
            except (OSError, ValueError) as e:
                d.add("structure", "schema-load-error", f"could not apply {schema_name}: {e}")

    # ---- structure: report.md present + has the expected sections
    raw_report = ""
    if not report.exists() or report.stat().st_size < 500:
        d.add("structure", "missing-report", "report.md absent or trivially short")
        report_text = ""
    else:
        raw_report = report.read_text()
        report_text = raw_report.lower()
        for sec in REPORT_SECTIONS:
            if sec not in report_text:
                d.add("structure", "missing-section", f"report.md has no '{sec}' section")

    surface_ids: set[str] = set()
    recon_ids: set[str] = set()
    grounded = ungrounded = 0
    if recon and _require(recon, ["components", "data_stores", "entry_points", "trust_boundaries", "external_deps"], d, "recon"):
        for bucket in ["components", "data_stores", "entry_points", "trust_boundaries", "external_deps"]:
            for el in recon.get(bucket, []):
                if not _require(el, ["id", "name", "evidence"], d, f"recon.{bucket}"):
                    continue
                recon_ids.add(el["id"])
                if bucket in ("entry_points", "data_stores", "trust_boundaries"):
                    surface_ids.add(el["id"])
                # grounding: at least one evidence string must resolve in the repo
                evs = el["evidence"] if isinstance(el["evidence"], list) else [el["evidence"]]
                if any(_resolves_in_repo(repo, e) for e in evs):
                    grounded += 1
                else:
                    ungrounded += 1
                    d.add("grounding", "ungrounded-element",
                          f"recon {el['id']} '{el['name']}' — no evidence resolves in repo: {evs}")

    # conditional requirement the schema can't express (validated in app code, not the schema): an
    # 'other' detected_pattern must carry a detail, mirroring coverage's present->source rule.
    if recon and recon.get("detected_pattern") == "other" and not (recon.get("detected_pattern_detail") or "").strip():
        d.add("structure", "detected-pattern-other-without-detail",
              "recon.detected_pattern is 'other' but detected_pattern_detail is empty")

    # ---- findings: consistency + grounding refs
    covered: set[str] = set()
    counts = {s: 0 for s in SEVERITIES}
    n_findings = 0
    cwe_total = mitre_total = atlas_total = 0
    control_classes = {"mitigated": 0, "accepted-risk": 0, "none": 0, "uncovered": 0}
    controls_total = 0
    fids: set[str] = set()
    if findings_doc and _require(findings_doc, ["findings", "summary_counts", "no_issue_surface"], d, "findings"):
        for f in findings_doc["findings"]:
            n_findings += 1
            fid = f.get("id", "?")
            if "id" in f:
                fids.add(f["id"])
            if not _require(f, ["id", "stride_lm", "likelihood", "impact", "severity", "asset_refs", "surface_refs"], d, fid):
                continue
            # value domains
            for cat in f["stride_lm"]:
                if cat not in STRIDE_LM:
                    d.add("structure", "bad-stride-lm", f"{fid}: '{cat}' not a STRIDE-LM category")
            if f["severity"] in SEVERITIES:
                counts[f["severity"]] += 1
            else:
                d.add("structure", "bad-severity", f"{fid}: severity '{f['severity']}'")
            # consistency: severity must equal band(L x I). Guard the domain first so an
            # out-of-range score (schema also flags it) can't be silently rubber-stamped as
            # self-consistent — band() has no domain guard of its own.
            try:
                L, I = int(f["likelihood"]), int(f["impact"])
                if not (1 <= L <= 5 and 1 <= I <= 5):
                    d.add("structure", "out-of-range-LxI", f"{fid}: likelihood/impact must be 1-5, got L{L} I{I}")
                else:
                    expect = band(L * I)
                    if f["severity"] != expect:
                        d.add("consistency", "severity-formula",
                              f"{fid}: severity {f['severity']} != band(L{L} x I{I})={expect}")
            except (ValueError, TypeError):
                d.add("structure", "bad-LxI", f"{fid}: non-integer likelihood/impact")
            # consistency: an optional CVSS exploitability vector must band to the finding's OWN
            # likelihood. Reference-free — recompute 8.22*AV*AC*PR*UI over the finding's own vector
            # and compare the derived band to its own stated likelihood (same recompute-over-emitted-
            # facts family as severity-formula). Fires only when the field is present; an unparseable
            # vector that slipped past the schema is a structure defect, never a silent pass.
            vec = f.get("cvss_vector")
            if vec:
                try:
                    derived = exploitability_band(vec)
                except ValueError:
                    d.add("structure", "bad-cvss-vector",
                          f"{fid}: cvss_vector {vec!r} is not a legal AV:_/AC:_/PR:_/UI:_ vector")
                else:
                    try:
                        stated = int(f["likelihood"])
                    except (ValueError, TypeError):
                        stated = None  # a non-integer likelihood is already flagged as bad-LxI above
                    if stated is not None and stated != derived:
                        d.add("consistency", "cvss-likelihood",
                              f"{fid}: stated likelihood {stated} != derived band {derived} from cvss_vector {vec}")
            # grounding: refs must resolve to recon ids
            for ref in f.get("asset_refs", []) + f.get("surface_refs", []):
                if recon_ids and ref not in recon_ids:
                    d.add("grounding", "dangling-ref", f"{fid}: ref '{ref}' not in recon manifest")
            covered.update(s for s in f.get("surface_refs", []) if s in surface_ids)
            covered.update(a for a in f.get("asset_refs", []) if a in surface_ids)
            # id well-formedness (fabrication is only partially checkable offline)
            for c in (f.get("cwe") or []):
                cwe_total += 1
                if not re.fullmatch(r"CWE-\d+", c):
                    d.add("consistency", "malformed-cwe", f"{fid}: '{c}'")
            for m in (f.get("mitre") or []):
                mitre_total += 1
                if not re.fullmatch(r"T\d{4}(\.\d{3})?", m):
                    d.add("consistency", "malformed-mitre", f"{fid}: '{m}'")
            # AI/ML controlled-vocabulary guardrail — keyed on the DECLARED framework field (the
            # atlas[] field -> the ATLAS regex), never guessed from the bare token, so an AML.T####
            # id is never run through the ATT&CK T\d{4} regex. Shape-only, mirroring malformed-mitre;
            # a missing/null atlas[] is never flagged. Broader ATLAS namespace than the schema's
            # technique-only field: tactics TA, techniques T, mitigations M, case-studies CS.
            for a in (f.get("atlas") or []):
                atlas_total += 1
                if not re.fullmatch(r"AML\.(TA\d{4}|T\d{4}(\.\d{3})?|M\d{4}|CS\d{4})", a):
                    d.add("consistency", "malformed-atlas", f"{fid}: '{a}'")

            # control coverage (the defensive dual of surface coverage) — reference-free over the
            # finding's OWN emitted facts. A `control` defect layer, NEVER in the production gate:
            # zero-control is a FLAG, not an auto-fail, and honest abstention passes. The eval never
            # asserts a control is the *correct* remediation — that is the agent/coverage-judge's job.
            controls = f.get("controls") or []
            controls_total += len(controls)
            disp = f.get("control_disposition")
            note = (f.get("disposition_note") or "").strip()
            has_ctl = len(controls) >= 1
            # well-formedness (format only; mapping correctness is agent-verified in Phase 6)
            for c in controls:
                cid = c.get("id", "") if isinstance(c, dict) else ""
                if not _CTL_ID_RE.fullmatch(cid):
                    d.add("control", "malformed-control-id", f"{fid}: control id '{cid}'")
                fr = c.get("framework_ref") if isinstance(c, dict) else None
                if fr and not _FRAMEWORK_REF_RE.fullmatch(fr):
                    d.add("control", "malformed-framework-ref", f"{fid}: framework_ref '{fr}'")
            # internal consistency + honest abstention + zero-control flag; classify for the profile
            if has_ctl:
                cls = "mitigated"
            elif disp == "accepted-risk":
                cls = "accepted-risk"
            elif disp == "none":
                cls = "none"
            else:
                cls = "uncovered"
            control_classes[cls] += 1
            if disp is not None:
                # `mitigated` iff >=1 control (both agent-emitted; recompute one from the other)
                if (disp == "mitigated") != has_ctl:
                    d.add("control", "control-disposition-mismatch",
                          f"{fid}: control_disposition '{disp}' disagrees with {len(controls)} control(s)")
                # accepted-risk / none are honest abstentions only WITH a note (unknown-needs-a-note rule)
                if disp in ("accepted-risk", "none") and not note:
                    d.add("control", "disposition-without-note",
                          f"{fid}: control_disposition '{disp}' but no disposition_note (why the risk is accepted / no control applies)")
            elif not has_ctl:
                # neither controlled nor explicitly dispositioned — a coverage gap, surfaced as a flag
                d.add("control", "uncovered-control",
                      f"{fid}: no controls and no control_disposition — control coverage unknown (flag, not a failure)")

        # summary counts must match reality
        for s in SEVERITIES:
            declared = findings_doc["summary_counts"].get(s)
            if declared != counts[s]:
                d.add("consistency", "count-mismatch", f"summary_counts.{s}={declared} but {counts[s]} findings present")

        # cross-artifact: report.md TM-NNN count vs manifest
        if report_text:
            report_tm = len(set(re.findall(r"tm-\d{3}", report_text)))
            if report_tm and abs(report_tm - n_findings) > 1:
                d.add("consistency", "report-manifest-drift",
                      f"report.md references {report_tm} TM ids but findings.json has {n_findings}")

        # coverage: every surface element examined (a finding, or explicitly no-issue)
        no_issue = set(findings_doc.get("no_issue_surface", []))
        uncovered = surface_ids - covered - no_issue
        for s in sorted(uncovered):
            d.add("coverage", "uncovered-surface", f"surface '{s}' has no finding and is not marked no-issue")

        # kill_chains: each declared step must reference a finding that exists (referential
        # integrity). The id FORMATS (^KC^, ^TM-NNN$) are enforced structurally by the schema;
        # this is the cross-field semantic check the schema cannot express.
        for kc in findings_doc.get("kill_chains", []) or []:
            kid = kc.get("id", "?")
            for step in kc.get("steps", []) or []:
                if step not in fids:
                    d.add("consistency", "killchain-dangling-step",
                          f"{kid}: step '{step}' is not a finding id in findings.json")

    # AI/ML controlled-vocabulary guardrail (OWASP-LLM) — keyed on the DECLARED framework field: the
    # OWASP-LLM Top-10 checklist table, identified by an "OWASP-LLM" header cell (never any table that
    # merely mentions an LLM class in prose, so a finding's OWASP-category cell is not mis-read). Every
    # LLM-prefixed id in that checklist is validated against the fixed vocabulary, shape only, mirroring
    # malformed-mitre/atlas. Never requires a particular class to be present.
    if raw_report:
        for tbl in diagram_checks._md_tables(raw_report):
            if not any(re.search(r"owasp[-\s]?llm", c, re.I) for c in tbl["header"]):
                continue
            for row in tbl["rows"]:
                for cell in row:
                    for tok in _OWASP_LLM_LOOSE.findall(cell):
                        if not _OWASP_LLM_STRICT.fullmatch(tok):
                            d.add("consistency", "malformed-owasp-llm", f"OWASP-LLM checklist id '{tok}'")

    # diagram verification (its own defect layer). Coverage carries the has_ai_ml gate for the ATLAS
    # layer block; loaded softly (coverage has its own checker in coverage_checks) so an absent
    # coverage.json never adds a defect here.
    cov_path = run_dir / "coverage.json"
    try:
        coverage = json.loads(cov_path.read_text()) if cov_path.exists() else None
    except (OSError, ValueError):
        coverage = None
    diag = diagram_checks.check(raw_report, recon, findings_doc, coverage)
    d.items.extend(diag["defects"])

    scores = _scores(d, grounded, ungrounded, surface_ids, covered, findings_doc)
    scores.update(diag["scores"])
    # control-coverage profile: counts by class + covered fraction (mitigated / n). A profile signal,
    # not a gate — uncovered findings are flagged, not failed (same as the coverage-ledger profile).
    covered_frac = round(control_classes["mitigated"] / n_findings, 3) if n_findings else None
    scores["control_coverage"] = {"by_class": control_classes, "covered_frac": covered_frac}
    return {
        "defects": d.items,
        "stats": {
            "findings": n_findings,
            "counts": counts,
            "recon_elements": len(recon_ids),
            "surface_elements": len(surface_ids),
            "surface_covered": len(covered),
            "grounded": grounded,
            "ungrounded": ungrounded,
            "cwe_ids": cwe_total,
            "mitre_ids": mitre_total,
            "atlas_ids": atlas_total,
            "controls": controls_total,
            "control_coverage": control_classes,
            "diagram": diag["stats"],
        },
        "scores": scores,
    }


def _scores(d: Defects, grounded: int, ungrounded: int, surface_ids: set, covered: set, findings_doc) -> dict:
    structure_ok = not d.by_layer("structure")
    consistency_ok = not d.by_layer("consistency")
    g_total = grounded + ungrounded
    grounding = round(grounded / g_total, 3) if g_total else None
    no_issue = set(findings_doc.get("no_issue_surface", [])) if findings_doc else set()
    examined = len((covered | no_issue) & surface_ids)
    coverage = round(examined / len(surface_ids), 3) if surface_ids else None
    return {
        "structure_pass": structure_ok,
        "consistency_pass": consistency_ok,
        "grounding": grounding,
        "coverage": coverage,
    }


if __name__ == "__main__":
    import sys
    out = run_checks(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(out, indent=2))
