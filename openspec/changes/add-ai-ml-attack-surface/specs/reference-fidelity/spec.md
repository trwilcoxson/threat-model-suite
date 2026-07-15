## ADDED Requirements

### Requirement: ATLAS and OWASP-LLM Top-10 are reference taxonomies, never answer keys
`frameworks.md` SHALL carry MITRE ATLAS and the OWASP-LLM Top-10 as reference taxonomy tables in the same
style as the existing ATT&CK/CWE tables — prompt guidance the agent reasons with — together with a fixed
OWASP-LLM→ATLAS crosswalk. These tables SHALL be guidance only: no eval SHALL require any id from them to
appear in a finding, and the agent SHALL retain the existing "No matching ID in reference set — manual
verification recommended" escape hatch. The tables SHALL use the verified official OWASP-LLM identifiers
and titles.

#### Scenario: Taxonomy guides, never dictates
- **WHEN** the agent maps an AI/ML threat to an ATLAS or OWASP-LLM id
- **THEN** it selects the id from the `frameworks.md` reference tables (or records "No matching ID in
  reference set — manual verification recommended"), and no deterministic check requires any particular id
  to be present

### Requirement: Framework ID Verification extends to the ATLAS and OWASP-LLM namespaces
The Framework ID Verification rules in `frameworks.md` SHALL extend to ATLAS and OWASP-LLM ids: only ids
listed in the reference tables are used, ids not in the tables are described in plain text with the
manual-verification note, ids are never fabricated, and Phase 6 (False Positive Validation) cross-checks
every ATLAS/OWASP-LLM id against the tables — exactly as it already does for ATT&CK and CWE ids.

#### Scenario: AI ids cross-checked in Phase 6
- **WHEN** Phase 6 verifies the framework ids in the findings
- **THEN** every `atlas[]` id and every OWASP-LLM checklist id is verified against the `frameworks.md`
  tables using the same rules applied to ATT&CK and CWE ids
