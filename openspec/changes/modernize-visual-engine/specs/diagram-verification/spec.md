## ADDED Requirements

### Requirement: A per-engine extractor feeds shared reference-free assertions
The diagram eval SHALL separate engine-specific extraction — parsing source into a normalized model of
blocks, edges with labels, boundary containers, node type tokens, and stamps — from the engine-agnostic
property assertions. Adding an engine SHALL add only a new extractor; the property assertions (required
layers, typed and annotated edges, trust-boundary containers, ownership markers, the L4-to-`TM-NNN`
linkage, and the analytical visuals) SHALL run identically over the normalized model regardless of
engine, so no property check changes meaning. The engine SHALL be detected from the declared fence or
file extension, never guessed from content.

#### Scenario: Same assertion, two engines
- **WHEN** the same threat model is authored once in Mermaid and once in D2
- **THEN** both extract to the normalized model and the identical property assertions run over it, so
  every property check keeps its meaning across engines

#### Scenario: Engine chosen from the declared fence
- **WHEN** a diagram block is parsed
- **THEN** the extractor is selected by the declared ` ```d2 ` or ` ```mermaid ` fence (a declared
  fact), not by sniffing the syntax inside the block

### Requirement: Node-type vocabulary compliance is a grounding check
The eval SHALL verify that every drawn node carries a type token, that every type token is a member of
the controlled vocabulary, that the same type token maps to the same icon or class across all diagrams
in the report, and that the legend covers every type token used. It SHALL count typed-versus-untyped
nodes and vocabulary membership only — it SHALL NOT assert which type a node ought to be. An explicit
`unknown`/`other` type SHALL count as typed and pass. More than 10% untyped nodes SHALL be a defect; at
or below 10% it SHALL be a warning.

#### Scenario: Untyped nodes flagged by ratio
- **WHEN** more than 10% of the nodes in a diagram carry no type token
- **THEN** a defect is recorded; at or below 10% untyped, a warning is recorded instead

#### Scenario: Membership, not choice
- **WHEN** a node is typed `datastore`
- **THEN** the check passes because `datastore` is in the vocabulary, and it does not assert the node
  should have been any other type

#### Scenario: Unknown type passes
- **WHEN** a node is typed `unknown`/`other`
- **THEN** it counts as typed and does not fail the compliance check

#### Scenario: Consistent icon per type
- **WHEN** two diagrams in the report both contain `service` nodes
- **THEN** both map `service` to the same vendored icon, otherwise an icon-inconsistency defect is
  recorded

### Requirement: Edge endpoints resolve to declared nodes
The eval SHALL verify that every edge endpoint resolves to a node the source declares, so a mistyped
edge target that an engine would silently auto-create as a phantom node is caught. Duplicate node ids
SHALL be flagged. This check SHALL be engine-agnostic and reference-free — it resolves ids within the
source only, never against an external list.

#### Scenario: Phantom node caught
- **WHEN** an edge names a target id that is not a declared node
- **THEN** a dangling-endpoint defect is recorded rather than a phantom node being silently accepted

#### Scenario: Duplicate id flagged
- **WHEN** two nodes are declared with the same id
- **THEN** a duplicate-id defect is recorded

### Requirement: Verification stays reference-free across engines
Every assertion the generalized eval makes SHALL be a property, grounding, consistency, or coverage
check over the model's own emitted source — well-formedness, id resolution within the source,
vocabulary membership, or arithmetic recomputation of a value the model stated — and SHALL NOT compare a
diagram to a golden or reference diagram. Honest abstention — `unknown`/`other` types, `n/a`/`clean`
cells, and checks skipped because a precondition is false — SHALL remain a passing outcome on every
check.

#### Scenario: No golden comparison
- **WHEN** a diagram is verified on either engine
- **THEN** the verdict depends only on its own well-formedness, its own ids resolving, vocabulary
  membership, and recomputed values, never on matching an expected diagram

#### Scenario: Abstention passes
- **WHEN** a precondition is false or a node is honestly typed `unknown`/`other`
- **THEN** the relevant check is skipped or passes, and the run is not failed for the abstention
