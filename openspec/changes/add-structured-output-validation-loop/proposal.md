## Why

The skill emits three machine-readable manifests (`recon.json`, `findings.json`, `coverage.json`) as
files, and the eval validates them. But the structural contract was only *partly* real: the
`schema/*.json` files were **dead documentation** — no code applied them, so id patterns, 1–5 bounds,
enum domains, and stray-field rules went unenforced and `checks.py` hand-rolled a drifting subset.
Worse, the contract was **internally inconsistent**: the skill documented one OWASP band scheme
(`CRIT 20-25 / HIGH 12-19 / …`) while the eval enforced another (`CRIT 17-25 / …`), so a faithful run
could be flagged for a `severity == band(L×I)` "mismatch" that was really a documentation bug. And the
**validation loop existed only offline**: nothing ran the deterministic checks *in the production
flow*, so the analytical manifests were never gated before report generation.

This is the standard structured-output failure mode (mapped pattern-by-pattern in
[docs/STRUCTURED-OUTPUT-CONTRACT.md](../../../docs/STRUCTURED-OUTPUT-CONTRACT.md)): structural compliance
is not semantic correctness, and a reliable structured-output system needs (a) the schema enforced,
(b) room to say "absent" instead of fabricating, and (c) a validate → retry-with-specific-feedback loop
run by application code. This suite is a Claude Code flow, not an SDK app, so those map to **post-hoc
schema validation** and a **parent-orchestrated (or hook-enforced) gate**.

## What Changes

- The `schema/*.json` files become **load-bearing**: a dependency-free validator (`schema_checks.py`)
  validates each manifest against its schema (id patterns, 1–5 bounds, enum domains,
  `additionalProperties:false`) as the structure layer; `checks.py`/`coverage_checks.py` keep the
  semantic layer (consistency, grounding, coverage) over the now-validated structure.
- **Room for absent data, never fabrication**: optional may-be-absent fields accept explicit `null`
  as well as omission; ambiguity has the `unknown` enum (+ note); closed categorization has
  `other` (+ detail). Honest absence never forces an invented value.
- **One authoritative severity band** (`LOW 1-4 / MEDIUM 5-9 / HIGH 10-16 / CRITICAL 17-25`, from
  `frameworks.md` and the eval) used identically across all three skills, both agent definitions, and
  the docs — removing the contradiction the consistency check would otherwise flag.
- **Referential integrity + judge integrity**: kill-chain steps SHALL resolve to real findings; a
  malformed/incomplete agent-judged layer SHALL be recorded and prevent a clean verdict (no silent cap).
- A **Manifest Validation Gate** runs the deterministic validator in-flow: the orchestrator validates
  the manifests after the analysis agent and before report generation, re-spawns the agent with the
  specific defects on failure, and routes information genuinely absent from the source to
  `null`/`unknown`/`no_issue_surface`/Open Questions rather than retrying. When the suite is installed
  as a **plugin**, a `PreToolUse` hook enforces the gate deterministically (denies report generation
  until the manifests pass); absent the plugin the orchestrator enforces the same check.

The boundary holds: the validator is deterministic structure-checking over emitted facts; the agents
do all reasoning and generation; the gate re-spawns the agent (it never edits the answer in code).

## Capabilities

### New Capabilities
- `structured-output-contract`: the manifests' structural + consistency contract — post-hoc
  JSON-Schema validation (the file-based analog of strict tool decoding), nullable/`unknown`/`other`
  absence handling, the single authoritative band, internal consistency and referential integrity,
  and judge-output integrity.
- `manifest-validation-gate`: the in-flow validate → retry-with-specific-feedback loop — proactive
  agent self-check, the orchestrator-run (soft) gate, the plugin `PreToolUse` hard gate, and
  not-retryable routing of absent information.

### Modified Capabilities
<!-- composes with completeness-coverage / coverage-verification (coverage.json now also schema-validated)
     and diagram-verification; no requirement changes to them -->

## Impact

- New: `evals/reliability/schema_checks.py` (the validator), `evals/reliability/run.py validate`
  (the gate CLI), `hooks/hooks.json` + `hooks/validate_gate.py` (the plugin hook),
  `.claude-plugin/plugin.json` + `marketplace.json`, `docs/STRUCTURED-OUTPUT-CONTRACT.md`.
- Modified: `schema/{recon,findings,coverage}.schema.json` (load-bearing, `additionalProperties`,
  nullable fields, `detected_pattern`); `checks.py`/`coverage_checks.py` (wire the validator, bound
  L/I, kill-chain refs, `other`-detail); `run.py`/`report.py` (judge-output integrity);
  `SKILL.md`/`agent-prompts.md`/`executor.md` (emit the manifests, Pre-Emit Self-Check, the gate);
  the OWASP band scheme across all three skills + both agent definitions + docs; `agents/` flattened
  to `agents/*.md` for plugin auto-discovery.
