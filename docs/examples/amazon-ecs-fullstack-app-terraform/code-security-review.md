# Code Security Specialist — Code Security Review

## Metadata
| Field | Value |
|-------|-------|
| Agent | code-security-specialist |
| Date | 2026-07-11 |
| Target System | AWS ECS Fullstack App (Terraform Demo) |
| Scope | `Code/server/src/app.js`, `Code/server/src/swagger/swagger.js`, `Infrastructure/Modules/IAM/main.tf`, `Infrastructure/Modules/ALB/main.tf`, `Infrastructure/Modules/SecurityGroup/main.tf`, `Infrastructure/Modules/ECR/main.tf`, `Infrastructure/Modules/CodeBuild/main.tf`, `Infrastructure/Modules/CodePipeline/main.tf`, `Infrastructure/Templates/{buildspec.yml,taskdef.json,appspec.yaml}`, `Infrastructure/main.tf` (module wiring), `Code/*/Dockerfile`, `Code/server/package.json`, `Code/client/src/services/RestServices.js` |
| Methodology | Manual secure-code review; CVSS v3.1 scoring; threat-model-directed prioritization against Phase 1 recon + Phase 2 DFD node ids |
| Scoring System | CVSS v3.1 |

## Summary
- Total findings: 6 (0 critical, 4 high, 2 medium, 0 low)
- Top 3 risks: (1) **CR-002** DevOps IAM role is a cloud privilege-escalation primitive — `iam:PassRole` on `*` combined with `ecs:RegisterTaskDefinition` + `ecs:RunTask`, executed by a privileged CodeBuild that runs repo-controlled code; (2) **CR-003** software supply chain has no integrity controls — `:latest` unpinned base images, `MUTABLE` ECR with no scan-on-push, privileged Docker-in-Docker build, tagless `taskdef.json` image; (3) **CR-001** no TLS anywhere — both internet-facing ALBs serve only HTTP:80, so the SPA and every API response are delivered in cleartext.
- Key recommendation: Break the supply-chain escalation chain first — remove `iam:PassRole "*"` and scope `ecs:*` resources on the DevOps role (CR-002), then pin/scan images and add an approval gate (CR-003, CR-004). These are the changes that convert a single merged/compromised commit from "full-account impact" to "contained."

## Findings

### HIGH CR-001: All application traffic served over cleartext HTTP — no TLS listener created

| Field | Value |
|-------|-------|
| ID | CR-001 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | C4, C5, C2, C3, E1, E2, E3, TB1 |
| Scoring System | CVSS v3.1 |
| Score | 7.4 (AV:N/AC:H/PR:N/UI:N/S:U/C:H/I:H/A:N) |
| Cross-Framework | MITRE: N/A (no verified ATT&CK technique maps cleanly to cleartext-transit) · CWE-311 · OWASP A02:2021 |

**Description**: The ALB module only ever creates an HTTP:80 listener. The HTTPS listener is gated behind `enable_https`, which defaults to `false` and is never set to `true` by the root module for either ALB, so no TLS listener, ACM certificate, or HTTP→HTTPS redirect exists. Both ALBs are `internal = false` (internet-facing). The SPA calls the API over `http://`, and Swagger advertises `schemes: ['http']`. Every browser↔ALB and ALB↔task hop is cleartext, exposing an on-path attacker to inject arbitrary JavaScript into the delivered SPA (client takeover, redirection, credential harvesting if auth is ever added) and to read/tamper with API responses.

**Evidence**:
- `Infrastructure/Modules/ALB/main.tf:38-53` — only `aws_alb_listener.http_listener` (port 80, `protocol = "HTTP"`) is unconditional; `https_listener` (line 20-21) is `count = ... var.enable_https == true ? 1 : 0`.
- `Infrastructure/Modules/ALB/variables.tf` — `variable "enable_https" { default = false }`.
- `Infrastructure/main.tf:110-127` — `module "alb_server"` and `module "alb_client"` never pass `enable_https`, so it stays `false`; `aws_alb.alb` has `internal = false` (`ALB/main.tf:14`).
- `Code/client/src/services/RestServices.js:6` — `let serverUrl = "http://<SERVER_ALB_URL>"`.
- `Code/server/src/swagger/swagger.js:23` — `schemes: ['http']`.

