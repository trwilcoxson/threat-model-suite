## Context

The engine decision is settled by research track T1 (`research/t1-engine/REPORT.md`, POC renders in
`research/t1-engine/poc/`): **D2** is the flagship as-code engine, **Mermaid `@{shape: icon}` + ELK**
is the zero-eval-change phase-1 legibility win, and PlantUML/C4 and self-hosted-Kroki-for-D2 are
rejected. Two supporting tracks shape the eval side: T4 (`research/t4-evals/REPORT.md`) specifies the
typed-icon compliance check as a straight extension of the existing `analytical_checks` invariants, and
T5 (`research/t5-pipeline/REPORT.md`) specifies the per-engine extractor as the "green-throughout"
mechanism — each diagram converts to D2 only after its extractor lands.

Three facts from the repo constrain the design and de-risk it:

1. **The blocking production gate does not gate on diagrams.** `run.py validate` blocks only on the JSON
   manifests' `{structure, consistency, coverage, grounding}`; `diagram_checks.py` runs in the
   reliability harness and is *advisory* in the production gate. **An engine swap cannot break the hard
   gate** — the single biggest de-risker for the whole migration.
2. **`diagram_checks.py` already separates cleanly into two halves.** The engine-specific *extractors*
   (`_blocks`, `_layer_of`, `_edges`, `_nodes`, `_typed`) parse Mermaid syntax into semantic primitives;
   the *property assertions* in `check()` / `analytical_checks()` operate on those primitives and are
   already engine-agnostic in spirit (required layers, typed-edge ratio, boundary-container count,
   ownership fraction, L4↔`TM-NNN` linkage). The generalization is a refactor along a seam that already
   exists, not a rewrite.
3. **Node types are already a controlled set** — `mermaid-spec.md` §3 enumerates external / process /
   dataStore / identity / secrets / control / pipeline / externalDep / outOfScope as the *only* allowed
   shapes+`classDef`s. The node-type→icon vocabulary makes that latent closed set explicit and binds
   each member to a vendored icon; it does not invent a new taxonomy.

## The determinism boundary (how each new check preserves it)

The boundary is non-negotiable: **agents do all reasoning and generation; deterministic layers enforce
structure over emitted facts and never infer content or script the answer.** Every check below is
reference-free — it verifies well-formedness, grounding (an element traces to a real id the model
emitted), internal consistency (a value the model stated, recomputed and checked against another value
the model stated), or a ratio over the model's own source — and every check admits honest abstention.

- **Per-engine extractor (T5-05 / T1-06).** The property assertions are *unchanged* — same required
  layers, same typed+annotated-edge ratio, same boundary-container rule, same ownership fraction, same
  L4↔`TM-NNN` linkage. Only the *extraction* (source text → normalized model) becomes engine-specific.
  Because the assertions run over the normalized model, **no property changes meaning across engines**;
  the same threat model authored in Mermaid or D2 gets the same verdict shape. The extractor is chosen
  from the *declared* fence/extension (` ```d2 ` vs ` ```mermaid `), never guessed from content —
  matching the existing rule that `_layer_of` reads a *declared* `Layer: L{N}` stamp and never infers a
  layer from prose.
- **Node-type vocabulary compliance (T4-01 / T1-05).** This is a **grounding + consistency** check, not
  content scripting. It verifies (a) every node carries a type token — *counts typed vs untyped*, never
  *which type*; (b) the token ∈ the fixed controlled vocabulary — compares to a *vocabulary constant*,
  not a per-node answer key; (c) the same type token → the same icon/class across all diagrams —
  intra-document consistency, no external reference; (d) the legend covers every used type — a
  projection of the document onto itself. **The agent alone decides which type each node is.** An
  explicit `unknown`/`other` type is a first-class *passing* value, so the model is never forced to
  invent a type it cannot justify. The `>10%` untyped → defect / else warning threshold mirrors the
  existing `untyped-edges` fraction check verbatim.
- **Edge-endpoint integrity (T1-06).** Reference-free by construction: it resolves every edge endpoint
  *within the source the model emitted* (does target `X` name a declared node?) and never against an
  external list. It exists because the D2 POC showed a typo'd edge target silently auto-creates a
  phantom node — a well-formedness defect, exactly the kind of structural error the deterministic layer
  is meant to catch, with no content inference.
- **Reference-free-across-engines guarantee.** Stated as an explicit requirement so the port cannot
  drift into a golden-diagram comparison: every assertion remains a property/grounding/consistency/
  coverage check over the model's own source, and abstention (`unknown`/`other`/`n/a`/`clean`/
  skipped-when-precondition-false) stays a passing outcome on every check.

Nothing here moves a check between code and judgment, and nothing adds a check that would change its
verdict based on *which* type/id/finding the model chose. Semantic correctness — is this node really a
datastore, is that boundary placed right — remains the diagram judge's job (`prompts/diagram-judge.md`).

## Decisions

1. **D2 is the flagship; Mermaid is the phase-1 path AND the permanent fallback.** D2 best satisfies the
   owner's two goals and renders a hermetic offline SVG. But the migration is incremental: Mermaid
   `@{shape: icon}` + ELK ships first (zero eval change), and Mermaid stays an accepted input forever so
   committed `.mmd` examples and the auth-sequence diagrams (which need `alt`/`opt` fragments D2 lacks)
   keep working. The suite is deliberately **mixed-engine** — D2 for boxes-and-boundaries, Mermaid for
   sequences.

2. **Generalize the extractor before converting any diagram.** The property assertions are the asset;
   they must survive verbatim. So the eval gets a per-engine extractor seam *first*, each diagram
   converts to D2 only *after* its extractor can parse it, and the reference-free evals stay green at
   every step. This is why the change is the dependency root for the downstream artifact/framework
   workstreams — they inherit a stable, engine-neutral assertion layer.

