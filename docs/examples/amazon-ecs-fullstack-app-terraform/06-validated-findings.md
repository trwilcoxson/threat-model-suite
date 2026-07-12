# Security Architect — Phase 6 False-Positive Validation (Skeptical, Fresh-Context Pass)

## Metadata
| Field | Value |
|-------|-------|
| Agent | security-architect — Phase 6+8 validation pass (independent, fresh context) |
| Phase | 6 (False-Positive Validation — skeptical, evidence-based) |
| Date | 2026-07-11 |
| Target System | AWS ECS Fullstack App (Terraform Demo) |
| Inputs read back | 01-reconnaissance.md, 03-threat-identification.md, 04-risk-quantification.md, 05-false-negative-hunting.md, recon.json, frameworks.md, findings.schema.json |
| Independent verification | Re-read source directly, not inherited: `Code/server/src/app.js`, `Infrastructure/Modules/IAM/main.tf` (full policy docs), `Infrastructure/Modules/ALB/main.tf`, `Infrastructure/Modules/ECR/main.tf`, `Infrastructure/Modules/S3/main.tf`, `Infrastructure/Modules/CodeBuild/main.tf`, `Infrastructure/Templates/buildspec.yml` |
| Scoring convention | Risk = L(1-5) × I(1-5); LOW 1-4 / MEDIUM 5-9 / HIGH 10-16 / CRITICAL 17-25 (frameworks.md) |
| Mandate | Validate or reject **every** Phase 3 (TM-001…TM-025) and Phase 5 (TM-026, TM-027) finding — none left unaddressed. Evaluate the generator's dedup hints on the evidence; do not rubber-stamp. |

---

## 1. Independent Evidence Re-Verification (before validating)

I did not inherit the generative pass's confidence. The headline claims that drive severity were re-checked against source:

| Claim | Verified? | Evidence / correction |
|-------|-----------|-----------------------|
| No authN/authZ on any route | **Yes** | `app.js`: three routes (`/status`, `/api/getAllProducts`, `/api/docs`), zero middleware/guards. |
| ECS **task role** has `iam:PassRole` on `*` | **Yes** | `IAM/main.tf:317-323` sid `AllowIAMPassRole`, `resources=["*"]` on the app runtime role. Striking and confirmed. |
| DevOps role has `iam:PassRole` on `*` + broad ECS/S3 | **Yes, with precision fix** | `IAM/main.tf:287-293` PassRole `*` confirmed. **Correction:** the S3 and ECS grants are *enumerated action lists on `resources=["*"]`* (`s3:PutObject/GetObject/GetObjectVersion/GetBucketAcl/List*`; a long `ecs:` list incl. `RegisterTaskDefinition`+`RunTask`) — **not** literal `s3:*`/`ecs:*` action wildcards as 03/04 stated. The escalation combo (`RegisterTaskDefinition`+`RunTask`+`PassRole *`) is present, so **TM-016 holds**; wording tightened. |
| Both ALBs HTTP-only, no TLS | **Yes, with nuance** | `ALB/main.tf`: an `https_listener` **resource exists** but `count` is gated on `var.enable_https` (default `false`, never set) → only `http_listener` :80 is instantiated. HTTP-only **in effect**; remediation is cheap (flip the flag + ACM cert). **TM-002 holds.** |
| Error handler leaks `err.message`; fragile status | **Yes, with correction** | `app.js:77-88`: `console.error(raw err)` and `{code: err.status, description: err.message}` returned — TM-007/TM-022 confirmed. **Correction to TM-008:** the `getAllProducts` scan error is handled **inline** (`res.send` → HTTP 200 with `code: undefined`) — malformed but does **not** throw. `res.status(error.code)` in the middleware throws a `RangeError` only for a status-less error *routed through the middleware*, which the SDK scan path does not do. The stray `status: err.status || 500` is a dead JS label. So TM-008 is a real robustness defect but **more theoretical than 03/04 framed** — stays LOW. |
| ECR MUTABLE, no scan-on-push | **Yes** | `ECR/main.tf:10` `image_tag_mutability="MUTABLE"`; no `scan_on_push`. |
| S3 `force_destroy=true`, no versioning/SSE/PAB | **Yes** | `S3/main.tf`: `acl="private"`, `force_destroy=true`; no versioning/encryption/public-access-block/logging blocks. |
| CodeBuild `privileged_mode=true`, `standard:4.0` | **Yes** | `CodeBuild/main.tf:20-22`. |
| buildspec `sed` injects `taskRoleArn` into taskdef | **Yes** | `buildspec.yml:18` inserts a `taskRoleArn` line; `:45-49` template placeholders; `docker build/push`. TM-018/TM-019 hold. |
| **DevOps role can DELETE S3 objects** (TM-026 premise) | **No — corrected** | The DevOps role has `s3:PutObject` (overwrite) but **no `s3:DeleteObject`**. Destruction vectors are (a) **overwrite/ransom** via `PutObject` + no versioning (DevOps role, KC-03), and (b) `terraform destroy` with `force_destroy=true` (operator R5). TM-026's "over-broad delete" framing is **corrected to overwrite/ransom + destroy**; finding survives at MEDIUM. |

