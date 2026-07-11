# Tasks

## 1. SKILL.md orchestration
- [x] 1.1 Team step 8: spawn `subagent_type: "validation-specialist"` by name (drop `general-purpose`)
- [x] 1.2 Steps 3/5 (Solo + Team): spawn `subagent_type: "diagram-specialist"` by name (drop `security-architect`)
- [x] 1.3 Replace `TaskOutput(task_id=..., block=true)` (step 7) with completion-notification wait; fix the "has all tools: Task, TaskOutput" prose to `Agent`
- [x] 1.4 Delete the `/tmp/threat-model-refs` copy block, the dead `SKILL_BASE` line, and the `|| true` punts; set `{refs_dir}` to the absolute `references/` path
- [x] 1.5 `Task` → `Agent` in the spawn-parameter prose (note the alias)

## 2. agent-prompts.md
- [x] 2.1 Diagram-specialist Phase 2/7 prompts: drop "Read your full instructions from {refs_dir}/diagram-specialist-agent.md"; carry the task inline
- [x] 2.2 Validation-specialist prompt: drop "Read your full instructions from {refs_dir}/validation-specialist-agent.md"; add the missing Execution Log clause
- [x] 2.3 Point all `{refs_dir}` substitutions at the real `references/` dir

## 3. Persona definitions (agents/*/*.md)
- [x] 3.1 validation-specialist.md: remove "Spawned as a general-purpose agent" from the description; drop `Edit` from tools
- [x] 3.2 diagram-specialist.md: remove the "runs under security-architect / read from copy" assumptions from Workflow Integration
- [x] 3.3 code-review-agent.md: fix `CRA-` → `CR-` in the examples (lines ~90/120) to match its own mandate
- [x] 3.4 privacy-agent.md: drop unneeded `Bash`/`Edit` from tools
- [x] 3.5 code-quality-reviewer.md: add an explicit `tools` list (stop inheriting all); fix the `\n`-literal description and the renamed-"Task tool" example
- [x] 3.6 Add a one-line `model` rationale to each persona; leave adversarial/synthesis seats on the strong model
- [x] 3.7 Fix the "persistent Persistent Agent Memory" typo across affected files
- [x] 3.8 Label security-reviewer + code-quality-reviewer as standalone companions in their bodies

## 4. Docs
- [ ] 4.1 ARCHITECTURE.md §4.1/§4.6/§8: rewrite the stale constraint prose (tools-can't-expand, custom-can't-be-spawned, agents-can't-spawn, TaskOutput); reframe flat orchestration as an intentional choice
- [ ] 4.2 ARCHITECTURE.md Component Inventory: relabel the "Built-in Agent Type" column (these are custom subagents; there is no built-in `security-architect`)
- [x] 4.3 README.md: roster wording → "7 pipeline personas + 2 standalone companions"

## 5. Verify
- [x] 5.1 grep SKILL.md + agent-prompts.md for `TaskOutput`, `general-purpose`, `threat-model-refs`, `SKILL_BASE` → no stale hits remain (except an intentional historical mention if any)
- [x] 5.2 `openspec validate modernize-orchestration --strict`
- [ ] 5.3 Live: a re-run spawns each persona by name and completes end-to-end (covered by the re-record)
