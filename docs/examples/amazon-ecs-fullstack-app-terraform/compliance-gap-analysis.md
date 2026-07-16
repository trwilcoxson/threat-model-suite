# Compliance Specialist — Compliance Gap Analysis

## Metadata

| Field | Value |
|-------|-------|
| Agent | compliance-specialist (grc-agent) |
| Date | 2026-07-11 |
| Target System | AWS ECS Fullstack App (Terraform Demo) — MIT-0 reference sample |
| Frameworks Assessed | SOC 2 Type II (2017 TSC, scored) · CIS AWS Foundations / cloud-security baseline (technical checks, scored) · ISO 27001:2022 & NIST 800-53 Rev 5 (cross-mapped reference) · PCI-DSS v4.0 & HIPAA (assessed Not Applicable) |
| Assessment Scope | `Infrastructure/` (Terraform IaC + modules + Templates), `Code/server` (Node.js/Express API), `Code/client` (Vue.js SPA), CI/CD pipeline, AWS control surface — as inventoried in `01-reconnaissance.md` and referenced by Phase 2 node ids (C1-C13, D1-D6, E1-E5, TB1-TB6, R0-R5, X1-X5) |
| Scope Exclusions | AWS-managed physical/environmental controls (shared-responsibility — AWS SOC 2/ISO reports cover data-center, hardware, hypervisor); runtime penetration testing; organizational policy documents (none exist in repo) |
| Assessment Method | Static IaC/config/code review via reconnaissance + structural DFD; control mapping against verified framework reference files; no runtime testing |
| Scoring System | Qualitative (per agent-output-protocol.md — CRITICAL/HIGH/MEDIUM/LOW) |
| Methodology | SOC 2 TSC control mapping + CIS AWS/cloud baseline + cross-framework mapping (ISO 27001:2022, NIST 800-53 Rev 5); 6-phase compliance-assessment methodology |

---

## Summary

- **Total findings: 14 (0 Critical, 8 High, 4 Medium, 2 Low).** No CRITICAL: per the qualitative rubric, CRITICAL denotes an active regulatory violation/enforcement — and **no compliance regime is formally in scope** for this MIT-0 demo (no PII/PHI/cardholder data). Findings are framed as **"what a production deployment would need to close"** before it could pass a SOC 2 Type II or clear a CIS AWS baseline.
- **SOC 2 readiness ≈ 15.7%; CIS AWS/cloud technical baseline ≈ 13.3%; combined ≈ 15.0%.** The system has credible cloud-network *bones* (private subnets, SG chaining, multi-AZ, blue/green rollback) but essentially **no security program and no audit-evidence surface** — the two things a SOC 2 Type II is built on.
- **Top 3 gaps (all HIGH, all audit-blocking for a real engagement):**
  1. **No security audit trail** (GRC-004) — no CloudTrail, no ALB access logs, no VPC flow logs, no Config/GuardDuty. A SOC 2 Type II literally cannot be evidenced without an audit trail (CC7.2/CC7.3).
  2. **No governance program** (GRC-008) — no policies, risk assessment, incident response, access reviews, or training. SOC 2 is ~50% organizational controls (CC1-CC5, CC9); all are absent.
  3. **No encryption in transit** (GRC-001) — both public ALBs are HTTP:80 only; all app traffic is plaintext (CC6.1/CC6.7).
- **Key recommendation:** For any non-demo use, sequence remediation as **(a) turn on the audit-evidence plane** (CloudTrail + access/flow logs + Config) — cheap, unblocks everything downstream — then **(b) close the transport/access-control gaps** (TLS, scoped IAM, image scanning), then **(c) stand up the governance program** (policies, risk assessment, IR, vendor management) which is the long pole for SOC 2.

---

## Scope and Applicability Matrix

| Framework | Applicable? | Rationale | Priority |
|-----------|:-----------:|-----------|:--------:|
| **SOC 2 Type II** (2017 TSC) | Yes (reference) | Cloud-hosted SaaS-shaped fullstack app; SOC 2 is the standard enterprise-customer assurance report and the most relevant framework for this control surface. Assessed against Common Criteria (CC1-CC9) + Availability (A1). Used as the primary scored framework. | P1 |
| **CIS AWS Foundations / cloud-security baseline** | Yes (reference) | The system is 100% AWS (ECS/ALB/S3/DynamoDB/ECR/IAM/VPC). CIS AWS Foundations Benchmark is the canonical baseline for the AWS control surface (encryption, logging, IAM, network exposure). Scored as a technical checklist; see limitation on CIS numeric IDs below. | P1 |
| **ISO 27001:2022** | Yes (cross-map) | The international ISMS certification path. Not independently scored here (would require the management-system clauses + a full 93-control Annex A pass); mapped to SOC 2/NIST equivalents for evidence reuse. | P2 |
| **NIST 800-53 Rev 5** | Yes (cross-map) | Serves as the detailed control catalog behind CIS AWS and FedRAMP. Not independently scored; used to give each finding a precise control anchor via `cross-framework-mapping.md`. | P2 |
| **PCI-DSS v4.0** | **No** | No cardholder data anywhere. Product catalog is non-financial (`id/path/title`); the `Login.vue` "password" field is inert (`Code/client/src/components/Login.vue:28`); no payment flow exists. No cardholder-data environment (CDE) to scope. | — |
| **HIPAA Security Rule** | **No** | No protected health information (PHI). No healthcare context, no covered-entity/business-associate relationship, no ePHI stored or transmitted. | — |
| **GDPR / CCPA (privacy)** | **No** (this report) | `has_personal_data = false` (recon §1.10). Privacy posture is owned by the privacy-specialist (`privacy-assessment.md`); not re-assessed here. | — |

> **PCI/HIPAA note:** Both are Not Applicable *today*. If a production deployment wires the login form to real auth, stores user accounts, or adds a payment path, PCI-DSS and/or privacy scope must be re-triggered (recon §1.10 flags this explicitly).

---

## Compliance Status Dashboard

> **Calculation:** `% Complete = (Compliant + Partial*0.5) / (Total - N/A) * 100`

| Framework | Version | Total Reqs | Compliant | Partial | Not Implemented | N/A | % Complete |
|-----------|---------|:----------:|:---------:|:-------:|:---------------:|:---:|:----------:|
| SOC 2 (CC + Availability) | 2017 TSC | 36 | 0 | 11 | 24 | 1 | **15.7%** |
| CIS AWS / cloud baseline (technical checks) | — | 15 | 0 | 4 | 11 | 0 | **13.3%** |
| **Combined** | — | **51** | **0** | **15** | **35** | **1** | **15.0%** |

**SOC 2 math:** `(0 + 11*0.5) / (36 - 1) * 100 = 5.5 / 35 * 100 = 15.7%`
**CIS/cloud math:** `(0 + 4*0.5) / (15 - 0) * 100 = 2.0 / 15 * 100 = 13.3%`
**Combined math:** `(0 + 15*0.5) / (51 - 1) * 100 = 7.5 / 50 * 100 = 15.0%`

**SOC 2 per-criterion breakdown (36 criteria = CC1.1-CC9.2 [33] + A1.1-A1.3 [3]):**

| Status | Criteria |
|--------|----------|
| **Partial (11)** | CC2.1 (informal data classification in recon §1.4), CC5.1, CC5.2 (some technical control activities exist), CC6.1 (cloud IAM present but no user auth/MFA/TLS), CC6.5 (`force_destroy` exists, no sanitization policy), CC6.6 (SG + private subnets, but `0.0.0.0/0:80` open, no WAF), CC7.2 (CloudWatch autoscaling alarms, no security monitoring), CC7.5 (blue/green deploy rollback only), CC8.1 (CodePipeline + IaC, no approval/test gate), A1.1 (autoscaling min1/max4), A1.2 (multi-AZ, but single-NAT SPOF, no DR) |
| **N/A (1)** | CC6.4 (physical access — AWS shared responsibility) |
| **Not Implemented (24)** | CC1.1-CC1.5, CC2.2, CC2.3, CC3.1-CC3.4, CC4.1, CC4.2, CC5.3, CC6.2, CC6.3, CC6.7, CC6.8, CC7.1, CC7.3, CC7.4, CC9.1, CC9.2, A1.3 |
| **Compliant (0)** | — none reach the "auditor-defensible, fully satisfies" bar in a demo with no program and no evidence retention |

