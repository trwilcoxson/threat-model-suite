# Privacy Specialist — Privacy Impact Assessment (PIA/DPIA)

## Metadata
| Field | Value |
|-------|-------|
| Agent | privacy-specialist |
| Date | 2026-07-11 |
| Target System | AWS ECS Fullstack App (Terraform Demo) |
| Scope | `Code/client` (Vue SPA incl. Login stub), `Code/server` (Express API, `/api/getAllProducts`, `/api/docs`), `Infrastructure/` (Terraform IaC), data stores D1–D6, entry points E1–E5 — assessed for personal-data processing |
| Methodology | LINDDUN GO privacy threat analysis; GDPR / CCPA-CPRA / HIPAA regulatory gap analysis; Privacy by Design (Cavoukian 7 principles); OWASP Risk Rating (L×I) for severity |
| Scoring System | OWASP Risk Rating (Likelihood × Impact-on-individuals) |
| Context flags (from recon) | `has_personal_data=false`, `has_regulatory=false`, `multi_tenant=false`, `has_ai_ml=false` |

## Summary
- **Total findings: 4 (0 critical, 0 high, 0 medium, 4 low).** All four are LOW in the current state because **no personal data is processed** — impact on individuals is negligible when there are no data subjects. Each finding carries an explicit **conditional severity** (MEDIUM–HIGH) that activates the moment a real deployment wires up authentication and user accounts.
- **Current privacy posture: MINIMAL RISK / OUT OF SCOPE for data-protection law.** The system processes no personal data. The DynamoDB catalog (D1) holds non-personal product reference data (`id`/`path`/`title`). The `Login.vue` credential form is an inert demo stub — verified in source: `onSubmit()` only routes to `/main` and never transmits or stores the typed username/password. The single anonymous API call (`getAllProducts`) carries no user data. No GDPR, CCPA/CPRA, or HIPAA obligation is engaged.
- **Top forward-looking risks (if auth + PII are added — the login stub signals that intent):** (1) no TLS on the public ALBs means any future personal data (or client IP, if ALB access logs are ever enabled) travels in plaintext over the Internet; (2) no transparency/consent/DSAR scaffolding exists, so the first personal-data feature ships non-compliant by default; (3) the CloudWatch log sink (D5) has no PII scrubbing or personal-data retention policy.
- **Key recommendation:** Treat this PIA as the **privacy baseline gate**. Before any personal-data or authentication feature is merged, require: TLS termination on both ALBs, a privacy notice + lawful-basis decision, a documented retention/deletion policy, and log-field minimization. None of these should be retrofitted after a real user base exists.

---

## 1. Scope and Methodology

**Systems assessed.** The full repository was reviewed for personal-data processing: the Vue 2 SPA (`Code/client`, including the `Login.vue` component and `RestServices.js` API client), the Express API (`Code/server`, routes `/status`, `/api/getAllProducts`, `/api/docs`), the Terraform IaC (`Infrastructure/`), and all six data stores (D1 DynamoDB, D2 S3 assets, D3 S3 artifacts, D4 ECR, D5 CloudWatch Logs, D6 local Terraform state) enumerated in Phase 1 reconnaissance and drawn in the Phase 2 L1/L2/L3 diagrams.

**Regulations considered.** GDPR (EU), CCPA/CPRA (California), and HIPAA (US health) were assessed for applicability, per the team lead's scope. UK GDPR and LGPD are noted where they would mirror GDPR in a real multi-jurisdiction deployment.

**Methodology.** LINDDUN GO was applied across all seven privacy-threat categories against the Phase 1–2 data inventory and data flows. Regulatory gap analysis was performed against the verified article references in the skill's `gdpr-article-reference.md` and `global-privacy-regulations.md`. Privacy by Design was assessed against the 7 foundational principles. Severity uses OWASP Risk Rating (Likelihood × Impact **on individuals**, not organizational liability), per skill guidance.

**Anti-hallucination.** Every GDPR article, non-GDPR regulation section, and LINDDUN threat type cited below was verified against the skill's reference files. No citation is drawn from memory.

**Limitations.**
- No `.tfvars` are committed, so concrete region/account values are unknown; a single region / single environment is assumed per the README (consistent with recon).
- The assessment is static (code + IaC). No running deployment was exercised, so runtime log contents were inferred from the source error handler rather than observed.
- The forward-looking ("conditional") analysis is scenario-based: it assumes the login stub is later made functional and user accounts + personal data are introduced. It is deliberately labelled as conditional and does not inflate current-state severity.

---

## 2. Data Inventory

The purpose of this inventory is to establish, element by element, that **no personal data is processed** in the current system — and to name the elements that *would become* personal data under a real deployment. Sensitivity uses the skill's 1 (Public) – 5 (Restricted) scale.

