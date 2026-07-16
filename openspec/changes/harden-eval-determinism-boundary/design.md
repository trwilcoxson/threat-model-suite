## Context

These are corrections to the eval's deterministic layer surfaced by the eval-architecture and
visual-architecture reviews and reproduced empirically. Each was verified: the attack-flow and legend
bugs by running the checks against spec-compliant snippets; the grounding false-passes by evaluating
`Path('/tmp/repo') / '/etc/passwd'` and common-basename cases; the verdict gap against the committed
NodeGoat sample (recon-audit found missed subsystems while the banner logic stayed green).

## The determinism boundary (the point of this change)

The core principle is "deterministic code checks structure over emitted facts; it never infers content
or scripts the answer." This change removes the two places the code violated it (name-vocab auth gating,
prose-keyword layer inference) and keeps every other check on the declared-fact side. The judge-content
signals added to the verdict are **presentation** — they qualify how the result reads, computed from the
judges' own outputs, and are strictly guarded so an odd payload is inert. Correctness of a finding, a
diagram, or a coverage state remains the LLM judge's call; the code only asks "is the structure present
and self-consistent."

## Decisions

1. **Documented-stamp detection.** `_typed` accepts `| type: <kind>` inside a `%% Version:` line in
   addition to the bare `%% type:` line, hyphen-or-space tolerant, for attack-tree/attack-flow/SBOM. The
   convention is then documented in the two reference files so it no longer lives only in source.
2. **Label-aware edge counting.** `_edges` strips double-quoted node-label spans before testing for an
   edge operator, so a legend node's glyph is not an edge while a real `A -->|"…"| B` still is.
3. **Declared-fact auth gate.** The auth-sequence requirement fires on a non-empty declared `roles[]` or
   an S/E finding; the name-vocab scan is deleted. `executor.md` states `roles[]` is the declared auth
   signal so the emitter knows what gates it. `_layer_of` is stamp-only.
4. **Sound grounding.** `_resolves_in_repo` rejects empty/whitespace and absolute paths up front, drops
   the bare-basename rglob (a common basename can no longer ground an invented path — the full relative
   path must resolve), and strips a trailing `:line[:col]` before resolving. The safe grep invocation
   (`-F`, `--exclude-dir=.git`, 20s timeout) and the direct-path/glob/literal-substring checks stay.
5. **Component-only scaling.** `size = len(components)`.
6. **Judge-content verdict.** `report._verdict` gains guarded caveats (mean_soundness < 0.6,
   proportionality inflated/thin, missed subsystems) that downgrade green→amber; `run.py` loads the
   diagram- and coverage-judge outputs; a distinct guarded renderer shows them. The structured-output
   change's judge-*integrity* gate (malformed/incomplete output prevents a clean verdict) is preserved.

## Risks / trade-offs

- The verdict caveats are advisory by design — they never hard-fail a run, so a genuinely bad diagram is
  surfaced as a caveat plus the diagram section, not a gate. Hard gating on a judgment would put content
  assessment in the blocking path, which the boundary forbids.
- Each fix ships a runnable assertion in `test_checks.py`; the committed sample runs are re-verified to
  confirm no run's defect set changes (the fixes remove false failures, they don't relax real ones).