**Attack Scenario**:
1. Attacker positions on-path (rogue Wi-Fi, ISP/backbone tap, ARP/DNS spoofing on a shared network) between a user and the client ALB (C4).
2. Because the SPA is delivered over plaintext HTTP, the attacker injects malicious `<script>` into the HTML/JS response.
3. The script runs in the victim's browser with full origin trust — exfiltrating anything the SPA can reach, redirecting the user, or silently proxying the unauthenticated API (C5/E2).

**Existing Mitigations**: Tasks run in private subnets reachable only from the ALB SG; AWS-managed TLS protects the task→DynamoDB/S3 SDK calls (in-cloud). Neither protects the internet-facing browser hop.

**Recommendation**: Provision an ACM certificate, set `enable_https = true` for both ALBs, add an HTTP→HTTPS redirect action on the :80 listener (301 to :443), and switch `RestServices.js`/`swagger.js` to `https`. Enforce HSTS at the ALB/Nginx layer.

---

### HIGH CR-002: DevOps IAM role is a privilege-escalation primitive (`iam:PassRole *` + `ecs:RegisterTaskDefinition`/`RunTask`)

| Field | Value |
|-------|-------|
| ID | CR-002 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | R3, R2, C10, C9, TB4 |
| Scoring System | CVSS v3.1 |
| Score | 8.8 (AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:H) |
| Cross-Framework | MITRE: T1078 · T1098 · CWE-269 · CWE-732 · OWASP A01:2021 |

**Description**: The DevOps role (R3) — assumed by CodeBuild, CodeDeploy, and CodePipeline — grants `iam:PassRole` on `Resource: "*"` alongside a broad set of `ecs:*` actions including `ecs:RegisterTaskDefinition`, `ecs:RunTask`, `ecs:StartTask`, and `ecs:UpdateService`, all on `Resource: "*"`. `iam:PassRole *` + `RegisterTaskDefinition` + `RunTask` is a well-known AWS escalation chain: the principal can register a task definition whose `taskRoleArn` points at **any** role in the account (e.g., an administrative role) and run it, thereby executing code with that role's permissions. Because CodeBuild (C10) runs *as* this role (`service_role = module.devops_role.arn_role`) and executes attacker-influenceable content from the repo (buildspec commands, `npm install` scripts, Dockerfile), any actor who can land a commit on `main` (or poison a dependency — see CR-003) inherits the full DevOps role and this escalation path. The ECS **task role** (R2) — the runtime identity of the internet-facing, unauthenticated Node service — separately carries `iam:PassRole` on `"*"`; it lacks a service action to consume it today, but it is a latent over-grant that widens the blast radius of any app-layer RCE/SSRF.

**Evidence**:
- `Infrastructure/Modules/IAM/main.tf:286-293` (DevOps policy) — `sid = "AllowIAMPassRole"`, `actions = ["iam:PassRole"]`, `resources = ["*"]`.
- `Infrastructure/Modules/IAM/main.tf:260-285` (DevOps policy) — `sid = "AllowCECSServiceActions"` includes `ecs:RegisterTaskDefinition`, `ecs:RunTask`, `ecs:StartTask`, `ecs:UpdateService`, `ecs:CreateTaskSet`, all with `resources = ["*"]`. S3 statement (line 176-187) and CloudWatch statement (line 294-303) also use `resources = ["*"]`.
- `Infrastructure/Modules/IAM/main.tf:316-323` (ECS task-role policy) — `sid = "AllowIAMPassRole"`, `actions = ["iam:PassRole"]`, `resources = ["*"]`.
- `Infrastructure/main.tf:301-316` — `module "codebuild_server"` sets `iam_role = module.devops_role.arn_role`; `Infrastructure/Modules/CodeBuild/main.tf:12` binds it as `service_role`.