| Data Element | Category | Source | Purpose | Legal Basis | Retention | Recipients | Sensitivity | Personal Data? |
|---|---|---|---|---|---|---|---|---|
| Product catalog `id` / `path` / `title` (D1) | Product reference (non-personal) | Seeded by operator | Serve catalog to anonymous browsers | N/A — not personal data (GDPR Art. 4 not engaged) | No policy set; DynamoDB `PAY_PER_REQUEST`, no PITR | Anonymous users (R0) via C2→C5 | 1–2 (Public/Internal) | **No** |
| Product images (D2, S3) | Product reference (non-personal) | Operator upload | Display product images | N/A | No versioning/lifecycle policy | Anonymous users (R0), fetched directly from S3 | 1–2 (Public) | **No** |
| Login form `user` / `password` (Login.vue) | Would be Account/Authentication | Typed into browser | **None — inert stub** | N/A — not collected | Not stored; lives only in Vue component memory, discarded on route change | **None** — never leaves the browser (verified: no axios/fetch call) | Would be 4 (Sensitive) if activated | **No (not collected)** |
| Source IP address of requester | Would be Device/Technical | Network layer | Request routing | N/A — not persisted | **Not logged** — no ALB access logs, no VPC flow logs configured | Transiently seen by ALB (C4/C5) only | Would be 2–3 if logged | **No (not retained)** |
| CloudWatch Logs (D5) | App stdout/stderr | ECS tasks / CodeBuild | Debugging, health | N/A | 30-day retention | Operators with CloudWatch access | 1–2 (Internal); currently no PII | **No** |
| GitHub PAT (D6, Terraform state) | Operator credential (secret) | Operator | Pipeline source access | N/A — operator credential, not data-subject PII | Persists in local unencrypted state | Operator workstation | Restricted (security, not privacy) | **No (not data-subject data)** |

**Data inventory conclusion.** There is **no personal data** in the system as built. The two elements that superficially look personal — the login credentials and the client IP — are respectively (a) never collected (inert UI stub, confirmed in `Login.vue:46-49`) and (b) never logged or persisted (no ALB access logging in the Terraform). The GitHub PAT is an operator secret handled by the threat-model/compliance tracks, not a data-subject privacy concern.

**Special-category (GDPR Art. 9) and children's data (GDPR Art. 8 / COPPA):** none present. No health, biometric, financial, or demographic data of any kind.

---

## 3. Data Flow Analysis

The system has **zero personal-data flows**. For completeness, the personal-data-relevant flows that *would* exist under a real deployment are mapped against canonical Phase 2 node ids:

**Collection points (current):**
- **E1/E2 — anonymous HTTP GET** at the client ALB (C4) and server ALB (C5). No form submission carries user data. `getAllProducts` (`RestServices.js:9-11`) is a parameterless GET.
- **Login.vue** presents a credential-collection *surface* (username/password inputs) but is **not a collection point** — no notice, no consent, and no transmission. It is a visual placeholder.

**Transmission paths (current, and their latent privacy exposure):**
- `R0 → C4` and `R0 → C5`: **plaintext HTTP:80**, no TLS listener created (recon §1.8; Phase 2 L3 marks every ingress edge `[PLAIN]`). Carries only non-personal catalog data today. **This is the single most consequential latent privacy control gap** — see PA-001.
- `C2 → D1` (DynamoDB scan), `C8 → D5` (awslogs), `R0 → D2` (image fetch): ride AWS-managed TLS (`[ENC]` in Phase 2 L3). Non-personal payloads.

**Storage locations (current):** D1, D2, D3, D4, D5 all hold non-personal data under AWS-managed default encryption. D6 (local Terraform state) is plaintext-at-rest but holds only the operator PAT, not personal data.

**Third-party sharing:** none of personal data. AWS is the infrastructure processor for non-personal content; GitHub and public ECR are supply-chain, not personal-data recipients.

**Deletion lifecycle:** not applicable — there is no personal data to delete, and consequently no DSAR/erasure pathway is required today. (This becomes a gap the moment accounts exist — see PA-004.)

Because there are fewer than five personal-data flows (there are zero), no dedicated personal-data flow diagram is warranted; the Phase 2 L3 data diagram already documents the `[PLAIN]`/`[ENC]` state of every edge.

---

## 4. LINDDUN Privacy Threat Assessment

Each of the seven LINDDUN GO categories was assessed against the inventory and flows. Because no personal data is processed, most threat types are **not currently instantiated** — this is recorded honestly rather than inflated. The genuine current-state observations, plus the conditional (post-PII) exposure, are captured as findings PA-001…PA-004.

