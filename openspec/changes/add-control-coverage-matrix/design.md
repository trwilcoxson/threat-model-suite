## Context

From TRACK T2 (`research/t2-artifacts/REPORT.md`, rec T2-03): a threat-to-control coverage matrix is the
cheapest genuinely-additive artifact in the catalogue, and its enabling schema — promoting free-text
`remediation` into addressable control objects — is shared with T2-02 attack-defense trees (rank 7). The
skeptic's central constraint (§3 of the report) is that an artifact is only worth building if its *novel*
content is grounding/coverage-shaped, not correctness-shaped. The control matrix qualifies: its one new
property — "does this finding have any control?" — is a coverage check over the model's own findings and
never asks whether the control is *right*.

The engine decision (D2 flagship, Mermaid `@{shape: icon}` + ELK for phase-1) is settled and orthogonal:
the matrix is a markdown table, not a rendered graph, so it is engine-independent.

## The determinism boundary (how each new check preserves it)

Agents do all the reasoning: *which* control addresses a finding, whether a risk is acceptable, and which
NIST/D3FEND id is the right normalized name are all agent/judge decisions. The deterministic layer only
enforces structure over the agent's own emitted facts, and always allows honest abstention. Every new
check is one of the four permitted shapes:

- **Well-formedness.** `controls[].id` matches `^CTL-[0-9]{3}$`; `framework_ref`, when present, matches a
  shaped NIST-800-53 / D3FEND pattern. This is exactly the `malformed-cwe` / `malformed-mitre` format
  check in `checks.py` — format only, no membership assertion in the offline eval.
- **Internal consistency (agent-fact vs agent-fact).** `control_disposition == "mitigated"` **iff**
  `controls` is non-empty. Both sides are values the agent itself emitted; the check recomputes one from
  the other and flags disagreement — the same species as `severity == band(L × I)`. No external truth.
- **Coverage (ratio over the model's own findings).** A finding that is neither controlled nor explicitly
  dispositioned is *flagged* as an uncovered gap; the profile reports counts by class and a covered
  fraction. This is the defensive dual of `uncovered-surface` and the exact shape of the coverage ledger's
  "every applicable item reached a terminal state." The set being covered is the model's own findings —
  never an external control catalogue.
- **Honest abstention (never a failure).** `accepted-risk` and `none` are first-class terminal states that
  **pass** when they carry a `disposition_note`, precisely mirroring the ledger's `unknown`/`absent`
  requiring a note. Zero-control is a *flag*, not an auto-fail: the eval surfaces the gap in the profile;
  it does not reject the run for it.

What the eval never does, by construction: assert that a control is the *correct* remediation, that
`accepted-risk` is a *justified* decision, or that a `framework_ref` is the *right* mapping for the threat.
Those are the agent's job (and the coverage/security judge's), verified the same way ATT&CK/CWE ids are
today — against the reference tables in `frameworks.md`, in Phase 6, not in the deterministic eval.

## Decisions

1. **Control objects live on the finding; `remediation` stays.** `controls[]` is added to each finding
   (not a separate top-level manifest section) because coverage is a per-finding property and the counter-
   edge relation (rank 7) is per-finding. `remediation` is retained required and unchanged so migration is
   strictly additive: a legacy `findings.json` with only `remediation` validates, renders, and is simply
   *flagged* as control-coverage-unknown until it is migrated. No big-bang cutover.

2. **Disposition is an explicit enum + note, not inferred from an empty array.** An empty `controls[]` is
   ambiguous — it could mean "risk accepted", "genuinely no control applies", or "agent didn't get to it".
   The eval must not guess. `control_disposition ∈ {mitigated, accepted-risk, none}` + `disposition_note`
   makes the agent state which it is, and the note is the evidence honest abstention requires. This is the
   `unknown`-needs-a-note rule from `coverage_checks.py`, applied to findings.

3. **The coverage property lives in `checks.py`, not a new module.** `checks.py` already iterates every
   finding, already owns the `consistency` and `coverage` defect layers, and already has the grounding
   resolver. Folding the control-coverage property into that loop (a `control` defect layer + a
   `control_coverage` scores block) is the smallest correct change; a standalone `control_checks.py` would
   duplicate the iteration for no benefit. The matrix *rendering* check lives in
   `diagram_checks.analytical_checks` beside the STRIDE / RBAC / heat-map checks it is a sibling of.

4. **The matrix is a markdown table verified like the STRIDE matrix.** `analytical_checks` finds the table
   by its columns (a control-id / disposition column set), then checks presence and faithful projection
   (every finding id appears; a zero-control finding shows a `GAP` cell) — presence/consistency only, never
   whether the control listed is correct. Gate: ≥1 finding exists (a run with only `no_issue_surface` and
   no findings needs no matrix). This reuses the `_md_tables` / `_section` helpers already in the module.

5. **`framework_ref` is optional and format-checked; membership is agent-verified.** The offline eval
   cannot (and per the boundary must not) assert that `SC-7` is the *right* control for a finding — that is
   a mapping judgment. So `framework_ref` gets a shaped-pattern format check in the eval, and the
   authoritative NIST-800-53 / D3FEND reference set plus the "never fabricate; unknown → plain text" rule
   go into `frameworks.md`, verified in Phase 6 — byte-for-byte the treatment ATT&CK and CWE ids already
   get. This keeps the determinism boundary intact and adds no offline reference-data dependency.

6. **`counters[]` is reserved, not consumed.** The control object is shaped now so the rank-7 attack-
   defense-tree change can attach `counters:[attackNodeId]` without a second schema migration. In *this*
   change `counters[]` is optional and defaults empty, and no grounding is enforced on it — the attack-node
   id namespace and its grounding check are defined by rank 7. Reserving the field here is the entire
   "shared schema enabler" deliverable; enforcing it here would couple this change to work that has not
   landed.

7. **`CTL-NNN` is a distinct id namespace, aligned-not-merged with the report's `R-NNN` roadmap.** The
   markdown report already uses `R-NNN` for remediation-roadmap items (report-template §VIII). Rather than
   overload that markdown convention into the machine manifest, controls get their own `CTL-NNN` space in
   `findings.json`; a control's fuller remediation plan may still be detailed under an `R-NNN` roadmap
   item. Unifying the two namespaces is a follow-up (see open questions), not a prerequisite.

## Risks / trade-offs

- **Two id namespaces (`CTL-NNN` and `R-NNN`) during migration** could read as duplication. Mitigated by
  keeping `CTL-NNN` the addressable *control object* (what the matrix and counter-edges point at) and
  `R-NNN` the report's *roadmap sequencing*; a later change can unify them once both have settled.
- **Legacy findings flag as uncovered** until migrated. This is intended (the flag is the feature), but it
  means the `control_coverage` covered-fraction starts low on old runs — it is a profile signal, not a
  gate, so it does not break any run.
- **`counters[]` is defined before its consumer exists.** If rank 7 chooses a different attack-node id
  shape, `counters[]`'s element type may need revisiting — cheap, since it is an untyped string array with
  no enforced grounding here.
- **Deferred:** unifying `CTL-NNN` with `R-NNN`; any deterministic membership check of `framework_ref`
  against an offline NIST-800-53 / D3FEND allowlist (kept agent-verified for now, consistent with ATT&CK/CWE).
