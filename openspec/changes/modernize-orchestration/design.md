## Context

The architecture doc (§4.1, §4.6, §8) records constraints "discovered" in early-2026 Claude Code:
custom agents can't add tools, custom-only agents can't be spawned by name, agents can't spawn agents,
and the orchestrator waits with `TaskOutput`. All five were verified stale against the current official
docs (`code.claude.com/docs`: sub-agents, skills, hooks, plugins, agent-teams) in July 2026. This
change is almost entirely *deletion* of the resulting workarounds; the risk is low because the demo
recording already exercised the target mechanics.

## The determinism boundary (unchanged)

This change touches only orchestration mechanics — which tool spawns which persona, and how the parent
waits. No deterministic-vs-LLM boundary moves: the agents still do all reasoning, the templates/evals
still enforce structure. The manifest-validation-gate hook (from the structured-output change) matches
on the spawn tool name and the target `subagent_type`/`name` strings; by-name spawning keeps those
strings (`report-analyst`/`report-generator`) intact, so the hard gate is unaffected.

## Decisions

1. **Keep subagents, not Agent Teams.** The pipeline is sequential, dependency-heavy, shares a
   filesystem, and yields one report set — the docs put exactly this on the subagent side ("for
   sequential tasks or work with many dependencies, a single session or subagents are more effective").
   Agent Teams is experimental (flag-gated), costlier, and forbids nested teams. Flat parent-orchestrated
   spawning stays — but now as an intentional choice (transparent, debuggable, every agent visible),
   documented as such, not as a forced consequence of "agents can't spawn agents."

2. **By-name spawning is the whole mechanism.** `agents/validation-specialist/validation-specialist.md`
   and `agents/diagram-specialist/diagram-specialist.md` already carry the correct `name:` frontmatter,
   so `subagent_type: "validation-specialist"` / `"diagram-specialist"` are valid today. Removing the
   workarounds also restores each agent's declared least-privilege `tools` (general-purpose over-granted
   validation-specialist the full set) and routes its `description` to the delegation router.

3. **`{refs_dir}` = the skill's real `references/` directory.** Subagents read arbitrary absolute paths
   and preload skills via `skills:` frontmatter, so the `/tmp` copy is unnecessary. Substituting the
   absolute `references/` path removes the staleness/collision/sandbox-denial failure modes and the dead
   `SKILL_BASE`/`|| true` code. Cross-skill references the specialists need (compliance/privacy) are
   reached the same way — via each specialist's own preloaded skill, which already ships them.

4. **Persona hygiene rides along** because it touches the same `agents/*.md` files and is cheap:
   least-privilege tool lists, a stated `model` rationale (so `model:` is a decision, not a default),
   the `CRA-`/`CR-` id fix (its own output currently fails validation step 7), the memory-boilerplate
   typo, and labeling the two non-pipeline reviewers as standalone companions so the "9-agent pipeline"
   claim stops being false.

## Risks / trade-offs

- **Plugin-shipped agents ignore `hooks`/`mcpServers`/`permissionMode` frontmatter.** The personas use
  none of those (only `tools`/`model`/`skills`/`memory`/`color`), so plugin distribution stays clean; the
  validation gate lives at plugin level (`hooks/hooks.json`), which is supported.
- **`model` retargeting** is left as a rationale note plus conservative choices; we do not force a
  cheaper tier on any persona whose quality depends on the heavier model (the adversarial/synthesis
  seats stay on the strong model).