| LINDDUN Category | Applicable threat type (verified) | Current state | Conditional state (if auth + PII added) |
|---|---|---|---|
| **L — Linkability** | L1 (data items), L2 (actions), L3 (identities) | **Not instantiated** — no user identifiers exist to link; catalog rows are non-personal. | Persistent user IDs / session identifiers would enable L1/L2; shared single DynamoDB table without segregation would enable cross-context linking. |
| **I — Identifiability** | I1 (identifiers), I2 (quasi-identifiers), I3 (context) | **Not instantiated** — no direct or quasi-identifiers stored. | Account emails/usernames → I1; unlogged client IP would become I2/quasi-identifier if ALB access logs are enabled. |
| **N — Non-repudiation** | N1/N2/N3 | **Not instantiated** — no audit trail of user actions exists. | Over-detailed audit logs of user actions exposed to non-security staff → N3. Low priority even then. |
| **D — Detectability** | D1 (data), D2 (actions), D3 (identities) | **Not instantiated** — no accounts to enumerate; the anonymous API is uniform. Positively, the account-less design removes the user-enumeration surface entirely. | Auth added without care → D3 (user enumeration via differential login errors), a classic detectability flaw. Design the login response uniform from day one. |
| **D — Disclosure of Information** | D1 (access-control failure), D2 (breach), D3 (inference), D4 (surplus data) | **Latent — PA-001, PA-003.** Plaintext transport (no TLS) and a verbose error handler (`app.js` returns `{code, description: err.message}`) are disclosure vectors that carry no PII *today*. | Plaintext HTTP would expose personal data in transit (Disclosure D1/D2); error handler + CloudWatch (D5) would leak PII into logs (Disclosure D4 surplus data); broad `getAllProducts`-style responses over a user table → D4. |
| **U — Unawareness** | U1 (transparency), U2 (intervenability), U3 (user control) | **Present observation — PA-002.** No privacy notice exists anywhere, and `Login.vue` presents a credential UI with zero notice. No data is collected, so no harm — but no transparency infrastructure exists. | U1/U2/U3 all instantiate immediately: no privacy notice, no consent withdrawal, no DSAR mechanism for the new accounts. |
| **N — Non-compliance** | N1 (consent), N2 (subject rights), N3 (principles), N4 (accountability), N5 (transfers) | **Latent — PA-004.** No ROPA, no documented legal basis, no retention policy, no DSAR process. No obligation today because there is no personal data. | N1–N5 all engage: consent/legal basis (GDPR Art. 6), subject rights (Art. 12–22), minimization/storage limits (Art. 5), ROPA (Art. 30), and cross-border transfer safeguards (Art. 44/46) if EU users are served from a US region. |

### Findings

### LOW PA-001: No TLS on public ALBs — plaintext transport is a latent disclosure vector for any future personal data
| Field | Value |
|-------|-------|
| ID | PA-001 |
| Severity | LOW (current) · **conditional HIGH (10–16) if PII added** |
| Confidence | HIGH |
| Affected Component(s) | C4 (Client ALB), C5 (Server/API ALB), C2 (Server API), E1, E2 |
| Scoring System | OWASP Risk Rating |
| Score | Current L2 × I1 = 2 (LOW) · Conditional L4 × I3 = 12 (HIGH) |
| Cross-Framework | LINDDUN: Disclosure of Information — D1 (access-control failure) / D2 (breach) · GDPR Art. 32 (security of processing) · GDPR Art. 5(1)(f) (integrity and confidentiality) |

**Description**: Both ALBs create only an HTTP:80 listener; no TLS listener, ACM certificate, or HTTP→HTTPS redirect exists (`enable_https` defaults false; Phase 2 L3 marks every ingress edge `[PLAIN]`). Today this carries only non-personal catalog data, so the privacy impact is negligible. But it is the load-bearing control gap: the instant any personal data (a login credential, a profile field, or a client IP written to ALB access logs) traverses these ALBs, it is exposed in cleartext to any on-path observer on the public Internet.

**Evidence**: recon §1.8 ("only an HTTP:80 listener is created"); `RestServices.js:6` uses `http://<SERVER_ALB_URL>`; Phase 2 L3 note ("all application HTTP is `[PLAIN]`").

**Attack Scenario** (conditional, post-PII):
1. A real deployment activates the login stub and posts credentials to the API over the existing HTTP ALB.
2. An attacker on a shared/upstream network path (coffee-shop WiFi, compromised transit) passively captures the plaintext request.
3. Credentials / personal data are harvested with no exploitation of the application itself.

**Existing Mitigations**: Tasks sit in private subnets reachable only from the ALB SG; AWS-managed TLS protects the task→managed-service hops. Neither protects the Internet→ALB hop.

**Recommendation**: **Technical** — terminate TLS 1.2+ on both ALBs with an ACM certificate and force HTTP→HTTPS redirect *before* any personal-data feature ships; treat plaintext HTTP as a release blocker for auth. **Organizational** — add "TLS on all public listeners" to the privacy release gate (see PA-004). Addresses GDPR Art. 32.

