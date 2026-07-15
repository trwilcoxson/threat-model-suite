## Why

The suite's STRIDE-LM analysis is **element-centric**: `analytical-visuals.md §1` produces one row per
DFD *element* (external entity / process / data store / data flow) and proves every element was
considered against every STRIDE-LM category. That view has a documented structural blind spot — the
threats that live at the *interaction*, not the element: the tool call, the network hop, the identity
handoff where one component hands data or authority to another across a trust zone. STRIDE-per-element
under-finds exactly there, which is why Shostack / Microsoft SDL pair the per-element matrix with a
per-interaction one.

The suite already carries everything needed to close that gap and produces nothing from it:

- The DFD already draws **trust-boundary subgraph zones** (`diagram_checks.py` requirement 3) and
  **typed, sensitivity-tagged edges** (`mermaid-diagrams.md`: protocol / `[PUBLIC…RESTRICTED]` /
  `[ENC|PLAIN]`). Which edges cross a zone is therefore already an emitted structural fact.
- `recon.json` already declares `trust_boundaries[]` (with a `kind`: network / trust / tenant / cicd /
  region). No new manifest field is needed to know a boundary exists.
- `coverage_checks.py` already establishes the reference-free coverage-property pattern (every
  applicable item reaches a terminal state; grounded sources; honest `unknown`). The per-element matrix
  in `diagram_checks.analytical_checks` already enforces "no blank cells, every placed `TM-NNN`
  resolves to a finding."

So the gap is not inputs — it is that no artifact enumerates the boundary crossings, and no check holds
the model to covering them. Full STRIDE-per-*interaction* (every edge) is the wrong fix: it explodes
combinatorially with no measured accuracy gain (arXiv 2208.01524), which is why Microsoft de-emphasized
it. The cheap, boundary-clean win is to enumerate STRIDE-LM over **only the edges that cross a trust
boundary** — the documented complement to the per-element matrix, checked by one coverage property.

## What Changes

- **Add a second analytical visual — the Boundary-Crossing STRIDE-LM Interaction Matrix.** Rows = the
  DFD edges whose two endpoints sit in different trust zones (each keyed by its `source → destination`
  recon ids); columns = the seven STRIDE-LM categories; cells = a finding id (`TM-NNN`), `n/a`, or
  `clean`. No blank cells. It is the interaction-level dual of the per-element matrix.
- **Bound it to crossings only.** Intra-zone edges never appear. The producing agent enumerates exactly
  the tool-call / network-hop / identity-handoff edges, so the matrix stays small and signal-dense
  instead of combinatorial.
- **Derive everything from facts already emitted — no new manifest fields.** The crossing set comes from
  the DFD the agent drew (which nodes it placed in which subgraph) plus the presence of
  `recon.trust_boundaries`; the cells reference existing `findings.json` ids. `recon.schema.json`,
  `findings.schema.json`, and `coverage.schema.json` are untouched.
- **Add one deterministic coverage-property check** (in `diagram_checks.py`, alongside the per-element
  matrix check): every boundary-crossing edge in the emitted DFD has exactly one matrix row, every row
  resolves all seven cells to a terminal state, and every placed id grounds in recon / findings. It
  checks *coverage and grounding only* — never whether a listed threat is correct, and a fully
  `clean` / `n/a` row passes (honest abstention).
- **Gate it on a declared fact.** The matrix is required only when the emitted DFD contains at least one
  boundary-crossing edge; a single-zone system (or no declared boundaries) marks it NOT APPLICABLE with
  a one-line reason and the check is skipped, not failed.
- **Route the producing agent to the format.** The matrix belongs to the risk-overlay phase (Phase 7)
  that already owns the analytical visuals; its section is added to `analytical-visuals.md` and the
  Phase 7 completeness checklist so the agent is actually pointed at it.

## Capabilities

### New Capabilities
- `boundary-crossing-matrix`: the interaction-level STRIDE-LM coverage matrix the skill produces over
  trust-boundary-crossing DFD edges — its scope bound, its grounding, and the reference-free coverage
  property the eval enforces over it (structure only; threat validity stays with the diagram judge).

### Modified Capabilities
<!-- Composes with `threat-model-visuals` + `diagram-verification` (add-product-grade-diagrams), which
     introduce the per-element STRIDE matrix, the trust-boundary subgraphs, and the analytical_checks
     harness this extends; no requirement of those changes. Phase-7 placement composes with
     refine-pipeline-flow (analytical visuals moved to Phase 7). No changes to those requirements. -->

## Impact

- Skill: `skills/threat-model/references/analytical-visuals.md` (new §: the boundary-crossing matrix,
  format + preconditions + NOT-APPLICABLE rule), `skills/threat-model/references/report-template.md`
  (the matrix's place in the Contents), the Phase 7 completeness checklist, and the Phase 7 spawn
  prompt's read list.
- Eval: `skills/threat-model/evals/reliability/diagram_checks.py` (one new coverage-property check in
  `analytical_checks`; a helper that derives cross-zone edges from subgraph membership), and
  `prompts/diagram-judge.md` (threat validity of the enumerated crossings).
- No new manifest fields; `recon.schema.json`, `findings.schema.json`, `coverage.schema.json` unchanged.
- No change to the existing per-element matrix, the heat map, or any other visual.
