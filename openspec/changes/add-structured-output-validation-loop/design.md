## Approach

Two layers, cleanly split: **structure** (the schema, mechanical) and **semantics** (the validation
loop, application code). Both run post-hoc because an agent writes the manifests as files — there is no
constrained decoding to lean on.

### Structure layer — `schema_checks.py` (stdlib, no new dependency)

A ~90-line validator interprets exactly the JSON-Schema keywords the three schemas use: `type`
(including `["x","null"]` unions), `required`, `properties`, `additionalProperties:false`, `items`,
`enum`, `pattern` (full match), `minimum`/`maximum`, `minItems`, and local `$ref` to `#/$defs`. The
`schema/*.json` become load-bearing: `checks.py` (recon + findings) and `coverage_checks.py` (the
ledger) call it first and emit `schema-violation` defects, so the schema is the authoritative
*structural* contract. `checks.py` keeps a thin layer of consistency/semantic checks the schema cannot
express (`severity == band(L×I)`, `out-of-range-LxI` domain guard before `band()`, count agreement,
kill-chain referential integrity, `detected_pattern == other ⇒ detail`); these run over the
now-schema-validated structure rather than re-deriving it. The schemas are tightened to match the contract
they always implied: `additionalProperties:false`, `^TM-[0-9]{3}$` / `^KC[0-9]+$` id patterns, 1–5
bounds, enum domains, and — the nullable pattern — `["string","null"]` / `["array","null"]` on the
optional fields a source may legitimately lack (recon `description`/`tech`/`manifest`/`risk`/
`detected_pattern_detail`, findings `cwe`/`mitre`), plus an `unknown` enum and an `other`(+detail)
escape hatch on `detected_pattern`.

### Semantic layer — `checks.py` / `coverage_checks.py`

Logic constraints the schema cannot express, recomputed independently over the emitted facts:
`severity == band(likelihood × impact)` on the authoritative band, `summary_counts` vs tally,
ref-resolves-to-recon-id, kill-chain-step-resolves-to-finding, recon evidence resolves in the repo, a
1–5 domain guard before `band()`, and `detected_pattern == other ⇒ detail` (the conditional-requirement
pattern, mirroring coverage's `present ⇒ source`). The eval recomputes the band rather than trusting a
self-reported "matches" flag — correct for an *independent* checker.

### The gate — `run.py validate` + the orchestrator + the plugin hook

`run.py validate --run <dir> [--repo <path>]` gates on structure + consistency + coverage (grounding
when `--repo` given), routes diagram/report defects to advisory, and exits non-zero with one
`DEFECT field: constraint: actual-vs-expected` line per issue. In the production flow the **parent
orchestrator** runs it after the analysis agent and before the report-analyst, and re-spawns the agent
with those lines on failure (SKILL.md "Manifest Validation Gate"). When installed as a **plugin**, a
`PreToolUse` hook (`hooks/validate_gate.py`) runs the same command and **denies** the report-analyst
spawn on failure, feeding the defects back as the denial reason — moving enforcement from the agent's
goodwill into the harness. The hook is self-scoped (no-op for non-report tool calls) and fail-open on
infrastructure errors. Path via `${CLAUDE_PLUGIN_ROOT}`; agents flattened to `agents/*.md` for plugin
auto-discovery.

### Judge integrity

`run.py` distinguishes a malformed/incomplete judge output (recorded as an integrity defect that blocks
a green verdict, surfaced in `report.py`) from an absent one (a legitimate deterministic-only run) — no
silent degradation.

## Determinism boundary

Deterministic: the schema validation, `band()`, count/ref/kill-chain consistency, grounding resolution,
the gate's exit code, and — when a plugin — the hook's deny/allow. None of these calls a model; same
`(manifests, repo)` → byte-identical defects. Non-deterministic: the agents (recon, threats, the
manifests, the parent's decision to run the gate and act on it). The gate **re-spawns** the agent to
fix; it never edits the answer in code. The nullable/`unknown`/`other` paths exist so honest absence is
representable without fabrication — the eval enforces *honesty + grounding + internal consistency*,
never the presence of any particular content.

## Notes / risks

- The schemas combined carry 25 optional and 7 union-type params; the 7 union-types stay under
  the 16-union structured-output ceiling, and the 25 optionals only matter *if* the three were ever one
  strict API request — they are not (each agent emits its own manifest, which is the standard "split
  across subagents" remedy). This bounds how many nullable unions may be added later.
- The hook is the hard gate; the SKILL.md instruction is the soft gate. Both invoke the identical
  `run.py validate`, so behavior matches whether or not the plugin is installed.
- The committed `sample-runs/` predate `coverage.json`; the schema/consistency layers stay green on all
  of them, and the band scheme they used is consistent with the unified Scheme A at every score.
- Frozen `sample-runs/*/report.md` are left unedited as historical run evidence; only normative content
  was migrated to the single band scheme.
