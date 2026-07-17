## ADDED Requirements

### Requirement: Evidence is first-class and resolvable on every finding

Every finding SHALL be able to carry direct, problem-specific evidence in an OPTIONAL additive
`evidence[]` array on the finding itself, distinct from the recon evidence inherited transitively through
the components it references. Each evidence item SHALL carry a `ref` — a findable reference (a
repo-relative path, `path:line`, `path:line-range`, glob, doc locator, or a recon/diagram node id such as
`C1`/`D1`/`E1`/`X1`/`TB1`) that resolves in the target source and is precise enough to extract an excerpt.
An item MAY carry a `kind` (`code`|`config`|`doc`|`diagram`) and a `quote` (the agent's verbatim snippet);
the build generators add the resolved `excerpt` at build time. An item MAY instead declare
`no_direct_evidence` with a required `justification`. The `evidence[]` field SHALL be additive and
nullable so that existing committed manifests without it still conform to the schema.

#### Scenario: A finding carries a resolvable, extractable reference

- **WHEN** an agent emits a finding for a concrete flaw
- **THEN** the finding carries at least one `evidence[]` item whose `ref` resolves in the run's real
  source and is precise enough that an excerpt of the cited code, config, document, or diagram element can
  be extracted from it

#### Scenario: Evidence-less committed manifests still conform

- **WHEN** a previously committed `findings.json` that has no `evidence` on its findings is validated
  against the schema
- **THEN** it conforms, because `evidence[]` is additive and nullable and the presence requirement is not
  baked into the schema

### Requirement: Evidence is enforced across the whole agent flow with honest abstention

Every agent that emits findings SHALL attach resolvable evidence to EVERY finding — the
security-architect and the privacy, GRC, and code-review specialists alike. A reference-free run-gate check, extending
the existing grounding check, SHALL verify that each finding has at least one evidence reference that
RESOLVES in the real source and is extractable. The only allowed abstention SHALL be an explicit
`no_direct_evidence` with a `justification`; a finding that is neither grounded nor honestly abstaining
SHALL fail the gate. The check SHALL assert only resolvability and extractability, never dictate the
content of the evidence, preserving the determinism boundary. This presence/resolvability requirement
SHALL be enforced in the run-gate and eval — NOT in the schema — so committed evidence-less manifests
still validate.

#### Scenario: Every finding is grounded or honestly abstains

- **WHEN** the run-gate grounding check runs over a run's `findings.json`
- **THEN** each finding either has ≥1 evidence reference that resolves in the real source and is
  extractable, or carries `no_direct_evidence` with a `justification`, and any finding that does neither
  is reported as a defect

#### Scenario: A fabricated or unresolvable reference is caught

- **WHEN** a finding cites an evidence `ref` that does not resolve in the run's source, or omits evidence
  without declaring `no_direct_evidence`
- **THEN** the reference-free check reports a defect and the report gate blocks until it is corrected

#### Scenario: The determinism boundary is held

- **WHEN** the check evaluates a finding's evidence
- **THEN** it asserts that the reference resolves and an excerpt can be extracted, and it does not judge or
  rewrite the content of the finding or its evidence

### Requirement: Every output derives, embeds, and validates the evidence excerpt

The dashboard and report generators SHALL, at BUILD time, resolve each finding's evidence `ref`, extract
the excerpt (the cited line-range, document quotation, or diagram element), and EMBED it in the output so
the output is self-contained and needs no access to the repo to show the proof. The dashboard's finding
drawer SHALL show the embedded evidence snippet (monospaced, syntax-lit for code), the findable reference
(`file:line`), and a jump to the related diagram node. A reference-free validator per output SHALL assert
that each finding's evidence is present, resolvable, and that the embedded excerpt matches the cited
source (no fabricated excerpt), and SHALL assert cross-output consistency between the dashboard and the
report. When a finding honestly declares `no_direct_evidence`, the output SHALL show that no-evidence
state and SHALL NOT fabricate a snippet.

#### Scenario: The excerpt is embedded and grounded

- **WHEN** the dashboard or report is generated for a finding whose evidence resolves
- **THEN** the output embeds the extracted excerpt and its findable reference, and the per-output
  validator confirms the embedded excerpt matches the cited source with no fabricated content

#### Scenario: A fabricated or drifted excerpt is caught

- **WHEN** an output embeds an evidence excerpt that does not match the source it cites
- **THEN** the reference-free per-output validator reports a defect

#### Scenario: Honest no-evidence state is shown, not fabricated

- **WHEN** a finding declares `no_direct_evidence` with a justification
- **THEN** the output renders the honest no-evidence state for that finding and shows no fabricated snippet

#### Scenario: Outputs cite the same evidence for the same finding

- **WHEN** both the dashboard and the report are generated for a run
- **THEN** the cross-output consistency check confirms they cite the same evidence reference for the same
  finding id

### Requirement: Evidence is linked into the dashboard data model both directions

The evidence SHALL be wired into the dashboard's linked data model as finding ⇄ evidence-excerpt ⇄
source-location ⇄ diagram-node, computed only from real identifiers in the manifests. Pivoting to a
finding SHALL surface its evidence, and pivoting from a diagram node SHALL surface the findings that
reference it together with their evidence, forming one traceable graph from agent analysis to finding to
evidence to source.

#### Scenario: Pivot from a finding to its evidence

- **WHEN** a user selects a finding in the dashboard
- **THEN** its evidence excerpt, findable reference, and the related source-location and diagram node are
  surfaced

#### Scenario: Pivot from a diagram node to findings and evidence

- **WHEN** a user selects a diagram node
- **THEN** the findings that reference that node are surfaced along with each finding's evidence excerpt
