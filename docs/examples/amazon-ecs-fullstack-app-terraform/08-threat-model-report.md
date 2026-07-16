# Threat Model Summary — AWS ECS Fullstack App (Terraform Demo)

## Metadata
| Field | Value |
|-------|-------|
| Agent | security-architect — Phase 8 summary (independent Phase 6+8 validation pass) |
| Date | 2026-07-11 |
| Methodology | STRIDE-LM + PASTA (attack simulation) + OWASP-inspired Risk Rating (L×I) |
| Findings source | 25 validated findings (`06-validated-findings.md`, `findings.json`) — 27 source findings, 2 merged, 0 rejected |
| Note | This is the lightweight analytical summary. The full consolidated report (all sections, diagrams, cross-refs) is produced separately by the report-analyst. |

---

## 1. Executive Summary

**Overall security posture: CONCERNING.** As built, the system defaults to *open* on every axis — no authentication or authorization anywhere, both public ALBs are HTTP-only (TLS listener present but disabled by default), CORS reflects any origin, egress is unrestricted, and there is no WAF, no image/dependency scanning, and no security logging. The one material mitigant is the data class: the only data processed is a **non-personal product catalog** (id/path/title, INTERNAL), which caps confidentiality-driven impact and keeps every *individual* finding at or below HIGH. The genuinely CRITICAL-grade risk is **composite**: a CI/CD compromise chain (KC03) runs from a stolen PAT or a poisoned dependency, through a no-approval auto-deploy and a privileged build, to account-wide privilege escalation — undetected end to end. This posture would be **CRITICAL** for any production system holding real or personal data; it is rated CONCERNING here strictly because of the demo's non-personal scope.

**Threats by severity (25 validated findings):**

| CRITICAL | HIGH | MEDIUM | LOW |
|:--------:|:----:|:------:|:---:|
| 0 (composite CRITICAL = KC03) | 10 | 11 | 4 |

**Top 3 risks:**
1. **KC03 — CI/CD → production RCE → cloud account (composite CRITICAL).** A stolen GitHub PAT (TM-012) or a poisoned `:latest`/EOL dependency (TM-018) auto-deploys with no approval gate (TM-013) into a privileged build (TM-015), then escalates via the DevOps role's `RegisterTaskDefinition`+`RunTask`+`PassRole *` (TM-016) to account-wide control. *Business impact: full compromise of the running application and the AWS account, with no audit trail to detect or attribute it.*
2. **KC01 — Anonymous economic/availability denial (HIGH).** No auth (TM-001) + no rate limit (TM-004) + a full-table DynamoDB scan per request on `PAY_PER_REQUEST` (TM-005) lets a trivial script drive unbounded AWS spend and saturate the 4-task ceiling. *Business impact: direct financial loss and API outage from an unauthenticated attacker.*
3. **Arbitrary code execution in production (TM-013 / TM-015, individual HIGH, I=5).** The no-approval pipeline and privileged Docker-in-Docker build each independently allow attacker code to reach production with the build's IAM identity. *Business impact: integrity/availability compromise of the deployed system and a route to account takeover.*

**Key strengths observed (genuine, credited):**
- **Network segmentation** — tasks in private subnets, reachable only via their ALB security group (SG chaining); NAT for egress.
- **Resilience primitives** — multi-AZ ALBs and tasks, target-tracking autoscaling, CodeDeploy blue/green with auto-rollback on failure.
- **Partial IAM discipline** — role separation (execution/task/devops/codedeploy); the task role's DynamoDB and S3 *data* actions are scoped to specific resource ARNs (the `PassRole *` is the outlier, not the norm).
- **Small, injection-free surface** — 3 parameterless routes, no user-controlled input reaching any query/command/template sink (traced negative result).
- **Clean secret hygiene in the tree** — no committed keys/tokens; the single PAT is a `sensitive` variable (its *storage in local state* is the issue, not a committed secret).
- **Non-personal data** — no PII/PHI/financial data, which genuinely bounds breach impact.

---

## 2. Validated Findings Summary Table

Severity = OWASP band of L×I. Confidence per Phase 6 (HIGH = confirmed by code/config; MEDIUM = plausible, some assumptions; LOW = theoretical).

