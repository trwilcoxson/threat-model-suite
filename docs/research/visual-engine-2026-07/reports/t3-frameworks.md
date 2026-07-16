# Track T3 — Modern-Framework Integration (2024–2026 LLM/agentic threat-modeling literature)

**Question:** Which concrete elements from the recent LLM/agentic-threat-modeling literature should
`threat-model-suite` adopt, and how does each map to a visual artifact (T2), an eval (T4), or a
pipeline change (T5) — without breaking the determinism boundary (frameworks guide the agent's
reasoning; they must never become an answer key)?

**Method.** Six parallel research sub-agents clustered the owner-supplied corpus
(benchmarks/metrics · STRIDE extensions · agentic frameworks · privacy/LINDDUN-GenAI ·
attack-defense trees + CVSS · layered/temporal), each finding primary sources and adversarially
killing low-signal items. A seventh skeptic verified the two load-bearing claims (OWASP ASI01–10;
CVSS v3.1 determinism). Findings below are the survivors.

---

## The one framing that makes almost everything adoptable

The literature is full of **reference-based** metrics (recall / ROUGE / cosine-similarity against an
expert answer key). None of those can be a deterministic eval for this suite. But three structural
patterns recur that are **natively reference-free** and map onto the suite's existing property-eval
machinery:

1. **Coverage over a fixed partition** — a taxonomy (STRIDE cells, OWASP ASI01–10, lifecycle stages)
   where the eval checks *every applicable cell is resolved to a terminal state* (finding /
   examined-clean / n-a / unknown, each with evidence), never *which* threat is correct. This is
   exactly the existing `coverage.json` ledger + STRIDE-per-element matrix pattern.
2. **Coverage as a ratio with a *discoverable* denominator** — the inversion that rescues ACSE-Eval:
   `found / discoverable-from-recon.json`, never `found / golden-set`.
3. **A closed-form formula over agent-chosen inputs** — CVSS v3.1 exploitability. The agent picks the
   metric values (judgment, no ground truth); the eval recomputes the arithmetic and checks the
   agent's own stated band. Pure internal-consistency check.

Every high-ranked recommendation below is one of these three shapes.

---

## Current-suite baseline (what we already have — to avoid re-adopting)

- STRIDE-**LM** (STRIDE + Lateral Movement), **per-element** matrix (`analytical-visuals.md §1`).
- PASTA (7 stages) → Likelihood×Impact (1–5 each → 1–25 bands, `frameworks.md`).
- MITRE ATT&CK (enterprise), CWE groups, OWASP Top 10 (2021) + API Top 10 (2023), LINDDUN (7 classic
  categories), cloud-native patterns, an AI/ML supplement (LLM app / agentic / RAG / multi-modal).
- Attack **trees** + attack **flows** per kill chain; L×I heat map; ATT&CK Navigator layer; SBOM graph.
- A 225-item coverage taxonomy resolved to terminal states in `coverage.json`.
- Phase 5 already reasons about *temporal* threats (key rotation, cert expiry, drift) but with **no
  structured tag** recording *when in the lifecycle* a threat manifests.

The gaps the literature fills: no per-**interaction/edge** STRIDE view; Likelihood is a subjective
1–5 vibe with no decomposed justification; attack trees have no **defense/countermeasure** nodes;
no **agentic** coverage partition (OWASP ASI, MITRE ATLAS); privacy is classic LINDDUN with no
GenAI-native lenses; no lifecycle/temporal tag; no coverage *ratios* over discoverable facts.

---

## Cluster findings (primary sources + the survivor per cluster)

### A. Benchmarks & metrics — *take schemas, not metrics*
- **ACSE-Eval** (arXiv 2505.11565; dataset + MIT-licensed scorer public). Confirmed from `scorer.py`:
  TFC (Threat *Framework* Coverage), CWE coverage, AWS Service Coverage are all **`found / golden`**
  recall — **reference-based**, cannot be deterministic evals for us. ROUGE-L and semantic-similarity
  likewise. **Survivors:** its clean per-threat JSON schema (STRIDE+OWASP+MITRE+CWE+affected-components
  +C/I/A+likelihood+recommendations) and the *idea* of coverage-as-ratio, **re-based on recon.json**.
- **ThreatModeling-LLM** (arXiv 2411.17058): Precision/Recall/Jaccard/BERT-sim, all golden-set;
  dataset non-public. **Survivor:** the STRIDE→mitigation→NIST-800-53 chain shape as prompt scaffold.
- **ThreMoLIA** (arXiv 2504.18369, vision paper): endorses **reference-free structural metrics**
  (DFD node/edge counts, model complexity) as a legitimate axis; supplies an OWASP-LLM-Top-10 ×
  MITRE-ATLAS mapping table. **Survivors:** those two, as taxonomy + a structural well-formedness eval.

### B. STRIDE extensions — *per-interaction, scoped to boundaries; kill DREAD*
- **STRIDE-per-interaction** (Shostack, MS SDL/TMT-2016 default): analyze each (source, dest, flow)
  tuple, i.e. each **edge**, not each element. A replicated controlled experiment (arXiv 2208.01524)
  found **no statistically significant** accuracy gain over per-element — so its value for us is not
  accuracy, it's that a **per-edge grid is a natural verifiable coverage property**.
- **LLM-Enabled Robotic Systems** (arXiv 2604.27267): the scaling discipline to copy — apply
  per-interaction STRIDE **only at trust-boundary-crossing edges** (6 points, not all edges), with a
  **CCT/AdvT/ConT** overlay keyed to ATT&CK / ATLAS / OWASP-LLM per crossing.
