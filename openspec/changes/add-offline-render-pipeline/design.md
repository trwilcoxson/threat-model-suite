## Context

The T5 integration research (t5-pipeline/REPORT.md) mapped every diagram-production touchpoint and found
the production hard gate does **not** gate on diagrams — `run.py validate` blocks only on the manifest
`{structure, consistency, coverage, grounding}` contract; `diagram_checks.py` prints advisory notes in
the production gate (run.py:155-166). That is the single biggest de-risker: **an engine/render swap
cannot break the blocking gate.** Only two production touchpoints are Mermaid-render-coupled: the
report-analyst's Step-2.5 raster (agent-prompts.md:55,103) and the HTML embed. Everything else is already
engine-neutral text/JSON.

The engine decision is settled by `modernize-visual-engine`: D2 (Terrastruct) as flagship, Mermaid
`@{shape: icon}` + ELK as the zero-eval-change phase-1 win. The hands-on T1 POC proved D2 renders a 25-node
diagram to a **hermetic offline SVG** in ~140ms with the network blocked when icons are vendored locally,
and reproduced the two traps this design guards against: a **remote icon URL silently renders a broken
icon while exiting 0**, and browser-free rasterization silently blanks foreignObject labels.

This change owns the render/packaging/migration mechanics. It is deliberately **distinct from** the
author-facing engine change: agents authoring `.d2`/`.mmd`, the icon vocabulary, and the eval-parser
generalization all belong to `modernize-visual-engine`; this change consumes those and makes them
render offline, fail loud, and migrate safely.

## The determinism boundary (preserved, and how)

The boundary today: agents author diagram *source text*; rendering and validation are mechanical — no
content inference, no manual layout tweak. D2 keeps this exactly (agents write `.d2`; `d2` + a rasterizer
+ the eval parser are all deterministic given the source). Every check this change adds is well-formedness
or internal-consistency over the run's **own** emitted artifact, never a comparison to a golden diagram,
and every constraint leaves an honest escape hatch:

- **Extension dispatch / CDN ban / SVG-or-PNG embed** — pure structural checks over the emitted HTML and
  file set (does a diagram embed exist; is a client-side Mermaid runtime referenced; does the extension
  map to a renderer). No model facts are interpreted.
- **Plain-label constraint on the resvg tier** — checks the emitted diagram *source* against the *active
  renderer's known capability* (resvg drops `<foreignObject>`), not against any expected label text. The
  honest alternative is always available and already preferred: move the threat annotation to the
  adjacent STRIDE/heat-map matrix, which already carries the machine-parseable `TM-NNN·MITRE·L×I` data.
  The check never says *what* a label must contain — only that a label the fallback renderer would blank
  must not be the sole carrier of the annotation.
- **Non-blank raster verification** — checks the output PNG is non-degenerate (it exists and is not an
  empty image), i.e. the render didn't silently fail. It does not compare the raster to a reference image.
- **Air-gap preflight** — verifies *tools and assets* exist before the run; it involves no model output
  at all, so it cannot script content.
- **Deterministic layout / vendored local icons / pinned version** — remove sources of non-determinism
  (network fetches, watermarked TALA, version drift, manual nudging) so the same source yields the same
  render. This *strengthens* the boundary.

No new field forces a specific finding, and no check infers content. Abstention stays first-class: a
diagram with genuinely no risk overlay, a run that legitimately uses the fallback tier, an installation
that legitimately has no browser — each is a supported, declared state, never a failure.

## Decisions

1. **One extension-dispatching seam, not an engine flag.** `scripts/render_diagrams.sh` dispatches by
   file extension over the diagram artifacts in the output dir. This is the migration seam: both engines
   coexist, diagrams convert one at a time, and `.mmd` stays renderable forever (committed
   `docs/examples/**/*.mmd` and `docs/diagrams/*.mmd` never break). The seam is **phase-agnostic** — it
   renders whatever diagram files exist regardless of which phase authored them, which is the
   render-relevant slice of "place new artifacts by input-set" (the *authoring* placement rule itself
   belongs to `modernize-visual-engine`/T2-T3, not here).

2. **HTML gets inline SVG; Office gets PNG.** D2 SVG is pure-Go and fully offline — inlining it into
   `report.html` is a strict improvement over status quo (crisp, zoomable, full-fidelity labels because a
   browser *views* the HTML), and it satisfies the existing Mermaid-CDN ban without a raster round-trip.
   `verify_run.sh` is relaxed to accept an inline `<svg>` as a diagram embed (today it requires `<img>`),
   with the CDN/runtime ban unchanged. docx/pdf/pptx still need raster PNG, so PNG is not eliminated —
   only removed from the HTML critical path.

