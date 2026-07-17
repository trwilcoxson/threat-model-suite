# Tasks

## 1. Run-plan fact
- [ ] 1.1 Add `skills/threat-model/evals/reliability/schema/run-plan.schema.json` — `{mode, team[], outputs[], confirmed, source}` with enumerated team/output values
- [ ] 1.2 Wire `run-plan.schema.json` into `schema_checks.py`

## 2. Selection step (SKILL.md)
- [ ] 2.1 Add "Step 0: Run-Plan Selection" — parse a one-shot spec and echo it for confirmation, OR print the menu and STOP for a pick when unspecified
- [ ] 2.2 On confirmation, write `run-plan.json` to the output dir
- [ ] 2.3 Make Team specialist spawns conditional on `team[]`; make the report-analyst emit exactly `outputs[]`
- [ ] 2.4 Recast Solo/Team as named presets over the run plan (back-compat)

## 3. Hard start gate
- [ ] 3.1 Extend `hooks/validate_gate.py` (and `hooks/hooks.json`) with a PreToolUse-on-`Task` matcher that denies the first pipeline spawn unless a schema-valid, `confirmed:true` `run-plan.json` exists, with the menu as the deny reason
- [ ] 3.2 Extend the existing report-spawn denial to also block when produced outputs would contradict the plan

## 4. Reference-free determinism check
- [ ] 4.1 Add `skills/threat-model/evals/reliability/run_plan_checks.py` — assert each specialist output and each selected output exists iff planned (missing-planned AND extra-unplanned are defects)
- [ ] 4.2 Wire it into `run.py check`/`validate`, active only when `run-plan.json` is present
- [ ] 4.3 Add self-check cases to `test_checks.py` (matching run passes; missing-planned and extra-unplanned runs fail)

## 5. Verify
- [ ] 5.1 `openspec validate add-deterministic-run-selection --strict`
- [ ] 5.2 `cd skills/threat-model/evals/reliability && python3 test_checks.py` (all pass)
- [ ] 5.3 `python3 schema_checks.py` (all conform, incl. run-plan) and `python3 run.py validate` on the flagship example (PASS, unaffected)
- [ ] 5.4 Adversarial: confirm the first spawn is denied with no `run-plan.json`; confirm an extra/missing output fails the run-plan check
