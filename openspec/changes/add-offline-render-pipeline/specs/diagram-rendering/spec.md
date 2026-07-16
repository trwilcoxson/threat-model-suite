## ADDED Requirements

### Requirement: Diagrams render through a single extension-dispatching seam
The skill SHALL render diagrams through one `scripts/render_diagrams.sh` seam that dispatches by file
extension (`.mmd` to the Mermaid renderer, `.d2` to the D2 toolchain) over every diagram artifact the run
produced, independent of which phase emitted it. The seam SHALL be behavior-identical to today's inline
render for `.mmd` inputs, and an unrecognized extension SHALL fail loudly (nonzero exit naming the file)
rather than silently omit a diagram.

#### Scenario: Mixed-engine run renders each by extension
- **WHEN** a run has authored both `.mmd` and `.d2` diagram files in the output directory
- **THEN** the seam renders each file with the renderer for its extension, and a `.d2` file never routes
  to the Mermaid renderer nor a `.mmd` file to D2

#### Scenario: Unknown extension fails loud
- **WHEN** a diagram artifact carries an extension no renderer handles
- **THEN** the seam exits nonzero naming the offending path, rather than producing a report silently
  missing that diagram

### Requirement: HTML report embeds diagrams with no runtime render dependency
The HTML report SHALL embed each diagram as inline SVG or a pre-rendered PNG, and SHALL NOT reference a
client-side Mermaid runtime or CDN. D2 SVG SHALL be inlined directly into the HTML (pure-Go, offline, no
browser at render time). The post-assessment HTML verification SHALL accept an inline `<svg>` diagram as
satisfying the diagram-embed check, not only an `<img>` PNG, while keeping the Mermaid-CDN/runtime ban.

#### Scenario: Inline SVG satisfies the embed check
- **WHEN** the report embeds the structural diagram as inline `<svg>` and contains no `<img>` PNG
- **THEN** the HTML verification passes the diagram-embed check on the basis of the inline SVG

#### Scenario: CDN reference still rejected
- **WHEN** `report.html` references a mermaid.js CDN/runtime or calls `mermaid.initialize`
- **THEN** the HTML verification fails loudly (the ban is unchanged by the SVG relaxation)

### Requirement: Two-tier offline PNG for Office deliverables
Raster PNG — required for docx/pdf/pptx and as the HTML embed fallback — SHALL be produced by a two-tier
renderer: a primary tier using a one-time-warmed, cached headless browser (offline after warm-up,
full-fidelity labels) and a browser-free fallback tier (`d2` to SVG to `resvg` to PNG). The renderer SHALL
record which tier produced each PNG in the generation log. Neither tier SHALL require network access at
render time.

#### Scenario: Primary tier when the cached browser is present
- **WHEN** the one-time-warmed browser cache is available
- **THEN** PNGs render on the primary tier at full label fidelity and the generation log records the tier
  used

#### Scenario: Fallback tier when no browser is available
- **WHEN** the host has no usable headless browser (locked-down or air-gapped) but the fallback tier's
  dependencies are present
- **THEN** the renderer produces PNGs on the browser-free resvg tier and records the fallback in the log

### Requirement: The browser-free tier never silently blanks a diagram
When the browser-free fallback rasterizer is active, the diagram source SHALL be constrained to plain
single-line text labels (the rasterizer drops `<foreignObject>`, which D2 uses for markdown, multi-line,
and wrapped labels), with rich threat annotations carried in the adjacent machine-parseable matrix
instead. The deterministic diagram check SHALL reject a `|md|`, multi-line, or foreignObject-bearing label
while the fallback tier is active, and the renderer SHALL verify each rasterized PNG is non-degenerate
(non-blank) rather than embedding an empty image. This check compares the emitted source only against the
active renderer's known capability and checks the output artifact is non-empty — never against a golden
diagram — and the honest alternative (move the annotation to the adjacent matrix) is always available.

#### Scenario: Rich label rejected on the fallback tier
- **WHEN** the fallback tier is active and a diagram label uses `|md|` or a multi-line/wrapped form
- **THEN** the diagram check flags it so the annotation moves to the adjacent matrix, before a silently
  blank label can reach the report

#### Scenario: Blank raster caught before embedding
- **WHEN** a rasterized PNG comes out blank or degenerate
- **THEN** the renderer fails loudly rather than embedding an empty diagram into the deliverables

### Requirement: A fail-loud preflight verifies the renderer before the pipeline runs
A `scripts/ensure_renderer.sh` preflight SHALL run at pipeline start and verify every render dependency
the run needs is present locally — the `d2` and `resvg` binaries, the vendored local icon set and font,
and (for the primary PNG tier) the warmed browser cache — exiting nonzero with the specific missing
dependency if any is absent. A missing or unusable renderer SHALL surface as a startup error, never as a
silent failure at render time several agents later.

#### Scenario: Missing binary halts at start
- **WHEN** the preflight runs and `d2`, `resvg`, or the vendored font/icons are absent
- **THEN** the pipeline stops at startup naming the missing dependency, not at report generation

#### Scenario: Air-gapped host with no browser declares the fallback tier
- **WHEN** the host is air-gapped, the warmed browser cache is absent, but the resvg fallback
  dependencies are present
- **THEN** the preflight passes with the fallback tier declared active, which in turn enforces the
  plain-single-line-label constraint on the diagram source

### Requirement: Rendering is hermetic, offline, and deterministic
The renderer SHALL reference icons by vendored local file paths and SHALL NOT use remote icon URLs (which
fail air-gapped and can render a broken icon while exiting 0). It SHALL pin a free offline deterministic
layout engine (dagre or ELK) and SHALL NOT use a proprietary or watermarked layout (TALA). It SHALL pin
the engine version so the same source yields the same output, and layout SHALL be automatic with no human
nudging — preserving the determinism boundary that agents author source and rendering is mechanical.

#### Scenario: Remote icon URL rejected for a local path
- **WHEN** a diagram references a remote icon URL
- **THEN** the preflight or render step rejects it in favor of a vendored local path, so no network fetch
  occurs at render time

#### Scenario: Deterministic layout produces identical output
- **WHEN** the same `.d2` or `.mmd` source is rendered twice with the pinned engine version and layout
- **THEN** the output is identical and no manual layout hint was applied

### Requirement: Migration is incremental behind the eval parser, with Mermaid accepted indefinitely
Diagrams SHALL convert from Mermaid to D2 one type at a time, and a diagram type SHALL convert only after
the reference-free diagram parser can extract its properties (the green-throughout guarantee). The render
seam SHALL accept `.mmd` inputs indefinitely so committed worked-example artifacts never break. Diagram
constructs D2 cannot express natively (sequence `alt`/failure fragments, AND/OR attack-tree gates) SHALL
remain in Mermaid or PlantUML.

#### Scenario: Pilot converts one diagram, the rest stay Mermaid
- **WHEN** the diagram parser can extract the Phase-2 structural diagram's properties from D2 source
- **THEN** that diagram may convert to `.d2` while every other diagram stays Mermaid, and the converted
  diagram's reference-free properties still verify

#### Scenario: Legacy Mermaid worked-example still renders
- **WHEN** a committed `.mmd` worked-example is rendered after the migration has begun
- **THEN** the seam still renders it, because Mermaid remains an accepted input
