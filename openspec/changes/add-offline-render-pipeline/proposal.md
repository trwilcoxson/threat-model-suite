## Why

The report-analyst renders diagrams and assembles the four deliverables today with two coupled defects
that a better authoring engine (`modernize-visual-engine`) does not fix on its own — they live in the
*render and packaging* seam, not in how agents author:

- **The only render path needs the network and a headless browser at render time.** The report-analyst
  spawn prompt hard-codes `npx -y @mermaid-js/mermaid-cli … -w 3000 --scale 2` (agent-prompts.md:55,103;
  mermaid-diagrams.md:223). `npx -y` pulls mermaid-cli and Puppeteer downloads Chromium on first run.
  On a fresh or locked-down host there is no renderer installed, so a run can reach Phase-7 render and
  only *then* discover it cannot draw — a silent failure five agents deep. There is no preflight.
- **The HTML report is self-contradictory about the Mermaid CDN.** `report-template.md:84,99` tell the
  agent to use a "Mermaid live render (HTML)", while `report-template.md:353` and the shipped
  `scripts/verify_run.sh:31-32` *ban* the Mermaid CDN/runtime — a race-prone, `file://`-breaking,
  parser-breaking dependency. The report can satisfy the ban only by embedding raster PNG, so it forfeits
  crisp, zoomable, offline vector diagrams even though a browser is already viewing the HTML.
- **`verify_run.sh` hard-requires `<img>` PNG embeds** (`verify_run.sh:29`) and PNG is unavoidable for
  docx/pptx/pdf — so raster generation is on the critical path and inherits the browser dependency.
- **The biggest latent risk is a *silent* one.** A browser-free rasterizer (resvg/librsvg) drops HTML
  `<foreignObject>`, which D2 uses for markdown/multi-line/wrapped labels. Rasterized, those labels come
  out **blank while the command exits 0** — broken diagrams reach docx/pdf/pptx and nobody is told.

`modernize-visual-engine` settles the flagship engine (D2, with Mermaid `@{shape: icon}` + ELK as the
phase-1 legibility win) and the diagram eval parser. This change is the ops-facing complement: the render
and packaging mechanics that let a run draw the chosen engine **offline, fail-loud, and incrementally**,
without regressing the reference-free evals.

## What Changes

- **Insert one extension-dispatching render seam** (`scripts/render_diagrams.sh`): lift the report-analyst
  Step 2.5 render logic into a standalone script that dispatches by file extension (`.mmd` → mmdc,
  `.d2` → the D2 toolchain) over every diagram artifact in the output dir, independent of the phase that
  emitted it. Behavior-identical for `.mmd` on day one; an unknown extension fails loud, never skips.
- **Inline offline D2 SVG into the HTML report and kill the Mermaid CDN.** D2 SVG is pure-Go and fully
  offline — inline it directly into `report.html`. Relax the `verify_run.sh` HTML check to accept an
  inline `<svg>` diagram as an embed (not only `<img>` PNG); keep the Mermaid-CDN/runtime ban unchanged.
  Resolve the report-template contradiction toward inline SVG.
- **Add a two-tier offline PNG path** for docx/pdf/pptx (and the HTML PNG fallback): a **primary** tier
  using a one-time-warmed, cached headless browser (offline after warm-up, full-fidelity labels), and a
  **browser-free fallback** tier (`d2 → svg → resvg → png`). The renderer records which tier drew each
  PNG in `report-generation-log.md`.
- **Make the browser-free tier fail loud, never silently blank.** When the resvg fallback is active,
  constrain diagram labels to plain single-line text (rich threat annotations move to the adjacent
  machine-parseable matrix, which already carries the data); the diagram check rejects a
  `|md|`/multi-line/foreignObject label while that tier is active, and the renderer verifies each PNG is
  non-degenerate rather than embedding a blank image.
- **Add a fail-loud air-gap preflight** (`scripts/ensure_renderer.sh`) at pipeline start: verify the
  `d2` and `resvg` binaries, the vendored local icon set and font, and (for the primary tier) the warmed
  browser cache are present, exiting nonzero with the specific missing dependency — a startup error, not
  a Step-2.5 surprise.
- **Pin the render for determinism and hermetic offline:** reference icons by vendored local file paths
  (never remote URLs), pin a free offline deterministic layout (dagre/ELK, never proprietary/watermarked
  TALA), and pin the engine version. Layout stays automatic — no human nudging.
- **Migrate diagram-by-diagram behind the eval parser.** Convert one diagram type only after the
  reference-free parser can extract its properties (green-throughout); keep `.mmd` an accepted input
  indefinitely so committed worked-examples never break; keep sequence `alt`/failure fragments and
  AND/OR attack-tree gates in Mermaid/PlantUML (D2 lacks those primitives).

## Capabilities

### New Capabilities
- `diagram-rendering`: the render/packaging/migration seam — extension dispatch, offline SVG inlining and
  the HTML-embed/CDN gate, the two-tier offline PNG path and its silent-blank guards, the fail-loud
  air-gap preflight, hermetic deterministic render configuration, and the incremental Mermaid→D2
  migration ordering.

### Modified Capabilities
<!-- Depends on `modernize-visual-engine` for the engine decision and the diagram-eval parser
     (diagram_checks.py D2 extractor); this change adds no requirement to that capability and does not
     alter the diagram property checks — it only feeds them a rendered artifact and one renderer-tier
     precondition (the plain-label constraint) that stays reference-free. -->

## Impact

- Modified: `skills/threat-model/references/agent-prompts.md` (report-analyst prompts call
  `scripts/render_diagrams.sh` instead of an inline `npx … mermaid-cli`; HTML rules allow inline SVG),
  `skills/threat-model/references/report-template.md` (resolve the CDN vs. live-render contradiction
  toward inline SVG for HTML; PNG for Office), `skills/threat-model/scripts/verify_run.sh` (accept inline
  `<svg>` as a diagram embed; CDN ban unchanged), `skills/threat-model/SKILL.md` (Phase 7 / pipeline
  start references the preflight and the render seam).
- New: `skills/threat-model/scripts/render_diagrams.sh` (the extension-dispatching render seam),
  `skills/threat-model/scripts/ensure_renderer.sh` (the fail-loud preflight), vendored local icon set +
  font under the plugin, and packaging updates in `.claude-plugin/` for the new binaries/cache.
