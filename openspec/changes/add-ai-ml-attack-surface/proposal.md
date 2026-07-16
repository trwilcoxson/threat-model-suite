## Why

The suite already emits a MITRE ATT&CK **enterprise** Navigator layer (the shipped
`ecs-fullstack-attack-navigator-layer.json`, `domain: "enterprise-attack"`, technique ids `T####`),
but enterprise ATT&CK **cannot express the adversarial-ML attack surface** — data/RAG poisoning,
evasion, model extraction/inversion, prompt injection, tool-call injection, agent hijack. For an AI/ML
target the suite therefore has no artifact for the exact techniques that matter most. Concretely:

- **`coverage.context.has_ai_ml` already exists** as a declared applicability flag (coverage.schema.json),
  and `frameworks.md` already carries an "AI/ML Security Threats (Supplementary)" section (LLM / Agentic /
  RAG / Multi-Modal). But nothing **consumes** `has_ai_ml` to produce an AI-specific artifact, and that
  supplementary section carries **no verifiable framework-id namespace** — no MITRE ATLAS ids, no
  OWASP-LLM Top-10 ids, and no entry in the Framework ID Verification rules. So an AI finding either omits
  a framework id or **fabricates** one, with no deterministic guardrail to catch it.
- **`findings.schema.json` has `mitre[]` (ATT&CK) but no ATLAS field.** An AI finding cannot record the
  adversarial-ML technique it maps to, so no ATLAS layer can be grounded to the model's own findings.
- **The eval has a `no-attack-layer` check for ATT&CK** (`diagram_checks.analytical_checks`) and
  `malformed-mitre` / `malformed-cwe` regex checks (`checks.py`), but **nothing for the ATLAS namespace**.
  The ATT&CK `T\d{4}` regex must not be run over `AML.T####` ids — an ATLAS layer is told apart from an
  ATT&CK layer only by `domain=="atlas-atlas"` and the `AML.` prefix.

Net: the enterprise ATT&CK layer, the STRIDE-matrix renderer, the Navigator JSON emitter, and the
`has_ai_ml` gate all already exist. The AI/ML attack surface is a **wiring + taxonomy gap**, not new
machinery — reuse the emitter with an ATLAS domain, add one additive finding field, and extend the
reference-free checks to the ATLAS/OWASP-LLM vocabularies.

## What Changes

- **Emit a MITRE ATLAS Navigator layer** by **reusing the existing ATT&CK-Navigator JSON emitter** with
  `domain: "atlas-atlas"`, gated on the **existing** `coverage.context.has_ai_ml` flag. When `has_ai_ml`
  is false the ATLAS layer is not produced and every other artifact (including the ATT&CK-enterprise
  layer) is unchanged — non-AI targets are wholly unaffected.
- **Add one additive finding field `atlas[]`** to `findings.schema.json` (optional, nullable, pattern
  `^AML\.T\d{4}(\.\d{3})?$`), mirroring the existing nullable `mitre[]` field. Absence is an honest gap,
  never a validation failure.
- **Render an OWASP-LLM Top-10 coverage checklist** (LLM01–LLM10) using the **existing STRIDE-matrix
  table renderer** — a checklist, **not** a second diagram. Each row resolves over the model's own
  `atlas[]` ids through a fixed OWASP-LLM→ATLAS crosswalk (a grouping, not an answer key) to a finding id
  / `n-a` / `clean`, projecting the OWASP-LLM view **onto the ATLAS layer** rather than duplicating it.
- **Add MITRE ATLAS and the OWASP-LLM Top-10 to `frameworks.md` as reference taxonomies** — prompt
  guidance in the same style as the existing ATT&CK/CWE tables, with the OWASP-LLM→ATLAS crosswalk — and
  **extend the Framework ID Verification rules** to the ATLAS and OWASP-LLM namespaces. Guidance the agent
  reasons with, never an answer key.
- **Extend the reference-free eval** with two checks, both gated on `has_ai_ml` / a declared ATLAS id:
  - *ATLAS-layer grounding + well-formedness* (T4-03): `domain=="atlas-atlas"`, every `techniqueID`
    matches `^AML\.T\d{4}(\.\d{3})?$`, sub-technique parents present, and the technique ids shown are a
    **subset of the distinct `atlas[]` ids across findings** — the same grounding rule as today's ATT&CK
    layer, never "technique X must be present".
  - *Controlled-vocabulary id guardrail* (T4-07): every AI/ML framework id is validated against the fixed
    regex for its **declared framework field** (ATLAS `^AML\.(TA\d{4}|T\d{4}(\.\d{3})?|M\d{4}|CS\d{4})$`,
    OWASP-LLM `^LLM(0[1-9]|10):2025$`), mirroring `malformed-mitre` / `malformed-cwe`. Keyed on the
    declared framework, never guessed from the bare token (so `AML.T####` is never run through the ATT&CK
    `T\d{4}` regex, and an OWASP-LLM `LLM0x` is never confused with an ATT&CK id).

## Capabilities

### New Capabilities
<!-- No new capability dir: every surface here extends an existing one. -->

### Modified Capabilities
- `threat-model-visuals`: adds the ATLAS Navigator layer artifact and the OWASP-LLM Top-10 coverage
  checklist (projected onto the ATLAS layer / STRIDE-matrix renderer), both gated on `has_ai_ml`.
- `eval-determinism`: adds the additive `atlas[]` findings field and the two reference-free checks
  (ATLAS-layer grounding, controlled-vocabulary id guardrail) that preserve the determinism boundary.
- `reference-fidelity`: adds the MITRE ATLAS and OWASP-LLM Top-10 reference taxonomies + crosswalk to
  `frameworks.md` and extends the Framework ID Verification rules to those namespaces.

<!-- Composes with add-product-grade-diagrams (reuses its Navigator JSON emitter + STRIDE-matrix renderer,
     no change to their existing requirements), add-coverage-ledger (reuses the has_ai_ml context flag),
     and harden-eval-determinism-boundary (extends the gate-on-declared-facts invariant to ATLAS). -->

## Impact

- Modified: `skills/threat-model/references/analytical-visuals.md` (new §: ATLAS Navigator layer with
  `domain: "atlas-atlas"`, gated on `has_ai_ml`; OWASP-LLM Top-10 checklist via the STRIDE-matrix
  renderer), `skills/threat-model/references/frameworks.md` (ATLAS + OWASP-LLM taxonomy tables, the
  OWASP-LLM→ATLAS crosswalk, Framework ID Verification extended to the AI namespaces),
  `skills/threat-model/evals/reliability/schema/findings.schema.json` (additive nullable `atlas[]`),
  `skills/threat-model/evals/reliability/diagram_checks.py` (ATLAS-layer block in `analytical_checks`),
  `skills/threat-model/evals/reliability/checks.py` (`malformed-atlas` / `malformed-owasp-llm`
  controlled-vocab checks keyed on the declared framework field).
- Unaffected by design: any target with `has_ai_ml == false` — every new artifact and check is gated, so
  the existing pipeline output for non-AI systems is byte-for-byte unchanged.
