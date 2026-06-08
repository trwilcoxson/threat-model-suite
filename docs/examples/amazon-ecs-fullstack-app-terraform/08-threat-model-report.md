# Security Architect -- Phase 8 Threat Model Summary

## Metadata
| Field | Value |
|-------|-------|
| Agent | security-architect |
| Date | 2026-02-18 |
| Target System | Amazon ECS Fullstack App (Terraform Demo) |
| Scope | Full system: 14 Terraform modules, Node.js backend, Vue.js frontend, AWS CI/CD pipeline |
| Methodology | STRIDE-LM + PASTA + OWASP Risk Rating |
| Scoring System | OWASP Risk Rating (Likelihood 1-5 x Impact 1-5) |

---

## 1. Executive Summary

**Overall Security Posture: CONCERNING**

This AWS ECS demo/reference architecture contains significant security gaps that make it unsuitable for production use without substantial hardening. While expected for a demonstration project, organizations forking this repository as a production starting point face serious risk.

| Severity | Count |
|----------|-------|
| CRITICAL | 2 |
| HIGH | 10 |
| MEDIUM | 11 |
| LOW | 3 |
| **Total** | **26** |

**Top 3 Risks**:

1. **Repository-sourced buildspec with broad IAM (TM-004, CRITICAL, Score 25)**: Any developer with GitHub push access can execute arbitrary commands with near-admin AWS permissions. This is a 4-step chain from git push to full AWS account compromise with zero gates at any step.

2. **IAM PassRole on wildcard resource (TM-003, CRITICAL, Score 20)**: Both the DevOps role and ECS task role can pass any IAM role in the account, enabling privilege escalation from any code execution context to full account admin.

3. **No TLS on public-facing ALBs (TM-001, HIGH, Score 15)**: All user traffic traverses the internet in plaintext. While the current data is public, this enables traffic interception and response modification (including JavaScript injection into the SPA).

**Key Strengths Observed**:
- Private subnets for ECS tasks with security group segmentation (good east-west isolation)
- Fargate launch type (AWS-managed infrastructure isolation)
- Blue/Green deployment with auto-rollback on failure
- Read-only DynamoDB access from the application (least privilege for data operations)
- awsvpc network mode enabling per-task security group enforcement

---

## 2. Validated Findings Summary Table

