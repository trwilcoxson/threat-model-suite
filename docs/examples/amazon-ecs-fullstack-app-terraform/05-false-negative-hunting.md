# Security Architect — Phase 5 False-Negative Hunting

## Metadata
| Field | Value |
|-------|-------|
| Agent | security-architect (generative pass, Phases 3-5) |
| Phase | 5 (False-Negative Hunting — expansive/adversarial) |
| Date | 2026-07-11 |
| Inputs | 03-threat-identification.md, 04-risk-quantification.md, recon.json, 02-structural-diagram.md |
| Mindset | Assume Phases 3-4 missed threats. Re-challenge low-risk components, trace complete kill chains, model insider/supply-chain/temporal/cascade. |
| Output | 2 new findings (TM-026, TM-027, fully scored); 4 declared kill chains (KC-01 – KC-04); coverage states; execution log |
| Diagram note | Attack-tree / attack-flow **rendering is deferred to the Phase 7 diagram-specialist** per the team split (this pass does not produce `.mmd` files or `findings.json`). Each chain below is declared in full so Phase 7 can render it and Phase 8 can populate `kill_chains[]`. |

---

## 1. Re-examination of "Low-Risk" / No-Findings Components

| Component | Original read | Adversarial re-read | Verdict |
|-----------|---------------|---------------------|---------|
| **C3 Swagger (TM-003, MED)** | Low-value docs | If a future route exposes anything sensitive, Swagger auto-publishes its schema anonymously. Blast radius grows silently with the API. | Keep MED; note as a *scaling* risk in Open Questions. |
| **C12 Autoscaling/CloudWatch** | Not a threat target | The 4-task cap is itself an availability weakness under TM-004/005 (it *guarantees* saturation is reachable), and alarms feed no security detection. | Folded into TM-004/TM-005; no new finding. |
| **C13 SNS deploy topic** | Benign notifier | Only carries deploy metadata; topic policy not shown in IaC. Could leak deploy timing/account detail if world-subscribable — **undetermined from sources**. | No fabricated finding; logged as Open Question / coverage `unknown`. |
| **D5 CloudWatch Logs (TM-022, LOW)** | Non-PII logs | Under a real deployment the same `console.error(raw err)` pattern would capture whatever the API later handles; retention (30d) also caps forensics for the *account*, not just app. | Keep LOW now; flagged to re-score if data class changes. |
| **C1 Client SPA (TM-023, LOW)** | Vue auto-escapes | Confirmed no write-path puts attacker data into the catalog, so no stored-XSS sink today. But if `title`/`path` ever become writable (admin/import), Vue's `v-html` or attribute binding could become a stored-XSS sink rendered in every visitor's browser. | Keep LOW; recorded as a persisted-input watch item (see §7). |
| **E5 Health check** | Clean | `/status` is anonymous but returns only a static string — no leak beyond TM-001. | Examined-and-clean; nominate for `no_issue_surface` (Phase 6). |

**Persisted / cross-context input tracing (explicit):** the only store the app *reads* into a render sink is DynamoDB `title`/`path` → Vue SPA. There is **no application write path** to DynamoDB or S3 (the API is read-only; assets/catalog are populated out-of-band by the operator/pipeline). Therefore no stored-XSS / second-order injection chain exists *today*. The latent chain — attacker who reaches the catalog via the pipeline or a broad IAM role (TM-016) writes a malicious `title`, which then executes in every SPA visitor's browser — **is** real and is captured as a cross-context escalation within KC-03 (supply-chain → data → client). Recorded, not scored as a separate finding because its entry is already TM-016/TM-013.

---

## 2. Kill-Chain Tracing (declared)

Four complete, multi-step chains. Each step cites the Phase 3/4 `TM-NNN` that covers it; **no step is uncovered** (the hunt confirms Phase 3 enumerated every link). `TM-021` (no detection) is a **cross-cutting amplifier present in all four chains** — every chain runs blind to the defender.

