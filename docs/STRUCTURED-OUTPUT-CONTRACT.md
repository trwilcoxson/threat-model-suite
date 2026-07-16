# Structured output and the validation loop — pattern-to-implementation map

How this suite realizes the standard structured-output reliability patterns. Those patterns are written
for an **SDK app** that calls the Claude API with tool schemas; this suite is a **Claude Code skill +
agents** that writes manifests as files and is graded by a reference-free eval. So most patterns map by
**analog** (post-hoc validation, parent-orchestrated retry) rather than literally. Each row records the
pattern, how it applies here, a status, and the file evidence.

Status legend: **APPLIED** (implemented here) · **ALIGNED** (already correct by design) ·
**ANALOG** (literal API feature N/A; file-based equivalent in place) · **N/A** (not applicable, with reason).

The named idea throughout: **structured output is a JSON (structural) contract, not a correctness
contract.** Schema compliance is not semantic correctness — they are different guarantees, enforced by
different layers.

---

## Structured output as a contract

| Pattern | This system | Status | Evidence |
|---|---|---|---|
| Tool/`strict` output is a structural contract, not a correctness contract | Determinism only checks structure over emitted facts; correctness is judged by LLM layers | ALIGNED | `README.md` layer split; `checks.py` docstring |
| Reliable extraction = generate → validate semantics in app code → retry with specific feedback | The parent orchestrator runs `run.py validate` over the manifests and re-spawns the agent with the specific defects | APPLIED | `SKILL.md` "Manifest Validation Gate"; `run.py cmd_validate` |
| Retry specificity is not optional | Each defect prints `field: constraint: actual-vs-expected` | APPLIED | `run.py cmd_validate`; `checks.py` detail strings |

## Two structured-output features — output_config.format, strict, streaming

| Pattern | This system | Status | Evidence |
|---|---|---|---|
| `strict:true` constrains tool-input JSON via compiled grammar | An agent writing a file is **not** token-constrained, so the contract is enforced **post-hoc**: `schema_checks.py` validates each manifest against `schema/*.json` | ANALOG | `schema_checks.py`; wired in `checks.py`, `coverage_checks.py` |
| `output_config.format` constrains the final response JSON | The "final response" here is `report.md` + the manifests, all written as files and validated after the fact | ANALOG | `prompts/executor.md`; `checks.py` |
| Constrained decoding (token space limited at each step) | No constrained decoding exists in a file-writing flow; post-hoc validation is the deliberate substitute, which is *why* the validation loop matters more here | N/A (literal) | — |
| **output_config.format + streaming are incompatible** | The one place this suite streams structured data is the observability event stream, which is **NDJSON** — each line a complete, independently-valid JSON object — the shape that sidesteps the whole-grammar-vs-streaming tension | N/A → ANALOG | `events.py` (`tm.run-event/1`), `tm_observe.py` |

## Forcing the artifact — tool_choice

| Pattern | This system | Status | Evidence |
|---|---|---|---|
| `tool_choice:"any"`/forced guarantees a structured call; `"auto"` may return prose | The harness fails loudly on a missing manifest (`missing-artifact`); the gate blocks a prose-only run; the spawn prompts enumerate the manifest files as required output | ANALOG | `checks.py` `missing-artifact`; `agent-prompts.md` |
| Force the *specific* tool when the document type is known | Each agent has a fixed output contract — it does not choose *whether* to emit its manifest | ALIGNED | `agent-prompts.md`, `SKILL.md` phase File Outputs |

## Schema design — preventing invented answers