**Attack Scenario**:
1. Attacker gets code to run inside CodeBuild — via a merged commit to `main`, a malicious transitive npm dependency, or a poisoned base image (CR-003).
2. The build step, running as the DevOps role, calls `iam:PassRole` on a high-privilege role plus `ecs:RegisterTaskDefinition`/`ecs:RunTask` (or `sts` against a passable role).
3. The attacker now executes with that role's permissions — pivoting beyond the pipeline to broader account resources.

**Existing Mitigations**: IAM role separation exists (execution vs. task vs. devops vs. codedeploy); DynamoDB and S3-assets actions on the task role are ARN-scoped. These do not constrain `iam:PassRole *` or the wildcard-resource `ecs:*` grants.

**Recommendation**: Remove `iam:PassRole "*"` from both R3 and R2. Where PassRole is genuinely needed (CodeDeploy passing the ECS execution/task roles), scope it to those specific role ARNs and add an `iam:PassedToService` condition (`ecs-tasks.amazonaws.com`). Scope `ecs:RegisterTaskDefinition`/`RunTask`/`UpdateService` to the specific cluster/service ARNs. Delete the PassRole statement from the ECS task role entirely (the app has no use for it).

---

### HIGH CR-003: Software supply chain has no integrity controls — unpinned `:latest` images, mutable ECR, privileged build

| Field | Value |
|-------|-------|
| ID | CR-003 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | C10, D4, C7, C8, X4, TB4 |
| Scoring System | CVSS v3.1 |
| Score | 8.3 (AV:N/AC:H/PR:N/UI:R/S:C/C:H/I:H/A:H) |
| Cross-Framework | MITRE: T1195 · CWE-732 · OWASP A08:2021 |

**Description**: There is no image or dependency integrity control anywhere in the build-to-deploy path:
- **Unpinned base images**: the server Dockerfile pulls `public.ecr.aws/bitnami/node:latest` and the client production stage `public.ecr.aws/nginx/nginx:latest` — no digest pinning, so the image content can change under the same tag between builds.
- **Mutable registry, no scanning**: the ECR module hardcodes `image_tag_mutability = "MUTABLE"` and sets no `image_scanning_configuration { scan_on_push = true }`, so a pushed tag (including `:latest`) can be silently overwritten and images are never scanned for CVEs.
- **Privileged build**: CodeBuild runs `privileged_mode = true` (Docker-in-Docker) on the dated `aws/codebuild/standard:4.0` image, maximizing the impact of any build-time compromise (host/daemon access) — and it runs as the over-privileged DevOps role (CR-002).
- **Tagless deploy reference**: CodeBuild pushes `$REPO_URL:$IMAGE_TAG` with `IMAGE_TAG = "latest"`, while `taskdef.json` references the image as bare `<REPO_URL>` (no tag/digest), so ECS resolves the mutable `:latest` at deploy time — a push swaps what runs in production.
- **Non-reproducible installs**: both Dockerfiles run `npm install` (not `npm ci`), ignoring the lockfile pin and allowing newer/unexpected transitive versions; no SCA/SBOM step exists in `buildspec.yml`.

**Evidence**:
- `Code/server/Dockerfile:4` — `FROM public.ecr.aws/bitnami/node:latest`; `Code/client/Dockerfile:13` — `FROM public.ecr.aws/nginx/nginx:latest`.
- `Infrastructure/Modules/ECR/main.tf:8-11` — `image_tag_mutability = "MUTABLE"`, no scanning block.
- `Infrastructure/Modules/CodeBuild/main.tf:19-22` — `image = "aws/codebuild/standard:4.0"`, `privileged_mode = true`; `main.tf:39-42` — `environment_variable { name = "IMAGE_TAG", value = "latest" }`.
- `Infrastructure/Templates/buildspec.yml:33` — `docker push $REPO_URL:$IMAGE_TAG`; `Infrastructure/Templates/taskdef.json:6` — `"image": "<REPO_URL>"` (no tag/digest).
- `Code/server/Dockerfile:12` / `Code/client/Dockerfile:8` — `RUN npm install`.

