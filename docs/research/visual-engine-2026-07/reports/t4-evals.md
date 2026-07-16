# T4 — Evals for richer visuals (reference-free consistency WITHOUT constraining the model)

**Track:** t4-evals · **Question:** as T1 (engine) and T2/T3 (new artifacts) land, how do we guarantee
consistency and quality **reference-free** — property / grounding / coverage checks that hold for *any*
good threat model, with no answer key and no constraint on the model's freedom to choose and reason?

**Answer in one line:** extend the *exact* pattern already in `diagram_checks.analytical_checks` —
**gate each new artifact on a skill-declared fact, then check only presence + shape + grounding +
cross-artifact consistency, with an abstention hatch on every check.** Nothing below compares to a
golden artifact; every denominator is the model's own recon/findings.

---

## 1. What the existing eval already does (the pattern I am extending)

I read `checks.py`, `coverage_checks.py`, `schema_checks.py`, `diagram_checks.py`, the schemas, and the
harness README. The five-layer model (structure → consistency → grounding → coverage → diagram) already
contains a working template for "richer-visual" checks: `diagram_checks.analytical_checks()` verifies the
STRIDE matrix, risk heat map, ATT&CK layer, RBAC matrix, attack tree, attack-flow, auth sequence and SBOM
**today** — and it does so with seven design invariants I treat as hard constraints for every new check:

| # | Invariant (from the code) | Where it lives today |
|---|---|---|
| 1 | **Gate on a skill-DECLARED fact, never inferred content.** Attack tree gated on `≥3 kill_chains`; auth-seq on an S/E finding *or* `roles[]` — explicitly *not* on name-sniffing an entity string (see the `# determinism boundary` comment at `diagram_checks.py:153`). | `analytical_checks` gates |
| 2 | **Structure-only.** A present + internally-consistent visual passes even if the analysis is wrong; correctness is the judge's job (`prompts/diagram-judge.md`). | whole module |
| 3 | **Grounding = trace to a real id.** Refs must resolve to recon ids / finding ids / the repo; `dangling-ref`, `ungrounded-element` are the defects. | `checks.py:195`, `_resolves_in_repo` |
| 4 | **Consistency = recompute, don't trust.** `band(L×I)` recomputed; every HIGH+ finding must appear in the L4 overlay; matrix must be a projection of findings. | `checks.py:189`, `diagram_checks.py:307` |
| 5 | **Defect vs warning.** Hard failures are defects; soft "wants more" are warnings; ratio thresholds decide which (`>10%` untyped edges → defect, else warn). | throughout |
| 6 | **Abstention is first-class.** `no_issue_surface[]`, coverage `unknown`/`absent`+note, matrix cells accept `n/a`/`clean`, `kind: unknown\|null` accepted. An honest "examined, nothing here" never fails. | `checks.py:224`, `coverage_checks.py:86` |
| 7 | **Coverage denominator = the model's own recon**, never a golden list. | `checks.py:225`, `coverage_checks.py:65` |

Every T4 recommendation below is a straight extension of `analytical_checks` obeying all seven. New
artifacts are new gated blocks in the same file; new manifest fields are additive and nullable.

---

## 2. The one meta-insight that governs the whole track

**Reference-free coverage measures self-consistency, not accuracy — so a coverage ratio must never be a
hard pass/fail gate, and must stay paired with the recon-completeness layer.**

The strongest external finding (verified across ACSE-Eval, ThreatModeling-LLM, and the taxonomy-coverage
audit literature): *every published, named threat-modeling benchmark measures coverage against a golden
key.* The only ratios that survive reference-free are those whose **denominator is either (a) a fixed
taxonomy** (e.g. the 7 STRIDE-LM categories — denominator is a constant, so it is reference-free *by
construction*) **or (b) the model's own recon** (ACSE-Eval's AWS-Service-Coverage is the one published
metric of this shape). The failure mode is **denominator gaming**: a model that under-discovers in
`recon.json` shrinks its own denominator and scores 100% coverage while missing real threats. The harness
already defends this exact hole with the *agent-judged* layer — `recon-auditor` (recon vs real repo) and
`red-team → gap-validator` (independent HIGH+ gaps). So the rule for T4:

> **Report coverage ratios as metrics; never gate on them; always keep them beside an absolute count and
> the recon-auditor.** A high ratio over a thin recon is caught by recon-auditor, not by inflating the
> ratio into a threshold (which would push the model to pad findings — a determinism-boundary violation).

Sources: ACSE-Eval arXiv:2505.11565; ThreatModeling-LLM arXiv:2411.17058; ThreatCompute/TTC (CCSW'25,
mlsec.org/docs/2025-ccsw.pdf); STRIDE-network case study arXiv:2505.04101.

---

## 3. Per-artifact check catalogue

Each block: **gate** (declared fact) · **well-formedness** · **grounding** · **consistency** ·
**abstention** · **reference-free because…**. All are new blocks in `diagram_checks.py` /
a sibling `visual_checks.py`, layer `"diagram"` unless noted.