| ID | Threat | Severity | STRIDE-LM | Likelihood | Impact | Risk Score | Confidence | Affected Component(s) |
|----|--------|----------|-----------|------------|--------|------------|------------|----------------------|
| TM-004 | Repository-Sourced Buildspec + Broad IAM | CRITICAL | T,E,LM | 5 | 5 | 25 | HIGH | CodeBuild, CodePipeline, DevOpsRole, GitHub |
| TM-003 | Overly Broad IAM PassRole (*) | CRITICAL | E,LM | 4 | 5 | 20 | HIGH | DevOpsRole, ECSTaskRole, CodeBuild, ServerECS |
| TM-023 | No Branch Protection on Repository | HIGH | T,R | 4 | 4 | 16 | MEDIUM | GitHub, CodePipeline |
| TM-013 | CodeBuild Privileged Docker Mode | HIGH | E,LM | 4 | 4 | 16 | HIGH | CodeBuild |
| TM-014 | No Pipeline Approval Gates / Scanning | HIGH | T,R | 4 | 4 | 16 | HIGH | CodePipeline, CodeBuild, CodeDeploy |
| TM-001 | No TLS/HTTPS on Public ALBs | HIGH | I,T | 5 | 3 | 15 | HIGH | ClientALB, ServerALB |
| TM-002 | No Authentication or Authorization | HIGH | S,E | 5 | 3 | 15 | HIGH | ServerALB, ServerECS, ClientALB, ClientECS |
| TM-005 | GitHub Token in Terraform State | HIGH | I,S | 3 | 5 | 15 | HIGH | TFState, GitHubToken, CodePipeline |
| TM-006 | Mutable ECR Tags + Latest Pattern | HIGH | T | 3 | 5 | 15 | MEDIUM | ECR, CodeBuild, ServerECS, ClientECS |
| TM-007 | No WAF or Rate Limiting | HIGH | D | 4 | 3 | 12 | HIGH | ClientALB, ServerALB |
| TM-022 | Unrestricted Egress from ECS Tasks | HIGH | I,LM | 3 | 4 | 12 | HIGH | ServerECS, ClientECS, SG_ECS |
| TM-024 | No Billing Alarm / Cost Detection | HIGH | D | 4 | 3 | 12 | HIGH | DynamoDB, ServerECS |
| TM-009 | S3 Buckets Missing Security Controls | MEDIUM | I,T | 3 | 3 | 9 | MEDIUM | S3Assets, S3Pipeline |
| TM-011 | No VPC Flow Logs | MEDIUM | R | 3 | 3 | 9 | HIGH | VPC |
| TM-015 | Outdated Dependencies | MEDIUM | T,E | 3 | 3 | 9 | MEDIUM | ServerECS, ClientECS, CodeBuild |
| TM-017 | ECS Container Hardening Deficiencies | MEDIUM | E,LM | 3 | 3 | 9 | HIGH | ServerECS, ClientECS |
| TM-012 | Error Handler Info Leakage + Bug | MEDIUM | I | 4 | 2 | 8 | HIGH | ServerECS |
| TM-025 | npm install vs npm ci | MEDIUM | T | 2 | 4 | 8 | HIGH | CodeBuild, ServerECS, ClientECS |
| TM-008 | Unrestricted CORS | MEDIUM | S | 3 | 2 | 6 | HIGH | ServerECS |
| TM-018 | Single NAT Gateway (SPOF) | MEDIUM | D | 2 | 3 | 6 | HIGH | VPC, ServerECS, ClientECS |
| TM-021 | No Container Insights / Monitoring | MEDIUM | R | 3 | 2 | 6 | HIGH | CloudWatch, ServerECS, ClientECS |
| TM-026 | No CloudTrail Data Events | MEDIUM | R | 3 | 2 | 6 | HIGH | DynamoDB, S3Assets, S3Pipeline |
| TM-016 | Swagger Docs Publicly Exposed | MEDIUM | I | 5 | 1 | 5 | HIGH | ServerECS, ServerALB |
| TM-010 | DynamoDB Missing PITR + CMK | LOW | I,T | 2 | 2 | 4 | HIGH | DynamoDB |
| TM-019 | No VPC Endpoints | LOW | I,D | 2 | 2 | 4 | HIGH | ServerECS, ClientECS |
| TM-020 | SNS No Subscribers / Encryption | LOW | R,I | 3 | 1 | 3 | HIGH | SNS |

---

## 3. Remediation Priority List

### Wave 1: Quick Wins (HIGH impact, LOW effort, no dependencies)
*Target: 1-2 days. These are configuration changes with outsized security impact.*

| R-ID | Recommendation | Addresses | Effort | Dependencies |
|------|---------------|-----------|--------|-------------|
| R-001 | Set ECR `image_tag_mutability = "IMMUTABLE"` | TM-006 | LOW | None |
| R-002 | Add `aws_s3_bucket_public_access_block` to both buckets | TM-009 | LOW | None |
| R-003 | Enable DynamoDB PITR: `point_in_time_recovery { enabled = true }` | TM-010 | LOW | None |
| R-004 | Replace `npm install` with `npm ci` in Dockerfiles | TM-025 | LOW | None |
| R-005 | Create AWS billing alarm ($50 threshold) | TM-024 | LOW | None |
| R-006 | Enable ECR scan-on-push | TM-006, TM-014 | LOW | None |
| R-007 | Add VPC gateway endpoints for DynamoDB and S3 (free) | TM-019, TM-018 | LOW | None |
| R-008 | Add SNS subscription for deployment notifications | TM-020 | LOW | None |
| R-009 | Fix error handler: sanitize responses, fix labeled statement bug | TM-012 | LOW | None |
| R-010 | Configure CORS with specific origin | TM-008 | LOW | None |