Framework-ID discipline (03/05) was clean: every out-of-reference-set MITRE/CWE was flagged in plain text rather than fabricated. My independent cross-check (§4) confirms no hallucinated IDs.

---

## 2. Deduplication Decisions (evaluated on evidence — not rubber-stamped)

The generative pass handed forward three candidate merges. I evaluated each against the criterion "same underlying issue discovered through different frameworks," and against whether the second finding has an **independent realistic attack path** in *this* system.

### MERGE — TM-009 → TM-001 (accepted)
- **TM-009** (implicit network trust / zero-trust gap) and **TM-001** (no authN/authZ) share **CWE-306** and the same root: *no request-level authentication anywhere*. TM-009 is that gap at the network layer, TM-001 at the app layer.
- TM-009's only *incremental* attack path — "any actor routable to a task (SSRF chain, second in-VPC workload) is trusted" — has **no concrete surface** here: the injection/SSRF sweep found parameterless routes (traced negative), and there is no second in-VPC workload. The sole actor that reaches a task is the **public ALB**, which is exactly TM-001 territory.
- **Verdict:** merge. The zero-trust / network-position (LM) dimension is folded into TM-001 as a note; TM-001 gains `C7/C8`, `TB2`, and STRIDE `LM`. No independent risk lost. Drops finding count by 1.

### MERGE — TM-027 → TM-012 (accepted)
- Both concern the **single GitHub PAT**. TM-012 = *where it is stored* (plaintext local state + pipeline config); TM-027 = *its lifecycle* (long-lived, no rotation/expiry/revocation). The generative pass kept them apart because "remediation differs."
- On evidence, the modern remediation is **one coherent action**: replace the long-lived PAT with a GitHub App / OIDC federation from a managed secret store — which fixes storage **and** lifecycle simultaneously. Splitting one credential's hygiene into two findings inflates the count without a distinct fix.
- **Verdict:** merge. The lifecycle (rotation/revocation) dimension is folded into TM-012's description and remediation; TM-012 gains MITRE `T1078`. Drops finding count by 1. TM-012 stays HIGH (L3×I4=12) — the storage gap is the higher-severity facet, so the merge does not change the score.

### KEEP DISTINCT — TM-026 vs TM-014 (rejected merge, with corrected framing)
- **TM-014** = default-AWS-owned encryption / no CMK-SSE-KMS / no PAB (a *confidentiality + key-management* config gap across D1-D4). **TM-026** = *destruction/ransom impact* on the S3 buckets (integrity/availability, MITRE T1485/T1486).
- They **share** two sub-controls (no versioning, `force_destroy`) but have **different primary drivers and STRIDE** (TM-014: I/T confidentiality; TM-026: T/D destruction) and different MITRE mappings. Collapsing them would bury the destruction/availability narrative under an encryption finding.
- **Verdict:** keep distinct; **correct TM-026's mechanism** (overwrite/ransom via `PutObject`+no-versioning and `terraform destroy`+`force_destroy` — not API delete) and cross-reference TM-014 so remediation (enable versioning + object-lock/MFA-delete + drop `force_destroy` + scope IAM) is not double-counted.

**Net effect:** 27 source findings → **25 validated findings** (2 merges, 0 outright rejections). Every source finding survived as a real issue; the two merges eliminate double-counting, not risk.

---

## 3. Per-Finding Validation Ledger (all 27 source findings dispositioned)

