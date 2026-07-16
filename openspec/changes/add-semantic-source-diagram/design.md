## Context

`recon.json` is already the suite's structured, hard-gate-validated model of the system
(components / data_stores / entry_points / external_deps / trust_boundaries / roles, each
`{id, name, tech|kind, evidence[]}`). Its one missing primitive is the set of **edges** between elements —
today those exist only inside the rendered diagram. Adding them makes `recon.json` a complete semantic
source that a deterministic transform can render, and against which the structural checks become JSON
operations.

## Decisions

1. **`dataflows[]` is the edge model, keyed on existing element ids.** Each dataflow's `source`/`destination`
   reference the `id` of a declared element. `type` (`data|control|build|async|admin`) drives edge colour,
   `protocol`/`sensitivity`/`enc` drive the annotation, `evidence[]` grounds it. Endpoint integrity is then a
   set-membership check over the declared ids — replacing the regex that scraped endpoints out of diagram
   text and mapped them to recon ids.
2. **`element.type` and `element.zone` are optional additive fields.** `type` is a node-type token from the
   controlled vocabulary (`references/node-type-icons.json`) → the icon; membership is a JSON check over the
   same catalog the diagram-side `_node_type_checks` uses (same fuzzy-suggestion behaviour). `zone` names the
   trust boundary that contains the element, so the transform can render **nested boundary containers** —
   the recon model described boundary *crossings*, not containment, so `zone` is the minimal primitive that
   was missing. Both optional, so the back-compat claim is strengthened, not weakened.
3. **The transform (`recon_to_d2.py`) owns 100% of presentation and is pure/deterministic.** Sorted
   iteration, no randomness, output-relative icon paths → byte-stable across machines (a self-check asserts
   re-render identity). The agent authors `recon.json`; it never picks a shape, colour, icon or coordinate.
4. **Every new check is reference-free and inert without `dataflows[]`.** `dataflow-endpoint-integrity`
   (hard/consistency: endpoints ∈ declared ids), `recon-node-type-unknown` (advisory: `type` ∈ catalog),
   `dataflow-ungrounded` (advisory: edge has grounding evidence). When `dataflows[]` is absent the checks do
   not fire, so runs that keep authoring the diagram directly are unaffected.

## The determinism boundary

This **strengthens** the boundary for the structural diagram: the agent emits pure meaning (validated JSON),
and the deterministic transform injects all shapes/icons/colours/layout — the agent literally cannot author
an off-style diagram. The structural checks move from regex-over-diagram-text to property-checks-over-JSON
(id membership, catalog membership, grounding), which are simpler and harder to fool. It never compares to a
golden diagram and abstains cleanly when the semantic source isn't used.

## Alternatives considered

- **OTM as the semantic source.** Rejected (`OTM-EVAL.md`): dormant single-vendor v0.2.0 whose required
  fields fight the suite's contract (0–100 unbanded `threat.risk` breaks `severity == band(L×I)`, required
  diagram coordinates, free-form `component.type`), and the structured-source win comes from JSON, not from
  OTM — `recon.json` already is that JSON.
- **Keep authoring the diagram directly.** Retained as an accepted path (Mermaid + hand-D2 stay valid); the
  semantic source is additive, for when the deterministic-presentation win is wanted.
- **Make `dataflows[]` required.** Rejected: it would break every committed `recon.json` and force the model
  to enumerate edges even when a hand-authored diagram already carries them. Optional preserves back-compat.
