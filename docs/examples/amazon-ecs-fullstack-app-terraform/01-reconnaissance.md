# Security Architect — Phase 1 Reconnaissance

## Metadata
| Field | Value |
|-------|-------|
| Agent | security-architect |
| Date | 2026-07-11 |
| Target System | AWS ECS Fullstack App (Terraform Demo) |
| Scope | `Infrastructure/` (Terraform IaC), `Code/server` (Node.js API), `Code/client` (Vue.js SPA), `Infrastructure/Templates` (buildspec/appspec/taskdef), `Documentation_assets/` (architecture diagrams) |
| Methodology | Observational reconnaissance (no threat scoring); feeds STRIDE-LM + PASTA in Phases 3-4 |
| Scoring System | N/A (Phase 1 is inventory only) |
| Machine-readable manifests | `recon.json` (attack surface), `coverage.json` (225-item ledger seed) |

## Summary
- **System**: An MIT-0 AWS reference sample. A Vue.js SPA (client) and a Node.js/Express API (server) run as two independent ECS Fargate services, each behind its own **internet-facing** Application Load Balancer in a single VPC, all provisioned by Terraform. A GitHub-triggered CodePipeline (CodeBuild + CodeDeploy blue/green) builds Docker images to ECR and deploys to ECS. The API returns a product catalog from DynamoDB; images are served from S3.
- **Pattern**: `web-app` (fullstack) delivered as cloud IaC. Medium system — 13 components, 6 data stores, 5 external entry points.
- **Defining characteristics for the assessment**: (1) **No authentication or authorization anywhere** — the login screen is an explicit non-functional stub; every endpoint is anonymous. (2) **Both ALBs, including the backend/API ALB, are public and HTTP-only** — no TLS listener is created. (3) The system processes **no personal data** (product catalog: id/path/title). (4) Heavy reliance on an **unpinned, unscanned supply chain** (GitHub PAT, `:latest` base images, no SCA).
- **Gaps flagged**: No image/dependency scanning, no WAF/rate limiting, no ALB/VPC access logging, broad IAM wildcards, GitHub PAT stored in local Terraform state. Detailed as observations below — not yet scored.

---

## 1.1 Visual Comprehension (provided architecture diagrams)

Two PNGs in `Documentation_assets/` were examined.

**`Infrastructure_architecture.png`** — Runtime topology:
- `Users` (Internet) → **Application Load Balancer Front-end** → ECS Cluster "Service Front-end" (AWS Fargate) spread across **AZ1/AZ2**, each in a **Private subnet (Front-end)**.
- Front-end → **Application Load Balancer Back-end** → ECS Cluster "Service Back-end" (Fargate) in **Private subnet (Back-end)**, AZ1/AZ2.
- Autoscaling policies attached to both services.
- A single **IAM Role** node fans out from the back-end tasks to **Amazon DynamoDB** and **Amazon S3**.
- Enclosing boundaries drawn: **Region** → **VPC** → per-AZ subnet groups.
- **Reconciliation with Terraform**: tasks are indeed in private subnets (`private_subnets_server` / `private_subnets_client`), but **both ALBs are `internal = false`** (public subnets, SG `0.0.0.0/0:80`). The diagram's "front→back ALB" arrow understates that the browser reaches the **server ALB directly** (`RestServices.js` calls `http://<SERVER_ALB_URL>/api/getAllProducts`). The back-end ALB is Internet-exposed, not internal.

**`CICD_architecture.png`** — Pipeline topology:
- **CodePipeline** wraps: **GitHub repository** → **CodeBuild** → **CodeDeploy** → **Amazon ECS**; CodeBuild also pushes to **Amazon ECR**; **Amazon SNS** receives deployment notifications. All inside the Region boundary.

## 1.2 Documentation Review (`README.md`, `CONTRIBUTING.md`)
- Self-described **demo** to showcase ECS + DevOps + Terraform. Explicitly states corners are cut "due to demo proposals."
- **Terraform state is stored locally** on the operator machine (README §Infrastructure) — no remote backend, no state encryption/locking by default. The `github_token` (a `sensitive` variable) lands in that plaintext local state.
- Deploy requires an AWS profile with broad create permissions plus a **GitHub Personal Access Token** granting repo access.
- Server exposes exactly 3 routes: `/status` (health), `/api/getAllProducts` (DynamoDB scan), `/api/docs` (Swagger UI). Swagger endpoint is published in the Terraform output.
- No stated security requirements, threat model, data-classification policy, or compliance scope. **No embedded prompt-injection / instruction-channel content** was found in any reviewed file (checked README, code comments, configs) — nothing attempted to redirect the analysis.

