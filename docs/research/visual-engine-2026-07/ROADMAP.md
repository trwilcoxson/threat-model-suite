# Visual-engine & threat-model-content roadmap (2026-07)

A research program (5 parallel tracks, each with its own sub-agent team + adversarial verification) fed a
3-lens triage panel that deduped ~40 cross-track recommendations into **13 ranked workstreams**. This
is the output. Six are drafted as openspec change proposals in `openspec/changes/` (this branch); seven
are deferred with explicit dependencies; six recommendations were dropped.

The whole program holds the suite's **determinism boundary**: agents do all reasoning and generation;
every eval added below checks *properties over the model's own emitted facts* (well-formedness, grounding,
internal consistency, coverage ratios over the model's own recon) and always permits honest abstention —
never an answer key, never content inference in code.

## The engine decision (settled by a rendered bake-off)
The T1 track rendered the flagship ECS structural diagram in Mermaid (baseline), **D2**, and PlantUML-C4
(`poc/`). **D2 (Terrastruct) is the flagship pick** — typed per-node-type icons, nested colored trust
boundaries, declarative as-code form, offline pure-Go SVG. **Mermaid `@{shape: icon}` + ELK layout** is
the zero-eval-change phase-1 legibility win (kept as an accepted input throughout migration). PlantUML-C4
and self-hosted Kroki were evaluated and **rejected** (D2 won on typed icons + nested boundaries; Kroki's
stateless server can't read the vendored local icon set the icon-rich path needs).

## Designed now (rank 1–6 · `openspec/changes/`)

| # | Change | I/E/risk | Core |
|---|--------|----------|------|
| 1 | `modernize-visual-engine` | 5/4/med | D2 flagship + Mermaid-icon phase-1; controlled node-type→icon vocabulary as a *grounding* check; generalize `diagram_checks.py` into a per-engine extractor feeding the **unchanged** property assertions |
| 2 | `add-offline-render-pipeline` | 4/3/med | extension-dispatching render seam; inline offline D2 SVG into the HTML report (kills the Mermaid CDN); two-tier PNG (cached Chromium → browser-free resvg) with a **fail-loud** air-gap preflight; incremental migration |
| 3 | `add-cvss-decomposed-likelihood` | 5/2/low | emit an AV/AC/PR/UI vector behind Likelihood; ~15-line eval recomputes `8.22·AV·AC·PR·UI` over the finding's **own** vector and checks its **own** 1–5 band (same family as `severity==band(L×I)`) |
| 4 | `add-ai-ml-attack-surface` | 4/2/low | MITRE ATLAS Navigator layer (reuses the ATT&CK emitter, gated on existing `has_ai_ml`) + OWASP-LLM Top-10 checklist projected onto it; ATLAS/OWASP-LLM as prompt taxonomies; fixed-vocabulary id guardrail |
| 5 | `add-boundary-crossing-stride-matrix` | 4/2/low | STRIDE-per-interaction over trust-boundary-crossing DFD edges (no new manifest fields); coverage property = every crossing edge → one decided row; validity left to the judge |
| 6 | `add-control-coverage-matrix` | 4/2/low | promote free-text remediation into addressable control objects (`controls:[{id,counters}]`); threat→control matrix flags zero-control findings; the shared schema enabler for attack-defense-tree counter-edges |

## Deferred (rank 7–13 · next / later)

| # | Workstream | Tier | Depends on | Why deferred |
|---|-----------|------|-----------|--------------|
| 7 | `add-attack-defense-trees` (defense nodes + counter-edges + CVSS metric-transform + goal anchoring + eval) | next | cvss, control-coverage, engine | wants the CVSS vector + control-object schema + the migrated tree renderer first |
| 8 | `add-agentic-threat-coverage` (Berkeley R1–R7 recon detector → OWASP ASI01-10 coverage partition + agent-trust DFD overlay) | next | ai-ml-attack-surface, engine | needs a new agentic detector + gate machinery; payoff is agentic-only |
| 9 | `add-reference-free-coverage-metrics` (coverage-as-ratio panel, finding well-formedness, heat-map `cell==band(L×I)`, cross-artifact HIGH+ meta-check) | next | ai-ml, attack-defense-trees, agentic | the meta-check needs the new artifacts to exist first |
| 10 | `add-lifecycle-temporal-coverage` (`temporal_class` enum + per-lifecycle-class resolution check) | next | — | LASM's one clean extraction; promotable single-enum fast-follow |
| 11 | `add-linddun-privacy-matrix` (LINDDUN-per-element matrix + GenAI privacy lenses + eval) | later | — | **blocked**: resolve ownership with the sibling `privacy-impact-assessment` skill (it already owns LINDDUN) before building, or ship duplication |
| 12 | `add-residual-risk-burndown` (inherent→residual view; ships only the `residual≤inherent` monotonicity check) | later | control-coverage | weakest additive, biggest single schema add, only the monotonicity is reference-free |
| 13 | `refine-framework-hygiene` (namespace layer stamps so `_layer_of` can't misread; Shostack 4-Questions persona framing) | later | — | two effort-1 fold-ins for the nearest proposal |

## Dropped (with reason)
- **T1-03 PlantUML+C4 alternate engine** — D2 decisively won the bake-off on typed icons, nested boundaries, declarative form.
- **T1-04 self-hosted Kroki** — wrong substrate for the icon-rich D2 path (stateless server can't read local vendored icons).
- **T2-08 LASM 7-layer × 4-temporality matrix** — its one genuine axis (temporality) is captured cheaply and codebase-agnostically by workstream 10; the full grid is experimental/agentic-only.
- **T4-06 LASM grid well-formedness eval** — existed only to validate T2-08's tags; nothing left to check once T2-08 is dropped.
- **T4-05 STRIDE-per-element applicability warning** — the boundary-closest check in the corpus; it second-guesses the model's own applicability reasoning → **would violate the determinism boundary**.
- **T4-10 SAND temporal-ordering DAG acyclicity** — validates an ordered/sequential-AND artifact no kept workstream emits.

## Method
Research reports per track are in `reports/`. The rendered POC is in `poc/` (baseline Mermaid vs D2 vs
PlantUML-C4). Each design proposal in `openspec/changes/<name>/` was adversarially reviewed for the
determinism boundary and openspec format; one boundary blocker (a "faithful projection" content-judgment
in the boundary-crossing matrix) was caught and corrected to pure id-grounding before commit.
