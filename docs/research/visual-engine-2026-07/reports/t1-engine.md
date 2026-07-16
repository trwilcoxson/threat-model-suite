# TRACK T1 — Visual engine (diagram-as-code with real aesthetics + typed icons)

**Question:** can we materially improve diagram aesthetics/legibility — distinguishable icons per node
type, clean flows/boxes/trust-boundaries, good auto-layout — while staying **authored as code**,
rendering **offline**, and preserving the pipeline's **deterministic boundary** (agents reason &
generate; deterministic layers only verify structure over emitted facts, never script content)?

**Answer: yes, decisively.** Two engines (D2, PlantUML/C4) give real per-type icons and legible
trust zones today; the Mermaid incumbent can *also* get real typed icons in place without an eval
rewrite. I re-rendered the flagship structural diagram in all three and proved offline render
hands-on (`./poc/`). Recommendation below is a **#1 pick (D2)** plus a **cheap incumbent-upgrade
fallback (Mermaid `@{shape:icon}`)**, with a decoupling architecture that keeps the determinism
boundary intact.

---

## 1. What we produce today, and its concrete weakness

The current structural diagram (`docs/examples/.../structural-diagram.mmd`, rendered
`00-baseline-mermaid.png`) is a `flowchart TD` where a node's **type is encoded only by shape + a
`classDef` fill colour** (external `[ ]`, process `([ ])`, datastore `[( )]`, pipeline `[/ /]`), with
**no icons**; trust boundaries are `subgraph` blocks; edges are typed via text labels + `linkStyle`
colours. Rendered, it is competent but **muddy exactly as the owner says**: every node is a grey/blue
box, so you must read each label to know what it is, and the boundaries are faint flat rectangles.