---

### LOW PA-002: No transparency/notice infrastructure; login stub presents a credential UI with no privacy notice
| Field | Value |
|-------|-------|
| ID | PA-002 |
| Severity | LOW (current) · **conditional MEDIUM (5–9) if PII added** |
| Confidence | HIGH |
| Affected Component(s) | C1 (Client SPA / Login.vue) |
| Scoring System | OWASP Risk Rating |
| Score | Current L1 × I1 = 1 (LOW) · Conditional L3 × I2 = 6 (MEDIUM) |
| Cross-Framework | LINDDUN: Unawareness — U1 (lack of transparency) · GDPR Art. 13 (information at collection) · GDPR Art. 12 (transparent communication) |

**Description**: No privacy notice, cookie banner, or data-processing disclosure exists anywhere in the SPA or API. `Login.vue` renders username/password inputs that, to a reasonable user, imply credential collection — while collecting nothing (verified inert). Today there is no processing to disclose, so no data-subject harm occurs. The finding is that **zero transparency scaffolding exists**, and the visible login surface signals an intent to collect that has no accompanying notice.

**Evidence**: `Login.vue:8-30` (credential form with only the disclaimer `*No auth was implemented`); `onSubmit()` at `Login.vue:46-49` discards inputs and routes to `/main`; no privacy-policy route in `router/index.js`.

**Attack Scenario**: N/A (transparency/compliance gap, not an exploit). Conditional harm: activating the login without adding an Art. 13 notice means every account is created with no lawful-basis disclosure, no purpose statement, and no rights information — a per-user transparency violation.

**Existing Mitigations**: The `*No auth was implemented` disclaimer is a partial honesty signal, but it is not a privacy notice.

**Recommendation**: **Technical** — when the login is made functional, ship an Art. 13-compliant privacy notice at the point of collection (identity of controller, purposes, legal basis, retention, rights, complaint route) and a linkable privacy policy. **Organizational** — until then, either remove the inert credential form or keep the disclaimer prominent so no user is misled into typing real credentials. Addresses GDPR Art. 12–13.

---

### LOW PA-003: CloudWatch log sink has no PII scrubbing or personal-data retention policy
| Field | Value |
|-------|-------|
| ID | PA-003 |
| Severity | LOW (current) · **conditional MEDIUM (5–9) if PII added** |
| Confidence | MEDIUM |
| Affected Component(s) | D5 (CloudWatch Logs), C2 (Server API) |
| Scoring System | OWASP Risk Rating |
| Score | Current L2 × I1 = 2 (LOW) · Conditional L3 × I3 = 9 (MEDIUM) |
| Cross-Framework | LINDDUN: Disclosure of Information — D4 (surplus data) · Non-compliance — N3 (data-protection principles) · GDPR Art. 5(1)(e) (storage limitation) · GDPR Art. 5(1)(c) (data minimisation) |

**Description**: The Express error handler logs raw errors to stderr and returns `{code, description: err.message}` to the client (recon §1.8). Those logs flow to CloudWatch (D5) with a flat 30-day retention and no field-level redaction or PII filtering. There is no personal data to leak today. But the pattern — log-everything, echo raw errors — is exactly what silently captures personal data into logs once endpoints begin handling user input, and the fixed 30-day retention is not a personal-data-aware retention policy.

**Evidence**: recon §1.8 ("error handler returns `{code, description: err.message}` … `console.error`s the raw error"); recon §1.4 D5 ("`awslogs` driver, 30-day retention").

**Attack Scenario**: N/A today. Conditional: a future `/login` or `/profile` endpoint echoes a validation error containing the submitted email/username; that PII is written to CloudWatch and retained 30 days, readable by anyone with CloudWatch access, outside any consent or retention scope the user agreed to (Disclosure D4 + storage-limitation breach).

**Existing Mitigations**: 30-day retention bounds exposure; CloudWatch access is IAM-gated.

**Recommendation**: **Technical** — before personal-data endpoints ship, adopt structured logging with an allow-list of loggable fields (never log request bodies/credentials), redact identifiers, and set retention per data class rather than one flat window. **Organizational** — add "no PII in logs" to code-review and the privacy gate. Addresses GDPR Art. 5(1)(c) and 5(1)(e).

---

