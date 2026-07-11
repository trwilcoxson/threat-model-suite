## ADDED Requirements

### Requirement: Reference citations are accurate against their source standard
Every control id, article number, and framework name a reference file presents as authoritative SHALL be
correct against the standard it cites. A cited item that is fabricated or misattributed is a defect in the
reference file, not merely a documentation nit.

#### Scenario: Breach-notification citations
- **WHEN** the HIPAA reference lists breach-notification requirements
- **THEN** notification to individuals is §164.404, to the media §164.406, and to the Secretary §164.408 —
  each under Subpart D

#### Scenario: No fabricated control ids
- **WHEN** the SOC 2 reference lists the privacy criteria
- **THEN** the series begins at P1.1 (no fabricated P1.0), and each criterion's description matches the
  actual Trust Services Criteria

### Requirement: Ungroundable cross-framework mappings are marked
A cross-framework mapping that cites a control not resolvable in the local reference files SHALL be
marked as such (rather than presented as locally verifiable), so an agent following the "verify both
sides" rule is not forced to cite an unverifiable id.

#### Scenario: Unverifiable mapping flagged
- **WHEN** a mapping references a control with no entry in the corresponding local reference file
- **THEN** it carries a marker indicating it is a real control not grounded in the local reference

### Requirement: Framework methods are named accurately
A reference SHALL name a method for what it is. A simplified Likelihood×Impact matrix SHALL NOT be
presented as a standardized methodology it is not, though its numeric bands (used suite-wide and enforced
by the eval) are unchanged.

#### Scenario: Risk-rating method named honestly
- **WHEN** the frameworks reference presents the L×I matrix
- **THEN** it is named as an OWASP-inspired adaptation, not as the OWASP Risk Rating Methodology, and the
  1-4/5-9/10-16/17-25 bands are retained

### Requirement: The standardized finding format is valid markdown
The agent-output-protocol's finding-table format SHALL render as valid markdown — cell contents that
contain the table delimiter are escaped or replaced — so downstream agents can parse it. Mirror copies of
the protocol SHALL stay in sync with the canonical copy.

#### Scenario: Cross-framework cell renders
- **WHEN** a finding's Cross-Framework cell lists a MITRE id, a CWE id, and an OWASP category
- **THEN** the cell uses a non-delimiter separator so the two-column row is not split into extra cells

### Requirement: Documentation describes the current system
The architecture and diagram docs SHALL reflect the current reference-file count, agent roster (pipeline
vs standalone), emitted artifacts, and change status. Sample-run write-ups SHALL agree with their own
committed artifacts, including honest disclosure where the harness's own judge flagged a headline finding.

#### Scenario: Counts match reality
- **WHEN** the architecture doc states the reference-file and agent counts
- **THEN** they match the repository (16 reference files; 7 pipeline personas + 2 standalone companions)

#### Scenario: Write-up matches its artifacts
- **WHEN** a sample-run write-up reports a metric
- **THEN** it matches the committed `scored.json`/judge output, and a finding its own quality judge rated
  weak is disclosed as such