| Pattern | This system | Status | Evidence |
|---|---|---|---|
| Make fields optional/**nullable** when the source may lack the value (`"po_number": ["string","null"]`) | Optional may-be-absent fields accept explicit `null` as well as omission so honest absence never forces a fabrication | APPLIED | recon `description`/`tech`/`manifest`/`risk`/`detected_pattern_detail` → `["string","null"]`; findings `cwe`/`mitre` → `["array","null"]` (+ `or []` code guards) |
| Use an **"unclear"** enum for genuinely ambiguous fields | Coverage `state` includes `unknown` (with a required note); `detected_pattern` includes `unknown` | APPLIED/ALIGNED | `coverage.schema.json`; `coverage_checks.py` (`unknown-without-note`); `recon.schema.json` |
| Use **"other" + detail** for extensible categorization | `detected_pattern` has `other`; an `other` value requires `detected_pattern_detail` (conditional rule enforced in code, since JSON Schema can't) | APPLIED | `recon.schema.json`; `checks.py` `detected-pattern-other-without-detail` |
| Goal: make it easy to say "I don't know" | Coverage `unknown`/`absent`, `no_issue_surface[]`, empty ref arrays, nullable optionals | ALIGNED | `SKILL.md` Coverage Ledger; `findings.schema.json` |

## Property ordering

| Pattern | This system | Status | Evidence |
|---|---|---|---|
| Required props emit before optional, regardless of schema order; if order matters, mark everything required | Manifests are `json.loads`→dict and read **by key**, never positionally — output property order is irrelevant to every consumer | N/A (with reason) | `checks.py`/`report.py`/`stability.py` all key-access; no index-into-object parsing |

## The validation loop

| Pattern | This system | Status | Evidence |
|---|---|---|---|
| Semantic errors (wrong field, bad sums, wrong-source values) live above the schema | Captured by the consistency/grounding/coverage layers + LLM judges, separate from the schema layer | ALIGNED | `checks.py`, `coverage_checks.py`, `prompts/*-judge.md` |
| Application code is the only place semantic validation can happen | The **parent orchestrator** is that application code — it runs the deterministic validator via Bash between agent spawns | APPLIED | `SKILL.md` gate; `run.py cmd_validate` |
| Specific feedback: which field, which constraint, actual vs expected | `severity HIGH != band(L3 x I2)=MEDIUM`; `summary_counts.LOW=0 but 1 findings present`; `step 'TM-999' is not a finding id` | APPLIED | `checks.py` defect details |
| Numeric consistency checks (sums) | `severity == band(likelihood × impact)`; `summary_counts == per-severity tally` | ANALOG/ALIGNED | `checks.py` `severity-formula`, `count-mismatch` |
| Date-format verification | The structured manifests carry **no date field** (the markdown Metadata date is human-facing, not in the validated contract), so no date check is needed | N/A (with reason) | `recon/findings/coverage.schema.json` have no date |
| Referential integrity between fields | `asset_refs`/`surface_refs` must resolve to recon ids; `kill_chains[].steps` must resolve to real findings | APPLIED/ALIGNED | `checks.py` `dangling-ref`, `killchain-dangling-step` |

## Self-correction fields

| Pattern | This system | Status | Evidence |
|---|---|---|---|
| Build the check into the schema: emit `stated_total` + `calculated_total` + `totals_match` + `conflict_detected` | The agent emits `likelihood`, `impact`, **and** `severity`; the eval **recomputes** `band(L×I)` *independently* rather than trusting a self-reported "matches" flag — the right choice for an **independent** checker. `summary_counts == tally` is the `totals_match` analog | ALIGNED (contextual deviation) | `checks.py` `band()`, `severity-formula`, `count-mismatch` |
| Also do the self-check proactively in the extraction pass | A **Pre-Emit Self-Check** has the agent verify the same invariants before writing the manifest (reactive eval-catch + proactive self-correction, both present) | APPLIED | `SKILL.md` "Pre-Emit Self-Check" |
| `detected_pattern` metadata enables systematic failure analysis by source pattern | `recon.detected_pattern` archetype (web-app/api/iac/polyglot-microservices/…) lets reliability be grouped by target shape | APPLIED | `recon.schema.json`; `prompts/executor.md` |

## When retries are not the answer

| Pattern | This system | Status | Evidence |
|---|---|---|---|
| Retries fix format/structure, not missing information | A defect rooted in absent source data routes to `null`/`no_issue_surface`/coverage `unknown`/Open Questions instead of a retry | APPLIED | `SKILL.md` gate (route-don't-retry clause) + Pre-Emit Self-Check; `run.py cmd_validate` message |
| Distinguish retryable (extracted wrong) from not-retryable (info absent) | Grounding catches fabrication (a retryable how-extracted error); `unknown`/nullable is the info-absent path | ALIGNED | `checks.py` grounding; `coverage_checks.py` |
| Address absent info at schema level (optional) or pipeline level (route/human review) | Both: nullable/optional fields **and** lift unknown/partial into Open Questions / Known Limitations | APPLIED/ALIGNED | schemas; `SKILL.md` Coverage Ledger Phase 8 |

## Complexity limits (20 strict tools / 24 optional params / 16 union types)

| Pattern | This system | Status | Evidence |
|---|---|---|---|
| Per-request cumulative limits on strict-tool grammars | No API request exists, so the limits don't bind today — but they are the budget the schemas must respect *if* the executor/judges are ever driven via the API with these as strict/format schemas | N/A (literal) → tracked | — |
| 16 union-type params total | Combined union-type params across all three schemas = **7** (the `["x","null"]` nullables) — well under 16. This is the live constraint on how many nullable unions may be added | TRACKED | accounting: findings 2 + recon 5 + coverage 0 = 7 |
| 24 optional params total per request | Combined optional params = **25** — would *exceed* 24 **if all three were one strict request**. They never are: each agent emits its own manifest. That separation **is** the "split across subagents" remedy | TRACKED / ANALOG | findings 3 + recon 8 + coverage 14 = 25; pipeline splits emission across agents |
| Strategy: split tools across requests/subagents | The 8-phase pipeline already distributes manifest emission across distinct subagents (recon agent → recon.json; analysis agent → findings.json) | ALIGNED | `SKILL.md` pipeline; `agent-prompts.md` |

## Structure vs semantics — the core distinction

| Pattern | This system | Status | Evidence |
|---|---|---|---|
| Structure (mechanical) vs semantics (validation loop) are different guarantees | The whole design: deterministic layers = structure/consistency/grounding/coverage; LLM judges = semantics; stability = cross-run | ALIGNED | `README.md` "Structured output" section + layer list |
| Combine both layers + retry + route to human | Schema gate + semantic checks + judges + re-spawn + Open Questions routing | APPLIED/ALIGNED | `run.py`, `SKILL.md`, `prompts/*` |
| The error is trusting structured output for more than it guarantees | "Determinism lives only in templates and evals … never the answer" | ALIGNED | `README.md`; `openspec/` principle |
| Tool-schema context-window cost | References are loaded on demand, not all in context (progressive disclosure) | ALIGNED | `SKILL.md` Reference Files |

---

**Bottom line.** Every structured-output pattern is either applied, already aligned, realized as a
file-based analog, or N/A for a documented reason. The two that are *literally* inapplicable
(constrained-decoding complexity limits; streaming-vs-format incompatibility) still produced real design
checks here: the schemas stay within the union-type budget (7 ≤ 16) and split emission across subagents
(the remedy for the 24-optional limit), and the event stream uses NDJSON to keep each structured record
independently valid.
