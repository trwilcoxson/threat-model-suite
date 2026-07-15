# draw.io / diagrams.net — evaluated against the D2 pick

The T1 engine bake-off did not include draw.io (diagrams.net). This is that evaluation, run on the
**same 7-axis rubric**, hands-on (five real headless renders of the flagship ECS structural diagram),
with two opposing verifiers (one mandated to steelman draw.io, one to stress-test it) to keep the call
honest. **Verdict: draw.io is a genuine contender, not a reject — but it does not dislodge D2.**

## Scorecard (draw.io ~28/35 · D2 ~32/35)

| Axis | draw.io | D2 | Note |
|------|:---:|:---:|------|
| as-code | 3 | 5 | Native `.drawio` is geometry-positional XML (manual layout). A real declarative path exists — CSV / Mermaid import with `--layout` ELK — but it's a constrained import DSL, not a purpose-built grammar. |
| offline render | 4 | 5 | **Proven air-gap capable** (`--network none`, icons as inline vectors) — but via a ~2 GB Electron/Chromium image that crashed until `--shm-size=2g --no-sandbox`, vs D2's single ~30 MB Go binary. |
| typed icons / type | 5 | 5 | **Best-in-class**: ~10,000 bundled official AWS/Azure/GCP/k8s stencils offline; equal-or-better fidelity than D2's Terrastruct set. |
| trust-boundary rendering | 5 | 4 | **Richer than D2** — named AWS group stencils with corner icons, cleanly nested colored containers. |
| autolayout quality | 3 | 4 | ELK/tree/organic exist headlessly but are **not container-aware** — `organic` overflowed the trust zones, tree distorted the DFD; only the boundary-less CSV render was clean. |
| determinism fit | 3 | 4 | The decisive axis (see the crux). |
| license | 5 | 5 | Apache-2.0 tool; same AWS-icon trademark caveat as D2/PlantUML (a wash). |

## The crux (rendered — see `poc/`)
No single **agent-authorable** draw.io source delivers all four things the threat-model diagram needs at
once — typed icons, nested colored trust boundaries, per-edge typed/annotated labels, and clean
auto-layout:

- **`poc/03-drawio-geometry.png`** — hand-authored geometry `.drawio`: gorgeous official AWS icons +
  richly nested colored boundaries + per-edge labels, **but** hand-placed nodes → tangled edges,
  colliding labels. Manual layout violates the "automatic layout, no human nudging" requirement.
- **`poc/04-drawio-csv-autolayout.png`** — declarative CSV + `--layout elkLayered`, zero geometry: clean
  orthogonal auto-routing + typed icons, **but the trust boundaries are gone and edges carry no per-edge
  annotation** (`# connect:` styles a whole reference column, not per-edge).
- One path *does* unify all four — sparklabx `drawio-ai-kit` — via imperative JS that the agent runs to
  emit the diagram. It was first dismissed by analogy to the disqualified mingrammer `diagrams`; that
  analogy turned out to be wrong on the load-bearing point (see the postscript below) and the real reasons
  it stays behind D2 are different.

D2 delivers all four from **one declarative, auto-laid-out, parseable source** (`poc/01-d2-structural.png`).

## Why it stays #2 (and where the verifiers split)
Both verifiers agree **D2 stays flagship**. They split on draw.io's *tier*: the steelman lands on
"competitive alternate" (and correctly caught that CSV `# parent:`/`# parentstyle:` + `# layout:` *can*
combine boundaries+icons+autolayout in one source — though parent+layout is buggy in practice and per-edge
annotation still can't be expressed); the stress-test argues draw.io is arguably *below* the already-
rejected PlantUML by the bake-off's own determinism weighting, since PlantUML's single `.puml` carries all
four requirements at once (only its layout is messy) and draw.io's cannot, and draw.io has **no
Chromium-free render tier** — which `add-offline-render-pipeline` requires for air-gapped hosts.

Honest corrections surfaced (fairness both ways): the "30 MB vs 2 GB" gap is partly overstated for PNG
(D2 PNG also needs headless Chromium; D2's real edge is its Chromium-free SVG+resvg tier, which draw.io
lacks); the 28/35 is non-additive (icons=5 and boundaries=5 are only jointly reachable in the *manual*
render). The underlying standalone mxGraph library is also EOL since 2020 (only the app fork is maintained).

## Bottom line
**Keep D2 as flagship; record draw.io as a strong documented alternate.** If the suite ever reweights
toward icon/boundary fidelity over single-source determinism — and accepts either the CSV per-edge-annotation
limitation or an imperative generator — draw.io becomes the pick. On today's stated priorities (the
determinism boundary that drove the whole bake-off), D2 wins.

## Postscript — `drawio-ai-kit` evaluated properly (the analogy was lazy)

The first pass dismissed sparklabx `drawio-ai-kit` in one line as "imperative JS, disqualified like
mingrammer `diagrams`." On review that was reasoning from *input shape*, not tested. A dedicated
hands-on evaluation (cloned it, ran its 85 tests, generated a `.drawio`, ran its validator, and did a
tamper test) plus two opposing verifiers reached consensus:

**The analogy is false where it matters.** mingrammer `diagrams` was disqualified because its *only*
output is rendered pixels — "not declarative text a parser can validate." `drawio-ai-kit` emits a
declarative `.drawio` (mxGraph XML): containers = trust boundaries, `resIcon`/`grIcon` = node type, edge
cells carry `value=` labels + semantic style (`dashed=1`) = typed+annotated edges. It is at least as
property-checkable as Mermaid — proven: the kit's own `validateDiagram` caught an injected fake stencil id
(hard error + fuzzy suggestions) and a dangling edge target (warning) **without executing the source**.
So the eval boundary survives (agent generates content → pinned `renderTree()` auto-lays-out → the
deterministic layer checks the *emitted artifact*), and `drawio-ai-kit` genuinely delivers all four
requirements from one source. The det-fit score above (3) was therefore partly understated: it rested on
"the only all-four path is disqualified imperative execution," and that premise is wrong.

**D2 still stays flagship — but for these reasons, not the analogy:**
1. **Execution/injection surface** — producing the artifact requires the agent to author and *run*
   `node build.mjs`. For a tool that ingests untrusted target repos, that's a real
   prompt-injection→local-code-execution vector that pure-declarative D2/Mermaid (fixed sandboxed
   renderer) structurally lack. The kit's hardening secures the *kit*, not the agent-generated build script.
2. **No Chromium-free render tier** — PNG needs the draw.io Electron CLI; `add-offline-render-pipeline`
   requires a browser-free tier that D2's `d2→svg→resvg` meets. (Independent of `drawio-ai-kit`.)
3. **Maturity** — MIT, zero-dep, 85 tests, but ~4 weeks old, single-org, GitHub-not-npm; vendor-and-pin,
   don't hard-depend unpinned.

**Adoptable regardless of the engine choice:** `drawio-ai-kit`'s ground-truth **stencil catalog +
membership validator (`checkRef`, with fuzzy-match suggestions over the emitted artifact) is exactly the
T1-05 typed-icon grounding mechanism** `modernize-visual-engine` specifies — the same validation shape
(membership over emitted facts) ports directly to checking a D2 `icon:` field against a vendored catalog.
Recommend lifting the mechanism (and optionally the MIT catalog JSONs) into the suite independent of which
engine wins. And: rewrite any short-form dismissal to cite execution-surface + no-Chromium-free-render +
maturity, not "un-checkable imperative output."
