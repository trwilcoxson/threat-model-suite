# Tasks

## 1. Control-object schema (additive, back-compat)
- [ ] 1.1 `findings.schema.json`: add optional `controls[]` to each finding — items `{id, name, framework_ref?, counters[]}`; `id` pattern `^CTL-[0-9]{3}$`; `name` string; `framework_ref` `["string","null"]` with a shaped NIST-800-53 / D3FEND pattern; `counters` array of string, default `[]`
- [ ] 1.2 `findings.schema.json`: add optional `control_disposition` enum `["mitigated","accepted-risk","none"]` and optional `disposition_note` string to each finding
- [ ] 1.3 `findings.schema.json`: keep `remediation` required and unchanged (back-compat); leave `additionalProperties: false` intact with the new properties added to the allow-set
- [ ] 1.4 Update the schema `description` to note that control-coverage is a reference-free per-finding property (consistency + zero-control flagging), not an answer key

## 2. Reference-free control-coverage property (checks.py)
- [ ] 2.1 In the findings loop, add a `control` defect layer: consistency check `control_disposition == "mitigated"` ⟺ `len(controls) >= 1` (both agent-emitted; flag disagreement)
- [ ] 2.2 Coverage flag: a finding neither controlled (`controls` empty) nor explicitly dispositioned (`accepted-risk`/`none`) is surfaced as an uncovered-control gap — a flag, never a hard fail
- [ ] 2.3 Honest abstention: `accepted-risk` / `none` pass **only** with a non-empty `disposition_note` (mirror the `unknown-without-note` rule); missing note → defect
- [ ] 2.4 Well-formedness: each `controls[].id` matches `^CTL-[0-9]{3}$`; each present `framework_ref` matches the shaped NIST-800-53 / D3FEND pattern (format only — no membership assertion offline)
- [ ] 2.5 Emit a `control_coverage` scores/stats block: counts by class (mitigated / accepted-risk / none / uncovered) and a covered fraction, alongside the existing coverage stats
- [ ] 2.6 Do NOT enforce grounding on `controls[].counters[]` (reserved for the rank-7 attack-defense-tree change)

## 3. Threat-to-control coverage matrix (render + verify)
- [ ] 3.1 `analytical-visuals.md`: add §6 "Threat-to-Control Coverage Matrix" — rows = findings (`TM-NNN`), columns = control id(s)/normalized name/disposition; zero-control findings shown as an explicit `GAP` cell (RBAC-matrix convention); state it is a faithful projection of `findings.json`
- [ ] 3.2 `report-template.md` Section IV-A: add `## Threat-to-Control Coverage Matrix` to the visual list with its precondition (≥1 finding) and the `GAP`-cell convention
- [ ] 3.3 `diagram_checks.py` `analytical_checks`: detect the matrix by its column set; check presence (gate: ≥1 finding) and faithful projection (every finding id appears; a zero-control finding shows `GAP`); presence/consistency only — never control correctness; add `control-matrix` to `analytical_present`

## 4. Normalized control naming (agent-verified, boundary-preserving)
- [ ] 4.1 `frameworks.md` Framework ID Verification: add a curated NIST-800-53 / D3FEND control-id reference set and the rule "a `framework_ref` not in the set is written as plain text — never fabricate a control id"
- [ ] 4.2 `frameworks.md`: add the control-id cross-check to the Phase 6 verification step (alongside ATT&CK/CWE id verification)

## 5. Migration / back-compat
- [ ] 5.1 Confirm a legacy `findings.json` (only free-text `remediation`, no `controls`/`control_disposition`) still passes schema validation and renders; the eval flags it as control-coverage-unknown without failing the run
- [ ] 5.2 Document the `CTL-NNN` ↔ `R-NNN` relationship (control object vs report roadmap item) in `analytical-visuals.md` §6 so the two id spaces do not read as duplication

## 6. Verify
- [ ] 6.1 `openspec validate add-control-coverage-matrix --strict`
- [ ] 6.2 Unit: a finding with `controls:[{id:CTL-001,...}]` + `control_disposition:mitigated` passes; the same with `control_disposition:none` flags a consistency defect
- [ ] 6.3 Unit: a finding with `controls:[]` + `control_disposition:accepted-risk` + a note passes (honest abstention); the same without a note flags a defect; with no disposition at all is flagged uncovered (not failed)
- [ ] 6.4 Unit: a malformed `controls[].id` / `framework_ref` is flagged; a well-formed `framework_ref` with an unknown mapping is NOT flagged by the eval (agent-verified only)
- [ ] 6.5 Live: a re-run emits `controls[]` + `control_disposition` and renders the Threat-to-Control Coverage Matrix with a `GAP` cell for any zero-control finding
