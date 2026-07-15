# TRACK T2 — Missing cyber-relevant visual artifacts

**Question.** Beyond components + trust-boundaries + annotations, what visual artifacts does a mature
threat model surface that this suite is missing? Catalogue them, map each to its inputs, and rank the
genuinely-additive new artifacts.

**Method.** Read the ground-truth specs + worked example to fix *current* coverage precisely, fanned
out 4 parallel research agents over the candidate catalogue (web + standards), then ran one adversarial
skeptic to refute the top additions and to verify two suspicious arXiv IDs. All external claims cited.

---

## 1. What we ALREADY produce (precise baseline — do not "rediscover" these)

From `references/mermaid-diagrams.md`, `references/analytical-visuals.md`, `references/mermaid-spec.md`,
`references/visual-completeness-checklist.md`, `evals/reliability/diagram_checks.py`, and the ecs-fullstack
worked example:

| # | Existing artifact | Where specified |
|---|---|---|
| 1 | **Multi-layer DFD (L1–L4)** — full component detail, trust-boundary subgraphs, typed + sensitivity-tagged edges (`[PUBLIC/INTERNAL/CONFIDENTIAL/RESTRICTED]`, `[ENC/PLAIN]`, `[CTRL/AUTH/KEY/…]`), ownership markers (`[team:]/[vendor:]/[managed]`) | mermaid-spec/layers; `diagram_checks.py` reqs 1–4 |
| 2 | **L4 risk overlay** — risk-class coloring, per-node `⚠ STRIDE · L×I=score BAND / MITRE · CWE / ✓ {Mitigation} [{Status}] [R:{Residual}]`, TM-NNN linked to findings | mermaid-spec:157; diagram_checks req 5 |
| 3 | **Attack trees** (flowchart TD, AND/OR gates, feasibility coloring) | mermaid-diagrams §2 |
| 4 | **Attack-flow / kill-chain** (flowchart LR, temporal progression) | mermaid-diagrams §5 |
| 5 | **Auth sequence diagram** | mermaid-diagrams §3 |
| 6 | **Data-lifecycle diagram** (create→…→delete, classification+retention) | mermaid-diagrams §4 |
| 7 | **STRIDE-per-element coverage matrix** (element × S,T,R,I,D,E,LM; no blank cells) | analytical-visuals §1 |
| 8 | **Likelihood×Impact 5×5 risk heat map** | analytical-visuals §2 |
| 9 | **MITRE ATT&CK (enterprise) technique table + Navigator JSON layer** | analytical-visuals §3 |
| 10 | **RBAC / authorization matrix** (roles × resources, anon row, GAP cells) | analytical-visuals §4 |
| 11 | **SBOM / dependency graph** | analytical-visuals §5 |

**Inputs already in the manifests** (ecs-fullstack `recon.json` / `findings.json` / `coverage.json`):
- findings: `stride_lm[]`, `likelihood(1-5)`, `impact(1-5)`, `severity`, `cwe[]`, `mitre[]` (ATT&CK ids),
  `asset_refs[]`, `surface_refs[]`, `attack_path`, `remediation` (free text); `kill_chains[]` = `{id,goal,steps}`.
- recon: `roles[]`, `components[]`, `data_stores[]`, `entry_points[]`, `trust_boundaries[]` (with a `kind`
  field, e.g. `network`), `external_deps[]` (`manifest`, `risk`).
- coverage: `context` flags incl. **`has_ai_ml`**, **`has_personal_data`**, **`multi_tenant`**, `has_cloud`,
  `has_containers`, `has_cicd`, `has_regulatory`; per-item `state` (present/partial/missing).

Consequence: the suite already carries most inputs for the missing artifacts — the gaps are (a) an AI
technique namespace, (b) promoting `remediation` free-text into *addressable control objects*, and
(c) a post-mitigation risk pair. Almost nothing needs recon changes.

---

## 2. Coverage matrix (artifact × what-it-is / source / inputs / coverage / as-code? / additive value)

Legend — Coverage: **HAVE** / **PARTIAL** / **MISSING**. Additive: **YES / COND(itional) / NO**.