**Attack Scenario**:
1. Attacker compromises an upstream `:latest` base image or a transitive npm dependency (or opens a PR that a maintainer merges).
2. The privileged CodeBuild pulls the poisoned artifact and builds the image with no scan or integrity check, running the malicious code with DevOps-role credentials during the build.
3. The image is pushed to the mutable `:latest` tag and auto-deployed (CR-004); ECS pulls the tampered image on task start, running attacker code in production.

**Existing Mitigations**: Blue/green deploy with auto-rollback on `DEPLOYMENT_FAILURE` (does not detect a *functionally healthy but backdoored* image); the client build stage pins the minor tag `node:16` (still mutable).

**Recommendation**: Pin base images by digest (`FROM ...@sha256:...`) and keep the tag for readability. Set `image_tag_mutability = "IMMUTABLE"` and `image_scanning_configuration { scan_on_push = true }` on ECR; deploy by immutable tag or digest, not `:latest`. Switch Dockerfiles to `npm ci`. Add a dependency/image scan (e.g., `npm audit`/SCA + ECR enhanced scanning) as a gating build step. Remove `privileged_mode` unless Docker-in-Docker is strictly required; upgrade off `standard:4.0`.

---

### HIGH CR-004: GitHub PAT stored in cleartext (local state + pipeline config) and auto-deploy has no approval gate

| Field | Value |
|-------|-------|
| ID | CR-004 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | C9, X1, D6, R5, TB4 |
| Scoring System | CVSS v3.1 |
| Score | 8.7 (AV:L/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H) |
| Cross-Framework | MITRE: T1552 · T1195 · CWE-312 · CWE-306 · OWASP A08:2021 |

**Description**: The GitHub Personal Access Token — the single trust anchor of the supply chain — is passed as `OAuthToken = var.github_token` directly into the CodePipeline source-action configuration and, because Terraform state is local and unencrypted (README §Infrastructure), is persisted in cleartext in `terraform.tfstate` (D6). It is a long-lived token with no rotation. Compounding this, the pipeline uses GitHub v1 source with `PollForSourceChanges = true` on branch `main` and defines **no manual approval action** between Source→Build→Deploy, so any commit reaching `main` is automatically built (privileged, CR-003) and blue/green-deployed to production. Leakage of the state file (laptop backup, accidental commit, workstation compromise) yields full repo control, which — via auto-deploy — yields production code execution.

**Evidence**:
- `Infrastructure/Modules/CodePipeline/main.tf:28-34` — `configuration = { OAuthToken = var.github_token, ... PollForSourceChanges = true }`.
- `Infrastructure/Modules/CodePipeline/main.tf:17-107` — three stages (Source, Build, Deploy) with **no `category = "Approval"` action**; Deploy actions run automatically after Build.
- `Infrastructure/main.tf:362-379` — `module "codepipeline"` wires `github_token = var.github_token`; README documents local (unencrypted, unlocked) Terraform state, so the `sensitive` variable lands in `terraform.tfstate`.
- The `ignore_changes = [stage[0].action[0].configuration]` lifecycle (line 111) reduces plan drift but does not remove the token from state.

**Attack Scenario**:
1. The local `terraform.tfstate` leaks (backup sync, `git add .`, stolen/compromised operator workstation — R5).
2. Attacker extracts the plaintext PAT and pushes a malicious commit to `main`.
3. With no approval gate, the pipeline auto-builds (privileged) and blue/green-deploys the attacker's code to production; the PAT also grants direct repository control.

**Existing Mitigations**: `github_token` is a `sensitive` Terraform variable and is not committed to the repo; `ignore_changes` keeps it out of plan diffs. Neither encrypts state at rest nor adds a deploy gate.