**CIS AWS / cloud baseline (15 technical checks):** Partial (4): S3 SSE (default AWS-owned key, no CMK), SG exposure (only :80, tasks private — but `0.0.0.0/0` open), DynamoDB encryption (default), multi-AZ redundancy (single NAT). Not Implemented (11): ALB HTTPS/TLS, S3 public-access-block, S3 versioning, S3/ALB access logging, CloudTrail, VPC flow logs, AWS Config, GuardDuty, IAM least-privilege (no wildcards), ECR scan-on-push + immutable tags, Secrets Manager/SSM (no plaintext secret in state).

---

## Framework-Specific Findings

> Findings are grouped by control domain. Each cites verified SOC 2 IDs (`soc2-trust-services-criteria.md`) plus cross-framework anchors verified against `nist-800-53-controls.md`, `iso27001-annex-a-controls.md`, and `cross-framework-mapping.md`. Node ids (C*/D*/E*/TB*/R*/X*) reference the Phase 2 structural diagram.

### SOC 2 Type II + CIS AWS / cloud baseline

---

### HIGH GRC-001: No Encryption in Transit — Public ALBs are HTTP-only

| Field | Value |
|-------|-------|
| ID | GRC-001 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | C4 (Client ALB), C5 (Server/API ALB), C1, C2, C3; entry points E1, E2, E3; boundaries TB1, TB2 |
| Scoring System | Qualitative |
| Score | HIGH (material deficiency — auditors flag plaintext transport as a reportable control failure) |
| Cross-Framework | SOC 2 CC6.1, CC6.7 · NIST SC-8, SC-8(1) · ISO A.8.24 · (map: PCI 4.2, HIPAA §164.312(e)(1) — N/A here) |

**Description**: No TLS listener is created on either ALB. `enable_https` defaults `false` and `main.tf` never sets it, so only an HTTP:80 listener exists. All browser↔ALB and ALB↔task traffic is plaintext; the SPA calls `http://<SERVER_ALB>/api/getAllProducts` and Swagger advertises `schemes: ['http']`. SOC 2 CC6.7 (restrict transmission of information) and CC6.1 cannot be met without encryption in transit on public interfaces.

**Evidence**: `Infrastructure/Modules/ALB/main.tf:38` (HTTP:80 listener only); `variables.tf:27` (`enable_https` default false); `Code/server/src/swagger.js` (`schemes: ['http']`); recon §1.8 "No TLS". L3 DFD marks every ingress/east-west edge `[PLAIN]`.

**Attack Scenario**:
1. Attacker on any network path between client and ALB (public WiFi, upstream ISP, compromised router) passively captures traffic.
2. Product data, Swagger API structure, and any future session tokens are readable in cleartext.
3. Active MitM injects/modifies responses (no integrity protection).

**Existing Mitigations**: AWS-SDK calls from tasks to DynamoDB/S3/ECR ride AWS-managed TLS (`[ENC]` in L3) — but that only covers task→AWS-service, not the public app plane.

**Recommendation**: Add an ACM certificate and an HTTPS:443 listener on both ALB modules; set `enable_https = true`; add an HTTP→HTTPS redirect (301); restrict SG ingress to :443; set Swagger `schemes: ['https']` and the SPA base URL to `https://`. Enforce TLS 1.2+ via a modern ALB security policy.

---

### HIGH GRC-002: No Authentication or Authorization on Application Endpoints

| Field | Value |
|-------|-------|
| ID | GRC-002 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | C1 (Client SPA), C2 (Server API), C3 (Swagger); E1, E2, E3; R0 (anonymous user); TB1 |
| Scoring System | Qualitative |
| Score | HIGH (SOC 2 CC6.1/CC6.2/CC6.3 logical-access criteria are foundational; total absence fails the domain) |
| Cross-Framework | SOC 2 CC6.1, CC6.2, CC6.3 · NIST AC-3, IA-2, AC-2 · ISO A.5.15, A.5.16, A.8.5 |

**Description**: There is no authentication or authorization anywhere in the application. `Login.vue`'s `onSubmit()` discards the entered credentials and routes to `/main`; the server has no middleware, guards, tokens, or sessions. Every endpoint (including the DynamoDB-backed `/api/getAllProducts` and the Swagger UI) is anonymous. SOC 2 CC6.1 (logical access), CC6.2 (registration/authorization before credential issuance), and CC6.3 (access modification/removal, least privilege) have no user-facing implementation to evidence.

**Evidence**: `Code/client/src/components/Login.vue:28` (`*No auth was implemented, just a Vue.js demo component`); `Code/server/src/app.js` (routes `/status`, `/api/getAllProducts`, `/api/docs` with no auth middleware); recon §1.3 "AuthN/AuthZ: None."

**Attack Scenario**:
1. Any internet user reaches every endpoint with no credential.
2. Full product catalog is scrapable; Swagger UI exposes the API contract to aid further probing.
3. In a production variant that adds any write path or user data, the same anonymous surface becomes a direct data-exposure/abuse vector.

**Existing Mitigations**: Machine-to-cloud identity exists (ECS task/execution roles authenticate to AWS) — but this is not user access control. For the *demo* dataset (non-personal catalog) the exposure is low; the gap is a production/compliance readiness blocker, not a live breach of sensitive data.

**Recommendation**: Introduce an authentication layer before any production use — e.g., an ALB OIDC/Cognito authenticate action at the edge, or app-level JWT/session middleware — with role-based authorization on the API, MFA for privileged/admin paths (NIST IA-2), and a documented user registration/deprovisioning process (CC6.2/CC6.3). Restrict Swagger UI to non-public/authenticated access.

---

### HIGH GRC-003: IAM Over-Permissioning — Wildcard Actions and `iam:PassRole *`

| Field | Value |
|-------|-------|
| ID | GRC-003 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | R2 (ECS task role), R3 (DevOps role); TB3, TB4 |
| Scoring System | Qualitative |
| Score | HIGH (least-privilege violation with broad blast radius — a standard SOC 2 CC6.3 / CIS IAM finding) |
| Cross-Framework | SOC 2 CC6.1, CC6.3 · NIST AC-6, AC-6(1), AC-6(5), AC-5 · ISO A.8.2, A.5.15, A.5.18 |

**Description**: The DevOps role grants `s3:*` / `ecs:*` / `codedeploy:*` / `logs:*` / `iam:PassRole` on `resources = ["*"]`, and the **ECS task (application runtime) role holds `iam:PassRole` on `*`** — an unusual and dangerous grant for an app role. This breaks least privilege (SOC 2 CC6.3, NIST AC-6). `iam:PassRole *` combined with service access is a well-known privilege-escalation primitive.

**Evidence**: `Infrastructure/Modules/IAM/main.tf:175` and `:306` (wildcard actions + `iam:PassRole` on `*`); recon §1.5 (R2 has `iam:PassRole *`), §1.8 "IAM over-permissioning."

**Attack Scenario**:
1. Attacker gains code execution in the server container (any app RCE/SSRF foothold).
2. Container assumes the task role via IMDS; `iam:PassRole *` lets it pass a higher-privileged role to an AWS service it can invoke.
3. Privilege escalation and lateral movement across the account.

**Existing Mitigations**: DynamoDB and S3 actions on the task role *are* resource-scoped to specific ARNs (recon §1.8) — partial least privilege. Fargate removes host-level access.

**Recommendation**: Remove `iam:PassRole` from the task role entirely (an app runtime role should not pass roles). Scope the DevOps role to specific resource ARNs and the minimum action set per pipeline stage; replace `s3:*`/`ecs:*` with enumerated actions. Add an IAM Access Analyzer policy and enable AWS Config `iam-*` rules to catch wildcard drift.

---

### HIGH GRC-004: No Security Audit Trail — CloudTrail, ALB Access Logs, VPC Flow Logs, Config all Absent

| Field | Value |
|-------|-------|
| ID | GRC-004 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | Whole account/VPC (TB5, TB6); C4, C5 (no ALB logs); D5 (CloudWatch — task/build logs only) |
| Scoring System | Qualitative |
| Score | HIGH (audit-evidence plane absent — a SOC 2 Type II cannot be evidenced without it; also a CIS AWS logging-baseline failure) |
| Cross-Framework | SOC 2 CC7.1, CC7.2, CC7.3 · NIST AU-2, AU-3, AU-6, AU-9, AU-11, AU-12, SI-4 · ISO A.8.15, A.8.16 · (map: PCI 10.2/10.4, HIPAA §164.312(b) — N/A here) |

