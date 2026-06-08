# Coverage judge — are the ledger states correct? (semantic)

`coverage_checks.py` confirms the ledger is *structurally* sound: every applicable item has a terminal
state, `present`/`partial` are grounded, `unknown` is noted. You judge whether those **states are
correct** against the real system — not their presence.

## Inputs
- `{repo}` — the target.
- `{run_dir}/coverage.json` — the ledger (context + items) + `{run_dir}/recon.json`, `findings.json`.
- `references/coverage-taxonomy.json` — the item set (ids, sections, tiers, preconditions).

## Judge (sample across sections; prioritize the consequential items)
1. **`not-applicable` is real** — for items the ledger calls not-applicable, confirm the system
   genuinely lacks that concern (not a missed area). Flag any that actually apply.
2. **`absent` is real** — for items called absent, confirm the thing is genuinely not present (this is
   a missed-finding check: an "absent control" that actually exists, or an "absent" that should be a
   finding). Flag mismatches.
3. **`present`/`partial` detail is accurate** — spot-check that the recorded detail and source match
   what's in the repo; flag overstated or wrong claims.
4. **`unknown` is honest** — was it genuinely indeterminable from the sources, or discoverable with
   reasonable effort? Flag unknowns that the materials actually answer.
5. **Context flags are right** — does the declared `context` (has_api, multi_tenant, has_ai_ml, …)
   match the real system? A wrong flag mis-gates a whole section.

## Output (JSON)
```json
{ "coverage_soundness": 0.0, "verdict": "robust|adequate|weak",
  "issues": [ {"item_id":"...", "kind":"wrong-na|missed-absent|overstated-present|answerable-unknown|wrong-context", "detail":"...", "severity":"high|med|low"} ],
  "notes":"..." }
```
`coverage_soundness` = fraction of sampled items whose state is correct. Cite the repo file when you
flag something. The deterministic layer already proved the ledger is complete and grounded; you are
checking whether it tells the truth.
