# Tasks

## 1. Additive schema field
- [ ] 1.1 `findings.schema.json`: add optional nullable `atlas` (array, items pattern `^AML\.T\d{4}(\.\d{3})?$`), mirroring `mitre[]`; keep it out of `required`
- [ ] 1.2 Update the schema `description` to note the reference-free grounding rule (ATLAS layer ids ⊆ findings' `atlas[]` ids), matching the existing `mitre[]` note
- [ ] 1.3 `schema_checks.py` / `test_checks.py`: add a case that a finding with `atlas: null` / omitted validates, and a malformed `AML.T99999` fails on shape

## 2. Reference taxonomies (frameworks.md)
- [ ] 2.1 Add a MITRE ATLAS reference table (AI/ML adversarial techniques, `AML.T####` ids) in the ATT&CK/CWE table style, under the existing "AI/ML Security Threats" section
- [ ] 2.2 Add an OWASP-LLM Top-10 table using the verified official `LLM01:2025`–`LLM10:2025` ids and titles
- [ ] 2.3 Add the fixed OWASP-LLM→ATLAS crosswalk table (each LLM0x class → its set of `AML.T####` techniques)
- [ ] 2.4 Extend the "Framework ID Verification" rules to name the ATLAS and OWASP-LLM namespaces and the Phase 6 cross-check

## 3. Artifact rendering (analytical-visuals.md)
- [ ] 3.1 Add a §: "MITRE ATLAS Technique Layer (when `has_ai_ml`)" — Navigator JSON with `domain: "atlas-atlas"`, reusing the ATT&CK-layer emitter/gradient/legend; state the ids-⊆-findings grounding rule
- [ ] 3.2 Add a §: "OWASP-LLM Top-10 Coverage Checklist (when `has_ai_ml`)" — rendered via the STRIDE-matrix table renderer, rows LLM01–LLM10, cells = finding id / `n-a` / `clean`, resolved through the crosswalk; explicitly note "no second diagram"
- [ ] 3.3 Route the Phase 7 producing agent to these two §§ (add to the Phase 7 read list / completeness checklist so `has_ai_ml` targets actually emit them)

## 4. Reference-free checks (eval)
- [ ] 4.1 `diagram_checks.analytical_checks`: add an ATLAS-layer block — gate on `has_ai_ml` OR a declared `atlas[]` id; discriminate on `domain=="atlas-atlas"` + `AML.` prefix; verify `techniqueID` shape, sub-technique parents present, and shown ids ⊆ distinct findings' `atlas[]` ids; skip cleanly when there is no AI surface
- [ ] 4.2 Ensure the new block never runs the ATT&CK `T\d{4}` regex over `AML.T####` ids (keep the two layer detectors separate)
- [ ] 4.3 `checks.py`: add `malformed-atlas` (regex `^AML\.(TA\d{4}|T\d{4}(\.\d{3})?|M\d{4}|CS\d{4})$` over the `atlas[]` field) and `malformed-owasp-llm` (regex `^LLM(0[1-9]|10):2025$` over the OWASP-LLM checklist ids), keyed on the declared framework field, mirroring `malformed-mitre`
- [ ] 4.4 `test_checks.py`: cover an ATLAS layer with an ungrounded technique (defect), a well-formed grounded layer (pass), a non-AI run (block skipped), and both malformed-id cases

## 5. Verify
- [ ] 5.1 `openspec validate add-ai-ml-attack-surface --strict`
- [ ] 5.2 Live: a re-run of an AI/ML target (`has_ai_ml == true`) produces the ATLAS Navigator layer and the OWASP-LLM checklist; the ATLAS-layer check and both malformed-id checks fire on seeded bad inputs
- [ ] 5.3 Live: a re-run of a non-AI target (`has_ai_ml == false`) produces byte-for-byte the same artifacts as before (all new blocks gated off)