### A. Typed-icon / node-type vocabulary  *(validates T1 engine)*

The T1 engine introduces a controlled node-type→icon/shape/`classDef` vocabulary (the "muddy diagram"
fix). Checks that every node is *typed from a controlled set* — the structural precondition that makes an
icon engine legible — without dictating which type any node is.

| Check | Layer | Property enforced | Reference-free because | Abstention |
|---|---|---|---|---|
| `node-type-present` | diagram | every drawn node carries a type token (`classDef`/shape/`%%type:` per T1 spec) | counts *typed vs untyped*, never *which type* | a node may be typed `unknown`/`other` and pass |
| `node-type-in-vocab` | diagram | every type token ∈ the T1 controlled vocabulary | compares to a fixed *vocabulary*, not a per-node answer | `other`+detail is a valid vocab member (mirrors `detected_pattern:"other"`) |
| `icon-consistency` | consistency | same type token → same icon/`classDef` across all diagrams in the report | intra-document consistency, no external ref | n/a — a pure well-formedness rule |
| `legend-covers-types` | diagram | every type token used appears in the legend subgraph | projection of the doc onto itself | unused vocab members need not be in the legend |

Threshold: `>10%` untyped nodes → defect (mirrors `untyped-edges`), else warning. **Escape hatch that
prevents "type everything or fail":** an explicit `unknown`/`other` type is a first-class, passing value —
so the model is never forced to invent a type it can't justify (invariant 6).

### B. Attack-Defense Trees (ADT)  *(validates T2)*

Extends the existing `no-attack-tree` check (which today only looks for AND/OR gates) to the Kordy–Mauw
**attack-defense** formalism, where defense/countermeasure nodes appear. Well-formedness rules are taken
verbatim from *Foundations of Attack–Defense Trees* (FAST 2010) and the ADTool XSD.

| Check | Layer | Property enforced | Reference-free because | Abstention |
|---|---|---|---|---|
| `adt-present` | diagram | gate `≥3 kill_chains` (reuse existing gate) → an ADT (or plain attack tree) exists | presence, gated on declared fact | if the model declares no defenses, a plain attack tree still passes — defenses are not *forced* |
| `adt-node-types` | diagram | every node ∈ {attack, defense}; every refinement ∈ {OR, AND} (no other gate type) | fixed grammar, not content | — |
| `adt-one-countermeasure` | consistency | **≤1 opposite-type (`switchRole="yes"`) child per node** (the canonical ADT restriction) | structural invariant of the formalism | — |
| `adt-role-alternation` | consistency | same-type refinement children match the node's own type; crossing a counter edge flips role | typing rule, not answer | — |
| `adt-nonleaf-has-children` | diagram | every refinement node has ≥1 same-type child; tree is acyclic (rooted DAG) | graph well-formedness | a bare basic-action leaf is valid |
| `adt-attack-leaf-grounded` | grounding | each attack leaf traces to a finding id / recon id | grounding to declared ids | leaf may map to a kill-chain step id instead |
| `adt-defense-grounded` | grounding | each defense node references a finding's `remediation`/a declared mitigation id | grounding, **not** "produce mitigation X" | a defense with no finding link → **warning**, never defect (see §5); a node may declare `mitigation: none\|accepted-risk` to say "chose not to mitigate" without being flagged |

**Serialization note:** if T2 emits ADTs as ADTool XML rather than Mermaid, validate against `adtree.xsd`
*then* add rules `adt-one-countermeasure` / `adt-role-alternation` (the XSD alone does **not** enforce
them — it allows unbounded `switchRole="yes"` children). SAND/sequential-AND gates are **not** part of the
ADT formalism; if T2 wants temporal ordering, that is a separate SAND artifact (see G / rec T4-10).

### C. MITRE ATLAS technique layer  *(validates T3, AI systems)*

The existing `no-attack-layer` check handles ATT&CK enterprise. ATLAS is the AI-system analogue and needs
its own regex + domain discriminator — the two share the Navigator JSON schema (ATLAS Navigator is a fork).

| Check | Layer | Property enforced | Reference-free because | Abstention |
|---|---|---|---|---|
| `atlas-gate` | diagram | gate: `≥1` finding carries an `atlas` id (new field) OR recon is agentic/LLM | declared fact | non-AI system → block skipped entirely |
| `atlas-layer-wellformed` | diagram | `domain == "atlas-atlas"`; every `techniqueID` matches `^AML\.T\d{4}(\.\d{3})?$`; `versions.layer` present | fixed MITRE schema | — |
| `atlas-ids-subset` | consistency | technique ids shown ⊆ distinct `atlas` ids across findings (no invented technique) | subset of the model's own ids | extra findings-side ids not yet on the layer → warning |
| `atlas-subtech-parent` | consistency | every `AML.T####.###` has parent `AML.T####` present | structural | — |