**The dominant constraint on any engine change** — the deterministic diagram eval
(`skills/threat-model/evals/reliability/diagram_checks.py`) is a **Mermaid text parser**: it regexes
` ```mermaid ` fences and matches `-->` / `subgraph` / `classDef` / `:::class` / `Layer: L1` stamps to
verify *properties* (required layers, every edge typed+annotated, trust-boundary subgraphs, ownership
markers, an L4 overlay whose `TM-NNN` ids match findings). **Any engine that isn't Mermaid either
forces a port of this parser to the new syntax, or a decoupled "semantic source vs render" split.**
This drove the ranking as much as aesthetics did.

## 2. Engine evaluation (5 parallel sub-agents, each adversarially self-verified)

Scores 1–5. **as-code** / **offline** = renders to SVG/PNG with no SaaS / **icons** = distinct
controlled icon per node *type* / **bound** = trust-boundary quality / **layout** = auto-layout on a
dense DFD / **det/eval** = fit to declarative, deterministic-boundary pipeline + our existing eval /
**lic** = license friendliness / **effort** = migration effort (5 = easy).

| Engine | as-code | offline | icons | bound | layout | theme | det/eval | lic | maturity | effort | Verdict |
|--------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|:--:|---------|
| **D2** (Terrastruct) | 5 | 5¹ | 5 | 4 | 4 | 5 | 4² | 5 (MPL-2.0) | 4 | 3 | **#1 — best aesthetics+icons, declarative, hermetic offline** |
| **Mermaid `@{shape:icon}`** (in-place) | 5 | 3³ | 4 | 3 | 4⁴ | 4 | **5** | 5 (MIT) | 3 | **5** | **Fallback — real typed icons, eval untouched** |
| **PlantUML + C4 + sprites** | 5 | 4 | 5 | 4 | 2 | 3 | 3 | 3 (GPL dflt)⁵ | 5 | 3 | **#3 — richest offline sprites, but dot layout messy on dense graphs** |
| Structurizr DSL / C4 | 5 | 3⁶ | 3 | 5 | 4 | 3 | 5 | 5 (Apache-2.0) | 3 (CLI/Lite frozen) | 4 | Best *model*, but no headless raster — exports to DOT/PUML then renders |
| mingrammer `diagrams` (Py) | 3 | 5 | 5 | 3 | 4 | 4 | **2**⁷ | 5 (MIT) | 4 | 3 | Prettiest icons, **disqualified**: imperative Python that must *execute* breaks the determinism boundary |
| Graphviz / dot | 5 | 5 | 2⁸ | 3 | 5 | 2 | 5 | 4 (EPL) | 5 | 3 | The substrate the others sit on; max control, manual icons, verbose |
| Kroki (render server) | — | 5⁹ | 2⁹ | — | — | — | 4 | 5 (MIT) | 5 | — | Render *substrate*, not a language; great for Mermaid/PlantUML, weak for D2 icons |

¹ D2 inlines **local-file** icons into the SVG → hermetic offline (proven, `03-d2-offline-localicons.png`,
network blocked). Referencing **remote** icon URLs breaks offline **and silently renders a broken icon
while exiting 0** on a 403 (I hit a real 403) — so *vendor icons locally, never remote URLs*.
² D2 is declarative/parseable (cleaner than Mermaid), but it is **not** what today's eval parses →
adopting it needs a port of `diagram_checks.py`'s property checks to D2 syntax (feasible; see §4).
³ Mermaid's `mmdc --iconPacks` **fetches icons from unpkg at render time**; fully-offline needs a
one-time **local icon-JSON mirror** (`--iconPacksNamesAndUrls "logos#http://localhost:PORT/icons.json"`)
or a small custom harness importing the installed `@iconify-json/*` packages.
⁴ Mermaid gains ELK via `@mermaid-js/layout-elk` — a real legibility upgrade for dense graphs.
⁵ Default `plantuml.jar` is GPLv3; LGPL/MIT/EPL jars exist but must be chosen deliberately + feature-checked.
Also ships a JRE + Graphviz dependency.
⁶ Structurizr **cannot emit PNG/SVG headlessly** (raster is browser-rendered); its offline path is
`export → DOT/PlantUML → render`, i.e. it routes through Graphviz/PlantUML anyway.
⁷ `diagrams` is a Python *program that executes* — the agent would write runnable code, not declarative
text a parser can validate; that violates "deterministic layer checks structure, never executes/scripts
content" and needs a sandbox. No Kroki (can't run Python).
⁸ Graphviz icons = manual `image=` local files; no controlled vocabulary of its own.
⁹ Self-hosted Kroki renders offline great **for PlantUML** (sprite libs bundled in the jar → work
server-side). For **D2 it can't see local icon files** (stateless server) → needs data-URI inlining;
and **public kroki.io rate-limits/400s under load** (observed: same valid source flipped 200→400 in
seconds) → POC-only, self-host for anything real.

**Verified hands-on this session** (not just from docs): D2 and PlantUML both installed and rendered
the full 25-node diagram **offline**; D2's local-icon offline render was proven with the network
blocked; Kroki's rate-limiting and D2-local-icon blindness were reproduced directly.

## 3. Recommendation

### #1 — Adopt **D2** as the flagship visual engine (structural + L4 risk-overlay + SBOM diagrams)
D2 best satisfies the owner's two explicit goals: **distinguishable icons per node type** and
**clean, legible flows/boxes/trust-boundaries** (`01-d2-structural.png` vs the baseline is night and
day). It stays diagram-as-code (declarative `.d2`), is a single MPL-2.0 Go binary, and renders a
**hermetic offline SVG** when icons are vendored locally (proven). Colored semantic edges
(build/admin/async/control) and tinted, dashed **nested** trust zones give it the cleanest security-map
read of the three. Render by **shelling out to the `d2` CLI directly** (not Kroki — Kroki can't see
local icon files and its public instance rate-limits).

### Cheap incumbent-upgrade fallback — **Mermaid `@{shape: icon}` (v11.3.0) + ELK + tuned theme**
If porting the eval to D2 is unacceptable now, Mermaid can get **real per-type Iconify icons while
keeping `flowchart` `-->` / `subgraph` / `classDef` / `:::` verbatim** — so `diagram_checks.py` stays
**100% intact**. Add ELK layout (`@mermaid-js/layout-elk`) for dense-graph legibility and a tuned
`themeVariables`/`look: handDrawn`. Offline needs a one-time local icon-JSON mirror. This is the
lowest-risk, lowest-effort win and a valid **phase-1** even if D2 is the eventual target.
> **Trap to avoid:** the `architecture-beta` diagram type has prettier native icon syntax but uses
> `group`/`service`/`edge` keywords — **no `-->`/`subgraph`/`classDef`** — so it would *nuke* the
> existing eval. Stay on `flowchart` + the `icon` shape.

### #3 — **PlantUML + C4 + sprites**, if brand-logo fidelity + server-side rendering dominate
Best-in-class **offline** icon breadth (AWS/Azure/GCP/k8s/`logos`/FontAwesome, all bundled in the jar
→ render even through a stateless Kroki server), first-class C4 trust boundaries + a free auto-legend.
Held back by GPL-default license, a Java+Graphviz dependency, and `dot` layout that tangles on dense
threat models (visible in `02-plantuml-c4-structural.png`).

## 4. Migration / augmentation shape (preserves the determinism boundary)

The right architecture **decouples the eval-checked semantic source from the renderer**, so richer
visuals never weaken determinism:

1. **Agent authors engine source** (`.d2`, or enhanced `.mmd`) — all reasoning/choice stays in the
   agent, unchanged.
2. **Deterministic layer verifies *properties* over that source** — same philosophy as today: every
   edge typed+annotated, trust-boundary containers present, each node carries a valid *type* from a
   controlled vocabulary, L4 overlay ids ∈ findings. **Never** compare to a golden diagram.
   - For the **D2 path**, port `diagram_checks.py`'s regexes to D2's cleanly-parseable grammar:
     edges `a -> b: "label"`, containers = trust boundaries, `class:`/`classes:` = node type,
     a `# Version: … | Layer: Ln` comment stamp (keep the existing convention). D2 is *easier* to
     parse than Mermaid (real containers + classes, not shape glyphs).
   - For the **Mermaid path**, the eval needs **zero change**.
3. **Controlled typed-icon vocabulary** (T1-05): ship a small, versioned map `node_type → icon`
   (service / datastore / queue / external-actor / secret / boundary + cloud-provider logos), vendored
   as **local SVGs** so renders are hermetic. The agent still *chooses* each node's type; the
   deterministic layer only checks each node has a *valid type + a mapped icon* — a **grounding check,
   not content scripting**. This is the mechanism that turns "pretty" into "consistently pretty"
   without scripting the answer.
4. **Offline CLI render**, engine version **pinned** for reproducible output (D2 layout and PlantUML
   `dot` output both shift across versions).
5. **Keep Mermaid for `sequenceDiagram`** (auth sequences) regardless — it is the strongest and the
   eval already handles it; a mixed-engine suite (D2 for boxes-and-boundaries, Mermaid for sequences)
   is fine.

**Hedge option:** emit **both** — Mermaid as the eval-checked semantic source *and* D2 as the "hero"
render — during a transition, then retire Mermaid rendering once the D2 property-eval is trusted.

## 5. Open questions (for L0 / owner)
- **Eval port vs dual-source:** port `diagram_checks.py` to D2, or keep Mermaid as the eval-checked
  source and use D2 purely for the hero render? (dual-render de-risks but doubles authoring.)
- **Icon pack + license to vendor:** Terrastruct icon library vs AWS Architecture Icons (check
  redistribution terms) vs Iconify `logos`/`mdi` (permissive). Needs a licensing decision before
  bundling.
- **One engine for all artifacts, or engine-per-artifact?** D2 for structural/overlay/SBOM + Mermaid
  for sequence is my recommendation; confirm the owner wants a single hero engine vs a best-tool-per-
  diagram suite.
- Should the L4 risk-overlay and attack-tree/flow companions also move to D2 (bigger consistency win)
  or stay Mermaid in phase 1?

---

```json
{
  "track": "t1-engine",
  "recommendations": [
    {
      "id": "T1-01",
      "title": "Adopt D2 (Terrastruct) as the flagship visual engine for structural / L4-overlay / SBOM diagrams",
      "summary": "D2 gives distinct controlled icons per node type, tinted nested trust-boundary containers, colored semantic edges, and a cleaner elk/dagre layout than Mermaid — staying declarative (as-code) and rendering a hermetic offline SVG when icons are vendored locally. Best on the owner's two explicit goals (typed icons + legible boundaries).",
      "maps_to": "engine",
      "adoptability": 4,
      "impact": 5,
      "effort": 3,
      "risk": "med",
      "depends_on": ["T1-05", "T1-06"],
      "evidence": "Hands-on: brew-installed d2 v0.7.1 (MPL-2.0 single Go binary); re-rendered the full 25-node ECS structural diagram (poc/01-d2-structural.png) — visibly far more legible than baseline (poc/00-baseline-mermaid.png). Adversarially proved fully-offline typed-icon render: poc/03-d2-offline-localicons.png rendered in 140ms with HTTP(S)_PROXY pointed at a dead port, local ./icons/*.svg inlined as base64. Sub-agent adversarial verify confirmed the remote-icon silent-fail-exit-0 trap (I reproduced a real 403).",
      "sources": ["https://d2lang.com/tour/icons/", "https://github.com/terrastruct/d2", "https://github.com/terrastruct/d2/issues/2367", "https://d2lang.com/tour/themes/"]
    },
    {
      "id": "T1-02",
      "title": "Cheap fallback / phase-1: Mermaid flowchart `@{shape: icon}` (v11.3.0) + ELK + tuned theme",
      "summary": "Mermaid can get real per-type Iconify icons while keeping flowchart `-->`/`subgraph`/`classDef`/`:::` verbatim, so the existing deterministic eval stays 100% intact. Add ELK layout and a tuned theme/handDrawn look. Lowest-risk, lowest-effort legibility upgrade; valid phase-1 even if D2 is the eventual target.",
      "maps_to": "engine",
      "adoptability": 5,
      "impact": 3,
      "effort": 2,
      "risk": "low",
      "depends_on": [],
      "evidence": "Sub-agent verified against primary docs: the flowchart `icon` shape landed v11.3.0 and attaches an Iconify glyph to an ordinary flowchart node (CONFIRMED, could not refute) — `-->`/`subgraph`/`classDef`/`:::` all preserved, so diagram_checks.py is untouched. REFUTED the naive offline claim: `mmdc --iconPacks` fetches from unpkg at render time → fully-offline needs a local icon-JSON mirror. architecture-beta would break the eval (different syntax) — avoid.",
      "sources": ["https://mermaid.js.org/config/icons.html", "https://mermaid.ai/open-source/syntax/flowchart.html", "https://github.com/mermaid-js/mermaid-cli/pull/954/files", "https://www.npmjs.com/package/@mermaid-js/layout-elk"]
    },
    {
      "id": "T1-03",
      "title": "PlantUML + C4 + bundled sprites — alternate engine when brand-logo fidelity + server-side render dominate",
      "summary": "Richest fully-offline icon breadth (AWS/Azure/GCP/k8s/logos/FontAwesome, all bundled in the jar and renderable even through a stateless Kroki server), first-class C4 trust boundaries and a free auto-legend. Held back by GPL-default license, a Java+Graphviz dependency, and dot layout that tangles on dense threat models.",
      "maps_to": "engine",
      "adoptability": 3,
      "impact": 4,
      "effort": 4,
      "risk": "med",
      "depends_on": ["T1-04"],
      "evidence": "Hands-on: brew-installed plantuml 1.2026.6 (pulls Java+Graphviz); rendered full 25-node C4 diagram offline in ~2s (poc/02-plantuml-c4-structural.png) — rich logos + colored C4 boundaries + auto-legend, but dot produced sweeping cross-diagram edges + label overlap. Sub-agent inspected dist .puml bytes: each cloud-icon file embeds a monochrome sprite + a base64 PNG, no URLs → offline sprite claim CONFIRMED; hint-free clean autolayout on a 25-node graph REFUTED.",
      "sources": ["https://github.com/plantuml-stdlib/C4-PlantUML", "https://github.com/awslabs/aws-icons-for-plantuml", "https://plantuml.com/layout-engines", "https://plantuml.com/faq"]
    },
    {
      "id": "T1-04",
      "title": "Self-host Kroki as an offline render substrate for Mermaid/PlantUML — NOT the D2 icon path",
      "summary": "Self-hosted Kroki (single core Docker image) is a clean offline HTTP render layer for Mermaid and PlantUML (whose sprite libs are bundled and render server-side). It is the wrong path for icon-rich D2 (stateless server can't read local icon files) and the public kroki.io rate-limits under load — for D2, shell out to the D2 CLI directly.",
      "maps_to": "pipeline",
      "adoptability": 4,
      "impact": 2,
      "effort": 2,
      "risk": "low",
      "depends_on": [],
      "evidence": "Reproduced directly: public kroki.io flipped the SAME valid source 200->400 within seconds (rate-limiting), and its 5s D2 command-timeout was blown by ~20 server-side icon fetches. Sub-agent verified: Kroki is stateless so D2 local-path icons never reach it (need data-URI inlining) while PlantUML StdLib sprites render offline server-side; default SECURE mode blocks filesystem/network. MIT license.",
      "sources": ["https://docs.kroki.io/kroki/setup/configuration/", "https://github.com/yuzutech/kroki/blob/main/DOCKERHUB.md", "https://kroki.io/", "https://github.com/yuzutech/kroki/issues/33"]
    },
    {
      "id": "T1-05",
      "title": "Ship a controlled node-type→icon vocabulary (vendored local SVGs) + a grounding check",
      "summary": "Define a small versioned map of node type (service/datastore/queue/external-actor/secret/boundary + cloud-provider logos) to a vendored local SVG. The agent still chooses each node's type; the deterministic layer verifies each node has a valid type and a mapped icon — a grounding/consistency check, never content scripting. This is what makes richer visuals *consistently* good without losing the model's freedom to reason.",
      "maps_to": "eval",
      "adoptability": 5,
      "impact": 4,
      "effort": 2,
      "risk": "low",
      "depends_on": ["T1-01"],
      "evidence": "Design synthesized from the determinism boundary in CONTEXT + how diagram_checks.py already gates on skill-declared facts (roles/kill_chains/manifest) rather than inferring content. Vendoring proven necessary+sufficient by the D2 offline render (T1-01) and the observed remote-icon 403 silent-fail. Preserves 'structure over emitted facts, never a golden answer'.",
      "sources": ["https://d2lang.com/tour/icons/", "https://github.com/terrastruct/d2/issues/2367"]
    },
    {
      "id": "T1-06",
      "title": "Decouple the eval-checked semantic source from the renderer; port diagram_checks.py property checks to the chosen engine",
      "summary": "Keep the deterministic layer verifying properties (typed/annotated edges, trust-boundary containers, valid node types, L4 ids ∈ findings) over whatever source the agent emits. For a D2 move, port the regex property-checks to D2's cleanly-parseable grammar (edges/containers/classes/version-stamp); for the Mermaid fallback, zero change. Optionally emit both (Mermaid=eval source, D2=hero render) during transition.",
      "maps_to": "eval",
      "adoptability": 3,
      "impact": 3,
      "effort": 3,
      "risk": "med",
      "depends_on": ["T1-01"],
      "evidence": "Read diagram_checks.py: it is a Mermaid-specific text parser (mermaid code fences, and -->/subgraph/classDef/:::/Layer: regexes) checking properties, not a golden answer. D2's grammar (containers=boundaries, classes=types, `a -> b: label` edges, `#`-comment stamps) is at least as parseable — I authored a spec-faithful 25-node D2 with those exact structures (poc/structural.d2). One instructive determinism note: a typo'd edge target auto-created a phantom D2 node in my first render — argues for a dangling/duplicate-id check in the port.",
      "sources": ["https://d2lang.com/tour/layouts/", "https://github.com/terrastruct/d2"]
    },
    {
      "id": "T1-07",
      "title": "Adopt ELK auto-layout for whichever text engine is chosen (Mermaid or D2)",
      "summary": "ELK (available for both Mermaid via @mermaid-js/layout-elk and D2 via D2_LAYOUT=elk) materially improves legibility on dense DFDs — fewer edge crossings, cleaner orthogonal routing — for near-zero authoring cost. A trivial, high-leverage lever independent of the icon decision.",
      "maps_to": "engine",
      "adoptability": 5,
      "impact": 3,
      "effort": 1,
      "risk": "low",
      "depends_on": [],
      "evidence": "The POC D2 structural render (poc/01-d2-structural.png) used D2_LAYOUT=elk and laid out 25 nodes + 3 nested boundaries cleanly. Mermaid sub-agent verified ELK is a real dense-graph upgrade over dagre (NETWORK_SIMPLEX/BRANDES_KOEPF placement, mergeEdges).",
      "sources": ["https://d2lang.com/tour/layouts/", "https://www.npmjs.com/package/@mermaid-js/layout-elk"]
    }
  ],
  "open_questions": [
    "Port diagram_checks.py to D2, or keep Mermaid as the eval-checked semantic source and use D2 only for the hero render (dual-render de-risks but doubles authoring)?",
    "Which icon pack to vendor and under what license — Terrastruct icons vs AWS Architecture Icons (redistribution terms) vs Iconify logos/mdi (permissive)?",
    "Single hero engine for all artifacts, or engine-per-artifact (recommend: D2 for structural/overlay/SBOM, keep Mermaid for sequenceDiagram)?",
    "Move the L4 risk-overlay + attack-tree/flow companions to D2 in phase 1 for consistency, or migrate structural-only first?"
  ],
  "poc_results": "poc/00-baseline-mermaid.png — Mermaid (current): legible but monochrome, node type only by box shape/fill, faint boundaries. poc/01-d2-structural.png — D2 (#1): distinct AWS icon per type, tinted nested trust zones, colored semantic edges, cleanest layout — best node-type-by-icon distinction. poc/02-plantuml-c4-structural.png — PlantUML C4+sprites: richest brand logos + C4 boundaries + auto-legend, but dot routing tangles on this dense graph. poc/03-d2-offline-localicons.png — D2 offline proof: rendered 140ms with network blocked using local vendored icons (base64-inlined). See poc/COMPARISON.md. Winner for distinguishing node types by icon: D2 (legibility) / PlantUML (brand fidelity); both crush the Mermaid baseline."
}
```
