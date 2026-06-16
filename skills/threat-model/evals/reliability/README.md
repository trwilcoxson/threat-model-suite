# Reliability harness (reference-free, dynamic)

Validates that the threat-model flow is **reliable on whatever you point it at** — not that it
reproduces a fixed answer. There is no per-target ground truth. A target is just a real system
(`targets/<id>.yaml` = id + source + a local repo path supplied at runtime); adding one is adding
a file and cloning a repo. The system is run **N times** per target.

This supersedes the answer-key approach in `../cases/` + `../harness/` (fixed prompts with
hand-authored must-find lists). That approach forced answers — e.g. it recorded a correctly
reasoned MEDIUM(9) finding as a "miss" because the key demanded HIGH. Quality here is graded from
properties of `(target, output)` that hold for any good threat model, so it scales to any target.

## How quality is judged without an answer key

Five layers. The system emits, per run, `report.md` + three manifests (`recon.json`, `findings.json`,
`coverage.json`; see `schema/`, applied post-hoc by `schema_checks.py`). Everything below is derived
from those plus the real repo.

**Deterministic (the reliability contract — should hold on every run, any target):**
1. **Structure** — each manifest validates against its JSON-Schema (`schema/*.json` via
   `schema_checks.py`): required fields, `TM-NNN`/`KC` id patterns, Likelihood/Impact 1-5, enum
   domains, no stray properties; `report.md` has the template sections.
2. **Consistency** — `severity == band(likelihood × impact)`; `summary_counts` match the findings;
   `TM-NNN` cross-refs and `report.md`↔manifest counts agree; CWE/MITRE ids are well-formed.
3. **Grounding** — every recon element's `evidence` resolves in the actual repo (path/glob/string);
   every finding ref points to a real recon id. Catches invented components.
4. **Coverage** — every entry point / data store / trust boundary the system *itself* discovered is
   addressed by a finding or explicitly marked `no_issue_surface`. The denominator is the system's
   own recon, not a golden list.
5. **Diagram** (`diagram_checks.py`) — the threat-model diagram is the core artifact, so it is
   verified against the skill's own spec: required layers per scaling (L1-L4), every edge typed and
   annotated (protocol / sensitivity / `[ENC|PLAIN]`, spec §4), trust-boundary subgraphs, component
   ownership markers (§7), legend + version stamp (§6), and an L4 risk overlay linked to the findings
   (risk classes + threat annotations whose `TM-NNN` ids match, every HIGH+ finding's components
   present, §5). See [`sample-runs/DIAGRAM-FINDING.md`](sample-runs/DIAGRAM-FINDING.md) — adding this
   caught that all earlier runs produced under-built diagrams while passing every other check.

**Agent-judged (sampled, reference-free):**
5a. **Quality** (`quality-judge`) — is each attack path sound against the real repo, and is severity
    *defensible* (not equal to a target)? Is it proportionate (no padding, no invented components)?
5b. **Adversarial recall** (`red-team` → `gap-validator`) — an independent agent threat-models the
    same repo and surfaces HIGH+ risks the model missed; a second agent confirms each is grounded,
    uncovered, and material. This replaces hand-authored must-finds with gaps generated per target.
5c. **Recon completeness** (`recon-auditor`) — compares recon to the real repo so the coverage
    denominator can't be gamed by a recon that skipped a subsystem.
5d. **Diagram correctness** (`diagram-judge`) — beyond the deterministic presence checks, judges
    whether trust boundaries are placed right, flow annotations are accurate, and the L4 risk layer
    faithfully reflects the findings, against the real architecture.

**Stability:** across the N runs, the HIGH+ "core" is matched semantically and we report how much of
it is present in *every* run. Reliability = the crown jewels appear every time; breadth may vary.

## Structured output — where the contract lives

This flow is a Claude Code **skill**, not an SDK app, so the structured-output guarantees from the
Claude API have **file-based analogs** here rather than literal API features: the agents write the
manifests as files, and the contract is
enforced **post-hoc** instead of by constrained decoding.

