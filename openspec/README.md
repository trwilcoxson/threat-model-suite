# OpenSpec — design & specification

This directory is the **spec-first design** of the threat-model skill and its evaluation harness,
using [OpenSpec](https://github.com/Fission-AI/OpenSpec). Each capability is specified as
`Requirement`s with `Scenario`s (WHEN/THEN) before it is built, so the design is auditable and the
intent is explicit.

## The principle (every capability obeys it)

> The LLM/agents do **all reasoning and generation** — every threat, every visual, every event
> payload. **Determinism lives only in the templates and evals**, to enforce that the structure is
> present and internally consistent (the same *kind* of result each run). Deterministic code never
> scripts or judges the answer.

A recurring corollary: when the eval needs to gate on something, the **skill emits the fact** as a
neutral structured field (declared kill chains, trust-boundary kind, dependency manifest, coverage
state) and the eval checks structure over that fact — it never infers content in code.

## Changes

| Change | Capabilities | Status |
|---|---|---|
| [`add-product-grade-diagrams`](changes/add-product-grade-diagrams/) | `threat-model-visuals`, `diagram-verification` | implemented + verified |
| [`add-pipeline-observability`](changes/add-pipeline-observability/) | `pipeline-observability` | implemented + verified |
| [`add-coverage-ledger`](changes/add-coverage-ledger/) | `completeness-coverage`, `coverage-verification` | implemented (live verification pending) |
| [`add-structured-output-validation-loop`](changes/add-structured-output-validation-loop/) | `structured-output-contract`, `manifest-validation-gate` | implemented + verified |
| [`modernize-orchestration`](changes/modernize-orchestration/) | `pipeline-orchestration` | implemented (live verification pending) |
| [`refine-pipeline-flow`](changes/refine-pipeline-flow/) | `assessment-flow` | implemented (live verification pending) |
| [`harden-eval-determinism-boundary`](changes/harden-eval-determinism-boundary/) | `eval-determinism` | implemented + verified |
| [`correct-reference-data`](changes/correct-reference-data/) | `reference-fidelity` | implemented |

Each change folder has `proposal.md` (why/what), `specs/<capability>/spec.md` (the
ADDED/MODIFIED requirement deltas), `design.md` (technical approach + the determinism boundary), and
`tasks.md` (implementation checklist with status).

## Capability map

- **threat-model-visuals** — the visuals the skill renders (the 8 product-grade additions + the DFD
  layers), each gated by a precondition, plus the neutral facts the skill emits for verification.
- **diagram-verification** — the deterministic, structure-only checks per visual (presence / shape /
  consistency against the manifests) and the diagram judge's correctness assessment.
- **pipeline-observability** — the `tm.run-event/1` stream (a projection of each persona's Execution
  Log) and the pure `tm-observe` renderer ("what agent is doing what").
- **completeness-coverage** — the coverage taxonomy + ledger: agents attempt every applicable
  production-grade item and record `present(+source)` / `partial` / `absent` / `not-applicable` /
  `unknown(+note)`; unknowns surface as open questions.
- **coverage-verification** — structure-only checks that every applicable item reached a terminal
  state (the agent tried), `present` is grounded, `unknown` is noted; never requires a specific item
  present.
- **structured-output-contract** — the manifests' structural + consistency contract: post-hoc
  JSON-Schema validation (the file-based analog of strict tool decoding), nullable/`unknown`/`other`
  handling so absent data is never fabricated, the single authoritative OWASP band, internal
  consistency + referential integrity over emitted facts, and judge-output integrity (no silent caps).
- **manifest-validation-gate** — the in-flow validate → retry-with-specific-feedback loop: the agent's
  pre-emit self-check, the orchestrator-run soft gate and the plugin `PreToolUse` hard gate, and the
  routing of information genuinely absent from the source (to `null`/`unknown`/Open Questions) instead
  of a retry.

## Working with it

```bash
openspec list                              # active changes + task progress
openspec view                              # interactive dashboard
openspec show add-product-grade-diagrams   # a proposal + its spec deltas
openspec validate <change> --strict        # validate a change
openspec archive <change>                  # after merge: fold deltas into specs/
```

Implementation lives in `../skills/threat-model/` (the skill: `SKILL.md` + `references/`) and
`../skills/threat-model/evals/reliability/` (the harness: `diagram_checks.py`, `events.py`,
`tm_observe.py`, `coverage_checks.py`, schemas, prompts, `sample-runs/`).
