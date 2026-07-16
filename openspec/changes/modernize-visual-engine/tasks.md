# Tasks

## 1. Per-engine extractor seam (do this FIRST — it must land before any diagram converts)
- [x] 1.1 Refactor `diagram_checks.py`: split engine-specific extraction (`_blocks`, `_layer_of`, `_edges`, `_nodes`, `_typed`) from the property assertions in `check()` / `analytical_checks()`, introducing a normalized diagram model (blocks, edges+labels, boundary containers, node type tokens, stamps)
- [x] 1.2 Route extraction by declared engine from the fence/extension (` ```d2 ` vs ` ```mermaid `); keep the Mermaid extractor behavior byte-identical so the Mermaid path stays zero-change
- [x] 1.3 Add the D2 extractor: edges `a -> b: "label"`, containers = trust boundaries, `class`/`classes` = node type, `#`-comment / `%% Version:`-style stamp; map D2 primitives onto the same normalized model
- [x] 1.4 Cross-engine parity test: author one sample threat model in both Mermaid and D2; assert the property assertions produce the same verdict shape (`test_checks.py`)

## 2. Node-type→icon vocabulary (the grounding-check substrate)
- [x] 2.1 Author `references/node-type-icons.md`: the versioned closed vocabulary (service / datastore / queue / external-actor / secret / boundary + cloud-provider logos) with an explicit `unknown`/`other` member, each mapped to a vendored local SVG path
- [ ] 2.2 Vendor the chosen icon set locally as SVGs; record the license; reference icons by local file path only (never remote URLs) — *catalog JSON + license recorded; actual SVG asset files NOT yet vendored (needs real asset fetch, see node-type-icons.md §5)*
- [x] 2.3 Re-express `mermaid-spec.md` §3 symbol taxonomy as the same controlled node-type vocabulary (shape+`classDef` ⇄ vocabulary type) so the Mermaid and D2 paths share one type set

## 3. Node-type vocabulary compliance check (T4-01)
- [x] 3.1 Add `node-type-present`: every drawn node carries a type token; `>10%` untyped → defect, else warning (mirror the `untyped-edges` ratio)  *(code `node-type-untyped`)*
- [x] 3.2 Add `node-type-in-vocab`: every type token ∈ the controlled vocabulary; `unknown`/`other` is a passing member  *(code `node-type-unknown-token`, with fuzzy suggestions)*
- [x] 3.3 Add `icon-consistency`: the same type token → the same icon/class across all diagrams in the report  *(code `icon-inconsistency`)*
- [x] 3.4 Add `legend-covers-types`: every type token used appears in the legend  *(warning-level)*
- [x] 3.5 Confirm none of 3.1-3.4 assert *which* type a node is; add an abstention test (a node typed `unknown` passes)

## 4. Edge-endpoint integrity check (T1-06)
- [ ] 4.1 Add a dangling-endpoint check: every edge endpoint resolves to a node the source declares (catch the phantom node a typo'd D2 target auto-creates) — *deferred (out of this pass's scope; extractor primitives are in place to add it)*
- [ ] 4.2 Add a duplicate-node-id check; both are engine-agnostic and resolve ids within the source only — *deferred*

## 5. D2 engine adoption (authoring + rendering)
- [x] 5.1 Author `references/d2-spec.md` mirroring `mermaid-spec.md`: symbol/icon taxonomy, typed edges, container = trust boundary, risk `classes`, the version/layer/type stamp convention
- [ ] 5.2 Update SKILL.md Phase 2 to author the structural DFD as `.d2` (agent writes source; renderer + layout add nothing), keeping the Phase 2 acceptance gate assertions unchanged — *SKILL.md wiring deferred to the pipeline-integration workstream*
- [ ] 5.3 Update SKILL.md Phase 7 to author the L4 overlay + SBOM/dependency diagram as `.d2`; keep threat annotations (`⚠ {STRIDE} · {L}×{I}={Score} {BAND}`, `TM-NNN`, MITRE/CWE) and the L4↔findings linkage — *deferred (SKILL.md wiring)*
- [x] 5.4 Pin the `d2` version and a free offline layout (ELK or dagre); forbid TALA and remote layout  *(mandated in d2-spec.md §1; the binary pin/install is owned by the render-pipeline workstream)*
- [x] 5.5 Bind icons into D2 `classes` so every node of a type inherits its vendored icon deterministically  *(documented in d2-spec.md §2 + node-type-icons.md §3)*

## 6. Mermaid `@{shape: icon}` + ELK phase-1 path
- [x] 6.1 Document the Mermaid `flowchart` `@{shape: icon}` node form in `mermaid-spec.md`; keep `-->` / `subgraph` / `classDef` / `:::` verbatim; explicitly forbid `architecture-beta`
- [x] 6.2 Adopt ELK layout on the Mermaid path (`@mermaid-js/layout-elk`); document the one-time local icon-JSON mirror needed for offline Mermaid icons
- [x] 6.3 Verify the Mermaid path is zero-eval-change: the icon nodes leave every token the eval parses intact  *(regression-locked by t_mermaid_extractor_identity + all original self-checks + flagship still green)*

## 7. Rendering dispatch + Mermaid back-compat
- [ ] 7.1 Make the diagram render step dispatch by extension (`.mmd`→mmdc, `.d2`→d2); keep `.mmd` accepted indefinitely (coordinate the preflight/packaging with the pipeline-integration workstream — a dependency, not this change) — *deferred to the render-pipeline workstream*
- [ ] 7.2 Inline the D2 SVG into the HTML report (offline, no CDN); keep sequence diagrams in Mermaid — *deferred (render pipeline)*
- [ ] 7.3 Confirm committed `docs/examples/…/*.mmd` and `docs/diagrams/*.mmd` still render through the dispatcher — *deferred (no dispatcher yet); the eval already accepts both `.mmd` and `.d2` fences*

## 8. Boundary + docs
- [x] 8.1 Update `mermaid-review-checklist.md` / `mermaid-diagrams.md` to engine-neutral wording (node-type vocabulary, engine-agnostic assertions)
- [x] 8.2 State in the eval module docstring that verification stays reference-free across engines (no golden-diagram comparison; abstention passing)

## 9. Verify
- [x] 9.1 `openspec validate modernize-visual-engine --strict`
- [x] 9.2 Run the reliability harness on a D2-authored sample and a Mermaid-authored sample; confirm identical property verdicts and green evals  *(t_d2_extractor_parity: identical defect codes + stats on the equivalent pair)*
- [ ] 9.3 Adversarial pass: confirm no new check changes its verdict based on which type/id/finding the model chose, and that a network-blocked render still succeeds with vendored icons — *first half proven (membership-not-choice, `unknown`/`other` pass, abstention on no-tokens); network-blocked render is a real-tooling check owned by the render-pipeline workstream*
