## Why

Today a run starts with no explicit user choice, which is exactly the "accidental full run" this change
prevents.

- **Mode is auto-inferred, not chosen.** `SKILL.md` picks Solo vs Team as a self-applied heuristic
  ("Default: Team … When in doubt: Team") and then spawns Phase 1 immediately — there is no stop and no
  user pick.
- **Team means everything.** Team implies all three specialists and the report always emits all four
  formats; a user cannot ask for privacy-but-not-GRC, or dashboard-and-pdf-only.
- **No machine-checkable record of intent.** Nothing records what the user chose, so nothing can verify
  the run produced exactly that.

## What Changes

- **Explicit upfront run-plan selection.** A new first step presents the choice — mode (Solo/Team),
  team composition (any subset of privacy / grc / code-review), and outputs (any subset of the report
  formats, the dashboard, and analytical visuals) — and **stops for a pick if unspecified**, or parses
  a one-shot specification (e.g. `team=privacy+code-review, outputs=dashboard+pdf`) and confirms it.
- **A `run-plan.json` emitted fact.** The confirmed choice is written as a small structured manifest at
  the start of the run, making the selection explicit and machine-checkable.
- **A hard start gate.** A PreToolUse hook on the `Task` tool denies the first pipeline spawn unless a
  schema-valid, confirmed `run-plan.json` exists — so no run starts without a plan. This reuses the
  repo's existing deny-on-`Task` gate pattern.
- **A reference-free determinism check.** A new deterministic check verifies the run produced EXACTLY
  the planned team and outputs — no missing planned artifact, no extra un-planned one.

## Capabilities

### New Capabilities
- `run-selection`: the explicit upfront selection of mode, team, and outputs; the `run-plan.json`
  emitted fact; the start gate that forbids an unplanned run; and the reference-free check that the run
  matched the plan.

### Modified Capabilities
<!-- composes with the existing assessment-flow (Solo/Team) capability, which becomes named presets
over the run plan; no requirement changes to it. -->

## Impact

- New: `hooks/` start-gate matcher/logic (extends `validate_gate.py` / `hooks.json`),
  `skills/threat-model/evals/reliability/schema/run-plan.schema.json`,
  `skills/threat-model/evals/reliability/run_plan_checks.py`, self-check cases in `test_checks.py`.
- Modified: `skills/threat-model/SKILL.md` (Step 0 selection + conditional specialist spawns +
  outputs driven by the plan), `agents/report-analyst.md` (emit exactly the planned outputs),
  `README.md` (document the selection step).
