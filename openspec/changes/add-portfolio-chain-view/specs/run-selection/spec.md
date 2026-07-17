## ADDED Requirements

### Requirement: A run may opt in to a portfolio chain at selection time
The Step 0 run-selection SHALL present an opt-in choice to add the run to a portfolio/chain, defaulting to
standalone. The skill SHALL NOT infer chain membership; a run SHALL be chained only when the user explicitly
supplies a portfolio id and this run's id in the chain, either in a one-shot specification or as a pick in
the selection surface. When the user does not choose chaining, the run SHALL be standalone.

#### Scenario: Default is standalone
- **WHEN** a user selects a run plan without any chaining choice
- **THEN** the run is standalone, no portfolio is touched, and `run-plan.json` records no chain

#### Scenario: Explicit chaining is recorded
- **WHEN** a user specifies a portfolio id and a run id for the chain
- **THEN** the confirmed `run-plan.json` records a `chain` block with the portfolio id, the run id, and the
  portfolio locator, and the run is organised into that portfolio

### Requirement: The chain choice rides the existing run-plan fact and start gate
The chain choice SHALL be recorded as an additive optional `chain` block on the existing `run-plan.json`
fact, and SHALL be validated by the existing run-plan start gate rather than introducing a new gate or a
second stop. When present, the `chain` block SHALL carry the portfolio id, the run id, and the portfolio
locator. An absent `chain` block SHALL mean standalone and SHALL keep pre-existing run plans valid.

#### Scenario: Chained plan validates and starts
- **WHEN** a confirmed `run-plan.json` carries a well-formed `chain` block
- **THEN** the start gate treats the plan as valid and allows the pipeline to start, using the same gate
  that already forbids an unplanned run

#### Scenario: Legacy plans remain valid
- **WHEN** a `run-plan.json` written before chaining and having no `chain` block is validated
- **THEN** it validates unchanged and is treated as a standalone run

### Requirement: Joining a portfolio never fabricates a relationship
Recording chain membership SHALL upsert only the run's membership entry, keyed by its chain run id, and
SHALL NOT create any declared relationship between products. Cross-product relationships SHALL require a
separate explicit assertion with real element ids and provenance.

#### Scenario: Membership upsert adds no edges
- **WHEN** a run joins a portfolio
- **THEN** the portfolio's `members` gains or updates exactly that run's entry and its `relationships` are
  unchanged, so no cross-product link is created by joining