**Description**: The only logging in the IaC is `awslogs` for ECS tasks and CodeBuild (30-day retention). There is **no CloudTrail** (API-call audit), **no ALB access logs**, **no VPC flow logs**, and **no AWS Config / GuardDuty** declared. SOC 2 CC7.2/CC7.3 (monitor components for anomalies; evaluate security events) and the entire NIST AU family have no evidence source. This is the single biggest audit-readiness blocker: a SOC 2 Type II is an *evidence-over-time* report, and there is no security audit trail to sample.

**Evidence**: `Infrastructure/Modules/ECS/TaskDefinition/main.tf:45` (awslogs driver, 30-day retention); recon §1.8 "No ALB access logs, no VPC flow logs; no GuardDuty/Config/CloudTrail declared in IaC"; L1/L3 DFD show D5 receiving only task+build logs.

**Attack Scenario**:
1. Attacker performs reconnaissance, credential use, or data access against the account.
2. No CloudTrail/flow-log/access-log record exists to detect, alert, or reconstruct the activity.
3. Incident goes undetected; post-incident forensics and breach scoping are impossible (also cripples CC7.4/CC7.5).

**Existing Mitigations**: CloudWatch metrics + autoscaling alarms exist for operational (not security) monitoring (CC7.2 partial). ECS task logs capture app stderr.

**Recommendation**: Enable an org/account CloudTrail (management + data events for S3/DynamoDB) to an encrypted, access-logged S3 bucket with ≥1yr retention (AU-11); enable ALB access logs on C4/C5; enable VPC flow logs on the VPC; enable AWS Config with a conformance pack and GuardDuty for anomaly detection (SI-4). Centralize + alert (CC7.3). This is low-cost and unblocks most downstream audit evidence.

---

### HIGH GRC-005: No Vulnerability Management — No Image Scanning, No SCA, Mutable Tags, Unpinned Base Images

| Field | Value |
|-------|-------|
| ID | GRC-005 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | D4 (ECR), C10 (CodeBuild), X2/X3 (npm), X4 (base images); TB4 |
| Scoring System | Qualitative |
| Score | HIGH (no vulnerability-detection capability across image + dependency supply chain) |
| Cross-Framework | SOC 2 CC7.1 · NIST RA-5, SI-2, SI-2(2), CM-7, SR-3 · ISO A.8.8, A.8.28 · (map: PCI 6.3/11.3 — N/A here) |

**Description**: ECR repositories are `MUTABLE` with **no `scan_on_push`**; Docker base images are unpinned (`node:latest`, `nginx:latest`) with no digest pinning; and there is no software composition analysis (SCA)/SBOM in the pipeline. SOC 2 CC7.1 (detect newly discovered vulnerabilities) and NIST RA-5/SI-2 have no implementation. Mutable tags mean a `:latest` push can silently replace a running image (integrity gap).

**Evidence**: `Infrastructure/Modules/ECR/main.tf` (MUTABLE, no scan-on-push); `Code/*/Dockerfile` (unpinned `:latest`); recon §1.8 "ECR: MUTABLE tags, no scan_on_push. Base images unpinned; no SBOM/SCA."; §1.10 notes aws-sdk v2 + Vue 2 are EOL/maintenance.

**Attack Scenario**:
1. A vulnerable transitive npm package or base-image CVE ships to production undetected (no scan gate).
2. Mutable tag allows an attacker with registry write (or a compromised build) to overwrite an image tag pointing at running tasks.
3. Exploitable vulnerability persists with no detection/remediation loop.

**Existing Mitigations**: Fargate patches the host/runtime; blue/green rollback limits a bad deploy's blast radius. Neither addresses image/dependency vulnerabilities.

**Recommendation**: Set ECR `image_tag_mutability = IMMUTABLE` and `scan_on_push = true` (or Inspector enhanced scanning); pin base images by digest; add SCA (npm audit / Trivy / Dependabot) and generate an SBOM in `buildspec.yml` with a fail-the-build severity gate; establish a patch cadence (SI-2) and plan migration off EOL aws-sdk v2 / Vue 2 (SA-22).

---

### HIGH GRC-006: CI/CD Change Management — No Approval Gate, Auto-Deploy on `main`, Privileged Build

| Field | Value |
|-------|-------|
| ID | GRC-006 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | C9 (CodePipeline), C10 (CodeBuild, privileged), C11 (CodeDeploy), X1 (GitHub), E4; TB4; R3 |
| Scoring System | Qualitative |
| Score | HIGH (change-management control CC8.1 lacks the segregation/approval that audits require) |
| Cross-Framework | SOC 2 CC8.1, CC3.4 · NIST CM-3, CM-3(2), CM-5, AC-6 · ISO A.8.32, A.8.4, A.8.31 |
| Related | GRC-003 (DevOps role), GRC-005 (build supply chain) |

**Description**: `PollForSourceChanges = true` on `main` means any merge auto-builds and auto-deploys with **no manual approval gate** and no automated test/quality gate before production. CodeBuild runs `privileged_mode = true` (Docker-in-Docker) on a dated managed image (`standard:4.0`). SOC 2 CC8.1 (authorize, test, approve changes) is only partially met: the mechanics (IaC, blue/green) exist, but the *authorization and testing gates* auditors sample do not.

**Evidence**: `Infrastructure/Modules/CodePipeline/main.tf:20,33` (`PollForSourceChanges`, no approval stage); recon §1.3 "any merge to `main` auto-builds and deploys," "CodeBuild `privileged_mode = true`"; TA3 profile (§1.6) — insider/compromised dev, no deploy approval gate.

**Attack Scenario**:
1. A developer with `main` push access (or a compromised account) merges malicious code.
2. Pipeline auto-builds and deploys to production with no human approval or test gate.
3. Malicious change is live; privileged build container widens the compromise surface.

**Existing Mitigations**: CodeDeploy blue/green with auto-rollback on `DEPLOYMENT_FAILURE`; SNS deploy notifications; branch-based triggering. These cover *availability* of a bad deploy, not *authorization* of a malicious one.

**Recommendation**: Add a manual approval stage (or protected-branch + required PR reviews + required status checks) before the deploy stage (CC8.1, CM-5); add automated test/lint/security gates in the build (CM-3(2)); remove `privileged_mode` unless Docker-in-Docker is strictly required and upgrade the CodeBuild image; separate the pipeline that can *approve* from the one that *builds* (segregation of duties, AC-5).

---

### HIGH GRC-007: Secrets Management — GitHub PAT in Unencrypted Local Terraform State, No Vault, No Rotation

| Field | Value |
|-------|-------|
| ID | GRC-007 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | D6 (local Terraform state), X1 (GitHub PAT), R5 (operator); TB4 |
| Scoring System | Qualitative |
| Score | HIGH (long-lived credential stored plaintext at rest with no rotation — sole supply-chain trust anchor) |
| Cross-Framework | SOC 2 CC6.1 · NIST SC-12, IA-5, IA-5(6) · ISO A.8.24, A.5.17 |

**Description**: The GitHub PAT (the single supply-chain trust anchor) is passed as a `sensitive` Terraform variable but persisted into **local, unencrypted `terraform.tfstate`** on the operator workstation and into the CodePipeline source config, with no rotation. There is no Secrets Manager/SSM/KMS usage; `taskdef.json` `secretOptions: null`. SOC 2 CC6.1 and NIST SC-12/IA-5 (authenticator management) have no managed secrets implementation; the design has no path to inject future runtime secrets safely.

**Evidence**: `Infrastructure/Modules/CodePipeline/main.tf:29`; `README.md:37` (local state holds `github_token`); recon §1.3 "No Secrets Manager/SSM/KMS," §1.4 D6 "unencrypted, no locking," §1.8 "Terraform state local + unencrypted with the PAT inside."

**Attack Scenario**:
1. Operator workstation is compromised or the `terraform.tfstate` file is inadvertently shared/committed.
2. Plaintext PAT is extracted, granting repo access (source tampering → auto-deploy via GRC-006).
3. No rotation means the exposure window is open indefinitely.

**Existing Mitigations**: PAT is marked `sensitive` and excluded from plan drift via `ignore_changes`; `.gitignore` excludes `terraform.tfstate*` (reduces accidental commit). It is a design/handling concern, not a committed secret (recon §1.3 confirmed clean tree).

**Recommendation**: Move to a remote encrypted Terraform backend (S3 + SSE-KMS + DynamoDB state locking); replace the long-lived PAT with GitHub's CodeConnections/OAuth app (short-lived tokens) or a fine-grained PAT stored in Secrets Manager with rotation (IA-5); never persist credentials to local state. Adopt Secrets Manager/SSM+KMS as the standard injection path for any future runtime secret.

---

### HIGH GRC-008: No Governance Program — Policies, Risk Assessment, Incident Response, Access Reviews, Training All Absent

