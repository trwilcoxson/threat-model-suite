# Security Architect — Phase 3 Threat Identification

## Metadata
| Field | Value |
|-------|-------|
| Agent | security-architect (generative pass, Phases 3-5) |
| Phase | 3 (Threat Identification — STRIDE-LM, no scoring) |
| Date | 2026-07-11 |
| Target System | AWS ECS Fullstack App (Terraform Demo) |
| Inputs | 01-reconnaissance.md, 02-structural-diagram.md, recon.json; spot-verified against `Code/server/src/app.js`, `Infrastructure/Modules/IAM/main.tf`, `Infrastructure/Templates/buildspec.yml`, `Infrastructure/Modules/CodePipeline/main.tf`, `Infrastructure/Modules/ALB/main.tf` |
| Method | STRIDE-LM per trust zone (medium system → group by zone per skill §Scaling), MITRE ATT&CK / CWE / OWASP cross-classification using verified IDs only |
| Scoring | **None** — identification only. Likelihood/Impact/Severity are Phase 4. |
| Node-id contract | References canonical ids from recon.json / 02-structural-diagram.md: C1-C13, D1-D6, E1-E5, TB1-TB6, R0-R5, X1-X5. |

## Scope Note & Verification
The Phase 1 recon signals were independently re-verified at the code/config level before enumerating threats (not merely inherited):
- **No authN/authZ**: `Code/server/src/app.js` — three routes (`/status`, `/api/getAllProducts`, `/api/docs`), zero middleware, zero guards. `Login.vue` is an inert stub. Confirmed.
- **Both ALBs public + HTTP-only**: `Infrastructure/Modules/ALB/main.tf` creates only an `aws_alb_listener.http_listener` on port 80/`HTTP`; no HTTPS listener, no ACM. SG allows `0.0.0.0/0:80`. Confirmed.
- **`iam:PassRole` on `*` twice**: `Infrastructure/Modules/IAM/main.tf` sid `AllowIAMPassRole` appears in **both** the DevOps role (`resources = ["*"]`) and the **ECS task role** (`resources = ["*"]`). DevOps also has `s3:*`/`ecs:*`/`logs:*`/CloudWatch on `resources = ["*"]`. Confirmed.
- **Open CORS**: `app.use(cors())` with no origin allowlist (reflects any origin). Confirmed.
- **Error leak**: route handler returns `{code: err.status, description: err.message}` to the client; error middleware also returns `err.message`; `console.error` logs the raw error. `AB3_TABLE = "DYNAMODB_TABLE"` is an implicit global (no `var`/`let`/`const`); `res.status(error.code)` is called with a possibly-undefined status. Confirmed.
- **Supply chain**: `CodePipeline/main.tf` sets `OAuthToken = var.github_token`, `PollForSourceChanges = true`, GitHub v1 `ThirdParty` source on branch `main`. `buildspec.yml` runs `sed` to inject env values into shipped source (`RestServices.js`, `swagger.js`, `app.js`) and to inject a `taskRoleArn` into `taskdef.json`; `docker build`/`push`; CodeBuild `privileged_mode = true`. ECR `MUTABLE`, no scan-on-push. Confirmed.

**Injection-sink tracing (explicit negative result):** No application entry point accepts user-controlled input that reaches a query, command, template, deserializer, or redirect sink. `/api/getAllProducts` takes **no** parameters and issues a fixed `DocumentClient.scan({TableName})`; `/status` takes none. There is therefore **no SQL/NoSQL/operator-injection, SSTI, command-injection, or SSRF surface in the application tier** — recorded here so the absence is a traced conclusion, not an omission. The one place untrusted-ish structured values flow into generated artifacts is the **build-time `sed`** (TM-018), which is a supply-chain concern, not a request-path injection.

**Prompt-injection / instruction-channel:** none present. No LLM/agent component ingests external content; recon found no embedded override payloads in any reviewed file. Marked not-applicable.

---

## STRIDE-LM by Trust Zone

Grouped by trust boundary (medium system; components inside a zone that share a threat profile are assessed together, unique per-component threats broken out). Every threat carries a stable `TM-NNN` id used unchanged in Phases 4-8.

