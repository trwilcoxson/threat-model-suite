# Tasks

## 1. Diagram detection
- [x] 1.1 `_typed()` accepts the documented `| Type: <kind>` stamp (attack-tree/flow/SBOM), hyphen/space tolerant
- [x] 1.2 Document the matched stamp in `references/mermaid-diagrams.md` §5 and `references/analytical-visuals.md`
- [x] 1.3 `_edges()` strips quoted node-label spans so legend glyphs aren't counted as edges

## 2. Declared-fact gating (remove content inference)
- [x] 2.1 Auth-sequence gate keys on declared `roles[]` (or an S/E finding); drop the `AUTH_VOCAB` name scan
- [x] 2.2 `executor.md`: state `roles[]` is the declared auth signal
- [x] 2.3 `_layer_of()` is stamp-only (remove the prose-keyword fallback)

## 3. Grounding + scaling
- [x] 3.1 `_resolves_in_repo()` rejects empty/absolute evidence, drops the bare-basename fallback, accepts `path:line`
- [x] 3.2 Layer scaling `size = len(components)`
- [x] 3.3 Heat-map section match is specific (`heat map`/`heatmap`/`risk matrix`, not bare `likelihood`)

## 4. Verdict reflects judged content
- [x] 4.1 `report._verdict` adds guarded caveats (mean_soundness<0.6, proportionality inflated/thin, missed subsystems) — green→amber, never hard-fail
- [x] 4.2 `run.py` loads diagram-judge + coverage-judge; a guarded renderer shows them
- [x] 4.3 Preserve the structured-output change's judge-integrity gate (malformed/incomplete prevents a clean verdict)

## 5. Verify
- [x] 5.1 `test_checks.py`: a runnable assertion per fix (9 self-checks) all pass
- [x] 5.2 32/32 committed manifests conform; no committed run's defect set changes
- [x] 5.3 `openspec validate harden-eval-determinism-boundary --strict`
