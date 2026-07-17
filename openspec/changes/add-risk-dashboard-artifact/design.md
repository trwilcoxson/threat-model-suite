## Context

The pipeline already produces all the facts a risk dashboard needs, distributed across the run
manifests. The visual-engine work established the pattern to follow: an agent authors a structured fact
(`recon.json` + `dataflows[]`) and a deterministic transform (`recon_to_d2.py`) owns 100% of the
presentation. The dashboard is the same shape at report scale — a deterministic transform over the full
manifest set into one self-contained HTML view.

## The determinism boundary

Nothing moves between code and judgment. The **agents** emit every security fact (severity, likelihood,
impact, STRIDE tags, MITRE/CWE ids, kill-chain ordering, coverage states, evidence). The **generator**
only reshapes those emitted facts into charts — it computes no new security assessment. The single
derived value, the headline "risk posture" band, is a pure, documented function of
`findings.summary_counts` (e.g. any CRITICAL ⇒ CRITICAL; ≥5 HIGH ⇒ HIGH RISK), not a judgment. The
grounding eval is reference-free: it checks properties (every shown number equals a recount of the
source; no un-sourced finding id in a structural slot) and never compares against an answer key.

## Decisions

1. **Deterministic generator, agent-agnostic.** `build_dashboard.py` reads the manifests and renders
   the template with no model in the path, so the same run always yields the same HTML (no timestamps,
   no RNG; provenance is read from the manifests' own `generated` field). This keeps the artifact
   reproducible like the offline diagram renders.
2. **Self-contained + offline.** Inline CSS/JS, Unicode/inline-SVG icons, system-font stack, zero
   external requests — verified by a check that asserts no `http(s)://` / `//` resource loads. Matches
   the suite's offline-render discipline.
3. **Templated with empty states.** A fixed section inventory; each section self-renders a graceful
   empty state when its source field is absent. Absent-but-schema-valid fields
   (`controls`/`cvss_vector`/`atlas`/`dataflows`) are permanent slots that degrade, proven by rendering
   from a thinned manifest set.
4. **Embed the run's real diagram; interactive but grounded.** The embedded diagram is the run's own
   rendered structural diagram — the `recon_to_d2.py`/`structural-diagram` SVG of this run's `recon.json`,
   the identical artifact the flow emits elsewhere (same nodes, layout, and dataflow edges) — embedded
   inline, not a bespoke system-map re-layout. Its node ids are the recon element ids (`C1`/`D1`/`E1`/`X1`)
   so they link natively to findings, and its edges are the run's real `recon.dataflows[]`, never edges
   synthesized from finding co-reference. Over it, the linked model (`links` adjacency, `graph` edges,
   `findings_by_id`) is precomputed in the generator from real ids and embedded as JSON, with vanilla-JS
   pan/zoom and a shared-selection cross-filter. No relationship exists that is not in the manifests.

5. **One source of truth, cross-output consistent.** The dashboard is a separate build but not
   independent data: it reads only the run's canonical manifests and embeds the run's real diagram, so
   every number equals what the report shows for the same run. A reference-free cross-output consistency
   check reconciles dashboard-derived values to the manifests — severity counts == `findings.summary_counts`,
   coverage % == `coverage.json`, diagram nodes == recon elements, kill chains == `findings.kill_chains` —
   and asserts the embedded diagram is the run's real structural artifact, the same discipline as the
   existing report↔manifest consistency checks.
6. **Opt-in output.** The dashboard is produced only when listed in the run plan's `outputs`
   (composes with the run-selection capability), so it never forces extra work on a run that did not
   ask for it.

## Risks / trade-offs

- **Offline font substitution.** No web fonts ship, so the dashboard uses a system-font stack
  approximating the demo's typography rather than the exact faces — an intentional, visible trade for
  full offline determinism.
- **Posture band is a derived label.** It is a convenience rollup, not an agent judgment; it is
  documented as a fixed function of `summary_counts` so it can never drift into scripted assessment.
- **New generator surface.** Kept small and pure (manifests → model → template) with a self-check, so
  it cannot regress the existing evals; it runs only when the dashboard output is planned.