### Zone A — Internet edge / public ALBs (TB1; C4, C5, C2, C3; E1, E2, E3)

| TM ID | Title | STRIDE-LM | Affected component(s) | Affected data flow(s) | Cross-framework | Description |
|-------|-------|-----------|----------------------|----------------------|-----------------|-------------|
| **TM-001** | No authentication/authorization on any endpoint | S, E | C2, C3, C5 (E2, E3) | R0→C5→C8 (`GET /api/getAllProducts`, `/status`); R0→C5→C3 (`/api/docs`) | CWE-306; OWASP A07:2021, API2:2023; MITRE T1190; CIA: C | Every route is anonymous — no login, token, session, or middleware. Any Internet client invokes the API and reads the full catalog. This is the root access-control gap: it also means any privileged function added later is unprotected by construction, and it removes the natural throttle/attribution that auth provides for the abuse threats below. |
| **TM-002** | Cleartext HTTP on both public ALBs (no TLS) — transit interception & response tampering | T, I | C4, C5 (E1, E2) | R0→C4 (SPA load); R0→C5 (API); C4→C7, C5→C8 (ALB→task, also plaintext) | CWE-311; OWASP A02:2021; CIA: C, I. *(MITRE: on-path/AiTM technique not in reference set — manual verification recommended)* | Only an HTTP:80 listener exists. An on-path attacker (rogue Wi-Fi, ISP, compromised transit) can read all request/response traffic and, more importantly, **inject a modified HTTP response** — e.g., replace the SPA bundle or API JSON with malicious content served to the victim's browser. No HSTS, no redirect. |
| **TM-003** | Swagger / OpenAPI UI publicly reachable (`/api/docs`) — attack-surface enumeration | I | C3 (E3) | R0→C5→C3 | CWE-200; OWASP API9:2023; MITRE T1595; CIA: C | The Swagger UI and machine-readable spec are anonymous and the URL is published in the Terraform output. It hands an attacker the full API contract (routes, schemas, host) for enumeration. Low intrinsic secrecy here (3 trivial endpoints) but it is free reconnaissance and normalizes an "internal docs on the Internet" pattern. |
| **TM-004** | No WAF / rate limiting / bot control in front of public ALBs — L7 DoS & scraping | D | C4, C5 (E1, E2) | R0→C4, R0→C5 | CWE-770; OWASP API4:2023; MITRE T1498; CIA: A | Nothing throttles inbound. A single host can flood either ALB or scrape at will. Autoscaling is capped (min 1 / max 4 tasks), so saturation is reached quickly; there is no upstream shield. |
| **TM-005** | Unauthenticated full-table `scan` on every request → cost amplification / economic DoS | D | C2, C5, D1 (E2) | R0→C5→C8→D1 (`DocumentClient.scan`) | CWE-400; OWASP API4:2023; MITRE T1498; CIA: A | `/api/getAllProducts` triggers a full-table DynamoDB **scan** per call, and the table is `PAY_PER_REQUEST`. With no auth (TM-001) and no rate limit (TM-004), an attacker loops the endpoint to drive unbounded read-capacity + data-transfer billing and to exhaust task capacity — availability *and* direct financial impact with a trivial script. |
| **TM-006** | Permissive CORS (`cors()` reflects any origin) | S, I | C2 (E2) | R0→C5→C8 | CWE-200 *(permissive-CORS CWE-942 not in reference set — noted)*; OWASP A05:2021; CIA: C | The API reflects any `Origin`. Any website can read API responses from a visitor's browser. Impact is limited because responses carry no credentials/cookies and the data is already anonymous — but it is a misconfiguration and would become serious the moment auth/cookies are introduced. |
| **TM-007** | Error-message information disclosure to client | I | C2 | R0→C5→C8 (error path) | CWE-209; OWASP A05:2021; CIA: C | Both the route handler and the error middleware return `err.message` (and `err.status`) to the caller. AWS SDK errors can carry internal detail (table name, region, ARNs, throttling/permission specifics), leaking implementation facts that aid an attacker. |
| **TM-008** | Fragile error handling → unhandled exception on error path | D | C2 | R0→C5→C8 (error path) | CWE-755; OWASP A04:2021; CIA: A | The error middleware calls `res.status(error.code)` where `error.code = err.status`, which is `undefined` for AWS-SDK-origin errors → `RangeError`. Combined with the stray labeled statement (`status: err.status || 500`) and the implicit global `AB3_TABLE`, the error path is brittle: induced backend errors can throw inside the handler rather than degrade gracefully. Primarily a robustness/DoS-surface defect. |