Discriminator is load-bearing: an ATLAS layer is told apart from an ATT&CK layer **only** by
`domain=="atlas-atlas"` + the `AML.` prefix. Do **not** run the `T\d{4}` ATT&CK regex over ATLAS ids.
Source: mitre-atlas/atlas-data, atlas-navigator-data (live-verified this session).

### D. LINDDUN privacy matrix  *(validates T3)*

A privacy analogue of the STRIDE-per-element matrix. Structure mirrors `no-stride-matrix` exactly.

| Check | Layer | Property enforced | Reference-free because | Abstention |
|---|---|---|---|---|
| `linddun-gate` | diagram | gate: recon has a data_store/flow handling personal data **as declared** (new `handles_pii` flag) or a privacy finding exists | declared fact, not PII-sniffing | no declared PII surface → skipped |
| `linddun-matrix-present` | diagram | table with the 7 category columns keyed `L,I,Nr,D,Dd,U,Nc` | fixed taxonomy | — |
| `linddun-vocab` | consistency | category labels ∈ accepted alias set; **reject "Information disclosure"** (STRIDE's, not LINDDUN's `Dd`=Data Disclosure); don't mix gerund+noun vocab | fixed vocabulary | a version flag (`gerund`/`noun`) selects the alias set |
| `linddun-no-blank-cells` | diagram | every cell = finding id / `n/a` / `clean` (same rule as STRIDE matrix) | projection of findings | `n/a` + `clean` are the abstention values |
| `linddun-flow-has-process` | consistency | (PRO form) every analyzed interaction has ≥1 Process endpoint | LINDDUN PRO structural rule | classic element-form skips this |

**Boundary note:** LINDDUN-GenAI keeps the **same 7 categories** (no new letters) — arXiv:2603.06051 adds
examples, not taxonomy. So the checker never needs an AI-specific privacy vocabulary; the 7-category check
is stable. (There is no official "LINDDUN-GenAI" release — flag if T3 cites one as canonical.)
Sources: linddun.org/threat-types, /instructions-for-pro, PRO mapping table PDF.

### E. DFD-STRIDE / STRIDE-per-interaction + applicability  *(validates T3 — see §5, RISKY)*

Two sub-parts. The *per-interaction structure* check is boundary-safe; the *applicability* check is the
one that risks constraining reasoning and is deliberately **warning-only** (§5).

| Check | Layer | Property enforced | Reference-free because | Abstention |
|---|---|---|---|---|
| `stride-interaction-shape` | diagram | (if T3 emits per-interaction) every row names source + destination + flow; interaction crosses a trust boundary | structural, gated on declared edges | intra-zone interaction → warning |
| `stride-applicability` **(warning)** | consistency | a finding whose *only* ref is a `data_store` should not be `S`/`E`-tagged; `data_flow` not `S/R/E`; `external_entity` only `S/R` (classic Microsoft chart, element-type = declared `dfd_type`) | element type is a *declared fact*; chart is a fixed rule | **warning only**; `dfd_type:unknown`, a multi-type ref, **or a declared `cross_applicable:true`/`stride_rationale`** on the finding suppresses it — the model can keep an intentional S-on-store and say why |

### F. Risk heat-map / matrix enrichment  *(validates T2)*

The `no-risk-heatmap` check exists; enrich it with the cell-position consistency the analytical-visuals
spec already demands.

| Check | Layer | Property enforced | Reference-free because | Abstention |
|---|---|---|---|---|
| `heatmap-cell-band` | consistency | each finding is plotted at the cell `(likelihood, impact)` matching its own scores, and the cell's band == `band(L×I)` | recomputed from the finding's own numbers | unscored finding not required on grid |
| `heatmap-complete` | consistency | every scored finding appears exactly once | projection of findings | — |

### G. LASM layered / temporal grid  *(validates T3 — see §5 + §6, RISKY)*

LASM (arXiv:2604.23338) is a **grid**: each AI threat is a cell at (layer L1–L7, temporality T1–T4). It is
NOT a DAG — temporality is an ordinal label, not edges. It is a **young single-paper taxonomy**, so it is
opt-in and warning-heavy.

| Check | Layer | Property enforced | Reference-free because | Abstention |
|---|---|---|---|---|
| `lasm-gate` | diagram | gate: recon declared agentic/LLM **and** the run opts into LASM | declared fact + opt-in | non-agentic or opted-out → skipped |
| `lasm-vocab` | consistency | layer tag ∈ {L1..L7}, temporality ∈ {T1..T4} from the fixed LASM sets | fixed vocabulary | a threat may be tagged one axis + `unknown` on the other |
| `lasm-cell-single` | consistency | each tagged threat has exactly one (layer, temporality) pair | structural | `unknown` allowed per axis |

