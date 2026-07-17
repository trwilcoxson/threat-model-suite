# Tasks

## 1. Generator
- [ ] 1.1 Add `skills/threat-model/scripts/build_dashboard.py` — read `recon.json`/`findings.json`/`coverage.json` (+ navigator layer if present) into a derived analytics model
- [ ] 1.2 Add the HTML template module/reference (`references/dashboard-template.*`) — inline CSS/JS, fixed section inventory, empty states, CVD-safe severity palette, motion with `prefers-reduced-motion` guard
- [ ] 1.3 Embed the run's real structural diagram (the `recon_to_d2.py`/`structural-diagram` SVG of this run's `recon.json` — same nodes/layout/dataflow edges as the flow's other diagram output, node ids = recon element ids `C1`/`D1`/`E1`/`X1`); emit the linked model (`links` adjacency + `graph` edges from `recon.dataflows[]` + `findings_by_id`) from real ids only; layer pan/zoom + cross-filter/tooltip/drawer interaction JS over it
- [ ] 1.4 Ensure the generator emits byte-stable HTML (no timestamps/RNG; provenance from manifests) and loads no external resource

## 2. Pipeline wiring
- [ ] 2.1 Update `agents/report-analyst.md` to emit `dashboard.html` when `"dashboard" ∈ run-plan outputs`
- [ ] 2.2 Update `skills/threat-model/SKILL.md` Phase-8 output list to include the dashboard

## 3. Reference-free eval
- [ ] 3.1 Add `skills/threat-model/evals/reliability/dashboard_checks.py` — grounding (headline numbers equal a recount of the manifests), non-fabrication (no un-sourced finding id in a structural slot), **cross-output consistency (dashboard severity counts == `findings.summary_counts`, coverage % == `coverage.json`, diagram nodes == recon elements, kill chains == `findings.kill_chains`; edges are the run's real `recon.dataflows[]`, not finding co-reference; embedded diagram is the run's real structural artifact)**, offline (no external resource load), templated-blanks (absent fields render empty states)
- [ ] 3.2 Add self-check cases to `test_checks.py` covering the flagship run and a thinned/empty run
- [ ] 3.3 Wire the dashboard checks into `run.py check`/`validate` (only when `dashboard.html` is planned/present)

## 4. Verify
- [ ] 4.1 `openspec validate add-risk-dashboard-artifact --strict`
- [ ] 4.2 `cd skills/threat-model/evals/reliability && python3 test_checks.py` (all pass)
- [ ] 4.3 `python3 schema_checks.py` (all conform) and `python3 run.py validate` on the flagship example (PASS)
- [ ] 4.4 Render `dashboard.html` for the flagship example and from a thinned manifest set; confirm layout holds with blanks
