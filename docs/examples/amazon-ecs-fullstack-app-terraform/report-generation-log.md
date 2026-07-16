# Report Generation Log

| Field | Value |
|-------|-------|
| Agent | report-analyst (consolidation & multi-format generation) |
| Date | 2026-07-11 |
| Target System | AWS ECS Fullstack App (Terraform Demo) |
| Output directory | `{output_dir}/` |
| Template followed | `references/report-template.md` (all 14 sections + IV-A, in exact order) |
| Toolchain | `@mermaid-js/mermaid-cli` (diagrams); Python venv `/tmp/report-venv` with `python-docx`, `python-pptx`, `reportlab`, `Pillow`; single `report_data.py` data model feeding four generators |

---

## 1. Deliverables

| Deliverable | Status | Size | Notes / Errors |
|-------------|--------|------|----------------|
| `report.html` | **SUCCESS** | 165,967 bytes | Single-file; all CSS/JS inline; 2 PNGs referenced by relative `<img src>`; no external deps. |
| `report.docx` | **SUCCESS** | 3,163,969 bytes | Full report, all 14 sections + IV-A; both diagrams embedded (`width=6.5in`). |
| `report.pdf` | **SUCCESS** | 3,836,727 bytes | 46 pages (letter); reportlab/platypus; 2 embedded diagram images; page footer + numbering. |
| `executive-summary.pptx` | **SUCCESS** | 1,913,967 bytes | 8 slides, 16:9; risk-overlay diagram embedded on slide 4; no shapes overflow the canvas. |
| `structural-diagram.png` | **SUCCESS** | 1,371,231 bytes | L1 architecture (5826x7368). |
| `risk-overlay-diagram.png` | **SUCCESS** | 2,061,748 bytes | L4 threat overlay (7384x7742). |

All six files exist and are non-empty. No deliverable failed.

---

## 2. Diagram Rendering Results

Source `.mmd` files written to the output dir, then rendered with:
`npx -y @mermaid-js/mermaid-cli -i <in>.mmd -o <out>.png -c references/mermaid-config.json -w 3000 --scale 2 -b white`

| Diagram | Source | mermaid-cli exit | Output | Warnings |
|---------|--------|:----------------:|--------|----------|
| `structural-diagram.png` | `structural-diagram.mmd` (L1 architecture layer, extracted from `02-structural-diagram.md`) | **0** | 5826x7368, 1.37 MB (not a stub) | none material |
| `risk-overlay-diagram.png` | `risk-overlay-diagram.mmd` (copy of Phase-7 `ecs-fullstack-L4-threat-overlay.mmd`) | **0** | 7384x7742, 2.06 MB (not a stub) | none material |

Both rendered clean on the first pass. Visual spot-check (headless Chromium screenshot of the HTML; `pdftoppm` render of the PDF diagram page) confirmed the L4 overlay shows correct risk color-coding (red=HIGH/CRITICAL, orange=MEDIUM, green=LOW), STRIDE/CWE node annotations, and the thick-red KC01-KC04 attack-path overlays. The Phase-7 companion diagrams (`ecs-fullstack-attack-tree-{1..4}.mmd`, `ecs-fullstack-attack-flow-{1..4}.mmd`, `ecs-fullstack-sbom.mmd`) were left as-is in the output dir and referenced in the report (Section IV-A) rather than re-rendered inline, per the "at minimum embed structural + risk-overlay" instruction.

---

## 3. HTML Validation Checks (report.html)

Each mandatory check run via `grep`:

