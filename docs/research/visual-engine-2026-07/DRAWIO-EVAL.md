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
- The only path that unifies all four (sparklabx `drawio-ai-kit`) is **imperative JavaScript that must
  execute** — the exact pattern that got mingrammer `diagrams` disqualified in the T1 bake-off.

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
