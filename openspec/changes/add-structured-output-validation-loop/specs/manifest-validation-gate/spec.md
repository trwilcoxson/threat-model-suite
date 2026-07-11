## ADDED Requirements

### Requirement: Proactive self-check before emitting
Before writing the manifests, the analysis agent SHALL self-verify the same invariants the gate
enforces — `severity == band(likelihood × impact)`, `summary_counts` equals the tally, refs resolve,
every surface is covered or marked `no_issue_surface`, kill-chain steps reference real findings — so the
check is built into the work, not left for the gate to catch.

#### Scenario: Agent reconciles before emit
- **WHEN** the agent finalizes `findings.json`
- **THEN** it recomputes each severity from the authoritative band and reconciles `summary_counts`
  before the file is written

### Requirement: In-flow validation before report generation
The orchestrator SHALL run the deterministic validator (`run.py validate`) over the manifests after the
analysis agent has written them and before the report-analyst is spawned. This is where "the application
validates" in a Claude Code flow: the deterministic Python is the application code, run via Bash, with no
model in the validation path.

#### Scenario: Manifests fail the contract
- **WHEN** `run.py validate` reports one or more structure/consistency/coverage defects
- **THEN** report generation does not proceed until they are resolved

#### Scenario: Manifests pass
- **WHEN** the validator exits zero
- **THEN** the flow proceeds to report generation

### Requirement: Retry with specific feedback
On gate failure the orchestrator SHALL re-spawn the analysis agent with the specific defects — each
naming the field, the constraint, and the actual-vs-expected value — not a generic "validation failed".

#### Scenario: Specific defect fed back
- **WHEN** a finding has `severity HIGH` but `band(L3 × I2) = MEDIUM`
- **THEN** the re-spawn prompt carries that exact line so the agent can fix the score or the band

### Requirement: Missing source information is not retryable
A defect that reflects information genuinely absent from the source SHALL be routed — recorded as
`null`/`no_issue_surface`/coverage `unknown`/an Open Question — not retried. The agent SHALL NOT
fabricate a value to satisfy the gate.

#### Scenario: Surface with no issue
- **WHEN** a discovered surface element genuinely carries no finding
- **THEN** it is listed in `no_issue_surface` (examined-and-clean), not retried into a fabricated finding

### Requirement: Hard enforcement when installed as a plugin
When the suite is installed as a Claude Code plugin, a `PreToolUse` hook SHALL deterministically deny
the report-analyst spawn until the manifests pass, feeding the defects back as the denial reason. The
hook SHALL act only on the report-generation spawn (no-op for every other tool call) and SHALL fail open
on infrastructure errors (validator missing, unparsable event, timeout) so it never blocks for a reason
unrelated to the manifest contract. Absent the plugin, the orchestrator enforces the identical check.

#### Scenario: Report spawn blocked on failing manifests
- **WHEN** the parent attempts to spawn the report-analyst while the manifests have a contract defect
- **THEN** the hook denies the spawn and returns the specific defects as the reason

#### Scenario: Infrastructure problem does not block
- **WHEN** the validator cannot be located or the hook event cannot be parsed
- **THEN** the hook allows the spawn (fail open), leaving the orchestrator's soft gate as the backstop
