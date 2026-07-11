## Context

The flow findings came from the flagship-flow, personas, and knowledge-refs reviews, cross-checked
against the demo recording. Two of the changes (fresh-context Phase 6, early specialists) are supported
by the multi-agent research corpus; the rest are wiring corrections where an eval-gated artifact was
unowned at the point its inputs existed.

## The determinism boundary (unchanged)

Nothing here moves a check between code and judgment. It reassigns *who produces which artifact when* so
the deterministic gates (coverage_checks, diagram_checks, the manifest gate) have something valid to
check. The coverage ledger's structure and verification are unchanged — this only names its per-agent
writers and the single merger.

## Decisions

1. **Analysis split A={3,4,5}, B={6,8}.** Phases 3–5 stay bundled (score continues from identify; the
   false-negative hunt benefits from having its own 3/4 in-window). Phase 6 moves to a fresh spawn that
   reads 01/03/04/05 — distillates, not the generator's trace — which is the clean-context-reviewer
   shape and dissolves the fragile self-audit 5↔6 loop. Phase 8 (summary) stays with 6 so the agent that
   just validated writes the authoritative finding table.

2. **Specialists spawn after Phase 2, not Phase 7.** Their only hard dependency is recon (01) plus the
   node-id namespace (02). Feeding them 04/06 would anchor them and defeat independent rediscovery, whose
   value is exactly that two agents hitting the same issue independently raises confidence (and the
   validation-specialist dedups). Running them in the background from Phase 2 overlaps them with the long
   analysis phases — the parallelism the demo already used.

3. **Ledger single-writer via merge, not concurrent write.** Three background specialists writing one
   `coverage.json` is the same-file-contention anti-pattern. Instead each records states in its own
   markdown output (natural, since each already writes one file), and the validation-specialist — which
   already reads everything — merges into `coverage.json`. Recon seeds `context`. This keeps the ledger's
   "each agent attempts its domain" intent without the race.

4. **Analytical visuals belong to Phase 7.** Their preconditions (scored findings, declared kill chains,
   roles, dep manifest) don't exist at Phase 2, and Phase 2 forbids risk content. The acceptance-gate
   text moves the analytical block to Phase 7; the Phase 7 spawn prompt gains `analytical-visuals.md` and
   the Phase 7 checklist so the producing agent is actually routed to the formats it must satisfy.

5. **SKILL.md length.** The verification bash is deterministic and fragile — it belongs in a script
   (`scripts/verify_run.sh`), which also satisfies the skills "scripts for deterministic ops" guidance.
   The pipeline-summary template and the illustrative mermaid pipeline diagram are reference material,
   not operating instructions — they move to `references/`. This is the cheapest path under 500 lines
   without splitting the methodology from the orchestration (that larger refactor is deferred).

## Risks / trade-offs

- **One extra spawn** (the Phase 6+8 split) costs ~4 file reads and a fresh context; the anti-anchoring
  and reduced peak-context payoff outweighs it.
- **Deferred**: a full SKILL.md split of agent-facing methodology from parent-facing orchestration.
  Scoped out to keep this change reviewable; the extractions above already land under the guidance line.