**Do not require LASM tags on every finding** — requiring a young taxonomy the model didn't choose is a
boundary violation. LASM is a *reported enrichment*, gated on opt-in, warning-level. See §6 for the layer
namespace collision this creates.

### H. Controlled-vocabulary label check (cross-cutting, layer `consistency`)

A single reusable check: any framework id a finding/visual emits must match the **fixed regex** for its
declared framework — catches typos/fabrication, never demands a specific id. New optional finding fields
`atlas[]`, `owasp_llm[]`, `owasp_agentic[]`, `maestro_layer`:

| Vocabulary | Regex | Source (verified) |
|---|---|---|
| MITRE ATLAS | `^AML\.(TA\d{4}\|T\d{4}(\.\d{3})?\|M\d{4}\|CS\d{4})$` | mitre-atlas/atlas-data schemas |
| OWASP LLM Top-10 2025 | `^LLM(0[1-9]\|10):2025$` | genai.owasp.org/llm-top-10 |
| OWASP Agentic (T1–T15) | `^T([1-9]\|1[0-5])$` | genai.owasp.org Agentic Threats & Mitigations v1.0 |
| MAESTRO layer | `^L[1-7]$` or `Layer [1-7]` | CSA MAESTRO blog 2025-02-06 |

Mirrors the existing `malformed-cwe`/`malformed-mitre` regex checks. **Collision warning:** OWASP-Agentic
`T1`..`T15` overlaps lexically with ATT&CK `T####` truncated — key the regex on the finding's *declared
framework field*, never guess from the bare string.

### I. Reference-free coverage-ratio panel (layer `coverage`, REPORTED not gated)

Per §2 — metrics beside the existing `coverage`/`grounding` scores, never thresholds.

| Ratio | Numerator / Denominator | Reference-free because | Ceiling to log |
|---|---|---|---|
| STRIDE-LM category coverage | distinct STRIDE-LM cats in findings / **7** | denominator is a fixed taxonomy | breadth ≠ validity; 7/7 gameable |
| Trust-boundary coverage | boundaries with ≥1 finding / `len(recon.trust_boundaries)` | denominator = own recon | "addressed" by an irrelevant finding |
| Service/tech coverage | components+entry_points touched by ≥1 finding / total in recon | own recon (= ACSE-Eval ASC with swapped denom) | touched ≠ analyzed |
| Actor coverage | `roles[]` referenced by ≥1 finding / `len(roles)` | own recon | — |

Each emitted with its absolute numerator so a thin denominator is visible; recon-auditor remains the
backstop against denominator gaming.

---

## 4. New schema fields these imply (all additive, nullable, declared-fact)

- **recon.element**: `dfd_type` enum `{external_entity, process, data_store, data_flow, unknown}` (lets
  §E applicability + §D LINDDUN gate on a *declared* element type instead of inferring from the bucket);
  `handles_pii: bool|null` on data_stores/flows (gates LINDDUN, §D).
- **recon**: `ai_system: bool|null` / reuse `detected_pattern` to add `agentic-ai`, `llm-app` archetypes
  (gates ATLAS §C, LASM §G — a declared fact, not sniffed).
- **findings.finding**: `atlas: [str]|null` (regex `AML.…`), `owasp_llm: [str]|null`,
  `owasp_agentic: [str]|null`, `linddun: [enum L,I,Nr,D,Dd,U,Nc]|null`, `mitigation_id: str|null`
  (lets ADT defense nodes ground, §B), `lasm: {layer, temporality}|null` (§G),
  `cross_applicable: bool|null` + `stride_rationale: str|null` (suppresses the §E applicability warning
  when the model *intends* an off-chart STRIDE tag and says why — the honest-deviation hatch).
- **findings**: `defenses: [{id, mitigation_id\|"none"\|"accepted-risk", counters: [finding_id]}]|null` —
  declared defense catalogue so ADT defense nodes ground to ids the model chose (§B), with `none`/
  `accepted-risk` as expressible "chose not to mitigate" values, never to an eval-supplied list.
- **diagram stamp**: a distinct `Family:` token for enriched artifacts (`Family: ADT|ATLAS|LINDDUN|LASM`)
  so the parser routes blocks without keyword-sniffing — extends the existing `Type:` stamp convention.

All follow the existing nullable/`unknown` idiom: absence is an honest gap, never a failure.

---

## 5. Checks that risk constraining reasoning — and how I kept them property-based

The brief demands these be flagged. Three proposed checks came closest to the boundary; here is the
redesign that keeps each a *property*:

1. **STRIDE-per-element applicability (§E).** *Risk:* the classic Microsoft chart says a data store can't
   be Spoofed — but a "data store" that is really a cache/service *can* be, and impersonation of a store is
   arguable. Hard-failing an `S`-on-data_store finding would **overrule the model's own reasoning** = a
   violation. *Kept property-based by:* (a) **warning-level only**, never a defect; (b) gating on the
   *declared* `dfd_type`, with `unknown`, any multi-type ref, **and a declared `cross_applicable:true` /
   `stride_rationale`** all suppressing it — so the model can keep an intentional "Spoofing on a cache
   data-store" finding and *say why* rather than be overruled; (c) framing it as "did the model's STRIDE
   tag and its declared element type disagree?" — a *consistency* signal for the judge, not a verdict. It
   flags a *possible* mislabel, never forces a category.