| Artifact | What it is | Framework/source | Inputs needed (in manifests?) | Coverage | As-code? | Additive |
|---|---|---|---|---|---|---|
| Leveled DFD 0/1/2 | Context→L1→L2 decomposition w/ balancing | Yourdon/DeMarco; MS SDL; Shostack | DFD hierarchy (have) | **HAVE** (= our L1–L4 multi-layer) | yes | **NO** — same value under Yourdon nomenclature |
| **STRIDE-per-interaction (bounded to boundary crossings)** | STRIDE enumerated per (src,flow,dst) tuple that *crosses a trust boundary* | Shostack; MS SDL/TM Tool | DFD edges + `trust_boundaries` (have) | **MISSING** | yes (table + tagged edges) | **YES (bounded)** — closes the boundary-crossing gap per-element structurally under-finds |
| **MITRE ATLAS Navigator layer** | Adversarial-ML tactics/techniques (`AML.Txxxx`): poisoning, evasion, model theft, prompt-injection, agent hijack | MITRE ATLAS (atlas.mitre.org) | `atlas`/`aml` ids on findings (**NEW**, small); gate `has_ai_ml` | **MISSING** | yes (reuse Navigator JSON emitter) | **YES — top pick** — enterprise ATT&CK cannot express ML techniques |
| **Attack-Defense Trees (ADTree)** | Attack trees + green defense nodes + dotted counter-edges | Kordy/Mauw/Radomirović/Schweitzer 2014; ADTool | control node + `counters:[attackNodeId]` (**NEW**) | **PARTIAL** (mitigations exist only on L4 overlay, not on the tree) | approx. in Mermaid (shapes/classes/dotted edges; AND-arc = convention) | **YES (capped)** — co-locates the defense with the attack it blocks; novelty capped by skeptic |
| **Threat→control coverage matrix** | findings × controls; flags threats with **zero** controls (coverage gaps) | MITRE CTID NIST-800-53↔ATT&CK Mappings Explorer | `controls:[id]` per finding (**NEW**, shared w/ ADTree) | **MISSING** | yes (markdown table) | **YES (cheap)** — the defensive dual of the STRIDE matrix; gap-flagging is a real reference-free property |
| MITRE D3FEND | Defensive countermeasure knowledge graph, ATT&CK-linked | d3fend.mitre.org | ATT&CK ids per finding (**have `mitre[]`**) | **MISSING** | not Mermaid-native | **COND** — best as a *control taxonomy* feeding ADTree/matrix, weak as its own visual |
| **Inherent→residual risk burndown** | before/after L×I per finding (heat map w/ pre→post, or register) | NIST 800-30/RMF; ISO 27005; FAIR | post-mitigation likelihood+impact pair (**NEW**, biggest add) | **PARTIAL** (inline `[R:Residual]` on L4 nodes) | yes (register table; quadrantChart) | **COND** — exec-requested but residual score is subjective (only monotonicity is checkable) |
| **LINDDUN-per-element privacy matrix** | element × 7 privacy categories (L,I,N,D,D,U,N) | LINDDUN PRO (linddun.org); LINDDUN-GenAI (arXiv 2603.06051) | `linddun[]` tags (**NEW**); gate `has_personal_data` | **MISSING** (categories *defined* in frameworks.md; no visual) | yes (reuse STRIDE renderer) | **COND** — real privacy gap but overlaps sibling **privacy-impact-assessment** skill (scope) |
| **OWASP LLM/Agentic Top 10 coverage checklist** | LLM01–LLM10 / ASI rows = covered? | OWASP GenAI Security Project | `llm_owasp[]` tag (**NEW**); gate `has_ai_ml` | **MISSING** | yes (reuse STRIDE renderer) | **COND** — additive as a checklist, content overlaps ATLAS; do not build a 2nd diagram |
| LASM layer×temporality matrix | 7 agent-stack layers × 4 temporality classes (T1 instantaneous … T4) | *single 2026 survey* — arXiv 2604.23338 (verified real) | `lasm_layer` + `temporality` tags (**NEW**); gate `has_ai_ml` | **MISSING** | yes (2D matrix) | **COND (experimental)** — only the *temporality* axis is new; one preprint, low authority, agent-only; **the "infra-layer onion" framing in the brief is a mislabel** — LASM layers are LLM-agent-specific |
| Data-classification overlay | color stores+flows by sensitivity | NIST FIPS 199 / ISO 27001 A.5.12 | sensitivity tags (**have** on edges) | **HAVE** (edge tags) | yes | **NO** — already annotate `[PUBLIC/…/RESTRICTED]`; at most node coloring |
| Trust-zone / network-segmentation map | zones + *allowed* inter-zone flows (policy view) | NIST SP 800-207; CISA microsegmentation; PCI 11.4 | `trust_boundaries.kind=network` (have) | **PARTIAL** ("Network Zones" is a checklist category; drawn as DFD subgraphs) | yes | **NO/thin** — ~80% overlaps trust-boundary subgraphs; only allow/deny policy is new |
| CVSS scoring viz / exploitability gauge | 0–10 severity gauge + vector | FIRST.org CVSS v3.1/v4.0 | full CVSS vector (~8–11 sub-fields) + scorer (**NEW, heavy**) | **MISSING** | yes (badge) | **NO** — score duplicates our severity band; high schema cost |
| DREAD scoring viz | D,R,E,A,D sub-scores | Microsoft (**internally deprecated**) | 5 sub-scores (**NEW**) | **MISSING** | yes | **NO** — deprecated, subjective; L×I is the better version |
| Sankey (data-volume / privilege flow) | flow width ∝ magnitude | Mermaid `sankey-beta` | per-edge numeric weight (**NEW**; none today) | **MISSING** | yes (native) | **COND** — useful *only* with real data-volume weights; else decorative |