| ID | Threat | Severity | STRIDE-LM | L | I | Risk | Conf. | Affected component(s) |
|----|--------|----------|-----------|:-:|:-:|:----:|-------|-----------------------|
| TM-013 | main-push auto-deploy, no approval gate | HIGH | T,E,LM | 3 | 5 | 15 | HIGH | C9, C11 (pipeline/deploy) |
| TM-015 | Privileged CodeBuild (DinD) build-time RCE | HIGH | E,LM | 3 | 5 | 15 | HIGH | C10 (CodeBuild) |
| TM-004 | No WAF / rate limiting (L7 DoS, scraping) | HIGH | D | 4 | 3 | 12 | HIGH | C4, C5, C12 |
| TM-005 | Unauth full-table scan → cost/economic DoS | HIGH | D | 4 | 3 | 12 | HIGH | C2, C5, D1 |
| TM-012 | GitHub PAT plaintext in local state + no rotation | HIGH | S,I,E | 3 | 4 | 12 | HIGH | C9, D6 |
| TM-017 | Mutable ECR tags + no scan-on-push | HIGH | T,LM | 3 | 4 | 12 | HIGH | D4, C10, C6 |
| TM-018 | Unpinned `:latest` base + no SCA/SBOM + EOL deps | HIGH | T | 3 | 4 | 12 | HIGH | C10 (X2/X3/X4) |
| TM-021 | No ALB/flow/CloudTrail logging → no detection | HIGH | R | 4 | 3 | 12 | MEDIUM | D5 (all flows) |
| TM-001 | No authN/authZ on any endpoint (+ zero-trust) | HIGH | S,E,LM | 5 | 2 | 10 | HIGH | C2, C3, C5, C7, C8 |
| TM-016 | Over-permissioned DevOps role + PassRole * | HIGH | E,LM | 2 | 5 | 10 | HIGH | C9, C10 (R3) |
| TM-002 | Cleartext HTTP, no TLS (intercept + inject) | MEDIUM | T,I | 3 | 3 | 9 | HIGH | C4, C5 |
| TM-003 | Swagger publicly reachable | MEDIUM | I | 4 | 2 | 8 | HIGH | C3 |
| TM-010 | Task role `iam:PassRole *` | MEDIUM | E,LM | 2 | 4 | 8 | HIGH | C8 (R2) |
| TM-011 | IMDS task-credential theft → cloud pivot | MEDIUM | I,E,LM | 2 | 4 | 8 | MEDIUM | C8 (R2) |
| TM-019 | Deploy-artifact / taskdef tampering | MEDIUM | T,E | 2 | 4 | 8 | MEDIUM | C10, C11, D3 |
| TM-007 | Error-message information disclosure | MEDIUM | I | 3 | 2 | 6 | HIGH | C2 |
| TM-014 | Default encryption only; no PAB/versioning | MEDIUM | I,T | 2 | 3 | 6 | HIGH | D1, D2, D3, D4 |
| TM-020 | Unrestricted egress → exfil & C2 | MEDIUM | I,LM | 2 | 3 | 6 | HIGH | C8 (TB6) |
| TM-024 | TF state no backend/locking (integrity+inventory) | MEDIUM | T,I | 2 | 3 | 6 | HIGH | D6 |
| TM-025 | Single NAT gateway (egress SPOF, cascades) | MEDIUM | D | 2 | 3 | 6 | HIGH | C8, C12 (TB6) |
| TM-026 | S3 destruction/ransom (overwrite + force_destroy) | MEDIUM | T,D | 2 | 3 | 6 | MEDIUM | D2, D3 |
| TM-006 | Permissive CORS | LOW | S,I | 3 | 1 | 3 | MEDIUM | C2 |
| TM-008 | Fragile error handling on API error path | LOW | D | 2 | 2 | 4 | LOW | C2 |
| TM-022 | Sensitive data in logs + short retention | LOW | I,R | 2 | 2 | 4 | MEDIUM | C2, D5 |
| TM-023 | Missing client security headers / CSP | LOW | T,I | 2 | 2 | 4 | HIGH | C1, C7 |

