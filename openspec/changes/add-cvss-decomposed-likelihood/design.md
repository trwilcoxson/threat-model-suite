## Context

The recommendation is T3-01 from the modern-framework research (`t3-frameworks/REPORT.md`), the top-ranked
item (adoptability 5 / impact 5 / effort 2 / risk low). Its load-bearing claim — that CVSS v3.1 exploitability
is closed-form and its weights are fixed — was verified by a dedicated skeptic against the FIRST.org v3.1
spec, who re-derived the maximum sub-score `8.22 × 0.85 × 0.77 × 0.85 × 0.85 = 3.887043`. The design grounds
on the current suite: the `severity == band(likelihood × impact)` consistency check in
`evals/reliability/checks.py`, the `findings.schema.json` contract (where the vector field lands), and
SKILL.md Phase 4 (risk quantification). It is the dependency-root for the rank-7 attack-defense-tree change.

## The determinism boundary (preserved by construction)

This change is **determinism-clean by construction** and is, if anything, the purest example of the boundary
in the whole suite:

- **The agent does all the reasoning.** It picks the four metric values — Attack Vector, Attack Complexity,
  Privileges Required, User Interaction — from its Phase 4.2 attack-path analysis. There is no ground truth
  for a vector; it is judgment, exactly like the existing Likelihood number.
- **The code does only arithmetic over emitted facts.** The check recomputes `8.22 × AV × AC × PR × UI` from
  the agent's *own* stated vector and compares the derived band to the agent's *own* stated `likelihood`. Both
  sides of the comparison are values the agent emitted. This is the identical shape to `severity-formula`
  (`severity` recomputed from the agent's own `likelihood × impact`). No external CVSS database, no per-target
  answer key, no expected finding.
- **Abstention is first-class.** The field is optional. A finding with no `cvss_vector` (or an explicit
  `null`) is a valid, honest "this Likelihood was not decomposed" — every pre-existing manifest still
  validates and the check simply does not fire. Nothing forces the agent to invent a vector, mirroring the
  existing "Room for absent data, never fabrication" contract requirement.
- **The mapping table is a consistency relation, not an answer key.** The exploitability→1–5 table does not
  say *which* Likelihood a given threat has; it says the Likelihood must be internally consistent with the
  vector the agent chose. Change the vector and the required band changes with it. It scripts form, not
  content — the same way `band()` scripts the severity–score relation without scripting the score.

## Decisions

1. **Vector as a strict string, validated in the schema; parsed in the check.** The field is a CVSS-canonical
   string `AV:N/AC:L/PR:N/UI:R`, constrained by `^AV:[NALP]/AC:[LH]/PR:[NLH]/UI:[NR]$`. This is the most
   auditable form (a human reads the whole justification at a glance in the report), pins every metric to its
   legal letters at the **structure** layer (a bad letter is a schema violation, not a silent pass), and the
   check parses it with one regex. A structured `{av, ac, pr, ui}` object was rejected as more nodes for no
   gain — the regex already enum-constrains each metric.

2. **Adopt only the exploitability sub-score; not Scope, not the impact sub-score.** The suite keeps its
   PASTA-derived Impact 1–5 (research open-question #4). Because CVSS Scope is not adopted, the `PR` weight is
   otherwise ambiguous (v3.1 gives `PR` different weights under Scope-Changed). **Decision: pin the
   Scope-Unchanged weights** `PR:{N:0.85, L:0.62, H:0.27}` and state it in the mapping table. This keeps the
   formula closed-form and fully reproducible. (Ceiling: if a future change adopts Scope, `PR` becomes
   scope-dependent and the table gains a Scope column — noted for the attack-defense-tree follow-on.)

3. **Exploitability→1–5 via normalized quintiles of the fixed maximum.** Divide the sub-score by the frozen
   `3.887043` maximum to get a fraction in `(0, 1]`, then floor into fifths: `band = min(5, ⌊frac × 5⌋ + 1)`.
   Worked: `AV:N/AC:L/PR:N/UI:N → 5` (trivially exploitable), `AV:N/AC:L/PR:N/UI:R → 4`,
   `AV:N/AC:H/PR:L/UI:N → 3`, `AV:L/AC:H/PR:H/UI:R → 1`. Quintiles were chosen over hand-picked thresholds
   because reproducibility *is* auditability — anyone can rederive the boundary. **The thresholds are v1 and
   expected to be tuned against real runs** (research open-question #4); the table is versioned so a retune is
   a one-line table edit, not a code change. This is a `ponytail:` deliberate corner: a naive uniform
   quintile split, upgrade path = recalibrate the five thresholds from a corpus of scored runs.

4. **Exact band equality, not a ±1 tolerance.** The check asserts `likelihood == exploitability_band(vector)`
   exactly, mirroring the tolerance-free `severity-formula` check. A ±1 tolerance was considered (it would
   absorb v1-threshold noise) and rejected: it makes the check nearly toothless (almost any vector would be
   "consistent" with almost any adjacent band) and it breaks the parallel with the existing exact severity
   check. If early runs surface friction, the fix is to tune the thresholds (Decision 3), not to blunt the
   check.

5. **Optional/additive, not required.** Requiring the vector on every finding would break every existing
   manifest and force fabrication on findings the agent legitimately did not decompose (e.g. a summary-scored
   LOW-likelihood threat under the Solo shortcut). Optional-with-null is the back-compatible, abstention-honest
   choice, and it is exactly what the existing contract's "Room for absent data" requirement already sanctions
   — so no existing requirement changes. A later change may *promote* the vector to required for
   MEDIUM-or-higher findings once adoption is proven; that is out of scope here.

6. **Check lives in `checks.py`, beside the severity check — not a new module.** It is one arithmetic
   consistency check in the same findings loop, sharing the same `Defects` sink and the `consistency` layer.
   A separate module would be ceremony for ~15 lines. (Contrast: `diagram_checks`/`coverage_checks` are
   separate because they own large, self-contained sub-domains; this does not.)

## Alternatives considered

- **CVSS v4.0 base score.** Rejected: v4.0 replaced the closed-form sub-score with a MacroVector lookup
  table, which is a worse deterministic-eval target (no arithmetic to recompute). v3.1 exploitability is the
  right target precisely because it is a formula. AT/Automatable can ride along as optional tags later if
  wanted, but not as the band driver.
- **Full CVSS base score (exploitability + impact).** Rejected: duplicates the suite's PASTA-derived Impact
  axis and imports CVSS's C/I/A impact model the suite deliberately does not use. Only exploitability maps
  onto Likelihood.
- **Free-text likelihood justification only (no structured vector).** Rejected: prose is not
  machine-recomputable, so it yields no reference-free eval — which forfeits the entire point of T3-01.

## Risks / trade-offs

- **v1 thresholds will need a retune.** Mitigated by versioning the table and keeping it a data edit; a
  tasks item calibrates it against sample runs before the check is treated as blocking.
- **One more field for the agent to fill.** Marginal — Phase 4.2 already produces the underlying reasoning;
  the vector is a compact restatement, and it is optional so it never blocks a run.
- **Deferred:** promoting the vector to required for scored findings; adopting AT/Automatable tags; the
  attack-defense-tree `metric_transform` semantics (rank 7) that build on this vector. All out of scope.
