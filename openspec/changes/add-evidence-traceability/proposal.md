## Why

Today a finding only references recon components — `asset_refs`/`surface_refs` point at recon element
ids, and it is the recon `evidence[]` that carries source pointers. There is **no direct,
problem-specific evidence on the finding itself**: clicking a finding in the dashboard (or reading it in
the report) shows the claim and the components it touches, but no proof of *that* problem — no cited code
snippet, document quotation, or diagram element that evidences the flaw.

- **Evidence is indirect.** A finding inherits recon's evidence transitively via the components it names,
  so the reader cannot see what specifically substantiates the finding without re-deriving it by hand.
- **No enforced per-finding grounding.** Nothing requires each finding to carry a resolvable, extractable
  reference to what proves it, and nothing embeds that proof in the self-contained outputs.

## What Changes

- **New: evidence is first-class on every finding.** Each finding in `findings.schema.json` gains an
  OPTIONAL additive `evidence[]` array. Each item carries a `ref` (a findable reference — repo-relative
  path, `path:line`, `path:line-range`, glob, doc locator, or a recon/diagram node id `C1`/`D1`/`E1`/`X1`/`TB1`)
  precise enough to resolve in the target source and extract an excerpt; optional `kind`
  (`code`|`config`|`doc`|`diagram`); optional `quote` (the agent's verbatim snippet); and an honest
  abstention pair `no_direct_evidence` (bool) + `justification` (required when abstaining). The build
  generators add `excerpt` at build time. The field is additive/nullable: committed manifests without
  `evidence` still conform to the schema (back-compat).
- **Flow enforcement, each time.** Every agent (security-architect + privacy/grc/code-review specialists)
  MUST attach resolvable evidence to EVERY finding. A reference-free run-gate check (extending the
  existing grounding check) verifies every finding has ≥1 evidence reference that RESOLVES in the real
  source and is extractable; explicit `no_direct_evidence` + `justification` is the only allowed
  abstention. The determinism boundary holds: the check asserts resolvability, never dictates content.
  The presence/resolvability requirement lives in the run-gate + eval, NOT in the schema, so committed
  evidence-less manifests still validate.
- **Outputs derive, embed, and validate the excerpt.** The dashboard AND report generators resolve each
  finding's evidence `ref` at BUILD time, extract the excerpt (cited line-range / doc quote / diagram
  element), and EMBED it self-contained. The dashboard finding drawer shows the evidence snippet
  (monospaced, syntax-lit for code), the findable reference (`file:line`), and a jump to the related
  diagram node. A reference-free validator per output asserts evidence is present, resolvable, that the
  embedded excerpt matches the cited source (no fabricated excerpt), and cross-output consistency; the
  honest no-evidence state is shown, never a fabricated snippet.
- **Linked into the dashboard data model, both directions.** finding ⇄ evidence-excerpt ⇄ source-location
  ⇄ diagram-node is wired into the dashboard's linked data model, so pivoting to a finding surfaces its
  evidence and pivoting from a diagram node surfaces the findings and their evidence.

## Capabilities

### New Capabilities
- `evidence-traceability`: first-class, resolvable, per-finding evidence; the flow enforcement that
  requires it each time with honest abstention and schema back-compat; and the build-time
  derive/embed/validate of the excerpt at every output, wired into the dashboard's linked model.

### Modified Capabilities
<!-- composes with risk-dashboard (adds the evidence snippet to the finding drawer + linked model),
report generation (embeds the per-finding excerpt), the grounding eval (requires + extracts per-finding
evidence), and the findings schema (additive `evidence[]`) — no requirement changes to those. -->

## Impact

- Schema: `skills/threat-model/evals/reliability/schema/findings.schema.json` (additive `evidence[]`).
- Flow enforcement: `skills/threat-model/evals/reliability/checks.py` (per-finding evidence
  presence/resolvability/extractability), `skills/threat-model/evals/reliability/test_checks.py`
  (self-checks); the agent prompts (`agents/security-architect.md`, `agents/privacy-agent.md`,
  `agents/grc-agent.md`, `agents/code-review-agent.md`) — attach evidence to every finding.
- Outputs: `skills/threat-model/scripts/build_dashboard.py` and
  `skills/threat-model/references/dashboard_template.py` (resolve → extract → embed the excerpt; drawer +
  jump-to-node; linked model both directions), the report template
  (`skills/threat-model/references/report-template.md`) — embed the per-finding excerpt,
  `skills/threat-model/evals/reliability/dashboard_checks.py` (per-output reference-free evidence
  validator: present, resolvable, excerpt matches source, cross-output consistent, honest no-evidence).
- Docs: `README.md`.
