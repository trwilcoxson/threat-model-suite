## Why

Phase 4 Likelihood is a subjective 1–5 vibe. `frameworks.md` asks the agent to "rate likelihood 1-5"
with a written justification, but nothing decomposes *why* — the report shows "Likelihood = 4" with prose,
and the eval can only check that `severity == band(likelihood × impact)`. There is no reference-free way to
tell an honest, defensible 4 from a hand-wave 4, because the number has no structured internal referent to
recompute against.

The T3 modern-framework research (T3-01, top-ranked, adoptability 5 / impact 5) identified the cleanest fix
available: CVSS v3.1 has a **closed-form** exploitability sub-score — `8.22 × AV × AC × PR × UI` with fixed
metric weights (FIRST.org spec; the skeptic re-derived the `3.887043` maximum). The agent already exercises
exactly the judgment CVSS asks for when it reasons about entry point, preconditions, and controls-to-bypass
in Phase 4.2. Capturing that reasoning as an `AV/AC/PR/UI` vector behind each Likelihood turns a vibe into a
decomposed, auditable justification — and yields a genuine new **reference-free** eval that recomputes the
sub-score over the agent's own emitted vector and checks it against the agent's own stated band. It is the
same style as the existing `severity == band(L × I)` consistency check: recompute a value the agent stated,
compare it to another value the agent stated. No CVSS answer key enters the loop — the agent still picks the
metric values (pure judgment, no ground truth); the code only does the arithmetic.

This is also the **dependency-root** for the rank-7 attack-defense-tree work (T3-03): defense nodes that
carry a `metric_transform` (MFA moves `PR:N→H`; a HITL gate moves `UI:N→R`) can only be checked once a CVSS
vector lives behind each leaf. Landing the vector and its formula-check first unblocks that change.

CVSS **v4.0** is deliberately not adopted: it dropped the closed form for a MacroVector lookup table, which
is a worse deterministic-eval target. Only the v3.1 **exploitability** sub-score is adopted; Impact stays on
the existing PASTA-derived 1–5 axis (the CVSS impact sub-score is not adopted).

## What Changes

- **Add an optional `cvss_vector` field to each finding** (`findings.schema.json`): a CVSS v3.1 exploitability
  vector string `AV:_/AC:_/PR:_/UI:_` constrained by a strict regex to the legal metric letters. It is
  **additive and optional** — a finding may omit it (or set `null`), so every existing manifest still
  validates and honest abstention ("this Likelihood was not decomposed") stays a first-class answer.
- **Add a ~15-line reference-free consistency check** in `evals/reliability/checks.py`, in the findings loop
  right beside the `severity-formula` check: when a finding carries a `cvss_vector`, recompute
  `8.22 × AV × AC × PR × UI` from the agent's own vector, map it to a 1–5 band via a fixed table, and record
  a `cvss-likelihood` consistency defect if it disagrees with the agent's own stated `likelihood`. The check
  never fires on a finding without the vector.
- **Publish the mapping as one explicit, auditable table** in `frameworks.md`: the frozen CVSS v3.1 metric
  weights (with a stated Scope-Unchanged pin for `PR`, since the suite does not adopt CVSS Scope), the fixed
  `3.887043` normalizer, and the normalized-quintile thresholds that carry the sub-score to a 1–5 band. The
  same table is the single source the eval implements — no second scheme.
- **Route Phase 4 to emit the vector**: add a step to SKILL.md Phase 4.3 (Likelihood Scoring) telling the
  agent to record the `AV/AC/PR/UI` vector alongside the 1–5 score, keeping the 1–5 band as the user-facing
  number (avoids CVSS false precision) and the vector as the audit trail.

## Capabilities

### New Capabilities
- `risk-metrics`: decomposed, auditable risk quantification — the CVSS v3.1 exploitability vector behind each
  Likelihood, the explicit exploitability→1–5 mapping, and the reference-free formula-check that recomputes
  the sub-score over the agent's own vector and asserts its own stated band. This is the forward-compatible
  home for the rank-7 attack-defense-tree `metric_transform` requirements.

### Modified Capabilities
<!-- Composes with structured-output-contract (adds one optional finding field; the existing "Room for absent
     data, never fabrication" requirement already sanctions optional-with-null, so no existing contract
     requirement changes) and with eval-determinism (adds one consistency check in the existing
     recompute-over-emitted-facts family; no existing check changes). No requirement changes to either. -->

## Impact

- Modified: `skills/threat-model/evals/reliability/schema/findings.schema.json` (new optional `cvss_vector`
  property, strict pattern, not in `required`), `skills/threat-model/evals/reliability/checks.py` (weight
  tables + `exploitability_band()` helper + the `cvss-likelihood` check in the findings loop),
  `skills/threat-model/evals/reliability/test_checks.py` (cases for consistent / inconsistent / absent /
  malformed vector), `skills/threat-model/references/frameworks.md` (the CVSS exploitability decomposition
  and the mapping table in the Risk Rating section), `skills/threat-model/SKILL.md` Phase 4.3 (emit the
  vector alongside the Likelihood score).
- New surface: findings may now carry a `cvss_vector` string; the eval reports a `cvss-likelihood`
  consistency defect code when present-and-inconsistent and a `bad-cvss-vector` structure code when present
  but unparseable.
