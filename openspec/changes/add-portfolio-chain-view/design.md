# Design — portfolio / chain-of-models view

## Context

Builds on the merged risk-dashboard (`build_dashboard.py` + `dashboard_template.py`, one-source-of-truth
reshape of `recon/findings/coverage.json`) and the merged deterministic run-selection (`run-plan.json` +
`Task` start gate). This is the layer above: combine N runs into one meta-view without changing any member.

## Goals / non-goals

- **Goals:** aggregate posture across products; grounded cross-product analytics; a persisted, generalizable
  relationship model; drill-down into per-product dashboards; deterministic, offline, reference-free.
- **Non-goals:** no re-derivation of member numbers; no fabricated cross-product edges; no new heuristic
  that infers relationships; no change to the single-product dashboard's look or data.

## Key decisions

1. **Reuse the per-product model verbatim.** The portfolio generator calls
   `build_dashboard.model_for_run(run_dir)` per member and also renders each member's own dashboard as the
   drill-down target. One source of truth, two altitudes; the meta-view is a superset wrapper.
2. **Persist only what can't be recomputed.** `portfolio.json` stores membership + declared edges.
   Aggregates and taxonomy overlaps are derived at build time, so they can never drift from the members.
3. **The auto-derived vs declared split** (see PORTFOLIO-MODEL-DESIGN §1). Auto-derivation is gated to
   controlled global vocabularies (CWE/ATT&CK/STRIDE) where an id is the same node across products;
   everything structural is declared with an `origin` field and validated for grounding. This is the STIX
   SRO / SPDX Relationship / OSCAL-UUID shape plus an explicit `origin`+`join_key` gate.
4. **Honest aggregation** (portfolio-dashboard research): severity = exact sum; posture = worst-of; coverage
   = assessed-weighted with uncovered = unknown (never green); riskiest = a ranked list, not an invented
   composite.
5. **Chaining rides the existing gate.** An additive `chain` block on `run-plan.json`, validated by the
   run-plan start gate — no new stop, no accidental chaining. Membership upsert is idempotent and never
   writes an edge.

## Grounding / determinism boundary

The presentation is deterministic (fixed template, fixed sections, blanks first-class); the content is the
members' emitted facts. The generator computes no new security judgment. Every aggregate reconciles to the
members; every cross-product link is either a controlled-vocabulary id-equality or a declared edge with two
resolving endpoints. A reference-free `portfolio_checks.py` asserts reconciliation + grounding, exactly like
the report↔manifest consistency checks — never an answer key, and it is skipped when no portfolio exists.

## Risks

- **Determinism boundary:** the only new "computation" is folds + id set-equality — both grounded. The risk
  is scope creep into inferred edges; the `origin` gate + endpoint-resolution rule forbid it, enforced by a
  check that rejects any dangling/derived-stored edge.
- **Back-compat:** the `run-plan.json` `chain` block and the new `portfolio.json` are additive; absent means
  standalone. No member manifest, schema, or agent contract changes. The reconciliation check is inert when
  no portfolio is present, so all existing evals stay green.
- **Freeform-name temptation:** external-dep/component names look joinable but are not normalized; auto-
  joining them would fabricate. The design forbids it; such links must be declared.