### LOW PA-004: No privacy governance scaffolding (ROPA, legal basis, retention, DSAR, consent)
| Field | Value |
|-------|-------|
| ID | PA-004 |
| Severity | LOW (current) · **conditional HIGH (10–16) if PII added** |
| Confidence | HIGH |
| Affected Component(s) | System-wide (C1, C2, D1, D5) |
| Scoring System | OWASP Risk Rating |
| Score | Current L1 × I1 = 1 (LOW) · Conditional L4 × I3 = 12 (HIGH) |
| Cross-Framework | LINDDUN: Non-compliance — N4 (accountability), N2 (data-subject rights), N1 (consent) · GDPR Art. 30 (ROPA), Art. 6 (lawful basis), Art. 17 (erasure), Art. 15 (access) · CCPA §1798.105 (right to delete), §1798.100 (right to know) |

**Description**: The system has no privacy governance artifacts: no Record of Processing Activities (GDPR Art. 30), no documented legal basis (Art. 6), no retention/deletion policy, no consent mechanism, and no data-subject-access-request pathway. This is entirely correct for a demo that processes no personal data — there is nothing to govern. It is recorded as a LOW finding because the **absence is total**: the first personal-data feature would ship into an environment with zero compliance foundation, making non-compliance the default rather than a slip.

**Evidence**: recon §1.2 ("No stated security requirements, threat model, data-classification policy, or compliance scope"); no consent, retention, or DSAR code anywhere in the tree; no accounts to which rights would attach.

**Attack Scenario**: N/A (governance gap). Conditional: launching accounts without a lawful basis (Art. 6) and without access/erasure mechanisms (Art. 15/17, CCPA §1798.100/§1798.105) exposes the operator to data-subject complaints (GDPR Art. 77) and, at scale, administrative fines (Art. 83).

**Existing Mitigations**: None needed currently — the no-personal-data posture is itself the mitigation.

**Recommendation**: **Technical** — build DSAR (access/export/delete) and consent capture as first-class features alongside, not after, the first account feature; instrument data-access audit logging. **Organizational** — before that feature, conduct a fresh DPIA (this document is the baseline), designate a privacy owner, and stand up a ROPA. Addresses GDPR Art. 30, 6, 15, 17; CCPA §1798.100, §1798.105.

---

## 5. Regulatory Compliance Matrix

Applicability was determined from the Phase 1 finding that **no personal data of any data subject is processed** and that the system is a demo (no revenue, no consumer base, no covered-entity relationship).

| Requirement | Regulation & Article (verified) | Status | Evidence / Rationale | Remediation (conditional) |
|---|---|---|---|---|
| Material scope — is personal data processed? | GDPR Art. 4 (definitions), Art. 2 (material scope) | **Not Applicable** | No personal data processed; catalog is non-personal, login stub inert, IPs not logged. | If EU users' personal data (incl. logged IP) is processed, GDPR engages. |
| Territorial scope | GDPR Art. 3 | **Not Applicable** | No offering of goods/services *for* personal data, no behavior monitoring. | Serving EU data subjects with accounts would trigger Art. 3(2). |
| Lawful basis | GDPR Art. 6 | **Not Applicable** | No processing requiring a basis. | Select and document a basis (likely Art. 6(1)(b) contract or 6(1)(a) consent) before account launch. |
| Transparency / notice | GDPR Art. 12, 13 | **Non-Compliant (latent)** — see PA-002 | No privacy notice exists; harmless today (nothing collected) but absent. | Publish an Art. 13 notice at collection. |
| Data-subject rights | GDPR Art. 15–22; CCPA §1798.100, §1798.105, §1798.110 | **Not Applicable** | No data subjects, no data to access/erase/port. | Build DSAR + deletion (PA-004) before accounts. |
| Data protection by design/default | GDPR Art. 25 | **Partially Compliant** | Account-less, PII-free design is minimizing *by accident*; but no TLS / encryption strategy for future PII (PA-001). | Bake in TLS, minimization, retention before PII. |
| Security of processing | GDPR Art. 32 | **Partially Compliant** | AWS-managed at-rest/in-transit for backend hops; but public HTTP ingress (PA-001). | TLS on ALBs; KMS/SSE for any PII store. |
| Storage limitation / minimization | GDPR Art. 5(1)(c), 5(1)(e) | **Not Applicable (latent PA-003)** | No personal data retained; flat 30-day log window is not PII-aware. | Per-class retention + log minimization. |
| Records of processing (ROPA) | GDPR Art. 30 (note Art. 30(5) SME exemption) | **Not Applicable** | No processing to record. | Stand up ROPA at first PII feature. |
| DPIA obligation | GDPR Art. 35(1), 35(7) | **Not Applicable** | No high-risk processing; no personal data. This document is the baseline PIA. | Re-run a full DPIA before high-risk processing (profiling, large-scale, special category). |
| Breach notification | GDPR Art. 33, 34 | **Not Applicable** | No personal-data breach is possible with no personal data. | Adopt a 72-hour (Art. 33) notification runbook before PII. |
| International transfers | GDPR Art. 44, 46 | **Not Applicable** | No personal data crosses borders. | If EU data is processed in a US AWS region, put SCCs (Art. 46(2)(c)) in place. |
| CCPA applicability | Cal. Civ. Code §1798.140 (definitions); §1798.100 thresholds | **Not Applicable** | No "personal information" collected; demo meets no $25M/100k-consumer/50%-revenue threshold. | Re-assess if commercialized with a California consumer base. |
| CCPA — right to know / delete / opt-out | §1798.100, §1798.105, §1798.120, §1798.135 | **Not Applicable** | No personal information to disclose, delete, or sell/share. | Build if commercialized. |
| HIPAA | 45 CFR §164.502, §164.312 | **Not Applicable** | No PHI; operator is not a covered entity or business associate; no health data of any kind. | Only relevant if health data is ever introduced (not indicated). |