## 1.3 Code Scanning
- **Entry points**: `Code/server/src/app.js` (`/status`, `/api/getAllProducts`, `/api/docs`), Swagger router (`swagger.js`). Client routes in `router/index.js` (`/`, `/main`, `/about`, `/search`→`EasterEgg.vue`, `*`→`/`).
- **AuthN/AuthZ**: **None.** `Login.vue` renders username/password fields but `onSubmit()` discards them and routes to `/main` (`<h5>*No auth was implemented, just a Vue.js demo component</h5>`). No middleware, guards, tokens, or session logic on the server. Every API call is anonymous.
- **Configuration / secrets management**: No app secrets. `app.js` reads a hardcoded placeholder `AB3_TABLE = "DYNAMODB_TABLE"` that CodeBuild `sed`-replaces at build (`buildspec.yml:20`). No Secrets Manager / SSM / KMS usage; `taskdef.json` `secretOptions: null`. CodeBuild injects 12 plaintext `environment_variable`s (region, account id, table name, roles, ALB DNS) — none are credentials.
- **IaC**: Terraform (`Infrastructure/`) with 15 modules. `versions.tf` present. No remote backend block (local state).
- **CI/CD & supply chain**: `Infrastructure/Templates/buildspec.yml` (ECR login, `sed` templating, `docker build/push`), `appspec.yaml`, `taskdef.json`. CodePipeline `PollForSourceChanges = true` on branch `main` → any merge to `main` auto-builds and deploys. CodeBuild `privileged_mode = true` (Docker-in-Docker), image `aws/codebuild/standard:4.0`.
- **Data schemas**: DynamoDB table — `hash_key = id (N)`, plus app-level `path (S)`, `title (S)` (README). No migrations/ORM; server does a raw `DocumentClient.scan`.
- **External integrations**: `aws-sdk` v2 (DynamoDB), `axios` (client→server), `cors` (open), GitHub source, public ECR base images.
- **Secrets & sensitive-artifact sweep (whole-tree grep, per Phase 1.3)**: **No committed private keys, certs, `.pem`/`.key`/`id_rsa`, `AKIA…` access keys, or hardcoded passwords/tokens.** `.gitignore` excludes `.env*.local`, `node_modules`, `terraform.tfstate*`. The only credential in the design is the GitHub PAT, passed as a `sensitive` Terraform variable (not committed) but persisted to **local** state and the CodePipeline source config. `Login.vue` "password" field is inert. **Result: clean tree; the PAT-in-local-state is the sole credential-handling concern and is a design observation, not a committed secret.**

## 1.4 Asset Inventory
| ID | Asset | State | Sensitivity | Notes |
|----|-------|-------|-------------|-------|
| D1 | DynamoDB product catalog (id/path/title) | At rest | INTERNAL | Non-personal reference data; default (AWS-owned) encryption, no explicit SSE-KMS, no PITR, no deletion protection |
| D2 | S3 assets bucket (product images) | At rest | INTERNAL/PUBLIC | `acl=private`, `force_destroy=true`; no SSE block, no public-access-block, no versioning, no access logging. Image URLs embedded in client. |
| D3 | S3 CodePipeline artifact bucket | At rest | CONFIDENTIAL | Holds source + build artifacts (app source in transit through the pipeline); same S3 hardening gaps as D2 |
| D4 | ECR repositories (server + client images) | At rest | CONFIDENTIAL | `MUTABLE` tags, no scan-on-push; a `:latest` push can silently replace a running image |
| D5 | CloudWatch Logs (ECS task + CodeBuild) | At rest / processing | INTERNAL | `awslogs` driver, 30-day retention; error handler logs `err` to stderr → logs |
| D6 | Terraform state (local) | At rest | RESTRICTED | Contains the plaintext GitHub PAT and full resource inventory; local file, unencrypted, no locking |
| — | GitHub PAT | In transit / at rest | RESTRICTED | Repo access token; single supply-chain trust anchor |
| — | API responses (`/api/getAllProducts`) | In transit | INTERNAL | Served over **HTTP** (no TLS) from the public server ALB |

## 1.5 Actor Enumeration
**Human actors**
- **Anonymous Internet user** (R0) — the only application principal; reaches both ALBs and Swagger with no credential.
- **Terraform operator / deployer** (R5) — human with broad AWS credentials + GitHub PAT; runs `terraform apply` from a workstation holding local state.
- **Developer with `main` push access** — merging to `main` auto-triggers build+deploy (no manual approval gate).

