## Why

The orchestration was designed around Claude Code platform constraints that are now stale. Verified
against current official docs (July 2026), five of the assumptions baked into `SKILL.md` and
`docs/ARCHITECTURE.md` no longer hold — and the platform grew *more* capable, so the workarounds they
forced can be **deleted**, not redesigned:

- Custom agents are **spawnable by their `name`** (identity = the `name` frontmatter). There is no
  "built-in type" ceiling; the only built-ins are `Explore`/`Plan`/`general-purpose`. So
  `validation-specialist` need not be spawned as `general-purpose`, and `diagram-specialist` need not be
  spawned as `security-architect` with its real instructions read from a `/tmp` copy.
- `tools:` is an allowlist over *all* tools (omitted ⇒ inherit all), not a restrict-only field.
- The spawn tool is **`Agent`** (`Task` was renamed in v2.1.63; `Task(...)` still works as an alias).
  **`TaskOutput` is not a current tool** — blocking is `run_in_background: false`, and background spawns
  notify on completion.
- Subagents may spawn nested subagents (depth ≤5) — flat orchestration is now a *choice*, not a mandate.

The published demo already proves the target state: its recording spawned `subagent_type:
validation-specialist` **by name** and ran Phase 7 concurrently with the specialists. The current spec
regressed from that. Today's stale mechanics also cause real harm: spawning `validation-specialist` as
`general-purpose` silently gives it the **full** tool set instead of its declared least-privilege list,
and both workaround-spawned agents' carefully-written routing descriptions never reach the router.

## What Changes

- **Spawn every persona by its own `name`** (`subagent_type: "<persona>"`). Delete the `general-purpose`
  workaround for `validation-specialist` and the `spawn-as-security-architect` + prompt-pointer pattern
  for `diagram-specialist`. Each persona then runs with its own declared `model`/`tools`/`memory`.
- **`Task` → `Agent`; remove `TaskOutput`.** Blocking spawns use `run_in_background: false`; the parallel
  wave waits on background completion notifications.
- **Delete the `/tmp/threat-model-refs` copy step.** Point `{refs_dir}` at the skill's real
  `references/` directory (absolute path). Remove the dead `SKILL_BASE` line, the hardcoded `~/.claude`
  source paths (which break project-level and plugin installs), and the silent `|| true` punts.
- **Least-privilege + correctness pass on the persona definitions**: fix `code-review-agent`'s `CRA-`
  vs `CR-` finding-id contradiction; drop unneeded `Bash`/`Edit` from `privacy-agent` and `Edit` from
  `validation-specialist`; give `code-quality-reviewer` an explicit `tools` list (it currently inherits
  all); state a per-persona `model` rationale (the structural/mechanical seats may use a cheaper tier);
  fix the "persistent Persistent Agent Memory" typo across the affected files; label `security-reviewer`
  and `code-quality-reviewer` as **standalone companions** (not spawned by the pipeline) everywhere the
  roster is described.
- **Correct the platform-constraint prose** in `docs/ARCHITECTURE.md` §4.1/§4.6/§8 and the "Built-in
  Agent Type" column (there is no built-in `security-architect`; these are the suite's own custom
  subagents) — reframing flat orchestration as an intentional, transparent design choice.

The boundary holds: no analysis behavior changes; this modernizes *how* the parent spawns the same
agents and removes contortions the platform no longer requires.

## Capabilities

### New Capabilities
- `pipeline-orchestration`: how the parent conversation spawns and sequences the personas — by-name
  spawning, the current `Agent` tool surface, reference-file access, and persona-definition hygiene
  (identity, least-privilege tools, model rationale, roster roles).

### Modified Capabilities
<!-- composes with the branch's manifest-validation-gate (the gate's PreToolUse hook matches Agent/Task
     spawns and is unaffected by by-name spawning) and with refine-pipeline-flow (which owns phase
     sequencing); no requirement changes to them. -->

## Impact

- Modified: `skills/threat-model/SKILL.md` (spawn steps, refs-prep block, tool-surface prose),
  `references/agent-prompts.md` (drop the "read your instructions from {refs_dir}/…-agent.md" pointers;
  by-name spawn params), `agents/*/*.md` (validation-specialist + diagram-specialist descriptions,
  code-review-agent id prefix, privacy-agent/validation-specialist tool lists, code-quality-reviewer
  tools, model rationale, memory-boilerplate typo, standalone labels), `docs/ARCHITECTURE.md`
  (§4.1/§4.6/§8 constraint prose + Component Inventory), `README.md` (roster wording: 7 pipeline
  personas + 2 standalone companions).
