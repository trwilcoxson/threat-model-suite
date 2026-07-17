## ADDED Requirements

### Requirement: A run requires an explicit user-confirmed run plan before it starts
The skill SHALL, before spawning any pipeline agent, obtain an explicit run plan covering the mode, the
team composition, and the output types. When the invocation does not specify a plan, the skill SHALL
present the options and STOP for the user's choice; it SHALL NOT start the pipeline with an inferred
default.

#### Scenario: Unspecified invocation halts for a choice
- **WHEN** a user invokes the skill without specifying mode, team, and outputs
- **THEN** the skill presents the mode/team/output menu and stops, and no pipeline agent is spawned
  until the user picks

#### Scenario: One-shot specification is parsed and confirmed
- **WHEN** a user invokes the skill with a full specification (for example team and outputs stated in
  one message)
- **THEN** the skill resolves it into a run plan, echoes the resolved plan, and proceeds without asking
  again

### Requirement: The run plan is recorded as an emitted fact
The skill SHALL record the confirmed choice as a `run-plan.json` file at the start of the run,
containing the mode, the selected team members, the selected outputs, and a confirmation flag. The file
SHALL validate against the run-plan schema.

#### Scenario: Run plan written before Phase 1
- **WHEN** the user has confirmed a plan
- **THEN** `run-plan.json` is written to the output directory with `mode`, `team`, `outputs`, and
  `confirmed: true`, and it conforms to the run-plan schema

### Requirement: No pipeline run starts without a valid confirmed run plan
A deterministic start gate SHALL deny the first pipeline agent spawn unless a schema-valid
`run-plan.json` with `confirmed: true` exists in the output directory. The denial SHALL carry the
selection menu so the user can choose.

#### Scenario: First spawn denied without a plan
- **WHEN** the first pipeline agent spawn is attempted and no valid confirmed `run-plan.json` exists
- **THEN** the start gate denies the spawn and returns the selection menu as the reason

#### Scenario: Spawn allowed with a plan
- **WHEN** a schema-valid `run-plan.json` with `confirmed: true` exists
- **THEN** the start gate allows the first pipeline agent spawn

### Requirement: The run produces exactly the planned team and outputs
The run SHALL produce exactly the specialists and outputs named in the run plan — no un-planned
specialist output and no un-planned output file, and no planned artifact missing. A reference-free
check SHALL verify this by comparing produced artifacts to the plan.

#### Scenario: Matching run passes the determinism check
- **WHEN** the run-plan check runs and every planned specialist output and planned output file is
  present and no un-planned one is present
- **THEN** the check passes

#### Scenario: Extra or missing artifact fails the determinism check
- **WHEN** the run produced a specialist output or output file not named in the plan, or omitted one
  that was named
- **THEN** the run-plan check reports a defect

### Requirement: Selection is additive and backward compatible
The selection capability SHALL preserve the existing Solo and Team behaviours as named presets over the
run plan, and SHALL NOT change any existing manifest, schema, or agent contract. Runs that predate the
run plan SHALL remain valid.

#### Scenario: Solo and Team remain available as presets
- **WHEN** a user selects Solo, or Team with all specialists and all outputs
- **THEN** the run behaves as the corresponding pre-existing mode

#### Scenario: Legacy runs unaffected
- **WHEN** the reliability harness runs against a run that has no `run-plan.json`
- **THEN** the run-plan check is skipped and the other checks are unaffected
