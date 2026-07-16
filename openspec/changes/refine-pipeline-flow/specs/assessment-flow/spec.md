## ADDED Requirements

### Requirement: Skeptical validation runs in a fresh context
The false-positive validation phase (Phase 6) and the summary (Phase 8) SHALL run in a context separate
from the one that generated the findings (Phases 3–5), reading the prior phases from disk. The
generative phases SHALL NOT also perform their own skeptical self-validation as the authoritative pass.

#### Scenario: Fresh-context validation
- **WHEN** the analysis phases (identify, score, false-negative hunt) have written 03/04/05
- **THEN** a new agent instance is spawned to perform Phase 6 (false-positive validation) and Phase 8
  (summary), reading 01/03/04/05, so its skepticism does not inherit the generator's anchoring

### Requirement: Specialists start at their true dependency frontier
The parallel specialist agents (privacy, compliance, code review) SHALL be spawnable once the structural
diagram (Phase 2) exists, and SHALL run concurrently with the later analysis phases rather than waiting
for Phase 7. Their inputs SHALL include the reconnaissance and the structural diagram, and SHALL NOT
include the architect's validated findings (independent rediscovery is the point).

#### Scenario: Early parallel specialists
- **WHEN** Phase 2 has produced the structural diagram
- **THEN** the parent may spawn the 3 specialists in the background, and they run while the analysis
  phases and Phase 7 proceed

#### Scenario: Node-id contract satisfiable
- **WHEN** a specialist writes a finding whose affected component must match a Phase 2 diagram node id
- **THEN** the structural diagram is among its inputs, so it can name the canonical id the validator checks

### Requirement: The coverage ledger has a single writer
Each agent SHALL record the coverage states for items in its domain within its own output, and exactly
one agent (the validation-specialist) SHALL merge those into the single `coverage.json`. No set of
parallel agents writes the same `coverage.json` concurrently.

#### Scenario: Ledger seeded and recorded
- **WHEN** reconnaissance runs
- **THEN** it seeds the ledger context, and each subsequent agent records its domain's item states in its
  own output file; the validation step merges them into `coverage.json`

#### Scenario: Report consumes the ledger
- **WHEN** the report-analyst assembles the report's Coverage Profile / Open Questions / Known
  Limitations
- **THEN** `coverage.json` is named among its inputs and the post-assessment verification checks it exists

### Requirement: Analytical visuals are produced when their inputs exist
The skill SHALL assign the analytical and communication visuals (STRIDE-per-element matrix, L×I heat
map, MITRE ATT&CK layer, RBAC matrix, SBOM graph) to the phase where their preconditions hold (the risk
overlay, Phase 7), not to the pre-risk structural phase, and SHALL route the producing agent to the
formats reference and the corresponding completeness checklist.

#### Scenario: Heat map produced after scoring
- **WHEN** findings have been scored (Phases 4–5) and Phase 7 runs
- **THEN** the risk-overlay phase produces the applicable analytical visuals, and its spawn prompt
  includes `analytical-visuals.md` and the Phase 7 completeness checklist in its read list

### Requirement: Completeness checklists align with their phases
Each phase's instruction to consult a completeness checklist SHALL point at the checklist for that same
phase, and the Phase 8 checklist SHALL describe the summary-only Phase 8 output (not the pre-split full
report).

#### Scenario: Correct checklist pointer
- **WHEN** Phase 6 (false-positive validation) consults a completeness checklist
- **THEN** it is directed to the Phase 6 checklist (which includes the framework-id verification step),
  not the Phase 5 checklist

### Requirement: Solo mode is reachable for proportionate requests
The Solo/Team decision SHALL allow a genuinely small, low-sensitivity system to be assessed in Solo mode
on a plain request; an explicitly narrow ask SHALL be an independent sufficient trigger for Solo, not a
condition that must combine with all others.

#### Scenario: Small clean system, plain request
- **WHEN** the system is small, processes no sensitive data, has no cloud/IaC and no compliance need
- **THEN** Solo mode is selected even though the user did not phrase the request narrowly