### Zone B — Public → private subnet, ALB → task (TB2; C4→C7, C5→C8; E5)

| TM ID | Title | STRIDE-LM | Affected component(s) | Affected data flow(s) | Cross-framework | Description |
|-------|-------|-----------|----------------------|----------------------|-----------------|-------------|
| **TM-009** | Implicit network trust — tasks accept any traffic from the ALB SG with no per-request auth (zero-trust gap) | S, LM | C7, C8 (E5) | C4→C7, C5→C8, HC→C8 | CWE-306; OWASP A04:2021; CIA: C, I | The tasks authorize inbound purely by source security-group (the ALB), with no request-level identity check. Because the fronting ALB is itself Internet-facing (TB1), the "private subnet" gives no inbound isolation for the app path — anything the public ALB forwards is trusted. Any actor able to route to a task (SSRF chain, a second workload in-VPC, or simply the public ALB) is implicitly trusted. |

### Zone C — ECS task → AWS services via IAM task role (TB3; R1, R2, C8, D1, D2)

| TM ID | Title | STRIDE-LM | Affected component(s) | Affected data flow(s) | Cross-framework | Description |
|-------|-------|-----------|----------------------|----------------------|-----------------|-------------|
| **TM-010** | ECS **task role** carries `iam:PassRole` on `*` — latent privilege escalation | E, LM | R2, C8 (TB3) | C8--o R2 (assume task role) | CWE-269; OWASP A01:2021; MITRE T1078, T1068; CIA: C, I, A | The application's runtime identity holds `iam:PassRole` on every role in the account. An attacker who compromises the server container (and thereby the task role) can pass any role to any service action they can reach — the classic PassRole escalation primitive. It is unnecessary for a read-only catalog API and dramatically widens blast radius. |
| **TM-011** | Post-exploitation task-credential theft via IMDS → cloud pivot | I, E, LM | C8, R2 (TB3, TB6) | C8→IMDS→(R2 creds)→D1/D2/AWS | CWE-200 *(insufficiently-protected-credentials CWE-522 not in reference set — noted)*; MITRE T1552; OWASP A05:2021; CIA: C | If the Node/Nginx container is compromised (vulnerable dependency, TM-017), the task role's temporary credentials are readable from the instance metadata service and can be used off-box. Combined with unrestricted egress (TM-020) and PassRole (TM-010), a single container foothold becomes a cloud-account foothold. |
| **TM-012** | GitHub PAT stored plaintext in local Terraform state and pipeline config | S, I, E | D6, X1, C9, R5 (TB4, TB5) | R5==>PAT==>D6; X1==>C9 (`OAuthToken`) | CWE-798, CWE-312; OWASP A02:2021, A07:2021; MITRE T1552; CIA: C, I | The long-lived GitHub personal access token is persisted in unencrypted local `terraform.tfstate` on the operator workstation and in the CodePipeline source configuration (readable to anyone who can read pipeline config via the over-broad DevOps role). Theft yields repository write access — the single trust anchor of the whole supply chain. |
| **TM-014** | Default AWS-owned encryption only; no CMK/SSE-KMS; S3 lacks public-access-block/versioning; `force_destroy=true` | I, T | D1, D2, D3, D4 (TB3, TB5) | C8→D1, C8→D2, C10→D4, C9→D3 | CWE-311; OWASP A02:2021; CIA: C | Every store relies on AWS-owned default keys — no customer-managed key, no key-usage audit, no cross-account key isolation. The S3 buckets have no public-access-block or versioning and `force_destroy=true`. Confidentiality/recoverability controls are the platform default, not deliberate; there is no defense against key-plane or account-plane exposure and no object-version safety net. |

