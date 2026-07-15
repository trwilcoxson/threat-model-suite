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

## The six proposals (this branch)
`openspec/changes/`: `modernize-visual-engine`, `add-offline-render-pipeline`,
`add-cvss-decomposed-likelihood`, `add-ai-ml-attack-surface`, `add-boundary-crossing-stride-matrix`,
`add-control-coverage-matrix`. All pass `openspec validate --strict`. **Design proposals only — no
implementation.** Review, then approve the ones to build.
