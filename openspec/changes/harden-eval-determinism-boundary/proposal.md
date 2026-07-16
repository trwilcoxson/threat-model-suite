## Why

The eval's determinism boundary is drawn correctly across ~90% of the surface, but the review found
specific leaks where deterministic code **infers content** (against the core principle and the module's
own docstring), plus false-pass/false-fail bugs in the checks that let a bad run pass or a good run fail:

- **Attack-flow detection required an undocumented magic string.** `diagram_checks._typed()` matched only
  `%% type: attack-flow`, not the *documented* stamp `%% Version: … | Type: Attack Flow`. A spec-compliant
  run with ≥3 kill chains always got a false `no-attack-flow` defect — the convention lived only in eval
  source and one sample run.
- **Legend glyphs counted as unlabeled edges.** Arrow glyphs inside the spec-*required* legend text nodes
  (`RL6["==> Attack Path"]`) tripped the `untyped-edges` defect on fully-typed diagrams.
- **Content-sniffing gates.** The auth-sequence requirement fired when an entry-point *name* matched a
  15-word vocab (an entry point named "tokenizer" forced a sequence diagram); `_layer_of` inferred a
  diagram's layer from prose when the declared stamp was absent. Both infer content in code.
- **Grounding false-passes/false-fails.** `_resolves_in_repo` treated empty-string and absolute-path
  evidence as grounded, let a common basename ground an invented path, and failed on `path:line` refs.
- **Layer-size mismatch.** Scaling counted `components + data_stores`, but every prose rule scales on
  components — a small system could fail `missing-layers`.
- **The verdict ignored judge content.** A green "Reliable" banner could sit over a "weak" judged diagram,
  an "inflated" finding set, or an untrustworthy coverage denominator.

## What Changes

- `_typed()` accepts the documented `| Type: <kind>` stamp (and the convention is documented in
  `mermaid-diagrams.md` / `analytical-visuals.md`).
- `_edges()` strips quoted node-label spans so legend glyphs are not counted as edges.
- The auth-sequence gate keys on a **declared** fact (`roles[]` non-empty, or an S/E finding), not
  entry-point names; `_layer_of` is stamp-only. The eval no longer infers content.
- `_resolves_in_repo` rejects empty/absolute evidence, drops the bare-basename fallback, and accepts
  `path:line` refs — grounding neither false-passes an invented path nor false-fails a real one.
- Layer scaling counts components only.
- The report verdict reflects judge **content** — low mean soundness, `inflated`/`thin` proportionality,
  and recon-audit missed subsystems downgrade a green banner to an amber caveat (never a hard fail), and
  the diagram- and coverage-judge outputs are loaded and rendered — all guarded so a malformed judge
  payload can never crash report generation. This composes with the structured-output change's judge
  *integrity* gate (malformed/incomplete judge output still prevents a clean verdict).

The boundary is *restored*, not moved: every fix pushes a check toward "structure over emitted facts,"
and the judge-content signals qualify the presentation without ever scripting the answer.

## Capabilities

### New Capabilities
- `eval-determinism`: the corrected deterministic checks (documented-stamp detection, label-aware edge
  counting, declared-fact gating, sound grounding resolution, component-only scaling) and the
  judge-content-aware verdict — all structure-only, all guarded.

### Modified Capabilities
<!-- composes with structured-output-contract / manifest-validation-gate (schema validation + judge
     integrity are unchanged and preserved); no requirement changes to them. -->

## Impact

- Modified: `evals/reliability/diagram_checks.py` (`_typed`, `_edges`, auth gate, `_layer_of`, size,
  `_section`), `checks.py` (`_resolves_in_repo`), `report.py` (verdict + judge-content caveats + guarded
  judge-section rendering), `run.py` (load the diagram/coverage judges), `prompts/executor.md` (declare
  `roles[]` as the auth signal), `references/mermaid-diagrams.md` + `references/analytical-visuals.md`
  (document the `| Type:` stamp).
- New: `evals/reliability/test_checks.py` (a runnable self-check per fix); `schema_checks.check_sample_runs`.
