## Why

The diagram is the suite's core artifact, and today it is the weakest link aesthetically. The Phase 2
structural DFD is a Mermaid `flowchart` where a node's **type is encoded only by shape + a `classDef`
fill colour** (external `[ ]`, process `([ ])`, data store `[( )]`) with **no icons**; trust
boundaries are flat `subgraph` rectangles. Rendered, every node is a grey/blue box — you must read each
label to know what it is. The owner's two explicit goals — *distinguishable icons per node type* and
*clean, legible flows/boxes/trust-boundaries* — are unmet by the incumbent.

A rendered engine bake-off (research track T1, POC renders under `research/t1-engine/poc/`) settled the
engine question: **D2 (Terrastruct)** wins on both goals — a distinct controlled icon per node type,
tinted nested trust zones, coloured semantic edges, cleaner ELK layout — while staying declarative
(as-code) and rendering a **hermetic offline SVG** when icons are vendored locally. **Mermaid
`@{shape: icon}` + ELK** is the cheap phase-1 win: real per-type icons with `flowchart` / `-->` /
`subgraph` / `classDef` / `:::` preserved verbatim, so the existing eval needs zero change on that path.
PlantUML/C4 and self-hosted Kroki (for the D2 icon path) were evaluated and rejected.

The dominant constraint is not aesthetics — it is the **determinism boundary**. The diagram eval
(`skills/threat-model/evals/reliability/diagram_checks.py`) is a **Mermaid text parser**: it regexes
` ```mermaid ` fences and matches `-->` / `subgraph` / `classDef` / `:::` / `Layer: L{N}` / `TM-NNN`
to verify *properties* (required layers, every edge typed+annotated, trust-boundary containers,
ownership markers, an L4 overlay whose ids trace to findings) — **never a golden diagram**. Any engine
that isn't Mermaid would force a rewrite of this parser, or a decoupled "eval-checked source vs render"
split. The engine cannot move without a plan that keeps every reference-free property assertion intact.

That plan is this change: adopt D2 behind a **per-engine extractor** so the reference-free property
assertions survive verbatim, and make the controlled node-type→icon vocabulary itself a **grounding
check** — the mechanism that turns "pretty" into "consistently pretty" without scripting the model's
answer. This change is the dependency root for the richer-artifact and framework workstreams that
follow it.

## What Changes

- **Adopt D2 as the flagship diagram-as-code engine** for the structural (L1-L3), risk-overlay (L4),
  and SBOM/dependency diagrams. The agent authors declarative `.d2`; `d2` renders an offline SVG. All
  reasoning and layout choice stays in the agent — no deterministic layer infers, lays out, or edits
  content. (T1-01)
- **Land Mermaid `@{shape: icon}` + ELK as the zero-eval-change phase-1 legibility upgrade** — per-type
  icons on ordinary `flowchart` nodes with `-->` / `subgraph` / `classDef` / `:::` unchanged, so the
  eval is untouched on this path. Forbid `architecture-beta` (its `group`/`service`/`edge` syntax would
  nuke the eval). (T1-02)
- **Ship a controlled node-type→icon vocabulary** — a small, versioned map `node type → vendored local
  SVG` (service / datastore / queue / external-actor / secret / boundary + cloud-provider logos), with
  an explicit `unknown`/`other` member. The agent still chooses each node's type; the vocabulary is a
  fixed closed set. (T1-05)
- **Make renders hermetic and deterministic** — reference only locally vendored icons (never remote
  URLs, which break offline and silently render a broken icon on a 403), pin the engine version, and
  use a free offline **ELK** (or dagre) auto-layout — never proprietary/watermarked TALA. (T1-07)
- **Keep Mermaid an accepted input throughout** — the renderer and eval dispatch by declared
  engine (fence/extension); sequence diagrams (auth flows) stay Mermaid (it has the `alt`/`opt`
  fragment primitives D2 lacks); committed `.mmd` worked-examples never break. (T1-02)
- **Generalize `diagram_checks.py` into a per-engine extractor feeding shared reference-free
  assertions** — split engine-specific parsing (blocks / edges+labels / boundary containers / node
  type tokens / stamps) from the engine-agnostic property assertions, so a diagram converts to D2 only
  after its extractor lands and **no property check changes meaning**. (T5-05, T1-06)
- **Add a typed-icon / node-type vocabulary compliance grounding check** — every node typed, every type
  in the controlled vocabulary, same type → same icon across diagrams (consistency), legend covers used
  types; `unknown`/`other` passes; `>10%` untyped → defect, else warning. It counts typed-vs-untyped
  and vocab membership, **never which type a node is**. (T4-01)

## Capabilities

### New Capabilities
- `diagram-rendering`: the multi-engine authoring + rendering surface — D2 as the flagship as-code
  engine, the Mermaid `@{shape: icon}` + ELK phase-1 path, the controlled node-type→icon vocabulary,
  hermetic offline rendering with vendored local icons and pinned deterministic layout, and Mermaid
  remaining an accepted input in a mixed-engine suite.

### Modified Capabilities
- `diagram-verification`: extends the existing deterministic diagram checks with a per-engine extractor
  feeding the SAME reference-free property assertions, the node-type vocabulary compliance grounding
  check, and an explicit boundary guarantee that verification stays reference-free across engines.
  (Edge-endpoint integrity — dangling/duplicate-id resolution — is deferred, not delivered here; see
  tasks.md 4.1/4.2.) <!-- ADDED requirements only; the existing structure/consistency/grounding
  assertions in diagram_checks.py keep their meaning verbatim. -->

## Impact

- Skill: `skills/threat-model/SKILL.md` (Phase 2 structural + Phase 7 risk/analytical steps and both
  acceptance gates: name the engine, the node-type vocabulary, and the offline render constraint),
  `references/mermaid-spec.md` (§3 symbol taxonomy re-expressed as the controlled node-type→icon
  vocabulary; note the Mermaid `@{shape: icon}` path and the `architecture-beta` prohibition), a new
  `references/d2-spec.md` (D2 symbol/edge/container/class conventions mirroring mermaid-spec.md), a new
  `references/node-type-icons.md` (the versioned vocabulary map + vendored icon set), and
  `references/mermaid-diagrams.md` / `mermaid-review-checklist.md` (engine-neutral wording).
- Eval: `skills/threat-model/evals/reliability/diagram_checks.py` (per-engine extractor split; new
  node-type vocabulary-compliance check; property assertions unchanged in meaning). Edge-endpoint
  integrity is deferred (tasks.md 4), not landed in this pass.
- Rendering: the diagram render step gains extension dispatch (`.mmd`→mmdc, `.d2`→d2) and vendors the
  icon set + pins the engine — the install/preflight mechanics are owned by the pipeline-integration
  workstream and are a dependency, not part of this change.
- No change to the `structure` / `consistency` / `grounding` / `coverage` layers, to the JSON manifest
  schemas (`recon`/`findings`/`coverage`), or to the blocking production gate (diagram checks stay
  advisory there).
