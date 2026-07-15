## Context

This change lands recommendations **T2-01** (ATLAS Navigator layer), **T2-05** (OWASP-LLM Top-10
checklist), **T3-10** (ATLAS + OWASP-LLM as reference taxonomies), **T4-03** (ATLAS-layer grounding
eval), and **T4-07** (controlled-vocabulary id check). All five were unanimous "keep" items across the
T2/T3/T4 research with low determinism risk, because their novel content is **grounding/coverage-shaped**,
not correctness-shaped — the property the whole suite is built to check reference-free.

The machinery is almost entirely already present: the Navigator JSON emitter and the STRIDE-matrix table
renderer (`add-product-grade-diagrams`), the `has_ai_ml` applicability flag (`add-coverage-ledger`), and
the `no-attack-layer` / `malformed-mitre` reference-free checks (`harden-eval-determinism-boundary`). The
design is deliberately a **reuse-and-gate** change, not a new subsystem.

The flagship as-code engine decision (D2 as flagship, Mermaid `@{shape: icon}` + ELK as the phase-1
legibility win) is **settled and not touched here** — an ATLAS Navigator layer is Navigator JSON, not a
rendered diagram, so it is independent of the diagram engine. The OWASP-LLM checklist is a markdown table,
also engine-independent. This change can land before or after the engine work with no ordering
constraint.

## The determinism boundary (how every new check stays reference-free)

Agents do all reasoning and generation; the deterministic layer checks **structure / grounding /
consistency over the model's own emitted facts**, never against an answer key, and every check allows
honest abstention. Each new element preserves that boundary as follows:

1. **ATLAS layer emission** — gated on the **declared** `coverage.context.has_ai_ml` flag (a boolean the
   skill emitted, exactly like the existing attack-tree gate on `>=3 kill_chains` — never sniffed from an
   entity string). If `has_ai_ml` is false the layer is not produced; a non-AI target is never penalized
   for its absence.

2. **`atlas[]` field** — additive and **nullable**, pattern-validated for **shape only**
   (`^AML\.T\d{4}(\.\d{3})?$`), never for presence. A finding may omit it or set it null; the schema
   still validates. This mirrors the existing nullable `mitre[]`/`cwe[]` fields exactly.

3. **ATLAS-layer grounding (T4-03)** — the technique ids shown on the layer must be a **subset of the
   distinct `atlas[]` ids across the findings** (an invented technique with no backing finding is a
   defect). This is the identical grounding rule the ATT&CK layer already enforces
   (`analytical-visuals.md` §3: "the set of technique ids shown equals the distinct `mitre` ids across the
   findings"). It checks *the layer projects the findings*, never *which technique is correct*. Abstention:
   when `has_ai_ml` is false or no finding declares an ATLAS id, the whole block is **skipped**.

4. **OWASP-LLM Top-10 checklist (T2-05)** — a **projection**, not a judgement. Each of the 10 rows is
   marked covered / `n-a` / `clean` by asking "does any finding's own `atlas[]` id fall in this OWASP-LLM
   class's crosswalk set?". The crosswalk (OWASP-LLM class → the set of ATLAS techniques that class
   corresponds to) is a **fixed grouping published by OWASP GenAI / the community**, not a statement about
   what *this* target contains. A row with no matching finding is a legitimate `n-a`/`clean`; abstention is
   first-class. Because it resolves over the model's own emitted `atlas[]` ids, the checklist adds **no new
   finding field** and stays reference-free.

5. **Controlled-vocabulary id guardrail (T4-07)** — a **well-formedness** regex, the exact shape of the
   existing `malformed-mitre` (`checks.py:207`). It validates that an emitted id *matches the fixed regex
   for its declared framework*; it never requires a *particular* id and never infers content. It is keyed
   on the **declared framework field** (the `atlas[]` field → the ATLAS regex; the OWASP-LLM checklist
   column → the OWASP-LLM regex) precisely so the `T1..T15` (OWASP-Agentic) vs `T####` (ATT&CK) lexical
   collision the T4 research flagged can never mis-fire. A malformed `AML.T99999` is flagged; a well-formed
   `AML.T0051` passes; a missing id is never flagged.

The rule the whole design obeys (T4 REPORT §5): *if a check would change its verdict based on which
finding/id/category the model chose, it is wrong.* Every check here changes its verdict only on
gate-state, id-shape (regex), or id-resolution (subset/projection) — all invariant to the model's content
choices.

## Decisions

1. **Reuse the ATT&CK Navigator emitter with `domain: "atlas-atlas"`, do not fork it.** ATLAS ships an
   ATT&CK-Navigator-compatible layer schema (`atlas-navigator-data`); the only load-bearing differences
   are the `domain` string and the `AML.` id prefix. The emitter, gradient, and legend structure are
   identical (see the shipped `ecs-fullstack-attack-navigator-layer.json`). One emitter, two domains.

