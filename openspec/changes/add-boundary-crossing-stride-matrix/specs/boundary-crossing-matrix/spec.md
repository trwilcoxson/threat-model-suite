## ADDED Requirements

### Requirement: Boundary-crossing STRIDE-LM interaction matrix
The skill SHALL produce, as an analytical visual, a STRIDE-LM coverage matrix whose rows are the DFD
edges that cross a trust boundary — the interaction-level complement to the per-element matrix. Rows
SHALL be keyed by the crossing edge's `source → destination` recon ids; columns SHALL be the seven
STRIDE-LM categories in order (`S T R I D E LM`); each cell SHALL hold a finding id (`TM-NNN`), `n/a`
(category inapplicable to that interaction), or `clean` (examined, no finding). There SHALL be no blank
cells.

#### Scenario: Each crossing edge gets a row
- **WHEN** the emitted DFD contains an edge whose source and destination sit in different trust zones
- **THEN** the boundary-crossing matrix contains exactly one row for that edge, keyed by its `source →
  destination` recon ids

#### Scenario: Every cell resolved
- **WHEN** the boundary-crossing matrix is produced
- **THEN** each of the seven STRIDE-LM cells in every row holds a `TM-NNN`, `n/a`, or `clean`, and no
  cell is blank

### Requirement: Scope bounded to boundary crossings
The matrix SHALL enumerate only the edges whose endpoints lie in different trust zones (the tool-call,
network-hop, and identity-handoff interactions); intra-zone edges SHALL NOT appear. The skill SHALL NOT
produce a full per-interaction matrix over every DFD edge, so the artifact stays bounded rather than
combinatorial.

#### Scenario: Intra-zone edge excluded
- **WHEN** a DFD edge connects two nodes that sit within the same trust zone
- **THEN** that edge SHALL NOT appear as a row in the boundary-crossing matrix

### Requirement: Derived from emitted facts with no new manifest fields
The matrix SHALL derive entirely from facts the run already emits — the DFD edges and their trust-zone
membership, plus the presence of `recon.trust_boundaries` — and this change SHALL add no new field to
`recon.schema.json`, `findings.schema.json`, or `coverage.schema.json`. Each row's `source` and
`destination` SHALL resolve to real recon element ids, and each `TM-NNN` placed in a cell SHALL resolve
to a real finding id in `findings.json`.

#### Scenario: Placed finding id grounds
- **WHEN** a cell holds a finding id `TM-NNN`
- **THEN** `TM-NNN` resolves to a finding in `findings.json` (edge and threat-category correctness are
  left to the judge, exactly as the per-element matrix does — the deterministic check grounds the id only)

#### Scenario: Row endpoints ground
- **WHEN** a row is keyed `source → destination`
- **THEN** both ids resolve to declared recon element ids, and no matrix row references an id absent
  from recon

### Requirement: Deterministic coverage property, structure-only and reference-free
The eval SHALL deterministically verify only that every boundary-crossing edge in the emitted DFD has
exactly one matrix row, that every row resolves all seven STRIDE-LM cells to a terminal state, and that
every placed id grounds in recon / findings. The check SHALL NOT judge whether the enumerated threats
are correct, SHALL NOT require any specific threat to exist, and SHALL pass a row whose cells are all
`clean` or `n/a`. Threat validity SHALL be left to the diagram judge.

#### Scenario: Present but analytically wrong still passes
- **WHEN** the boundary-crossing matrix covers every crossing edge with all cells resolved and all ids
  grounded, but a listed threat is analytically wrong
- **THEN** the deterministic check passes and the error is reported only by the diagram judge

#### Scenario: Missing or blank row is a defect
- **WHEN** a boundary-crossing edge in the emitted DFD has no matrix row, or a row leaves a STRIDE-LM
  cell blank
- **THEN** the deterministic check reports a defect

#### Scenario: Fully clean row is honest coverage
- **WHEN** a crossing edge was examined and no threat was found in any category
- **THEN** its row of `clean` / `n/a` cells passes the check without any finding being required

### Requirement: Honest abstention when no crossing exists
The skill SHALL mark the boundary-crossing matrix NOT APPLICABLE with a one-line reason when the emitted
DFD contains no boundary-crossing edge (a single-zone system, or no declared trust boundaries), and the
eval SHALL skip the coverage check rather than fail it in that case.

#### Scenario: Single-zone system
- **WHEN** every DFD edge connects nodes within one trust zone, or the DFD declares no trust-zone
  subgraphs
- **THEN** the matrix is marked NOT APPLICABLE with a one-line reason, and the boundary-crossing check
  is skipped, not counted as a defect