*Merged (dispositioned, not dropped): **TM-009**→TM-001 (no independent attack path — same CWE-306 root, no SSRF/2nd-workload surface); **TM-027**→TM-012 (same PAT asset — lifecycle facet with a unified remediation). Full rationale in `06-validated-findings.md` §2.*

**Kill chains** (declared in `findings.json` as KC01–KC04): KC01 anonymous economic/availability denial (TM-003→001→004→005); KC02 on-path content injection (TM-002→023); **KC03 CI/CD→prod→account, composite CRITICAL** (TM-012→018→013→015→017→019→016); KC04 container foothold→cloud priv-esc/exfil (TM-018→011→010→020). TM-021 (no detection) is the cross-cutting amplifier under all four.

---

## 3. Remediation Priority List

Dependency notation: `R-a → R-b` means R-b builds on R-a. ⚡ = quick win (high leverage, low effort, no dependency).

### Wave 1 — Quick wins (immediate, low effort)
| R-ID | Title | Addresses | Effort | Notes |
|------|-------|-----------|--------|-------|
| R-01 ⚡ | Delete `iam:PassRole *` from the ECS **task** role | TM-010 | LOW | One-statement removal; the app does not need it. Shrinks KC04. |
| R-02 ⚡ | Enable TLS: `enable_https=true` + ACM cert + HTTP→HTTPS 301 + HSTS | TM-002, (TM-023 HSTS) | LOW | HTTPS listener already exists in the module — flip the flag + cert. |
| R-03 ⚡ | Restrict CORS to an explicit origin allowlist | TM-006 | LOW | — |
| R-04 ⚡ | Harden error handling (generic client errors + correlation id; `const AB3_TABLE`; coerce status; drop dead label) | TM-007, TM-008 | LOW | Add one test on the SDK error path. |
| R-20 ⚡ | Add security headers / CSP to Nginx | TM-023 | LOW | Pairs with R-02 (HSTS). |

### Wave 2 — Access control & abuse containment (current cycle)
| R-ID | Title | Addresses | Effort | Notes |
|------|-------|-----------|--------|-------|
| R-05 | Add authN/authZ + per-request identity on the API/ALBs | TM-001 | MEDIUM | Root fix; unblocks scoping of KC01. |
| R-06 | Attach WAF + rate limiting to both ALBs | TM-004, TM-005 | MEDIUM | ⚡-ish foundational L7 shield. |
| R-07 | Paginated Query + caching instead of full-table scan; billing/DynamoDB alarms | TM-005 | MEDIUM | `R-06 → R-07`. |
| R-08 ⚡ | Gate or disable Swagger in production; drop it from TF output | TM-003 | LOW | — |

### Wave 3 — Supply chain & pipeline (current cycle — closes KC03)
| R-ID | Title | Addresses | Effort | Notes |
|------|-------|-----------|--------|-------|
| R-09 | Replace PAT with GitHub App/OIDC from a managed secret store (rotation+expiry); move TF state to encrypted remote backend + locking | TM-012, TM-024 | MEDIUM | Closes both storage and lifecycle gaps. |
| R-10 | CodePipeline manual-approval action + protected `main` + required reviews + signed commits | TM-013 | MEDIUM | `R-09 → R-10`. |
| R-11 | ECR `IMMUTABLE` + scan-on-push + deploy-by-digest + image signing | TM-017 | MEDIUM | — |
| R-12 | Blocking SCA/SBOM gates; pin base images by digest; upgrade EOL deps (Vue 2→3, aws-sdk v2→v3) | TM-018 | HIGH | Largest effort; highest supply-chain leverage. |
| R-13 | Remove privileged CodeBuild (rootless/kaniko/buildkit); scope build IAM | TM-015 | MED-HIGH | `R-14 → R-13`. |
| R-14 | Scope DevOps role to specific ARNs; constrain `PassRole` via `iam:PassedToService`; remove `resources=["*"]` on write/run | TM-016, TM-019 | MEDIUM | Decisive for KC03 escalation link. |
| R-15 | Treat taskdef/appspec as reviewed, version-controlled artifacts; restrict artifact-bucket write to the pipeline role | TM-019 | MEDIUM | Overlaps R-14. |

