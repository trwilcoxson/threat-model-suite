# Tasks

## 1. Companion-skill reference data
- [x] 1.1 HIPAA: §164.404/.406/.408 retitled + Subpart D; safeguard counts recomputed from the file's rows
- [x] 1.2 global-privacy-regulations: LGPD DPO Art. 41; PIPL penalties 66-71; PDPA Part labels; POPIA §72
- [x] 1.3 SOC 2: remove fabricated P1.0; CC7.1 detection, CC7.5 recovery
- [x] 1.4 cross-framework-mapping: ground the ungroundable cells; add the `†` marker + footnote
- [x] 1.5 ISO A.5.19/A.5.21 stray (NEW) markers removed; PCI v4.0 mandatory date corrected

## 2. Flagship references
- [x] 2.1 frameworks.md: rename the risk-rating method (bands unchanged); T1046 + CWE-732 names
- [x] 2.2 agent-output-protocol (3 copies): fix the unescaped-pipe cell; mirror-header on the 2 non-canonical copies (bodies byte-identical)

## 3. Docs
- [x] 3.1 ARCHITECTURE.md: 11→16 references, 7→9 agents (7 pipeline + 2 standalone), add coverage/visuals/observability/evals/openspec, v6 evolution row (platform prose left to modernize-orchestration)
- [x] 3.2 docs/diagrams/*.mmd: count refreshes + new output artifacts
- [x] 3.3 VALIDATION-PATTERNS.md: repo framing, Pattern 25 reconciled, links flattened, stale SKILL.md anchors delinked
- [x] 3.4 openspec/README.md: add-coverage-ledger status truthful
- [x] 3.5 sample-runs: DIAGRAM-FINDING table → scored.json; terragoat honest-negative caveat; crAPI file count

## 4. Verify
- [x] 4.1 residual-error grep across companion references → 0 remaining known errors
- [x] 4.2 counts match `ls references/` (16) and `ls agents/` (9)
- [ ] 4.3 follow-up citation audit for the flagged out-of-scope items (one PDPA range; VALIDATION-PATTERNS reference-file line anchors)
- [x] 4.4 `openspec validate correct-reference-data --strict`