| # | Check | Expected | Result | Detail |
|---|-------|----------|--------|--------|
| 1 | `<img` PNG embeds present | >= 2 | **PASS** | 2 embeds: `src="structural-diagram.png"`, `src="risk-overlay-diagram.png"`. |
| 2 | No Mermaid CDN / client-side render | 0 | **PASS** | `grep -ic 'mermaid'` = 0. |
| 3 | No JS-escaped closing script tag | 0 | **PASS** | escaped form = 0; exactly 1 literal `</script>`. |
| 4 | No `defer`/`async` on script tag | 0 | **PASS** | inline JS runs after the DOM it reads (script is last in body). |
| 5 | `charset` meta declared | 1 | **PASS** | `<meta charset="utf-8">` is the first line (fixed after a first-pass mojibake finding - see section 5). |
| 6 | No external CDN / http(s) resource refs | 0 | **PASS** | only self-contained inline CSS/JS + the 2 local PNGs. |

Additional HTML rules satisfied: closing `</script>` written literally (not escaped); no `defer`/`async`; all CSS and JS inline in the single file; finding IDs (`TM-NNN`) hyperlinked to their finding cards; both diagrams embedded as pre-rendered `<img>` PNGs (never Mermaid.js).

---

## 4. Corrections Applied from validation-report.md

| # | Correction | How applied in the report |
|---|-----------|---------------------------|
| 1 | **Deduplication - 49 finding-records to ~28 distinct issues** across merge clusters C1-C13 (do NOT double-count). | Section VII presents 28 distinct findings: the 25 validated threat-model findings + the 3 program-level items with no technical-track twin (GRC-008 governance, PA-002 privacy notice, PA-004 privacy governance). Cross-track source IDs are listed per finding via the `Source` row; severities are never summed. Executive-summary count (28) matches Section VII exactly. |
| 2 | **Severity harmonization / preserve dual scores** - highest severity for prioritization, show the range, never convert lenses. | Merged rows carry the CVSS v3.1 score (e.g., TM-002 shows CVSS 7.4 from CR-001) alongside the OWASP LxI band; the `Source` row names all contributing tracks. Severity conflicts (C1/C2/C7/C10) presented at the unified/highest band with the lens noted. |
| 3 | **DevOps-role precision** - grants are enumerated action lists on `resources=["*"]`, NOT literal `s3:*`/`ecs:*` action wildcards; the sharp risk is `RegisterTaskDefinition`+`RunTask`+`PassRole *`. | TM-016 title and body corrected to "broad ECS/S3 action lists + `iam:PassRole *` on wildcard resources"; CR-002's precise IAM line refs adopted (per validation section 8). Logged in Appendix C QA log. |
| 4 | **TM-009 to TM-001** and **TM-027 to TM-012** merges. | Reflected: only 25 TM findings (no TM-009/TM-027). TM-001 body notes it absorbs the network-position gap; TM-012 body notes it absorbs the PAT-lifecycle gap. |
| 5 | **TM-026 mechanism** - reframe from "over-broad delete" to overwrite/ransom (`PutObject`, not `DeleteObject`) + `force_destroy`. | TM-026 title/body corrected; kept MEDIUM. |
| 6 | **Frame GRC HIGHs as production-readiness / audit-readiness severity on non-personal data, not live exploit.** | Section X preamble, GRC-008 finding, and the Assumptions "Confidence Disclaimers" all state this explicitly; GRC severities are presented distinct from CVSS/OWASP live-exploit severity so they are not double-weighted. |
| 7 | **Privacy is conditional** - current-state LOW (no data subjects), with a conditional column; do not present as current HIGH. | Section XI preamble + each LINDDUN row show "LOW (current) - conditional ..."; PA-002/PA-004 findings scored current L1xI1=1. |
| 8 | **CWE-79 loose fit for TM-023**; **ISO Clause 6.1.2 / HIPAA 45 CFR 164.502** advisory citations. | Noted inline in TM-023 (CWE-1021/693 fit better), the cross-framework table (dagger on Clause 6.1.2), and the Privacy regulatory note (164.502 out-of-set); all captured in Appendix C. |
| 9 | **Coverage ledger sourced from `coverage.json`** (final, merged). | Section XIII Coverage Profile uses the actual ledger counts - present 90 / partial 57 / absent 52 / not-applicable 25 / unknown 1 = 225 (224 terminal). The single `unknown` (`risk-assessment.risk-acceptance-ownership`) and the SNS-topic-policy question are the Open Questions; partials + absent-by-gap are the Known Limitations. |