**Regulatory conclusion:** In its current state the system triggers **no** GDPR, CCPA/CPRA, or HIPAA obligation because it processes no personal data. The two "Non-Compliant/Partially Compliant" rows (transparency, by-design/security) reflect *latent* structural gaps that carry no present legal exposure but would become live obligations on the first personal-data feature.

---

## 6. Privacy by Design Assessment

| # | Principle | Rating | Key Observation | Recommendation |
|---|---|---|---|---|
| 1 | Proactive not Reactive | **Weak** | No privacy risk assessment was done during design; this PIA is the first. Low stakes given no PII, but no proactive mechanism exists. | Make a PIA/DPIA a mandatory gate before any personal-data feature (this document is the template). |
| 2 | Privacy as the Default | **Adequate (incidental)** | The system collects no personal data and creates no accounts — the most privacy-protective posture possible. It is achieved by the demo's simplicity, not by deliberate default-setting. | Preserve minimization intentionally: when auth is added, make optional fields optional, opt-in not pre-checked, shortest retention default. |
| 3 | Privacy Embedded into Design | **Weak** | No TLS, no encryption strategy for future PII, no pseudonymization or PII/behavior separation in the data model. Nothing to protect yet, but no embedded patterns either. | Design a separate identity store, field-level encryption, and TLS *before* PII, per PbD Principle 3 patterns. |
| 4 | Full Functionality (Positive-Sum) | **Not Evaluable** | No privacy-vs-utility trade-off exists because there is no personal-data processing. | Revisit (differential privacy / synthetic test data) if analytics on user data is ever added. |
| 5 | End-to-End Security | **Weak** | Plaintext HTTP ingress (PA-001), no KMS/SSE beyond AWS defaults, local unencrypted Terraform state. Lifecycle protection for personal data is absent. | TLS in transit, AES-256/KMS at rest, crypto-shred/retention enforcement before any PII lifecycle exists. |
| 6 | Visibility and Transparency | **Absent** | No privacy notice, no ROPA, no consent receipts, no audit logging of data access (PA-002, PA-004). | Build notice + ROPA + access audit logging alongside the first personal-data feature. |
| 7 | Respect for User Privacy | **Not Evaluable / Absent** | No data subjects exist, so no DSAR, consent, or preference mechanisms are present to evaluate. | Ship self-service access/export/deletion and granular consent with the first account feature (PbD Principle 7 patterns). |

**PbD summary:** The system is privacy-protective today *by absence* (Principle 2 incidental strength) but has **no embedded privacy architecture** (Principles 3, 5, 6 weak/absent). The gap is not a present risk; it is a readiness gap that must be closed before the login stub becomes real.

---

## 7. Risk Register

| Risk ID | Description | LINDDUN Category | Likelihood (current) | Impact-on-individuals (current) | Severity (current) | Conditional Severity (PII added) | Regulatory Citation | Effort |
|---|---|---|---|---|---|---|---|---|
| PA-001 | Plaintext HTTP on public ALBs — latent transport exposure | Disclosure D1/D2 | 2 | 1 | **LOW (2)** | HIGH (12) | GDPR Art. 32, 5(1)(f) | Low |
| PA-002 | No transparency/notice; misleading inert login UI | Unawareness U1 | 1 | 1 | **LOW (1)** | MEDIUM (6) | GDPR Art. 12, 13 | Low |
| PA-003 | CloudWatch sink lacks PII scrubbing / PII-aware retention | Disclosure D4 · Non-compliance N3 | 2 | 1 | **LOW (2)** | MEDIUM (9) | GDPR Art. 5(1)(c), 5(1)(e) | Medium |
| PA-004 | No privacy governance scaffolding (ROPA/basis/DSAR/consent) | Non-compliance N4/N2/N1 | 1 | 1 | **LOW (1)** | HIGH (12) | GDPR Art. 30, 6, 15, 17; CCPA §1798.100, §1798.105 | Medium |