2. **`domain=="atlas-atlas"` + `AML.` prefix is the discriminator; never run the ATT&CK regex over ATLAS
   ids.** The ATLAS layer is told apart from the ATT&CK layer *only* by these two signals. The
   controlled-vocab guardrail is keyed on the declared framework field for the same reason. This is the
   single most important correctness constraint in the change (T4 REPORT §C).

3. **One additive finding field, `atlas[]` — deliberately not `owasp_llm[]`.** The brief scopes exactly
   one field. The OWASP-LLM checklist is *projected* onto the ATLAS layer via the crosswalk, so it needs
   no per-finding OWASP-LLM tag: a row is "covered" when a finding's ATLAS id lands in that class's
   crosswalk set. This keeps the schema delta minimal and avoids a second AI namespace on findings. (If
   per-finding OWASP-LLM tagging is later wanted for finer granularity, `owasp_llm[]` is the additive
   follow-on — see open questions.)

4. **No second diagram for OWASP-LLM.** The T2 research is explicit: OWASP-LLM content ⊂ ATLAS, so a
   standalone OWASP-LLM diagram would duplicate the ATLAS layer. It renders as a checklist through the
   existing STRIDE-matrix table renderer (fixed 10-row enum, cells = finding id / `n-a` / `clean`).

5. **ATLAS + OWASP-LLM enter `frameworks.md` as reference tables, exactly like ATT&CK/CWE.** Pure prompt
   guidance — the agent selects from them or writes "No matching ID in reference set — manual verification
   recommended", the same escape hatch the existing Framework ID Verification rules already provide. Ship
   the **verified official OWASP strings** (the T3 skeptic corrected several titles; the crosswalk and the
   ASI/agentic distinctions are captured there). No eval requires any id from these tables to appear.

6. **Everything gates on `has_ai_ml`.** A single, already-declared boolean turns the entire feature on and
   off. This is what guarantees "non-AI targets are unaffected" is a structural property, not a promise.

## Alternatives considered

- **A standalone OWASP-LLM diagram / matrix.** Rejected (decision 4): its threat content is a subset of
  ATLAS, so it would be a second view of the same data. Projecting onto the ATLAS layer / STRIDE-matrix
  renderer is strictly cheaper and avoids cross-artifact drift.
- **A curated ATLAS id allowlist embedded in the eval (like a per-target answer key).** Rejected: that
  would make the eval infer/require content — a determinism-boundary violation. The guardrail is a *regex
  over a controlled id-shape*, not a set of expected ids; validity of a *specific* mapping stays the
  judge's job (`prompts/diagram-judge.md`).
- **A new `owasp_llm[]` finding field now.** Deferred (decision 3): out of scope for a one-field change,
  and the crosswalk projection makes it unnecessary for the checklist. Recorded as an open question.
- **Forking the Navigator emitter for ATLAS.** Rejected (decision 1): the schemas are compatible; a fork
  would duplicate the gradient/legend logic and drift.

## Risks / trade-offs

- **Crosswalk staleness.** The OWASP-LLM→ATLAS crosswalk is a fixed table in `frameworks.md`; if OWASP or
  ATLAS renumber, it needs a refresh. Mitigated by it being *guidance* — a stale crosswalk mis-groups a
  checklist row (a warning-level cosmetic issue), it never fails a run or dictates a finding. Owned by the
  same `reference-fidelity` discipline that maintains the ATT&CK/CWE tables.
- **ATLAS id churn.** MITRE ATLAS adds techniques (e.g. the 2025 agentic additions). The regex validates
  *shape* (`AML.T####`), not membership, so new real ids pass without an eval update; only the
  `frameworks.md` reference table needs periodic top-up — the same maintenance the ATT&CK table already
  has.
- **`has_ai_ml` under-declared.** If recon fails to set `has_ai_ml` on a genuine AI system, the ATLAS
  artifact is silently skipped. This is the correct failure mode for a declared-fact gate (the alternative
  — sniffing "is this AI?" from content — is the boundary violation we are avoiding), and it is backstopped
  by the existing `recon-auditor` agent, which judges recon completeness against the real repo.
- **Scope discipline.** The T3/T4 research surfaces a much larger AI/agentic program (CVSS-decomposed
  likelihood, OWASP-Agentic ASI01–10 coverage partition, LINDDUN-GenAI, LASM temporality). This change
  stays narrowly on the ATLAS + OWASP-LLM attack surface; those are separate workstreams and are not
  pulled in here.
