## ADDED Requirements

### Requirement: The portfolio is a persisted relationship model
The suite SHALL persist a portfolio as a `portfolio.json` file conforming to the `portfolio/v1` schema,
recording the member runs and any declared typed relationships between them. Membership SHALL reference
each member run by a stable id and a locator to its canonical manifests. Declared relationships SHALL be
typed edges whose source and target each reference a member run and a real recon element id in that run.

#### Scenario: Portfolio manifest validates
- **WHEN** a `portfolio.json` lists member runs and declared relationships
- **THEN** it conforms to the `portfolio/v1` schema, each member has a unique `run_id` and a `path`, and
  each relationship has a `type` from the fixed vocabulary, a `source` and `target` of `{run, element}`,
  `origin: "declared"`, and `provenance`

#### Scenario: Membership updates are idempotent
- **WHEN** a run whose `run_id` already exists in the portfolio is added again
- **THEN** its member entry is updated in place and no duplicate member is created, and re-deriving the
  portfolio from the same members and manifest yields byte-identical output

### Requirement: Cross-product links are grounded, never fabricated
Auto-derived cross-product links SHALL be computed only over controlled global vocabularies (CWE ids,
MITRE ATT&CK technique ids, STRIDE-LM categories), where the same identifier denotes the same taxonomy node
across products, and a link SHALL appear only when at least two members share the identifier. A member SHALL
be listed under a shared identifier only when a real finding in that member carries it. Declared structural
relationships SHALL NOT be derived from freeform names; the generator SHALL render a declared edge only when
both of its endpoints resolve to a real recon element id in the named members, and SHALL drop and report any
edge that does not.

#### Scenario: Shared weakness is a real shared taxonomy node
- **WHEN** the generator derives shared-CWE and shared-ATT&CK links
- **THEN** every link is shared by at least two members, and every member listed under a link carries that
  CWE or technique in one of its findings, with no link derived from a freeform dependency or component name

#### Scenario: A dangling declared edge is rejected, not drawn
- **WHEN** a declared relationship names a `run` or `element` that does not resolve to a real recon element
  id in a member
- **THEN** the edge is excluded from the rendered relationships and reported in a rejected-edges list with
  a reason, and no fabricated edge is shown

### Requirement: The portfolio meta-view aggregates honestly and reconciles to the members
The portfolio meta-view SHALL derive every aggregate only from the member runs' canonical manifests. The
portfolio severity counts SHALL equal the sum of the member severity counts; the portfolio posture SHALL be
a worst-of roll-up so that any member at CRITICAL makes the portfolio CRITICAL; and the coverage roll-up
SHALL count only members that have a coverage ledger, treating a member with no ledger as unknown rather
than covered. A reference-free check SHALL verify the aggregates reconcile to the members.

#### Scenario: Aggregates reconcile to the members
- **WHEN** the reconciliation check runs over a generated portfolio meta-view and its member manifests
- **THEN** the portfolio severity counts equal the sum of the member `findings.summary_counts`, the posture
  is CRITICAL when any member is CRITICAL, and the coverage roll-up excludes members that have no
  `coverage.json`

#### Scenario: An uncovered product is unknown, not green
- **WHEN** a member run has no coverage ledger
- **THEN** the meta-view shows that member's coverage as unknown and excludes it from the assessed count and
  the coverage numerator, and never presents it as fully covered

### Requirement: The portfolio meta-view is a self-contained offline artifact that drills into members
The portfolio meta-view SHALL be a single self-contained `portfolio.html` with inline CSS and JavaScript
and no external network resource, rendering offline like the suite's other artifacts, and byte-identical for
the same members and manifest. It SHALL present each member with a link that opens that product's own
generated dashboard, so the meta-view pivots down into the unchanged per-product view.

#### Scenario: Meta-view renders offline and deterministically
- **WHEN** the portfolio meta-view is generated twice from the same members and opened without network
- **THEN** it renders fully, references no `http(s)://` loaded resource, and the two files are byte-identical

#### Scenario: Drill-down opens the member's own dashboard
- **WHEN** a user follows a member's drill-down link in the meta-view
- **THEN** the member's own per-product dashboard opens, produced by the same dashboard generator, with no
  re-derived or divergent numbers

### Requirement: The portfolio meta-view is templated and degrades gracefully
The portfolio meta-view SHALL have a fixed section inventory for every portfolio. When a member has thin or
absent data, or the portfolio has no shared weaknesses or no declared relationships, those sections SHALL
render honest empty states and the overall layout SHALL remain intact.

#### Scenario: A thin member keeps the layout
- **WHEN** the portfolio includes a member with few findings, no coverage ledger, and no external
  dependencies
- **THEN** that member's card and every portfolio section still render in place, empty areas show an
  empty/unknown state, and no section is missing or broken

#### Scenario: No shared links renders an empty state
- **WHEN** no CWE or technique is shared across members and no relationship is declared
- **THEN** the shared-weakness, attack-surface, and relationships sections render empty states rather than
  erroring or fabricating a link

### Requirement: The portfolio view is additive and backward compatible
The portfolio capability SHALL NOT change any existing manifest, schema, agent contract, or output. It SHALL
reuse the per-product dashboard generator to build member views and SHALL be produced only when a portfolio
is requested. Runs and single-product dashboards that predate the portfolio view SHALL remain valid.

#### Scenario: Existing outputs unchanged
- **WHEN** a portfolio meta-view is generated
- **THEN** every member's per-product manifests and dashboard are produced unchanged, and no existing output
  is altered

#### Scenario: Portfolio is opt-in
- **WHEN** no portfolio is requested
- **THEN** no `portfolio.json` or `portfolio.html` is produced and the single-product flow is unaffected
