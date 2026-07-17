## Why

The suite emits `report.html`, `report.docx`, `report.pdf` and `executive-summary.pptx`, plus the
analytical visuals — all excellent for a security reader, none of them a single at-a-glance
**product-risk view** an executive or product owner can absorb in one screen.

- **No consolidated risk dashboard.** The rich facts the pipeline discovers (severity mix, likelihood ×
  impact, coverage %, STRIDE/MITRE/CWE spread, kill chains, component and supply-chain risk) live spread
  across `recon.json`, `findings.json`, `coverage.json` and the report. There is no one artifact that
  composes them into an executive risk picture.
- **No self-contained shareable single view.** The dashboard is one offline HTML file (inline CSS/JS,
  no CDN) that renders the whole risk posture of a run — the most impressive single artifact to hand to
  a stakeholder.

## What Changes

- **New output: `dashboard.html`** — a templated, data-rich, self-contained product-risk dashboard
  generated deterministically from a run's manifests, added as a new report-analyst (Phase 8) output.
  All existing outputs are unchanged.
- **Deterministic generator.** A new script transforms `recon.json` + `findings.json` + `coverage.json`
  (+ the ATT&CK navigator layer when present) into a derived analytics model, then renders a fixed HTML
  template. The agent emits the manifests; the deterministic transform owns all presentation — the same
  split as the existing `recon_to_d2.py` semantic-source path.
- **Interactive linked-model explorer over the run's real diagram.** The dashboard embeds the run's own
  rendered structural diagram (the `recon_to_d2.py`/`structural-diagram` render of this run's `recon.json`
  — same nodes, layout, and dataflow edges as the diagram the flow emits elsewhere, node ids = recon
  element ids `C1`/`D1`/`E1`/`X1`) and layers pan/zoom + a precomputed linked data model over it, so any
  data point (a node, finding, framework token, kill chain, severity band) cross-highlights and
  cross-filters every related point across the diagram and panels. Edges are the run's real
  `recon.dataflows[]`, not edges synthesized from finding co-reference; all relationships derive only
  from real ids in the manifests (no invented edges, no bespoke system-map layout).
- **Templated with graceful blanks.** The template has a fixed section inventory; any absent field
  (e.g. `findings.controls[]`, `cvss_vector`, `recon.dataflows[]`) renders an empty "—/No evidence
  surfaced" state, never a broken layout.
- **Reference-free grounding + cross-output consistency eval.** A new deterministic check verifies every
  headline number traces to a manifest and no finding id is shown that is not in `findings.json`, and a
  reference-free cross-output consistency check confirms the dashboard reconciles to the run's canonical
  manifests (severity counts == `findings.summary_counts`, coverage % == `coverage.json`, diagram nodes
  == recon elements, kill chains == `findings.kill_chains`) and embeds the run's real structural diagram
  — preserving the determinism boundary and the single-source-of-truth discipline (no golden answer,
  property checks over emitted facts).

## Capabilities

### New Capabilities
- `risk-dashboard`: the templated, grounded, offline product-risk dashboard artifact and the
  reference-free checks that verify its groundedness and templated degradation.

### Modified Capabilities
<!-- composes with the existing report generation and coverage-ledger capabilities; adds a new
output alongside them, no requirement changes to those. -->

## Impact

- New: `skills/threat-model/scripts/build_dashboard.py` (+ template module) — the deterministic
  generator; `skills/threat-model/references/dashboard-template.*` — the HTML template;
  `skills/threat-model/evals/reliability/dashboard_checks.py` — reference-free grounding/structure
  checks; self-check cases in `test_checks.py`.
- Modified: `agents/report-analyst.md` (emit `dashboard.html` when planned),
  `skills/threat-model/SKILL.md` (list the dashboard as an output), `README.md` and
  `docs/diagrams/*.mmd` (document the new artifact).