**System actors / principals** (IAM roles — see `recon.json roles[]`)
- **ECS task execution role** (R1, `ECS-task-excecution-Role`) — `AmazonECSTaskExecutionRolePolicy` (ECR pull, log write).
- **ECS task role** (R2, `ECS-task-Role`) — app runtime identity: DynamoDB read (`Describe*`/`List*`/`Get`/`Query`/`Scan`) on the table, S3 `GetObject`/`ListBucket` on assets, **and `iam:PassRole` on `*`**.
- **DevOps role** (R3) — assumed by CodeBuild/CodeDeploy/CodePipeline; broad `s3:*`/`ecs:*`/`codedeploy:*`/`iam:PassRole` on `*`.
- **CodeDeploy role** (R4) — `AWSCodeDeployRoleForECS` managed policy.
- **CodePipeline / CodeBuild / CodeDeploy services**, **SNS**, **Autoscaling/CloudWatch** — AWS-managed system actors.

## 1.6 Threat Actor Profiles (feed PASTA likelihood in Phase 4)
| ID | Actor | Motivation | Capability (1-5) | Access | Relevance |
|----|-------|-----------|:---:|--------|-----------|
| TA1 | Opportunistic unauthenticated Internet attacker | Data scraping, defacement, resource abuse | 2 | Public HTTP ALBs, Swagger, no auth | **High** — every endpoint is anonymous and plaintext |
| TA2 | Automated bot / botnet (DoS, scanners) | Disruption, enumeration | 2 | Public endpoints; no WAF/rate limit; autoscaling capped at 4 tasks | **High** — cost/availability pressure, no L7 protection |
| TA3 | Malicious insider / compromised developer | Sabotage, backdoor, data theft | 4 | `main` push → auto-deploy; broad DevOps IAM; local TF state | **High** — no deploy approval gate; PAT + state on workstation |
| TA4 | Compromised upstream dependency / base image | Supply-chain implant | 3 | npm installs + `:latest` base images pulled at build; privileged CodeBuild | **Medium-High** — no pinning, no SCA, no image scan |
| TA5 | Post-exploitation attacker inside an ECS task | Lateral movement, privilege escalation, cloud pivot | 4 | Server container → IMDS + task role (`iam:PassRole *`) | **Medium** — depends on an initial app foothold; broad role amplifies blast radius |

## 1.7 Attack Surface Catalog
| ID | Entry point | Location | Protocol | Auth | Exposure | Input types |
|----|-------------|----------|----------|------|----------|-------------|
| E1 | Client ALB | `main.tf:100` SG `0.0.0.0/0:80`; `ALB/main.tf:38` | **HTTP** :80 | None | **Internet** | HTTP GET (static SPA) |
| E2 | Server/API ALB | `main.tf:90` SG `0.0.0.0/0:80`; `app.js:47` | **HTTP** :80 | None | **Internet** | HTTP GET `/api/getAllProducts`, `/status` |
| E3 | Swagger UI `/api/docs` | `swagger.js:42`; published in `outputs.tf:9` | **HTTP** | None | **Internet** | HTTP GET; serves API spec/UI |
| E4 | GitHub source trigger | `CodePipeline/main.tf:20,33` | GitHub v1 poll | PAT | SaaS→pipeline | Source commits on `main` |
| E5 | ALB → task health check | `main.tf:46`; `ALB/main.tf:65` | HTTP | None | Intra-VPC | GET `/status`, `/` |
| — | Egress | NAT → `0.0.0.0/0`; SG egress `-1` to `0.0.0.0/0` | any | — | outbound | Task egress unrestricted |

## 1.8 Security Control Inventory (authoritative for Phase 6)
**Present**
- Network segmentation: tasks in **private subnets**, reachable only from their ALB SG (`security_groups = [alb_sg]`); ALBs in public subnets. NAT for egress.
- Multi-AZ (2 AZs) for ALBs and tasks; autoscaling (CPU/mem target-tracking, min 1 / max 4) + CloudWatch alarms.
- IAM role separation (execution vs task vs devops vs codedeploy); DynamoDB and S3 task-role actions scoped to specific resource ARNs.
- CodeDeploy **blue/green** with auto-rollback on `DEPLOYMENT_FAILURE`; SNS deploy notifications.
- Fargate (no host/EC2 to patch); `awsvpc` networking.
- DynamoDB `PAY_PER_REQUEST` (no provisioned-capacity exhaustion). S3 `acl=private`. GitHub token marked `sensitive`; `ignore_changes` keeps it out of plan drift.
- CloudWatch Logs for tasks (30-day retention).

