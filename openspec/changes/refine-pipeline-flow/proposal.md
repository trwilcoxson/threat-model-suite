## Why

The 8-phase pipeline is sound, but the evaluation surfaced concrete flow defects — one real design
debt and several wiring gaps where an eval-gated artifact is owned by nobody at the point its inputs
exist:

- **The skeptical Phase 6 shares a context with the generative Phases 3–5.** The only semantic
  false-positive pass (does a realistic attack path exist? is severity honest?) runs in the same
  security-architect context that produced the findings, so it inherits the generator's anchoring — and
  the downstream validation-specialist checks *structure*, not attack-path realism. Best practice is a
  clean-context evaluator.
- **The 3 specialists are spawned after Phase 7, though their dependency frontier is Phase 2** (they
  need canonical node ids, not the risk overlay). The published demo already ran Phase 7 concurrently
  with the specialists; the current spec serialized it, wasting wall-clock.
- **`coverage.json` is eval-gated but wired to no agent or prompt.** SKILL.md says "each agent records
  items in its domain," but no spawn prompt, phase step, or agent definition mentions the ledger; the
  specialists run their own skills and never see the Coverage Ledger section. As written it would also
  be three parallel background agents writing one JSON — a same-file-contention hazard.
- **The analytical/communication visuals have no owner at a workable time.** Their requirements sit in
  the Phase 2 acceptance gate, but their preconditions (scored findings, declared kill chains) don't
  exist until Phases 4–5, and Phase 2 forbids risk content. The Phase 7 checklist lists them, but
  SKILL.md's Phase 7 steps and the diagram-specialist prompt never route the agent to
  `analytical-visuals.md` or that checklist.
- **Smaller correctness gaps:** the Phase 5→6 completeness-checklist pointers are off by one (Phase 5 is
  sent to "the Phase 4 checklist", Phase 6 to "the Phase 5 checklist"); Phase 5 carries an impossible
  "if Phase 6 has already completed" conditional; the Phase 8 checklist still describes the pre-split
  full report; and the Solo/Team gate makes Solo unreachable for a plain request on a small clean
  system, contradicting the skill's own "scale proportionally" rule.

## What Changes

- **Split the analysis bundle**: spawn A = Phases 3–5 (generative), spawn B = Phases 6+8 (skeptical
  validation + summary) in a **fresh context** reading 01/03/04/05 from disk. The bidirectional 5↔6
  re-check loop dissolves into B's whole job.
- **Spawn the 3 specialists in the background right after Phase 2**, running them concurrently with the
  analysis phases and Phase 7. Keep their inputs at 01 (+02 for node ids) — independence beats anchoring.
- **Give the specialists the Phase 2 node-id source** (`02-structural-diagram.md`) so they can satisfy
  the "matching diagram node ids" contract the validator enforces.
- **Assign the coverage ledger an owner**: each agent records its domain's states inside its own output
  file; the validation-specialist merges them into a single `coverage.json` (one writer). Add ledger
  seeding to Phase 1 and the seed/record duties to the spawn prompts and phase checklists; add
  `coverage.json` to the report-analyst's input list and to Post-Assessment Verification.
- **Move the analytical-visuals requirement out of the Phase 2 gate into Phase 7**, add the visuals to
  Phase 7's steps, and add `analytical-visuals.md` + the Phase 7 completeness checklist to the Phase 7
  spawn prompt's read list.
- **Fix the smaller gaps**: correct the two off-by-one checklist pointers; delete the impossible Phase 5
  conditional; rewrite the Phase 8 checklist to mirror the summary-only Phase 8; make the "explicit
  narrow ask" an independent *sufficient* Solo trigger so plain requests on small clean systems can go
  Solo.
- **Slim SKILL.md toward the <500-line guidance**: move the Post-Assessment Verification bash into a
  shipped `scripts/verify_run.sh`, and the pipeline-summary template + the illustrative pipeline diagram
  into `references/`, keeping SKILL.md as trigger + Solo/Team decision + orchestration + methodology.

## Capabilities

### New Capabilities
- `assessment-flow`: the phase sequencing and hand-offs — the generative/skeptical context split,
  specialist spawn timing and inputs, coverage-ledger ownership, analytical-visuals placement, the
  Solo/Team trigger logic, and the completeness-checklist ↔ phase alignment.

### Modified Capabilities
<!-- composes with completeness-coverage (this assigns the ledger's per-agent owner without changing the
     ledger's structure or verification) and with modernize-orchestration (spawn mechanics); no
     requirement changes to those. -->

## Impact

- Modified: `skills/threat-model/SKILL.md` (analysis split into two spawns, specialist spawn point,
  coverage-ledger seeding/recording, analytical-visuals moved to Phase 7, Solo condition, Phase 5/6/8
  text, length trim), `references/agent-prompts.md` (spawn A/B prompts, specialist inputs + node-id +
  ledger-record clauses, Phase 7 read list), `references/analysis-checklists.md` (Phase 5/6 pointer
  targets, Phase 8 checklist), `references/report-template.md` (Section IV-A in Contents).
- New: `skills/threat-model/scripts/verify_run.sh` (the extracted verification), `references/`
  pipeline-summary template + pipeline diagram (extracted from SKILL.md).
