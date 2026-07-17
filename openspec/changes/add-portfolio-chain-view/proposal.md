## Why

The suite produces one self-contained risk dashboard per product run, but there is no way to see **many
products together**. An owner assessing a fleet has N independent runs and no combined posture, no
cross-product weakness view, and no way to record that two products are related.

- **No portfolio roll-up.** Combined severity, portfolio coverage, and "which product is riskiest" must be
  eyeballed across N separate dashboards.
- **Cross-product risk is invisible.** A `CWE-306` or an ATT&CK `T1190` shared by four products — the
  portfolio-wide weakness that a single fix would shrink across the fleet — is nowhere surfaced.
- **Relationships between products aren't modeled.** A shared datastore, a shared base image, an
  upstream/downstream trust dependency — real structural links across products — have no home, so they are
  neither recorded nor validated.
- **Chaining is undefined.** Nothing lets a run declare, deterministically, that it belongs to a portfolio.

## What Changes

- **A portfolio meta-view artifact.** A new self-contained offline `portfolio.html` "chain of models"
  dashboard, same discipline and theme as the per-product one: portfolio posture (worst-of), aggregate
  severity, coverage roll-up, a chain map of the products, a riskiest-product ranking, member cards that
  **drill down** into each product's own dashboard, and grounded cross-product analytics.
- **A persisted relationship model — `portfolio.json` (`portfolio/v1`).** Stores portfolio membership and
  **declared typed edges** between products, each referencing real recon element ids on both ends with
  provenance. A typed-edge-over-resolvable-ids shape (STIX/SPDX/OSCAL lineage).
- **Grounded cross-product links.** Taxonomy overlaps (shared CWE / ATT&CK / STRIDE) are **auto-derived**
  from the members (same global id = same node); structural links are **declared** and validated — an edge
  whose endpoint does not resolve is dropped and reported, never drawn.
- **A chaining question in Step 0.** The deterministic run-selection gains an opt-in "add this run to a
  portfolio/chain" choice, recorded in `run-plan.json`; membership upsert is deterministic and idempotent.
- **A reference-free reconciliation check.** A new deterministic check verifies the meta-view's aggregates
  reconcile to the members, every cross-product link is grounded, and no declared edge is dangling.

## Capabilities

### New Capabilities
- `portfolio-view`: the persisted `portfolio.json` relationship model; the deterministic portfolio
  meta-view generator; the grounded cross-product analytics (auto-derived taxonomy overlaps + validated
  declared edges); the drill-down into member dashboards; and the reference-free reconciliation check.

### Modified Capabilities
- `run-selection`: adds an opt-in chaining choice to Step 0 and an additive `chain` block to the
  `run-plan.json` fact, so a run can deterministically record portfolio membership. No existing run-plan
  behaviour changes; absent `chain` means standalone.

## Impact

- New: `skills/threat-model/scripts/build_portfolio.py`,
  `skills/threat-model/references/portfolio_template.py`,
  `skills/threat-model/evals/reliability/schema/portfolio.schema.json`,
  `skills/threat-model/evals/reliability/portfolio_checks.py`, self-check cases in `test_checks.py`.
- Modified (additive only): `skills/threat-model/evals/reliability/schema/run-plan.schema.json` (optional
  `chain` block), `skills/threat-model/SKILL.md` (Step 0 chaining question + post-run membership upsert),
  `README.md` (document the portfolio view). No existing manifest, agent contract, or output changes; the
  per-product dashboard is embedded and drilled into, never re-derived.