Confidence: **HIGH** = clear attack path confirmed by code/config; **MEDIUM** = plausible path, some assumptions; **LOW** = theoretical, significant assumptions.

| Source ID | Disposition | L | I | Risk | Band | Conf. | Validation note |
|-----------|-------------|:-:|:-:|:----:|------|-------|-----------------|
| TM-001 | **Validated** (absorbs TM-009) | 5 | 2 | 10 | HIGH | HIGH | `curl` the API, no credential, no control to bypass — verified in `app.js`. Now also carries the network-position/zero-trust (LM) dimension from TM-009. Impact honestly capped at 2 by non-personal catalog. |
| TM-002 | **Validated** | 3 | 3 | 9 | MEDIUM | HIGH | On-path read + response injection; HTTP-only confirmed (HTTPS listener gated off). |
| TM-003 | **Validated** | 4 | 2 | 8 | MEDIUM | HIGH | Swagger anonymous, URL published in TF output; free recon. Low intrinsic secrecy (3 routes) → I2. |
| TM-004 | **Validated** | 4 | 3 | 12 | HIGH | HIGH | No WAF/rate-limit; autoscaling caps at 4 tasks → saturation reachable. |
| TM-005 | **Validated** | 4 | 3 | 12 | HIGH | HIGH | Full-table `scan` per call on `PAY_PER_REQUEST` → cost + availability. Verified in `app.js`. |
| TM-006 | **Validated** | 3 | 1 | 3 | LOW | MEDIUM | `app.use(cors())` reflects any origin; impact bounded (no cookies/creds, data already public). Would escalate if auth added. |
| TM-007 | **Validated** | 3 | 2 | 6 | MEDIUM | HIGH | `err.message` returned to client; SDK errors leak table/region/ARN detail. |
| TM-008 | **Validated (downgraded framing)** | 2 | 2 | 4 | LOW | LOW | Robustness defect confirmed, but the specific "unhandled `RangeError`" path is theoretical (scan error handled inline, returns 200 with `code:undefined`, does not throw). Stays LOW. |
| **TM-009** | **MERGED → TM-001** | — | — | — | — | — | No independent attack path (no SSRF surface, no 2nd in-VPC workload); same CWE-306 root. See §2. |
| TM-010 | **Validated** | 2 | 4 | 8 | MEDIUM | HIGH | Task role `iam:PassRole *` verified (`IAM/main.tf:317-323`). Control gap certain; exploitation gated behind container foothold (L2). |
| TM-011 | **Validated** | 2 | 4 | 8 | MEDIUM | MEDIUM | IMDS credential read on container RCE → off-box use. Architectural; RCE precondition is an assumption. |
| TM-012 | **Validated** (absorbs TM-027) | 3 | 4 | 12 | HIGH | HIGH | PAT in unencrypted local state (README) + pipeline `OAuthToken` verified. Now also covers the long-lived/no-rotation lifecycle gap (TM-027). |
| TM-013 | **Validated** | 3 | 5 | 15 | HIGH | HIGH | `PollForSourceChanges=true` on `main`, no approval action → arbitrary code to prod. Top individual risk (tied). |
| TM-014 | **Validated** | 2 | 3 | 6 | MEDIUM | HIGH | Default encryption only; no versioning/PAB; `force_destroy` — verified. Distinct from TM-026 (confidentiality/key framing). |
| TM-015 | **Validated** | 3 | 5 | 15 | HIGH | HIGH | `privileged_mode=true` → build-time code exec = privileged Docker + build IAM. Top individual risk (tied). |
| TM-016 | **Validated (wording tightened)** | 2 | 5 | 10 | HIGH | HIGH | Escalation combo (`RegisterTaskDefinition`+`RunTask`+`PassRole *`) verified. **Corrected:** grants are enumerated actions on `resources=["*"]`, not literal `s3:*`/`ecs:*`. Impact I5 unchanged. |
| TM-017 | **Validated** | 3 | 4 | 12 | HIGH | HIGH | ECR MUTABLE + no scan-on-push → silent image replacement; no digest pin. Verified. |
| TM-018 | **Validated** | 3 | 4 | 12 | HIGH | HIGH | `:latest` base images, no SCA/SBOM, EOL deps (Vue 2 / aws-sdk v2). Verified via Dockerfiles/recon. |
| TM-019 | **Validated** | 2 | 4 | 8 | MEDIUM | MEDIUM | `buildspec.yml:18` injects `taskRoleArn` via `sed`; artifact bucket writable via DevOps `s3` grant. Exploitation needs build-env/artifact influence. |
| TM-020 | **Validated** | 2 | 3 | 6 | MEDIUM | HIGH | SG egress `-1`, NAT `0.0.0.0/0` — egress openness confirmed; exfil/C2 gated behind foothold. |
| TM-021 | **Validated (scored as amplifier)** | 4 | 3 | 12 | HIGH | MEDIUM | No ALB/flow/CloudTrail logging confirmed. L4 reflects near-certain undetectability; this is the cross-cutting amplifier under all four kill chains, not a standalone breach. HIGH retained for prioritization. |
| TM-022 | **Validated** | 2 | 2 | 4 | LOW | MEDIUM | `console.error(raw err)` + 30-day retention. Low sensitivity today (non-PII); needs log-read access. |
| TM-023 | **Validated** | 2 | 2 | 4 | LOW | HIGH | No CSP / `X-Frame-Options` / HSTS (Nginx default). Defense-in-depth gap; no live XSS sink (Vue escapes). |
| TM-024 | **Validated** | 2 | 3 | 6 | MEDIUM | HIGH | Local unencrypted state, no backend/locking (README) → integrity + inventory exposure. Distinct from TM-012's secrecy angle. |
| TM-025 | **Validated** | 2 | 3 | 6 | MEDIUM | HIGH | Single NAT, no VPC endpoints → egress SPOF; cascades to full API failure on AZ/NAT loss (§5 cascade). |
| TM-026 | **Validated (mechanism corrected)** | 2 | 3 | 6 | MEDIUM | MEDIUM | Corrected to overwrite/ransom (`PutObject`+no-versioning) + `terraform destroy`(`force_destroy`); **not** API delete (no `s3:DeleteObject`). Distinct destruction/availability impact vs TM-014. |
| **TM-027** | **MERGED → TM-012** | — | — | — | — | — | Same PAT asset; lifecycle facet of the same credential-hygiene issue with a unified remediation. See §2. |

