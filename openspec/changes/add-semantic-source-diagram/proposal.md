## Why

The suite's diagrams are authored as diagram-DSL text (Mermaid today, D2 after
`modernize-visual-engine`), which mixes *semantic content* (what components/flows/zones exist) with
*presentation* (shapes, colours, layout) in the same artifact the agent writes. That has two costs: the
agent makes presentation choices it shouldn't (weakening the determinism boundary), and the diagram checks
are regex over diagram text (edge endpoints, node types, trust-boundary crossings all parsed out of the
rendered syntax).

The OTM evaluation (`docs/research/visual-engine-2026-07/OTM-EVAL.md`) established the better architecture —
the agent emits a **structured semantic source** and a **deterministic transform** owns 100% of the
presentation — and showed the dominant vehicle is our **own `recon.json`**, which is already a
hard-gate-validated structured artifact and lacks exactly one thing: a typed **edges** array. A spike
(`docs/research/visual-engine-2026-07/SEMANTIC-SOURCE-SPIKE.md`, rendered proof in
`poc/05-recon-to-d2.{d2,svg,png}`) proved it out: `recon.json` + `dataflows[]` → a deterministic
`recon_to_d2.py` transform renders a legible diagram with typed icons, nested trust boundaries and the full
annotated edge set — structurally equal to the hand-authored D2 but generated entirely from the semantic
source, and the diagram checks collapse into JSON reference/membership checks.

## What Changes

- **Add an optional typed edge model to `recon.json`**: `dataflows[]`
  (`{id, source, destination, type, protocol, sensitivity, enc, label, evidence[]}`), plus optional
  `element.type` (node-type token) and `element.zone` (trust-boundary containment) on elements. All
  additive and optional — every existing `recon.json` still conforms.
- **Add a deterministic `recon → D2` transform** (`scripts/recon_to_d2.py`): the agent authors `recon.json`;
  the transform owns all shapes/icons/colours/nesting/layout, rendering offline via `d2` (+ the vendored
  node-type icon set) with no presentation choices left to the agent.
- **Move the structural diagram's checks from diagram-regex to JSON property checks**: dataflow
  endpoint-integrity (every `source`/`destination` resolves to a declared element id), node-type
  vocabulary membership (`element.type` ∈ the controlled catalog, with a fuzzy suggestion on a miss), and
  dataflow evidence grounding — all reference-free, and **inert when `dataflows[]` is absent** so nothing
  changes for runs that keep authoring the diagram directly.
- **Keep the diagram engines and Mermaid unchanged**: this is a new *authoring path* (semantic source →
  D2), additive to the per-engine extractor from `modernize-visual-engine`, not a replacement.