- **LLM-Powered Applications** (arXiv 2406.11007): Shostack's **4 Questions** (useful persona
  framing); DREAD scoring — **killed** (subjective, MS-abandoned, not OWASP-recommended, redundant
  with our L×I; even this pro-DREAD paper only uses H/M/L with no formula).

### C. Agentic frameworks — *anchor on OWASP ASI + Berkeley survey; ASTRIDE/ATFAA are mostly subsets*
- **Attack & Defense Landscape of Agentic AI** (arXiv 2603.11088; USENIX Sec 2026; Song/Li/Guo) — the
  strongest source. **R1–R7** risk set (adds Resource-Drain/DoS R7, Unsafe-Data-Flow R3) + **7 design
  dimensions** (Input Trust, Workflow, Access Sensitivity, Action, Tool, Memory, UI) that are
  **code-observable recon flags**.
- **OWASP Top 10 for Agentic Applications 2026** (real OWASP GenAI deliverable, 9 Dec 2025) —
  **ASI01–10** as the canonical, citable coverage partition (the survey subsumes ASTRIDE/ATFAA).
  Official titles (verified): ASI01 Agent Goal Hijack · ASI02 Tool Misuse · ASI03 Identity & Privilege
  Abuse · ASI04 Agentic Supply Chain Vulnerabilities · ASI05 Unexpected Code Execution · ASI06 Memory
  & Context Poisoning · ASI07 Insecure Inter-Agent Communication · ASI08 Cascading Failures · ASI09
  Human-Agent Trust Exploitation · ASI10 Rogue Agents. (Lock these exact strings — OWASP's own
  materials show some wording drift.)
- **ASTRIDE** (arXiv 2512.04785): the "A" letter is repackaged prompt-injection/tool-misuse already in
  ASI01/02/06; its VLM-consortium-reads-a-PNG pipeline solves a problem **we don't have** (we own the
  structured DFD from code recon). **Kill** the VLM pipeline and the "A" bucket; keep one cue
  ("reasoning/plan-path subversion").
- **ATFAA/SHIELD** (arXiv 2504.19956): 9 threats; most duplicate our list. **Survivors:** T2 goal
  *drift*, T5 resource-exhaustion, T7 human→agent trust, **T8 oversight-saturation**, **T9 agent
  repudiation/audit-obfuscation** (STRIDE-R for agents) — 5 orphan cues. **SHIELD killed** (generic
  control checklist; we find threats, not prescribe controls).

### D. Privacy — *LINDDUN-GenAI as a lens set for the privacy-agent, not a new taxonomy*
- **LINDDUN-based Privacy TM for GenAI** (arXiv 2603.06051): extends only **3 of 7** LINDDUN
  categories (Disclosure, Unawareness, Non-compliance). ~30% genuinely new. **Survivors:** the **6
  Common Attacker Models (CAMs)** — data-flow leakage vectors telling the agent *where* to look in an
  LLM/agent topology — plus **fabricated/hallucinated PII** (DD.3.5), **intermediary-data reversibility**
  (embeddings/vector-store inversion, DD.1.3), and the **decision-manipulation** subtree.
  **Killed/gated:** importing the 100 examples (padding); training-context threats (CAM3, gradient
  leakage, membership inference) unless a `trains_or_finetunes_model` flag is set; AI-Act compliance
  (unverifiable reference-free — soft "flag for review" only). Cross-session memory linkability is
  real but classic LINDDUN Linkability already covers it (zero novelty).