| Field | Value |
|-------|-------|
| ID | GRC-008 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | Whole system / organization |
| Scoring System | Qualitative |
| Score | HIGH (SOC 2 is ~50% organizational controls; the entire control environment, risk-assessment, monitoring, and incident-response program is absent — not audit-ready) |
| Cross-Framework | SOC 2 CC1.1-CC1.5, CC2.2, CC2.3, CC3.1-CC3.4, CC4.1, CC4.2, CC5.3, CC7.4, CC9.1, CC9.2 · NIST PL-2, RA-3, IR-1, IR-4, IR-8, AT-2, PS-3 · ISO A.5.1, A.5.24, A.6.3 |
| Related | GRC-011 (vendor management, CC9.2) |

**Description**: The repository is a demo with **no security program**: no policies (information security, acceptable use, data classification, change management), no risk-assessment process, no incident-response plan, no monitoring/deficiency-tracking process, no security roles/ownership (recon: "no TM owner assigned"), no personnel security or awareness training. This collapses the entire SOC 2 organizational spine — CC1 (control environment), CC2 (communication), CC3 (risk assessment), CC4 (monitoring), CC5.3 (policy deployment), CC7.4 (incident response), CC9 (risk mitigation/vendor). README explicitly states corners are cut "due to demo proposals."

**Evidence**: recon §1.2 "No stated security requirements, threat model, data-classification policy, or compliance scope"; §1.10 coverage `document-metadata.ownership: partial` (no TM owner); absence of any `SECURITY.md`, policy docs, or IR runbook in the 85-file tree.

**Attack Scenario**: (governance, not technical) An auditor requests the information-security policy, the most recent risk assessment, the access-review log, and the incident-response plan on day one of a SOC 2 Type II. None exist → the engagement stops before technical controls are even sampled.

**Existing Mitigations**: This threat-model assessment itself is a first risk-assessment artifact (CC3.2 seed). Some technical control activities exist (CC5.1/CC5.2 partial).

**Recommendation**: Stand up the governance baseline before pursuing SOC 2: assign a security owner (CC1.3); author the core policy set (InfoSec, acceptable use, data classification, access control, change management, incident response) (CC5.3, PL-2); implement an annual + change-triggered risk-assessment process (CC3.2, RA-3); write and test an incident-response plan (CC7.4, IR-8); define access-review cadence (CC6.3); add security awareness training (CC1.4, AT-2). This is the long pole — plan 3-6 months of program build.

---

### MEDIUM GRC-009: Encryption at Rest Not Hardened — Default AWS-Owned Keys, No S3 Public-Access-Block/Versioning

| Field | Value |
|-------|-------|
| ID | GRC-009 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | D1 (DynamoDB), D2 (S3 assets), D3 (S3 artifacts), D4 (ECR) |
| Scoring System | Qualitative |
| Score | MEDIUM (baseline encryption exists via AWS defaults; gap is CMK control + S3 hardening, not raw plaintext) |
| Cross-Framework | SOC 2 CC6.1 · NIST SC-28, SC-28(1), SC-12 · ISO A.8.24 |

**Description**: All AWS stores get AWS-owned default encryption at rest, but there is **no explicit SSE-KMS/customer-managed key**, no S3 **public-access-block**, no S3 **versioning**, and no bucket policy hardening. DynamoDB has no explicit KMS. SOC 2 CC6.1 and NIST SC-28 are *partially* met (data is encrypted) but lack the key-control and configuration hardening auditors expect, and the missing public-access-block leaves a bucket-exposure risk if an ACL/policy is later misconfigured.

**Evidence**: recon §1.4 D1 "default (AWS-owned) encryption, no explicit SSE-KMS," D2 "no SSE block, no public-access-block, no versioning"; §1.8 "S3: no server-side-encryption block, no public-access-block, no versioning"; L3 DFD marks stores `[ENC]` with "AWS-managed default / no explicit KMS."

**Attack Scenario**:
1. A future change (or human error) sets a permissive bucket ACL/policy on D2/D3.
2. Without an account/bucket public-access-block as a backstop, objects become internet-readable.
3. No versioning means overwrite/deletion is unrecoverable; no CMK means no key-level access separation or rotation control.

**Existing Mitigations**: AWS-owned-key encryption is on by default for S3/DynamoDB/ECR (`[ENC]`); S3 `acl=private` is set.

**Recommendation**: Add explicit `aws_s3_bucket_server_side_encryption_configuration` with an SSE-KMS CMK; enable `aws_s3_bucket_public_access_block` (all four flags true) at bucket and account level; enable versioning on D2/D3; set DynamoDB `server_side_encryption` to a CMK and enable ECR KMS encryption (SC-28(1), SC-12).

---

### MEDIUM GRC-010: No WAF, Rate Limiting, or DoS Protection on Public ALBs

| Field | Value |
|-------|-------|
| ID | GRC-010 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | C4 (Client ALB), C5 (Server/API ALB); E1, E2; TB1 |
| Scoring System | Qualitative |
| Score | MEDIUM (availability + boundary-protection gap on internet-facing L7 surface) |
| Cross-Framework | SOC 2 CC6.6, A1.1 · NIST SC-5, SC-7, SC-7(5) · ISO A.8.20, A.8.21 |

**Description**: Both internet-facing ALBs (SG `0.0.0.0/0:80`) have no WAF, no rate limiting, and no bot/DoS control. Open CORS (`app.use(cors())`) reflects any origin. SOC 2 CC6.6 (restrict access through boundaries) is partially met by network segmentation but lacks L7 protection; Availability A1.1 is pressured because autoscaling is capped at 4 tasks, so a flood can exhaust capacity and drive cost.

**Evidence**: `Infrastructure/main.tf:90,100` (SG `0.0.0.0/0:80`); `Code/server/src/app.js:10` (`app.use(cors())`); recon §1.8 "No WAF, no rate limiting, no bot control"; TA2 profile (§1.6) "no WAF/rate limit; autoscaling capped at 4 tasks."

**Attack Scenario**:
1. Bot/botnet floods the public API/SPA endpoints.
2. Autoscaling hits its max-4 ceiling; latency/availability degrade; cost rises.
3. No L7 filtering blocks scanners, credential-stuffing (if auth is later added), or injection probes.

**Existing Mitigations**: Multi-AZ ALBs + target-tracking autoscaling (min1/max4) absorb moderate load; tasks are in private subnets reachable only from the ALB SG.

**Recommendation**: Attach AWS WAF (managed rule groups + rate-based rules) to both ALBs; tighten CORS to an explicit allow-list of origins; consider Shield Advanced if DoS is a material concern; raise/parameterize the autoscaling ceiling with a documented capacity plan (A1.1).

---

### MEDIUM GRC-011: Third-Party / Vendor Risk Unmanaged; EOL Dependencies

| Field | Value |
|-------|-------|
| ID | GRC-011 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | X1 (GitHub), X2/X3 (npm server+client), X4 (base images), X5 (CodeBuild image); C1, C2 |
| Scoring System | Qualitative |
| Score | MEDIUM (no vendor due-diligence process; concrete EOL/maintenance-status dependencies in the stack) |
| Cross-Framework | SOC 2 CC9.2 · NIST SR-3, SR-6, SA-22 · ISO A.5.19, A.5.21, A.5.23 |
| Related | GRC-005 (SCA/image scanning), GRC-008 (CC9 program) |

**Description**: No vendor management or third-party risk process exists for the external dependencies the system trusts: GitHub (source + PAT), npm registries, public ECR base images, and the CodeBuild managed image. Two core dependencies are EOL/maintenance: **aws-sdk v2** (superseded by v3) and **Vue 2** (EOL). SOC 2 CC9.2 (assess and manage vendor risk) and NIST SR-3/SR-6 have no process; SA-22 (unsupported components) is triggered by the EOL libraries.

**Evidence**: recon §1.3 external integrations (aws-sdk v2, axios, cors, public ECR base images); §1.10 "aws-sdk v2 + Vue 2 are EOL/maintenance"; §1.8 "no SCA/SBOM."

**Attack Scenario**:
1. An EOL dependency receives no security patches; a disclosed CVE has no upstream fix.
2. A compromised/typosquatted npm package or base image is pulled at build (no provenance check).
3. No vendor monitoring means the org is unaware of a supplier breach affecting GitHub/registry.

**Existing Mitigations**: Dependencies are enumerated in the manifests; `.gitignore` excludes `node_modules`.