### KC-01 — Anonymous abuse → economic/availability denial
**Goal:** Deny service and inflict direct AWS cost with zero credentials.
**Actor:** TA1/TA2 (capability 2). **Composite severity:** HIGH.
**Steps:**
1. **Recon** — GET `/api/docs` (TM-003) to confirm `/api/getAllProducts` and host. *(MITRE T1595)*
2. **Initial access** — anonymous call to E2 (TM-001); no auth to bypass. *(T1190)*
3. **Amplify** — script a high-rate loop; no WAF/rate limit (TM-004) stops it. *(T1498)*
4. **Impact** — each call = full DynamoDB `scan` on `PAY_PER_REQUEST` (TM-005) → cost blowout + task saturation past the 4-task cap. *(T1498)*
**Coverage gap check:** none — all four steps map to identified threats. **Amplifier:** TM-021 (unseen).

### KC-02 — On-path HTTP → malicious content to end users
**Goal:** Execute attacker-controlled script in a victim's browser.
**Actor:** TA1 (on-path, capability 2). **Composite severity:** HIGH.
**Steps:**
1. **Position** — attacker on the network path (rogue Wi-Fi / ISP / transit) between R0 and C4/C5.
2. **Intercept/inject** — traffic is plaintext HTTP with no TLS/HSTS (TM-002); rewrite the SPA bundle or API JSON in flight.
3. **Execute** — injected script runs with **no CSP / security headers** to blunt it (TM-023).
4. **Impact** — client-side compromise (session/data theft in a real deployment; here, control of the rendered storefront).
**Coverage gap check:** none. **Amplifier:** TM-021.