*(TM-013 is placed in Zone D. IDs remain globally unique and sequential across zones.)*

### Zone D — CI/CD supply chain (TB4; X1-X5, C9, C10, C11, D3, D4, R3, R4)

| TM ID | Title | STRIDE-LM | Affected component(s) | Affected data flow(s) | Cross-framework | Description |
|-------|-------|-----------|----------------------|----------------------|-----------------|-------------|
| **TM-013** | `main`-push auto-deploy to production with no approval gate | T, E, LM | C9, X1 (TB4) | X1→C9→C10→C11→C6 | CWE-732 *(broad-access-control CWE-284 not in reference set — noted)*; OWASP A08:2021; MITRE T1195; CIA: I, A | `PollForSourceChanges = true` on branch `main` means any merge/push auto-builds and blue/green-deploys to production with **no manual approval, no review gate, no separation of duties**. One developer (or a stolen PAT, TM-012) ships arbitrary code straight to prod. |
| **TM-015** | Privileged CodeBuild (Docker-in-Docker) → build-time RCE, container/host escape | E, LM | C10 (TB4) | X1→C9→C10; X2/X3/X4→C10 | CWE-269; OWASP A08:2021; MITRE T1195, T1059; CIA: C, I, A | CodeBuild runs with `privileged_mode = true`. Any code that executes during the build — a malicious dependency (`npm install`), a poisoned `:latest` base image (TM-017), or attacker-modified source (TM-013) — runs with privileged Docker access and the build's IAM identity, enabling escape and lateral movement. |
| **TM-016** | Over-permissioned DevOps role (`s3:*`/`ecs:*`/`iam:PassRole *`/`logs:*` on `*`) | E, LM | R3 (TB4, TB5) | C10--o R3; R3-.->D4/ECS/account | CWE-269, CWE-732; OWASP A01:2021; MITRE T1078; CIA: C, I, A | The identity the pipeline assumes can act on **any** S3 bucket and **any** ECS resource, write **any** log group, and — decisively — `PassRole` on `*`. `ecs:*` + `iam:PassRole *` together are a complete privilege-escalation combo: register a task definition with any role and run it. Compromise of the build (TM-015) inherits account-wide power. |
| **TM-017** | Mutable ECR tags + no scan-on-push → silent image replacement | T, LM | D4, C10, C6 (TB4) | C10→D4→C6 (image pull on task start) | CWE-732 *(missing-integrity-check CWE-494 not in reference set — noted)*; OWASP A08:2021; MITRE T1195; CIA: I | ECR repositories are `MUTABLE` with no `scan_on_push`. Anyone with ECR push (via the DevOps role, TM-016, or the pipeline, TM-013) can overwrite the deployed tag / `:latest`; the next task start or scale-out silently pulls the attacker's image. No digest pinning in the task definition to detect it. |
| **TM-018** | Unpinned `:latest` base images, no SCA/SBOM, EOL runtime deps → upstream supply-chain implant | T | X2, X3, X4, C10 (TB4) | X4→C10 (base image); X2/X3→C10 (npm) | *(unmaintained/vulnerable-components CWE-1104 not in reference set — noted)*; OWASP A06:2021; MITRE T1195; CIA: I | Dockerfiles pull `bitnami/node:latest` and `nginx:latest` (mutable, unpinned, non-reproducible); there is no dependency or image scanning, no SBOM, no lockfile-integrity gate. Runtime deps are EOL/maintenance (Vue 2, aws-sdk v2). A compromised upstream tag or a known-CVE dependency lands in production unremarked. |
| **TM-019** | Deploy-artifact & task-definition tampering (artifact bucket + build-time `sed` injects `taskRoleArn`) | T, E | D3, C10, C11 (TB4) | C10→D3 (`taskdef.json`/`appspec.yaml`); C11 consumes | CWE-732; OWASP A08:2021; MITRE T1195; CIA: I | The build writes `taskdef.json`/`appspec.yaml` into the artifact bucket (D3) and injects the task-role ARN into the task definition via `sed`. An attacker who can influence the build environment or the artifact bucket (DevOps role `s3:*`, TM-016) can deploy an attacker-chosen task role or container definition — directly weaponizing PassRole (TM-010/TM-016). |

