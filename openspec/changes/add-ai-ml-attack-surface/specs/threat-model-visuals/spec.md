## ADDED Requirements

### Requirement: MITRE ATLAS Navigator layer for the AI/ML attack surface
The skill SHALL emit a MITRE ATLAS Navigator layer using the same Navigator JSON emitter as the existing
ATT&CK-enterprise layer, distinguished by `domain: "atlas-atlas"` and `AML.` technique ids, gated on the
declared `coverage.context.has_ai_ml` flag. The layer's techniques SHALL be the distinct `atlas[]` ids
across the findings — no technique invented on the layer that no finding maps to. When `has_ai_ml` is
false the ATLAS layer SHALL NOT be produced, and the existing ATT&CK-enterprise layer and all other
artifacts SHALL be unchanged.

#### Scenario: AI/ML target emits an ATLAS layer
- **WHEN** `coverage.context.has_ai_ml` is true and at least one finding declares an `atlas[]` id
- **THEN** the report includes a Navigator JSON layer with `domain: "atlas-atlas"` whose `techniques` are
  the distinct `atlas[]` ids across the findings, rendered by the same emitter that produces the
  ATT&CK-enterprise layer

#### Scenario: Non-AI target produces no ATLAS layer
- **WHEN** `coverage.context.has_ai_ml` is false
- **THEN** no ATLAS layer is produced, and the ATT&CK-enterprise layer, STRIDE matrix, heat map, and every
  other artifact are unaffected

### Requirement: OWASP-LLM Top-10 coverage checklist projected onto existing renderers
The skill SHALL render an OWASP-LLM Top-10 coverage checklist (rows LLM01–LLM10) using the existing
STRIDE-per-element matrix table renderer, gated on `has_ai_ml`, and SHALL NOT introduce a second AI/ML
diagram. Each row SHALL be resolved to a finding id, `n-a`, or `clean` by projecting the model's own
`atlas[]` ids through the fixed OWASP-LLM→ATLAS crosswalk in `frameworks.md`; a row with no matching
finding is a valid `n-a`/`clean` (honest abstention).

#### Scenario: Checklist reuses the matrix renderer, no new diagram
- **WHEN** `has_ai_ml` is true and the report is assembled
- **THEN** an OWASP-LLM Top-10 checklist (LLM01–LLM10, one row each) is rendered through the STRIDE-matrix
  table renderer, and no separate standalone OWASP-LLM diagram is emitted

#### Scenario: Row resolved by projection over the model's own ATLAS ids
- **WHEN** a finding declares an `atlas[]` id that falls in an OWASP-LLM class's crosswalk set
- **THEN** that OWASP-LLM row is marked with the finding id; a class whose crosswalk set matches no
  finding's `atlas[]` id is marked `n-a` or `clean`, and the checklist still passes
