## ADDED Requirements

### Requirement: Findings carry addressable control objects

Each finding SHALL be able to carry a `controls` array of control objects, each with an addressable id
(`CTL-NNN`), a human-readable `name`, an optional normalized `framework_ref`, and a `counters` array
reserved for attack-defense-tree counter-edges. The extension SHALL be additive: the existing free-text
`remediation` field SHALL be retained and unchanged so that a findings manifest predating this change
still validates and still renders.

#### Scenario: Control object accepted and well-formed
- **WHEN** a finding declares `controls: [{ "id": "CTL-001", "name": "Enforce mTLS on service-to-service calls", "counters": [] }]`
- **THEN** the manifest validates, the control id is checked against `^CTL-[0-9]{3}$`, and the control is
  addressable by that id from the coverage matrix and (later) from counter-edges

#### Scenario: Legacy finding with only free-text remediation still validates
- **WHEN** a finding carries only the free-text `remediation` string and no `controls` array
- **THEN** the manifest still passes schema validation and the report still renders the remediation prose
  (the control-coverage property flags the finding but does not reject the run)

#### Scenario: Counter-edge slot reserved for attack-defense trees
- **WHEN** a control object is written with `counters: []`
- **THEN** the field is accepted and defaults empty, and no grounding is enforced on its members in this
  change — the attack-node id namespace and its grounding are defined by the attack-defense-tree change

### Requirement: Control disposition is internally consistent

Each finding SHALL be able to declare a `control_disposition` of `mitigated`, `accepted-risk`, or `none`.
`mitigated` SHALL hold if and only if the finding carries at least one control object; `accepted-risk` and
`none` SHALL each carry a `disposition_note`. The eval SHALL recompute the disposition from the finding's
own `controls` array and flag any disagreement, using no external truth.

#### Scenario: Mitigated agrees with a present control
- **WHEN** a finding has one or more `controls` and `control_disposition: "mitigated"`
- **THEN** the consistency check passes because the disposition matches the presence of controls

#### Scenario: Disposition contradicts the control array
- **WHEN** a finding has one or more `controls` but declares `control_disposition: "none"` (or has an empty
  `controls` array but declares `control_disposition: "mitigated"`)
- **THEN** the eval flags a control-consistency defect (the agent-stated disposition disagrees with the
  agent-stated control set)

#### Scenario: Abstention requires a note
- **WHEN** a finding has an empty `controls` array and `control_disposition: "accepted-risk"`
- **THEN** the finding passes only if it carries a non-empty `disposition_note`; a missing note is flagged,
  the same way an `unknown` coverage-ledger item without a note is flagged

### Requirement: Zero-control findings are flagged, never auto-failed

The eval SHALL treat "every finding maps to ≥1 control OR is explicitly flagged accepted-risk/none" as a
reference-free coverage property over the model's own findings. A finding that is neither controlled nor
explicitly dispositioned SHALL be surfaced as an uncovered-control gap (a flag), and the run SHALL NOT be
auto-failed for it. The eval SHALL report a control-coverage profile (counts by disposition class and a
covered fraction) alongside the existing coverage stats.

#### Scenario: Uncovered finding surfaced as a gap
- **WHEN** a finding has an empty `controls` array and no `control_disposition`
- **THEN** the eval flags the finding as an uncovered-control gap and includes it in the control-coverage
  profile, without rejecting the run

#### Scenario: Explicit abstention is honest coverage, not a gap
- **WHEN** a finding has an empty `controls` array, `control_disposition: "none"`, and a note explaining no
  control applies
- **THEN** the finding counts as an honest terminal state in the control-coverage profile and is not
  flagged as an uncovered gap

### Requirement: Control framework references are format-checked and agent-verified
A control object's optional `framework_ref` (a NIST-800-53 or D3FEND control id) SHALL be checked by the
eval for well-formedness only (a shaped id pattern), and the eval SHALL NOT assert that the referenced
control is the correct one for the finding. The authoritative reference set and the "never fabricate;
unknown mapping becomes plain text" rule SHALL live in the framework-id verification discipline the agent
applies (mirroring how ATT&CK and CWE ids are verified), not in the deterministic eval.

#### Scenario: Malformed framework reference flagged
- **WHEN** a control carries `framework_ref: "nist ac three"`
- **THEN** the eval flags it as malformed on format grounds (it does not match the NIST-800-53 / D3FEND id
  shape)

#### Scenario: Well-formed but unmapped reference is not judged by the eval
- **WHEN** a control carries a well-formed `framework_ref` that does not correspond to a known mapping for
  the finding's threat
- **THEN** the deterministic eval does not flag it (mapping correctness is verified by the agent against the
  reference set in `frameworks.md`, in Phase 6, not by the eval)

### Requirement: The threat-to-control coverage matrix is a faithful projection

When at least one finding exists, the report SHALL render a `## Threat-to-Control Coverage Matrix` in the
coverage-and-communication visuals section, with a row per finding mapping it to its control id(s),
normalized name, and disposition, and SHALL mark a finding with zero controls as an explicit `GAP` cell.
The eval SHALL verify the matrix is present and a faithful projection of `findings.json` — presence and
consistency only — and SHALL NOT judge whether any listed control is the correct remediation.

#### Scenario: Matrix present and complete when findings exist
- **WHEN** the findings manifest contains one or more findings and the report is assembled
- **THEN** the report contains the threat-to-control coverage matrix, every finding id appears as a row,
  and the matrix is recorded among the present analytical visuals

#### Scenario: Zero-control finding shown as a gap
- **WHEN** a finding has no controls and is dispositioned `none`
- **THEN** its matrix row shows a `GAP` cell (not a blank), so the coverage gap is visible in the rendered
  artifact as well as in the eval profile