### Wave 2: Critical Security Fixes (HIGH impact, MEDIUM effort)
*Target: 1-2 sprints. These address the CRITICAL and highest HIGH findings.*

| R-ID | Recommendation | Addresses | Effort | Dependencies |
|------|---------------|-----------|--------|-------------|
| R-011 | Scope IAM PassRole to specific role ARNs (remove wildcard) | TM-003 | MEDIUM | None |
| R-012 | Move buildspec inline in Terraform or to separate restricted repo | TM-004 | MEDIUM | None |
| R-013 | Enable GitHub branch protection (required reviews, status checks) | TM-023 | MEDIUM | None |
| R-014 | Add manual approval action in CodePipeline (between Build and Deploy) | TM-014 | MEDIUM | R-013 |
| R-015 | Enable HTTPS: create ACM cert, enable HTTPS listener, add HTTP redirect | TM-001 | MEDIUM | ACM certificate provisioning |
| R-016 | Migrate GitHub source to CodeStar Connections (v2) | TM-005 | MEDIUM | R-013 |
| R-017 | Migrate to remote Terraform backend (S3 + DynamoDB with encryption) | TM-005 | MEDIUM | None |
| R-018 | Associate AWS WAF with both ALBs (managed rules + rate limiting) | TM-007 | MEDIUM | None |
| R-019 | Restrict SG egress to required destinations only | TM-022 | MEDIUM | R-007 (VPC endpoints reduce required egress) |

### Wave 3: Hardening and Monitoring (MEDIUM impact, MEDIUM effort)
*Target: 2-4 sprints. Defense-in-depth improvements.*

| R-ID | Recommendation | Addresses | Effort | Dependencies |
|------|---------------|-----------|--------|-------------|
| R-020 | Enable VPC Flow Logs | TM-011 | MEDIUM | None |
| R-021 | Enable ECS Container Insights | TM-021 | LOW | None |
| R-022 | Add container hardening (readonlyRootFilesystem, non-root user, health checks) | TM-017 | MEDIUM | Application testing |
| R-023 | Enable CloudTrail with data events | TM-026 | MEDIUM | None |
| R-024 | Add security scanning stage to pipeline (SCA, container scan, SAST) | TM-014, TM-015 | MEDIUM | R-014 |
| R-025 | Update dependencies (Express, aws-sdk v3, Axios, Vue 3 migration) | TM-015 | HIGH | Application refactoring |
| R-026 | Disable Swagger in production (conditional on NODE_ENV) | TM-016 | LOW | None |
| R-027 | Deploy NAT GW per AZ for high availability | TM-018 | MEDIUM | None |

### Wave 4: Production Readiness (Addresses remaining gaps)
*Target: Before production launch.*

| R-ID | Recommendation | Addresses | Effort | Dependencies |
|------|---------------|-----------|--------|-------------|
| R-028 | Implement authentication (Cognito, Auth0, or custom) | TM-002 | HIGH | Application redesign |
| R-029 | Add VPC interface endpoints for ECR, CloudWatch, SNS | TM-019 | MEDIUM | R-007 |
| R-030 | Use git commit SHA as image tag instead of `latest` | TM-006 | LOW | R-001 |
| R-031 | Remove `force_destroy = true` from S3 buckets | TM-009 | LOW | None |
| R-032 | Add S3 versioning for pipeline artifacts bucket | TM-009 | LOW | None |
| R-033 | Enable SNS encryption with KMS | TM-020 | LOW | None |

### Dependency Graph

```
R-007 --> R-019 (VPC endpoints reduce egress requirements)
R-013 --> R-014 (branch protection before pipeline gates)
R-013 --> R-016 (branch protection before connection migration)
R-014 --> R-024 (pipeline gates before adding scan stages)
R-001 --> R-030 (immutable tags before SHA-based tagging)
```

---

## 4. Assumptions and Scope

