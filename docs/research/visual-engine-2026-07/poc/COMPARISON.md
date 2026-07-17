# POC — flagship structural diagram re-rendered across engines

Same threat model (`amazon-ecs-fullstack-app-terraform`, L1 structural DFD, 25 nodes,
26 typed flows, 3 nested trust zones) authored **as code** in each engine and rendered
**offline** to PNG. The D2 and PlantUML sources are in this directory; the Mermaid baseline is
the committed flagship source at `docs/examples/amazon-ecs-fullstack-app-terraform/structural-diagram.mmd`.

| # | Image | Engine | Source | Render path | 1-line aesthetic verdict |
|---|-------|--------|--------|-------------|--------------------------|
| 00 | `00-baseline-mermaid.png` | **Mermaid** (current) | `docs/examples/amazon-ecs-fullstack-app-terraform/structural-diagram.mmd` | `mmdc` (existing) | Legible but **monochrome** — node *type* shown only by grey/blue box shape+fill; you must read every label to tell an ALB from an ECS task from DynamoDB, and trust boundaries are near-invisible flat-grey rectangles with tiny corner labels. This is exactly the "muddy" the owner described. |
| 01 | `01-d2-structural.png` | **D2** (elk layout, theme 4) | `structural.d2` | `d2` CLI (icons inlined) | **Clearest of the set.** Distinct AWS icon per node type (ELB / ECS / CodePipeline / DynamoDB / S3 / ECR / CloudWatch / SNS / VPC), `person` actors, `cylinder` datastores; **tinted, dashed nested trust zones** (purple CI/CD, blue VPC, orange private-subnet, blue public-subnet) read instantly as security zones; edges **colored by semantic type** (orange=build, red=admin, green=async, dashed=control). Best node-type-by-icon distinction + cleanest boundaries. |
| 02 | `02-plantuml-c4-structural.png` | **PlantUML + C4 + logos sprites** | `structural.puml` | `plantuml` (jar, offline) | Most **corporate-polished**: rich brand/service logos (GitHub, Docker, Terraform, Node.js, CodePipeline, DynamoDB, S3, ECS), C4's clean blue containers, colored dashed nested boundaries **and a built-in legend**. Weakness visible: `dot` routing produces sweeping cross-diagram edges + some label overlap on this dense graph. |
| 03 | `03-d2-offline-localicons.png` | **D2 (offline proof)** | `offline.d2` + `skills/threat-model/references/icons/*.svg` | `d2` CLI, **network blocked** | Adversarial-verification artifact: rendered in 140 ms with `HTTP(S)_PROXY` pointed at a dead port, using the **local vendored** icon set at `skills/threat-model/references/icons/*.svg` (referenced from `offline.d2` by relative path). All icons inlined as base64 → confirms D2 produces a self-contained, fully-offline typed-icon render with zero network. |

## Which engine best distinguishes node types by icon?
**D2 and PlantUML both decisively beat the Mermaid baseline** — each gives a distinct, controlled
icon per node *type*. D2 wins on **overall legibility** (colored semantic edges + cleaner elk layout +
crisply tinted nested boundaries); PlantUML wins on **icon/brand fidelity + a free auto-legend** but
loses on dense-graph edge routing.

## Verified engine facts (hands-on, this session)
- **D2**: `brew`-installed single Go binary v0.7.1 (MPL-2.0). Local-file `icon:` paths are **read and
  inlined into the SVG at render time** → hermetic offline output (proven with network blocked, #03).
  Remote icon URLs are fetched at render time and **silently produce a broken icon + exit 0** on a 403
  (I hit a real 403 on one AWS path) → *vendor icons locally, never reference remote URLs*.
- **PlantUML**: `brew`-installed (pulls Java + Graphviz). C4 + AWS/`logos` sprite libraries are
  **bundled in the jar** and render with **zero network**. Full 25-node C4 diagram rendered locally in
  ~2 s. `dot` layout is the weak point on dense graphs (confirmed: sweeping edges above).
- **Kroki public API** (`kroki.io`): renders D2 / PlantUML / Graphviz / Structurizr / Mermaid, but
  (a) **rate-limits / 400s under load** — the *same* valid source flipped 200→400 within seconds, so
  it is **POC-grade, not a production render path**; and (b) being **stateless it cannot see local
  icon files** — D2 local-path icons never reach it, and its 5 s D2 command-timeout is blown by ~20
  server-side icon fetches. Self-hosted Kroki fixes rate-limits and works great for PlantUML (bundled
  sprites) but still can't do D2 local icons (needs data-URI inlining) — so **for D2, shell out to the
  D2 CLI directly**.
