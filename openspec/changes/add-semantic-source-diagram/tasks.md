# Tasks

## 1. Semantic edge model in recon.json
- [x] 1.1 recon.schema.json: add optional `dataflows[]` (`{id, source, destination, type[data|control|build|async|admin], protocol, sensitivity[PUBLIC|INTERNAL|CONFIDENTIAL|RESTRICTED], enc[ENC|PLAIN], label, evidence[]}`)
- [x] 1.2 recon.schema.json: add optional `element.type` (node-type token) and `element.zone` (trust-boundary containment)
- [x] 1.3 Confirm additive/back-compat: all committed manifests still conform (`check_sample_runs` → 32 0)

## 2. Deterministic recon → D2 transform
- [x] 2.1 `scripts/recon_to_d2.py`: elements → typed-icon nodes, trust_boundaries/zones → nested containers, dataflows → typed/annotated/coloured edges
- [x] 2.2 Bind the vendored node-type icons (`references/icons/`) as offline `icon:` paths (output-relative, no remote refs)
- [x] 2.3 Pure/deterministic (sorted iteration; re-render is byte-identical — asserted by a self-check)

## 3. JSON property checks (replace diagram-regex checks)
- [x] 3.1 `dataflow-endpoint-integrity` (consistency): every `source`/`destination` ∈ declared element ids
- [x] 3.2 `recon-node-type-unknown` (advisory): `element.type` ∈ the vocabulary catalog, fuzzy suggestion on a miss
- [x] 3.3 `dataflow-ungrounded` (advisory): edge grounding evidence present
- [x] 3.4 All three inert when `dataflows[]` is absent (back-compat)

## 4. Render proof
- [x] 4.1 Augment a copy of the flagship recon with `dataflows[]` + types + zones (committed flagship untouched)
- [x] 4.2 Render offline via `d2 --layout elk` + `rsvg-convert` → `poc/05-recon-to-d2.{d2,svg,png}` (typed icons, nested boundaries, full annotated edge set)
- [x] 4.3 Writeup `SEMANTIC-SOURCE-SPIKE.md` with the rendered comparison + regex→JSON replacement table + verdict

## 5. Self-checks
- [x] 5.1 dataflow endpoint integrity (dangling flagged / valid passes)
- [x] 5.2 node-type membership (bad token flagged w/ suggestion / valid+alias passes)
- [x] 5.3 back-compat inertness (no dataflows → checks inert)
- [x] 5.4 transform smoke test (emitted D2 parses under `d2`; icons bind + embed offline)

## 6. Adoption (follow-up, not this change)
- [ ] 6.1 Offer recon→D2 as a first-class Phase 2 authoring path in SKILL.md (documented as an option here; make it the default only after a live-run pilot)
- [ ] 6.2 Pilot: author one target's structural diagram from recon→D2 end-to-end in a live run and confirm quality vs hand-authored
- [ ] 6.3 If the pilot holds, promote the JSON checks to the primary structural-diagram verification and derive the rendered diagram from `recon.json`
