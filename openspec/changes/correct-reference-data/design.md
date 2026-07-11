## Context

The reference-data errors were found by the team-skills and knowledge-refs reviews and each corrected
against the actual standard (HIPAA Security/Breach rules, LGPD/PIPL/PDPA/POPIA, SOC 2 TSC 2017, ISO
27001:2022, PCI-DSS v4, MITRE ATT&CK, CWE). The doc-truth items were found by the docs-openspec review.

## The determinism boundary (untouched)

This change corrects *content* — the accuracy of the reference material agents cite and the docs that
describe the system. No deterministic check and no judge prompt changes; the eval still enforces the same
structure over the same emitted facts. Fixing the reference data strengthens the anti-hallucination
architecture (verify-against-local-reference + `[UNVERIFIED]` marker + validator rejection) by making the
"local reference" trustworthy.

## Decisions

1. **Correct against the source, mark what can't be grounded.** Where a standard is unambiguous, fix the
   citation. Where a cross-framework mapping references a real control that simply isn't in the local
   reference file, keep the real control and add a `†` marker + footnote rather than delete a legitimate
   mapping — the agent then knows it is not locally verifiable.
2. **Keep the numeric bands, fix the name.** The L×I bands are load-bearing (the eval enforces them and
   they were just unified across the suite); only the misattributed *name* changes, with a one-line note
   that it is a simplified OWASP-inspired adaptation.
3. **One canonical protocol, visible mirrors.** The three `agent-output-protocol.md` copies stay
   body-identical; the two non-canonical copies gain a mirror header so a future edit that drifts them is
   visible (the pipeline still flattens all three into one refs view, where copy order would otherwise
   hide drift).
4. **Docs describe today, honestly.** Architecture/diagram counts and the emitted-artifact list are
   brought current; the v6 evolution row summarizes the post-v5 changes. `VALIDATION-PATTERNS.md` is
   reframed to this repo and its scorecard reconciled with the reference-free harness; stale SKILL.md line
   anchors are delinked rather than re-pinned against a file the flow change restructured. Sample-run
   write-ups are reconciled with their committed JSON, and the honest-negative culture is extended (a
   headline finding the target's own quality judge flagged as over-scoped is disclosed, not hidden).

## Risks / trade-offs

- A few citations outside the explicitly-named set (e.g. one PDPA section range, some VALIDATION-PATTERNS
  reference-file line anchors) are flagged for a follow-up audit rather than corrected here, to keep the
  change scoped to verified fixes. Those flags are recorded so the next pass can close them.
- The platform-constraint prose in `ARCHITECTURE.md` §4.1/§4.6/§8 is intentionally left to
  `modernize-orchestration` (a TODO marker is placed) so the two changes don't overlap on the same
  paragraphs.
