# D2 Diagram Specification

The canonical specification for **D2 (Terrastruct)** diagrams — the flagship diagram-as-code engine for
the structural (L1-L3), risk-overlay (L4), and SBOM/dependency diagrams. It mirrors `mermaid-spec.md`:
same node-type vocabulary, same typed-edge conventions, same trust-boundary and version-stamp rules,
re-expressed in D2 syntax. Sequence diagrams (auth flows) stay in Mermaid (it has the `alt`/`opt`
fragments D2 lacks) — the suite is deliberately mixed-engine.

The agent authors declarative `.d2`; the pinned `d2` CLI renders an **offline SVG**. No deterministic
layer infers, lays out, or edits content — the renderer only places and rasterizes what the agent wrote.

---

## §1 Rendering — hermetic, offline, deterministic

```bash
d2 --layout elk --theme 0 structural.d2 structural.svg
```

- **Pin the engine version** and use a **free, offline, deterministic** layout — **ELK** (or dagre).
  Never TALA (proprietary, watermarked without a paid key) and never a network layout.
- **Icons are local files only.** Reference every icon by a vendored local path — never a remote URL. A
  remote reference breaks offline rendering and silently renders a broken icon while the CLI exits 0 (a
  real 403 was hit in the POC).
- **Icons render on EVERY tier.** d2 embeds each vendored SVG as a base64 data URI in its own output
  SVG, so the icons survive both render tiers — the browser-free fallback (`rsvg-convert`/`resvg`) only
  blanks multi-line **foreignObject labels**, NOT embedded icons. "Fallback tier" therefore never means
  "no icons": bind the node-type icon regardless of tier; only labels degrade to plain single-line.
- Re-rendering the same source with the same pinned toolchain yields the same diagram (no human nudging).
- Inline the resulting SVG into the HTML report (offline, no CDN).

## §2 Symbol / icon taxonomy — the node-type vocabulary (MANDATORY icon binding)

Node types are the **controlled vocabulary** in `node-type-icons.md` (shared with the Mermaid path).
**Every typed class MUST bind its node-type `icon:`** — the vendored local glyph from
`references/icons/<type>.svg`. This is REQUIRED on hand-authored D2 too, not just the deterministic
`recon_to_d2.py` render: an un-iconned diagram is the *old plain* look and breaks visual consistency
with the rest of the flow's diagrams and the dashboard. The diagram eval enforces it
(`d2-missing-node-icon`).

```d2
classes: {
  external-actor: { shape: person;        icon: ./icons/external-actor.svg; style: { fill: "#cce5ff"; stroke: "#004085" } }
  service:        { shape: rectangle;      icon: ./icons/service.svg;        style: { fill: "#f5f5f5"; stroke: "#666666" } }
  datastore:      { shape: cylinder;       icon: ./icons/datastore.svg;      style: { fill: "#e2e3e5"; stroke: "#383d41" } }
  queue:          { shape: queue;          icon: ./icons/queue.svg }
  external-dep:   { shape: package;        icon: ./icons/external-dep.svg;   style: { stroke-dash: 3 } }
  pipeline:       { shape: parallelogram;  icon: ./icons/pipeline.svg;       style: { fill: "#d5dbdb"; stroke: "#7f8c8d" } }
}

R0: "Anonymous User\n(browser · no credential)" { class: external-actor }
D1: "Product Catalog\nDynamoDB [managed]"       { class: datastore }
```

- Every drawn node MUST carry a `class:` from the vocabulary, and every typed class MUST carry its
  vocabulary `icon:`. `unknown`/`other` is a passing member — use it rather than inventing a type.
- Same type → same class → same icon across every diagram (the consistency guarantee). Risk-styled L4
  variants (`svcHigh`, `dsMed`, …) still bind the underlying node-type icon (the risk rides the fill).
- The icon path is resolved by d2 **relative to the .d2 file's own directory** (not the CWD), and
  embedded offline as a base64 data URI. Icons render on BOTH tiers (see §1).
- **Deterministic guarantee.** Rather than rely on remembering, run the injector to bind icons onto any
  hand-authored D2 mechanically: `python3 scripts/inject_node_icons.py <file>.d2 -i` (idempotent; folds
  the risk/camelCase class names onto their node-type; leaves attack-graph classes untouched). Prefer
  the fully deterministic `recon_to_d2.py` render for the L1 structural diagram when recon is typed.

## §3 Trust boundaries = containers

A trust zone is a **container** (a node with child nodes). Nest them for VPC → subnet → task tiers, and
tint each with a `style` block:

```d2
VPC: "VPC 10.120.0.0/16 · 2 AZ" {
  style: { fill: "#eaf2fb"; stroke: "#004085"; stroke-dash: 4; border-radius: 8 }
  PUB: "Public Subnets — ALB tier" {
    style: { fill: "#f4f9ff"; stroke: "#3b6ea5"; stroke-dash: 2 }
    C4: "Client ALB\ninternet-facing [managed]" { class: service }
  }
  PRIV: "Private Subnets — Fargate tier" {
    style: { fill: "#fff8f0"; stroke: "#a5713b"; stroke-dash: 2 }
    C7: "ECS client task [managed]" { class: service }
  }
}
```

The container that encloses ≥1 child node is a boundary zone; the eval counts these the way it counts
Mermaid `subgraph`s. An edge whose endpoints sit in different containers is a **boundary crossing** — the
zone is read from the dotted path (`VPC.PRIV.C7` → innermost zone `PRIV`; a bare id → the external zone).

## §4 Typed + annotated edges

Every arrow MUST be typed, exactly as in `mermaid-spec.md §4`. In D2 the label carries the prefix,
protocol, sensitivity, and encryption state; edge semantics ride the `style`:

```d2
R0 -> VPC.PUB.C4: "HTTP · SPA page load [PUBLIC] [PLAIN]"
VPC.PRIV.C2 -> D1: "HTTPS · DocumentClient.scan [INTERNAL] [ENC]"
X1 -> CICD.C9:   "[BUILD] source poll [CONFIDENTIAL]" { style: { stroke: "#f39c12"; stroke-width: 2 } }
R5 -> D6:        "[ADMIN] terraform apply [RESTRICTED]" { style: { stroke: "#cc0000"; stroke-dash: 3 } }
```

- **Prefixes** (`[CTRL]`, `[AUTH]`, `[KEY]`, `[ADMIN]`, `[ASYNC]`, `[REPL]`, `[BUILD]`) and
  **sensitivity** (`[PUBLIC]`/`[INTERNAL]`/`[CONFIDENTIAL]`/`[RESTRICTED]`) are identical to the Mermaid
  path — the eval's annotation regexes are engine-agnostic and read them from the label verbatim.
- Every edge endpoint MUST resolve to a **declared node**. A typo'd target silently auto-creates a
  phantom node in D2 — declare every node before wiring it.

## §5 Risk overlay (L4) — classes + threat annotations

Reuse the risk styling classes and the machine-parseable annotation format from `mermaid-spec.md §5`:

```d2
classes: {
  highRisk:     { style: { fill: "#ffcccc"; stroke: "#cc0000"; stroke-width: 2 } }
  criticalRisk: { style: { fill: "#ff9999"; stroke: "#990000"; stroke-width: 3 } }
}
C5: "Server API ALB\n⚠ S,T,I,E · 4×4=16 HIGH\nTM-004 · T1190 · CWE-287" { class: highRisk }
```

Keep the L4↔findings linkage: every HIGH+ finding's `TM-NNN` appears in the overlay, and each overlay
threat annotation carries `⚠ {STRIDE} · {L}×{I}={Score} {BAND}` plus `TM-NNN` / MITRE / CWE.

## §6 Version / layer / type stamp

Every diagram MUST carry a stamp on a `#`-comment line (D2's comment syntax), mirroring the Mermaid
`%% Version:` stamp. The eval reads the **declared** `Layer:`/`Type:` fields — it never infers them:

```d2
# Version: 2026-07-15 | Phase: 2 | System: {name} | Layer: L1
# Version: 2026-07-15 | Phase: 7 | System: {name} | Type: SBOM
```

- `Layer: L1..L4` — the DFD decomposition level (drives the required-layers check).
- `Type: Attack Flow | SBOM | ...` — routes analytical/companion diagrams (uses the `| Type:` field
  form, shared with Mermaid).
- A legend covering the symbols, edge types, and risk classes used MUST be present in the report.

## §7 The eval-facing D2 subset

The deterministic extractor (`diagram_checks._d2_defs`) parses a documented subset — author within it:

1. **One statement per line.** Comments are `#` at line start.
2. **Trust-boundary containers** open with a trailing `{` and close with a `}` on its own line; children
   are defined on their own lines inside.
3. **Leaf nodes** carry an inline single-line body: `ID: "label" { class: TYPE; icon: PATH }`, or no body
   at all: `ID: "label"`.
4. **Edges**: `A.B -> C.D: "label"`, with an optional trailing `{ style }` on the same line.
5. **`classes:` / `vars:`** blocks are skipped by the extractor — put layout config there or on the CLI.

This subset delivers all four requirements the threat-model diagram needs from one declarative,
auto-laid-out, parseable source: typed icons, nested colored trust boundaries, per-edge typed/annotated
labels, and clean offline auto-layout.