2. **LASM layer requirement (§G).** *Risk:* requiring every AI finding to carry an L1–L7/T1–T4 tag forces
   a 2026 single-paper taxonomy the model may not have chosen — a content mandate. *Kept property-based
   by:* opt-in gate + warning-level + per-axis `unknown`. LASM is a *reported enrichment*; its absence is
   never a defect. Only *if present* are its tags checked against the fixed vocabulary.

3. **ADT defense grounding (§B).** *Risk:* requiring every attack node to have a defense would force the
   model to invent mitigations. *Kept property-based by:* defenses are **never required** (a plain attack
   tree passes invariant-1 style); only defense nodes *that are drawn* must ground to a declared
   `mitigation_id` — and an ungrounded one is a **warning**. This checks "does what you drew trace to what
   you found," never "you must defend threat X."

General rule applied everywhere: **if a check would change its verdict based on which finding/id/category
the model chose, it is wrong.** Every check above changes its verdict only on *well-formedness, id
resolution, or arithmetic recomputation* — all invariant to the model's content choices.

**Adversarial verification (skeptic pass).** An independent skeptic was tasked to *refute* the five
riskiest checks against the determinism boundary. Verdicts: ADT-defense-grounding (§B) and typed-icon
(§A) passed clean; STRIDE-applicability (§E) safe **only as a warning** with a declared-rationale hatch;
coverage ratios (§I) safe **only as reported metrics**, never a gate; a *required* LASM tag was ruled a
**straight violation** — accepted and already redesigned here to opt-in + warning-only. Two escape hatches
the skeptic surfaced are now folded in: `cross_applicable`/`stride_rationale` (§E) and
`mitigation:none\|accepted-risk` (§B). The L1-4/L1-7 regex collision it flagged is recommendation T4-11.

---

## 6. Engineering hazard: the L-layer namespace collision (must fix before T3)

Three different "layer" vocabularies now use overlapping `L#` tokens:

| Token | Meaning | Where |
|---|---|---|
| `Layer: L1..L4` | DFD **decomposition** level | existing diagram spec / `diagram_checks._layer_of` regex `Layer:\s*(L[1-4])` |
| `L1..L7` | **LASM** agent trust layers | arXiv:2604.23338 |
| `L1..L7` / `Layer 1..7` | **MAESTRO** reference-architecture layers | CSA MAESTRO |

`diagram_checks._layer_of` matches `Layer:\s*(L[1-4])`. If T3 emits a LASM/MAESTRO block stamped
`Layer: L5`, the current regex silently ignores it (harmless today) — but any future widening to `L[1-7]`
would make a LASM block masquerade as a DFD decomposition layer and corrupt the `missing-layers` check.
**Fix:** namespace the stamps — keep DFD as `Layer: L1..L4`, tag agent-layer artifacts with a distinct
key (`AgentLayer: L1..L7` + `Family: LASM|MAESTRO`). This is cheap eval hygiene that T1 (engine stamps)
and T3 (framework artifacts) must agree on. Recommendation **T4-11**.

---

## 7. Ranked recommendations

(Full JSON at the end. adoptability = fit to as-code deterministic boundary; impact = coverage/legibility
gain; effort 1=trivial.)

1. **T4-07** controlled-vocab label check (ATLAS/OWASP-LLM/OWASP-Agentic/MAESTRO regexes) — trivial, high
   value, pure extension of `malformed-mitre`. *adopt 5 / impact 3 / effort 1.*
2. **T4-08** reference-free coverage-ratio panel (reported, never gated) — the core T4 answer. *5/4/2.*
3. **T4-02** ADT well-formedness + grounding — extends `no-attack-tree`. *5/4/3.*
4. **T4-03** ATLAS layer check — extends `no-attack-layer`. *5/3/2.*
5. **T4-04** LINDDUN matrix check — clones STRIDE-matrix logic. *5/3/2.*
6. **T4-01** typed-icon/node-type vocabulary compliance — depends on T1's vocabulary. *4/4/2.*
7. **T4-09** heat-map cell==band(L×I) consistency — small enrichment. *5/2/1.*
8. **T4-11** L-layer namespace disambiguation — hygiene, blocks silent corruption. *5/2/1.*
9. **T4-05** STRIDE-per-element applicability (warning-only, boundary-guarded). *3/2/2.*
10. **T4-06** LASM layered/temporal grid (opt-in, warning-level). *3/2/3.*
11. **T4-10** SAND temporal-ordering DAG acyclicity for temporal attack artifacts. *4/2/2.*
12. **T4-12** cross-artifact "every HIGH+ finding appears in each applicable enriched artifact" meta-check
    (generalizes the existing overlay rule). *5/3/2.*

