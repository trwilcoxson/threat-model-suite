# TRACK T5 — Pipeline & Rendering Integration

**Question:** given a better engine (T1) and new artifacts (T2/T3) guarded by new evals (T4),
how do they slot into the existing pipeline with the least disruption — phase placement, offline
rendering, packaging, and the migration path off pure Mermaid?

**Assumption (from brief + verified in T1's problem space):** T1 lands on **D2**
([d2lang.com](https://d2lang.com)) — a single static Go binary with per-node typed `icon:`,
composable `classes` (a real classDef), first-class labeled containers for trust boundaries, and a
free offline layout engine. The design below is ~90% engine-agnostic; the ~10% that is D2-specific is
flagged, and the fallbacks (Graphviz / PlantUML) are noted where D2's offline story bites.

---

## 1. TL;DR

1. **The blocking production gate does not gate on diagrams.** `run.py validate` (the PreToolUse hard
   gate) blocks only on `{structure, consistency, coverage, grounding}` of the JSON manifests.
   `diagram_checks.py` runs in the *reliability harness* (`check`/`report`) and prints **advisory**
   notes in the production gate (`run.py:155-166`). **An engine swap cannot break the hard gate** —
   this is the single biggest de-risker for the whole migration.
2. **Only two production touchpoints are Mermaid-coupled:** (a) agents *author* Mermaid source in the
   phase `.md` files; (b) the report-analyst's *Step 2.5* extracts ` ```mermaid ` blocks and rasterizes
   them with `npx -y @mermaid-js/mermaid-cli` (Chromium + network at render time). Everything else
   (manifests, analytical matrices, Navigator JSON) is already engine-neutral text/JSON.
3. **Migrate by inserting one seam, then converting diagram-by-diagram.** Extract rendering into an
   extension-dispatching `render_diagrams.sh` (`.mmd`→mmdc, `.d2`→d2) so both engines coexist; convert
   the L1 structural diagram first; generalize `diagram_checks.py` to parse D2 *before* each
   conversion so the reference-free evals stay green throughout. Mermaid stays an accepted input the
   whole time — committed `.mmd` worked-examples never break.
4. **Offline rendering is the biggest risk, and it already exists today.** Current `mmdc` needs a
   headless Chromium it downloads over the network. D2's *SVG* is pure-Go and fully offline (a strict
   win, and we inline it into the HTML report — killing the banned Mermaid CDN). D2's *PNG* re-inherits
   a headless browser (Playwright/Chromium). Since docx/pptx/pdf need raster PNG and `verify_run.sh`
   requires PNG embeds, PNG generation is the crux — de-risked with a two-tier renderer.

---

## 2. Current diagram-production touchpoints (precise map)

| # | Where | Who | Produces | Inputs that must already exist | Coupling |
|---|-------|-----|----------|-------------------------------|----------|
| A | **Phase 2** structural | `diagram-specialist` | L1–L3 DFD layers → ` ```mermaid ` in `02-structural-diagram.md` + `{name}-L{N}-{layer}.mmd` | `01-reconnaissance.md`, `visual-completeness-checklist.md` | Mermaid syntax (author) |
| B | **Phase 3** auth seq | `security-architect` | `sequenceDiagram` → `{name}-auth-sequence.mmd` | Phase 2 node ids | Mermaid syntax (author) |
| C | **Phase 5** attack tree/flow | `security-architect` | `flowchart` trees + flows, `Type:` stamp → `{name}-attack-tree-{N}.mmd`, `…-attack-flow-{N}.mmd` | scored threats, `kill_chains[]` | Mermaid syntax (author) |
| D | **Phase 7** L4 overlay + analytical visuals | `diagram-specialist` | L4 risk overlay `.mmd`; STRIDE matrix (md table), L×I heat map (md), ATT&CK table + Navigator JSON, RBAC matrix (md), SBOM graph `.mmd` → `07-final-diagram.md` | `02`,`04`,`05`,`06`, `findings.json` | L4/SBOM Mermaid; **matrices/JSON already engine-neutral** |
| E | **report-analyst Step 2.5** render | `report-analyst` | extract ` ```mermaid ` → `.mmd`, strip `~~>`, `npx -y @mermaid-js/mermaid-cli -c mermaid-config.json -w 3000 --scale 2` → `*.png` | phase `.md` files | **mmdc CLI + Chromium + network** |
| F | Report embed | `report-analyst` | HTML (per `verify_run.sh`: PNG embeds, **no** Mermaid CDN), docx/pdf/pptx embed PNGs | rendered PNGs | consumes PNGs (engine-neutral) |
| G | Reliability eval | `diagram_checks.py` | reference-free property checks over ` ```mermaid ` blocks | `report.md` (eval executor artifact) | **Mermaid regex parser**; advisory in prod gate |
| H | Reference spec (author guidance) | 6 `mermaid-*.md` + `mermaid-config.json` + `analytical-visuals.md` | how agents author | — | Mermaid conventions |
| I | Back-compat artifacts | committed | `docs/examples/…/*.mmd`, `docs/diagrams/*.mmd` + `*.png` | — | Mermaid source on disk |

**Determinism boundary today (must be preserved):** agents author *source text* (A–D); rendering (E)
and validation (G) are mechanical, no content inference, no manual layout tweak. D2 keeps this exactly:
agents write `.d2`; `d2` + a rasterizer + the eval parser are all deterministic given the source.

---

## 3. Integration design

### 3.1 Phase placement of new artifacts (respect the existing dependency frontier)

The pipeline's frontier is fixed and correct: **Phase 2 needs Phase 1; Phase 7 needs Phase 2 + 4/5/6.**
New artifacts slot in by **the earliest phase where all their inputs exist**, produced by that phase's
owning persona, gated by that phase's existing acceptance gate — **adding no new blocking edges.**

| New-artifact class (from T2/T3) | Phase | Persona | Rationale (inputs) |
|---|---|---|---|
| **Structural / topology** (typed-icon DFD, layered attack-surface map / LASM base layer, data-lifecycle) | **2** | diagram-specialist | needs only recon; belongs with L1–L3, gated by the Phase-2 structural gate |
| **Interaction-level, pre-score** (STRIDE-per-interaction map, auth/agent sequence, ASTRIDE agent-interaction diagram) | **3** | security-architect | needs threat identification + node ids, not scores (mirrors today's auth-sequence at C) |
| **Risk-bearing / temporal** (L4 overlay, attack-defense trees, LASM temporality overlay, CVSS-exploitability overlay, MITRE ATT&CK/ATLAS layer, kill-chain flows) | **7** | diagram-specialist | needs scored findings + `kill_chains[]`; belongs with the Phase-7 risk gate |
| **Tabular/JSON** (LINDDUN-GenAI matrix, OWASP-LLM coverage table, ATLAS Navigator JSON) | **7** | diagram-specialist | already engine-neutral markdown/JSON — **no renderer needed**, no engine dependency |

Rule of thumb for T2/T3 to hand off any artifact: *declare its input set → it lands in the earliest
phase that satisfies it → its persona is that phase's owner → its precondition-gated check goes in that
phase's acceptance gate and (if it's a node-graph) in `diagram_checks.py`.* No frontier change, no new
serialization.

### 3.2 Offline rendering & packaging (the hard part — verified)

**What breaks naively:** in a fresh skill run there is **no** renderer installed (verified on this host:
no `d2`/`dot`/`mmdc`; only `node`/`npx`/`java`). Today's pipeline survives only by `npx -y` pulling
mermaid-cli **and** Puppeteer downloading Chromium at render time — i.e. **the current baseline already
requires network + a headless browser** ([mmdc #650](https://github.com/mermaid-js/mermaid-cli/issues/650)).
Any migration must be measured against *that* bar, not against zero-dependency.

**Verified engine facts:**
- **D2 SVG = pure Go, fully offline, no browser** (D2 FAQ: no internet after install).
  → **HTML report inlines the D2 SVG directly.** This is strictly better than status quo: crisp,
  zoomable, foreignObject/markdown labels render (a browser *views* the HTML), **no CDN, no runtime** —
  and it satisfies `verify_run.sh`'s "no Mermaid CDN" ban while adding scalable diagrams.
- **D2 PNG = needs Playwright + headless Chromium**, downloaded on first run
  ([d2 #744](https://github.com/terrastruct/d2/issues/744)). docx/pptx/pdf need raster PNG, and
  `verify_run.sh` requires ≥1 `<img>` PNG embed — so PNG can't be skipped.
- **Browser-free SVG→PNG is REAL-BUT-CONSTRAINED** (adversarially verified): `d2 → svg` then
  `resvg`/`rsvg-convert` → PNG works, but resvg/librsvg are static-SVG rasterizers that **drop HTML
  `<foreignObject>`** — and D2 renders **markdown (`|md|`) and multi-line/wrapped labels** as
  foreignObject ([D2 troubleshoot](https://d2lang.com/tour/troubleshoot/),
  [resvg unsupported](https://github.com/linebender/resvg/blob/main/docs/unsupported.md)). Plain
  single-line `<text>` labels rasterize fine; rich/multi-line labels come out **blank, silently**.

**The two-tier renderer** (`scripts/render_diagrams.sh`, dispatches by extension; the determinism-safe
mechanical layer):

1. **HTML → inline SVG.** `d2 --layout dagre in.d2 out.svg` (offline, pure-Go), inline into `report.html`.
   Full fidelity, no browser, no PNG needed for the web report. *(Mermaid inputs: `mmdc … -o out.svg`.)*
2. **docx/pdf/pptx → PNG, tiered:**
   - **Primary (full fidelity):** `d2 in.d2 out.png` with a **one-time-warmed, cached** Playwright
     Chromium vendored into the plugin's browser cache — headless, offline after warm-up. **No worse
     than today's mmdc+Chromium**, and renders rich labels correctly.
   - **Air-gap fallback (no browser at all):** `d2 → svg → resvg → png`, **under the authoring
     constraint: plain-text single-line labels only; multi-line threat annotations move to an adjacent
     markdown table** (the analytical matrices already carry the machine-parseable `TM-NNN·MITRE·L×I`
     data, so the diagram label can stay terse). Install Source Sans Pro locally as a font fallback.

**Packaging & install story** (`.claude-plugin/` + a preflight):
- Add `scripts/ensure_renderer.sh` run **at pipeline start** (fail loud early, not at Step 2.5):
  installs `d2` (release binary / `brew install d2` / `curl …/install.sh`), `resvg` (single Rust
  binary), and — for the primary PNG tier — warms + caches Chromium once. New hard deps: `d2` (~tens of
  MB), `resvg` (small). No JRE/Node needed for D2 itself (Node stays only if Mermaid inputs remain).
- **Air-gap:** vendor the `d2` + `resvg` binaries and a pre-warmed `~/.cache/ms-playwright/` (or skip
  the browser tier entirely and use the resvg fallback with the plain-label constraint). Everything is
  a static binary + a font — no network at render time.
- **Icons:** vendor the icon set locally and reference **local file paths** in `icon:`
  (`icon: ./icons/kms.svg`) — never remote `icons.terrastruct.com` URLs (network + air-gap failure).
  Bind icons into `classes` so every node of a type inherits its icon deterministically.
- **Layout:** pin **dagre** (or ELK) — both free + offline + deterministic. **Never TALA** (proprietary,
  watermarked without a paid key). Deterministic layout keeps the determinism boundary: no human nudging.

### 3.3 Keeping the reference-free evals green

`diagram_checks.py` is Mermaid-regex-coupled (` ```mermaid `, `-->`, `subgraph`, `classDef`,
`%% Version:`). To convert diagrams without red evals, **generalize the eval, don't rewrite its
properties**: add a per-fence engine detector (` ```d2 ` vs ` ```mermaid `) that routes to an
engine-specific *extractor* (blocks / edges / containers / classes / stamps), while the **property
assertions stay identical and reference-free** (required layers, every edge typed+annotated,
trust-boundary containers, ownership markers, L4↔`TM-NNN` link). D2 helps here: it emits a real
`class=` attribute and containers map cleanly to `subgraph` zones. This extractor work is a **T4
deliverable**; each diagram may convert to D2 only *after* T4 can parse it — that ordering is the
green-throughout guarantee.

---

## 4. Staged migration plan (smallest first → full adoption)

| Stage | Step | Blast radius | Blocked by |
|-------|------|--------------|-----------|
| **0** | Extract Step 2.5 into standalone `scripts/render_diagrams.sh`, **dispatch by file extension**, behavior-identical (only `.mmd`→mmdc today). Pure refactor; the seam. | none — evals unchanged | — |
| **1** | Add D2 as a second accepted extension in the renderer + `ensure_renderer.sh`; add `references/d2-spec.md` (icon/symbol taxonomy, typed edges, risk `classes`) mirroring `mermaid-spec.md`. **Convert nothing yet.** | none — Mermaid still authored | **T1** (engine choice) |
| **2** | Generalize `diagram_checks.py` to parse D2 (shared assertions). **Pilot: convert the Phase-2 L1 structural diagram to `.d2`** (highest legibility payoff, needs only recon, lowest blast radius, it's "the core artifact"). Update diagram-specialist Phase-2 prompt. Switch HTML to inline D2 SVG. | one diagram; Mermaid fallback intact | **T4** (D2 eval parser) |
| **3** | Convert the rest diagram-by-diagram behind their eval-parser support: L2–L4 → attack trees/flows → SBOM → sequence (**keep auth-sequence in Mermaid/PlantUML if native `alt`/failure fragments are required — D2 has no fragment primitive**). | one diagram at a time | **T4** per type; **T2/T3** for new types |
| **4** | Default all authoring to D2; move `mermaid-*.md` to a legacy note; regenerate committed worked-example as `.d2` twins (keep `.mmd` for back-compat); the renderer still accepts `.mmd` indefinitely. | full; reversible per-diagram | stages 2–3 done |

**Back-compat:** the extension-dispatching renderer accepts `.mmd` forever, so `docs/examples/…/*.mmd`
and `docs/diagrams/*.mmd` keep rendering; ARCHITECTURE.md PNG fallbacks keep working. Incremental beats
wholesale here precisely because the evals are reference-free properties (convert one, verify its
properties still hold) — a big-bang rewrite would strand every worked-example and can't be verified
piecewise.

---

## 5. Biggest integration risk & de-risking

**Risk:** *offline PNG rasterization in a headless / possibly air-gapped skill run.* If the renderer
needs a browser it can't get (locked-down box, no network to download Chromium) **or** the browser-free
path silently blanks multi-line threat-annotation labels, then docx/pdf/pptx get broken/empty diagrams
→ `verify_run.sh` FAILs (it requires PNG embeds) → the run has no deliverables.

**De-risk (in priority order):**
1. **HTML never needs the browser** — inline D2 SVG. The web report (the engineer-facing artifact) is
   full-fidelity offline regardless. This alone protects the most-used deliverable.
2. **Two-tier PNG with an explicit, tested fallback** (§3.2): cached-Chromium primary; resvg fallback
   with the *plain-single-line-label* authoring constraint enforced by the diagram-specialist prompt
   and checked by `diagram_checks.py` (reject `|md|`/multi-line labels when the resvg tier is active).
3. **Fail-loud preflight** (`ensure_renderer.sh` at pipeline start) so a missing renderer is a clear
   startup error, not a silent Step-2.5 failure five agents later.
4. **The bar is "no worse than today."** Status quo already needs network + Chromium; D2 SVG-for-HTML is
   a strict improvement and D2 cached-Chromium-for-PNG is parity. If a deployment genuinely forbids any
   browser *and* can't tolerate the plain-label constraint, **that deployment should have T1 pick
   Graphviz or PlantUML** (both do native, browser-free PNG) — surface this as T1's decision input.

---

## 6. Dependencies & what's blocked until T1/T4 land

- **Everything downstream of Stage 1 depends on T1's engine choice.** If T1 picks Graphviz/PlantUML
  instead of D2, §3.2's PNG story gets *easier* (native browser-free PNG) but §3.1/§4 are unchanged, and
  the HTML-inline-SVG win is smaller (uglier SVG). The phase-placement and staged-conversion design is
  engine-independent.
- **Stages 2–4 are blocked on T4** shipping the D2 (or chosen-engine) extractor in `diagram_checks.py`.
  No diagram converts before its property parser exists.
- **New-artifact placement (§3.1) depends on T2/T3** declaring each artifact's input set and precondition;
  the placement *rule* is ready now.

---

## Open questions

- Does the chosen engine's SVG rasterize faithfully through resvg for the *specific* label shapes T2/T3
  introduce (grids, tables-in-diagram)? Needs a one-sample end-to-end check per new artifact type before
  trusting the browser-free tier.
- Should the HTML report *drop PNG entirely* and inline SVG for all diagrams, leaving PNG only for
  docx/pdf/pptx? (Would simplify §3.2 tier-1 and remove a `verify_run.sh` assumption — but `verify_run.sh`
  currently asserts `<img>` PNG embeds in HTML; that check would need to accept inline `<svg>` too.)
- Is a self-hosted **Kroki** worth it as a single multi-DSL render service for teams already running
  Docker? It relocates (doesn't remove) the Mermaid Chromium into a companion container and adds a
  service to operate — likely over-engineered vs `d2 + resvg` for this CLI, but noted.
- Does moving multi-line threat annotations out of diagram labels (resvg tier) reduce the diagram's
  standalone legibility enough to matter, given the adjacent STRIDE/heat-map tables already carry the data?

```json
{
  "track": "t5-pipeline",
  "recommendations": [
    {
      "id": "T5-01",
      "title": "Extract rendering into an extension-dispatching render_diagrams.sh (the migration seam)",
      "summary": "Lift the report-analyst Step 2.5 render logic into a standalone script that dispatches by file extension (.mmd->mmdc, .d2->d2/resvg). Behavior-identical on day one; it's the seam that lets both engines coexist so diagrams convert one at a time.",
      "maps_to": "pipeline",
      "adoptability": 5,
      "impact": 3,
      "effort": 1,
      "risk": "low",
      "depends_on": [],
      "evidence": "Read report-analyst.md Step 2.5 (npx @mermaid-js/mermaid-cli, single hardcoded engine) and verify_run.sh (consumes PNGs). A dispatcher adds no new behavior for .mmd; confirmed no other production step renders diagrams.",
      "sources": []
    },
    {
      "id": "T5-02",
      "title": "Render engine SVG offline and inline it into the HTML report (kill the Mermaid CDN)",
      "summary": "D2 SVG is pure-Go and fully offline; inline it into report.html for crisp, zoomable, full-fidelity diagrams with no CDN and no runtime. Strictly better than status quo and satisfies verify_run.sh's existing 'no Mermaid CDN' ban.",
      "maps_to": "pipeline",
      "adoptability": 5,
      "impact": 4,
      "effort": 2,
      "risk": "low",
      "depends_on": ["T5-01"],
      "evidence": "Verified: D2 FAQ/docs confirm SVG needs no network after install and no browser. verify_run.sh already bans mermaid.js CDN and requires embeds; report-analyst.md 3.1 currently (contradictorily) specifies the CDN. Inline SVG resolves both.",
      "sources": ["https://d2lang.com/tour/exports/", "https://github.com/terrastruct/d2"]
    },
    {
      "id": "T5-03",
      "title": "Two-tier offline PNG for docx/pdf/pptx (cached headless Chromium primary; browser-free resvg fallback)",
      "summary": "Raster PNG is unavoidable for Office formats and required by verify_run.sh. Primary: d2-native PNG with a one-time-warmed, cached Playwright Chromium (offline after warm-up, no worse than today's mmdc). Fallback: d2->svg->resvg->png with a plain-single-line-label authoring constraint (resvg drops foreignObject that D2 uses for multi-line/markdown labels).",
      "maps_to": "pipeline",
      "adoptability": 3,
      "impact": 4,
      "effort": 3,
      "risk": "med",
      "depends_on": ["T5-01", "T5-02"],
      "evidence": "Adversarially verified: D2 PNG uses Playwright+Chromium (d2 #744); resvg/librsvg are static-SVG rasterizers that drop HTML foreignObject; D2 renders |md| and multi-line/wrapped labels as foreignObject (D2 troubleshoot doc). So browser-free PNG is real-but-constrained to plain-text labels. Current baseline mmdc already needs Chromium+network (mmdc #650), so the browser tier is parity, not regression.",
      "sources": ["https://github.com/terrastruct/d2/issues/744", "https://d2lang.com/tour/troubleshoot/", "https://github.com/linebender/resvg/blob/main/docs/unsupported.md", "https://github.com/mermaid-js/mermaid-cli/issues/650"]
    },
    {
      "id": "T5-04",
      "title": "Place new T2/T3 artifacts by input-set, respecting the existing dependency frontier",
      "summary": "Structural/topology artifacts -> Phase 2 (diagram-specialist); interaction-level pre-score (STRIDE-per-interaction, agent/auth sequence) -> Phase 3 (security-architect); risk-bearing/temporal (attack-defense trees, LASM overlay, ATT&CK/ATLAS layer, CVSS overlay) -> Phase 7 (diagram-specialist); tabular/JSON stay engine-neutral, no renderer. Each artifact's precondition-gated check goes in that phase's acceptance gate. No new blocking edges.",
      "maps_to": "pipeline",
      "adoptability": 5,
      "impact": 3,
      "effort": 2,
      "risk": "low",
      "depends_on": [],
      "evidence": "Mapped from SKILL.md phase graph: Phase 2 needs Phase 1; Phase 7 needs Phase 2 + 4/5/6. Mirrors how the existing auth-sequence (Phase 3) and attack-trees (Phase 5) and analytical visuals (Phase 7) are already placed. Placement is a rule; exact artifacts come from T2/T3.",
      "sources": []
    },
    {
      "id": "T5-05",
      "title": "Generalize diagram_checks.py to parse the new engine (per-engine extractor, shared reference-free assertions)",
      "summary": "Add a fence/extension engine detector routing to an engine-specific block/edge/container/class/stamp extractor while the property assertions (required layers, typed+annotated edges, boundary containers, ownership, L4<->TM-NNN link) stay identical and reference-free. Each diagram converts to D2 only after its parser lands — the green-throughout guarantee.",
      "maps_to": "eval",
      "adoptability": 4,
      "impact": 4,
      "effort": 3,
      "risk": "med",
      "depends_on": ["T5-01"],
      "evidence": "diagram_checks.py is Mermaid-regex-coupled (```mermaid, -->, subgraph, classDef, %% Version:) but its checks are properties, not answer keys; run.py:155-166 confirms diagram defects are ADVISORY in the blocking gate, so this can land without gate risk. D2 emits real class= attrs and containers map to subgraph zones. This is really a T4 deliverable.",
      "sources": ["https://d2lang.com/tour/classes", "https://d2lang.com/tour/containers"]
    },
    {
      "id": "T5-06",
      "title": "Migrate incrementally: pilot L1 structural first, keep Mermaid an accepted input throughout",
      "summary": "Convert diagram-by-diagram starting with the Phase-2 L1 structural DFD (best legibility payoff, recon-only inputs, lowest blast radius). Keep auth-sequence in Mermaid/PlantUML if native alt/failure fragments are needed (D2 lacks a fragment primitive). The renderer accepts .mmd indefinitely so committed worked-example artifacts never break.",
      "maps_to": "pipeline",
      "adoptability": 5,
      "impact": 4,
      "effort": 3,
      "risk": "low",
      "depends_on": ["T5-02", "T5-05"],
      "evidence": "Reference-free property evals make piecewise conversion verifiable (convert one, check its properties). D2 covers all 8 artifact types but has no native AND/OR-gate or sequence alt/opt fragment (verified against D2 docs) -> keep those cases in Mermaid/PlantUML. Committed docs/examples/*.mmd + docs/diagrams/*.mmd stay valid via the dispatcher.",
      "sources": ["https://d2lang.com/tour/sequence-diagrams", "https://d2lang.com/tour/containers"]
    },
    {
      "id": "T5-07",
      "title": "Package the renderer with a fail-loud preflight and an air-gap story",
      "summary": "Add scripts/ensure_renderer.sh run at pipeline start: install d2 (release binary/brew/curl) + resvg + warm/cache Chromium for the PNG primary tier; fail loudly if absent. Air-gap: vendor the static binaries + a pre-warmed browser cache + local icon set + Source Sans Pro; reference icons by local path (never remote URLs); pin dagre/ELK layout (free/offline/deterministic), never TALA (proprietary, watermarked).",
      "maps_to": "pipeline",
      "adoptability": 4,
      "impact": 3,
      "effort": 2,
      "risk": "med",
      "depends_on": ["T5-01", "T5-03"],
      "evidence": "Verified on this host: fresh run has no d2/dot/mmdc installed (only node/npx/java) -> a preflight is mandatory. Verified: D2 remote icon: URLs and TALA layout need network/license; dagre+ELK ship free and offline in the OSS binary; resvg is a single static Rust binary.",
      "sources": ["https://d2lang.com/tour/icons", "https://d2lang.com/tour/layouts", "https://github.com/terrastruct/TALA", "https://github.com/linebender/resvg"]
    }
  ],
  "open_questions": [
    "Does the chosen engine's SVG rasterize faithfully through resvg for the specific label shapes T2/T3 add (in-diagram grids/tables)? One-sample end-to-end check needed per new artifact type.",
    "Should the HTML report inline SVG for ALL diagrams and reserve PNG for docx/pdf/pptx only? verify_run.sh currently asserts <img> PNG embeds in HTML and would need to also accept inline <svg>.",
    "Is a self-hosted Kroki multi-DSL render service worth the operational weight for Docker-running teams, or is d2+resvg sufficient (Kroki relocates rather than removes the Mermaid Chromium)?",
    "If T1 picks Graphviz/PlantUML instead of D2, PNG gets easier (native browser-free) but the HTML-inline-SVG aesthetic win shrinks — confirm T1's choice before committing the rasterizer tier."
  ],
  "poc_results": null
}
```