### Zone E — Egress / VPC perimeter / detection (TB5, TB6; D5, C8)

| TM ID | Title | STRIDE-LM | Affected component(s) | Affected data flow(s) | Cross-framework | Description |
|-------|-------|-----------|----------------------|----------------------|-----------------|-------------|
| **TM-020** | Unrestricted egress (SG egress `-1` to `0.0.0.0/0`, NAT to `0.0.0.0/0`) → exfiltration & C2 | I, LM | C8, TB6 | C8→NAT→Internet | *(no matching egress-filtering CWE in reference set — noted)*; OWASP A05:2021; MITRE T1048, T1567; CIA: C | Tasks may reach any Internet host outbound with no allow-listing or DNS filtering. A compromised container (TM-011/TM-015) has a clear channel to exfiltrate catalog/credentials and to reach command-and-control. This is the amplifier that turns any foothold into data loss. |
| **TM-021** | No ALB access logs, VPC flow logs, CloudTrail, GuardDuty, or Config → no detection or attribution | R | D5, TB5, TB6 | (absence across all flows) | *(insufficient-logging CWE-778 not in reference set — noted)*; OWASP A09:2021; MITRE T1562; CIA: — (accountability) | The IaC declares only CloudWatch **task/build** logs. There are no ALB access logs, no VPC flow logs, and no account-level trail (CloudTrail/GuardDuty/Config). Scraping, cost abuse, credential misuse, and deploys are neither detectable nor attributable — every other threat here operates blind to the defender, and repudiation is total for pipeline/deploy actions. |
| **TM-022** | Sensitive data in logs + short retention (`console.error(raw err)`, 30-day) | I, R | D5, C2 | C8→D5 (awslogs) | CWE-532; OWASP A09:2021; CIA: C | The error handler logs the raw error object to stderr → CloudWatch. Low sensitivity today (non-PII), but the pattern captures internal detail, and 30-day retention limits forensic reach. |
| **TM-025** | Single NAT gateway — egress SPOF for all task→AWS-service traffic | D | TB6, C12 | C8→NAT→{D1,D2,D4,D5} | *(no matching CWE in reference set — noted)*; OWASP A04:2021; CIA: A | Without VPC endpoints, all task→DynamoDB/S3/ECR/CloudWatch traffic egresses through a **single** NAT gateway in one AZ. Loss of that AZ/NAT breaks the API's dependency calls even though the ALB and a second AZ's tasks survive — a resilience single-point-of-failure. |

### Zone F — Client SPA & operator/IaC (C1, C7; D6, R5)

