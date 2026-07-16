## Why

The suite scores and grounds threats but says almost nothing, machine-checkably, about the *defensive*
side. Every finding in `findings.json` carries a single free-text `remediation` string — prose that no
eval can address, no diagram can attach to, and no coverage property can flag. Concretely:

- **Remediation is unaddressable.** `remediation` is a bare string (`findings.schema.json:28`). There is
  no id to point a matrix cell at, no id for a defense node to reference, and no way to ask "which
  findings have *no* control at all?" The defensive dual of the STRIDE-per-element matrix (which proves
  every element was *examined*) simply does not exist — nothing proves every threat was *addressed*.
- **The one clean defensive coverage property is unclaimed.** "Every finding maps to ≥1 control, or is
  explicitly flagged accepted-risk/none" is a pure reference-free coverage check over the model's own
  findings — the same shape as the coverage ledger's "every applicable item reached a terminal state"
  (`coverage_checks.py`) and `no_issue_surface`'s "examined, clean" marker. Today a finding can ship with
  hand-wave remediation and nothing surfaces the gap.
- **Rank 7 (attack-defense trees) is blocked on a schema it does not own.** The T2-02 attack-defense-tree
  change needs to attach `counters:[attackNodeId]` to *addressable* controls. There is no control object
  to hang a counter-edge on, so the defensive-tree work cannot start until controls exist as first-class,
  id-bearing objects. This change is that shared enabler (research: `t2-artifacts/REPORT.md`, T2-03).
- **Normalized control naming has inputs but no home.** Findings already carry `mitre[]` ATT&CK ids, and
  MITRE CTID publishes NIST-800-53↔ATT&CK mappings and D3FEND countermeasures — enough to name controls in
  a normalized vocabulary. There is nowhere in the schema to record such a reference.

This is the cheapest genuinely-additive artifact in the T2 catalogue (rank 6, I4/E2/low): it reuses the
existing findings loop, the existing analytical-visuals renderer, and the existing framework-id
verification discipline, and its novel content is coverage/grounding-shaped — never correctness-shaped —
so it sits cleanly inside the determinism boundary.

## What Changes

- **Promote remediation into addressable control objects.** Additively extend `findings.schema.json`:
  each finding gains an optional `controls[]` array of `{id, name, framework_ref?, counters[]}`. `id` is a
  `CTL-NNN` addressable id; `name` carries the human control action (the migrated free-text); the existing
  `remediation` string is **retained unchanged** so legacy runs and in-flight reports still render.
- **Give each finding an explicit control disposition.** Add `control_disposition` ∈
  `{mitigated, accepted-risk, none}` and a `disposition_note`. `mitigated` means ≥1 control is attached;
  `accepted-risk` / `none` are honest abstentions that must carry a note (the reason the risk is accepted
  or no control applies). Both fields are optional in the schema so migration is backward-compatible.
- **Add the threat-to-control coverage property to the eval.** Over `findings.json` only, reference-free:
  (a) `control_disposition == mitigated` ⟺ `controls` non-empty (internal consistency); (b) findings that
  are neither controlled nor explicitly dispositioned are **flagged** as a coverage gap — a flag, never an
  auto-fail; (c) `accepted-risk`/`none` with a note pass as honest abstentions; (d) `framework_ref`, when
  present, is well-formedness-checked. A `control_coverage` profile (covered / accepted-risk / none /
  uncovered counts + covered fraction) joins the existing coverage stats.
- **Render the threat-to-control coverage matrix.** Add a `## Threat-to-Control Coverage Matrix` visual to
  `analytical-visuals.md` (a new §6) and Section IV-A of `report-template.md`: rows = findings, columns =
  control id(s) / normalized name / disposition, with zero-control findings shown as an explicit `GAP`
  cell (the same convention as the RBAC matrix's `GAP`). `diagram_checks.analytical_checks` verifies the
  matrix is present and a faithful projection of `findings.json`.
- **Reserve the counter-edge slot for attack-defense trees.** `controls[].counters[]` (default empty)
  holds attack-node ids the control interdicts — defined and consumed by the rank-7 attack-defense-tree
  change. Here it is only reserved and format-open; its grounding is deferred to that change.
- **Add normalized control naming to the framework-id discipline.** Extend the `frameworks.md` Framework
  ID Verification section with a curated NIST-800-53 / D3FEND control-id reference set and the rule that a
  `framework_ref` not in the set is written as plain text (never fabricated) — mirroring exactly how
  ATT&CK/CWE ids are handled today.

## Capabilities

### New Capabilities
- `control-coverage`: the addressable control-object model (`controls[]`, `control_disposition`,
  `counters[]` reservation), the reference-free threat-to-control coverage property (consistency +
  zero-control flagging with honest abstention), the format/agent-verification split for normalized
  control ids, and the threat-to-control coverage matrix as an analytical visual.

### Modified Capabilities
<!-- Additive only. The findings schema extension does not change any existing requirement of the
     structured-output-contract / manifest-validation-gate capabilities (existing fields, additionalProperties,
     and consistency checks are unchanged — only new optional properties are allowed). Composes with the
     coverage-ledger pattern (same attempt-every-item / honest-abstention shape, over findings.json instead
     of coverage.json) and with refine-pipeline-flow's Phase-7 analytical-visuals ownership (the matrix
     joins the Section IV-A bundle). Reverse dependency: the rank-7 attack-defense-tree change consumes
     controls[].counters[] from here. No requirement changes to those capabilities. -->

## Impact

- Modified: `skills/threat-model/evals/reliability/schema/findings.schema.json` (add optional `controls[]`,
  `control_disposition`, `disposition_note`; `remediation` unchanged), `evals/reliability/checks.py` (the
  control-coverage consistency + flagging property + `control_coverage` scores block, reusing the findings
  loop), `evals/reliability/diagram_checks.py` (matrix presence + faithful-projection check in
  `analytical_checks`), `references/analytical-visuals.md` (new §6 matrix format), `references/report-template.md`
  (Section IV-A gains the matrix), `references/frameworks.md` (control-id reference set + verification rule).
- New: none required — every surface already exists and is extended additively.
