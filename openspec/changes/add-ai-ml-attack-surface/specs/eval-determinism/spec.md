## ADDED Requirements

### Requirement: The findings contract carries an additive ATLAS id field
The findings manifest SHALL gain an optional, nullable `atlas[]` field on each finding whose members match
`^AML\.T\d{4}(\.\d{3})?$`, mirroring the existing nullable `mitre[]` field. The field SHALL be additive:
absence or a null value SHALL validate cleanly and SHALL be treated as an honest gap, never a failure. No
finding SHALL be required to carry an `atlas[]` id.

#### Scenario: ATLAS ids validated for shape only
- **WHEN** a finding declares `atlas: ["AML.T0051"]`
- **THEN** schema validation accepts it, and a finding that omits `atlas` or sets it to null also validates

#### Scenario: Malformed ATLAS id rejected on shape
- **WHEN** a finding declares `atlas: ["AML.T99999"]` (four-digit technique pattern violated)
- **THEN** the finding fails shape validation for the `atlas[]` field, exactly as a malformed `mitre[]` id
  would

### Requirement: The ATLAS layer is grounded and well-formed
A deterministic check SHALL verify, gated on `has_ai_ml` or a declared ATLAS id, that any ATLAS Navigator
layer has `domain == "atlas-atlas"`, that every `techniqueID` matches `^AML\.T\d{4}(\.\d{3})?$`, that
every sub-technique's parent technique is present, and that the technique ids shown are a **subset** of the
distinct `atlas[]` ids across the findings. The check SHALL NOT require any specific technique to be
present, and SHALL NOT run the ATT&CK `T\d{4}` regex over ATLAS ids (the `domain`/`AML.` discriminator).
When `has_ai_ml` is false and no finding declares an ATLAS id, the check SHALL be skipped.

#### Scenario: Shown ids are a subset of the findings' own ATLAS ids
- **WHEN** an ATLAS layer shows `AML.T####` technique ids
- **THEN** the check passes if and only if those ids are a subset of the distinct `atlas[]` ids across the
  findings, and a technique on the layer that no finding maps to is a defect

#### Scenario: Skipped when there is no AI surface
- **WHEN** `has_ai_ml` is false and no finding declares an `atlas[]` id
- **THEN** the ATLAS-layer check is skipped entirely and the run is not penalized for the layer's absence

### Requirement: AI/ML framework ids are validated against a fixed vocabulary keyed on the declared framework
A deterministic consistency check SHALL validate every emitted AI/ML framework id against the fixed regex
for its **declared framework field** — ATLAS ids (the `atlas[]` field) against
`^AML\.(TA\d{4}|T\d{4}(\.\d{3})?|M\d{4}|CS\d{4})$`, and OWASP-LLM ids (the OWASP-LLM checklist column)
against `^LLM(0[1-9]|10):2025$` — mirroring the existing `malformed-mitre` / `malformed-cwe` checks. The
check SHALL flag typos and fabrication (a well-formedness defect) and SHALL NOT require any specific id.
The regex SHALL be selected from the id's declared framework, never guessed from the bare token, so the
OWASP-Agentic `T1..T15` vs ATT&CK `T####` lexical overlap can never cause a mis-match.

#### Scenario: Fabricated ATLAS id flagged
- **WHEN** the `atlas[]` field contains `AML.T99999`
- **THEN** the check emits a `malformed-atlas` defect, while a well-formed `AML.T0051` passes

#### Scenario: Keyed on the declared framework, not the bare token
- **WHEN** an id is declared under the OWASP-LLM checklist column
- **THEN** it is matched against the OWASP-LLM regex (`^LLM(0[1-9]|10):2025$`), not the ATLAS or ATT&CK
  regex, and a bare `T3` token is never interpreted as an ATT&CK technique