| TM ID | Title | STRIDE-LM | Affected component(s) | Affected data flow(s) | Cross-framework | Description |
|-------|-------|-----------|----------------------|----------------------|-----------------|-------------|
| **TM-023** | Missing client security headers / CSP (Nginx default) | T, I | C1, C7 | R0→C4→C7 | CWE-79 (defense-in-depth) *(clickjacking CWE-1021 not in reference set — noted)*; OWASP A05:2021; CIA: I | The Nginx-served SPA sets no CSP, `X-Frame-Options`, `X-Content-Type-Options`, or HSTS. Vue auto-escapes so there is no direct XSS sink today, but the missing headers remove defense-in-depth against clickjacking and against any future injection, and pair with TM-002 (an on-path attacker's injected script faces no CSP). |
| **TM-024** | Terraform state without remote backend / locking — IaC integrity & inventory exposure | T, I | D6, R5 (TB5) | R5-.->D6 (`terraform apply`) | CWE-312; OWASP A05:2021; CIA: I, C | State is a local unencrypted file with no locking and no remote backend. Beyond the PAT (TM-012), it holds the full resource inventory; concurrent/interrupted applies can corrupt it (no locking), and there is no access control or audit around it. Distinct from TM-012 in that it covers state **integrity/availability and inventory disclosure**, not only the embedded secret. |

---

## Design-Level & Zero-Trust Assessment (secure-design principles)

| Principle | Finding | Refs |
|-----------|---------|------|
| **Fail-safe defaults** | System defaults to *open*: no auth, no TLS, open CORS, open egress, open ingress `0.0.0.0/0:80`. Every default favors access over safety. | TM-001, TM-002, TM-006, TM-020 |
| **Least privilege** | Violated at two identities: task role and DevOps role both carry `iam:PassRole *`; DevOps adds `s3:*`/`ecs:*`. | TM-010, TM-016 |
| **Defense in depth** | Single-layer everywhere — the "private subnet" is the only inbound control and it is nullified by public ALBs; no WAF, no egress control, no image scanning, no detection layer. | TM-004, TM-009, TM-017, TM-020, TM-021 |
| **Separation of duties** | None in the deploy path — `main` push = production deploy, one actor, no approval. | TM-013 |
| **Zero trust (verify explicitly)** | No service-to-service or per-request authentication anywhere; trust is by network position (ALB SG) only. | TM-009, TM-011 |
| **Assume breach** | East-west is plaintext HTTP; egress unrestricted; no detection — a breached component is neither contained nor observed. | TM-002, TM-020, TM-021 |
| **Economy of mechanism** | Reasonable — small surface (3 routes). This limits injection surface (see negative result above). Positive observation. | — |

## Business-Logic & Abuse-Case Threats
- **Cost/economic abuse (business flow):** the only meaningful business flow — "fetch catalog" — is abusable for cost amplification (TM-005) and scraping (TM-004) precisely because it is unauthenticated and unmetered. Captured; no separate ID.
- **Workflow bypass / TOCTOU / race conditions:** none material — the app is stateless read-only with no multi-step workflow, no writes, no locking-sensitive logic. Traced and cleared.
- **Insider / authorized-user misuse:** a developer with `main` push (or the operator with the PAT + local state) can ship malicious code to prod undetected (TM-013 + TM-012 + TM-021). Modeled further in Phase 5.

## API-Depth Assessment
REST over HTTP only; no GraphQL/gRPC/WebSocket. API-specific gaps reduce to: broken authentication (TM-001 ≙ API2:2023), unrestricted resource consumption (TM-004/TM-005 ≙ API4:2023), improper inventory management (TM-003 ≙ API9:2023). **Object-level authorization (API1/BOLA)** and **object-property authorization (API3)** are **not applicable** — there are no per-object or per-user resources; the sole endpoint returns the entire public catalog with no object identifiers in the request. Recorded as a traced non-applicability.

## Cloud-Native Threat Assessment
- **IAM & identity:** over-permissive roles + PassRole * (TM-010, TM-016). Long-lived PAT (TM-012). 
- **Instance metadata (IMDS):** credential theft path on container compromise (TM-011).
- **Object storage:** default encryption only, no public-access-block/versioning, `force_destroy` (TM-014).
- **Container supply chain:** mutable ECR, unpinned base images, no scan (TM-017, TM-018), privileged build (TM-015).
- **Cross-tenant isolation:** not applicable — single-tenant, single-account (traced).

## Auth Sequence Diagram
**Not applicable — the system has no authentication or authorization.** There is no credential exchange, token issuance, or session to diagram (`Login.vue` discards its inputs; every route is anonymous). Recorded as a deliberate N/A per skill Phase 3 guidance, consistent with recon §1.9.

## Threat Inventory Summary (Phase 3)
**25 threats identified — TM-001 through TM-025, contiguous, no gaps.** The zone ordering interleaves the ids (TM-013 sits in Zone D, TM-014 in Zone C) but every id TM-001…TM-025 appears exactly once across Zones A-F. Phase 5 appends TM-026 and TM-027 (27 total).

Per-zone counts: A=8 (TM-001–008), B=1 (TM-009), C=4 (TM-010,011,012,014), D=6 (TM-013,015,016,017,018,019), E=4 (TM-020,021,022,025), F=2 (TM-023,024).

**No scores assigned in this phase.** Phase 4 scores every threat; Phase 5 hunts for what this list missed. The complete set is handed to the fresh-context Phase 6 pass for skeptical validation — no self-validation here.
