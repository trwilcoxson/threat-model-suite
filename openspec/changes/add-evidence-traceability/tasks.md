# Tasks

## 1. Data model
- [ ] 1.1 Add an OPTIONAL additive `evidence[]` array to each finding in `findings.schema.json`: item `ref` (repo-relative path, `path:line`, `path:line-range`, glob, doc locator, or recon/diagram node id `C1`/`D1`/`E1`/`X1`/`TB1`), optional `kind` (`code`|`config`|`doc`|`diagram`), optional `quote`, `no_direct_evidence` (bool) + `justification`, and build-added `excerpt`
- [ ] 1.2 Keep it additive/nullable: committed manifests without `evidence` still conform (assert with `schema_checks.py`)

## 2. Flow enforcement
- [ ] 2.1 Extend the grounding check in `checks.py` to REQUIRE every finding carry ≥1 evidence `ref` that RESOLVES in the real source and is extractable (precise enough to pull an excerpt)
- [ ] 2.2 Allow `no_direct_evidence` + `justification` as the only abstention; fail on a silently missing or unresolvable reference; hold the determinism boundary (assert resolvability, never dictate content)
- [ ] 2.3 Update the agent prompts (security-architect + privacy/grc/code-review specialists) to attach resolvable evidence to EVERY finding, or abstain honestly
- [ ] 2.4 Keep the requirement in the run-gate + eval, NOT the schema (back-compat preserved)

## 3. Outputs — derive + embed
- [ ] 3.1 In `build_dashboard.py`, resolve each finding's evidence `ref` at BUILD time → extract the excerpt (cited line-range / doc quote / diagram element) → embed it self-contained (no repo needed to view)
- [ ] 3.2 In `dashboard_template.py`, show the evidence snippet in the finding drawer (monospaced, syntax-lit for code), the findable reference (`file:line`), and a jump to the related diagram node; render the honest no-evidence state, never a fabricated snippet
- [ ] 3.3 Embed the per-finding evidence excerpt in the report template similarly

## 4. Validators
- [ ] 4.1 Add a per-output reference-free evidence validator in `dashboard_checks.py`: every finding's evidence is present, resolvable, and the embedded excerpt matches the cited source (no fabricated excerpt)
- [ ] 4.2 Add cross-output consistency (dashboard and report cite the same evidence for the same finding) and honest-no-evidence assertions
- [ ] 4.3 Add self-check cases to `test_checks.py` (finding with resolvable evidence, honest abstention, a drifted/fabricated excerpt is caught)

## 5. Linked model
- [ ] 5.1 Wire finding ⇄ evidence-excerpt ⇄ source-location ⇄ diagram-node into the dashboard linked data model so pivots surface evidence both directions (finding → its evidence; diagram node → findings + their evidence)

## 6. Verify
- [ ] 6.1 `openspec validate add-evidence-traceability --strict`
- [ ] 6.2 `cd skills/threat-model/evals/reliability && python3 test_checks.py` (all pass)
- [ ] 6.3 `python3 schema_checks.py` (committed evidence-less manifests still conform)