**Recommendation**: Establish a vendor inventory + risk-tiering process (CC9.2); collect SOC 2 reports / attestations for critical suppliers where applicable; plan migration off aws-sdk v2 → v3 and Vue 2 → Vue 3 (SA-22); pair with GRC-005's SCA/SBOM and base-image pinning for supply-chain provenance (SR-3).

---

### MEDIUM GRC-012: Availability & Resilience Gaps — Single-NAT SPOF, No DR Testing, No DynamoDB PITR

| Field | Value |
|-------|-------|
| ID | GRC-012 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | C7, C8 (ECS services), C12 (autoscaling), D1 (DynamoDB); TB6 (VPC/NAT) |
| Scoring System | Qualitative |
| Score | MEDIUM (multi-AZ compute exists, but a single NAT SPOF, no backup/PITR, and no recovery testing undercut the Availability category) |
| Cross-Framework | SOC 2 A1.1, A1.2, A1.3 · NIST CP-9, CP-9(1), CP-10 · ISO A.8.13, A.8.14, A.5.30 |

**Description**: Compute is multi-AZ with autoscaling and blue/green rollback, but egress runs through a **single NAT gateway (one AZ)** — an availability single-point-of-failure — and there is **no DynamoDB point-in-time recovery (PITR)**, no backup strategy, and **no DR/recovery testing**. SOC 2 A1.2 (environmental protections/redundancy) is partial; A1.3 (test recovery procedures) is Not Implemented — blue/green auto-rollback is a *deploy*-level control, not a tested DR plan.

**Evidence**: recon §1.10 "Single NAT gateway (one AZ) — availability single-point"; §1.4 D1 "no PITR, no deletion protection"; §1.8 "single NAT is the redundancy gap"; §1.9/§1.8 no DR testing declared.

**Attack Scenario**: (availability) The single NAT's AZ fails → all task egress (image pulls, AWS API calls via public endpoints, logging) is disrupted with no automatic failover. A bad write/delete to DynamoDB is unrecoverable without PITR/backups.

**Existing Mitigations**: Multi-AZ ALBs and tasks; target-tracking autoscaling + CloudWatch alarms; CodeDeploy blue/green auto-rollback; DynamoDB `PAY_PER_REQUEST` (no capacity exhaustion).

**Recommendation**: Deploy one NAT gateway per AZ (or VPC endpoints to remove NAT dependence for AWS-service traffic); enable DynamoDB PITR and deletion protection; define + periodically test a documented recovery plan (A1.3, CP-10, CP-9(1)); add ICT-readiness-for-continuity testing (ISO A.5.30).

---

### LOW GRC-013: Insecure Data Disposal — `force_destroy` Buckets, No Lifecycle/Retention Policy

| Field | Value |
|-------|-------|
| ID | GRC-013 |
| Severity | LOW |
| Confidence | HIGH |
| Affected Component(s) | D2 (S3 assets), D3 (S3 artifacts) |
| Scoring System | Qualitative |
| Score | LOW (data-lifecycle/disposal hygiene; low impact given non-personal demo data) |
| Cross-Framework | SOC 2 CC6.5, C1.2 · NIST MP-6, SI-12 · ISO A.8.10 |

**Description**: Both S3 buckets set `force_destroy = true` (allows non-empty-bucket deletion) with no lifecycle, retention, or secure-disposal policy. SOC 2 CC6.5 (discontinue protections over disposed assets) / C1.2 (dispose of confidential information) and NIST MP-6 have no managed process; `force_destroy` is an anti-pattern that enables accidental/malicious bulk deletion.

**Evidence**: recon §1.4 D2/D3 "`force_destroy=true`"; §1.8 "force_destroy = true on both buckets."

**Attack Scenario**: A `terraform destroy` (accidental or via compromised operator, GRC-007) wipes both buckets including build artifacts with no versioning backstop (compounds GRC-009).

**Existing Mitigations**: `acl=private` on buckets; artifact bucket is pipeline-internal.

**Recommendation**: Remove `force_destroy` on production buckets; add S3 lifecycle + retention policies and object-lock/versioning where artifacts must be retained; define a documented media-sanitization/disposal procedure (MP-6, A.8.10).

---

### LOW GRC-014: Verbose Error Handling Leaks Internal Detail

| Field | Value |
|-------|-------|
| ID | GRC-014 |
| Severity | LOW |
| Confidence | HIGH |
| Affected Component(s) | C2 (Server API) |
| Scoring System | Qualitative |
| Score | LOW (information-disclosure hygiene; secure-development control gap) |
| Cross-Framework | SOC 2 CC8.1 · NIST SI-11 · ISO A.8.28 |

**Description**: The API error handler returns `{code, description: err.message}` to the client and `console.error`s the raw error. Because AWS SDK errors have no `.status`, `res.status(error.code)` can throw on an undefined status. This leaks internal error detail to clients and reflects the absence of secure-coding review (SOC 2 CC8.1 secure development, NIST SI-11 error handling).

**Evidence**: recon §1.8 "Error handling leaks detail: `app.js` error handler returns `{code, description: err.message}`... `res.status(error.code)` can throw"; `Code/server/src/app.js`.

**Attack Scenario**: An attacker triggers backend errors to enumerate internal behavior (table names, SDK internals) from returned messages, aiding further probing.

**Existing Mitigations**: Errors are also logged to CloudWatch via awslogs (visibility, though not sanitized).

**Recommendation**: Return generic client-facing error messages with a correlation id; log detail server-side only; guard `res.status()` against undefined codes (default 500); add secure-coding review to the SDLC (A.8.28) — overlaps GRC-006's build-gate remediation.

---

## Cross-Framework Control Mapping

> Verified against `cross-framework-mapping.md`. A single implementation produces evidence across all mapped cells. **N/A** cells for PCI/HIPAA reflect this system's scope (no cardholder data, no PHI) — the mapping-file equivalents are shown in parentheses for reference reuse if scope changes.

| Control Area | SOC 2 (TSC) | ISO 27001:2022 | NIST 800-53 Rev 5 | PCI-DSS v4.0 | HIPAA | System Status | Finding |
|---|---|---|---|---|---|:---:|:---:|
| Encryption in Transit | CC6.1, CC6.7 | A.8.24 | SC-8 | (4.2) N/A | (§164.312(e)(1)) N/A | Not Implemented | GRC-001 |
| Access Control | CC6.1 | A.5.15, A.8.3 | AC-2, AC-3 | (7.2, 7.3) N/A | (§164.312(a)(1)) N/A | Not Implemented | GRC-002 |
| Authentication | CC6.1, CC6.6 | A.8.5 | IA-2, IA-5 | (8.2, 8.3) N/A | (§164.312(d)) N/A | Not Implemented | GRC-002 |
| Least Privilege / IAM | CC6.1, CC6.3 | A.8.2, A.5.18 | AC-6 | (7.2) N/A | (§164.312(a)(1)) N/A | Not Implemented | GRC-003 |
| Logging & Monitoring | CC7.2, CC7.3 | A.8.15, A.8.16 | AU-2, AU-3, AU-6 | (10.2, 10.4) N/A | (§164.312(b)) N/A | Not Implemented | GRC-004 |
| Vulnerability Management | CC7.1 | A.8.8 | RA-5, SI-2 | (6.3, 11.3) N/A | N/A | Not Implemented | GRC-005 |
| Change Management | CC8.1 | A.8.32 | CM-3 | (6.5) N/A | N/A | Partial | GRC-006 |
| Key Management | CC6.1 | A.8.24 | SC-12 | (3.6, 3.7) N/A | N/A | Not Implemented | GRC-007 |
| Encryption at Rest | CC6.1, CC6.7 | A.8.24 | SC-28 | (3.5) N/A | (§164.312(a)(2)(iv)) N/A | Partial | GRC-009 |
| Network Security | CC6.1, CC6.6 | A.8.20, A.8.21, A.8.22 | SC-7 | (1.2, 1.3) N/A | (§164.312(e)(1)) N/A | Partial | GRC-010 |
| Third-Party Management | CC9.2 | A.5.19, A.5.20, A.5.21 | SA-9, SR-1 | (12.8, 12.9) N/A | (§164.308(b)(1)) N/A | Not Implemented | GRC-011 |
| Business Continuity | A1.1, A1.2 | A.5.29, A.5.30 | CP-1, CP-2, CP-4 | (12.10) N/A | (§164.308(a)(7)) N/A | Partial | GRC-012 |
| Backup & Recovery | A1.2 | A.8.13, A.8.14 | CP-9, CP-10 | N/A | (§164.308(a)(7)) N/A | Not Implemented | GRC-012 |
| Data Disposal | CC6.5 | A.8.10 | MP-6 | (3.1, 9.4) N/A | (§164.310(d)(2)) N/A | Not Implemented | GRC-013 |
| Risk Assessment | CC3.2, CC3.4 | Clause 6.1.2 † | RA-3 | (12.3.1) N/A | (§164.308(a)(1)(ii)(A)) N/A | Not Implemented | GRC-008 |
| Incident Response | CC7.4, CC7.5 | A.5.24-A.5.28 | IR-1, IR-4, IR-8 | (12.10) N/A | (§164.308(a)(6)) N/A | Not Implemented | GRC-008 |
| Security Awareness Training | CC1.4 | A.6.3 | AT-2, AT-3 | (12.6) N/A | (§164.308(a)(5)) N/A | Not Implemented | GRC-008 |