**Disposition tally:** 25 validated, 2 merged, 0 rejected. All 27 addressed. No finding left unresolved.

---

## 4. Framework ID Verification (every ID cross-checked against frameworks.md)

Verified each MITRE technique and CWE in the **validated** set appears in the frameworks.md reference tables; verified each in-finding OWASP id exists.

- **CWEs used (all in reference set):** 306, 311, 200, 770, 400, 209, 755, 269, 798, 312, 732, 532, 79. ✔
- **MITRE techniques used (all in reference set):** T1190, T1595, T1498, T1078, T1068, T1552, T1195, T1059, T1048, T1567, T1562, T1485, T1486. ✔
- **Correctly excluded (flagged plain-text by the generator, not fabricated):** CWE-942 (permissive CORS), CWE-522 (unprotected creds), CWE-284 (broad access control), CWE-494 (missing integrity check), CWE-1104 (unmaintained components), CWE-1021 (clickjacking), CWE-778 (insufficient logging); on-path/AiTM technique and egress-filtering/SPOF have no reference-set entry. Each stays as plain-text in the description — correct handling. ✔
- **No hallucinated IDs remain.** ✔

---

## 5. Attack-Path Realism & Kill-Chain Confirmation

Every validated finding has a concrete step-by-step path (see the `attack_path` field in `findings.json` and the scored table in 04). The four declared kill chains re-checked after the merges — none used a merged-away id as a step, so no chain repair was needed:

| Chain | Goal | Steps (all real, validated ids) | Composite |
|-------|------|--------------------------------|-----------|
| KC01 | Anonymous economic/availability denial | TM-003 → TM-001 → TM-004 → TM-005 | HIGH |
| KC02 | On-path HTTP content injection to end users | TM-002 → TM-023 | HIGH |
| KC03 | CI/CD compromise → prod RCE → cloud account | TM-012 → TM-018 → TM-013 → TM-015 → TM-017 → TM-019 → TM-016 | **CRITICAL (composite)** |
| KC04 | Container foothold → IMDS → cloud priv-esc/exfil | TM-018 → TM-011 → TM-010 → TM-020 | HIGH |

