# OTM (Open Threat Model) — evaluated as the canonical as-code source

**Question (owner):** could OTM be the standardized "as-code" source of truth, so agents author a portable
standard and a deterministic renderer produces the beautiful visual from it? Researched across the OTM
standard, the as-code-TM rendering landscape (threagile / pytm / Threat Dragon / threatspec), and the
architecture fit, with an adversarial verifier.

**Verdict: do NOT adopt OTM. The *idea* is right; OTM is the wrong vehicle.**

## What OTM is
IriusRisk's CC-licensed YAML/JSON **semantic** model (project / components / dataflows / trustZones /
assets / threats / mitigations / representations). A **data-interchange format, not a rendering spec** — it
ships no renderer (the whole OTM/StartLeft ecosystem flows sources *into* OTM; OTM renders only inside
IriusRisk's proprietary canvas). Still **v0.2.0**, pre-1.0 after ~4 years, single-vendor governance
(iriusrisk/OpenThreatModel, not OWASP), ~40 commits, effectively static.

## Why not canonical
It natively lacks almost everything the suite's contract enforces — no STRIDE-LM enum (`categories[]` is a
free string), no CVSS vector, no ATT&CK/ATLAS ids, no attack trees, no kill chains, no coverage ledger, no
severity band. Its **required** fields actively fight us: `threat.risk` is 0–100 with **no band** (destroys
the `severity == band(L×I)` invariant), `trustRating` 0–100 is required per zone (a fabricated unchecked
number), `component.type` is free-form (any *imported* OTM fails our vocab check), and diagram
representations **require** x/y coordinates (so "layout-free OTM" means not using OTM's model↔picture
feature at all). Cramming our validated fields into OTM's free-form `attributes[]` moves them *out* of
schema enforcement — the opposite of the point.

## The dominant alternative (what to build instead)
The boundary-strengthening the owner is after — *agent emits pure meaning, deterministic layer owns 100% of
layout & aesthetics* — comes from a **structured semantic source**, not from OTM specifically. `recon.json`
is **already** that structured, hard-gate-validated JSON; it lacks exactly one thing: a **`dataflows[]` /
typed-edges array** (edges live only in the diagram today). Add `dataflows[]` + a real node-**type enum**
to `recon.json` and a deterministic **`recon → D2`** render, and you get 100% of the benefit —
edge-endpoint integrity, node-type vocabulary compliance, and grounding all become **JSON reference /
membership checks inside the existing blocking gate** (cleaner and harder to fool than regex over diagram
text) — with the STRIDE-LM / CVSS / severity-band enums intact, **no second schema, no OTM→D2 transform, no
dormant single-vendor dependency**. Analytical matrices, attack trees, kill chains, and auth sequences have
no OTM form and stay Mermaid-authored either way — OTM narrows the as-code surface, it doesn't unify it.

## Decisions (2026-07-15)
- **`modernize-visual-engine` (#5) and `add-offline-render-pipeline` (#6) were never blocked by this** — the
  render engine (D2) and the authoring format are orthogonal. Both proceed with D2 as designed.
- **Semantic-source (`recon.json` + `dataflows[]` → deterministic `recon→D2`) is a queued time-boxed
  spike**, behind #5's per-engine extractor seam, before committing it as a small new openspec change —
  prove render quality ≥ hand-authored D2 and that the JSON checks are strictly simpler, then commit it.
- **OTM export: skipped (YAGNI).** A one-way `recon+findings → OTM v0.2.0` projection is cheap and
  contract-safe, but the consumer base is effectively IriusRisk customers; revisit only if a real consumer
  appears.