**Recommendation**: Migrate to a remote encrypted, locked state backend (S3 + DynamoDB lock, SSE-KMS) or, better, replace the PAT with a GitHub App / CodeStar (CodeConnections) connection so no long-lived token is stored. Add a manual approval action before the Deploy stage. Rotate the PAT and scope it to least privilege. Prefer webhook-based triggers over `PollForSourceChanges`.

---

### MEDIUM CR-005: Unauthenticated, unthrottled public API with wildcard CORS behind open `0.0.0.0/0` ALBs

| Field | Value |
|-------|-------|
| ID | CR-005 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | C2, C5, C4, E2, E3, TB1 |
| Scoring System | CVSS v3.1 |
| Score | 6.5 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:L) |
| Cross-Framework | MITRE: T1190 · T1498 · CWE-306 · CWE-770 · OWASP A07:2021 |

**Description**: Every API endpoint is anonymous, the app enables fully permissive CORS (`app.use(cors())` reflects any origin with no allowlist), and there is no application-level rate limiting or upstream WAF. Both ALB security groups open ingress to `0.0.0.0/0:80`, and the backend/API ALB is `internal = false`, so `/api/getAllProducts` (a full DynamoDB `scan`), `/status`, and the Swagger UI/JSON at `/api/docs` are directly reachable from the Internet by any client and any web origin. With no throttling, an attacker can hammer the DynamoDB scan (billed `PAY_PER_REQUEST` → unbounded cost) and drive ECS autoscaling (capped at 4 tasks) toward saturation — a low-effort cost/availability abuse — while Swagger discloses the full API contract to aid enumeration.

**Evidence**:
- `Code/server/src/app.js:10` — `app.use(cors())` (no origin allowlist); `app.js:47-68` — `/api/getAllProducts` performs `docClient.scan` with no auth check and no input constraints.
- `Code/server/src/swagger/swagger.js:42` — `router.use('/', swaggerUi.serve, swaggerUi.setup(swaggerSpec))` mounted at `/api/docs`, publicly served.
- `Infrastructure/main.tf:90-107` — both ALB SG modules set `cidr_blocks_ingress = ["0.0.0.0/0"]`, `ingress_port = 80`; `Infrastructure/Modules/SecurityGroup/main.tf:13-19` opens that ingress; `ALB/main.tf:14` — `internal = false`.
- No WAF (`aws_wafv2_web_acl_association`) or rate-limit middleware exists anywhere in the tree.

**Attack Scenario**:
1. Attacker scripts high-rate requests to `http://<server-alb>/api/getAllProducts` from many sources (no WAF/rate limit stops them).
2. Each call triggers a DynamoDB scan and CPU on the server tasks, inflating `PAY_PER_REQUEST` cost and pushing autoscaling to its cap.
3. Legitimate users see degraded availability while the account accrues cost; open CORS additionally lets any third-party website read the endpoint from victims' browsers.

**Existing Mitigations**: The catalog data is non-personal/public product info (limits confidentiality impact); DynamoDB is on-demand (no fixed-capacity throttling failure); autoscaling absorbs some load. No control caps request volume or origin.

**Recommendation**: Put a WAF (rate-based rule + managed rule groups) in front of both ALBs; add app-level rate limiting (e.g., `express-rate-limit`). Replace `cors()` with an explicit origin allowlist. Restrict/authenticate `/api/docs` or serve it only in non-production. If the API is only meant to be reached via the client, make the API ALB `internal` or restrict its SG to the client tier rather than `0.0.0.0/0`.

---

### MEDIUM CR-006: Error handler leaks internal error detail and can crash on `res.status(undefined)`

| Field | Value |
|-------|-------|
| ID | CR-006 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | C2, C8, E2 |
| Scoring System | CVSS v3.1 |
| Score | 4.8 (AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:N/A:L) |
| Cross-Framework | MITRE: N/A · CWE-209 · CWE-755 · OWASP A05:2021 |

