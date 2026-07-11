## 1. Structure layer (load-bearing schemas)

- [x] 1.1 Add `evals/reliability/schema_checks.py` (stdlib JSON-Schema subset: type incl. null-unions, required, properties, additionalProperties, items, enum, pattern, minimum/maximum, minItems, `$ref`)
- [x] 1.2 Wire it into `checks.py` (recon + findings) and `coverage_checks.py` (ledger) as the first structure gate; emit `schema-violation` defects
- [x] 1.3 Tighten `schema/{findings,recon}.schema.json`: `additionalProperties:false`, id patterns, 1–5 bounds; add recon `description`/`tech`/`detected_pattern`(+detail); `summary_counts` `minimum:0`
- [x] 1.4 Nullable pattern: `["string","null"]` / `["array","null"]` on optional may-be-absent fields (recon `description`/`tech`/`manifest`/`risk`/`detected_pattern_detail`, findings `cwe`/`mitre`) + code guards on the iterated fields

## 2. Semantic layer + consistency contract

- [x] 2.1 `checks.py`: 1–5 domain guard before `band()`; kill-chain step referential integrity; `detected_pattern==other ⇒ detail`
- [x] 2.2 Unify the OWASP band to `LOW 1-4 / MED 5-9 / HIGH 10-16 / CRIT 17-25` across all three skills, both agent definitions (`agents/diagram-specialist.md`, `agents/report-analyst.md`), and the docs/canonical example
- [x] 2.3 Judge-output integrity in `run.py` (`_load_judge`: malformed/incomplete recorded, absent allowed) + surface in `report.py` (cannot be green over it)

## 3. The gate (in-flow validation loop)

- [x] 3.1 `run.py validate` subcommand (structure + consistency + coverage; advisory diagram/report; specific DEFECT lines + non-zero exit)
- [x] 3.2 `SKILL.md`: emit `recon.json` (Phase 1) + `findings.json` (Phase 8); Pre-Emit Self-Check; "Manifest Validation Gate" (run, re-spawn-with-specifics, route-missing-info)
- [x] 3.3 `agent-prompts.md`: the four security-architect spawn prompts emit the three manifests the gate validates
- [x] 3.4 `executor.md`: absent data is `null`/omitted, never invented; `detected_pattern` guidance

## 4. Plugin packaging (hard gate, seamless install)

- [x] 4.1 `hooks/validate_gate.py` + `hooks/hooks.json`: `PreToolUse` on `Task`, deny the report-analyst spawn on failing manifests, fail-open on infra, `${CLAUDE_PLUGIN_ROOT}` path
- [x] 4.2 `.claude-plugin/plugin.json` + `marketplace.json`; flatten `agents/<name>/<name>.md` → `agents/<name>.md` for auto-discovery
- [x] 4.3 README: plugin install (hard gate) vs manual install (soft gate); `docs/STRUCTURED-OUTPUT-CONTRACT.md` map

## 5. Verify

- [x] 5.1 Validator: 7/7 crafted violations caught; all 32 committed manifests conform to the tightened schemas; explicit `null` accepted on every absent-optional field; no crash on null `cwe`/`mitre`
- [x] 5.2 Regression: structure+consistency defects = 0 across all 16 committed runs (only pre-existing `missing-report` in report-less `iteration-v2` dirs)
- [x] 5.3 Gate: clean run passes; corrupted run denies with specific defects; hook allows non-report tools and denies report spawn on bad manifests
- [ ] 5.4 Live: run the skill end-to-end on a target as a plugin; confirm the hook blocks report generation on an induced defect and the re-spawn fixes it
- [ ] 5.5 `openspec validate add-structured-output-validation-loop --strict`; archive after merge