### KC-03 — CI/CD compromise → production RCE → cloud account
**Goal:** Run attacker code in production and escalate to account-wide control.
**Actor:** TA3 (insider/compromised dev) or TA4 (upstream). **Composite severity:** CRITICAL (composite — this is the assessment's top risk).
**Steps:**
1. **Initial access** — either steal the PAT from unencrypted local state / pipeline config (TM-012), **or** poison an upstream `:latest` base image / EOL dependency (TM-018).
2. **Delivery** — push to `main`; `PollForSourceChanges` auto-triggers with **no approval gate** (TM-013). *(T1195)*
3. **Execution** — code runs in **privileged CodeBuild** (Docker-in-Docker) with the build IAM identity (TM-015). *(T1059)*
4. **Persistence/tamper** — overwrite the deployed image on **mutable ECR** (TM-017) and/or tamper the `taskdef.json` to set an attacker `taskRoleArn` (TM-019).
5. **Escalation** — the **DevOps role** wildcards (`ecs:*` + `iam:PassRole *`, TM-016) register+run a task under any role → account-wide privilege escalation.
6. **Cross-context bonus** — write a malicious `title` into the catalog (now controlling the pipeline) → stored XSS executes in every SPA visitor (see §1).
**Coverage gap check:** none — every link is an identified threat. **Amplifier:** TM-021 (no CloudTrail → the whole chain is unattributable).

### KC-04 — Container foothold → IMDS → cloud privilege escalation & exfiltration
**Goal:** Turn a single container compromise into cloud credentials and data exfiltration.
**Actor:** TA5 (post-exploitation, capability 4). **Composite severity:** HIGH.
**Steps:**
1. **Initial access** — RCE in the server container via a vulnerable/EOL dependency (TM-018) — no image/dep scanning to catch it.
2. **Credential access** — read task-role temporary credentials from IMDS (TM-011). *(T1552)*
3. **Escalation** — abuse the task role's `iam:PassRole *` (TM-010) to pass a privileged role to a reachable action. *(T1078)*
4. **Exfiltration/C2** — exfil catalog/credentials and reach C2 over **unrestricted egress** (TM-020). *(T1048/T1567)*
**Coverage gap check:** none. **Amplifier:** TM-021 (no VPC flow logs → exfil unseen).

**Kill-chain declaration (for Phase 7 / findings `kill_chains[]`):**
```
KC-01  goal: anonymous economic/availability denial     steps: TM-003, TM-001, TM-004, TM-005
KC-02  goal: on-path content injection to end users      steps: TM-002, TM-023
KC-03  goal: CI/CD compromise → prod RCE → account       steps: TM-012, TM-018, TM-013, TM-015, TM-017, TM-019, TM-016
KC-04  goal: container foothold → cloud priv-esc/exfil    steps: TM-018, TM-011, TM-010, TM-020
```
(TM-021 is intentionally not a *step* in any chain — it is the detection-blindness amplifier under all of them; Phase 7 may render it as an ambient annotation.)

---

## 3. Insider-Threat Scenarios
- **Compromised/malicious developer (TA3):** owns KC-03 outright — one `main` push ships to prod with no second signer (TM-013). No branch protection, no deploy approval, no artifact signing stand in the way. **Controls that should exist and don't:** required reviews, protected `main`, manual approval action in CodePipeline, signed images.
- **Terraform operator (R5):** holds the PAT and the unencrypted local state (TM-012/TM-024) on a workstation — a single-machine compromise yields repo write + full infra inventory + broad AWS credentials. No state encryption, no remote backend, no MFA-gated assume-role visible in IaC.
- **Result:** the insider/credential-theft path is the *least-gated* route to production and is the reason KC-03 is the composite-CRITICAL chain.

## 4. Supply-Chain Review (dependencies, build, registry, base images)
- **Base images (X4):** `bitnami/node:latest`, `nginx:latest` — mutable, unpinned, no digest, no scan (TM-018). A single upstream tag overwrite reaches prod.
- **npm (X2/X3):** no `npm audit`/SCA gate, no lockfile-integrity verification in `buildspec.yml`; aws-sdk v2 (maintenance) and Vue 2 (EOL) accrue unpatched CVEs (TM-018).
- **Build (C10, X5):** `privileged_mode` + `standard:4.0` (dated) — build-time code exec = privileged escape (TM-015).
- **Registry (D4):** MUTABLE, no scan-on-push, no image signing/verification at deploy (TM-017).
- **Source (X1):** GitHub v1 with a long-lived PAT and no webhook-signature/commit-signing requirement (TM-012, and TM-027 below).
- **New finding surfaced:** the *lifecycle* of the PAT (no rotation/revocation policy) is a distinct control gap from where it is stored → **TM-027**.

## 5. Temporal Threats
- **Secret lifecycle:** the GitHub PAT is long-lived with **no rotation or revocation mechanism** — once leaked it is valid indefinitely and there is no automated cutoff. → **TM-027 (new)**.
- **`:latest` drift:** the deployed base image changes meaning over time with no pin — today's reviewed image ≠ tomorrow's deployed image (covered by TM-018).
- **Certificate expiry:** **not applicable** — no TLS certificates exist to expire (TM-002 is the flip side).
- **Log retention (30d):** bounds forensic reach; a slow/low attack older than 30 days is unreconstructable (relates TM-021/TM-022).
- **Config drift:** `ignore_changes` on ALB listener default_action and the `github_token` mean Terraform will not detect/correct out-of-band changes to those — a drift blind spot; noted, folded into TM-024/TM-021.

## 6. Cross-Boundary Bypass Analysis
| Boundary | Expected control | Bypass path | Covered by |
|----------|------------------|-------------|-----------|
| TB1 Internet→ALB | (none — open `0.0.0.0/0:80`) | Direct anonymous access; nothing to bypass | TM-001, TM-004 |
| TB2 ALB→task | source-SG only | Public ALB already forwards Internet traffic; no per-request auth to reach the task logic | TM-009 |
| TB3 task→AWS | scoped read IAM | `iam:PassRole *` on the task role escapes the scoping | TM-010 |
| TB4 CI/CD | (poll + PAT) | Stolen PAT or malicious dep enters before any gate; no approval/signing | TM-012, TM-013, TM-018 |
| TB5 account | IAM boundaries | DevOps `PassRole *` + `ecs:*` crosses role boundaries within the account | TM-016 |
| TB6 VPC egress | (none) | Unrestricted outbound is itself the bypass — no exfil boundary exists | TM-020 |
**Finding:** every trust boundary except the (non-existent) egress boundary has an identified bypass; none required inventing a new threat — Phase 3 covered them. The reachability of a high-trust zone (TB5, account) from a low-trust start (TB1) is exactly KC-03/KC-04.

## 7. Data-Aggregation, Side-Channel, Cascade
- **Data aggregation:** single low-sensitivity source (catalog); combining it with itself yields nothing higher-sensitivity. **Not applicable** — traced.
- **Side-channel / info leak:** the meaningful one is error-message leakage (TM-007); no timing oracle on the parameterless read endpoints. Persisted-input watch item recorded (§1) in case `title`/`path` become writable.
- **Cascade failure:** single NAT (TM-025) → loss of one AZ's NAT breaks *all* task→AWS-service calls (DynamoDB/S3/ECR/CloudWatch have no VPC endpoints) → API returns errors (via the fragile handler, TM-008) despite a healthy ALB and second-AZ tasks. A targeted NAT/AZ disruption thus cascades to full API failure — a bigger blast radius than "single-NAT" suggests. Keeps TM-025 at MEDIUM but justifies it over "LOW/noted."
- **AI/ML threats:** **not applicable** — no ML/agent component.

---

## 8. New Findings (identified + scored, Phase 3/4 format)

### TM-026 — Irreversible data destruction / ransom of S3 buckets (over-broad delete + `force_destroy` + no versioning)
| Field | Value |
|-------|-------|
| STRIDE-LM | T, D |
| Affected component(s) | D2 (assets), D3 (artifacts), R3 (DevOps role) |
| Affected data flow(s) | R3-.->D2/D3 (`s3:*` on `*`) |
| Cross-framework | *(no matching data-destruction CWE in reference set — noted)*; OWASP A05:2021; MITRE T1485 (Data Destruction), T1486 (Data Encrypted for Impact); CIA: I, A |
| Description | The DevOps role's `s3:*` on `*` (TM-016), combined with `force_destroy=true` and **no versioning** on both buckets, means an attacker who reaches that identity — or a mistaken `terraform destroy` — can permanently delete (or overwrite/ransom) the assets and pipeline-artifact buckets with **no version history to recover from and no detection** (TM-021). This is a distinct *impact* (destruction) beyond TM-014's config-hardening framing. |

**Scoring (PASTA):** Actor TA3/TA5. Entry: DevOps-role compromise (via KC-03) or operator error. L=**2** (gated behind that access), I=**3** (irreversible loss of assets + in-flight build artifacts; recoverable-ish for a demo but no safety net, and pipeline artifacts feed live deploys). **Risk = 6 → MEDIUM.**

### TM-027 — Long-lived GitHub PAT with no rotation/revocation (temporal secret-lifecycle gap)
| Field | Value |
|-------|-------|
| STRIDE-LM | S, E |
| Affected component(s) | X1 (GitHub PAT), C9 (pipeline source), R5 |
| Affected data flow(s) | X1==>C9 (`OAuthToken`) |
| Cross-framework | *(rotation-specific CWE not in reference set; closest is CWE-798 hard-coded/long-lived credential — noted)*; OWASP A07:2021; MITRE T1078 (Valid Accounts), T1552; CIA: C, I |
| Description | The PAT is a single long-lived credential with no rotation schedule, no expiry policy, and no automated revocation path visible in the IaC. If leaked (TM-012), it stays valid until a human notices and manually revokes it — indefinite persistent access to the source of the supply chain. Distinct from TM-012 (which is about *where* the secret is stored) — this is about its *lifecycle*. |

**Scoring (PASTA):** Actor TA3/TA4. L=**3** (long-lived tokens leak over time through many channels; no automated cutoff makes exploitation of a leak durable), I=**3** (persistent repo/supply-chain access; bounded by the PAT's repo scope). **Risk = 9 → MEDIUM.** *(Candidate for merge-or-link with TM-012 in Phase 6 — kept distinct because the remediation differs: TM-012 = move the secret out of local state / into a managed store; TM-027 = rotate + expire + fine-grained scope.)*

---

## 9. Phase 5 Result Summary
- **Coverage confirmation:** the false-negative hunt found **no uncovered kill-chain step** — Phase 3's 25 threats span every link of KC-01…KC-04 and every trust-boundary bypass. That is a positive completeness signal, not a sign the hunt was shallow (the boundary-by-boundary and low-risk-component re-reads are documented above).
- **Two genuinely new findings** (TM-026 destruction/ransom impact; TM-027 secret lifecycle) — both surfaced by the "assume breach / temporal" lenses that the STRIDE-by-zone pass under-weights.
- **Composite risk:** KC-03 is the assessment's true top risk (composite CRITICAL) even though no single finding is CRITICAL — the multi-step CI/CD→prod→account chain is where impact and reachability multiply.
- **Running totals (Phases 3+5): CRITICAL 0 / HIGH 10 / MEDIUM 13 / LOW 4 = 27 findings.**

**Handoff to Phase 6 (fresh context):** validate the full set TM-001…TM-027 and the four kill chains skeptically. Explicit Phase-6 hints: candidate merges → {TM-012 ↔ TM-027}, {TM-014 ↔ TM-026}, {TM-009 ↔ TM-001}; candidate `no_issue_surface` → E5 health check, the application injection surface (parameterless routes), API1/API3 object-authz (no per-object resources). Do not treat any score here as final.

---

## Coverage States (Phases 3-5 domain — for merge into `coverage.json` by the validation-specialist)
States use taxonomy ids from `coverage-taxonomy.json`. Scope: the generative-analysis (threat/risk/kill-chain) items. Config-hardening items shared with the code-review and compliance specialists are left to those owners; where this pass contributes threat coverage over them it is noted, not claimed as the resolving owner.

| Item id | State | Detail / Note | Source |
|---------|-------|---------------|--------|
| threat-enumeration.methodology | present | STRIDE-LM per trust zone + PASTA St.6-7 + OWASP Risk Rating; frameworks.md IDs only. | 03, 04 |
| threat-enumeration.per-boundary-threats | present | Every TB1-TB6 boundary enumerated with threats + bypass paths (§6). | 03 Zones A-F, 05 §6 |
| threat-enumeration.threat-actors | present | TA1-TA5 mapped to each finding's likelihood (04 actor column). | 04 |
| threat-enumeration.threat-metadata | present | Each threat carries id, STRIDE-LM, components, data flows, MITRE/CWE/OWASP, CIA. | 03 tables |
| threat-enumeration.completeness-review | present | Phase 5 adversarial re-read of low-risk components + boundary bypass sweep; no uncovered chain step. | 05 §1, §6, §9 |
| metadata-threat.identity-and-description | present | TM-001…TM-027 each with title + description. | 03, 05 §8 |
| metadata-threat.category-and-rating | present | STRIDE-LM category + L×I severity band per threat. | 04 |
| metadata-threat.mitigation-and-status | partial | Remediation *directions* implied per finding; the structured remediation plan/status is Phase 8. | 04, 05 |
| risk-assessment.scoring-methodology | present | Risk = L×I (1-25), OWASP bands; methodology stated in 04 header. | 04 |
| risk-assessment.likelihood-impact-rating | present | Every finding L(1-5) × I(1-5) with written justification. | 04 |
| risk-assessment.prioritization-treatment | partial | Severity bands + composite kill-chain prioritization done; wave/treatment plan is Phase 8. | 04, 05 §2 |
| risk-assessment.risk-acceptance-ownership | unknown | No risk-owner/acceptance authority is stated in the source materials (demo repo, no governance). Lift to Open Questions. | — |
| attack-paths.end-to-end-chains | present | KC-01…KC-04 declared with per-step TM-ids. | 05 §2 |
| attack-paths.lateral-movement-escalation | present | KC-03/KC-04 trace lateral movement (task→account, build→account). | 05 §2 |
| attack-paths.choke-points-controls | partial | Controls-to-bypass identified per chain; the *should-exist* choke points listed (§3) but not yet a control-design plan. | 05 §2, §3, §6 |
| attack-paths.crown-jewel-exposure | present | Crown jewels = DynamoDB catalog, S3 buckets, DevOps/task IAM, the pipeline; exposure paths traced. | 05 §2 |
| abuse-misuse-cases.abuse-case-catalog | present | Cost/scrape abuse (TM-004/005), on-path injection (KC-02), CI/CD abuse (KC-03). | 03, 05 §2 |
| abuse-misuse-cases.business-logic-abuse | present | Only meaningful flow (fetch catalog) assessed for abuse; no other multi-step logic exists. | 03 Business-Logic section |
| abuse-misuse-cases.misuse-by-authorized-users | present | Insider dev (TM-013) and operator (TM-012/024) misuse modeled. | 05 §3 |
| abuse-misuse-cases.abuse-to-control-mapping | partial | Each abuse case names the absent control; formal control mapping is Phase 8 / compliance. | 05 §3, §6 |
| authorization-model.privilege-escalation | present | PassRole * on task (TM-010) and DevOps (TM-016) roles; escalation paths in KC-03/04. | 03 Zone C/D, 05 §2 |
| availability-resilience.threats-to-availability | present | L7 DoS (TM-004), cost/scan DoS (TM-005), NAT SPOF cascade (TM-025), fragile handler (TM-008). | 03, 05 §7 |
| security-controls.threat-to-control-traceability | partial | Findings reference the Phase 1 control inventory (present/absent) they defeat; full traceability matrix is Phase 7/8. | 04 attack paths |
| known-limitations-gaps.unmitigated-threats | partial | All 27 findings are currently unmitigated by design; finalized as Known Limitations in Phase 8. | 03, 04, 05 |

*(api-security.*, cicd-supply-chain-security.*, cloud-infrastructure-security.*, container-kubernetes-security.*, logging-monitoring.*, secrets-management.* config items: this pass contributes the threat/risk view [TM-001/003/004/005 → api-security; TM-013/015/017/018/019 → cicd; TM-010/011/014/016/020 → cloud-infra; TM-015/017/018 → container; TM-021/022 → logging; TM-012/024/027 → secrets], but their present/partial hardening state is resolved by Phase 1 and the code-review/compliance specialists — left to those owners to avoid double-writing.)*

---

## Execution Log

### Process Health
| Metric | Value |
|--------|-------|
| Files read | 01-reconnaissance.md, 02-structural-diagram.md, recon.json, coverage-taxonomy.json (ids); SKILL.md (Phases 3-5 + gates), frameworks.md, analysis-checklists.md; spot-verified 5 source/config files |
| Source files spot-verified | Code/server/src/app.js, Infrastructure/Modules/IAM/main.tf, Infrastructure/Templates/buildspec.yml, Infrastructure/Modules/CodePipeline/main.tf, Infrastructure/Modules/ALB/main.tf |
| Files written | 03-threat-identification.md, 04-risk-quantification.md, 05-false-negative-hunting.md |
| Threats identified | 27 (TM-001…TM-027); 25 in Phase 3, 2 new in Phase 5 |
| Kill chains declared | 4 (KC-01…KC-04) |
| Errors encountered | 0 |
| Self-assessed output quality | HIGH |

### What Went Well
- Recon and the L1-L3 diagrams were high-fidelity, so Phase 3 could reference canonical ids (C/D/E/TB/R/X) and Phase 2 flow labels directly without re-deriving topology.
- Independent code/config verification of the five headline claims (no-auth, HTTP-only ALB, dual `PassRole *`, error leak, privileged build + PAT) confirmed every one — no inherited claim went unchecked.
- The false-negative sweep found no uncovered kill-chain step, which is a genuine completeness signal here (small, well-enumerated surface), and still surfaced two real additions (TM-026 destruction impact, TM-027 secret lifecycle) plus the composite-CRITICAL framing of KC-03.

### Issues Encountered
- **Severity table arithmetic:** an initial Phase-4 distribution table under-counted HIGH by one (omitted TM-018); corrected in place to HIGH 10 / MEDIUM 11 / LOW 4 for Phase 3, HIGH 10 / MEDIUM 13 / LOW 4 = 27 with Phase 5. No downstream impact — the per-finding scores were always correct; only the roll-up needed the fix.
- **ID interleave across zones:** grouping by trust zone put TM-013 in Zone D and TM-014 in Zone C, so the ids are not monotonic within the document. Verified the set is nonetheless contiguous TM-001…TM-025 with no gap/duplicate (audit line in 03).

### What Was Skipped or Deliberately Not Done
- **No `findings.json`, no `06`, no false-positive validation** — owned by the fresh-context Phase 6+8 pass by design (avoids anchoring). The full set + merge/`no_issue_surface` hints are handed forward.
- **No `.mmd` diagrams (attack tree / attack flow / L4)** — owned by the Phase 7 diagram-specialist per the team split; the four chains are declared in full (goal + ordered TM-id steps) so they can be rendered without re-analysis.
- **SNS topic policy** not asserted as a finding — the source does not reveal the topic's access policy; recorded as coverage `unknown` / Open Question rather than fabricated.

### Assumptions Made
- **Data class = non-personal INTERNAL** (product catalog) drives the impact ceiling; if a real deployment adds auth, user data, or writable catalog fields, TM-001/006/022/023 and the KC-03 stored-XSS branch must be re-scored upward. Stated so Phase 6/8 can re-anchor.
- **No application write path to DynamoDB/S3** (read-only API) — verified in `app.js`; the only writes are operator/pipeline out-of-band, which is why stored-injection is latent (via TM-016/013), not live.
- **Composite CRITICAL (KC-03) is expressed as a kill chain, not a single inflated finding** — individual scores kept honest to the OWASP L×I bands; the fresh-context pass may choose to elevate a chain-anchor finding, but this pass declined to inflate.