---

## 3. Determinism-boundary note (shapes every eval below)

The skeptic's central point is correct and constrains every recommendation: the genuinely-new information
in an artifact often requires judging whether a *mapping/placement/score is correct* — which the
determinism boundary forbids. So each new artifact's deterministic check must verify **structure /
grounding / coverage only**, never correctness:
- ATLAS layer → every `AML.Txxxx` shown is a real ATLAS id **and** equals the distinct `atlas[]` ids across
  findings (same grounding rule as today's ATT&CK layer). ✅ clean.
- Boundary-crossing table → every DFD edge that crosses a `trust_boundary` has exactly one row (coverage
  property). ✅ clean; validity of the threats = judge.
- ADTree → every defense node references a real finding/control id and attaches to an attack node
  (grounding+structure). Whether the defense truly interdicts the path = judge. ✅ scoped.
- Control matrix → every finding maps to ≥1 control id; uncovered findings are flagged (coverage). ✅ clean.
- Residual burndown → only `residual ≤ inherent` monotonicity is structural; the residual number itself is
  **not** reference-free verifiable. ⚠ weakest.

This is why ATLAS + the coverage/boundary tables rank above ADTree/residual: their novel content is
grounding/coverage-shaped, not correctness-shaped.

---

## 4. Ranked recommendations

1. **T2-01 MITRE ATLAS Navigator layer** — unanimous keep; reuses the existing Navigator emitter with an
   ATLAS `domain`; fills the AI/ML attack surface enterprise ATT&CK structurally cannot. Gate `has_ai_ml`.
2. **T2-02 Attack-Defense Trees** — extend the existing Mermaid attack-tree generator with green defense
   nodes + dotted counter-edges; requires promoting `remediation` → addressable control objects.
3. **T2-03 Threat→control coverage matrix** — cheapest; shares T2-02's control ids; the only artifact that
   flags *findings with no control* (a real reference-free coverage property).
4. **T2-04 Trust-boundary-crossing interaction table** — bounded STRIDE-per-interaction over crossing edges
   only; no new fields; targets exactly where agentic/cloud threats live (tool call / net hop / identity handoff).
5. **T2-05 OWASP LLM/Agentic Top 10 coverage checklist** — reuse the STRIDE-matrix renderer with an
   LLM-Top-10 axis; low effort; gate `has_ai_ml`; do **not** build a separate diagram (content ⊂ ATLAS).
6. **T2-06 LINDDUN-per-element privacy matrix (or privacy cross-ref)** — real privacy-harm gap, but overlaps
   the sibling privacy-impact-assessment skill; recommend a lightweight matrix gated on `has_personal_data`
   *or* an explicit hand-off — resolve ownership first (open question).
7. **T2-07 Inherent→residual risk burndown view** — exec/audit-requested, but needs a post-mitigation L×I
   pair and its residual score is not reference-free verifiable; low priority, ship only monotonicity checks.
8. **T2-08 LASM layer×temporality matrix (experimental)** — adopt only the *temporality* axis for agentic
   targets; one preprint, low authority; depends on the framework track picking up LASM. Speculative.

**Cut outright:** leveled DFD 0/1/2, data-classification overlay, CVSS gauge, DREAD, standalone
trust-zone map (all redundant/deprecated per §2 matrix).

---

## 5. arXiv verification (adversarial)

Both IDs the research surfaced **resolve to real papers** (control probe `arxiv.org/abs/2604.99999` → HTTP
404, confirming the fetcher reports non-existence rather than confabulating). They are *not* future-dated —
today is 2026-07-15.
- **arXiv 2604.23338** — "A Systematic Survey of Security Threats and Defenses in LLM-Based AI Agents: A
  Layered Attack Surface Framework" (K. Chu, 25 Apr 2026). LASM = 7 layers + 4 temporal classes; 116-paper survey.
- **arXiv 2603.06051** — "A LINDDUN-based Privacy Threat Modeling Framework for GenAI" (Liao, Bellemans,
  Sion et al., KU Leuven DistriNet + Huawei, 6 Mar 2026).

---

```json
{
  "track": "t2-artifacts",
  "recommendations": [
    {
      "id": "T2-01",
      "title": "MITRE ATLAS Navigator layer for the AI/ML attack surface",
      "summary": "Emit an ATLAS (AML.Txxxx) technique table + Navigator JSON layer using the SAME emitter as the existing ATT&CK-enterprise layer, gated on coverage.context.has_ai_ml. Fills the adversarial-ML surface (poisoning, evasion, model theft, prompt-injection, agent hijack) that enterprise ATT&CK cannot express.",
      "maps_to": "artifact",
      "adoptability": 5,
      "impact": 4,
      "effort": 2,
      "risk": "low",
      "depends_on": [],
      "evidence": "ATLAS ships an ATT&CK-Navigator-compatible layer schema (atlas-navigator-data) identical to the layer we already generate; reference-free check = grounding (every AML id shown is real and equals the distinct atlas[] ids across findings), same rule as today's ATT&CK layer. Needs a small new finding field atlas[]/aml[]. Unanimous keep across research + skeptic.",
      "sources": ["https://atlas.mitre.org/", "https://github.com/mitre-atlas/atlas-navigator-data", "https://github.com/mitre-atlas/atlas-data"]
    },
    {
      "id": "T2-03",
      "title": "Threat-to-control coverage matrix (flags findings with no control)",
      "summary": "A findings × controls table whose one reference-free property is coverage: every finding maps to >=1 control id, and findings with zero controls are surfaced as gaps. The defensive dual of the STRIDE-per-element matrix; nothing today shows control coverage of threats.",
      "maps_to": "artifact",
      "adoptability": 4,
      "impact": 4,
      "effort": 2,
      "risk": "low",
      "depends_on": ["T2-02"],
      "evidence": "Cheapest of the set. Requires promoting free-text remediation into addressable control objects (controls:[id] per finding) shared with T2-02; the 'uncovered finding' flag is a clean coverage check that does not judge correctness. MITRE CTID NIST-800-53<->ATT&CK Mappings Explorer is the model; D3FEND (findings already carry mitre[]) can supply normalized control names.",
      "sources": ["https://center-for-threat-informed-defense.github.io/mappings-explorer/external/nist/", "https://d3fend.mitre.org/mappings/attack-mitigations/"]
    },
    {
      "id": "T2-02",
      "title": "Attack-Defense Trees (defense nodes + counter-edges on attack trees)",
      "summary": "Extend the existing Mermaid attack-tree generator with green defense nodes and dotted counter-edges attaching each control to the attack node it interdicts, per the Kordy/Mauw ADTree grammar. Co-locates the mitigation with the attack it blocks — new on the tree, which today shows zero defenses.",
      "maps_to": "artifact",
      "adoptability": 4,
      "impact": 3,
      "effort": 3,
      "risk": "med",
      "depends_on": ["T2-03"],
      "evidence": "Small extension of the current attack-tree pipeline (classDef color, node shape, -.-> edges); AND-arc semantics remain convention, not enforced. Skeptic capped novelty: defense text overlaps the L4 overlay's `✓ Mitigation`, so the genuinely-new bit is the attack-node<->control edge relation (needs counters:[attackNodeId]). Eval scoped to grounding+structure only (every defense node references a real control/finding, attaches to an attack node).",
      "sources": ["https://satoss.uni.lu/members/barbara/papers/adt.pdf", "https://link.springer.com/chapter/10.1007/978-3-642-40196-1_15", "https://newsletter.vithanco.com/p/new-notation-attack-defence-trees"]
    },
    {
      "id": "T2-04",
      "title": "Trust-boundary-crossing interaction table (bounded STRIDE-per-interaction)",
      "summary": "Enumerate STRIDE over each (source, flow, destination) tuple that CROSSES a trust boundary — the documented complement to STRIDE-per-element that structurally catches boundary-crossing threats. Bounded to crossings to avoid per-edge combinatorial noise (the reason Microsoft de-emphasized full per-interaction).",
      "maps_to": "artifact",
      "adoptability": 5,
      "impact": 3,
      "effort": 2,
      "risk": "low",
      "depends_on": [],
      "evidence": "No new manifest fields — derives from DFD edges + recon.trust_boundaries already present. Reference-free check = coverage property (every boundary-crossing edge yields exactly one row); threat validity left to the judge. For agentic/cloud systems the trust-boundary crossing (tool call, network hop, identity handoff) is where real threats concentrate. Skeptic flagged noise risk -> mitigated by the boundary-crossing bound.",
      "sources": ["https://ceur-ws.org/Vol-413/paper12.pdf", "https://learn.microsoft.com/en-us/archive/msdn-magazine/2006/november/uncover-security-design-flaws-using-the-stride-approach", "https://cheatsheetseries.owasp.org/cheatsheets/Threat_Modeling_Cheat_Sheet.html"]
    },
    {
      "id": "T2-05",
      "title": "OWASP LLM / Agentic Top 10 coverage checklist",
      "summary": "Render LLM01-LLM10 (and OWASP Agentic/ASI) as a coverage checklist using the existing STRIDE-matrix renderer with an OWASP-LLM axis, gated on has_ai_ml. A checklist, not a new diagram — its threat content overlaps ATLAS and should project onto the ATLAS layer, not duplicate it.",
      "maps_to": "artifact",
      "adoptability": 5,
      "impact": 3,
      "effort": 1,
      "risk": "low",
      "depends_on": ["T2-01"],
      "evidence": "Fixed 10-row enum; reuses the STRIDE-matrix table generator with a new llm_owasp[] finding tag. Community crosswalks map every LLM Top 10 item to ATLAS techniques (GenAI-Security-Crosswalk publishes a ready ATLAS Navigator layer), so it layers on T2-01 rather than standing alone.",
      "sources": ["https://genai.owasp.org/llm-top-10/", "https://github.com/emmanuelgjr/GenAI-Security-Crosswalk"]
    },
    {
      "id": "T2-06",
      "title": "LINDDUN-per-element privacy coverage matrix (or explicit PIA hand-off)",
      "summary": "element x 7 LINDDUN categories (reuse STRIDE renderer), gated on has_personal_data, surfacing privacy harms (linkability, re-identification, unawareness, non-compliance) no current artifact expresses. frameworks.md already DEFINES the categories but produces no visual.",
      "maps_to": "artifact",
      "adoptability": 4,
      "impact": 3,
      "effort": 2,
      "risk": "med",
      "depends_on": [],
      "evidence": "Cheap (STRIDE renderer, swap axis to the 7 LINDDUN categories; new linddun[] tag). BUT a sibling privacy-impact-assessment skill already owns LINDDUN (linddun-go-threats.md) -> scope overlap. Recommend resolving ownership: a lightweight security-side privacy matrix vs an explicit cross-reference/hand-off to the PIA skill. LINDDUN-GenAI (arXiv 2603.06051, verified) is the has_ai_ml extension.",
      "sources": ["https://linddun.org/", "https://downloads.linddun.org/tutorials/pro/v0/tutorial.pdf", "https://arxiv.org/abs/2603.06051"]
    },
    {
      "id": "T2-07",
      "title": "Inherent->residual risk burndown view",
      "summary": "A before/after view (risk register with pre/post columns, or a heat map with pre->post movement) showing whether mitigations actually move the needle. Answers the exec/audit 'is residual risk acceptable' question the L4 overlay's inline [R:Residual] label only hints at.",
      "maps_to": "artifact",
      "adoptability": 3,
      "impact": 3,
      "effort": 3,
      "risk": "med",
      "depends_on": [],
      "evidence": "Weakest additive: L4 nodes already carry [R:Residual] inline, so a dedicated view is partly a re-pivot; requires a NEW post-mitigation likelihood+impact pair per finding (biggest schema add). Determinism limit: only residual<=inherent monotonicity is a structural check; the residual score itself is subjective and cannot be reference-free verified. Required by NIST 800-30/RMF, ISO 27005, FAIR.",
      "sources": ["https://www.fairinstitute.org/blog/inherent-risk-vs.-residual-risk-explained-in-90-seconds", "https://secureframe.com/blog/iso-27005", "https://csrc.nist.gov/pubs/publications/detail/sp/800-30/rev-1/final"]
    },
    {
      "id": "T2-08",
      "title": "LASM layer x temporality matrix (experimental, agentic only)",
      "summary": "Plot findings on a 7-layer agent-stack x 4-class temporality grid (T1 instantaneous ... T4), highlighting the slow-burn high-layer corner. Only the TEMPORALITY axis is genuinely new vs the L×I heat map; adopt for LLM/agent targets only.",
      "maps_to": "artifact",
      "adoptability": 3,
      "impact": 2,
      "effort": 4,
      "risk": "high",
      "depends_on": ["T2-01"],
      "evidence": "Source verified real (arXiv 2604.23338, K. Chu, Apr 2026) but it is a single low-authority preprint scoped to agentic AI; the brief's 'infra-layer onion' framing is a MISLABEL (LASM layers are Foundation/Cognitive/Memory/Tool/Multi-Agent/Ecosystem/Governance, not external/network/host/app/data). Needs new lasm_layer + temporality finding tags and belongs to the framework track's remit. Speculative -> low priority.",
      "sources": ["https://arxiv.org/abs/2604.23338", "https://arxiv.org/html/2604.23338v2"]
    }
  ],
  "open_questions": [
    "T2-01/T2-05/T2-08 need a framework-track (T3) decision on the AI technique namespaces (ATLAS AML ids, OWASP-LLM ids, LASM layer/temporality classes) and a curated allowlist analogous to frameworks.md's ATT&CK/CWE 'Framework ID Verification' rules — otherwise findings will fabricate ids.",
    "Manifest schema additions required and their owner: findings.atlas[] (T2-01), findings.controls[] as addressable objects with counters:[attackNodeId] (T2-02/T2-03), findings.llm_owasp[] (T2-05), findings.linddun[] (T2-06), post-mitigation likelihood/impact pair (T2-07), lasm_layer+temporality (T2-08). Promoting free-text `remediation` into addressable control objects is the shared enabler for T2-02/T2-03/T2-07.",
    "T2-06 scope: does LINDDUN privacy analysis live in the threat-model skill or the sibling privacy-impact-assessment skill (which already ships linddun-go-threats.md)? Resolve before building to avoid duplication.",
    "Sankey diagrams (Mermaid sankey-beta) are additive ONLY if a per-edge data-volume/record-count weight is captured; the manifests have no such field today. Worth it only if data-volume-across-boundaries is a target use case — otherwise decorative.",
    "D3FEND: since findings already carry mitre[] ATT&CK ids, auto-mapping to D3FEND countermeasures is feasible and could supply normalized control names for T2-02/T2-03 — but D3FEND is weak as its own visual and has no Navigator-style JSON layer. Use as taxonomy, not artifact."
  ],
  "poc_results": null
}
```
