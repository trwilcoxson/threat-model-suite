# Anti-Hallucination & Bias Prevention Pattern Audit

Comprehensive audit of which patterns from the anti-hallucination and bias prevention taxonomy are implemented in the threat-model-suite repository. Each claim is validated against specific source files.

**Scorecard: 13 Implemented, 9 Partially Implemented, 3 Not Implemented**

---

## Table of Contents

- [Implemented Patterns (13)](#implemented-patterns-13)
- [Partially Implemented Patterns (9)](#partially-implemented-patterns-9)
- [Not Implemented Patterns (3)](#not-implemented-patterns-3)
- [Gap Analysis](#gap-analysis)

---

## Implemented Patterns (13)

### 1. Critic/Judge Agent

**Implementation:** The `validation-specialist` is a dedicated cross-agent judge with 7 validation steps: deduplication, false positive detection, severity consistency, visual completeness, framework ID verification, confidence escalation, and protocol compliance.

**Source Evidence:**
- [`validation-specialist.md:22-28`](../agents/validation-specialist.md) — Core responsibilities (7 steps)
- [`validation-specialist.md:78-98`](../agents/validation-specialist.md) — False positive detection and severity consistency checks
- [`validation-specialist.md:135-146`](../agents/validation-specialist.md) — Protocol compliance validation (9 rules)

---

### 2. Mandatory Citation

**Implementation:** The `agent-output-protocol.md` requires an Evidence field (file:line, config, architecture observation) on every finding. The code-review-agent prompt requires code-level evidence for every finding.

**Source Evidence:**
- [`agent-output-protocol.md:77-79`](../skills/threat-model/references/agent-output-protocol.md) — Finding format requires Description, Evidence, Attack Scenario fields
- [`code-review-agent.md:15`](../agents/code-review-agent.md) — "validate or invalidate architectural threat findings with code-level evidence"
- [`code-review-agent.md:83`](../agents/code-review-agent.md) — Findings "validated at code level (confirmed as real vulnerabilities with evidence)"

---

### 3. Schema Enforcement

**Implementation:** Deterministic document structure (Metadata, Summary, Findings, Observations, Assumptions, Cross-References). Agent-specific ID prefixes (TM-, CR-, PA-, GRC-, VS-). 9 validation rules checked by the validation-specialist.

**Source Evidence:**
- [`agent-output-protocol.md:25-58`](../skills/threat-model/references/agent-output-protocol.md) — Required document structure (6 mandatory sections in order)
- [`agent-output-protocol.md:60-89`](../skills/threat-model/references/agent-output-protocol.md) — Standardized finding format (9 required fields)
- [`agent-output-protocol.md:91-101`](../skills/threat-model/references/agent-output-protocol.md) — Agent-specific ID prefixes
- [`agent-output-protocol.md:162-174`](../skills/threat-model/references/agent-output-protocol.md) — 9 validation rules

---

### 4. Confidence Gating

**Implementation:** Every finding requires HIGH/MEDIUM/LOW confidence. Escalation rules: 2+ agents agree = MEDIUM, 3+ agents = HIGH. Severity-confidence mismatches are flagged.

**Source Evidence:**
- [`agent-output-protocol.md:131-139`](../skills/threat-model/references/agent-output-protocol.md) — Confidence level definitions with evidence requirements
- [`validation-specialist.md:125-133`](../agents/validation-specialist.md) — Confidence escalation rules (2+ → MEDIUM, 3+ → HIGH)
- [`validation-specialist.md:84`](../agents/validation-specialist.md) — Severity-confidence mismatches flagged for review

---

### 5. Factual Decomposition

**Implementation:** STRIDE-LM decomposes threats into 7 atomic categories per component. PASTA decomposes attack modeling into threat actor → attack path → entry point → steps → preconditions → likelihood (1-5) → impact (4 dimensions separately) → risk score.

**Source Evidence:**
- [`analysis-checklists.md:76`](../skills/threat-model/references/analysis-checklists.md) — "All seven STRIDE-LM categories assessed for every component and data flow"
- [`analysis-checklists.md:99-113`](../skills/threat-model/references/analysis-checklists.md) — Phase 4 checklist: attack path, likelihood, impact across 4 dimensions, OWASP calculation
- [`SKILL.md`](../skills/threat-model/SKILL.md) — Business impact across financial, operational, reputational, regulatory dimensions

---

### 6. Blackboard/Shared Context

**Implementation:** 8-phase file-based pipeline (`01-reconnaissance.md` through `08-threat-model-report.md`). Each agent reads prior outputs from `{output_dir}/`. Agents instructed to "re-establish context" from files.

**Source Evidence:**
- [`SKILL.md`](../skills/threat-model/SKILL.md) — Parent conversation orchestrates all agents as flat peers via shared output directory
- [`SKILL.md`](../skills/threat-model/SKILL.md) — Spawn parameter templates specifying which files each agent reads/writes
- [`SKILL.md`](../skills/threat-model/SKILL.md) — "Read back 01-reconnaissance.md and 02-structural-diagram.md from {output_dir}/ to re-establish context"

---

### 7. Provenance Tracking

**Implementation:** Agent-prefixed IDs (TM-, CR-, PA-, GRC-, VS-). Merged findings preserve originals: "Originally: TM-004, CR-007, PA-003". Execution logs document files read/written. Cross-references link findings to diagram nodes.

**Source Evidence:**
- [`agent-output-protocol.md:91-101`](../skills/threat-model/references/agent-output-protocol.md) — Agent-specific prefixes and example IDs
- [`agent-output-protocol.md:141-149`](../skills/threat-model/references/agent-output-protocol.md) — Cross-reference requirements (diagram refs, related findings, framework IDs)
- [`validation-specialist.md:72-73`](../agents/validation-specialist.md) — Merged findings preserve all original IDs as cross-references

---

### 8. Persona Diversification

**Implementation:** 5 specialist agents with distinct analytical lenses: security-architect (STRIDE-LM/attacker mindset), privacy-agent (LINDDUN/regulator perspective), grc-agent (compliance/auditor lens), code-review-agent (CVSS/code-level), diagram-specialist (visual/structural). Within the security-architect, Phase 5 adopts an "expansive adversarial mindset" vs Phase 6's "skeptical evidence-based" approach.

**Source Evidence:**
- [`SKILL.md`](../skills/threat-model/SKILL.md) — Phase 5: "Switch to an **expansive, adversarial mindset**"
- [`SKILL.md`](../skills/threat-model/SKILL.md) — Phase 6: "Switch to a **skeptical, evidence-based mindset**"

---

### 9. Structured Elicitation

**Implementation:** Analysis is forced through structured frameworks: STRIDE-LM (7 categories), PASTA (7 stages), LINDDUN (7 privacy categories), OWASP Risk Rating. Completeness checklists enforce that no category is skipped.

**Source Evidence:**
- [`analysis-checklists.md:76-77`](../skills/threat-model/references/analysis-checklists.md) — "All seven STRIDE-LM categories assessed for every component and data flow"
- [`analysis-checklists.md:99-113`](../skills/threat-model/references/analysis-checklists.md) — Phase 4 checklist with 13 mandatory items

---

### 10. Explanation Extraction

**Implementation:** Every finding requires: Description, Evidence, Attack Scenario (step-by-step), Existing Mitigations, Recommendation. Phase 4 requires "written justification" for every likelihood and impact score.

**Source Evidence:**
- [`agent-output-protocol.md:77-88`](../skills/threat-model/references/agent-output-protocol.md) — Finding format: Description, Evidence, Attack Scenario, Existing Mitigations, Recommendation
- [`analysis-checklists.md:105-106`](../skills/threat-model/references/analysis-checklists.md) — "Likelihood scored 1-5 for each threat with written justification"
- [`analysis-checklists.md:109`](../skills/threat-model/references/analysis-checklists.md) — "Impact scored 1-5 for each threat (highest dimension) with written justification"

---

### 11. Uncertainty Propagation

**Implementation:** Confidence levels (HIGH/MEDIUM/LOW) on every finding. Likelihood/impact scored 1-5. The risk-rating matrix produces severity bands (CRITICAL 17-25, HIGH 10-16, MEDIUM 5-9, LOW 1-4) — bands rather than point estimates.

**Source Evidence:**
- [`agent-output-protocol.md:107-130`](../skills/threat-model/references/agent-output-protocol.md) — Severity definitions with score ranges for OWASP, CVSS, and Qualitative
- [`agent-output-protocol.md:131-139`](../skills/threat-model/references/agent-output-protocol.md) — Confidence levels with evidence requirements

---

### 12. Decision Journaling

**Implementation:** The validation-specialist logs every merge decision with justification. An Execution Log section is mandatory on ALL agent outputs: process health, files read/written, issues, skips, assumptions.

**Source Evidence:**
- [`validation-specialist.md:76`](../agents/validation-specialist.md) — "Log every merge decision with justification in the deduplication section"
- [`validation-specialist.md:152-156`](../agents/validation-specialist.md) — Document finding ID, issue, evidence, recommended correction, severity for every issue

---

### 13. Counterfactual Prompting

**Implementation:** Phase 5 explicitly uses counterfactual reasoning across 10 adversarial perspectives: low-risk re-examination, kill chains, insider threat, supply chain, temporal, cross-boundary, AI-specific, data aggregation, side-channel, and cascade failures.

**Source Evidence:**
- [`SKILL.md`](../skills/threat-model/SKILL.md) — "What if this component is compromised? What blast radius does it create?"
- [`SKILL.md`](../skills/threat-model/SKILL.md) — "What happens if any upstream dependency is compromised?"
- [`SKILL.md`](../skills/threat-model/SKILL.md) — "Can an attacker reach a high-trust zone without passing through expected controls?"
- [`SKILL.md`](../skills/threat-model/SKILL.md) — "If component A fails, what happens to B, C, D?"

---

### 26. Dashboard Grounding & Cross-Output Consistency

**Implementation:** The opt-in `dashboard.html` is derived entirely from the run's canonical manifests, and a reference-free eval reconciles it back to them. Every headline number must recount `recon.json`/`findings.json`/`coverage.json` (grounding); no diagram node/edge/finding-id may appear that isn't real (non-fabrication); the **embedded structural diagram is the run's own diagram, not a substitute** — its edges must be a subset of the run's real dataflows/`structural-diagram.mmd`, never synthesized from finding co-reference (diagram consistency). Cross-output consistency requires dashboard severity == `findings.summary_counts` and coverage % from `coverage.json`. The eval is inert unless `dashboard.html` is present.

**Source Evidence:**
- [`evals/reliability/dashboard_checks.py`](../skills/threat-model/evals/reliability/dashboard_checks.py) — grounding, non-fabrication, diagram consistency, link-grounding, cross-output consistency, offline
- [`scripts/build_dashboard.py`](../skills/threat-model/scripts/build_dashboard.py) — deterministic manifests → derived model → template; embeds the run's real diagram
- [`references/dashboard_template.py`](../skills/threat-model/references/dashboard_template.py) — inline CSS/JS, no CDN/fonts; graceful empty states for absent fields

---

### 27. Run-Plan Match (Planned == Produced, Both Directions)

**Implementation:** The confirmed Step-0 run selection (`run-plan.json`, `run-plan/v1`) is treated as a contract, and a reference-free eval verifies the run produced EXACTLY the planned team + outputs — a MISSING planned artifact AND an EXTRA un-planned one are both defects. Two stages: `gate` (skips planned-but-not-yet-generated outputs to avoid deadlock at the report gate) and `post` (full). The plan is additionally enforced up front by a hard START gate (`hooks/validate_gate.py`) that denies the first pipeline spawn until the plan exists, validates, and is `confirmed`. Inert without `run-plan.json`.

**Source Evidence:**
- [`evals/reliability/run_plan_checks.py`](../skills/threat-model/evals/reliability/run_plan_checks.py) — planned team + outputs == produced, both directions; `gate`/`post` stages
- [`evals/reliability/schema/run-plan.schema.json`](../skills/threat-model/evals/reliability/schema/run-plan.schema.json) — `run-plan/v1` schema (`team` == `[]` when `mode="solo"`); registered in `schema_checks.py`
- [`hooks/validate_gate.py`](../hooks/validate_gate.py) — `PreToolUse` START gate scoped to the recon spawn; fail-open on infra errors

---

## Partially Implemented Patterns (9)

### 14. Anchor Stripping

| Aspect | Status |
|--------|--------|
| **What exists** | Fresh context windows per agent prevent carry-forward of intermediate reasoning. Agents re-read only authoritative prior outputs from files. |
| **What's missing** | No explicit stripping of confidence language or ordering effects. "Re-establish context" restores prior outputs but doesn't debias them. Downstream agents can see upstream severity/confidence ratings. |

**Source:** [`SKILL.md`](../skills/threat-model/SKILL.md) — "re-establish context" instruction

---

### 15. Round-trip Verification

| Aspect | Status |
|--------|--------|
| **What exists** | False positive detection checks attack paths against Phase 1 controls inventory. |
| **What's missing** | No explicit reconstruction of inputs from outputs (cycle-consistency pattern). |

**Source:** [`validation-specialist.md:80-86`](../agents/validation-specialist.md) — False positive verification against Phase 1 controls

---

### 16. Debate/Adversarial

| Aspect | Status |
|--------|--------|
| **What exists** | Phase 5 adopts "expansive adversarial mindset"; Phase 6 is "skeptical evidence-based." Bidirectional 5→6→re-check loop prevents false negatives from slipping through. |
| **What's missing** | No separate red-team agent entity arguing opposing positions across agents. The debate is intrapersonal (within one agent's phases), not interpersonal. |

**Source:** [`SKILL.md`](../skills/threat-model/SKILL.md) — Phase 5 adversarial, Phase 6 skeptical, bidirectional re-check loop

---

### 17. Chain-of-Verification (CoVe)

| Aspect | Status |
|--------|--------|
| **What exists** | Phase 6 validates Phase 3-5 findings systematically. Verification criteria: realistic attack path, existing mitigations, context validation, confidence assignment. |
| **What's missing** | No structured self-questioning pattern (generate questions about own answers, answer independently, revise). Verification is applied to findings, not to the reasoning chain. |

**Source:** [`SKILL.md`](../skills/threat-model/SKILL.md) — Phase 6 validation criteria

---

### 18. Tool-use as Grounding

| Aspect | Status |
|--------|--------|
| **What exists** | Phase 1 explicitly uses Glob/Grep for code scanning (entry points, auth, config, IaC). All agents have Bash/Read/Grep/Glob tool access. |
| **What's missing** | Tool use not mandated for all claims — agents can reason architecturally without tool verification for each assertion. |

**Source:** [`SKILL.md`](../skills/threat-model/SKILL.md) — Phase 1 code scanning with Glob and Grep

---

### 19. Red-team Agent

| Aspect | Status |
|--------|--------|
| **What exists** | Phase 5 is a formal red-team phase with 10 adversarial perspectives (insider, supply chain, cascade failures, temporal, AI-specific, data aggregation, side-channel). Includes kill chain tracing and attack tree diagrams. |
| **What's missing** | Adversarialism is within a single agent's Phase 5, not a separate dedicated red-team agent entity. |

**Source:** [`SKILL.md`](../skills/threat-model/SKILL.md) — Phase 5 with 10 adversarial perspectives

---

### 20. Human-in-the-Loop

| Aspect | Status |
|--------|--------|
| **What exists** | False positive candidates flagged for "responsible agent's confirmation." Final report delivered to user for review. |
| **What's missing** | No explicit "pause and wait for human approval" gates during analysis phases. The pipeline is fully autonomous once triggered. |

**Source:** [`validation-specialist.md:87`](../agents/validation-specialist.md) — "Flag them for the responsible agent's confirmation"

---

### 21. Retrieval/Reasoning Separation

| Aspect | Status |
|--------|--------|
| **What exists** | The diagram-specialist reads outputs but doesn't reason about threats. Phase 1 (reconnaissance) is conceptually distinct from Phases 3-6 (analysis). |
| **What's missing** | The same agent (security-architect) handles both Phase 1 retrieval and Phases 3-6 reasoning. No structural separation between retrieval and reasoning agents. |

**Source:** [`SKILL.md`](../skills/threat-model/SKILL.md) — Phase 1 reconnaissance (retrieval); [`SKILL.md`](../skills/threat-model/SKILL.md) — Phases 3-6 (reasoning)

---

### 25. Calibration Testing

_Reclassified from "Not Implemented": the reference-free reliability harness now provides recall/precision-like signal without an answer key._

| Aspect | Status |
|--------|--------|
| **What exists** | A reference-free reliability harness (`../skills/threat-model/evals/reliability/`) runs the pipeline across 3 committed targets (NodeGoat, crAPI, TerraGoat) and measures recall/precision-like signal *without an answer key*: an independent adversarial recall probe (real issues an independent pass surfaced that a run may have missed), a recon-audit (surface-element coverage), stability clustering across repeated runs (do findings reproduce), and an LLM quality judge (are findings grounded and proportionate). |
| **What's missing** | No absolute recall/precision against a ground-truth vulnerability set — **by design**. The suite's stated philosophy is reference-free / no-answer-key (see [`../openspec/README.md`](../openspec/README.md)): deterministic code checks structure and consistency, never scripts or judges the answer. Answer-key "planted vulnerability" calibration would conflict with that philosophy. |

**Source:** [`evals/reliability/`](../skills/threat-model/evals/reliability/) — `run.py`, `checks.py` (recall), `stability.py`, `report.py`; `sample-runs/` (nodegoat, crapi, terragoat) with committed `recall.json`, `recon-audit.json`, `stability-clusters.json`, `quality.json`

---

## Not Implemented Patterns (3)

### 22. Closed-book vs Open-book

**Why it matters:** Prevents retrieval bias from contaminating reasoning. When the same agent retrieves evidence and reasons about it, confirmation bias can cause selective evidence gathering.

**Potential addition:** Separate the recon agent from the analysis agent so that analysis only sees the structured reconnaissance output, not raw codebase access.

---

### 23. Model Diversity

**Why it matters:** Correlated failures — the same model tends to agree with its own hallucinations. All agents currently use `opus`.

**Potential addition:** Use a different model for the validation-specialist (e.g., Sonnet for generation agents, Opus for validation). This creates an independent check that doesn't share the same failure modes.

---

### 24. Temperature Management

**Why it matters:** Lower temperature for verification produces more conservative outputs; higher temperature for brainstorming produces more creative threat discovery.

**Potential addition:** Add temperature configuration to agent YAML frontmatter. Use lower temperature for Phase 6 (validation) and the validation-specialist; higher for Phase 5 (false negative hunting).

---

## Gap Analysis

### Coverage Summary

| Category | Count | Percentage |
|----------|-------|-----------|
| Fully Implemented | 13 | 52% |
| Partially Implemented | 9 | 36% |
| Not Implemented | 3 | 12% |
| **Total Patterns** | **25** | **100%** |

### Highest-Impact Gaps

1. **Model Diversity (#23)** — Easiest to implement (change `model:` in validation-specialist frontmatter). Highest ROI because it addresses correlated hallucination, where the same model validates its own outputs.

2. **Temperature Management (#24)** — Moderate implementation effort (requires Claude Code to support temperature in agent frontmatter). Would improve both creativity in Phase 5 and rigor in Phase 6/validation.

3. **Closed-book vs Open-book (#22)** — Requires architectural change (splitting security-architect into recon-agent and analysis-agent). Highest effort but addresses a fundamental bias vector.

### Patterns That Could Be Upgraded from Partial to Full

| Pattern | Current Gap | Upgrade Path |
|---------|------------|-------------|
| Debate/Adversarial (#16) | Intrapersonal only | Add a dedicated `red-team-agent` that reviews Phase 3-4 findings independently |
| Human-in-the-Loop (#20) | No pause gates | Add optional approval checkpoints between phases (user-configurable) |
| Tool-use as Grounding (#18) | Not mandated for all claims | Add checklist item: "Every CRITICAL/HIGH finding verified with tool evidence" |
| Calibration Testing (#25) | Reference-free signal only | Add a periodic live-run cadence across the committed targets and track the reliability signals over time |