**Description**: Error handling is fragile and over-shares. On a DynamoDB failure the `/api/getAllProducts` handler returns `{ code: err.status, description: err.message }` to the anonymous client — `err.message` exposes internal AWS/SDK detail (table names, validation messages, region/service internals). The AWS SDK v2 error object has no `.status` property (it uses `.code`, a string, and `.statusCode`, a number), so `code` is `undefined`. In the Express global error handler, `res.status(error.code)` is called with that (possibly `undefined`/non-integer) value, which throws `RangeError: Invalid status code` and 500s/aborts the response for any non-HTTP error routed through it. The line `status: err.status || 500` is a no-op JavaScript label statement (dead code — it assigns nothing), and `AB3_TABLE = "DYNAMODB_TABLE"` is assigned with no `var/let/const`, creating an implicit global (a `ReferenceError` under strict mode).

**Evidence**:
- `Code/server/src/app.js:54-59` — `docClient.scan(...)` error branch: `res.send({ code: err.status, description: err.message })`.
- `Code/server/src/app.js:78-88` — global handler: `console.error(...err)`, `let error = { code: err.status, description: err.message }`, dead label `status: err.status || 500`, then `res.status(error.code).send(error)`.
- `Code/server/src/app.js:48` — `AB3_TABLE = "DYNAMODB_TABLE"` (no declaration keyword → implicit global).

**Attack Scenario**:
1. A condition causes a DynamoDB error (throttle, transient service error, misconfiguration).
2. The client receives `description: <internal AWS error message>`, disclosing implementation detail useful for reconnaissance.
3. If a non-HTTP error reaches the global handler, `res.status(undefined)` throws, turning a handled error into a dropped/aborted response.

**Existing Mitigations**: The 404 handler sets a numeric `err.status = 404`, so the common not-found path does not hit the crash; errors are also logged to CloudWatch.

**Recommendation**: Return a generic client message (`{ error: "Internal Server Error" }`) with a fixed 500 and log details server-side only. Use `err.statusCode`/a validated integer for `res.status()`, defaulting to 500; guard with `Number.isInteger`. Declare `AB3_TABLE` with `const` and enable `'use strict'`. Fix the dead `status:` label to an actual assignment or remove it.

## Observations
- **No injectable query surface**: `/api/getAllProducts` performs a fixed-`TableName` `DocumentClient.scan` with zero user-supplied parameters, so there is no NoSQL/expression-injection vector on the sole data endpoint — a genuine positive for an unauthenticated API.
- **Meaningful IAM scoping does exist**: the ECS task role's DynamoDB and S3-assets actions are ARN-scoped (`IAM/main.tf:306-336`), and CodeBuild/CodeDeploy resource-scope several statements (`code_build_projects`, `ecr_repositories`, `code_deploy_resources`). The wildcards in CR-002 are the exception, not the rule — remediation is surgical, not a rewrite.
- **Network segmentation is sound**: ECS tasks live in private subnets and their SGs admit ingress only from the paired ALB SG (`main.tf:186-203`), so the tasks are not directly Internet-reachable; the exposure is at the ALB edge, which is the right place to add WAF/TLS.
- **Blue/green with auto-rollback** is configured for both services, a real availability control (it does not, however, detect a healthy-but-backdoored image — see CR-003).
- **No committed secrets** were found in the reviewed files; the only credential is the GitHub PAT handled as a `sensitive` variable (the concern is its cleartext persistence in local state, CR-004, not a hardcoded secret).

## Assumptions & Limitations
- **No transitive-dependency CVE scan (full SCA) was run.** `package.json` pins are declared (`aws-sdk ^2.876.0` — v2 is in maintenance/EOL; the client uses Vue 2, also EOL), but I did not resolve `package-lock.json` against a CVE database. CR-003 addresses the *absence of a scanning control*, not a specific enumerated CVE. A dedicated SCA pass is recommended.
- **Runtime behavior was inferred from source, not executed.** The CVSS exploitability judgments (e.g., the `res.status(undefined)` crash in CR-006, the `iam:PassRole` escalation in CR-002) are based on code/config reading and standard AWS/Node semantics, not a live deploy.
- **`.tfvars` values (region, account id, repo owner/branch, PAT) are not present** in the repo, so concrete resource ARNs and the GitHub target are unknown; findings reference the code paths that consume them.
- **Scope was the recon's top-risk surfaces** (`app.js`, IAM/ALB/SG/ECR modules, CI/CD templates and CodeBuild/CodePipeline). Lower-risk modules (SNS, Autoscaling, Cluster, per-service Networking internals) were read for wiring context but not line-audited.

