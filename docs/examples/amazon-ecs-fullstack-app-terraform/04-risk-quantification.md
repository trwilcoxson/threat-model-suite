# Security Architect — Phase 4 Risk Quantification

## Metadata
| Field | Value |
|-------|-------|
| Agent | security-architect (generative pass, Phases 3-5) |
| Phase | 4 (Risk Quantification — PASTA Stages 6-7, OWASP Risk Rating) |
| Date | 2026-07-11 |
| Inputs | 03-threat-identification.md; Phase 1 §1.6 threat-actor profiles (TA1-TA5), §1.7 attack surface, §1.8 control inventory |
| Scoring | Risk = Likelihood (1-5) × Impact (1-5); bands LOW 1-4 / MEDIUM 5-9 / HIGH 10-16 / CRITICAL 17-25 (frameworks.md) |

## Scoring Approach & Context Anchors
- **Likelihood** derives from PASTA Stage 6 (attack modeling): attacker capability (TA1-TA5, capability 2-4), preconditions, and which Phase 1 controls must be bypassed. Anonymous+plaintext+no-WAF endpoints skew likelihood **up**; anything gated behind an initial container/credential foothold skews it **down**.
- **Impact** derives from PASTA Stage 7 across financial/operational/reputational/regulatory; the **highest** dimension is the score. The dominant anchor: **the system processes no personal or regulated data** (product catalog id/path/title, INTERNAL). That caps confidentiality-driven impact — exposing a public storefront catalog is intrinsically low-impact. Impact rises where a threat yields **production code execution, cloud-account privilege escalation, availability/cost damage, or supply-chain control**, not mere data read.
- **Consequence of the anchors:** individual findings top out at **HIGH**; there is **no single CRITICAL finding**, because the maximal-likelihood findings have low data-impact and the maximal-impact findings each require a foothold (moderate likelihood). This is deliberate and honest — the CRITICAL-grade risk in this system is *composite* (multi-step kill chains), which Phase 5 declares.

## Threat Actor Reference (from Phase 1 §1.6)
| ID | Actor | Cap. | Primary relevance |
|----|-------|:---:|-------------------|
| TA1 | Opportunistic unauthenticated Internet attacker | 2 | Anonymous, plaintext, public endpoints |
| TA2 | Automated bot / botnet | 2 | No WAF/rate limit; cost & availability |
| TA3 | Malicious insider / compromised developer | 4 | `main` push → auto-deploy; PAT + local state |
| TA4 | Compromised upstream dependency / base image | 3 | Unpinned/unscanned supply chain; privileged build |
| TA5 | Post-exploitation attacker inside an ECS task | 4 | IMDS + task role `PassRole *`; open egress |

---

## Scored Threat Table

