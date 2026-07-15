# Tasks

## 1. Schema: the optional vector field
- [x] 1.1 findings.schema.json: add `cvss_vector` to a finding's `properties` — `{ "type": ["string","null"], "pattern": "^AV:[NALP]/AC:[LH]/PR:[NLH]/UI:[NR]$" }` with a description; do NOT add it to `required` (additive / back-compat)
- [x] 1.2 Confirm an existing sample-run findings.json (no `cvss_vector`) still validates against the updated schema

## 2. Eval: the reference-free formula-check
- [x] 2.1 checks.py: add the frozen CVSS v3.1 weight tables (`AV`, `AC`, `PR` Scope-Unchanged, `UI`) and the `EXPLOIT_MAX = 3.887043` constant near the module `band()` helper
- [x] 2.2 checks.py: add `exploitability_band(vector) -> int` — parse the vector, compute `8.22 * AV * AC * PR * UI`, normalize by `EXPLOIT_MAX`, return `min(5, int(frac*5)+1)`
- [x] 2.3 checks.py: in the findings loop, after the `severity-formula` check, when `f.get("cvss_vector")` is truthy, compare `int(f["likelihood"])` to `exploitability_band(vec)`; on mismatch add a `consistency`/`cvss-likelihood` defect naming the stated band, the derived band, and the vector
- [x] 2.4 checks.py: guard parse failure — an unparseable/partial vector that slipped past the schema records a `structure`/`bad-cvss-vector` defect (never a silent pass); the check does not fire when the field is absent or `null`

## 3. Frameworks reference: the explicit mapping table
- [x] 3.1 frameworks.md (Risk Rating section): add a "Decomposed Likelihood — CVSS v3.1 exploitability" subsection with the frozen weight table (AV N/A/L/P, AC L/H, PR N/L/H Scope-Unchanged, UI N/R), the `8.22 × AV × AC × PR × UI` formula, and the `3.887043` normalizer
- [x] 3.2 frameworks.md: add the normalized-quintile threshold table (fraction → 1–5 band) with the four worked examples; label it v1 / tunable and state it is the single source the eval implements
- [x] 3.3 frameworks.md: state the two scoping decisions explicitly — only the exploitability sub-score is adopted (Impact stays PASTA-derived 1–5), and `PR` uses Scope-Unchanged weights because CVSS Scope is not adopted

## 4. Pipeline: emit the vector in Phase 4
- [x] 4.1 SKILL.md Phase 4.3 (Likelihood Scoring): instruct the agent to record the `AV/AC/PR/UI` vector alongside the 1–5 score, drawing the metric values from the Phase 4.2 attack path; keep 1–5 as the user-facing number and the vector as the audit trail
- [x] 4.2 SKILL.md Phase 4 Output Format: add `CVSS Vector` to the scored-threat table columns (optional per row)
- [x] 4.3 Note in the Phase 4 guidance that the vector is optional — a threat whose Likelihood is not decomposed omits it rather than inventing metrics

## 5. Tests
- [x] 5.1 test_checks.py: a finding with `cvss_vector` whose band matches `likelihood` → no `cvss-likelihood` defect
- [x] 5.2 test_checks.py: a finding whose `likelihood` disagrees with the vector's band → one `cvss-likelihood` consistency defect
- [x] 5.3 test_checks.py: a finding with no `cvss_vector` (and one with `null`) → the check does not fire (back-compat / abstention)
- [x] 5.4 test_checks.py: assert the four worked-example vectors band to 5 / 4 / 3 / 1 (locks the mapping table against drift)

## 6. Verify
- [x] 6.1 `openspec validate add-cvss-decomposed-likelihood --strict`
- [x] 6.2 Run the eval over a sample run with and without vectors; confirm back-compat (no new defects on vector-less runs) and that a deliberately inconsistent vector is flagged
- [ ] 6.3 Calibrate the v1 quintile thresholds against the sample-run corpus before treating `cvss-likelihood` as a blocking defect
