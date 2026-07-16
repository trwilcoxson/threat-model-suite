# Tasks

## 1. Define the matrix artifact (skill side)
- [x] 1.1 `references/analytical-visuals.md`: add a new section for the Boundary-Crossing STRIDE-LM
      Interaction Matrix — rows = DFD edges whose endpoints are in different trust zones, keyed
      `Edge (src → dst)` by recon ids; columns `S T R I D E LM`; cells = `TM-NNN` / `n/a` / `clean`;
      no blank cells; a worked example table  *(§1a, next to the per-element matrix)*
- [x] 1.2 State the scope bound in that section: enumerate **only** boundary-crossing edges (tool call /
      network hop / identity handoff); intra-zone edges are excluded; note the anti-combinatorial rationale
- [x] 1.3 State the NOT-APPLICABLE rule: when the DFD has no boundary-crossing edge, emit the heading with
      a one-line "NOT APPLICABLE — single-zone system / no declared boundaries" reason
- [x] 1.4 Give the matrix a distinct heading (`## STRIDE-per-Interaction (Boundary-Crossing) Coverage
      Matrix`) and an `Edge (src → dst)` first-column header so it never collides with the per-element matrix

## 2. Route the producing agent
- [x] 2.1 Add the matrix to the Phase 7 completeness checklist (the analytical-visuals block)
      *(analysis-checklists.md Phase 7 + SKILL.md Phase 7 gate)*
- [x] 2.2 `references/report-template.md`: add the matrix to the Contents alongside the per-element matrix
- [x] 2.3 Phase 7 spawn prompt read list already includes `analytical-visuals.md` (via refine-pipeline-flow);
      confirm the new section is reachable and no extra read is needed  *(reachable; also named in the read-list parenthetical)*

## 3. Deterministic coverage check (eval side, structure-only)
- [x] 3.1 `diagram_checks.py`: add a helper that returns the set of boundary-crossing edges from the emitted
      DFD — an edge crosses iff its two endpoint node ids belong to different `subgraph` zones (a node in no
      subgraph = the implicit untrusted/external zone)  *(`_node_zones` + `_crossing_edges`; innermost zone wins for nesting)*
- [x] 3.2 In `analytical_checks`, gate on `>=1` crossing edge; select the boundary-crossing matrix by its
      first-column header (`Edge`/`Interaction`/`src → dst`), NOT by the shared STRIDE columns  *(`_edge_keyed`; per-element selector tightened to the non-edge-keyed table)*
- [x] 3.3 Check the coverage property: every crossing edge has exactly one row (`missing-crossing-row` /
      `duplicate-crossing-row`); every row has all seven cells non-blank (`crossing-matrix-blanks`)
- [x] 3.4 Check grounding: each placed `TM-NNN` resolves in `findings.json` (`crossing-matrix-ungrounded-finding`,
      a defect); each row's `src`/`dst` resolving in recon ids is a WARNING (brief constraint 4, matches the
      sequence-participant posture), not a gating defect
- [x] 3.5 When no crossing edge exists, skip the check (do not fail); add `boundary-crossing-matrix` to the
      `analytical_present` stats list when present
- [x] 3.6 Confirm the check never asserts a threat exists: a row of all `clean`/`n/a` passes  *(self-check #4)*

## 4. Judge + boundary note
- [x] 4.1 `prompts/diagram-judge.md`: add threat-validity assessment for the enumerated crossings (are the
      STRIDE threats per crossing realistic) — the correctness half the deterministic check does not do
- [x] 4.2 Note in the eval module docstring that this is a coverage property over emitted facts, reference-free

## 5. Verify
- [x] 5.1 `openspec validate add-boundary-crossing-stride-matrix --strict`
- [x] 5.2 Unit: a fixture DFD with 2 subgraphs + 1 cross-zone edge → matrix with 1 row passes; missing row
      or a blank cell → defect; a fully `clean` row → passes; single-zone DFD → check skipped
      *(`test_checks.py::t_boundary_crossing_matrix`, 9 cases incl. nesting + selector-collision)*
- [x] 5.3 Confirm no new fields land in `recon.schema.json` / `findings.schema.json` / `coverage.schema.json`
- [ ] 5.4 Live: a re-run on a multi-zone target emits the boundary-crossing matrix and the eval reports it in
      `analytical_present`  *(deterministic half proven by self-check #1; the agent re-run is the orchestrator's, out of scope for this edit-only pass)*