3. **The vocabulary is a closed set with an abstention member, vendored locally.** A fixed
   `node type → local SVG` map (not a per-run choice) is what makes the icon engine *consistently*
   legible. It is vendored as local SVGs because the POC proved remote icon URLs break offline rendering
   and silently render a broken icon while the CLI exits 0 (a real 403 was hit). `unknown`/`other` is a
   member so typing is never coerced.

4. **Route by declared engine, not by content-sniffing.** Extension/fence is a *declared fact* (the
   agent chose to write `.d2` or `.mmd`), consistent with the boundary's "gate on declared facts". A
   later `Engine:` token on the `%% Version:` stamp is optional sugar; the fence/extension is
   authoritative.

5. **Layout is pinned and free.** ELK (or dagre) — both offline, deterministic, no watermark. Never
   TALA (proprietary, watermarked without a paid key) and never a network layout. Deterministic layout
   is itself part of the boundary: no human nudging, same source → same diagram.

## Alternatives considered

- **Port `diagram_checks.py` wholesale to D2 syntax (drop Mermaid).** Rejected: it strands every
  committed `.mmd` worked-example, forces a big-bang rewrite that can't be verified piecewise, and loses
  the strongest engine for sequence diagrams. The per-engine extractor keeps both.
- **Dual-source (Mermaid as the eval-checked source, D2 only as a "hero" render).** A valid transition
  hedge (noted in T1 §4) but it doubles authoring indefinitely. Chosen instead: convert
  diagram-by-diagram behind extractor support, so D2 becomes the eval-checked source once its extractor
  is trusted, with dual-render available only as a temporary de-risk if needed.
- **PlantUML/C4 or self-hosted Kroki for D2.** Rejected per T1: PlantUML's `dot` layout tangles on dense
  threat models and defaults to GPL; Kroki is stateless so it cannot read D2's local icon files (and the
  public instance rate-limits). D2 renders via its own CLI.
- **draw.io / diagrams.net (mxGraph).** Evaluated hands-on after the fact (five real headless renders; see
  `docs/research/visual-engine-2026-07/DRAWIO-EVAL.md`). It has the **best icon library tested** (~10k
  official cloud stencils, offline) and **richer nested trust boundaries than D2** — but no single
  agent-authorable source delivers typed icons + nested boundaries + per-edge annotations + clean
  auto-layout together: the geometry `.drawio` path forces manual node placement (breaks automatic
  layout), the declarative CSV path drops boundaries and per-edge annotation labels, and the only
  all-in-one path (`drawio-ai-kit`) is imperative JS execution — the pattern that disqualified mingrammer
  `diagrams` in T1. It also has no Chromium-free render tier (needed by `add-offline-render-pipeline`) and
  rides on the EOL mxGraph core. Kept as a **documented strong alternate**, not the flagship — revisit if
  priorities reweight from single-source determinism toward icon/boundary fidelity.
- **`architecture-beta` for native Mermaid icons.** Rejected: prettier icon syntax but `group`/`service`
  /`edge` keywords with no `-->`/`subgraph`/`classDef` — it would nuke the existing eval. Stay on
  `flowchart` + the `icon` shape.
- **Make the vocabulary open / let the agent mint types.** Rejected: an open set defeats the consistency
  guarantee (same type → same icon) and the grounding check. The `unknown`/`other` member gives the
  needed escape hatch without opening the set.

## Risks / trade-offs

- **Offline PNG rasterization is the hard part** (T5 §5). D2 SVG is pure-Go and fully offline (a strict
  win for the HTML report); D2 PNG needs a headless Chromium, and the browser-free `d2 → svg → resvg`
  path silently blanks multi-line/markdown labels (they render as `foreignObject`). This is a rendering/
  packaging concern owned by the pipeline-integration workstream; this change depends on that renderer
  but is measured against the *existing* bar — today's `mmdc` already needs network + Chromium.
- **Two engines to author for, during the transition.** Mitigated by the mixed-engine decision (each
  engine owns the diagram types it's best at) and by Mermaid staying an accepted input, so nothing is
  forced to convert on a deadline.
- **Extractor drift.** The risk that a D2 extractor quietly checks something Mermaid didn't (or vice
  versa). Mitigated by the explicit "reference-free-across-engines" requirement and a cross-engine
  parity test: the same model authored in both engines must produce the same verdict shape.
- **Deferred to sibling workstreams:** the offline render preflight + air-gap packaging (pipeline), the
  richer artifacts and their gated checks (ranks 2/7/8), and the `Family:`/`AgentLayer:` stamp
  namespacing (eval-hygiene track). This change ships the engine seam and the vocabulary those
  workstreams build on.

## Open questions

- **Eval port vs dual-source during transition** — convert diagram-by-diagram behind extractor support
  (recommended), or run dual-render (Mermaid=eval source, D2=hero) until the D2 extractor is trusted?
- **Which icon set to vendor and under what license** — Terrastruct icons vs AWS Architecture Icons
  (check redistribution terms) vs Iconify `logos`/`mdi` (permissive). Needs a licensing decision before
  bundling.
- **How much of the vocabulary is cloud-provider-specific** — a generic type set (service/datastore/…)
  is engine- and cloud-agnostic; adding per-provider logos (RDS/KMS/SQS) improves fidelity but grows the
  vendored set and the licensing surface.
- **Should the L4 overlay and attack-tree/flow companions move to D2 in phase 1** for a bigger
  consistency win, or migrate structural-only first (recommended) and convert the rest behind their
  extractors?