**Absent / weak (observational — not scored)**
- **No TLS**: only an HTTP:80 listener is created; `enable_https` variable defaults `false` and `main.tf` never sets it. Client uses `http://`; Swagger `schemes: ['http']`. No ACM cert, no HTTP→HTTPS redirect.
- **No authentication/authorization** on any endpoint (app-level).
- **No WAF, no rate limiting, no bot control** in front of the public ALBs.
- **CORS wide open**: `app.use(cors())` (reflects any origin).
- **No ALB access logs, no VPC flow logs**; no GuardDuty/Config/CloudTrail declared in IaC.
- **ECR**: `MUTABLE` tags, no `scan_on_push`. **Base images unpinned** (`node:latest`, `nginx:latest`); no digest pinning, no SBOM/SCA in the pipeline.
- **IAM over-permissioning**: DevOps policy uses `s3:*`/`ecs:*`/`codedeploy:*`/`logs:*`/`iam:PassRole` on `resources = ["*"]`; the **ECS task role has `iam:PassRole` on `*`** (unusual and broad for an app runtime role).
- **CodeBuild `privileged_mode = true`** (Docker-in-Docker); managed image `standard:4.0` (dated).
- **S3**: no server-side-encryption block, no public-access-block, no versioning, no bucket logging; `force_destroy = true` on both buckets.
- **DynamoDB**: no explicit encryption/KMS, no point-in-time recovery, no deletion protection.
- **Error handling leaks detail**: `app.js` error handler returns `{code, description: err.message}` to the client and `console.error`s the raw error; AWS SDK errors have no `.status`, so `res.status(error.code)` can throw (undefined status). `AB3_TABLE` is assigned without `var/let/const` (implicit global).
- **Terraform state local + unencrypted** with the PAT inside; no state locking.
- **No secrets manager**: build-time `sed` templating instead of runtime secret injection (acceptable here since no real secrets, but no path for future ones).

## 1.9 Visual Completeness Applicability (summary — full checklist in `visual-completeness-checklist.md`)
- **Applicable (18)**: External Entities, Processes, Data Stores, Trust Boundaries, Data Flow Labels, Risk Color Coding, Threat Annotations, Component Metadata, Identity Elements (IAM roles), Control/Data Plane, Attack Paths, Control Indicators, Encryption State, Network Zones, Deployment Pipeline, External Dependency Markers, Typed Edges, Ownership Markers, Machine-Parseable Annotations, Version Stamp, Density Compliance — plus **Companion Diagrams** (attack tree for kill chains; **no auth sequence** since there is no AuthN/AuthZ).
- **Not applicable**: Secrets/Key Mgmt (no vault/HSM/KMS in design — mark with note), Data Classification zones (single INTERNAL tier, optional), Tenant Boundaries (single-tenant), Region Boundaries (single region). Justifications recorded per-category in the checklist file.

## 1.10 Reconnaissance Summary
**Components (13)**: Client SPA, Server API, Swagger endpoint, Client ALB, Server ALB, ECS Cluster, ECS client service, ECS server service, CodePipeline, CodeBuild, CodeDeploy, Autoscaling+CloudWatch, SNS. *(recon.json C1-C13)*
**Data stores (6)**: DynamoDB, S3 assets, S3 artifacts, ECR, CloudWatch Logs, local Terraform state. *(D1-D6)*
**Entry points (5)**: Client ALB HTTP, Server ALB HTTP, Swagger, GitHub trigger, health check. *(E1-E5)*
**Trust boundaries (6)**: Internet→public ALBs, public→private subnet, ECS task→AWS services via IAM, CI/CD supply chain, AWS account/region, VPC perimeter (IGW/NAT). *(TB1-TB6)*
**Roles (6)**: anonymous, task-execution, task, devops, codedeploy, terraform-operator. *(R0-R5)*
**External deps (5)**: GitHub+PAT, server npm, client npm, Docker base images (`:latest`), CodeBuild managed image. *(X1-X5)*

