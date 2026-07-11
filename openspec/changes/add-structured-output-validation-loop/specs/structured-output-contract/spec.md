## ADDED Requirements

### Requirement: Manifests conform to a load-bearing JSON-Schema contract
Each emitted manifest (`recon.json`, `findings.json`, `coverage.json`) SHALL be validated against its
`schema/*.json` by a dependency-free validator, as the **structure** layer. This is the file-based
analog of strict tool decoding: because an agent writes the manifest as a file, the contract is
enforced **post-hoc** rather than by constrained decoding. The schemas are the authoritative structural
contract — code SHALL apply them, not re-implement a subset.

#### Scenario: Schema violation is caught
- **WHEN** a finding id does not match `^TM-[0-9]{3}$`, `likelihood` is outside 1–5, an enum value is
  out of domain, or an object carries a property not declared in its schema
- **THEN** the structure layer records a `schema-violation` defect naming the field and the constraint

#### Scenario: Conforming manifest passes structurally
- **WHEN** a manifest satisfies every keyword its schema declares
- **THEN** the structure layer adds no defect, and the semantic checks run over the validated structure

### Requirement: Room for absent data, never fabrication
The contract SHALL give every value that the source may legitimately lack an honest "absent" path, so
the agent is never forced to invent a value. Optional may-be-absent fields SHALL accept explicit `null`
as well as omission; genuinely ambiguous values SHALL have an `unknown` enum member (carrying a note);
closed categorizations SHALL provide an `other` member plus a detail field.

#### Scenario: Explicit null on an absent optional field
- **WHEN** the source does not reveal a dependency's `manifest`, an element's `tech`, or a finding's
  `cwe`/`mitre`, and the agent emits `null` (or omits the field)
- **THEN** the validator accepts it (no defect) and the agent has not fabricated a value

#### Scenario: Honest unknown
- **WHEN** a coverage item is `unknown` with a note, or `detected_pattern` is `unknown`
- **THEN** the contract treats it as a valid honest answer, never a failure

#### Scenario: Other without its detail
- **WHEN** `detected_pattern` is `other` but `detected_pattern_detail` is empty
- **THEN** the check records a defect (the conditional requirement the schema cannot express, enforced
  in code)

### Requirement: Single authoritative severity band
A finding's `severity` SHALL equal the OWASP band of `likelihood × impact` under one scheme —
`LOW 1-4 / MEDIUM 5-9 / HIGH 10-16 / CRITICAL 17-25` — used identically by the skill instructions, the
agent definitions, the references/docs, and the eval. No file SHALL document a different band scheme.

#### Scenario: Boundary score is consistent across the system
- **WHEN** a finding scores `likelihood × impact = 18`
- **THEN** the skill documentation and the eval both band it `CRITICAL`, and the consistency check passes

#### Scenario: Severity disagrees with its score
- **WHEN** a finding's `severity` does not equal the band of its `likelihood × impact`
- **THEN** the consistency layer records a `severity-formula` defect with the expected band

### Requirement: Internal consistency and referential integrity over emitted facts
The semantic layer SHALL verify, by recomputing independently (never trusting a self-reported "matches"
flag): `summary_counts` equals the per-severity tally; every `asset_refs`/`surface_refs` id resolves to
a recon id; every `kill_chains[].steps` id resolves to a real finding; `likelihood`/`impact` are within
1–5; recon `evidence` resolves in the target.

#### Scenario: Dangling kill-chain step
- **WHEN** a declared kill chain lists a step id that is not a finding in `findings.json`
- **THEN** the check records a `killchain-dangling-step` defect

#### Scenario: Counts disagree with findings
- **WHEN** `summary_counts.HIGH` is 5 but four HIGH findings are present
- **THEN** the check records a `count-mismatch` defect

### Requirement: Agent-judged layers fail loud, not silent
A malformed or incomplete agent-judged output (quality, recall, recon-audit) SHALL be recorded as an
integrity defect and SHALL prevent a clean "reliable" verdict. It SHALL NOT silently degrade to the
same "not recorded" state as a layer that was never run.

#### Scenario: Malformed judge output
- **WHEN** a judge output file is present but is not valid JSON, or is missing a required key
- **THEN** the harness records a judge-integrity issue, surfaces it in the report, and the verdict
  cannot be green over it

#### Scenario: Judge layer simply absent
- **WHEN** a judge output file is not present at all (a deterministic-only run)
- **THEN** no integrity defect is raised (absence is a legitimate run mode, distinct from malformed)
