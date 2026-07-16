## Why

The suite's reference files are its anti-hallucination ground truth — agents are told to cite only what
these files contain. So an error in a reference file is worse than a general doc bug: it launders a wrong
citation as "verified." The review found real errors of exactly this kind, plus stale documentation that
no longer describes the current system:

- **Companion-skill reference data:** HIPAA's breach-notification table held §164.404 content under a
  §164.408 heading; `global-privacy-regulations.md` cited LGPD's DPO at GDPR's article numbers (and had
  PIPL/PDPA/POPIA range errors); `soc2-trust-services-criteria.md` contained a fabricated `P1.0` and
  mislabeled CC7.1/CC7.5; `cross-framework-mapping.md` cited controls absent from (or contradicting) the
  local reference files; ISO/PCI had stray markers and a wrong mandatory-compliance date.
- **Framework fidelity:** `frameworks.md` presented a simple L×I matrix under the name "OWASP Risk Rating
  Methodology" (which is a different, factor-based method), and carried a retired ATT&CK technique name
  and a truncated CWE name.
- **Protocol:** the standardized finding table's Cross-Framework cell used unescaped pipes, producing a
  malformed markdown row in the very format downstream agents parse.
- **Stale docs:** `ARCHITECTURE.md` described the v5 system (11 reference files, 7-8 agents, no coverage
  ledger / analytical visuals / observability / evals / openspec); `docs/diagrams/*.mmd` carried the same
  stale counts; `VALIDATION-PATTERNS.md` referenced the wrong repositories and a superseded scorecard;
  `openspec/README.md` mislabeled an implemented change as "proposed"; and two sample-run write-ups
  disagreed with their own committed JSON.

## What Changes

- Correct every identified reference-data error against the actual standard, and add a `†` "real control,
  not grounded in the local reference" marker where a cross-framework mapping cannot be verified locally.
- Rename the misattributed risk-rating method (bands unchanged — they are load-bearing and were just
  unified); fix the retired ATT&CK / truncated CWE names (ids unchanged).
- Fix the protocol's unescaped-pipe cell in all three copies and mark the two non-canonical copies as
  mirrors so future drift is visible.
- Bring the docs back to truth: `ARCHITECTURE.md` counts + a v6 evolution row (its platform-constraint
  prose is corrected by `modernize-orchestration`), `docs/diagrams/*.mmd`, `VALIDATION-PATTERNS.md`
  framing + scorecard + link/anchor repair, `openspec/README.md` status, and the two sample-run
  write-ups reconciled with their committed artifacts (including an honest-negative caveat on a finding
  the target's own quality judge flagged as over-scoped).

The determinism boundary is untouched — this only corrects the *content* of the reference material the
agents cite and the docs that describe the system; no check moves between code and judgment.

## Capabilities

### New Capabilities
- `reference-fidelity`: the correctness contract for the reference material — every cited standard is
  accurate against its source, a mapping that can't be grounded locally is marked, mirror copies stay in
  sync, and the docs describe the current system truthfully.

### Modified Capabilities
<!-- no requirement changes to other capabilities; this corrects the data those capabilities cite. -->

## Impact

- Modified: `skills/compliance-assessment/references/{hipaa-security-rule,soc2-trust-services-criteria,
  iso27001-annex-a-controls,pci-dss-v4-requirements,cross-framework-mapping}.md`,
  `skills/privacy-impact-assessment/references/global-privacy-regulations.md`,
  `skills/threat-model/references/frameworks.md`, the three `agent-output-protocol.md` copies,
  `docs/ARCHITECTURE.md`, `docs/VALIDATION-PATTERNS.md`, `docs/diagrams/{component-map,system-architecture}.mmd`,
  `openspec/README.md`, and `evals/reliability/sample-runs/{DIAGRAM-FINDING.md,terragoat/RELIABILITY.md,
  crapi/RELIABILITY.md}`.