### Wave 4 — Detection, data protection, resilience
| R-ID | Title | Addresses | Effort | Notes |
|------|-------|-----------|--------|-------|
| R-16 | Enable ALB access logs + VPC flow logs + CloudTrail + GuardDuty + Config | TM-021 | MEDIUM | Foundational — removes the blindness under every kill chain. |
| R-17 | S3 versioning + Object Lock/MFA-delete + PAB + SSE-KMS + remove `force_destroy`; DynamoDB PITR + SSE-KMS; ECR SSE-KMS | TM-014, TM-026 | MEDIUM | — |
| R-18 ⚡ | VPC endpoints (DynamoDB/S3/ECR/CloudWatch) + restrict egress SG + enforce IMDSv2 | TM-020, TM-011, TM-025 | MEDIUM | Endpoints also fix the NAT SPOF (R-19). |
| R-19 | NAT gateway per AZ | TM-025 | LOW | Largely subsumed by R-18 endpoints. |
| R-21 ⚡ | Structured/redacted logging + retention alignment + restrict log read | TM-022 | LOW | — |

**Sequencing headline:** Wave 1 quick wins (R-01, R-02) neutralize two of the sharpest gaps in hours. Wave 3 (R-09→R-10, R-14→R-13, R-11, R-12) is the priority investment — it dismantles the composite-CRITICAL KC03. R-16 (detection) should be pulled forward alongside Wave 1 because it is what makes every other remediation verifiable.

---

## 4. Assumptions and Scope

**Assumed:**
- **Data class = non-personal INTERNAL** (product catalog id/path/title). This anchors the impact ceiling; **it is the single most load-bearing assumption.** If a real deployment adds auth, user data, or writable catalog fields, re-score TM-001/006/022/023 and the KC03 stored-XSS branch upward.
- **Read-only application** — no write path from the API to DynamoDB/S3 (verified in `app.js`); the only writes are operator/pipeline out-of-band, which is why stored-injection is latent (via TM-016/TM-013), not live.
- **Single region, single environment, single account** (README implies one env; no multi-region/multi-account resources in IaC).
- **Default configuration deployed** — `enable_https=false` (never overridden), local Terraform state (README). Concrete region/account values unknown (no `.tfvars` committed).

**Not analyzed / out of scope here:**
- Deep transitive dependency CVE enumeration (deferred to the code-review specialist; recorded as EOL/maintenance status, not a full SCA).
- SNS topic access policy (not revealed in source — coverage `unknown`, Open Question).
- Runtime/dynamic testing — this is a static architectural review of IaC + app code.
- Privacy (LINDDUN) and compliance framework mapping — owned by the privacy and compliance specialists.

**Open Questions:**
- **Risk acceptance / ownership** — no risk-owner or acceptance authority is stated in the source (demo repo, no governance). Needs an assigned owner before findings can be formally accepted or waived.
- **SNS topic policy** — is the deploy-notifications topic world-subscribable? Undetermined from IaC.

**Threat model lifecycle triggers (re-assess when):**
- Authentication, user accounts, or any personal/regulated data are introduced (re-anchors the entire impact model upward).
- The catalog becomes writable via the API (activates the stored-XSS branch of KC03).
- A second in-VPC workload is added (revives the network-position trust concern folded into TM-001).
- The API surface grows (Swagger auto-publishes new schemas; TM-003 blast radius scales).
- Any move toward production (SLA, real traffic) — re-score availability/financial impacts (TM-004/005/025) upward.

---

## Coverage States (Phase 6+8 domain)

| Item id | State | Detail |
|---------|-------|--------|
| threat-validation.false-positive-check | present | 27 source findings dispositioned: 25 validated, 2 merged, 0 rejected. |
| threat-validation.existing-mitigation-check | present | Each checked against Phase 1 §1.8 control inventory; none fully mitigated by an existing control. |
| threat-validation.confidence-assignment | present | HIGH/MEDIUM/LOW per finding. |
| threat-validation.deduplication | present | 3 candidate merges evaluated on evidence; 2 accepted, 1 rejected (with corrected framing). |
| threat-validation.framework-id-verification | present | All MITRE/CWE cross-checked vs frameworks.md; no hallucinated ids. |
| risk-assessment.prioritization-treatment | present | Remediation waves R-01…R-21 with dependencies and quick wins (§3). |
| risk-assessment.risk-acceptance-ownership | unknown | No risk owner/authority in sources — Open Question. |
| known-limitations-gaps.unmitigated-threats | present | All 25 validated findings unmitigated by design; captured as Known Limitations. |
| attack-paths.end-to-end-chains | present | KC01–KC04 validated post-merge; steps all real finding ids. |