## Cross-References
- **Phase 1 recon** (`01-reconnaissance.md`): §1.8 (control inventory), §1.6 threat actors — CR-001↔TA1, CR-002/003/004↔TA3/TA4/TA5, CR-005↔TA2. Asset ids D3/D4/D6 and role ids R2/R3 reused here.
- **Phase 2 DFD** (`02-structural-diagram.md`): node ids C2/C4/C5/C9/C10, D4/D6, R2/R3, E1/E2/E3, TB1/TB4, X1/X4 as cited per finding.
- **Related downstream**: CR-001 (transport) and CR-004 (secrets/pipeline) overlap the compliance specialist's encryption/access-control controls; CR-005 CORS/rate-limit and CR-002 IAM overlap the threat-model TM- findings (spoofing/EoP/DoS on TB1/TB4). The validation-specialist should dedupe CR-001↔any TM in-transit-encryption finding, CR-002↔any TM IAM/EoP finding, and CR-003/CR-004↔any TM supply-chain finding, keeping the CVSS-scored CR- variant as the code-level evidence anchor.
- **Framework IDs**: all CWE / MITRE ATT&CK / OWASP ids used above were checked against `references/frameworks.md` (present in that file). Where no verified ATT&CK technique mapped cleanly (CR-001, CR-006), MITRE is recorded as N/A rather than guessed.

## Coverage States
Code-review-domain coverage-ledger item states for the validation-specialist to merge into `coverage.json`. States use the taxonomy ids seeded by Phase 1; these resolve items the recon left `partial`/`absent`/`unknown` for the owning (code-review) phase.

| Item id | State | Detail / Note | Finding |
|---------|-------|---------------|---------|
| cryptography.in-transit | absent | Only an HTTP:80 listener is created for both internet-facing ALBs; `enable_https` defaults false and is never set. Client + Swagger use `http`. No ACM cert, no redirect, no HSTS. | CR-001 |
| api-security.authentication | absent | No authentication on any endpoint; all anonymous (confirms recon). | CR-005 |
| api-security.authorization | absent | No authorization/access control; every route is public. | CR-005 |
| api-security.input-validation | partial | Sole data endpoint takes no user-supplied parameters (fixed-`TableName` scan → no injectable surface), but there is no schema/request validation framework and CORS is wildcard-open. | CR-005 |
| api-security.error-handling | absent | Error handler leaks internal `err.message` to clients and can crash on `res.status(undefined)`; implicit-global and dead-code defects present. | CR-006 |
| client-side-security.spa | partial | Vue 2 SPA over HTTP; no CSP/security headers (default Nginx); open CORS on the API it calls. | CR-001, CR-005 |
| cloud-infrastructure.iam-least-privilege | partial | DynamoDB/S3-assets and several CI/CD statements are ARN-scoped, but DevOps role has `iam:PassRole "*"` + wildcard-resource `ecs:*`/`s3:*`-action/`logs:*` statements, and the ECS task role has `iam:PassRole "*"`. | CR-002 |
| container-security.image-provenance | absent | `:latest` unpinned base images (no digest), ECR `MUTABLE` with no `scan_on_push`, tagless `taskdef.json` image, privileged Docker-in-Docker build, `npm install` (not `ci`); no SBOM/SCA. | CR-003 |
| cicd-supply-chain.pipeline-trust | partial | Pipeline exists and uses blue/green + rollback, but has no manual approval gate between Build and Deploy and polls `main` for auto-deploy; privileged build runs as over-privileged DevOps role. | CR-003, CR-004 |
| secrets-management.storage | partial | GitHub PAT passed as `OAuthToken` in pipeline config and persisted cleartext in local, unencrypted, unlocked Terraform state; long-lived, no rotation. No committed secrets otherwise. | CR-004 |
| third-party-vendor.dependencies | partial | Dependencies declared with `^` ranges; `aws-sdk` v2 (maintenance/EOL) and Vue 2 (EOL); `npm install` ignores lockfile pinning; no SCA/SBOM control. Full transitive-CVE scan not performed. | CR-003 |
| network-architecture.public-exposure | partial | ECS tasks correctly isolated in private subnets (ingress only from ALB SG), but both ALB SGs open `0.0.0.0/0:80` and the backend/API ALB is `internal = false`; no WAF/rate limiting at the edge. | CR-005 |
| logging-monitoring.coverage | partial | CloudWatch task/build logs present (30-day retention); error handler `console.error`s raw error objects to stderr→logs. No ALB access logs / VPC flow logs / CloudTrail in IaC (unchanged from recon). | CR-006 |