Note on ledger counts: the validation-report narrative quoted 90/59/51/24/1; the merged `coverage.json` file (the authoritative artifact) tallies **90/57/52/25/1 = 225**. The report uses the file's actual counts, as instructed to source from the ledger.

---

## 5. Issues Encountered & Resolutions

| Issue | Resolution |
|-------|-----------|
| **First-pass HTML mojibake** - em-dashes / multiplication-sign / middot rendered as garbage. | Root cause: no charset declaration, so the browser guessed Latin-1. Added `<meta charset="utf-8">` as the first line. Re-verified via headless screenshot - all Unicode now correct. |
| **Hero `<h1>` dark-on-dark** in the HTML header. | CSS specificity trap: the generic `h1{color:var(--ink)}` (a direct rule) beat the inherited light color under `.hero`. Fixed by setting `color:#f4f8fc` explicitly on `.hero h1`. |
| **Stale HTTP server on port 8899** served a *different* previous report during the visual check (wrong `<title>`). | The port was already bound by an earlier session's server; my new server silently failed to bind and curl hit the old one. Killed the stale process and moved to port 8911; confirmed the correct file was served. (No effect on the deliverable - the on-disk `report.html` was always correct.) |
| **reportlab PDF: `Invalid color value 'c0392b'`** and markup passed through an escaping helper. | reportlab `<font color>` requires a `#` prefix (fixed) and a non-escaping raw-markup helper was added so intentional `<b>`/`<font>` tags render instead of being HTML-escaped; plain text still routes through the escaping helper. |
| **Large PNG dimensions** (up to 7742 px tall) for docx/pdf/pptx embedding. | Scaled to fit: docx `width=6.5in`; pdf capped at frame width and 8.4in height (aspect-preserving); pptx fit-to-box with `min(w,h)` scale. |
| **PPTX could not be pixel-rendered** (no LibreOffice/soffice available). | Validated structurally instead with `python-pptx`: 8 slides, image embedded on slide 4, and **0 shapes past the canvas edge** (bounds-checked all shapes against the 13.33x7.5in canvas). Layout uses explicit inch coordinates with `word_wrap=True`. |

Cross-reference integrity was validated programmatically before generation: every finding ID appears in the Section IV Component Risk Mapping table; every finding maps to a defined `R-` remediation; every defined `R-` is referenced by >=1 finding; the Section I count (28) equals the Section VII count.

---

## 6. Overall Self-Assessed Quality

**HIGH.**

Justification:
- **Completeness** - all 14 template sections plus IV-A are present in exact order in the HTML, DOCX, and PDF; the PPTX is a purpose-built 8-slide executive summary. All mandated tables use the template's exact column headers.
- **Accuracy & dedup discipline** - findings are deduplicated to 28 distinct issues per the C1-C13 merge clusters with no double-counting; dual scores (OWASP LxI + CVSS + qualitative) are preserved, not converted; all nine documented corrections from `validation-report.md` are applied and logged.
- **Fidelity** - every table/finding traces to `findings.json`, `recon.json`, `coverage.json`, or a specialist report; a single `report_data.py` model feeds all four renderers, so the formats cannot drift from one another.
- **Diagrams** - both required PNGs rendered clean (non-stub) at high resolution and are embedded in every format; the risk overlay's color-coding and attack-path overlays were visually confirmed.
- **Verification** - all six HTML rules pass by grep; the PDF (46 pp, 2 images) and PPTX (8 slides, image embedded, no overflow) were checked; the HTML was screenshotted in a headless browser and refined.

Residual limitations (not defects): the PPTX was validated structurally rather than pixel-rendered (no LibreOffice available); the Phase-7 companion attack-tree/flow/SBOM `.mmd` diagrams are referenced rather than re-embedded inline, per the "at minimum embed structural + risk-overlay" scope.