*(Threat-enumeration, risk-scoring, and attack-path coverage items were resolved in the Phase 3-5 domain; config-hardening items — api-security.*, cicd-supply-chain-security.*, cloud-infrastructure-security.*, container-*, logging-monitoring.*, secrets-management.* — are owned by Phase 1 and the code-review/compliance specialists. This pass contributes the validated threat/risk view over them without re-claiming ownership.)*

---

## Execution Log

### Process Health
| Metric | Value |
|--------|-------|
| Files read back | 01, 03, 04, 05, recon.json, frameworks.md, findings.schema.json, SKILL.md (Phase 6/8 + gates), analysis-checklists.md |
| Source files independently re-verified | `Code/server/src/app.js`, `Infrastructure/Modules/IAM/main.tf` (full policy docs), `ALB/main.tf`, `ECR/main.tf`, `S3/main.tf`, `CodeBuild/main.tf`, `Templates/buildspec.yml` |
| Files written | 06-validated-findings.md, 08-threat-model-report.md, findings.json |
| Source findings dispositioned | 27 (TM-001…TM-027): 25 validated, 2 merged, 0 rejected |
| Validated findings emitted | 25 |
| Kill chains | 4 (KC01–KC04), re-checked post-merge |
| Validation gates run | jsonschema (VALID), custom invariant check (PASS), shipped `run.py validate` (PASS) |
| Errors encountered | 0 |
| Self-assessed output quality | HIGH |

### What Went Well
- Independent re-verification confirmed all five headline claims (no-auth, HTTP-only ALBs, dual `PassRole *`, error leak, privileged build + PAT) at source — no inherited claim went unchecked.
- The custom invariant check and the shipped deterministic validator both passed on the first emit (severity=band(L×I), summary_counts tally, ref grounding, surface coverage), so the manifest gate is clean before the report-analyst spawns.
- The dedup hints were evaluated, not rubber-stamped: 2 merges accepted on evidence, 1 rejected with a corrected mechanism — a defensible skeptical outcome rather than blanket acceptance.

### Issues Encountered (corrections made to the generative pass)
- **DevOps role wording (TM-016):** 03/04 described `s3:*`/`ecs:*`; the policy actually enumerates broad action lists on `resources=["*"]`, not literal action wildcards. Corrected; finding holds (the RegisterTaskDefinition+RunTask+PassRole* escalation combo is present).
- **TM-026 mechanism:** the DevOps role has `s3:PutObject` (overwrite) but **no `s3:DeleteObject`**. Reframed from "over-broad delete" to overwrite/ransom (PutObject + no versioning) + `terraform destroy` (force_destroy). Finding holds at MEDIUM.
- **TM-008 realism:** the SDK scan error is handled inline (HTTP 200, `code:undefined`), so the "unhandled RangeError" path is more theoretical than stated. Kept LOW with LOW confidence.
- **TM-002 nuance:** an `https_listener` resource exists but is gated behind `enable_https` (default false) — HTTP-only in effect; noted because it makes remediation cheap (R-02).

### Assumptions Made
- Non-personal INTERNAL data class drives the impact ceiling (stated as the primary re-assessment trigger).
- Default configuration deployed (`enable_https=false`, local state) per README, since no `.tfvars` overrides are committed.
- Kill-chain id form: `findings.json` uses `KC01`–`KC04` to satisfy the schema pattern `^KC[0-9]+$`; the prose "KC-0n" refers to the same chains.

### What Was Not Done (by design)
- No diagrams (Phase 2/7 — diagram-specialist). No consolidated multi-format report (report-analyst). No `coverage.json` merge (validation-specialist in team mode). This pass produced only the validated findings, the summary, and `findings.json`, plus its own `## Coverage States` for merge.
