## ADDED Requirements

### Requirement: Diagram detection uses the documented conventions
The deterministic diagram checks SHALL detect each diagram type by the convention the skill's references
document, not by an undocumented internal string. A spec-compliant diagram SHALL NOT be flagged as
missing solely because it used the documented stamp.

#### Scenario: Documented attack-flow stamp is detected
- **WHEN** an attack-flow diagram carries the documented stamp `%% Version: … | Type: Attack Flow | Chain: KC1`
- **THEN** the check recognizes it as an attack flow (no false `no-attack-flow` defect)

#### Scenario: Legend glyphs are not edges
- **WHEN** a diagram includes the spec-required legend as text nodes containing arrow glyphs
- **THEN** those glyphs are not counted as unlabeled edges

### Requirement: Deterministic checks gate on declared facts, never inferred content
A deterministic check SHALL derive its precondition from a skill-emitted fact (a declared role set, a
declared kill chain, a dependency manifest, a layer stamp), never from inferring meaning out of free text
(entry-point names, prose keywords).

#### Scenario: Auth-sequence gated on a declared fact
- **WHEN** the recon manifest declares no roles and no finding is Spoofing/Elevation
- **THEN** the auth-sequence diagram is not required — the requirement does not fire on an entry-point
  merely named like an auth endpoint

#### Scenario: Layer determined by the stamp
- **WHEN** a diagram block carries no `Layer: L{N}` version stamp
- **THEN** the check does not infer the layer from prose keywords; the missing stamp is itself the defect

### Requirement: Grounding resolution is sound
The grounding resolver SHALL treat evidence as grounded only when it actually resolves inside the target,
rejecting degenerate inputs (empty/whitespace, absolute paths that escape the target) and not letting a
common basename ground an invented path; it SHALL accept `path:line`-form evidence.

#### Scenario: Invented path does not resolve
- **WHEN** a recon element cites `made/up/nonexistent.json` (whose basename exists elsewhere) or an empty
  string or an absolute host path
- **THEN** the resolver reports it ungrounded

#### Scenario: Real path with a line suffix resolves
- **WHEN** a finding cites `app/routes/session.js:42` and that file exists in the target
- **THEN** the resolver reports it grounded

### Requirement: Layer scaling counts components
The layer-count scaling rule SHALL use the component count that the skill's own scaling guidance uses
(components), so a system the guidance calls small is not failed for choosing fewer layers.

#### Scenario: Small system, few layers
- **WHEN** a system has 4 components and 3 data stores (small per the guidance)
- **THEN** the check does not raise `missing-layers` for a 2-layer diagram

### Requirement: The reliability verdict reflects judged content
The rendered verdict SHALL be qualified by the judged layers' content — a low mean attack-path soundness,
an `inflated`/`thin` proportionality, or recon-audit missed subsystems downgrade an otherwise-green
verdict to a caveated one — without hard-failing on a judgment and without any judge payload being able to
crash report generation.

#### Scenario: Weak judged quality caveats a clean contract
- **WHEN** the deterministic contract holds on every run but the quality judge reports low mean soundness
- **THEN** the verdict is "reliable with caveats," naming the judged qualification, not an unqualified green

#### Scenario: Malformed judge payload never crashes
- **WHEN** a judge output file is present but malformed or an unexpected shape
- **THEN** report generation still completes (the malformed payload yields no caveat and no exception)