### E. Attack-defense trees + CVSS — *the highest-signal cluster*
- **Where Do LLM-based Systems Break?** (arXiv 2603.07460): DFD → **attack-defense trees** (defense
  nodes that *transform* a leaf's CVSS metrics rather than deleting it) → **CVSS v3.1 exploitability**
  per leaf → OR/AND/SAND propagation (`max`/`min`). Impact attached only at the goal node. Cleanly
  matches our L×I split: **exploitability → Likelihood; goal impact → Impact**.
- **ADTree formalism** (Kordy/Mauw/Radomirović/Schweitzer, FAST 2010): defense nodes are semantic, no
  fixed notation — so we render them as styled Mermaid nodes with a `control_ref` + `metric_transform`.
- **CVSS v3.1** (FIRST.org): closed-form `8.22 × AV × AC × PR × UI` → deterministic formula-check eval.
  **CVSS v4.0** dropped the closed-form sub-score for a MacroVector lookup table → worse eval fit,
  keep AT/Automatable as optional tags only.
- **ASTRAL** (arXiv 2604.05674): Bayesian-Network risk — **killed** (expert-elicited CPTs have no
  ground truth and no structural check; too heavy for an as-code pipeline; OR/AND/SAND gets ~80% of
  the path-aggregation value deterministically at ~5% of the cost).

### F. Layered / temporal — *extract the temporality tag; skip the 7×4 matrix*
- **LASM survey** (Layered Attack Surface + temporality; 7 agent-specific layers × 4 temporal classes).
  The 7 layers are agent-stack-specific and redundant with our 225-item taxonomy; forcing 28 cells
  onto a small non-agentic system over-fragments. **Survivor (the one hard extraction):** the
  **temporality axis** → a `temporal_class` lifecycle tag on findings + a reference-free "did the
  model consider non-runtime threats?" coverage check. Codebase-agnostic, cheap, fixes our
  static-snapshot blind spot. (Arxiv id for the survey to be reconfirmed — see Open Questions — but
  the temporality *concept* is well-grounded independent of that specific paper.)

---

## Master table — element → adopt-as → maps_to → effort/impact

| # | Element | What it adds | Adopt-as | maps_to | Ref-free? | Effort | Impact |
|---|---------|--------------|----------|---------|-----------|--------|--------|
| T3-01 | **CVSS v3.1 exploitability** as decomposed Likelihood | AV/AC/PR/UI vector behind every Likelihood; grounded + auditable + a **formula-check eval** | framework (+eval) | framework | **Y** (formula) | 2 | 5 |
| T3-02 | **STRIDE-per-interaction**, boundary-scoped per-edge matrix | edge-level threats per-element misses; a verifiable per-edge coverage grid | artifact (+eval) | artifact | **Y** (grid property) | 3 | 4 |
| T3-03 | **Attack-defense-tree nodes** (control_ref + metric_transform) | interleave controls that *move* CVSS metrics; shows chokepoints that break many kill chains | artifact | artifact | **Y** (structure/arith) | 2 | 4 |
| T3-04 | **OWASP ASI01–10** agentic coverage partition | canonical agentic-threat class list → reference-free "resolve every class" ledger check | eval (+persona) | eval | **Y** (partition) | 2 | 4 |
| T3-05 | **`temporal_class` lifecycle tag** (design/build/deploy/runtime/decommission) | records *when* a threat manifests → "considered non-runtime threats?" check | framework (+eval) | framework | **Y** (coverage) | 2 | 4 |
| T3-06 | **LINDDUN-GenAI CAMs** + fabricated-PII + embedding-inversion | GenAI-native privacy lenses for the privacy-agent; optional PII/vector-store overlay | framework (+eval/artifact) | framework | **Y** (coverage) | 2 | 4 |
| T3-07 | **Coverage-as-ratio, discoverable denominator** (ACSE inversion) | CWE-mappable-to-sinks & cloud-service coverage over recon.json, not a golden set | eval | eval | **Y** (recon-based) | 4 | 4 |
| T3-08 | **Berkeley survey R1–R7 + 7 design dimensions** | agentic reasoning scaffold + code-observable recon flags gating agentic evals | framework (+recon) | framework | **Y** (flags/taxonomy) | 3 | 4 |
| T3-09 | **ACSE per-threat schema + multi-framework tagging** discipline | every finding carries ≥1 STRIDE + framework tag → well-formedness check | eval (+schema) | eval | **Y** (well-formed) | 2 | 3 |
| T3-10 | **MITRE ATLAS + OWASP LLM Top 10** reference taxonomies (CCT/AdvT/ConT) | AI/LLM/adversarial-ML classes STRIDE/CWE miss, keyed to boundary edges | framework | framework | **Y** (taxonomy) | 2 | 3 |
| T3-11 | **Goal-driven** security-objectives step | anchor impact on system goals; dedupe shared attack paths | pipeline | pipeline | **Y** (agent-authored) | 2 | 3 |
| T3-12 | **Shostack's 4 Questions** persona framing | structures agent reasoning end-to-end (Q4 == our eval philosophy) | framework | framework | **Y** (framing) | 1 | 2 |
| T3-13 | **Agent-trust / tool-permission overlay** on DFD | which agent may call which tool; delegation edges across trust boundaries | artifact | artifact | **Y** (structure) | 3 | 3 |

**Killed (do not adopt):** DREAD scoring · ASTRIDE VLM-consortium pipeline · ASTRIDE "A" as a new
STRIDE letter · SHIELD control checklist · ASTRAL Bayesian-Network risk · CVSS v4.0 numeric scoring ·
full LASM 7×4 matrix as a default coverage spine · importing the 100 LINDDUN-GenAI examples ·
unscoped per-interaction (all-edges × 6) · all reference-based ACSE/ThreatModeling-LLM metrics
(TFC, ROUGE-L, semantic sim, golden-set Precision/Recall/Jaccard).

---

## Ranked recommendations (detail)

### T3-01 — CVSS v3.1 exploitability as decomposed, auditable Likelihood *(top pick)*
Have the security-architect emit a CVSS v3.1 vector (`AV:N/AC:L/PR:N/UI:N`) alongside each
Likelihood score, mapping the exploitability sub-score onto the existing 1–5 band. The agent chooses
the metric values (judgment, no ground truth — determinism boundary intact); a ~15-line deterministic
eval recomputes `8.22 × AV × AC × PR × UI` and asserts the agent's stated band matches. This is the
single highest-signal item: it turns "Likelihood = 4" (a vibe) into "Likelihood = 4 because
`AV:N/AC:L/PR:N/UI:R`" (decomposed + checkable) **and** yields a genuine reference-free eval with no
answer key. Keep the 1–5 band as the user-facing number to avoid CVSS false-precision; compute the
vector internally for the audit trail. **maps_to:** framework. **depends_on:** T4 (the formula-check
eval). **Risk:** low.

### T3-02 — STRIDE-per-interaction: boundary-scoped per-edge coverage matrix *(highlighted)*
Add a second coverage matrix (alongside the existing per-element one): rows = trust-boundary-crossing
DFD edges (keyed by recon id), columns = the 7 STRIDE-LM categories, cells = `TM-NNN` / `n/a` /
`clean`. **Scope to boundary edges only** (the robotics paper's discipline) — an all-edges grid
explodes combinatorially with no measured accuracy gain (arXiv 2208.01524). Eval = every boundary
edge has a decided row across all categories (same property-check class as the element matrix).
**maps_to:** artifact. **depends_on:** T2 (matrix render), T4 (the coverage property). **Risk:** low.

### T3-03 — Attack-defense-tree nodes (metric-transform semantics) *(highlighted)*
Extend the existing attack-tree diagram with `:::defense` nodes carrying `control_ref` (resolves to a
control in recon) + `metric_transform` (a legal CVSS metric change, e.g. MFA: `PR:N→H`; HITL gate:
`UI:N→R`; canonicalization: `AC:L→H`). Reference-free structure checks: (1) every defense node's
`control_ref` resolves in recon; (2) the transform is a legal CVSS change; (3) the parent's
post-transform exploitability equals the recomputed formula. This shows "one mTLS control breaks 3 of
5 kill chains" — a chokepoint view a flat control inventory can't. **maps_to:** artifact.
**depends_on:** T2, T3-01. **Risk:** low.

### T3-04 — OWASP ASI01–10 as the agentic coverage partition *(highlighted)*
When recon flags an agentic target, require the coverage ledger to resolve each of the 10 ASI classes
to a terminal state (`found` / `dismissed(rationale)` / `n-a(reason)`). A partition is not an answer
key — a codebase with no inter-agent messaging legitimately marks ASI07 `n-a`; the eval passes on
*resolution*, not *presence*. Adopt this over ASTRIDE/ATFAA (which are subsets of it). Cross-reference
findings to MITRE ATLAS technique IDs (AML.T0051/T0054 + the Oct-2025 agentic additions).
**maps_to:** eval. **depends_on:** T4. **Risk:** low (see verification note).

### T3-05 — `temporal_class` lifecycle tag + non-runtime-coverage eval *(highlighted — LASM's one extraction)*
Add an enum tag `temporal_class ∈ {design, build, deploy, runtime, decommission}` to each finding
(lifecycle-native naming, cleaner than LASM's session-gap semantics which only fit stateful agents).
Reference-free eval: every *applicable* temporal class is resolved (≥1 finding or an examined-clean /
n-a marker with evidence) — it checks the class was *considered*, never that a specific threat exists.
Directly fixes the static-snapshot blind spot; a Phase-5 prompt paragraph on slow-burn/cumulative
threats accompanies it. **maps_to:** framework. **depends_on:** T4. **Risk:** low.

### T3-06 — LINDDUN-GenAI lens set for the privacy-agent *(highlighted)*
Fold the 6 CAMs + fabricated-PII (DD.3.5) + embedding/vector-store reversibility (DD.1.3) + the
decision-manipulation subtree into the privacy-agent's LINDDUN reasoning guidance as GenAI-tagged
lenses. Optional reference-free privacy-coverage eval gated on `has_personal_data && has_ai_ml`
(each applicable GenAI privacy class resolved to a terminal state). Optional DFD overlay marking data
stores holding PII in vector/embedding or persistent-memory form. **Gate** training-context threats
behind `trains_or_finetunes_model`; keep AI-Act compliance as a soft "flag for review" nudge only.
**maps_to:** framework. **depends_on:** T4, T2. **Risk:** low.

### T3-07 — Coverage-as-ratio with discoverable denominators *(highlighted — the ACSE inversion, T4-facing)*
ACSE-Eval's coverage metrics are `found / golden` (reference-based, unusable). Re-base the denominator
on **recon.json**: e.g. `cloud-services-threat-tagged / cloud-services-in-recon`, and
`CWEs-found / CWEs-mappable-to-sinks-actually-present`. These become reference-free coverage ratios —
"did we threat-model every service/sink we discovered?" — never `found / answer-key`. Effort is higher
(the discoverable denominator must be derived from recon facts, not enumerated by hand). **maps_to:**
eval. **depends_on:** T4. **Risk:** med (denominator derivation must not smuggle in an implicit
expected set).

### T3-08 — Berkeley survey R1–R7 + 7 design dimensions
Inject R1–R7 as the AI/agentic reasoning scaffold in the AI/ML-supplement persona; map the 7 design
dimensions (Input Trust, Workflow, Access Sensitivity, Action, Tool, Memory, UI) to code-observable
recon signals that set the `has_ai_ml` / `agentic` gate (a boolean over emitted facts, not a
judgment). This is what fires T3-04's agentic coverage eval. **maps_to:** framework. **depends_on:**
T5 (recon-flag plumbing). **Risk:** low.

### T3-09 — ACSE per-threat schema + multi-framework tagging well-formedness
Align findings.json with ACSE-Eval's established per-threat schema and require every finding to carry
≥1 STRIDE-LM + ≥1 framework tag (OWASP/ATLAS/ATT&CK) + optional CWE. Well-formedness eval: no untagged
finding. Forces breadth and enables the coverage ratios. **maps_to:** eval. **depends_on:** T4.
**Risk:** low.

### T3-10 — MITRE ATLAS + OWASP LLM Top 10 as reference taxonomies
Add ATLAS and OWASP-LLM-Top-10 as prompt reference lists (exactly like the current ATT&CK/CWE/LINDDUN
tables in `frameworks.md`), with the CCT/AdvT/ConT overlay framing keyed to boundary-crossing edges.
Extends coverage to AI/LLM/adversarial-ML surfaces. Pure taxonomy — no determinism risk. **maps_to:**
framework. **depends_on:** none. **Risk:** low.

### T3-11 — Goal-driven security-objectives pipeline step
Add a light "system goals / security objectives" step (what must NOT happen) feeding Impact scoring,
so impact is anchored on objectives and shared attack paths dedupe under a common goal node.
Complements — does not replace — component-centric STRIDE. **maps_to:** pipeline. **depends_on:**
none. **Risk:** low.

### T3-12 — Shostack's 4 Questions persona framing
Frame the pipeline's persona prompts around the 4 Questions (Q1→DFD, Q2→STRIDE/findings,
Q3→mitigations, Q4→our eval layer). Near-zero cost, reinforces existing stages. **maps_to:**
framework. **depends_on:** none. **Risk:** low.

### T3-13 — Agent-trust / tool-permission DFD overlay
For agentic targets, an overlay showing which agent may invoke which tool and the delegation edges,
with structural checks (every agent node has ≥1 permission edge; every tool edge crosses a labeled
trust boundary). **maps_to:** artifact. **depends_on:** T2. **Risk:** low.

---

## Determinism-boundary compliance (applies to every recommendation)

Agents do all reasoning and generation. Every eval above verifies a **property over emitted facts**:
- **Coverage partitions** (T3-02/04/05/06/09) check *each applicable cell is resolved*, never which
  threat is correct. A partition/taxonomy is a reasoning prompt, not an answer key.
- **Ratios** (T3-07) use denominators derived from recon.json (discoverable facts), never a golden set.
- **Formula/structure checks** (T3-01/03) recompute arithmetic over the agent's own stated inputs.
- **Taxonomies & personas** (T3-08/10/11/12) enter as prompt guidance, exactly like the existing
  ATT&CK/CWE/LINDDUN reference tables.

Nothing here scripts the answer; each item constrains *form/coverage/consistency* only.

---

## Verification note (skeptic pass)

- **CVSS v3.1 exploitability (T3-01/03): CONFIRMED.** A dedicated skeptic verified against the
  FIRST.org v3.1 spec: the `8.22 × AV × AC × PR × UI` formula, all metric weights, and the max
  exploitability `8.22 × 0.85 × 0.77 × 0.85 × 0.85 = 3.887043 ≈ 3.887` (recomputed directly). v4.0's
  move to a MacroVector lookup table (dropping the closed form) is confirmed — so v3.1 is the right
  eval target.
- **OWASP ASI01–10 (T3-04): PARTIALLY-CONFIRMED — real document, authentic ID scheme, three title
  corrections.** It is a genuine OWASP GenAI Security Project deliverable (published 9 Dec 2025), not a
  blog fabrication, and the `ASI01–ASI10` scheme is authentic. Three official titles differ from the
  seed corpus wording: **ASI03 = "Identity & Privilege Abuse"** (no "Agent" prefix), **ASI04 = "Agentic
  Supply Chain Vulnerabilities"** (not "…Compromise"), **ASI08 = "Cascading Failures"** (not "Cascading
  Agent *Failures*"). Lock the verified strings above. The eval keys on the partition, not the prose, so
  the design is unaffected — but ship the official labels.

---

## Open questions (for L0 / other tracks)

1. **Sibling IDs.** `depends_on` uses track tokens (T2/T4/T5) because sibling internal IDs aren't known
   at authoring time. L0 should rewire to concrete item IDs — chiefly: T3-01/07/09 → the T4 eval that
   runs CVSS formula-check + coverage ratios; T3-02/03/06/13 → the T2 render work for the new
   matrices/overlays/defense-nodes; T3-05/06/08 → the finding-schema + recon-flag changes T4/T5 own.
2. **Agentic-target detector.** T3-04/08/13 all gate on "is this an LLM agent stack?" — the survey's 7
   design dimensions give code-observable signals, but who owns the detector (recon persona vs a new
   pipeline step)? T5 question.
3. **arXiv-id reconfirmation.** Several 2026 primary sources (esp. the LASM survey and the robotics /
   attack-defense / privacy papers) carry arXiv ids that should be reconfirmed against the live listing
   before they're cited in shipped docs. The *recommendations* stand on the underlying methods
   (CVSS, ADTrees, STRIDE-per-interaction, OWASP/ATLAS, lifecycle temporality), all of which have
   independent canonical anchors — so no recommendation depends on a single 2026 preprint being exactly
   as numbered.
4. **CVSS band mapping.** The exploitability-sub-score → 1–5 Likelihood band thresholds need tuning
   against real runs (T4), and Impact stays on the existing PASTA-derived 1–5 (CVSS impact sub-score is
   *not* adopted — only exploitability).

---

## Sources (primary)

**Benchmarks:** ACSE-Eval — https://arxiv.org/abs/2505.11565 ·
https://github.com/ACSE-Eval/acse-eval-experiments ·
https://huggingface.co/datasets/ACSE-Eval/ACSE-Eval · ThreatModeling-LLM —
https://arxiv.org/abs/2411.17058 · ThreMoLIA — https://arxiv.org/abs/2504.18369
**STRIDE:** Shostack ModSec08 —
https://shostack.org/files/papers/modsec08/Shostack-ModSec08-Experiences-Threat-Modeling-At-Microsoft.pdf ·
Shostack 4-Question — https://shostack.org/resources/threat-modeling · per-interaction replication —
https://arxiv.org/abs/2208.01524 · LLM robotic systems — https://arxiv.org/abs/2604.27267 ·
LLM-powered apps (STRIDE+DREAD) — https://arxiv.org/abs/2406.11007
**Agentic:** Berkeley survey — https://arxiv.org/abs/2603.11088 · OWASP Top 10 Agentic Apps 2026 —
https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ · ASTRIDE —
https://arxiv.org/abs/2512.04785 · Securing Agentic AI (ATFAA/SHIELD) —
https://arxiv.org/abs/2504.19956 · MITRE ATLAS — https://atlas.mitre.org
**Privacy:** LINDDUN-GenAI — https://arxiv.org/abs/2603.06051 · LINDDUN threat trees —
https://linddun.org/threat-trees/ · OWASP LLM08 vector/embedding —
https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/ · embedding inversion —
https://arxiv.org/html/2411.05034v1
**Attack-defense trees + CVSS:** Where Do LLM-based Systems Break — https://arxiv.org/abs/2603.07460 ·
Foundations of Attack–Defense Trees (Kordy et al.) —
https://satoss.uni.lu/members/barbara/papers/adt.pdf · CVSS v3.1 spec —
https://www.first.org/cvss/v3.1/specification-document · CVSS v4.0 —
https://www.first.org/cvss/v4.0/user-guide · ASTRAL — https://arxiv.org/abs/2604.05674
**Layered/temporal:** LASM survey (arXiv id to reconfirm) — https://arxiv.org/abs/2604.23338

---

```json
{
  "track": "t3-frameworks",
  "recommendations": [
    {
      "id": "T3-01",
      "title": "CVSS v3.1 exploitability as decomposed, auditable Likelihood + reference-free formula-check eval",
      "summary": "Emit a CVSS v3.1 vector (AV/AC/PR/UI) behind every Likelihood score; a ~15-line deterministic eval recomputes 8.22*AV*AC*PR*UI and asserts the agent's own stated band. Turns a subjective 1-5 into a decomposed, checkable justification and yields a genuine reference-free eval with no answer key.",
      "maps_to": "framework",
      "adoptability": 5,
      "impact": 5,
      "effort": 2,
      "risk": "low",
      "depends_on": ["T4"],
      "evidence": "Confirmed CVSS v3.1 closed-form formula + fixed weights from FIRST.org spec; skeptic re-ran arithmetic (max exploitability ~3.887). Determinism boundary holds: agent picks metric values (no ground truth), eval checks only arithmetic/band consistency. v4.0 dropped the closed form (MacroVector table) so v3.1 is the better eval target.",
      "sources": ["https://www.first.org/cvss/v3.1/specification-document", "https://arxiv.org/abs/2603.07460", "https://www.first.org/cvss/v4.0/user-guide"]
    },
    {
      "id": "T3-02",
      "title": "STRIDE-per-interaction: boundary-scoped per-edge coverage matrix",
      "summary": "Add a per-edge STRIDE-LM coverage matrix (rows = trust-boundary-crossing DFD edges, cols = 7 STRIDE-LM, cells = TM-NNN/n-a/clean) alongside the existing per-element matrix. Scope to boundary edges only to avoid combinatorial blowup; eval verifies every boundary edge has a decided row.",
      "maps_to": "artifact",
      "adoptability": 5,
      "impact": 4,
      "effort": 3,
      "risk": "low",
      "depends_on": ["T2", "T4"],
      "evidence": "STRIDE-per-interaction is the Microsoft TMT-2016 default (Shostack); a replicated controlled experiment (arXiv 2208.01524) found NO significant accuracy gain over per-element, so value = a verifiable per-edge coverage property, not accuracy. Robotics paper (2604.27267) supplies the boundary-scoping discipline (analyze crossings, not all edges). Same property-check class as the existing element matrix.",
      "sources": ["https://arxiv.org/abs/2208.01524", "https://arxiv.org/abs/2604.27267", "https://shostack.org/resources/threat-modeling"]
    },
    {
      "id": "T3-03",
      "title": "Attack-defense-tree nodes with metric-transform semantics",
      "summary": "Extend existing attack trees with :::defense nodes carrying control_ref (resolves in recon) + metric_transform (a legal CVSS metric change, e.g. MFA moves PR:N->H). Reveals chokepoint controls that break multiple kill chains; three reference-free structure/arithmetic checks.",
      "maps_to": "artifact",
      "adoptability": 4,
      "impact": 4,
      "effort": 2,
      "risk": "low",
      "depends_on": ["T2", "T3-01"],
      "evidence": "ADTree formalism (Kordy et al., FAST 2010) is semantic with no fixed notation, so rendered as styled Mermaid nodes. 'Where Do LLM Systems Break' (2603.07460) uses defense nodes that transform leaf CVSS metrics + OR/AND/SAND max/min propagation. Checks (control_ref resolves, transform legal, recomputed exploitability matches) are pure structure/arithmetic - reference-free. Adds a chokepoint view a flat control inventory can't give.",
      "sources": ["https://satoss.uni.lu/members/barbara/papers/adt.pdf", "https://arxiv.org/abs/2603.07460"]
    },
    {
      "id": "T3-04",
      "title": "OWASP Top 10 for Agentic Applications (ASI01-10) as the agentic coverage partition",
      "summary": "When recon flags an agentic target, require the coverage ledger to resolve each of the 10 ASI classes to a terminal state (found/dismissed/n-a). A partition is not an answer key - eval passes on resolution, not presence. Anchor on OWASP ASI (peer-reviewed, subsumes ASTRIDE/ATFAA) + MITRE ATLAS technique IDs.",
      "maps_to": "eval",
      "adoptability": 5,
      "impact": 4,
      "effort": 2,
      "risk": "low",
      "depends_on": ["T4"],
      "evidence": "Skeptic verified the OWASP Top 10 for Agentic Applications 2026 is a REAL OWASP GenAI deliverable (9 Dec 2025) with an authentic ASI01-10 scheme; three official titles corrected (ASI03 'Identity & Privilege Abuse', ASI04 'Agentic Supply Chain Vulnerabilities', ASI08 'Cascading Failures'). Berkeley/USENIX-Sec-2026 survey (2603.11088) R1-R7 + OWASP Agentic Top-10 are the canonical anchors; mapping proof shows ASTRIDE's 'A' and ATFAA's T1-T9 are strict subsets. Same coverage-ledger pattern as existing coverage.json. Adversarial: ASTRIDE VLM/diagram-OCR pipeline killed (we own structured DFD facts); SHIELD killed (prescribes controls, we find threats). Eval keys on the partition, not prose.",
      "sources": ["https://arxiv.org/abs/2603.11088", "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/", "https://atlas.mitre.org"]
    },
    {
      "id": "T3-05",
      "title": "temporal_class lifecycle tag on findings + non-runtime-coverage eval",
      "summary": "Add enum temporal_class in {design,build,deploy,runtime,decommission} to each finding. Reference-free eval checks every applicable lifecycle class is resolved (finding or examined-clean/n-a with evidence) - i.e. did the model consider non-runtime threats. Fixes the static-snapshot blind spot; the single high-value extraction from LASM.",
      "maps_to": "framework",
      "adoptability": 5,
      "impact": 4,
      "effort": 2,
      "risk": "low",
      "depends_on": ["T4"],
      "evidence": "LASM survey's temporality axis is its genuine contribution (severity concentrates in slow-burn/cumulative threats a type-centric taxonomy can't express). Lifecycle naming chosen over LASM's session-gap semantics (which only fit stateful agents) for codebase-agnostic applicability. The full 7x4 matrix was KILLED (agent-specific layers, over-fragments small systems, redundant with the 225-item taxonomy). Concept is well-grounded independent of the specific preprint id.",
      "sources": ["https://arxiv.org/abs/2604.23338"]
    },
    {
      "id": "T3-06",
      "title": "LINDDUN-GenAI lens set for the privacy-agent",
      "summary": "Fold the 6 Common Attacker Models + fabricated-PII (DD.3.5) + embedding/vector-store reversibility (DD.1.3) + decision-manipulation into the privacy-agent's LINDDUN guidance as GenAI-tagged lenses. Optional privacy-coverage eval gated on has_personal_data && has_ai_ml; optional PII/vector-store DFD overlay. Gate training-context threats.",
      "maps_to": "framework",
      "adoptability": 4,
      "impact": 4,
      "effort": 2,
      "risk": "low",
      "depends_on": ["T4", "T2"],
      "evidence": "LINDDUN-GenAI (2603.06051) extends only 3 of 7 LINDDUN categories; ~30% genuinely new (fabricated PII, CAM data-flow framing, manipulation). Corroborated by OWASP LLM08 (vector/embedding) + embedding-inversion research (2411.05034). Adversarial: importing the 100 examples killed (padding); training-context threats (CAM3, gradient leakage, membership inference) gated behind trains_or_finetunes_model; cross-session memory linkability is classic LINDDUN Linkability (zero novelty); AI-Act compliance downgraded to a soft flag (unverifiable reference-free).",
      "sources": ["https://arxiv.org/abs/2603.06051", "https://genai.owasp.org/llmrisk/llm082025-vector-and-embedding-weaknesses/", "https://arxiv.org/html/2411.05034v1"]
    },
    {
      "id": "T3-07",
      "title": "Coverage-as-ratio with discoverable denominators (the ACSE-Eval inversion)",
      "summary": "Re-base ACSE-Eval's coverage metrics from found/golden (reference-based) to found/discoverable-from-recon: e.g. cloud-services-threat-tagged / services-in-recon, and CWEs-found / CWEs-mappable-to-present-sinks. Yields reference-free coverage ratios that respect the determinism boundary.",
      "maps_to": "eval",
      "adoptability": 4,
      "impact": 4,
      "effort": 4,
      "risk": "med",
      "depends_on": ["T4"],
      "evidence": "Confirmed from ACSE-Eval scorer.py that TFC/CWE-coverage/AWS-service-coverage are all found/golden recall (reference-based, unusable as deterministic evals). The inversion (denominator from recon.json discoverable facts) is what converts recall into a reference-free coverage ratio. Risk med: the discoverable denominator must be derived from recon facts and must not smuggle in an implicit expected set.",
      "sources": ["https://arxiv.org/abs/2505.11565", "https://github.com/ACSE-Eval/acse-eval-experiments"]
    },
    {
      "id": "T3-08",
      "title": "Berkeley survey R1-R7 risk scaffold + 7 design dimensions as recon flags",
      "summary": "Inject R1-R7 (adds Resource-Drain/DoS, Unsafe-Data-Flow) as the AI/agentic reasoning scaffold; map the 7 design dimensions (Input Trust, Workflow, Access Sensitivity, Action, Tool, Memory, UI) to code-observable recon signals that set the has_ai_ml/agentic gate firing T3-04's coverage eval.",
      "maps_to": "framework",
      "adoptability": 5,
      "impact": 4,
      "effort": 3,
      "risk": "low",
      "depends_on": ["T5"],
      "evidence": "Berkeley/USENIX-Sec-2026 survey (2603.11088) is the strongest, most code-groundable agentic taxonomy; design dimensions each map to an observable code property (tool registry? persistent memory? external-data ingestion? code-exec sandbox? multi-agent messaging?). Recon flags are booleans over emitted facts, not judgments - determinism preserved.",
      "sources": ["https://arxiv.org/abs/2603.11088"]
    },
    {
      "id": "T3-09",
      "title": "ACSE per-threat schema alignment + multi-framework tagging well-formedness eval",
      "summary": "Align findings.json with ACSE-Eval's per-threat schema and require every finding to carry >=1 STRIDE-LM + >=1 framework tag (OWASP/ATLAS/ATT&CK) + optional CWE. Well-formedness eval: no untagged finding. Forces breadth and enables the coverage ratios.",
      "maps_to": "eval",
      "adoptability": 4,
      "impact": 3,
      "effort": 2,
      "risk": "low",
      "depends_on": ["T4"],
      "evidence": "ACSE-Eval's per-threat JSON schema (STRIDE+OWASP+MITRE+CWE+affected-components+C/I/A+likelihood+recommendations) is an established public schema; adopting it is the highest-value transferable asset from the benchmark cluster (the metrics themselves are all reference-based and killed). Tagging discipline is a pure property check.",
      "sources": ["https://arxiv.org/abs/2505.11565", "https://huggingface.co/datasets/ACSE-Eval/ACSE-Eval"]
    },
    {
      "id": "T3-10",
      "title": "MITRE ATLAS + OWASP LLM Top 10 reference taxonomies (CCT/AdvT/ConT overlays)",
      "summary": "Add ATLAS and OWASP-LLM-Top-10 as prompt reference lists (like the existing ATT&CK/CWE/LINDDUN tables), with the CCT/AdvT/ConT framing keyed to boundary-crossing edges. Extends coverage to AI/LLM/adversarial-ML surfaces STRIDE/CWE miss. Pure taxonomy, no determinism risk.",
      "maps_to": "framework",
      "adoptability": 5,
      "impact": 3,
      "effort": 2,
      "risk": "low",
      "depends_on": [],
      "evidence": "The robotics paper (2604.27267) layers Conventional/Adversarial/Conversational threat classes (ATT&CK/ATLAS/OWASP-LLM) per boundary crossing; ThreMoLIA (2504.18369) supplies the OWASP-LLM x ATLAS mapping table. Enters as prompt reference lists exactly like current frameworks.md tables - guidance, not answer keys.",
      "sources": ["https://arxiv.org/abs/2604.27267", "https://arxiv.org/abs/2504.18369", "https://atlas.mitre.org"]
    },
    {
      "id": "T3-11",
      "title": "Goal-driven security-objectives pipeline step feeding Impact",
      "summary": "Add a light 'system goals / security objectives' step (what must NOT happen) that anchors Impact scoring on objectives and dedupes shared attack paths under a common goal node. Complements, not replaces, component-centric STRIDE.",
      "maps_to": "pipeline",
      "adoptability": 4,
      "impact": 3,
      "effort": 2,
      "risk": "low",
      "depends_on": [],
      "evidence": "'Where Do LLM-based Systems Break' (2603.07460) anchors each attack-defense tree on a security objective and attaches impact only at the goal node, so subtrees reuse across goals. Agent-authored objectives (reference-free); maps onto the existing PASTA-derived Impact axis.",
      "sources": ["https://arxiv.org/abs/2603.07460"]
    },
    {
      "id": "T3-12",
      "title": "Shostack's 4 Questions persona framing",
      "summary": "Frame persona prompts around the 4 Questions (Q1->DFD, Q2->STRIDE/findings, Q3->mitigations, Q4->the eval layer). Near-zero cost, reinforces existing pipeline stages.",
      "maps_to": "framework",
      "adoptability": 5,
      "impact": 2,
      "effort": 1,
      "risk": "low",
      "depends_on": [],
      "evidence": "Canonical Shostack Four-Question framework; Q4 ('did we do a good job?') already IS the suite's reference-free eval philosophy. Prompt framing only - no determinism impact.",
      "sources": ["https://shostack.org/resources/threat-modeling", "https://arxiv.org/abs/2406.11007"]
    },
    {
      "id": "T3-13",
      "title": "Agent-trust / tool-permission overlay on the DFD",
      "summary": "For agentic targets, an overlay showing which agent may invoke which tool and delegation edges, with structural checks (every agent node has >=1 permission edge; every tool edge crosses a labeled trust boundary).",
      "maps_to": "artifact",
      "adoptability": 4,
      "impact": 3,
      "effort": 3,
      "risk": "low",
      "depends_on": ["T2"],
      "evidence": "ATFAA trust-boundary framing + OWASP ASI03 (identity/privilege abuse) / ASI07 (inter-agent comms) motivate an agent-trust/tool-permission graph. It is an emitted artifact the deterministic layer can structurally validate without a reference (permission-edge presence, tool-edge boundary crossing).",
      "sources": ["https://arxiv.org/abs/2504.19956", "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/"]
    }
  ],
  "open_questions": [
    "depends_on uses track tokens (T2/T4/T5) because sibling internal IDs are unknown at authoring time; L0 should rewire to concrete item IDs (CVSS/coverage-ratio/schema evals -> T4; new matrices/overlays/defense-nodes -> T2; finding-schema + recon-flag changes -> T4/T5).",
    "Agentic-target detector (fires T3-04/08/13) needs an owner - the survey's 7 design dimensions give code-observable signals but who runs the detector (recon persona vs a new pipeline step)? A T5 question.",
    "Several 2026 primary-source arXiv ids (esp. the LASM survey and the robotics/attack-defense/privacy preprints) should be reconfirmed against the live listing before shipping in docs; no recommendation depends on a single preprint since each stands on a canonical anchor (CVSS/ADTrees/STRIDE-per-interaction/OWASP/ATLAS/lifecycle temporality).",
    "CVSS exploitability-sub-score -> 1-5 Likelihood band thresholds need tuning against real runs (T4); Impact stays on the existing PASTA-derived 1-5 (CVSS impact sub-score is NOT adopted, only exploitability)."
  ],
  "poc_results": null
}
```
