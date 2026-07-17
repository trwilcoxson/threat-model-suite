# threat-model-suite

An agentic **security-assessment suite** for [Claude Code](https://docs.anthropic.com/en/docs/claude-code):
architectural threat modeling, privacy impact assessment, and compliance gap analysis, driven by a
pipeline of specialist agents and verified by a reference-free evaluation harness.

You point it at a real system; the agents reason about it and produce a full security review — threat
model with a product-grade diagram set, privacy and compliance assessments, prioritized findings, and
the artifacts a reviewer needs — while an evaluation harness checks that the output is reliable.

## Design & specification (OpenSpec)

The system is designed **spec-first** with [OpenSpec](https://github.com/Fission-AI/OpenSpec). The
whole design — what each capability must do, as `Requirement`/`Scenario` (WHEN/THEN) — lives in
[`openspec/`](openspec/) and is the front door for understanding it. Start there:

```bash
openspec list          # active change proposals + task status
openspec view          # interactive dashboard of specs and changes
openspec show <change> # a proposal + its spec deltas
```

One principle runs through every capability:

> **The LLM/agents do all reasoning and generation** — every threat, every visual, every event
> payload. **Determinism lives only in the templates and evals**, to enforce that the structure is
> present and internally consistent (the same *kind* of result each run) — never the answer. When the
> eval needs to gate on something, the skill **emits the fact** as a neutral structured field and the
> eval checks structure over it; it never infers content in code.

See [`openspec/README.md`](openspec/README.md) for the capability map.

## Components

```
openspec/    spec-first design (the front door)
skills/      the Claude Code skills
  threat-model/                SKILL.md + references/ + evals/   (the flagship)
  compliance-assessment/       compliance gap analysis (Team mode)
  privacy-impact-assessment/   DPIA / LINDDUN privacy analysis (Team mode)
agents/      the 7 pipeline personas (security-architect, diagram-specialist,
             privacy-agent, grc-agent, code-review-agent, validation-specialist,
             report-analyst) + 2 standalone companions (security-reviewer,
             code-quality-reviewer) invoked on their own, not by the pipeline
docs/        ARCHITECTURE.md, VALIDATION-PATTERNS.md, STRUCTURED-OUTPUT-CONTRACT.md, examples/
```

### threat-model — the flagship skill
- 8-phase methodology (reconnaissance → final report); **Solo** (threat model + report) or **Team**
  mode (adds privacy, compliance, code review agents).
- Mermaid DFDs (4-layer structural + risk overlay) **plus a product-grade visual suite**: attack
  trees, attack-flow/kill-chain graphs, auth sequences, STRIDE-per-element matrix, Likelihood×Impact
  risk heat map, MITRE ATT&CK technique layer, RBAC matrix, SBOM/dependency graph.
- A **coverage ledger** so the model attempts every production-grade item and records what it found,
  what's absent, and what it could not determine from the sources (gaps surfaced, not hidden).
- Output formats: HTML, Word (.docx), PDF, Executive PPTX.
- Opt-in **`dashboard.html`** — a single self-contained, offline analytics dashboard (no CDN/fonts): severity
  donut, L×I risk matrix, coverage ledger, STRIDE-LM/kill-chain/ATT&CK/CWE breakdowns, and the run's **own
  interactive structural diagram** (pan/zoom + click→cross-filter over the same threat model the report shows).
  Every number traces to the run's manifests; absent data degrades to graceful empty states. Produced only when
  `dashboard` is in the run plan; all other outputs are unchanged.

### agents
The pipeline the skill orchestrates. Each runs in a fresh context, writes a structured output file +
an Execution Log, and emits run events for observability.

### evals — reference-free reliability harness
`skills/threat-model/evals/reliability/` — point the skill at any real repo; no per-target answer key.
Deterministic layers enforce *structure* (report structure, consistency `severity == band(L×I)`,
grounding against the real repo, surface coverage, diagram verification of the 4 layers + 8 visuals).
LLM-judged layers assess *correctness* (reasoning quality, adversarial recall, recon completeness,
diagram correctness) and **cross-run stability**. A run-event stream powers `tm-observe` for an
uncluttered "what agent is doing what" view. Real runs across a web app, Terraform IaC, and a polyglot
microservices+LLM app are committed under
[`reliability/sample-runs/`](skills/threat-model/evals/reliability/sample-runs/).

## Install

### As a plugin (recommended — ships the deterministic hard gate)

The repo is a Claude Code plugin, so the skills, the specialist agents, and the **Manifest Validation
Gate** hook all install together and the hook activates immediately — no `settings.json` edit:

```text
/plugin marketplace add trwilcoxson/threat-model-suite
/plugin install threat-model-suite@threat-model-suite
```

(or, for a single-repo direct install: `/plugin install github:trwilcoxson/threat-model-suite`)

Then: `Run a threat model on <target>`.

**Step 0 — you pick the run.** Before anything spawns, the skill presents an explicit menu (MODE Solo/Team;
TEAM = any subset of privacy/grc/code-review; OUTPUTS = any subset of the six formats, dashboard and
analytical-visuals included) and **stops for your choice** — or you give a one-shot spec like
`team=privacy+code-review, outputs=dashboard+pdf`. Your confirmed pick is written to
`{output_dir}/run-plan.json`. The same `PreToolUse` hook enforces a **START gate**: the first pipeline spawn
is **denied until `run-plan.json` exists, validates, and is confirmed** (the deny reason carries the menu), so
there's no accidental full run. The rest of the run then spawns exactly the team and emits exactly the outputs
you planned.

Before the report is generated, the same hook
([`hooks/validate_gate.py`](hooks/validate_gate.py)) runs the deterministic validator over the emitted
`recon.json`/`findings.json`/`coverage.json` and **blocks report generation until they pass**, feeding
the specific defects back to the analysis agent to fix (the validate → retry-with-specific-feedback loop,
enforced by the harness rather than the agent's goodwill). See
[`docs/STRUCTURED-OUTPUT-CONTRACT.md`](docs/STRUCTURED-OUTPUT-CONTRACT.md).

### Manual (skill only — soft gate)

```bash
# Skills
for s in threat-model compliance-assessment privacy-impact-assessment; do
  cp -r skills/$s ~/.claude/skills/$s
done
# Agents (flat .md files)
mkdir -p ~/.claude/agents && cp agents/*.md ~/.claude/agents/
```
Then restart Claude Code. Run a threat model with: `Run a threat model on <target>`. Without the plugin
hook, the gate is the SKILL.md "Manifest Validation Gate" instruction (the parent runs `run.py validate`
and re-spawns on failure) — the same check, enforced by the orchestrator instead of the harness.

## License

MIT