3. **Two-tier PNG: cached-browser primary, resvg fallback.** The primary tier warms and caches a headless
   browser once, then renders offline at full label fidelity — **parity with today's mmdc+Chromium, not a
   regression** (the current baseline already needs a browser + network). The fallback tier
   (`d2 → svg → resvg → png`) is browser-free for genuinely locked-down/air-gapped hosts, under the
   plain-label constraint. The bar for the whole change is *no worse than today*, and each tier clears it.

4. **Design AROUND the silent-blank risk — the one thing that must never happen.** A blank multi-line
   label reaching docx/pdf/pptx is the failure mode this change exists to prevent. Three guards, in depth:
   (a) the resvg tier is only chosen when the preflight has *declared* it active; (b) while active, the
   diagram check rejects `|md|`/multi-line/foreignObject labels so the annotation is moved *before*
   render; (c) after render, each PNG is verified non-blank. Silent degradation is converted into a loud,
   early, actionable failure at every layer.

5. **Fail-loud preflight at pipeline start, not at Step 2.5.** `scripts/ensure_renderer.sh` runs at the
   start of a run and exits nonzero naming the missing dependency (`d2`, `resvg`, vendored font/icons, or
   — for the primary tier — the warmed browser cache). Verified on a fresh host: no `d2`/`dot`/`mmdc`
   installed (only `node`/`npx`/`java`), so a preflight is mandatory; without it a missing renderer is
   discovered five agents deep.

6. **Hermetic, deterministic render config.** Icons are referenced by vendored **local file paths**
   (a remote `icon:` URL breaks air-gap *and* silently renders broken while exiting 0 — reproduced in the
   T1 POC); layout is pinned to a free offline deterministic engine (dagre or ELK), **never** TALA
   (proprietary, watermarked without a paid key); the engine version is pinned (D2 layout output shifts
   across versions). All of this keeps renders reproducible and network-free.

7. **Migrate behind the parser, Mermaid forever.** A diagram type converts to `.d2` only after the
   reference-free diagram parser (a `modernize-visual-engine` deliverable) can extract its properties —
   convert one, verify its properties still hold, move on. Sequence `alt`/failure fragments and AND/OR
   attack-tree gates stay Mermaid/PlantUML (D2 has no such primitive). Piecewise conversion is only
   *verifiable* because the evals are reference-free properties, not a golden answer — a big-bang rewrite
   would strand every worked-example and can't be checked one diagram at a time.

## Alternatives considered

- **Self-hosted Kroki as a single multi-DSL render service.** Rejected for this CLI: it *relocates*
  (doesn't remove) the Mermaid Chromium into a companion container, adds an operational service, and is
  blind to D2's local icon files (stateless server) — over-engineered vs. `d2 + resvg` static binaries.
- **Drop PNG entirely, inline SVG for every diagram including in docx/pptx.** Office formats need raster;
  SVG-in-docx support is uneven. Kept as an open question for the *HTML* (inline SVG for all diagrams,
  PNG only for Office) but not adopted for the Office deliverables.
- **Keep the inline `npx … mermaid-cli` in the spawn prompt (no seam).** Rejected: it hard-codes a single
  engine, offers no migration path, and keeps the browser dependency implicit and un-preflighted.
- **If a deployment forbids any browser *and* cannot tolerate the plain-label constraint**, the right
  answer is `modernize-visual-engine` picking Graphviz/PlantUML (native browser-free PNG) for that
  deployment — surfaced as an input to the engine decision, not solved by adding a third tier here.

## Risks / trade-offs

- **New hard deps** (`d2` ~tens of MB, `resvg` small static binary, vendored font + icons, optional
  warmed browser cache) grow the plugin footprint. Mitigated: the binaries are static and the browser
  cache is optional (the resvg tier covers air-gap without it).
- **The resvg fallback reduces standalone diagram legibility** (annotations move to an adjacent table).
  Acceptable because the STRIDE/heat-map matrices already carry the same machine-parseable data; noted as
  an open question for the specific in-diagram grid/table shapes `modernize-visual-engine`/T2-T3 add.
- **Blocked per-diagram-type on `modernize-visual-engine`** shipping the D2 property extractor. This is a
  feature, not a bug: no diagram converts before its parser exists (the green-throughout guarantee). The
  seam, the offline SVG inlining, the preflight, and the two-tier PNG all land *before* any conversion,
  behind unchanged `.mmd` behavior.
