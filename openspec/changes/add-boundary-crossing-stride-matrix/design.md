## Context

This change lands two research recommendations that converged on the same artifact: **T2-04**
(bounded STRIDE-per-interaction over crossing edges) and **T3-02** (boundary-scoped per-edge coverage
matrix). Both rank it high-adoptability / low-risk for one reason: it needs no new inputs. The DFD
already draws trust-boundary subgraph zones and typed edges; `recon.json` already declares
`trust_boundaries[]`; the coverage-property machinery already exists in `coverage_checks.py` and in
`diagram_checks.analytical_checks` (the per-element STRIDE matrix). The only missing pieces are the
artifact itself and one check that holds the model to covering the crossings.

The engine decision is settled and does not touch this change: the matrix is a **markdown table**, not
a rendered graph, so it is engine-agnostic (it renders identically whether the DFD is Mermaid or D2).

## The determinism boundary

The new check is a **coverage property over the model's own emitted facts**, in the same class as the
existing per-element matrix check and the `coverage.json` ledger. It preserves the boundary by
construction:

- **The crossing set is derived, not inferred.** "Edge E crosses a boundary" is computed from *the DFD
  the agent drew* — which node ids the agent placed in which `subgraph` zone — and is true iff E's two
  endpoints belong to different zones. This is the same category of structural read the existing checks
  already perform (`diagram_checks._edges`, the `subgraph` count in requirement 3). The check never
  decides *where a boundary should be* or *whether a placement is right* — it reads the zones the agent
  declared and asks only: for the crossings **you** drew, is there a decided row? A wrong zone placement
  is a content error the diagram judge catches, not a deterministic failure.
- **It checks coverage + grounding, never correctness.** Pass condition: every crossing edge has exactly
  one row; every row resolves all seven STRIDE-LM cells to a terminal state (`TM-NNN` / `n/a` / `clean`,
  no blanks); every `TM-NNN` resolves to a real id in `findings.json`; every row's `source`/`dest`
  resolve to real recon ids. It never asserts a particular threat exists or is valid.
- **Honest abstention is first-class.** A cell may be `clean` (examined, no finding) or `n/a` (category
  inapplicable to that interaction type) — a fully clean row passes. When the DFD has **no** crossing
  edge, the matrix is marked NOT APPLICABLE with a one-line reason and the check is *skipped, not
  failed* (the gate is a declared fact, exactly like the RBAC-matrix `roles[]` gate and the SBOM
  `manifest` gate).
- **Coverage is over the model's own recon, never an answer key.** The denominator is "crossing edges in
  the DFD you emitted," not an external expected set. There is no golden matrix to compare against.

Whether the STRIDE threats enumerated for a crossing are the *right* threats is left entirely to
`prompts/diagram-judge.md`, matching how the per-element matrix already splits structure (deterministic)
from validity (judge).

## Decisions

1. **Bound to crossings, not all edges.** Full STRIDE-per-interaction (every edge × 7 categories)
   explodes combinatorially and a replicated controlled experiment (arXiv 2208.01524) found no
   significant accuracy gain over per-element — the reason Microsoft de-emphasized it. Scoping to
   boundary crossings keeps the matrix to the handful of tool-call / network-hop / identity-handoff
   edges where agentic and cloud threats actually concentrate (the robotics-paper discipline, arXiv
   2604.27267). The bound is also what makes the coverage property cheap and stable.

2. **Derive the crossing set from subgraph membership, not a new field.** Two candidate derivations were
   considered: (a) tag each edge in recon with a boolean `crosses_boundary`; (b) compute crossings from
   which subgraph each endpoint sits in, in the emitted DFD. (a) adds a manifest field the brief
   explicitly forbids and duplicates information the DFD already encodes; (b) reads a fact the agent
   already declared. Chose (b). An endpoint outside every subgraph is treated as the implicit
   *untrusted/external* zone, so an external-entity → internal-process edge counts as a crossing (the
   classic outer-boundary crossing), not just inter-subgraph edges. `recon.trust_boundaries[]` still
   supplies the existence gate and grounding target; the *relative* zone membership drives enumeration.

3. **One new capability, producer + verifier in one spec.** The change is one bounded visual and its one
   check. Rather than proliferate capability dirs, `boundary-crossing-matrix` holds both the producer
   requirement (the skill emits the matrix) and the verifier requirement (the eval checks it,
   structure-only) — the determinism split is expressed as separate requirements, not separate
   capabilities. This mirrors the producer/verifier separation add-product-grade-diagrams used for the
   eight visuals, at the scale this one addition warrants.

4. **Disambiguate from the per-element matrix.** Both matrices share the `S T R I D E LM` column header,
   so the eval's table selector must not grab the wrong one. The boundary-crossing matrix is
   distinguished by (i) a distinct section heading (`## STRIDE-per-Interaction (Boundary-Crossing)
   Coverage Matrix`) and (ii) an edge-keyed first column (`Edge (src → dst)`) versus the per-element
   matrix's `Element` first column. The selector keys on the first-column header; a `Type:` stamp is
   unnecessary because the table is markdown, not a fenced diagram block (open question 1 confirms).

5. **Place it in Phase 7.** Its precondition (a drawn DFD with typed edges + trust zones) holds from
   Phase 2, but it lives with the other analytical visuals in the risk-overlay phase so the cells can
   reference scored findings. This composes with refine-pipeline-flow, which moves the analytical-visuals
   block into Phase 7 and routes the producing agent to `analytical-visuals.md` and the Phase 7
   checklist.

## Risks / trade-offs

- **Crossing-detection depends on the DFD drawing subgraphs faithfully.** If the agent omits a
  subgraph, an edge that should cross reads as intra-zone and no row is required. This is bounded by the
  existing diagram checks (requirement 3 already flags missing trust-boundary subgraphs / `few-trust-
  boundaries`), so a DFD thin on zones fails there first. The judge covers residual placement errors.
- **Two S…LM matrices in one report.** Mitigated by decision 4 (distinct heading + first-column key);
  the risk is a selector collision, addressed in tasks by asserting the selector matches on the
  first-column header, not the STRIDE columns alone.
- **Deferred:** the CCT/AdvT/ConT per-crossing overlay (ATT&CK / ATLAS / OWASP-LLM keyed to each
  crossing, T3-10) is a natural follow-on but needs the AI-technique namespaces resolved first; out of
  scope here. This change ships only the STRIDE-LM coverage view.