| TM ID | Title | Actor(s) | Attack Path Summary (PASTA St.6) | L | I | Risk | Band |
|-------|-------|----------|----------------------------------|:-:|:-:|:----:|------|
| **TM-001** | No authN/authZ on any endpoint | TA1, TA2 | `curl http://<server-alb>/api/getAllProducts` — no credential, no control to bypass. Entry E2. | 5 | 2 | **10** | HIGH |
| **TM-002** | Cleartext HTTP, no TLS | TA1 | On-path position (rogue AP / ISP / transit) on E1/E2 → read + inject modified HTTP response into victim's SPA. Bypasses: none (no TLS/HSTS). | 3 | 3 | **9** | MEDIUM |
| **TM-003** | Swagger publicly reachable | TA1, TA2 | GET `/api/docs` (URL is in the TF output) → full API contract for enumeration. Entry E3. | 4 | 2 | **8** | MEDIUM |
| **TM-004** | No WAF / rate limiting (L7 DoS, scraping) | TA2 | Flood/scrape E1/E2 from one or many hosts; autoscaling caps at 4 tasks then saturates. Bypasses: none. | 4 | 3 | **12** | HIGH |
| **TM-005** | Unauth full-table scan → cost/economic DoS | TA2, TA1 | Loop E2 → each call = full DynamoDB `scan` on `PAY_PER_REQUEST` → unbounded RCU + transfer billing and task saturation. Bypasses: none (no auth TM-001, no rate limit TM-004). | 4 | 3 | **12** | HIGH |
| **TM-006** | Permissive CORS | TA1 | Host a page that `fetch`es the API from a visitor's browser and reads the response. Impact bounded — no cookies/creds, data already public. | 3 | 1 | **3** | LOW |
| **TM-007** | Error-message disclosure | TA1 | Induce a backend error (throttle/permission/timeout) → `err.message` returned to client leaks internal detail (table/region/ARNs). Entry E2. | 3 | 2 | **6** | MEDIUM |
| **TM-008** | Fragile error handling (unhandled throw) | TA1, TA2 | Drive the SDK error path so `res.status(undefined)` throws in-handler; per-request failure, brittle degradation. | 2 | 2 | **4** | LOW |
| **TM-009** | Implicit network trust (zero-trust gap) | TA1, TA5 | Any actor routable to the task (public ALB, SSRF, in-VPC workload) is trusted with no per-request auth. Bypasses: only source-SG (already Internet-fed). | 3 | 2 | **6** | MEDIUM |
| **TM-010** | Task role `iam:PassRole *` | TA5 | Precondition: container compromise (→ task role). Then pass an arbitrary role to a reachable service action → escalate. Bypasses: none once role held. | 2 | 4 | **8** | MEDIUM |
| **TM-011** | IMDS task-credential theft → cloud pivot | TA5, TA4 | Precondition: container RCE (TM-018 dep). Read IMDS → task-role creds → use off-box (D1/D2/AWS) via open egress (TM-020). | 2 | 4 | **8** | MEDIUM |
| **TM-012** | GitHub PAT in local state + pipeline config | TA3 | Steal PAT from unencrypted `terraform.tfstate` (workstation) or pipeline config (via DevOps role) → repo write. Bypasses: local file perms only. | 3 | 4 | **12** | HIGH |
| **TM-013** | `main`-push auto-deploy, no approval gate | TA3 | Push/merge to `main` (dev access or stolen PAT) → auto build + blue/green deploy of arbitrary code to prod. Bypasses: none (no review/approval). | 3 | 5 | **15** | HIGH |
| **TM-014** | Default encryption only; no PAB/versioning; `force_destroy` | TA5, TA3 | Exploiting the key gap needs account/key-plane access; the versioning/`force_destroy` gap removes the recovery net for tamper/delete. | 2 | 3 | **6** | MEDIUM |
| **TM-015** | Privileged CodeBuild (Docker-in-Docker) RCE | TA4, TA3 | Code running at build (malicious dep/base image/source) → privileged Docker + build IAM identity → escape & lateral. Entry: build stage. | 3 | 5 | **15** | HIGH |
| **TM-016** | DevOps role wildcards (`s3:*`/`ecs:*`/`PassRole *`) | TA3, TA4 | Precondition: compromise the pipeline/build identity (TM-015). Then `ecs:RegisterTaskDefinition` + `PassRole *` + `ecs:RunTask` → run any role; `s3:*` account-wide. | 2 | 5 | **10** | HIGH |
| **TM-017** | Mutable ECR tags + no scan-on-push | TA3, TA4 | With ECR push (DevOps role or pipeline) overwrite deployed tag / `:latest`; next task start/scale silently pulls attacker image. No digest pin to detect. | 3 | 4 | **12** | HIGH |
| **TM-018** | Unpinned `:latest` base + no SCA/SBOM + EOL deps | TA4 | Poison/compromise an upstream `:latest` tag or exploit a known CVE in Vue 2 / aws-sdk v2; lands in prod unscanned. Bypasses: none (no scan gate). | 3 | 4 | **12** | HIGH |
| **TM-019** | Deploy-artifact / taskdef tampering | TA3, TA4 | Influence build env or artifact bucket (DevOps `s3:*`) → alter `taskdef.json` (inject `taskRoleArn`) / `appspec.yaml` → deploy attacker role/container. | 2 | 4 | **8** | MEDIUM |
| **TM-020** | Unrestricted egress → exfil & C2 | TA5 | Precondition: container compromise. Open outbound (SG `-1`, NAT `0.0.0.0/0`) → exfiltrate data / reach C2. Bypasses: none (no egress filter/DNS control). | 2 | 3 | **6** | MEDIUM |
| **TM-021** | No ALB/flow/CloudTrail logging → no detection/attribution | TA1-TA5 | Not an intrusion step — the *absence* lets every other attack run undetected and unattributable; total repudiation for pipeline/deploy actions. | 4 | 3 | **12** | HIGH |
| **TM-022** | Sensitive data in logs + short retention | TA5, TA3 | Read CloudWatch logs (needs log-read access) for internal detail; 30-day window limits forensics. Low-sensitivity today. | 2 | 2 | **4** | LOW |
| **TM-023** | Missing client security headers / CSP | TA1 | Frame the SPA (clickjacking) or, with TM-002, run an injected script under no CSP. Defense-in-depth gap; no direct sink today (Vue escapes). | 2 | 2 | **4** | LOW |
| **TM-024** | TF state no backend/locking (integrity + inventory) | TA3 | Corrupt state via concurrent/interrupted apply (no lock), or read full inventory from the unencrypted local file. Distinct from PAT secrecy. | 2 | 3 | **6** | MEDIUM |
| **TM-025** | Single NAT gateway (egress SPOF) | TA2 (or non-adversarial) | AZ/NAT failure (or targeted NAT exhaustion) breaks all task→AWS-service calls; API fails despite surviving ALB/second-AZ tasks. | 2 | 3 | **6** | MEDIUM |

