# Tasks

## 1. Analysis context split (Phase 6+8 fresh)
- [x] 1.1 SKILL.md: split the analysis step into spawn A (Phases 3–5) and spawn B (Phases 6+8, fresh context reading 01/03/04/05)
- [x] 1.2 agent-prompts.md: add the Phase-3–5 and Phase-6+8 prompts; the Phase-6+8 prompt reads back 01/03/04/05 and owns "confirm every Phase 5 finding is validated or rejected"
- [x] 1.3 SKILL.md Phase 5: delete the impossible "if Phase 6 has already been completed" conditional
- [x] 1.4 Update the SKILL.md pipeline diagram / workflow steps to show A and B

## 2. Specialist spawn timing + inputs
- [x] 2.1 SKILL.md Team workflow: move the 3-specialist background spawn to right after Phase 2; they run concurrently with analysis + Phase 7
- [x] 2.2 agent-prompts.md: add `02-structural-diagram.md` to the privacy/grc/code-review specialist inputs (node-id namespace)

## 3. Coverage-ledger ownership
- [x] 3.1 SKILL.md §1.10 + Phase 1 prompt: seed the ledger context in recon
- [x] 3.2 Spawn prompts (analysis + specialists): "record coverage states for items in your domain in your output file"
- [x] 3.3 validation-specialist: merge domain states into a single `coverage.json` (single writer)
- [x] 3.4 report-analyst prompt: add `coverage.json` to the input list; Post-Assessment Verification: `test -s coverage.json`
- [x] 3.5 analysis-checklists.md: add a ledger-record item to the relevant phase checklists

## 4. Analytical visuals placement
- [x] 4.1 SKILL.md: move the "Analytical & communication visuals" block out of the Phase 2 acceptance gate into Phase 7's steps
- [x] 4.2 agent-prompts.md Phase 7 prompt: add `analytical-visuals.md` and the Phase 7 completeness checklist to the read list
- [x] 4.3 report-template.md: add Section IV-A to the Contents block

## 5. Checklist + Solo fixes
- [x] 5.1 SKILL.md Phase 5: pointer → "Phase 5 checklist"; Phase 6: pointer → "Phase 6 checklist"
- [x] 5.2 analysis-checklists.md: rewrite the Phase 8 checklist to mirror the summary-only Phase 8 (drop LINDDUN/final-diagram/full-inventory items); drop the SKILL.md:713 LINDDUN residue
- [x] 5.3 SKILL.md Solo condition 5: make the explicit-narrow-ask an independent sufficient Solo trigger

## 6. SKILL.md length
- [x] 6.1 Extract Post-Assessment Verification bash → `scripts/verify_run.sh`; SKILL.md references it
- [ ] 6.2 Extract the pipeline-summary template + the illustrative pipeline diagram → `references/`
- [ ] 6.3 Confirm SKILL.md is at or near ≤500 lines

## 7. Verify
- [x] 7.1 `openspec validate refine-pipeline-flow --strict`
- [x] 7.2 grep: no "Phase 4 checklist"/"Phase 5 checklist" mis-pointers; no impossible Phase-5 conditional
- [ ] 7.3 Live: a re-run produces `coverage.json` and the analytical visuals (covered by the re-record)
