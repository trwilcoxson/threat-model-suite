# Visual-engine research program — 2026-07

Investigates how to make the suite's diagrams (a) look better / more legible with distinguishable
per-type icons and clean trust boundaries, (b) carry the cyber-relevant visual artifacts a mature threat
model surfaces, (c) stay consistent under reference-free evals without constraining the model's reasoning,
and (d) adopt the right elements from the 2024–2026 LLM/agentic-threat-modeling literature.

## Contents
- **[ROADMAP.md](ROADMAP.md)** — the ranked 13-workstream roadmap: 6 designed now, 7 deferred, 6 dropped.
- **reports/** — the 5 research-track reports (engine, missing artifacts, framework integration,
  reference-free evals, pipeline integration), each produced by a sub-agent team with web research +
  adversarial verification.
- **poc/** — the rendered bake-off of the flagship ECS structural diagram:
  `00-baseline-mermaid.png` (today) vs `01-d2-structural.png` (**recommended engine**) vs
  `02-plantuml-c4-structural.png` (rejected alternate); plus the `.d2`/`.puml` source.
- **[DRAWIO-EVAL.md](DRAWIO-EVAL.md)** — draw.io / mxGraph evaluated as a diagram engine (verdict inside).
- **[OTM-EVAL.md](OTM-EVAL.md)** — Open Threat Model evaluated as a semantic source (verdict: not adopted;
  it pointed to the `recon.json` + `dataflows[]` approach instead).
- **[SEMANTIC-SOURCE-SPIKE.md](SEMANTIC-SOURCE-SPIKE.md)** — the `recon.json` + `dataflows[]` → deterministic
  `recon→D2` spike (rendered proof + the regex→JSON check-replacement table).

## The proposals (this branch)
`openspec/changes/`: `modernize-visual-engine`, `add-offline-render-pipeline`,
`add-cvss-decomposed-likelihood`, `add-ai-ml-attack-surface`, `add-boundary-crossing-stride-matrix`,
`add-control-coverage-matrix` (plus `add-semantic-source-diagram`, formalized later from the OTM spike).
All pass `openspec validate --strict`. **Implemented on this branch** — the four additive changes fully;
the engine pair (`modernize-visual-engine` + `add-offline-render-pipeline`) eval-side, with
D2-binary/icon-asset vendoring + diagram migration tracked in their `tasks.md`. See
[`openspec/README.md`](../../../openspec/README.md) for per-change status.