---

## 8. Open questions

- Does T1's engine emit node types as Mermaid `classDef`, an icon token, or a separate sidecar? The
  typed-icon checks (§A) key off whichever T1 picks — needs one agreed token.
- Will T2 emit ADTs as Mermaid (AND/OR text gates) or ADTool XML? The XSD path needs the extra
  `one-countermeasure`/`alternation` rules the schema can't express.
- Should coverage ratios ever influence the pass/fail *summary* at all, or stay purely informational? I
  recommend informational-only; confirm with L0.
- `owasp_agentic T1..T15` vs ATT&CK `T####` share the `T#` lexical space — is a declared `framework`
  field per id acceptable overhead, or should ids be prefixed (`OWASP-AGENTIC:T3`)?
- LASM and MAESTRO are both 2025–2026 single-source taxonomies; adopt now (opt-in) or wait for an industry
  standard? Recommend opt-in enrichment, not a required layer.

```json
{
  "track": "t4-evals",
  "recommendations": [
    {
      "id": "T4-07",
      "title": "Controlled-vocabulary label check for AI-security framework ids",
      "summary": "One reusable consistency check that validates any emitted framework id against the fixed regex for its declared framework (ATLAS AML.T####, OWASP-LLM LLM##:2025, OWASP-Agentic T1-T15, MAESTRO L1-7). Catches typos/fabrication; never demands a specific id.",
      "maps_to": "eval",
      "adoptability": 5,
      "impact": 3,
      "effort": 1,
      "risk": "low",
      "depends_on": ["T3-frameworks"],
      "evidence": "Mirrors existing malformed-cwe/malformed-mitre regex checks (checks.py:201-208). All four regexes live-verified against primary sources (mitre-atlas/atlas-data schemas; genai.owasp.org; CSA MAESTRO). Key on declared framework field to avoid the T1-15 vs T#### lexical collision.",
      "sources": ["https://github.com/mitre-atlas/atlas-data", "https://genai.owasp.org/llm-top-10/", "https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/", "https://cloudsecurityalliance.org/blog/2025/02/06/agentic-ai-threat-modeling-framework-maestro"]
    },
    {
      "id": "T4-08",
      "title": "Reference-free coverage-ratio panel (reported, never gated)",
      "summary": "Emit STRIDE-LM-category, trust-boundary, service/tech and actor coverage as ratios over the model's OWN recon, each beside its absolute numerator. Report as metrics; never threshold; keep recon-auditor as the anti-gaming backstop.",
      "maps_to": "eval",
      "adoptability": 5,
      "impact": 4,
      "effort": 2,
      "risk": "low",
      "depends_on": [],
      "evidence": "Verified against ACSE-Eval (only AWS-Service-Coverage is reference-free; TFC/CWE/ROUGE need a golden key) and the taxonomy-coverage audit (STRIDE-cat coverage over a FIXED 7-category denominator is reference-free by construction). Denominator-gaming failure mode confirmed; existing recon-auditor + red-team already defend it. Extends checks._scores.",
      "sources": ["https://arxiv.org/abs/2505.11565", "https://arxiv.org/abs/2411.17058", "https://arxiv.org/abs/2605.15118", "https://mlsec.org/docs/2025-ccsw.pdf"]
    },
    {
      "id": "T4-02",
      "title": "Attack-Defense Tree well-formedness + grounding check",
      "summary": "Extend the attack-tree check to the Kordy-Mauw ADT formalism: node types {attack,defense}, refinement {OR,AND}, <=1 countermeasure per node, strict role alternation, non-leaf has children, acyclic. Attack leaves ground to finding/recon ids; drawn defense nodes ground to declared mitigation ids (warning if not).",
      "maps_to": "eval",
      "adoptability": 5,
      "impact": 4,
      "effort": 3,
      "risk": "low",
      "depends_on": ["T2-artifacts"],
      "evidence": "Rules taken verbatim from Foundations of Attack-Defense Trees (FAST 2010) + ADTool manual XSD (primary sources fetched). Reuses existing >=3 kill_chains gate. Confirmed the XSD alone does NOT enforce one-countermeasure/alternation, so the parser must add them. Defenses never required (invariant-1) so no content is forced.",
      "sources": ["https://satoss.uni.lu/members/barbara/papers/adt.pdf", "https://satoss.uni.lu/members/piotr/adtool/manual.pdf", "https://arxiv.org/abs/1305.6829"]
    },
    {
      "id": "T4-03",
      "title": "MITRE ATLAS technique-layer well-formedness + grounding",
      "summary": "AI-system analogue of the ATT&CK-layer check: gate on a declared ATLAS id / agentic recon; verify domain=='atlas-atlas', techniqueID matches AML.T####(.###), sub-technique parents exist, and shown ids are a subset of findings' own atlas ids.",
      "maps_to": "eval",
      "adoptability": 5,
      "impact": 3,
      "effort": 2,
      "risk": "low",
      "depends_on": ["T3-frameworks"],
      "evidence": "domain string 'atlas-atlas' and AML.T#### regex live-verified against mitre-atlas/atlas-navigator-data (atlas_layer_matrix.json) and atlas-data output schema. Extends diagram_checks no-attack-layer. Discriminator (domain + AML prefix) prevents running the T#### regex over ATLAS ids.",
      "sources": ["https://github.com/mitre-atlas/atlas-data", "https://github.com/mitre-atlas/atlas-navigator-data", "https://github.com/mitre-attack/attack-navigator/blob/master/layers/spec/v4.5/layerformat.md"]
    },
    {
      "id": "T4-04",
      "title": "LINDDUN privacy matrix presence/shape/grounding",
      "summary": "Privacy analogue of the STRIDE-per-element matrix: gate on a declared PII surface / privacy finding; verify the 7 LINDDUN category columns (keys L,I,Nr,D,Dd,U,Nc), no blank cells (n/a|clean|finding-id), fixed-vocabulary labels (reject 'Information disclosure'), and PRO flow-has-Process rule.",
      "maps_to": "eval",
      "adoptability": 5,
      "impact": 3,
      "effort": 2,
      "risk": "low",
      "depends_on": ["T3-frameworks"],
      "evidence": "7-category set + two-vocabulary (gerund/noun) caveat + PRO interaction rule extracted from linddun.org primary pages and the PRO mapping-table PDF. LINDDUN-GenAI (arXiv:2603.06051) keeps the same 7 categories, so no AI-specific privacy vocab is needed. Clones no-stride-matrix logic.",
      "sources": ["https://linddun.org/threat-types/", "https://linddun.org/instructions-for-pro/", "https://downloads.linddun.org/tutorials/pro/v0/mappingtable.pdf", "https://arxiv.org/abs/2603.06051"]
    },
    {
      "id": "T4-01",
      "title": "Typed-icon / node-type vocabulary compliance",
      "summary": "Every diagram node carries a type token from T1's controlled vocabulary (unknown/other allowed); same type -> same icon/classDef across diagrams; legend covers every type used. Counts typed-vs-untyped and vocab membership, never which type a node is.",
      "maps_to": "eval",
      "adoptability": 4,
      "impact": 4,
      "effort": 2,
      "risk": "low",
      "depends_on": ["T1-engine"],
      "evidence": "Directly parallels the existing untyped-edges / ownership-marker fraction checks (diagram_checks.py:279,300). Reference-free because it compares to a fixed vocabulary + intra-doc consistency; 'unknown'/'other' escape hatch prevents forcing a type (invariant 6). Keyed off whatever type token T1 standardizes.",
      "sources": ["skills/threat-model/references/mermaid-diagrams.md", "skills/threat-model/evals/reliability/diagram_checks.py"]
    },
    {
      "id": "T4-09",
      "title": "Risk heat-map cell==band(L x I) consistency",
      "summary": "Each finding plotted at the cell matching its own (likelihood,impact) and the cell's band equals band(L x I); every scored finding appears exactly once. Recomputed from the finding's own numbers.",
      "maps_to": "eval",
      "adoptability": 5,
      "impact": 2,
      "effort": 1,
      "risk": "low",
      "depends_on": ["T2-artifacts"],
      "evidence": "Enriches existing no-risk-heatmap (diagram_checks.py:188). Reuses band() from checks.py. Analytical-visuals spec already requires exact cell placement; this makes it deterministic.",
      "sources": ["skills/threat-model/references/analytical-visuals.md", "skills/threat-model/references/frameworks.md"]
    },
    {
      "id": "T4-11",
      "title": "Disambiguate DFD L1-L4 vs agent-layer L1-L7 stamps",
      "summary": "Namespace the layer stamps: keep DFD decomposition as 'Layer: L1-L4'; tag LASM/MAESTRO agent-layer artifacts 'AgentLayer: L1-L7' + Family token, so the _layer_of regex can never mistake a LASM block for a DFD layer.",
      "maps_to": "eval",
      "adoptability": 5,
      "impact": 2,
      "effort": 1,
      "risk": "low",
      "depends_on": ["T1-engine", "T3-frameworks"],
      "evidence": "diagram_checks._layer_of matches 'Layer:\\s*(L[1-4])'. LASM (arXiv:2604.23338) and MAESTRO (CSA) both reuse L1-L7 for agent trust layers — a live collision if the DFD regex is ever widened. Cheap hygiene fix agreed across T1/T3.",
      "sources": ["https://arxiv.org/abs/2604.23338", "https://cloudsecurityalliance.org/blog/2025/02/06/agentic-ai-threat-modeling-framework-maestro"]
    },
    {
      "id": "T4-12",
      "title": "Cross-artifact coverage meta-check (HIGH+ appears in every applicable visual)",
      "summary": "Generalize the existing 'every HIGH+ finding annotated in the L4 overlay' rule: each HIGH+ finding must also appear in every OTHER applicable enriched artifact it qualifies for (STRIDE matrix, heat map, ATLAS layer, ADT). Projection consistency, never new content.",
      "maps_to": "eval",
      "adoptability": 5,
      "impact": 3,
      "effort": 2,
      "risk": "low",
      "depends_on": ["T2-artifacts", "T3-frameworks"],
      "evidence": "Generalizes diagram_checks.py:315-323 (high-findings-not-on-overlay) across artifacts. Pure projection of findings.json onto each visual; abstention via the artifact's own n/a/clean cells. Warning-level where an artifact is optional.",
      "sources": ["skills/threat-model/evals/reliability/diagram_checks.py"]
    },
    {
      "id": "T4-05",
      "title": "STRIDE-per-element applicability consistency (warning-only)",
      "summary": "Flag as a WARNING when a finding's STRIDE-LM tag disagrees with the classic element-type applicability chart for its declared dfd_type (e.g. Spoofing tagged on a data_store). Signals a possible mislabel to the judge; never a defect, never forces a category.",
      "maps_to": "eval",
      "adoptability": 3,
      "impact": 2,
      "effort": 2,
      "risk": "med",
      "depends_on": ["T3-frameworks"],
      "evidence": "Microsoft STRIDE-per-element chart (external entity->S,R; process->all6; data store->T,R,I,D; data flow->T,I,D) confirmed via Shostack ModSec08 + MS docs. RISKY: the chart has legitimate exceptions (a cache 'data store' can be spoofed), so kept warning-only + gated on declared dfd_type + suppressed on unknown/multi-type refs, so it never overrules the model's reasoning (see REPORT s5).",
      "sources": ["https://shostack.org/files/papers/modsec08/Shostack-ModSec08-Experiences-Threat-Modeling-At-Microsoft.pdf", "https://learn.microsoft.com/en-us/archive/msdn-magazine/2006/november/uncover-security-design-flaws-using-the-stride-approach"]
    },
    {
      "id": "T4-06",
      "title": "LASM layered/temporal grid well-formedness (opt-in, warning-level)",
      "summary": "When a run opts into LASM on an agentic system, verify each tagged threat has a layer in {L1..L7} and temporality in {T1..T4} from the fixed LASM sets, exactly one pair per threat, per-axis 'unknown' allowed. Never required on every finding.",
      "maps_to": "eval",
      "adoptability": 3,
      "impact": 2,
      "effort": 3,
      "risk": "med",
      "depends_on": ["T3-frameworks", "T4-11"],
      "evidence": "LASM 7-layer x 4-temporality grid from arXiv:2604.23338; it is a grid (ordinal labels), NOT a DAG. RISKY: young single-paper taxonomy, so opt-in + warning-only to avoid forcing a taxonomy the model didn't choose (REPORT s5). Depends on T4-11 namespace fix to avoid the L1-4/L1-7 collision.",
      "sources": ["https://arxiv.org/abs/2604.23338"]
    },
    {
      "id": "T4-10",
      "title": "SAND temporal-ordering DAG acyclicity for temporal attack artifacts",
      "summary": "If T2/T3 emits an ordered/temporal attack artifact (sequential-AND tree or phase graph), verify it is an acyclic ordered DAG whose SAND children are order-preserved and whose phases reference declared kill-chain steps. Structural only.",
      "maps_to": "eval",
      "adoptability": 4,
      "impact": 2,
      "effort": 2,
      "risk": "low",
      "depends_on": ["T2-artifacts"],
      "evidence": "SAND formalism (Jhawar et al., arXiv:1503.02261) is the correct home for temporal ordering, which ADTrees and LASM both LACK. Node types {leaf,OR,AND,SAND}; SAND children ordered; acyclic. Grounds phases to declared kill_chains[].steps.",
      "sources": ["https://arxiv.org/abs/1503.02261"]
    }
  ],
  "open_questions": [
    "How does T1's engine emit node types (Mermaid classDef vs icon token vs sidecar)? The typed-icon checks key off that token.",
    "Will T2 emit ADTs as Mermaid AND/OR text or ADTool XML? The XML path needs the extra one-countermeasure/alternation rules the XSD can't express.",
    "Should coverage ratios ever affect the pass/fail summary, or stay purely informational? Recommend informational-only.",
    "OWASP-Agentic T1-T15 shares the T# lexical space with ATT&CK T####: acceptable to key on a declared framework field, or prefix ids (OWASP-AGENTIC:T3)?",
    "LASM and MAESTRO are 2025-2026 single-source taxonomies: adopt as opt-in enrichment now or wait for an industry standard? Recommend opt-in, never a required layer."
  ],
  "poc_results": null
}
```
