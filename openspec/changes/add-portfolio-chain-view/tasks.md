# Tasks

## 1. Portfolio relationship model
- [ ] 1.1 Add `skills/threat-model/evals/reliability/schema/portfolio.schema.json` — `portfolio/v1`:
  `{schema, id, name, description?, version?, members[], relationships[]}`, with the fixed relationship-type
  vocabulary, `origin` gate, and required `provenance` on declared edges
- [ ] 1.2 Wire `portfolio.schema.json` into `schema_checks.py`

## 2. Portfolio generator
- [ ] 2.1 Add `skills/threat-model/scripts/build_portfolio.py` — load each member via
  `build_dashboard.model_for_run`, render each member dashboard as the drill-down target, aggregate posture
  (sum severity, worst-of, assessed-weighted coverage), derive shared CWE/ATT&CK/STRIDE, validate declared
  edges (drop + report dangling), build the chain map
- [ ] 2.2 Add `skills/threat-model/references/portfolio_template.py` — reuse `dashboard_template.CSS`;
  render the hero/KPIs, chain map, member cards with drill-down, cross-product tables, declared + rejected
  edges; add the shared-selection cross-filter JS
- [ ] 2.3 Ensure offline (inline CSS/JS, no CDN) and byte-deterministic output

## 3. Chaining in Step 0
- [ ] 3.1 Extend `run-plan.schema.json` with an optional `chain` block
  (`{portfolio_id, run_id, portfolio_path}`), additive and back-compatible
- [ ] 3.2 Add the opt-in chaining question to `SKILL.md` Step 0 (one-shot `chain=…, run-id=…` and menu row),
  default standalone, validated by the existing run-plan start gate — no new stop
- [ ] 3.3 Add the post-run membership upsert (create/append `portfolio.json` member keyed by `run_id`; never
  write a relationship) and optional meta-view regeneration

## 4. Reference-free reconciliation check
- [ ] 4.1 Add `skills/threat-model/evals/reliability/portfolio_checks.py` — assert portfolio severity == sum
  of member severities, worst-of posture, coverage roll-up excludes uncovered members, every shared link is
  ≥2-member and member-grounded, every rendered declared edge resolves, and output is deterministic + offline
- [ ] 4.2 Wire it into `run.py check`/`validate`, active only when a `portfolio.json` is present
- [ ] 4.3 Add self-check cases to `test_checks.py` (reconciling portfolio passes; a drifted aggregate, a
  dangling edge, and an uncovered-as-green all fail)

## 5. Docs
- [ ] 5.1 Update `README.md` to document the portfolio meta-view and the chaining choice
- [ ] 5.2 Note the portfolio view in `SKILL.md` outputs and the architecture docs
