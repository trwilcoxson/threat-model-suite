## Context

The run must first force an explicit choice with no accidental default start. Because the determinism
boundary means prose cannot enforce a gate, the design leans on two mechanisms the repo already ships:
the PreToolUse-on-`Task` deny gate (`hooks/validate_gate.py`, which already denies the report-analyst
spawn until manifests validate) and the reference-free deterministic checks in
`evals/reliability/`. The selection is captured as a new emitted fact, `run-plan.json`, the same way
`recon.json`/`findings.json`/`coverage.json` capture other run facts.

## The determinism boundary

Nothing moves between code and judgment. The **user** makes the selection; the **agent** only
transcribes the confirmed choice into `run-plan.json` (a neutral structured fact) — it applies no
selection heuristic of its own. The **hook** and the **eval** are deterministic code over that fact:
the hook denies an unplanned spawn by checking file existence + schema; the eval compares the produced
artifact set to the plan by file existence + set membership. No check judges *content* or scripts an
answer.

## Decisions

1. **`run-plan.json` as an emitted fact.** `{mode, team[], outputs[], confirmed, source}` written once
   at run start, schema-validated like the other manifests. It is additive; no existing manifest
   changes.
2. **Hard start gate reuses the existing pattern.** A PreToolUse matcher on `Task` denies the first
   pipeline spawn unless `{output_dir}/run-plan.json` exists, validates, and has `confirmed: true`. The
   deny reason carries the menu. `Write` is ungated, so the agent can produce the plan after the user
   picks and then spawn — no deadlock.
3. **Two entry paths.** A one-shot specification is parsed and echoed for confirmation; an unspecified
   invocation prints the menu and stops. Both end in the same confirmed `run-plan.json`.
4. **Conditional workflow.** Specialist spawns become conditional on `team[]` and the report-analyst
   emits exactly `outputs[]`. Solo/Team survive as named presets over the plan.
5. **Reference-free match check.** `run_plan_checks.py` asserts each specialist output and each
   selected output exists iff planned — flagging both missing-planned and extra-unplanned artifacts —
   and is wired into `run.py validate`; the report-spawn gate is extended to block on plan drift.

## Risks / trade-offs

- **Consent ceiling (stated honestly).** A hook cannot cryptographically prove a human chose the plan
  versus the model auto-filling one. The guarantee is bounded but strong: no run starts or completes
  without a validated, logged, user-visible plan the run provably matches — the blast radius of a soft
  ask failure is "a plan you can veto", never "a surprise full run".
- **Back-compat.** Existing runs without a `run-plan.json` (e.g. the archived flagship example) are
  unaffected because `run_plan_checks` only runs when the plan is present, keeping current evals green.
- **Two-layer gating complexity.** Mitigated by reusing the one already-shipped hook seam and the
  existing reference-free harness rather than introducing a new hook event type or dependency.