**Technology stack**: Vue.js 2 (bootstrap-vue, axios) on Nginx · Node.js/Express 4 + aws-sdk v2 · Docker · AWS ECS Fargate · ALB · DynamoDB · S3 · ECR · CodePipeline/CodeBuild/CodeDeploy · SNS · CloudWatch · IAM · VPC (2 AZ, public+private subnets, IGW, single NAT) · Terraform (≥0.13, local state).

**Gaps & explicit assumptions**
- **Single NAT gateway** (one AZ) — availability single-point; noted, not scored.
- No `.tfvars`/secrets committed, so concrete region/account/env values are unknown — assumed a single region, single environment as the README implies.
- DynamoDB `path`/`title` attributes are app-level (README), not declared in `attributes` (only `id`) — assumed the documented schema.
- **has_personal_data = false**: the login form is inert and the catalog is non-personal; if a real deployment wires auth or stores user data, re-flag privacy scope.
- **has_regulatory = false**: no stated compliance obligation; the compliance specialist still assesses general posture (encryption/logging/access-control hygiene).
- End-user data-lifecycle diagram deemed low-value (no personal data) — omitted.

---

## Coverage States (Phase 1 domain — merged into `coverage.json` by the validation-specialist)
Phase 1 resolves the observational/context items; threat-enumeration, risk, mitigation, and specialist-domain items (privacy, compliance, deep code) remain `unknown` in the seed for their owning phase. States below use taxonomy ids from `coverage-taxonomy.json`.

| Item id | State | Detail / Note | Source |
|---------|-------|---------------|--------|
| document-metadata.identity-version | absent | No threat-model doc exists pre-assessment; this run is version 1, dated 2026-07-11. | README.md |
| document-metadata.ownership | partial | Repo authored by AWS sample (author "Marina Burkhardt"); no TM owner assigned. | Code/server/package.json, swagger.js |
| system-context.deployment-environment | present | AWS ECS Fargate, single VPC (2 AZ), public ALBs, private task subnets, IaC via Terraform local state. | Infrastructure/main.tf, README.md |
| system-context.external-dependencies | present | GitHub, npm (server+client), public ECR base images, CodeBuild managed image. | recon.json external_deps |
| system-context.assumptions-constraints | present | Demo scope; no auth/TLS by design; local TF state; corners cut "due to demo proposals." | README.md |
| assets.data-assets | present | Catalog (DynamoDB), images (S3), artifacts (S3), images (ECR), logs, TF state incl. PAT. | recon.json data_stores |
| data-classification.scheme | partial | No formal scheme; classified INTERNAL/CONFIDENTIAL/RESTRICTED here from observation. | §1.4 |
| actors.human-actors | present | Anonymous user, TF operator, `main`-push developer. | §1.5 |
| actors.system-actors | present | 4 IAM roles + AWS-managed CI/CD/SNS/autoscaling principals. | Infrastructure/Modules/IAM/main.tf |
| trust-boundaries.enumeration | present | 6 boundaries enumerated (TB1-TB6). | recon.json trust_boundaries |
| architecture.diagrams | present | Two provided PNGs reviewed; DFD to be produced in Phase 2. | Documentation_assets/ |
| component-inventory.components | present | 13 components inventoried. | recon.json components |
| data-stores.inventory | present | 6 data stores with tech + hardening gaps. | §1.4 |
| entry-points.enumeration | present | 5 entry points cataloged. | recon.json entry_points |
| authentication.model | absent | No authentication implemented (login is a demo stub). | Code/client/src/components/Login.vue:28 |
| authorization.model | absent | No authorization; all endpoints anonymous. | Code/server/src/app.js |
| network-architecture.segmentation | present | Public ALB subnets vs private task subnets; SG chaining; single NAT egress. | Infrastructure/Modules/Networking/main.tf |
| cryptography.in-transit | partial | Only HTTP:80 listener created; no TLS; `enable_https` defaults false. | Infrastructure/Modules/ALB/main.tf:38, variables.tf:27 |
| cryptography.at-rest | partial | Default AWS-managed encryption only; no explicit SSE/KMS on S3/DynamoDB/ECR. | Infrastructure/Modules/S3/main.tf, Dynamodb/main.tf |
| secrets-management.storage | partial | No secrets manager; GitHub PAT in local TF state + pipeline config; taskdef secretOptions null. | Infrastructure/Modules/CodePipeline/main.tf:29, README.md:37 |
| api-security.authentication | absent | Public API with no client authentication. | Code/server/src/app.js:47 |
| client-side-security.spa | partial | Vue 2 SPA, no CSP/security headers configured (Nginx default), open CORS on API. | Code/client/, Code/server/src/app.js:10 |
| cloud-infrastructure.iam-least-privilege | partial | Resource-scoped DynamoDB/S3, but wildcard `s3:*`/`ecs:*`/`iam:PassRole *` in devops + task roles. | Infrastructure/Modules/IAM/main.tf:175,306 |
| container-security.image-provenance | partial | Unpinned `:latest` base images, MUTABLE ECR tags, no scan-on-push, privileged CodeBuild. | Code/*/Dockerfile, Infrastructure/Modules/ECR/main.tf |
| cicd-supply-chain.pipeline-trust | present | GitHub poll → auto-deploy to `main`, no manual approval; artifact bucket; PAT anchor. | Infrastructure/Modules/CodePipeline/main.tf |
| third-party-vendor.dependencies | partial | npm + base images enumerated; no SCA/SBOM; aws-sdk v2 + Vue 2 are EOL/maintenance. | package.json (server+client) |
| logging-monitoring.coverage | partial | CloudWatch task/build logs only; no ALB access logs, VPC flow logs, CloudTrail in IaC. | Infrastructure/Modules/ECS/TaskDefinition/main.tf:45 |
| availability-resilience.redundancy | present | Multi-AZ, autoscaling, blue/green rollback; single NAT is the redundancy gap. | Infrastructure/main.tf:242, Networking/main.tf:91 |

*(Tier-2 items gated off by context — multi_tenant, has_personal_data, has_regulatory, has_ai_ml, has_hardware — are seeded `not-applicable` in `coverage.json` with reasons. All other applicable items remain `unknown` pending their owning phase/specialist.)*

## Cross-References
- Machine-readable attack surface: `recon.json` (component/store/entry/boundary/dep ids C*/D*/E*/TB*/X*, roles R0-R5).
- Coverage ledger seed: `coverage.json` (context flags + 225 items).
- Downstream: diagram-specialist (Phase 2) builds L1-L3 DFD from these ids; privacy-, compliance-, and code-review specialists read this file + Phase 2 node ids; security-architect Phases 3-6 score threats against §1.6-1.8.