All current-state severities are LOW because **impact on individuals is 1 (negligible) when no individual's data is processed**. The conditional column is the actionable signal for anyone planning to add authentication and user accounts.

---

## 8. Recommendations

Prioritized by the conditional risk they head off. None are urgent in the current demo; all are **prerequisites** for any personal-data or authentication feature.

1. **Make TLS a release blocker for auth (PA-001).** *Technical:* ACM cert + HTTPS listener + HTTP→HTTPS redirect on C4 and C5; update `RestServices.js` to `https://`. *Organizational:* privacy release gate rejects any public HTTP listener once PII is in scope. *Regulatory:* GDPR Art. 32. *Effort: Low.*
2. **Establish the privacy governance baseline before the first account (PA-004).** *Technical:* build DSAR (access/export/delete) and consent capture as first-class features; add data-access audit logging. *Organizational:* designate a privacy owner, stand up a ROPA (Art. 30), document the legal basis (Art. 6), run a fresh DPIA. *PET:* consider synthetic data for non-prod so real PII never enters test environments. *Regulatory:* GDPR Art. 30, 6, 15, 17; CCPA §1798.100/§1798.105. *Effort: Medium.*
3. **Minimize and protect logs before endpoints handle user input (PA-003).** *Technical:* structured logging with a loggable-field allow-list, redact identifiers, never log request bodies/credentials, per-class retention. *Organizational:* "no PII in logs" in code-review checklist. *Regulatory:* GDPR Art. 5(1)(c), 5(1)(e). *Effort: Medium.*
4. **Add a real privacy notice and de-risk the login UI (PA-002).** *Technical:* Art. 13 notice at collection + linkable privacy policy when auth activates. *Organizational:* until then, keep the `*No auth was implemented` disclaimer prominent or remove the credential form so no user is misled into entering real credentials. *Regulatory:* GDPR Art. 12–13. *Effort: Low.*
5. **Design privacy into the future data model (PbD Principles 3 & 5).** Separate identity store from activity data, field-level encryption for sensitive fields, KMS/SSE on any PII store, PII-aware retention/crypto-shredding — decided at design time, not retrofitted.

---

## 9. Positive Observations

- **No personal data is processed** — the strongest possible privacy posture. Confirmed at source, not assumed: `Login.vue:46-49` discards credentials client-side; `RestServices.js:9-11` makes a single parameterless anonymous GET; the DynamoDB catalog holds only `id`/`path`/`title`.
- **Account-less design removes entire threat classes.** With no user accounts there is no user-enumeration surface (LINDDUN Detectability D3), no linkability of user actions (L1/L2), and no identifiability of data subjects (I1) — flaws that plague real auth systems are structurally absent.
- **Client IP addresses are not logged.** No ALB access logs or VPC flow logs are configured, so the one piece of routinely-personal network metadata (IP, personal data under GDPR per the *Breyer* line of reasoning) is never persisted.
- **Data minimization by default (incidental).** The API returns non-personal catalog data only; there is no over-collection because there is no collection.
- **Managed encryption on backend hops.** Task→DynamoDB/S3/CloudWatch traffic and at-rest stores use AWS-managed TLS/encryption (Phase 2 L3 `[ENC]`), so the data-plane behind the ALB is not the weak point — the public HTTP ingress is.
- **Honest self-labeling.** The `*No auth was implemented, just a Vue.js demo component` disclaimer signals the stub's nature, reducing (though not eliminating) the risk of a user mistaking it for a real login.

---

## Coverage States

Privacy-domain coverage-ledger item states, for the validation-specialist to merge into `coverage.json`. All five `privacy.*` items were seeded `not-applicable` at Phase 1 on the basis of the recon context flags; this assessment **confirms** that terminal state with independent, source-verified evidence (rather than leaving it as a seed assumption). `not-applicable` is the correct state for a system that processes no personal data. Each note also records what would flip the item to an active (`unknown`→to-be-assessed) state under a real deployment. Ids and states use the taxonomy in `coverage-taxonomy.json`.