**Confirmed:** no single finding reaches CRITICAL (17-25) — correct given the non-personal data ceiling. The CRITICAL-grade risk is the **composite KC03**, and it is honestly expressed as a chain rather than by inflating any one finding. I did **not** elevate any individual finding to CRITICAL; the composite framing is sound.

**Cascade confirmed (TM-025):** single NAT + no VPC endpoints means an AZ/NAT loss breaks all task→DynamoDB/S3/ECR/CloudWatch calls; the fragile handler (TM-008) then surfaces errors. Blast radius exceeds "single NAT" — justifies MEDIUM over LOW.

---

## 6. Examined-and-Clean Surfaces (no_issue_surface) & Traced Non-Applicabilities

- **E5 (ALB → task health check, `/status` `/`)** → `no_issue_surface`. `/status` returns a static string; `/` returns the SPA index. No data leak on the *internal* health-check flow. (The *public* anonymous exposure of `/status` is covered under TM-001 / E2.)
- **Application injection surface (parameterless routes)** — traced clean: `/api/getAllProducts` and `/status` take no parameters; the fixed `DocumentClient.scan({TableName})` reaches no user-controlled sink. No SQL/NoSQL/command/SSTI/SSRF surface in the app tier. Not a recon surface id, so recorded here in prose (not in the `no_issue_surface` array, which holds recon ids only).
- **API1/API3 object-level & property-level authorization** — not applicable: no per-object/per-user resources; the sole endpoint returns the entire public catalog with no object identifiers in the request. Traced non-applicability.
- **Prompt-injection / AI-ML** — not applicable: no LLM/agent/RAG component.
- **Cross-tenant isolation** — not applicable: single-tenant, single-account.

---

## 7. Consistency & Overall Validation
- **Severity recomputed for every finding** (§3) from L×I against the frameworks.md bands — all match; none eyeballed.
- **Like findings scored alike:** the two anonymous-abuse DoS findings (TM-004, TM-005) both 12/HIGH; the two supply-chain-integrity findings (TM-017, TM-018) both 12/HIGH; the pipeline-gated account-impact pair (TM-016 I5, TM-019 I4) differ only on escalation reachability, as intended.
- **No CRITICAL accidentally downgraded** — none reached 17; composite CRITICAL captured as KC03.
- **Data-class anchor accepted:** non-personal INTERNAL catalog caps confidentiality impact. If a real deployment adds auth, user data, or writable catalog fields, TM-001/006/022/023 and the KC03 stored-XSS branch must be re-scored upward (recorded as a lifecycle trigger in 08).

---

## Coverage States (Phase 6 domain — for merge into `coverage.json`)

| Item id | State | Detail / Note |
|---------|-------|---------------|
| threat-validation.false-positive-check | present | All 27 source findings dispositioned (25 validated, 2 merged, 0 rejected); each has a concrete attack path or was downgraded/merged. |
| threat-validation.existing-mitigation-check | present | Each finding checked against the Phase 1 §1.8 Security Control Inventory; none found fully mitigated by an existing control (the system's controls are network-segmentation/multi-AZ/blue-green, which do not close these gaps). |
| threat-validation.confidence-assignment | present | HIGH/MEDIUM/LOW assigned per finding (§3). |
| threat-validation.deduplication | present | 3 candidate merges evaluated on evidence; 2 accepted (TM-009→TM-001, TM-027→TM-012), 1 rejected (TM-026 kept distinct with corrected framing). |
| threat-validation.framework-id-verification | present | Every MITRE/CWE cross-checked against frameworks.md; no hallucinated ids; out-of-set ids kept as plain text. |
| risk-assessment.prioritization-treatment | present | Remediation waves R-01…R-nn produced in 08 §3 with dependencies and quick-wins. |
| risk-assessment.risk-acceptance-ownership | unknown | No risk-owner/acceptance authority stated in sources (demo repo, no governance). Lifted to Open Questions in 08. |
| known-limitations-gaps.unmitigated-threats | present | All 25 validated findings currently unmitigated by design; finalized as Known Limitations in 08. |

**Cross-references:** validated finding list mirrored in `findings.json`; summary + remediation waves in `08-threat-model-report.md`.