---

## Per-Finding Justifications (Likelihood + Impact rationale)

Only the non-obvious scores are expanded; the table's attack-path column carries the rest.

- **TM-001 (L5/I2=HIGH):** L=5 — literally `curl`, no skill/access needed (TA1). I=2 — the exposed data is a public product catalog (INTERNAL, non-personal); direct confidentiality impact is low. Rated HIGH because "missing authentication for critical function" is the categorical root enabler (it multiplies TM-004/005 and any future privileged route); the impact is honestly capped at 2 by the data class.
- **TM-004 / TM-005 (L4/I3=HIGH):** L=4 — automatable with common tools, few preconditions (TA2). I=3 — driving dimension is **operational/financial**: partial-to-full API outage within the 4-task ceiling, plus real DynamoDB `PAY_PER_REQUEST` spend; contained (a demo, no SLA) but non-trivial. Not I=4 because there is no revenue-critical SLA to breach.
- **TM-012 (L3/I4=HIGH):** L=3 — requires workstation access or DevOps-role read of pipeline config; plausible for TA3, not trivial for an external. I=4 — PAT = repository write = supply-chain foothold to production (TM-013), high integrity impact, bounded to this repo's blast radius.
- **TM-013 / TM-015 (L3/I5=HIGH, top of set):** I=5 — **arbitrary code execution in production** (deploy path) / **privileged build with account IAM** — full integrity+availability compromise of the running system and a route to account takeover. L=3 — needs privileged push (TA3) or a build-time code-exec primitive (TA4); credible but not anonymous. L×I=15, the highest individual risk; short of CRITICAL only because the trigger is gated behind privileged access / a supply-chain event.
- **TM-016 (L2/I5=HIGH):** I=5 — `ecs:*` + `iam:PassRole *` is a textbook complete privilege-escalation combo (register+run a task under any role) → account-wide. L=2 — the identity is only assumable after compromising the pipeline/build (TM-015), so likelihood is gated.
- **TM-017 / TM-018 (L3/I4=HIGH):** I=4 — attacker image/dependency runs in production with the task role and open egress. L=3 — a poisoned upstream `:latest`/known-CVE dependency, or an ECR overwrite via the over-broad DevOps role, is a realistic supply-chain event given zero scanning.
- **TM-021 (L4/I3=HIGH):** Scored as a control gap: L=4 reflects that operating undetected is essentially guaranteed (no logs exist to catch it); I=3 reflects the operational/regulatory cost of blind incident response and total non-repudiation, not a direct breach. This is the amplifier under every kill chain.
- **TM-010 / TM-011 / TM-019 / TM-020 (MEDIUM, I=4 or 3, L=2):** all gated behind an initial foothold (container compromise or pipeline access), so L=2; impact is high-ish (cloud pivot / arbitrary role / exfil) but each is one link in a chain rather than a standalone breach. Phase 5 composes them.
- **LOW set (TM-006, TM-008, TM-022, TM-023):** genuine but low-consequence given no personal data, no credentials in flows, and Vue's default escaping; retained for completeness and defense-in-depth, not inflated.

## Severity Distribution (Phase 3 findings only)
| Band | Count | Threat IDs |
|------|:-----:|-----------|
| CRITICAL (17-25) | 0 | — |
| HIGH (10-16) | 10 | TM-001, TM-004, TM-005, TM-012, TM-013, TM-015, TM-016, TM-017, TM-018, TM-021 |
| MEDIUM (5-9) | 11 | TM-002, TM-003, TM-007, TM-009, TM-010, TM-011, TM-014, TM-019, TM-020, TM-024, TM-025 |
| LOW (1-4) | 4 | TM-006, TM-008, TM-022, TM-023 |
| **Total (Phase 3)** | **25** | TM-001 – TM-025 |

Phase 5 adds TM-026 and TM-027, both MEDIUM → **assessment running totals: CRITICAL 0 / HIGH 10 / MEDIUM 13 / LOW 4 = 27** (see Phase 5).

## Consistency Check
- Similar threats scored consistently: the two anonymous-abuse DoS findings (TM-004, TM-005) both L4/I3=12; the two "gated behind pipeline compromise, account-wide impact" findings (TM-016 I5, TM-019 I4) differ only on reachability of the escalation, as intended; the two supply-chain-integrity findings (TM-017, TM-018) both L3/I4=12.
- No CRITICAL was down-graded — none reached 17; the composite CRITICAL-grade risk is captured as kill chains in Phase 5, not by inflating a single finding.
- Every score references a Phase 1 actor and the specific Phase 1 controls (or their absence) that gate the attack path.

**Handoff:** the fresh-context Phase 6 pass validates every score against evidence and existing controls; do not treat these as final. Phase 5 (next) adds TM-026, TM-027 with full scoring and declares the kill chains.