> **†** `Clause 6.1.2` is an ISO 27001 management-system clause (information security risk assessment), not an Annex A control — flagged as approximate in `cross-framework-mapping.md`. Verify against the primary standard before relying on it.

**Efficiency notes (evidence reuse):**
- **Turning on the AWS audit-evidence plane** (GRC-004: CloudTrail + ALB/VPC/access logs + Config) simultaneously produces evidence for **SOC 2 CC7.2/CC7.3, ISO A.8.15/A.8.16, and NIST AU-2/AU-6/SI-4** — one implementation, three frameworks. Highest evidence-per-effort item.
- **Adding TLS on the ALBs** (GRC-001) satisfies **SOC 2 CC6.7, ISO A.8.24, and NIST SC-8** at once, and pre-satisfies PCI 4.2 / HIPAA §164.312(e)(1) if scope ever changes.
- **SSE-KMS with a CMK** (GRC-009 + GRC-007 key management) covers **SOC 2 CC6.1, ISO A.8.24, NIST SC-28 and SC-12** together — encryption-at-rest and key-management rows share the implementation.
- **The governance program build** (GRC-008) is where cross-framework reuse is largest: one policy/risk/IR/training program produces evidence across the whole SOC 2 CC1-CC5/CC9 spine, ISO A.5/A.6, and the NIST -1/RA/IR/AT families.

---

## Risk Register

> Likelihood (L) × Impact (I) per the compliance-assessment Phase 5 rubric (1-5 each). Rating: Critical 17-25 · High 10-16 · Medium 5-9 · Low 1-4. Impact is calibrated to *compliance/audit + security* consequence for a production deployment (no active regulatory mandate today, so no cell reaches the regulatory-enforcement ceiling).

| Finding | Gap | L | I | Score | Rating | Treatment | Suggested Owner | Due |
|---------|-----|:-:|:-:|:-----:|:------:|-----------|-----------------|-----|
| GRC-004 | No security audit trail | 4 | 4 | 16 | High | Mitigate | DevOps / Platform | 0-30d |
| GRC-001 | No encryption in transit | 4 | 4 | 16 | High | Mitigate | Platform / DevOps | 0-30d |
| GRC-003 | IAM over-permissioning (`iam:PassRole *`) | 3 | 5 | 15 | High | Mitigate | Platform / Security | 0-30d |
| GRC-002 | No authN/authZ on app | 3 | 4 | 12 | High | Mitigate | App developers | 0-30d |
| GRC-005 | No vuln mgmt / image scanning / SCA | 4 | 3 | 12 | High | Mitigate | DevOps | 0-30d |
| GRC-006 | CI/CD no approval/test gate; privileged build | 3 | 4 | 12 | High | Mitigate | DevOps | 30-90d |
| GRC-007 | PAT in unencrypted local state, no rotation | 3 | 4 | 12 | High | Mitigate | DevOps / Security | 0-30d |
| GRC-008 | No governance program | 3 | 4 | 12 | High | Mitigate | Security lead / Mgmt | 30-180d |
| GRC-009 | Encryption at rest not hardened | 3 | 3 | 9 | Medium | Mitigate | Platform | 30-90d |
| GRC-010 | No WAF / rate limiting / DoS protection | 3 | 3 | 9 | Medium | Mitigate | Platform / Security | 30-90d |
| GRC-011 | Vendor risk unmanaged; EOL deps | 3 | 3 | 9 | Medium | Mitigate | Security / App devs | 90-180d |
| GRC-012 | Single-NAT SPOF, no DR test, no PITR | 2 | 4 | 8 | Medium | Mitigate | Platform | 90-180d |
| GRC-013 | Insecure data disposal (`force_destroy`) | 2 | 3 | 6 | Medium | Mitigate | Platform | 90-180d |
| GRC-014 | Verbose error handling leaks detail | 3 | 2 | 6 | Medium | Mitigate | App developers | 90-180d |

> Note: GRC-013/GRC-014 are LOW *severity* findings (audit-outcome impact) but land at Medium *risk score* (L×I) because they are plausible and non-trivial in blast radius; severity and risk-score are distinct axes per the two rubrics. Both are scheduled in the medium-term roadmap.

---

## Remediation Roadmap

### Immediate (0-30 days) — High Risk, high evidence-per-effort

| # | Finding | Framework(s) | Risk | Remediation | Owner | Est. Effort |
|---|---------|-------------|------|-------------|-------|-------------|
| 1 | GRC-004 | SOC2 CC7.2/7.3 · NIST AU-2/AU-6 · ISO A.8.15 | High | Enable CloudTrail (mgmt+data events) → encrypted S3; ALB access logs; VPC flow logs; AWS Config + GuardDuty; centralize + alert | DevOps/Platform | 2-4 days (Low complexity) |
| 2 | GRC-001 | SOC2 CC6.7 · NIST SC-8 · ISO A.8.24 | High | ACM cert + HTTPS:443 listener on both ALB modules; `enable_https=true`; HTTP→HTTPS redirect; TLS1.2+ policy; SPA/Swagger to `https` | Platform/DevOps | 2-3 days (Low) |
| 3 | GRC-003 | SOC2 CC6.3 · NIST AC-6 · ISO A.8.2 | High | Remove `iam:PassRole` from task role; scope DevOps role to ARNs + enumerated actions; add Access Analyzer + Config wildcard rules | Platform/Security | 3-5 days (Medium) |
| 4 | GRC-007 | SOC2 CC6.1 · NIST SC-12/IA-5 · ISO A.8.24 | High | Remote encrypted TF backend (S3+KMS+DynamoDB lock); replace PAT with CodeConnections/short-lived token in Secrets Manager + rotation | DevOps/Security | 2-4 days (Medium) |
| 5 | GRC-005 | SOC2 CC7.1 · NIST RA-5/SI-2 · ISO A.8.8 | High | ECR IMMUTABLE + scan_on_push; pin base images by digest; add SCA (Trivy/npm audit) + SBOM with fail-build gate in `buildspec.yml` | DevOps | 3-5 days (Medium) |
| 6 | GRC-002 | SOC2 CC6.1/6.2 · NIST IA-2/AC-3 · ISO A.8.5 | High | Add auth at edge (ALB OIDC/Cognito) or app JWT/session middleware + RBAC + MFA for privileged paths; restrict Swagger | App developers | 1-3 weeks (High) |

### Short-Term (30-90 days) — High & Medium Risk

| # | Finding | Framework(s) | Risk | Remediation | Owner | Est. Effort |
|---|---------|-------------|------|-------------|-------|-------------|
| 1 | GRC-006 | SOC2 CC8.1 · NIST CM-3/CM-5 · ISO A.8.32 | High | Manual approval stage + protected branch/required reviews + automated test/security gates; remove `privileged_mode`; upgrade build image | DevOps | 4-6 days (Medium) |
| 2 | GRC-009 | SOC2 CC6.1 · NIST SC-28/SC-12 · ISO A.8.24 | Medium | SSE-KMS CMK on S3/DynamoDB/ECR; S3 public-access-block (account+bucket); enable versioning | Platform | 3-4 days (Low) |
| 3 | GRC-010 | SOC2 CC6.6/A1.1 · NIST SC-5/SC-7 · ISO A.8.20 | Medium | AWS WAF (managed + rate-based rules) on both ALBs; tighten CORS allow-list; document capacity plan / raise autoscale ceiling | Platform/Security | 3-5 days (Medium) |

### Medium-Term (90-180 days) — Medium Risk & program build