| Item id | State | Detail / Note | Source |
|---------|-------|---------------|--------|
| privacy.data-inventory-classification | not-applicable | Confirmed: no personal data. Full data inventory (§2) verifies the catalog (D1) is non-personal (`id`/`path`/`title`), the login form (`Login.vue:46-49`) is inert and transmits nothing, and client IPs are not logged. Flip to active if user accounts/PII are introduced. | Login.vue, RestServices.js, recon §1.4, §2 above |
| privacy.purpose-minimization-consent | not-applicable | Confirmed: no personal data collected, so no purpose/consent/minimization obligation. Latent gap PA-002/PA-004 (no notice, no consent scaffolding) documented for the auth-added scenario. GDPR Art. 6/7 would engage on first account. | recon §1.2, PA-002, PA-004 |
| privacy.data-subject-rights | not-applicable | Confirmed: no data subjects and no personal data, so no access/erasure/portability rights attach. DSAR pathway absent by design; PA-004 flags this as the first-priority build before accounts. GDPR Art. 15–22 / CCPA §1798.100–105 conditional. | §3, PA-004 |
| privacy.retention-deletion | not-applicable | Confirmed: no personal data to retain or delete. CloudWatch (D5) 30-day window applies to non-personal app logs only; PA-003 flags it is not PII-aware retention. GDPR Art. 5(1)(e) conditional. | recon §1.4 (D5), PA-003 |
| privacy.anonymization-sharing | not-applicable | Confirmed: no personal data is anonymized, pseudonymized, or shared with third parties. AWS is an infrastructure processor for non-personal content only; no personal-data recipients exist. Cross-border transfer safeguards (GDPR Art. 44/46) conditional on serving EU data subjects. | §3, §5 |

**Cross-reference (not owned by privacy domain):** two adjacent items remain `unknown` and are owned by other phases but are privacy-relevant if PII is added — `data-classification.retention` and `logging-monitoring.centralization-retention`. Findings PA-003 (log minimization/retention) inform both; flagged here for the validation-specialist, not resolved by this agent.

---

## Cross-References
- **Phase 1 reconnaissance** (`01-reconnaissance.md`): asset inventory §1.4 (D1–D6), attack surface §1.7 (E1–E5), control inventory §1.8 (no-TLS, no-auth), and the `has_personal_data=false` / `has_regulatory=false` context basis.
- **Phase 2 structural diagram** (`02-structural-diagram.md`): node ids C1–C13, D1–D6, E1–E5, TB1–TB6, R0–R5, X1–X5. This assessment references C1, C2, C4, C5, D1, D5, D6, E1, E2, R0, TB1. L3 data diagram corroborates the `[PLAIN]`/`[ENC]` transport split underlying PA-001.
- **Related security findings (anticipated overlap):** PA-001 (no TLS) overlaps the threat-model's transport/eavesdropping and the compliance track's encryption-in-transit controls; PA-003 (logs) overlaps logging-monitoring coverage; PA-004 governance overlaps compliance ROPA/accountability. Deduplication is the validation-specialist's call — flagged here for cross-track merge.
- **Coverage ledger:** `coverage.json` privacy.* items (5), confirmed `not-applicable` above.

---

## Execution Log

### Process Health
| Metric | Value |
|--------|-------|
| Files Read | 9 (01-reconnaissance.md, 02-structural-diagram.md, agent-output-protocol.md, linddun-go-threats.md, gdpr-article-reference.md, global-privacy-regulations.md, privacy-by-design-patterns.md, Login.vue, RestServices.js) + coverage.json/recon.json inspected |
| Files Written | 1 (privacy-assessment.md) |
| Errors Encountered | 0 |
| Items Skipped | 0 |
| Self-Assessed Output Quality | HIGH |

### What Went Well
- Recon and Phase 2 diagram were thorough and internally consistent; canonical node ids (C/D/E/TB/R/X) mapped cleanly onto privacy findings.
- The single load-bearing fact — whether the login form actually collects data — was verified directly in `Login.vue` and `RestServices.js` rather than trusted from the recon summary. Confirmed inert: credentials never leave the browser.
- The seeded `coverage.json` already contained exactly five `privacy.*` items with clear `not-applicable` reasons, so Coverage States could confirm real ids/states rather than invent them.
- Every regulation article and LINDDUN threat type was cross-checked against the skill reference files before use.

### Issues Encountered
- None material. The main judgment call was avoiding template inflation: with zero personal data, the honest output is a small number of LOW findings plus a clearly-labelled conditional analysis, not a padded high-severity report. Resolved by scoring current-state impact-on-individuals as 1 (negligible) and separating conditional severity into its own column.

### What Was Skipped or Incomplete
- No dynamic/runtime observation — assessment is static (code + IaC). Runtime log contents (PA-003) were inferred from the source error handler, hence MEDIUM confidence on that finding. No impact on the core no-personal-data conclusion, which is source-confirmed.
- Did not read `data-classification-taxonomy.md` or `dpia-output-template.md` in full — the skill body provides the 1–5 sensitivity scale and 10-section structure directly, and no exotic classification was needed for non-personal data. Low risk.

### Assumptions Made
- Assumed the login stub represents intent to add authentication later (per the team lead's framing and the visible credential UI); the conditional/forward-looking analysis rests on this. Explicitly labelled as conditional throughout.
- Assumed single AWS region / single environment (consistent with recon), so cross-border transfer analysis is conditional, not current.
- Assumed no ALB access logging remains disabled (recon confirms none in the Terraform); this is why client IP is treated as not-personal-data-in-practice today.