## Execution Log

### Process Health
| Metric | Value |
|--------|-------|
| Files Read | 24 (2 phase outputs + agent-output-protocol; app.js, swagger.js, RestServices.js; IAM/ALB/SecurityGroup/ECR/CodeBuild/CodePipeline/S3/Dynamodb module main.tf; root main.tf; buildspec.yml/taskdef.json/appspec.yaml; server+client Dockerfile; server package.json; ALB/ECR variables.tf; frameworks.md) |
| Files Written | 1 (code-security-review.md) |
| Errors Encountered | 0 |
| Items Skipped | 0 blocking; full transitive-dependency SCA intentionally deferred (see below) |
| Self-Assessed Output Quality | HIGH |

### What Went Well
- Small, self-contained repo — the top-risk surfaces flagged by recon were all readable in full, with no sampling. Every finding carries a concrete `file:line` code/config citation.
- Recon and the Phase 2 DFD gave clean node ids (C*/D*/R*/E*/TB*/X*), so cross-referencing was direct.
- Verified every CWE / MITRE / OWASP id against `references/frameworks.md` before use; used N/A rather than guessing where no verified technique fit (CR-001, CR-006).
- Traced the actual privilege-escalation chain end to end (CodeBuild `service_role` → DevOps role `iam:PassRole *` + `ecs:RegisterTaskDefinition`/`RunTask`) rather than reporting the wildcard in isolation.

### Issues Encountered
- Recon phrased the DevOps grants as "`s3:*`/`ecs:*` wildcards." On reading the policy, the *action names are enumerated* (not `*`); the wildcard is on `resources = ["*"]`, and the sharp risk is the `iam:PassRole "*"` + `ecs:RegisterTaskDefinition`/`RunTask` combination. CR-002 states this precisely to avoid an over-broad, easily-rebutted finding. No impact on severity.

### What Was Skipped or Incomplete
- **Full SCA / transitive CVE enumeration** not performed (no lockfile-vs-CVE resolution). CR-003 targets the *missing scanning control*; a specific-CVE pass remains open. Impact: a concrete vulnerable-package list is not enumerated here.
- **Lower-risk Terraform modules** (SNS, Autoscaling, ECS Cluster/Service internals, Networking internals) were read only for wiring context, not line-audited — consistent with the directed top-risk scope. Impact: minor misconfigurations in those modules, if any, are not covered.
- **No live/dynamic testing** — findings are from static review; runtime-dependent judgments are noted as such in Assumptions.

### Assumptions Made
- Assumed local, unencrypted Terraform state per README (no remote backend block in IaC), making the PAT cleartext-at-rest (CR-004).
- Assumed AWS SDK v2 error semantics (`.code` string / `.statusCode` number, no `.status`) for the CR-006 `res.status(undefined)` crash analysis.
- Assumed both ALBs remain `enable_https = false` because the root module never overrides the module default (confirmed: not passed in `alb_server`/`alb_client`).
- Assumed the catalog data is non-personal/public (per recon `has_personal_data = false`), which caps the confidentiality impact in CR-005/CR-006 CVSS scoring.