### Assumptions
1. **Single AWS account deployment** -- no cross-account references found. In a multi-account setup, PassRole risk may differ.
2. **No pre-existing AWS security services** (GuardDuty, Config, CloudTrail, SecurityHub) active in the account outside this Terraform code.
3. **No GitHub branch protection rules** configured (not managed by Terraform, not mentioned in README).
4. **Demo/reference architecture** -- findings are assessed in context of production adoption risk, not demo-appropriate shortcuts.
5. **DynamoDB contains only public product catalog data** (no PII, no financial data).
6. **Fargate platform version LATEST** -- no known platform-level vulnerabilities assumed.
7. **AWS default S3 encryption (SSE-S3)** is active on new buckets (AWS default since January 2023).
8. **No additional IAM policies** attached to the roles outside of what is defined in this Terraform code.

### What Was Not Analyzed
- Runtime vulnerability scanning (npm audit not executed)
- Docker image vulnerability scanning (base images not scanned)
- Penetration testing or dynamic analysis
- Terraform plan/apply validation
- AWS account-level settings (SCPs, Organizations, root account MFA)
- GitHub organization-level security settings

### Threat Model Lifecycle Triggers
Re-assess this threat model when:
- Any authentication or authorization is added
- The application handles user data or PII
- New API endpoints are added
- The system is deployed to a production AWS account
- New AWS services are integrated
- The CI/CD pipeline structure changes
- The application migrates to a different compute platform

---

## Execution Log

### Process Health
| Metric | Value |
|--------|-------|
| Phases Executed | 3, 4, 5, 6, 8 |
| Files Read | 12 (01-reconnaissance.md, 02-structural-diagram.md, frameworks.md, analysis-checklists.md, agent-output-protocol.md, app.js, iam/main.tf, alb/main.tf, s3/main.tf, ecr/main.tf, codepipeline/main.tf, codebuild/main.tf, TaskDefinition/main.tf, SecurityGroup/main.tf, Networking/main.tf, buildspec.yml) |
| Files Written | 5 (03-threat-identification.md, 04-risk-quantification.md, 05-false-negative-hunting.md, 06-validated-findings.md, 08-threat-model-report.md) |
| Errors Encountered | 0 |
| Items Skipped | 0 |
| Self-Assessed Output Quality | HIGH |

### What Went Well
- Reconnaissance file (01-reconnaissance.md) was thorough and well-structured, providing a strong foundation for all analysis phases
- Structural diagram (02-structural-diagram.md) included a clear Node ID Reference table, making component cross-referencing straightforward
- Code verification during Phases 3-4 confirmed all reconnaissance findings and revealed additional details (error handler bug, security group egress configuration)
- Kill chain analysis in Phase 5 successfully identified 5 additional threats that were missed in the initial STRIDE-LM pass, particularly the unrestricted egress (TM-022) and branch protection gap (TM-023)
- Framework ID verification caught 6 IDs not in the reference tables and remapped them appropriately

### Issues Encountered
- None significant. All source files were readable and the project structure was well-organized.

### What Was Skipped or Incomplete
- **AI/ML assessment**: Not applicable -- no AI/ML components in this system.
- **LINDDUN privacy assessment**: Deferred to the privacy-agent. The system currently processes no personal data, so architectural privacy threats are minimal.
- **Terraform plan execution**: Static analysis only. Actual Terraform state and plan output were not examined.
- **npm audit**: Not executed. Dependency vulnerability assessment in TM-015 is based on version numbers only, not confirmed CVE mapping.

### Assumptions Made
- All 8 assumptions listed in Section 4 above
- The labeled statement bug in app.js line 85 was verified by reading the source code -- it is confirmed as a JavaScript labeled statement, not a variable assignment
- AWS SDK calls from ECS tasks use HTTPS by default (standard SDK behavior, not explicitly configured in the application code)
- The DevOps role's CloudWatch permissions (CreateLogGroup, CreateLogStream, PutLogEvents) do NOT include Delete operations, which was verified during Kill Chain 1 analysis