| # | Finding | Framework(s) | Risk | Remediation | Owner | Est. Effort |
|---|---------|-------------|------|-------------|-------|-------------|
| 1 | GRC-008 | SOC2 CC1-CC5/CC9 · NIST PL-2/RA-3/IR-8/AT-2 · ISO A.5.1/A.5.24/A.6.3 | High | Assign security owner; author policy set; annual+change-triggered risk assessment; IR plan + test; access-review cadence; awareness training | Security lead/Mgmt | 3-6 months (High) |
| 2 | GRC-011 | SOC2 CC9.2 · NIST SR-3/SA-22 · ISO A.5.19/A.5.21 | Medium | Vendor inventory + risk tiering; collect supplier attestations; migrate off EOL aws-sdk v2 → v3, Vue 2 → Vue 3 | Security/App devs | 2-4 weeks + migration (Medium) |
| 3 | GRC-012 | SOC2 A1.2/A1.3 · NIST CP-9/CP-10 · ISO A.8.13/A.5.30 | Medium | NAT-per-AZ or VPC endpoints; DynamoDB PITR + deletion protection; documented + tested recovery plan | Platform | 1-2 weeks (Medium) |
| 4 | GRC-013 | SOC2 CC6.5 · NIST MP-6 · ISO A.8.10 | Medium | Remove `force_destroy` on prod buckets; lifecycle/retention + object-lock/versioning; disposal procedure | Platform | 1-2 days (Low) |
| 5 | GRC-014 | SOC2 CC8.1 · NIST SI-11 · ISO A.8.28 | Medium | Generic client errors + correlation id; server-side detail only; guard `res.status()`; add secure-coding review to SDLC | App developers | 1-2 days (Low) |

### Long-Term (180+ days) — Strategic

| # | Item | Framework(s) | Remediation | Owner | Est. Effort |
|---|------|-------------|-------------|-------|-------------|
| 1 | Pursue formal SOC 2 Type II | SOC 2 (all) | After 0-180d remediation, engage auditor; run 6-12 month observation period with continuous evidence collection | Security lead/Mgmt | 6-12 months |
| 2 | ISO 27001:2022 certification path (optional) | ISO 27001 | Stand up the ISMS management-system clauses (4-10) + Annex A SoA; leverage SOC 2 evidence reuse | Security lead | 9-18 months |

---

## Evidence Collection Guide

> What to collect per gap so a future SOC 2 Type II can be evidenced. Store in a version-controlled evidence repository (or GRC tool); collect at the cadence shown.

| Gap | Evidence to Collect | Format | Storage | Frequency |
|-----|--------------------|--------|---------|-----------|
| GRC-004 | CloudTrail config screenshot/Terraform; sample log export; Config conformance-pack report; GuardDuty findings | Config export + logs | Encrypted S3 + GRC tool | Continuous; review quarterly |
| GRC-001 | ALB listener config (HTTPS:443); ACM cert ARN; SSL Labs / testssl report | Config + scan report | Evidence repo | On change + quarterly |
| GRC-003 | IAM policy JSON (post-scoping); Access Analyzer findings; access-review sign-off | JSON + review log | GRC tool | Quarterly access review |
| GRC-002 | Auth config (OIDC/Cognito/JWT); RBAC matrix; MFA enforcement proof | Config + matrix | Evidence repo | On change + quarterly |
| GRC-005 | ECR scan results; SCA/SBOM report; base-image digest pins; patch log | Scan reports | Pipeline artifacts | Per build |
| GRC-006 | Pipeline approval-stage config; PR review records; test-gate results | Config + PR logs | Git + pipeline | Per deploy |
| GRC-007 | Remote backend config; Secrets Manager rotation config; token-rotation log | Config + logs | GRC tool | On rotation |
| GRC-008 | Signed policies; risk-assessment report; IR plan + test after-action; training completion records | PDFs/records | GRC tool | Annual + on change |
| GRC-009 | SSE-KMS config; public-access-block status; versioning status | Config export | Evidence repo | Quarterly |
| GRC-010 | WAF rule config + blocked-request metrics; CORS config | Config + metrics | Evidence repo | Quarterly |
| GRC-011 | Vendor register; supplier SOC 2 reports; dependency-version report | Register + reports | GRC tool | Annual + on onboarding |
| GRC-012 | NAT/VPC-endpoint config; PITR status; DR-test after-action report | Config + report | Evidence repo | Per DR test (≥annual) |

---

## Policy Gap Analysis

> Required policies for a SOC 2 Type II vs. what exists in the repo. **None currently exist** (recon §1.2 confirms no policy/threat-model/data-classification docs).

| Required Policy | Framework Reference | Exists? | Gap |
|-----------------|--------------------|:-------:|-----|
| Information Security Policy | SOC2 CC5.3 · ISO A.5.1 · NIST PL-2 | No | Author top-level ISP with management approval |
| Access Control Policy | SOC2 CC6.1/6.3 · ISO A.5.15 · NIST AC-1 | No | Define provisioning/deprovisioning/review + least privilege |
| Data Classification Policy | SOC2 CC2.1 · ISO A.5.12 · NIST RA-2 | Informal only | Formalize the INTERNAL/CONFIDENTIAL/RESTRICTED scheme used in recon §1.4 |
| Change Management Policy | SOC2 CC8.1 · ISO A.8.32 · NIST CM-3 | No | Document approval, testing, rollback (ties to GRC-006) |
| Incident Response Plan | SOC2 CC7.4/7.5 · ISO A.5.24 · NIST IR-8 | No | Author + test IR plan; define breach roles/timelines |
| Risk Assessment Process | SOC2 CC3.2 · ISO Clause 6.1.2 · NIST RA-3 | This TM (seed) | Formalize annual + change-triggered process |
| Vendor / Third-Party Risk Policy | SOC2 CC9.2 · ISO A.5.19 · NIST SR-1 | No | Vendor inventory, tiering, due diligence (ties to GRC-011) |
| Acceptable Use Policy | SOC2 CC1.1 · ISO A.5.10 | No | Author AUP |
| Security Awareness Training Program | SOC2 CC1.4 · ISO A.6.3 · NIST AT-2 | No | Stand up onboarding + annual training |
| Business Continuity / DR Plan | SOC2 A1.2/A1.3 · ISO A.5.30 · NIST CP-2 | No | Document + test (ties to GRC-012) |
| Cryptography / Key Management Policy | SOC2 CC6.1 · ISO A.8.24 · NIST SC-12 | No | Define TLS/at-rest/key-rotation standards (ties to GRC-001/007/009) |

---

## Audit Readiness Assessment

**Readiness score: ~15% (Not Ready for a SOC 2 Type II).** The system is a demo, not a candidate for audit as-is.

**Blockers (must clear before an audit is viable):**
1. **No audit-evidence plane** (GRC-004) — a Type II samples evidence over a 6-12 month window; there is nothing to sample. This is blocker #1.
2. **No governance program** (GRC-008) — no policies, risk assessment, IR, access reviews, or training. The organizational half of SOC 2 is empty.
3. **Core technical control failures** (GRC-001 TLS, GRC-002 auth, GRC-003 IAM) — foundational CC6 criteria unmet.

**High-risk areas:** logical access (CC6), system operations/monitoring (CC7), change management (CC8), the entire control environment (CC1-CC5).

**Prep tasks (in order):** (1) enable logging/CloudTrail/Config (GRC-004); (2) close transport + IAM + secrets gaps (GRC-001/003/007); (3) add auth + vuln scanning + change gates (GRC-002/005/006); (4) build the governance program and start the observation window (GRC-008); (5) collect evidence continuously per the Evidence Collection Guide; (6) engage an auditor for readiness assessment, then the Type II observation period.

**Evidence readiness checklist (currently all ✗ except where noted):** InfoSec policy ✗ · risk assessment (this TM = partial seed) · access reviews ✗ · CloudTrail/audit logs ✗ · encryption in transit ✗ · IAM least-privilege evidence ✗ · vulnerability scan results ✗ · change-approval records ✗ · IR plan + test ✗ · vendor register ✗ · DR test ✗ · training records ✗.

---

## Observations (Positive)

- **Sound network segmentation** — tasks in private subnets reachable only from their ALB SG; ALBs in public subnets; NAT for egress (partial CC6.6, ISO A.8.22). Good bones for CC6.6 once WAF/TLS are added.
- **Multi-AZ + autoscaling + blue/green rollback** — a real availability/resilience foundation (partial A1.1/A1.2; CC8.1 mechanics exist), just missing DR testing and single-NAT redundancy.
- **IAM role separation** (execution vs task vs devops vs codedeploy) and **resource-scoped DynamoDB/S3 actions** — the least-privilege *pattern* is present even though the wildcards break it.
- **Default encryption at rest** on all AWS stores and **AWS-managed TLS** for task→service calls — the baseline is on; it just needs CMK control and public-plane TLS.
- **Clean secrets hygiene in the tree** — no committed keys/certs/passwords; the sole credential (PAT) is a `sensitive` variable, not a committed secret (recon §1.3).
- **Fargate** removes host/OS patching from scope (reduces CC7.1/SI-2 surface vs. self-managed EC2).