## Execution Log

### Process Health
| Metric | Value |
|--------|-------|
| Files Read | 34 (README, all Terraform root+modules+templates, server app/swagger/Dockerfile/package.json, client Vue components/router/services/config/Dockerfile, 2 architecture PNGs, skill + 3 reference/schema files) |
| Files Written | 4 (recon.json, coverage.json, 01-reconnaissance.md, visual-completeness-checklist.md) |
| Errors Encountered | 1 (recoverable) |
| Items Skipped | 0 |
| Self-Assessed Output Quality | HIGH |

### What Went Well
- Small, well-structured repo (85 files) — full coverage of IaC + app code was feasible without sampling.
- Provided architecture diagrams corroborated the code and surfaced the key nuance (backend ALB is public, not internal).
- Secrets sweep was clean; the single credential (GitHub PAT) traces cleanly to local state + pipeline config.
- Both manifests validated against their JSON schemas (`jsonschema`) with all recon evidence paths resolving in the repo and all 225 taxonomy ids present in the ledger.

### Issues Encountered
- Initial secrets-sweep `grep` failed under zsh due to unquoted `--include=*.js` globbing (no matches error). Re-ran with quoted globs; sweep completed and confirmed no committed secrets. No impact on output.
- This agent context was interrupted after writing the two JSON manifests and resumed to produce the markdown; recon.json/coverage.json were reused as the source of truth, so the markdown, ledger, and manifest are mutually consistent.

### What Was Skipped or Incomplete
- Deep dependency-tree analysis (transitive npm CVEs) deferred to the code-review specialist — Phase 1 records the manifests and EOL/maintenance status (aws-sdk v2, Vue 2) as `partial` coverage, not a full SCA.
- No `.tfvars` present, so concrete region/account/environment values are unknown; recorded as an assumption rather than guessed.
- End-user data-lifecycle companion diagram intentionally omitted (no personal data).

### Assumptions Made
- Default ports assumed from `variables.tf` (server 3001 in container / :80 via ALB, client :80). Container `EXPOSE 3001` (server) confirms.
- DynamoDB `path`/`title` attributes assumed per README (only `id` is declared in `attributes`).
- Single region / single environment assumed (README implies one env; no multi-region resources in IaC).
- `has_personal_data`/`has_regulatory` set false based on observed non-personal data and absent compliance scope; flagged for re-evaluation if a real deployment adds auth or user data.