| Claude-API mechanism | Analog in this flow |
| --- | --- |
| `strict:true` / `output_config.format` (constrained decoding) | agent writes `recon.json`/`findings.json`/`coverage.json` as files; `schema_checks.py` validates each against `schema/*.json` **after** generation (no constrained decoding when a model writes a file) |
| `tool_choice:"any"` (force a structured call, not prose) | the harness fails loudly on a missing manifest (`missing-artifact`); a prose-only run cannot pass |
| schema can't express conditional/semantic rules | `coverage_checks.py` enforces `present ⇒ source resolves`, `unknown ⇒ note`; `checks.py` enforces `severity == band(L×I)`, counts, ref integrity — the semantic layer over validated structure |
| nullable field so the model emits `null`, not a fabrication | coverage `state: unknown`/`absent`, `no_issue_surface[]` (examined-and-clean), optional `cwe`/`mitre` |
| `"unclear"` enum for ambiguous values | coverage `state` includes `unknown`; recon `detected_pattern` includes `unknown` + `other`(+detail) |
| self-correction field (emit *and* check in one pass) | the agent emits `likelihood`, `impact`, **and** `severity`; the eval **recomputes** `band(L×I)` independently rather than trusting an emitted "matches" flag (the right choice for an independent checker) |
| validate → **retry with specific feedback** loop | `run.py validate` prints one `DEFECT field: constraint: actual-vs-expected` line per issue; the parent re-spawns the analysis agent with those exact lines (SKILL.md "Manifest Validation Gate") |
| retries don't fix missing info → route, don't retry | a defect rooted in absent source data is recorded as `no_issue_surface` / coverage `unknown` / Open Question, not retried |

**Where "the application validates."** In an SDK app, deterministic application code wraps the model
call and runs the validate/retry loop. Here the **parent orchestrator** is that application code: it
runs `run.py validate` between agent spawns and re-spawns the failing agent with the specific defect
lines — the same loop, driven by the conversation + Bash instead of a Python `for`.

The full pattern-by-pattern map — every structured-output mechanism (including the API-level ones:
constrained decoding, streaming, property ordering, complexity limits) with a status and file evidence —
is in [`docs/STRUCTURED-OUTPUT-CONTRACT.md`](../../../../docs/STRUCTURED-OUTPUT-CONTRACT.md).

## Run it

```bash
cd skills/threat-model/evals/reliability
git clone --depth 1 https://github.com/OWASP/NodeGoat.git /tmp/nodegoat   # the target
# Run the skill N times on the repo (Executor prompt in prompts/executor.md), each emitting
# report.md + recon.json + findings.json into runs/<target>/run{1..N}/.
# Run the judged layers (quality-judge / red-team -> gap-validator / recon-auditor) into runs/<target>/agents/.
python3 run.py report --runs-root runs/nodegoat --repo /tmp/nodegoat \
    --target nodegoat --source https://github.com/OWASP/NodeGoat --out runs/nodegoat/reliability.html
```

`run.py check --run <dir> --repo <path>` runs just the deterministic layer on a single run.
`run.py validate --run <dir> [--repo <path>]` is the **production gate** the parent runs in-flow: it
validates the emitted manifests' structure + consistency (+ grounding when `--repo` is given) and
exits non-zero with one `DEFECT` line per issue for the orchestrator to act on (SKILL.md "Manifest
Validation Gate").

Committed real runs are under [`sample-runs/`](sample-runs/): NodeGoat (web app, with a multi-iteration
[improvement loop](sample-runs/nodegoat/improvements/LOOP-CLOSURE.md) — and the
[product-grade visuals verification](sample-runs/nodegoat/improvements/iteration-v5-product-grade/NOTE.md)),
TerraGoat (Terraform IaC), and crAPI (~900-file polyglot microservices + LLM agent) — same harness,
three different system types, no per-target tuning.

## Observability — `tm-observe`

Make the multi-agent run transparent. As personas run they emit a `tm.run-event/1` stream
(`events.ndjson`, a projection of each Execution Log); `tm_observe.py` renders an uncluttered
"what agent is doing what" view — pure function of the stream, same input → byte-identical output.

```bash
python3 run.py observe --transcripts <workflow-transcript-dir> --run <id> [--tree|--once]
python3 tm_observe.py events.ndjson [--tail|--tree|--once]
```

See [`../../references/pipeline-observability.md`](../../references/pipeline-observability.md).

## Coverage ledger

`coverage_checks.py` (per [`openspec/changes/add-coverage-ledger`](../../../../openspec/changes/add-coverage-ledger/))
validates the skill's `coverage.json` ledger against `schema/coverage.schema.json`, then checks it
structurally: every applicable production-grade taxonomy
item reached a terminal state (`present`/`partial`/`absent`/`not-applicable`/`unknown`), `present`
cites a resolving source, `unknown` carries a note — never requiring a specific item present.

## Design

The whole harness is specified in [`openspec/`](../../../../openspec/) — see its README for the
capability map and the determinism principle.