---

## Assumptions & Limitations

### Assumptions
- **No compliance regime is formally in scope.** Per the task framing and recon (`has_regulatory=false`, `has_personal_data=false`), SOC 2 and CIS AWS/cloud baselines are assessed as the *most relevant reference frameworks* for the AWS control surface, with gaps framed as production-readiness needs — not as active regulatory violations.
- Assessment is grounded in `01-reconnaissance.md` and `02-structural-diagram.md` (per skill guidance to reuse recon rather than re-scan); file paths/config values cited are as reported there.
- AWS-managed physical/environmental controls are assumed covered under the shared-responsibility model (AWS's own SOC 2/ISO reports) — CC6.4 marked N/A on that basis.
- Code in the reviewed tree represents the intended deployment (no separate prod branch was available).

### Limitations
- **Static analysis only** — no runtime testing, no live AWS account inspection; a real deployment's console settings (e.g., account-level CloudTrail/Config that aren't in this IaC) could change some statuses.
- **CIS AWS Foundations Benchmark numeric IDs are not in the curated reference set** (`references/` covers SOC 2, ISO 27001, NIST 800-53, PCI-DSS, HIPAA). To avoid citing unverifiable IDs, CIS/cloud checks are described by their technical intent and anchored to the *verified* SOC 2 / NIST / ISO equivalents rather than to CIS control numbers.
- **ISO 27001 and NIST 800-53 are cross-mapped, not independently scored.** A full ISO Annex A (93-control) or NIST moderate-baseline pass, and the ISO management-system clauses, were out of scope; only the mapped equivalences to scored SOC 2/CIS findings are asserted.
- **Organizational controls assessed as absent from evidence, not from interview** — CC1-CC5/CC9 findings reflect the absence of policy/program artifacts in the repo; a real org might hold these outside the codebase.
- Privacy (GDPR/CCPA) is owned by the privacy-specialist and not re-assessed here.

### Out of Scope
- PCI-DSS and HIPAA control-by-control assessment (both Not Applicable — no cardholder data, no PHI).
- Penetration testing, runtime configuration audit, and interview-based control effectiveness.

---

## Cross-References

- **Reconnaissance**: `01-reconnaissance.md` — §1.4 asset inventory (D1-D6), §1.5 actors/roles (R0-R5), §1.8 security control inventory (authoritative), §1.10 coverage seed.
- **Structural diagram**: `02-structural-diagram.md` — L1 architecture (C1-C13, D1-D6), L2 trust & identity (TB1-TB6, R1-R4), L3 data/encryption (`[PLAIN]`/`[ENC]` split).
- **Related specialist outputs** (expected): threat-model findings (TM-*) overlap on GRC-001 (TLS), GRC-003 (IAM `iam:PassRole *`), GRC-006 (CI/CD), GRC-004 (logging); code-review findings (CR-*) overlap on GRC-014 (error handling), GRC-005 (deps); privacy (PA-*) — no overlap (no personal data).
- **Framework references used (all IDs verified)**: `soc2-trust-services-criteria.md`, `nist-800-53-controls.md`, `iso27001-annex-a-controls.md`, `cross-framework-mapping.md`. PCI/HIPAA references consulted only to confirm Not-Applicable scoping.
- **Coverage ledger**: `coverage.json` — compliance-governance domain items updated below for the validation-specialist to merge.

---

## Coverage States

> Compliance-and-governance domain (taxonomy section 33). These four items were seeded `not-applicable` in `coverage.json` under `has_regulatory=false`. Having now assessed the AWS control surface against SOC 2 + CIS AWS/cloud baselines per the task framing, they are updated to reflect the assessed posture. States use the taxonomy vocabulary (`present`/`partial`/`absent`/`not-applicable`/`unknown`). The validation-specialist should merge these over the seed values.

| Item id | State | Detail / Note | Source |
|---------|-------|---------------|--------|
| compliance-governance.applicable-frameworks | partial | No regime is legally/contractually mandated (MIT-0 demo, no PII/PHI/PCI). Relevant reference baselines identified and assessed: SOC 2 Type II (primary) + CIS AWS Foundations/cloud-security; ISO 27001 & NIST 800-53 cross-mapped; PCI-DSS & HIPAA confirmed N/A. Applicability is now answered, but the system has no documented compliance scope/program of its own. | This report §Scope; recon §1.10 `has_regulatory=false` |
| compliance-governance.control-mapping | partial | A verified SOC2↔ISO↔NIST control mapping and per-control gap analysis were produced here (17-row cross-framework table; 36 SOC 2 criteria scored ≈15.7%). The system itself evidences few of the mapped controls and has no formal, audited control-to-feature mapping. | This report §Cross-Framework Mapping, §Dashboard; GRC-001..014 |
| compliance-governance.policy-ownership | absent | No security/privacy policy set, no assigned security/compliance owner (recon: no TM owner), and no risk-acceptance or exception-approval process exist. Governance spine (SOC 2 CC1-CC5) is unimplemented. | GRC-008; recon §1.2, §1.10 `document-metadata.ownership: partial` |
| compliance-governance.regulatory-reporting | absent | No breach-notification or regulatory-reporting process, and no incident-response plan; the missing audit-evidence plane (GRC-004) means a breach could not even be detected or scoped. No mandated reporting obligation applies to the current demo data, but the capability is entirely absent for any production/regulated use. | GRC-004, GRC-008; recon §1.8 |

---

## Execution Log

### Process Health
| Metric | Value |
|--------|-------|
| Files Read | 11 (01-reconnaissance.md, 02-structural-diagram.md, agent-output-protocol.md, compliance SKILL.md, soc2/nist/iso/cross-framework/gap-template/checklists reference files, coverage.json, coverage-taxonomy.json) |
| Files Written | 1 (compliance-gap-analysis.md) |
| Errors Encountered | 0 |
| Items Skipped | 0 |
| Self-Assessed Output Quality | HIGH |

### What Went Well
- Reconnaissance (§1.8 security control inventory) and the L2/L3 structural diagrams were thorough and directly mappable to control domains — every finding traces to a specific recon line + Phase 2 node id, so no re-scan of the codebase was needed.
- All cited SOC 2, NIST 800-53, and ISO 27001 control IDs were verified against the reference files before use; the cross-framework table was lifted from the verified `cross-framework-mapping.md` (including its `†` approximation flags).
- Clean framework scoping: PCI/HIPAA/privacy dispositioned as N/A with concrete rationale, avoiding template padding.

### Issues Encountered
- **CIS AWS Foundations Benchmark is not in the curated reference set.** Rather than cite unverifiable CIS numeric IDs, CIS/cloud checks are described by intent and anchored to verified SOC 2/NIST/ISO equivalents. Documented in Limitations. No impact on grounding.
- The four compliance-governance ledger items were seeded `not-applicable` (has_regulatory=false). Per the task framing (assess against SOC 2/CIS anyway), I updated them to assessed states (partial/absent) in Coverage States for the validation-specialist to merge — a deliberate override of the seed, noted with rationale.

### What Was Skipped or Incomplete
- ISO 27001 and NIST 800-53 were cross-mapped, not independently scored (would require full Annex A / moderate-baseline passes + ISO management-system clauses — out of scope). Only SOC 2 and the CIS/cloud technical checklist are scored in the dashboard; noted in Limitations.
- No runtime/live-account inspection — account-level AWS settings not expressed in the reviewed IaC (e.g., an org-wide CloudTrail) can't be confirmed or refuted; GRC-004 assumes the IaC is the source of truth.

### Assumptions Made
- Treated `01-reconnaissance.md` file paths/config values (e.g., `IAM/main.tf:175,306`, `ALB/main.tf:38`) as accurate without re-opening source, per skill guidance to reuse recon.
- Scoped SOC 2 to Common Criteria + Availability (36 criteria), treating Confidentiality/Processing Integrity/Privacy categories as not-in-scope-for-this-engagement (Confidentiality partially relevant to build artifacts, but not separately scored to avoid inflating the denominator).
- Calibrated qualitative severity so nothing is CRITICAL (no active regulatory mandate); "audit-blocking for a real SOC 2" gaps are HIGH.
