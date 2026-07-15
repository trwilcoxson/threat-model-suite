## ADDED Requirements

### Requirement: Likelihood may carry a decomposed CVSS exploitability vector
A finding SHALL be able to record a CVSS v3.1 exploitability vector — Attack Vector, Attack Complexity,
Privileges Required, User Interaction — behind its Likelihood score, as an optional `cvss_vector` string of
the canonical form `AV:_/AC:_/PR:_/UI:_` constrained to the legal metric letters. The agent SHALL choose the
metric values from its own attack-path analysis; the field SHALL remain optional so a finding whose
Likelihood was not decomposed may omit it (or set `null`) without failing, and every manifest emitted before
this field existed SHALL still validate.

#### Scenario: Vector emitted behind a Likelihood
- **WHEN** the agent scores a finding's Likelihood and records `cvss_vector: "AV:N/AC:L/PR:N/UI:R"`
- **THEN** the manifest validates and the vector stands as the decomposed, auditable justification for that
  Likelihood

#### Scenario: Vector omitted is honest abstention
- **WHEN** a finding carries no `cvss_vector` (or an explicit `null`)
- **THEN** the manifest still validates (the field is optional and additive) and no CVSS-based check fires for
  that finding

#### Scenario: Illegal metric letter is a structure defect
- **WHEN** a `cvss_vector` uses a letter outside the legal domain (e.g. `AV:X/AC:L/PR:N/UI:N`)
- **THEN** the structure layer records a schema violation naming the field and its pattern, before any
  semantic check runs

### Requirement: Likelihood is consistent with its exploitability vector
When a finding carries a `cvss_vector`, its `likelihood` SHALL equal the 1–5 band derived by recomputing the
CVSS v3.1 exploitability sub-score `8.22 × AV × AC × PR × UI` over the finding's own vector and mapping it
through the published table. The check SHALL recompute the sub-score independently from the agent's own
emitted vector and compare it to the agent's own emitted Likelihood — never against an external CVSS score or
per-target answer key — and SHALL NOT fire when the vector is absent. This is the same recompute-over-emitted-
facts family as the `severity == band(likelihood × impact)` consistency check.

#### Scenario: Consistent vector and band pass
- **WHEN** a finding states `likelihood: 4` and `cvss_vector: "AV:N/AC:L/PR:N/UI:R"` (sub-score 2.835,
  band 4)
- **THEN** the consistency layer records no defect for that finding

#### Scenario: Vector disagrees with the stated Likelihood
- **WHEN** a finding states `likelihood: 2` but its `cvss_vector` recomputes to band 4
- **THEN** the consistency layer records a `cvss-likelihood` defect naming the stated band, the derived band,
  and the vector

#### Scenario: Absent vector does not fire the check
- **WHEN** a finding has a `likelihood` but no `cvss_vector`
- **THEN** the CVSS consistency check is skipped and the finding is judged only by the checks that do not
  depend on the vector (back-compatible with pre-existing runs)

#### Scenario: Recompute uses the agent's own vector, not an answer key
- **WHEN** two findings describe similar threats but the agent assigned them different vectors
- **THEN** each finding's required band is derived from its own vector, so the check constrains internal
  consistency and never asserts which Likelihood is "correct"

### Requirement: The exploitability-to-Likelihood mapping is explicit and auditable
The suite SHALL publish the CVSS v3.1 metric weights, the fixed maximum sub-score normalizer, and the
exploitability-to-1-5 thresholds as one explicit table in the frameworks reference, and the eval SHALL
implement that same table with no second scheme. The weights SHALL be the frozen CVSS v3.1 values; because
CVSS Scope is not adopted, Privileges Required SHALL use the Scope-Unchanged weights, stated as such. Only the
exploitability
sub-score SHALL drive Likelihood — the CVSS impact sub-score SHALL NOT be adopted, and Impact SHALL remain on
the existing PASTA-derived 1–5 axis.

#### Scenario: One table, two implementations agree
- **WHEN** the same vector `AV:N/AC:L/PR:N/UI:N` is banded by the frameworks-reference table and by the eval
- **THEN** both yield band 5 (the maximum sub-score 3.887043 normalizes to fraction 1.0), because both
  implement the identical weights, normalizer, and thresholds

#### Scenario: Thresholds are versioned and tunable
- **WHEN** the exploitability-to-1-5 thresholds are recalibrated against a corpus of scored runs
- **THEN** the change is a single edit to the published table (which the eval reads as its source of truth),
  not a change to the consistency relation or the check's contract

#### Scenario: Scope-Unchanged Privileges-Required weights are pinned
- **WHEN** a vector sets `PR:H`
- **THEN** the sub-score uses the Scope-Unchanged Privileges-Required weight (0.27), matching the documented
  table, because the suite does not adopt the CVSS Scope metric
