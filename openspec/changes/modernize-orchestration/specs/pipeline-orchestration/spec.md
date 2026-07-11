## ADDED Requirements

### Requirement: Personas are spawned by their own name
The parent orchestrator SHALL spawn every persona with `subagent_type` set to that persona's `name`
(the identity field in its `agents/<persona>/<persona>.md` frontmatter). No persona is spawned under a
different built-in type as a workaround, and no persona is directed to read its own instructions from a
copied file.

#### Scenario: Validation specialist spawned by name
- **WHEN** the parent reaches the validation step
- **THEN** it spawns `subagent_type: "validation-specialist"` (not `general-purpose`), so the agent runs
  with its own declared `model`, `memory`, and least-privilege `tools`

#### Scenario: Diagram specialist spawned by name
- **WHEN** the parent reaches Phase 2 or Phase 7
- **THEN** it spawns `subagent_type: "diagram-specialist"` (not `security-architect`), and the spawn
  prompt carries the phase task directly rather than pointing at a `/tmp` copy of the agent definition

### Requirement: Current spawn tool surface
The orchestration instructions SHALL reference only tools that exist in current Claude Code: the `Agent`
tool (the `Task` alias is acceptable) for spawning, `run_in_background: false` for blocking spawns, and
background-completion notifications for the parallel wave. The instructions SHALL NOT reference
`TaskOutput`.

#### Scenario: Blocking spawn
- **WHEN** a step must complete before the next begins
- **THEN** it is spawned with `run_in_background: false` and the parent proceeds when it returns

#### Scenario: Parallel wave join
- **WHEN** the parent has spawned the background specialist wave
- **THEN** it waits on their completion notifications (not a `TaskOutput` call) before spawning the
  validation step

### Requirement: Reference files accessed in place
The parent SHALL make reference files available to spawned agents by absolute path to the skill's real
`references/` directory (and each specialist's own preloaded skill), not by copying them to a shared
temporary directory. No orchestration step depends on a hardcoded `~/.claude` path or a fixed
`/tmp/threat-model-refs` location.

#### Scenario: Agent reads a reference
- **WHEN** a spawned agent needs a framework or diagram reference
- **THEN** the spawn prompt gives it the absolute `references/` path, which resolves under manual,
  project-level, and plugin installs alike

### Requirement: Persona definitions are least-privilege and self-consistent
Each persona definition SHALL grant only the tools its job requires, use a finding-id prefix consistent
with the output protocol, and state the rationale for its `model` choice. Definitions that are not part
of the spawned pipeline SHALL be labeled as standalone companions wherever the roster is described.

#### Scenario: Least-privilege tools
- **WHEN** a persona only reads inputs and writes one report file
- **THEN** its `tools` list excludes capabilities it never uses (e.g. a read/analyze/write-one-file
  persona does not carry `Bash`/`Edit` it never invokes), and no persona inherits the full tool set by
  omitting `tools`

#### Scenario: Consistent finding ids
- **WHEN** the code-review persona emits findings
- **THEN** the id prefix in its examples matches the prefix its instructions and the output protocol
  mandate, so its own output passes the validator's id check

#### Scenario: Roster honesty
- **WHEN** documentation describes the agent roster
- **THEN** the personas the pipeline actually spawns are distinguished from standalone companion agents
  that it does not spawn
