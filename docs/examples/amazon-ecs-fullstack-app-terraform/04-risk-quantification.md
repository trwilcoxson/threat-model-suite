# Security Architect -- Phase 4 Risk Quantification

## Metadata
| Field | Value |
|-------|-------|
| Agent | security-architect |
| Date | 2026-02-18 |
| Target System | Amazon ECS Fullstack App (Terraform Demo) |
| Scope | Scoring all 21 threats identified in Phase 3 |
| Methodology | PASTA Stages 6-7 + OWASP Risk Rating |
| Scoring System | OWASP Risk Rating (Likelihood 1-5 x Impact 1-5) |

---

## Scored Threat Table

### TM-001: No TLS/HTTPS on Public-Facing Load Balancers

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-4 (Network-Position Attacker), TA-1 (Opportunistic) |
| Attack Path Summary | 1. Attacker positions on any network segment between user and AWS (public WiFi, ISP, corporate proxy). 2. Intercept HTTP traffic to ClientALB or ServerALB. 3. Read or modify all request/response data in transit. |
| Preconditions | Network position between user and ALB. Trivial on public WiFi or shared networks. |
| Existing Controls to Bypass | None. No TLS configured. Security groups are irrelevant to MITM. |
| Likelihood | **5** -- Trivially exploitable. HTTP traffic is inherently interceptable. No special skills needed -- tools like Wireshark, mitmproxy, or even browser dev tools on a shared network. TA-4 rates this as their primary attack vector. TA-1 can also exploit this with readily available tools. |
| Impact | **3** -- Currently serves only public product catalog data (low confidentiality impact). However, traffic modification could inject malicious JavaScript into SPA responses (high integrity impact for users). If the application adds any sensitive data in the future, impact escalates to 4-5. Driving dimension: Integrity (modified responses serve malicious content). |
| Risk Score | **15** |
| Severity | **HIGH** |

### TM-002: Complete Absence of Authentication and Authorization

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-1 (Opportunistic), TA-2 (Malicious Insider) |
| Attack Path Summary | 1. Navigate to ServerALB URL (publicly discoverable). 2. Access any API endpoint without credentials. 3. Enumerate full API via Swagger docs. 4. Call any endpoint with any parameters. |
| Preconditions | Internet access. Nothing else required. |
| Existing Controls to Bypass | None. No authentication exists. |
| Likelihood | **5** -- Zero skill required. Any internet user already has full access. TA-1 does not even need to "attack" -- the system is open by design. |
| Impact | **3** -- Currently the API is read-only (DynamoDB scan) and serves public product data. No write operations, no sensitive data, no user-specific data. If the application evolves to include write endpoints, user data, or admin functions, impact escalates to 5. Driving dimension: Operational (any unauthenticated user can consume API resources, and the application cannot enforce any business logic around user identity). |
| Risk Score | **15** |
| Severity | **HIGH** |

### TM-003: Overly Broad IAM PassRole Permissions

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-2 (Malicious Insider), TA-3 (Supply Chain) |
| Attack Path Summary | 1. Achieve code execution in ServerECS (via dependency vulnerability) or CodeBuild (via buildspec modification). 2. Use the ECSTaskRole or DevOpsRole's `iam:PassRole *` permission. 3. Create or update an AWS resource (Lambda, ECS task, EC2 instance) and pass an admin-level role to it. 4. Execute commands with the passed role's permissions, achieving privilege escalation to any role in the account. |
| Preconditions | Code execution in a context that assumes the ECSTaskRole or DevOpsRole. For DevOpsRole, this is trivially achievable via TM-004 (buildspec modification). For ECSTaskRole, requires exploiting a dependency vulnerability or injection in the Node.js application. |
| Existing Controls to Bypass | IAM role assumption is constrained to ecs-tasks.amazonaws.com principal. The attacker cannot directly assume other roles, but PassRole allows delegating any role to new resources. Fargate isolation prevents host-level escape but does not prevent IAM API calls. |
| Likelihood | **4** -- High likelihood because the DevOps role path requires only GitHub push access (TM-004). The ECS task role path requires code execution but the application has outdated dependencies (TM-015) and runs as root (TM-017). TA-2 has direct access to trigger this. |
| Impact | **5** -- Full AWS account compromise. PassRole on * means the attacker can escalate to any IAM role, access any resource, exfiltrate data from any S3 bucket or DynamoDB table in the account, modify infrastructure, or establish persistent backdoor access. Driving dimension: Financial + Operational (complete account takeover). |
| Risk Score | **20** |
| Severity | **CRITICAL** |

### TM-004: Repository-Sourced Buildspec with Broad IAM Permissions

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-2 (Malicious Insider / Compromised Developer) |
| Attack Path Summary | 1. Gain push access to the GitHub repository (TA-2 already has this; or compromise a developer account). 2. Modify `Infrastructure/Templates/buildspec.yml` to add arbitrary commands (e.g., `aws sts get-caller-identity`, `aws s3 ls`, exfiltrate secrets). 3. Push to main branch (no branch protection). 4. CodePipeline detects changes, triggers CodeBuild. 5. Arbitrary commands execute with DevOps IAM role permissions in a privileged Docker container. 6. Exfiltrate AWS credentials, access any S3 bucket, modify ECS task definitions, or use PassRole to escalate further. |
| Preconditions | GitHub push access to the main branch. No other preconditions -- no approval gate, no buildspec verification. |
| Existing Controls to Bypass | None in the pipeline. The only barrier is GitHub access control (which is external to this system and assumed to have no branch protection per Phase 1 assumptions). |
| Likelihood | **5** -- Trivially exploitable by anyone with repo push access. The buildspec path is configurable via Terraform but defaults to the repository. No verification or approval step exists. TA-2 can execute this with zero additional effort beyond a git push. |
| Impact | **5** -- The DevOps role has PassRole *, S3 *, ECS *, ECR push, CodeDeploy, and CloudWatch Logs. This is effectively AWS account admin access. A malicious buildspec can exfiltrate all secrets, deploy malicious containers, modify or destroy infrastructure, and establish persistent access. Driving dimension: All four dimensions are maximum -- this is a complete infrastructure compromise path. |
| Risk Score | **25** |
| Severity | **CRITICAL** |

### TM-005: GitHub OAuth Token Exposure in Terraform State

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-2 (Malicious Insider), TA-5 (Negligent Insider) |
| Attack Path Summary | 1. Access the deployer's workstation or the local filesystem where Terraform state is stored. 2. Read `terraform.tfstate` file. 3. Extract the GitHub OAuth token from the CodePipeline resource configuration. 4. Use the token to access the GitHub repository (read, write, potentially admin). 5. Chain to TM-004 (modify buildspec) for full infrastructure compromise. |
| Preconditions | Access to the deployer's local filesystem. For TA-2, this could be an adjacent workstation or shared drive. For TA-5, accidental commit of the state file to a repository. |
| Existing Controls to Bypass | The `github_token` Terraform variable is marked `sensitive = true`, which prevents it from showing in plan output. However, the state file contains it in plaintext. No file-level encryption or access controls are documented. |
| Likelihood | **3** -- Requires physical or remote access to a specific workstation. This is not trivially accessible from the internet. However, local state files are a known antipattern frequently found accidentally committed to repositories, left on shared drives, or accessible through workstation compromise. TA-5 makes accidental exposure likely over time. |
| Impact | **5** -- The GitHub token provides repository access, which chains directly to TM-004 (buildspec modification -> AWS account compromise). The token may also grant access to other repositories under the same GitHub user. Driving dimension: Operational (complete compromise chain). |
| Risk Score | **15** |
| Severity | **HIGH** |

### TM-006: Mutable ECR Image Tags with Latest Tag Pattern

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-3 (Supply Chain), TA-2 (Malicious Insider) |
| Attack Path Summary | 1. Gain ECR push access (via DevOps role through TM-004, or compromised AWS credentials). 2. Build a malicious Docker image with a backdoor. 3. Push it to ECR with the `latest` tag, overwriting the legitimate image. 4. On next ECS deployment (or service restart), the malicious image is pulled and runs in production. |
| Preconditions | ECR push access. Achievable through the DevOps role (TM-004 chain) or compromised AWS credentials with ECR permissions. |
| Existing Controls to Bypass | None -- mutable tags allow unrestricted overwrite. No image signing, no image scanning, no digest verification. |
| Likelihood | **3** -- Requires ECR push access, which is not trivially available from the internet. However, the DevOps role has ECR push permissions, and TM-004 provides a direct path to that role. TA-3 could also compromise the image via the supply chain (malicious base image from public ECR). |
| Impact | **5** -- A malicious container image runs with the ECSTaskRole, which has DynamoDB access, S3 access, and PassRole *. The attacker can exfiltrate data, modify application behavior, establish persistence, and use PassRole to escalate further. Driving dimension: Integrity + Operational (complete application compromise). |
| Risk Score | **15** |
| Severity | **HIGH** |

### TM-007: No WAF or Rate Limiting on Public Endpoints

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-1 (Opportunistic) |
| Attack Path Summary | 1. Identify the public ALB endpoints (trivially discoverable). 2. Launch volumetric attack from botnet or cloud instances. 3. Overwhelm ECS autoscaling (max 4 tasks). 4. Application becomes unresponsive. Alternatively, DynamoDB auto-scales causing excessive AWS costs. |
| Preconditions | Internet access and ability to generate traffic volume. Botnet access is readily available for purchase on dark web. |
| Existing Controls to Bypass | ECS autoscaling provides minimal mitigation (max 4 tasks). ALB itself has some AWS-level DDoS protection (AWS Shield Standard), but no application-layer protection. |
| Likelihood | **4** -- DDoS-as-a-service is commoditized. Any internet-facing endpoint without WAF/rate limiting is a target. The Swagger docs make the API surface trivially discoverable, making targeted L7 attacks easy. |
| Impact | **3** -- Application unavailability and/or excessive AWS costs. For a production application, this could mean revenue loss and customer churn. DynamoDB PAY_PER_REQUEST means billing scales with attack volume. Driving dimension: Financial (uncontrolled cloud spend) + Operational (service unavailability). |
| Risk Score | **12** |
| Severity | **HIGH** |

### TM-008: Unrestricted CORS Configuration

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-1 (Opportunistic) |
| Attack Path Summary | 1. Create a malicious website that makes cross-origin requests to the ServerALB. 2. Trick a user into visiting the malicious site. 3. Malicious JavaScript makes API calls to the server endpoint. 4. Responses are readable because CORS allows all origins. |
| Preconditions | User visits a malicious website while having network access to the server ALB. |
| Existing Controls to Bypass | None -- `app.use(cors())` without options allows all origins. |
| Likelihood | **3** -- The attack is technically simple, but the current API only serves public data with no authentication. There is nothing user-specific to steal. The risk is primarily forward-looking (if auth or user data is added). |
| Impact | **2** -- Currently minimal: the API returns the same public data to everyone. If authentication were added, impact would escalate to 4 (cross-site data theft). Driving dimension: Currently low across all dimensions. |
| Risk Score | **6** |
| Severity | **MEDIUM** |

### TM-009: S3 Buckets Missing Security Controls

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-5 (Negligent Insider), TA-2 (Malicious Insider) |
| Attack Path Summary | 1. (Accidental) A future Terraform change adds a permissive bucket policy without public_access_block as a safety net. 2. S3Pipeline bucket becomes publicly accessible, exposing build artifacts with IAM role ARNs and task definitions. 3. (Malicious) TA-2 uses S3 access from DevOps role to read/modify build artifacts, potentially injecting malicious task definitions. |
| Preconditions | For accidental exposure: a Terraform change that adds a public policy (no additional access needed). For malicious access: S3 permissions (available to DevOps role). |
| Existing Controls to Bypass | ACL is "private", which provides a baseline but is easily overridden by bucket policies. No public_access_block to prevent policy misconfiguration. |
| Likelihood | **3** -- S3 bucket misconfiguration is one of the most common cloud security incidents. The absence of public_access_block means there is no safety net for future misconfigurations. |
| Impact | **3** -- S3Assets contains public product images (low impact). S3Pipeline contains build artifacts with IAM role ARNs, task definition templates, and deployment specs (medium impact -- useful for attacker reconnaissance and potential artifact tampering). `force_destroy = true` means all objects are deleted on `terraform destroy` with no confirmation. Driving dimension: Integrity (artifact tampering) + Operational (accidental destruction). |
| Risk Score | **9** |
| Severity | **MEDIUM** |

### TM-010: DynamoDB Missing Point-in-Time Recovery and CMK Encryption

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-5 (Negligent Insider) |
| Attack Path Summary | 1. Accidental or malicious deletion of DynamoDB table items. 2. No PITR means no recovery to a prior state. 3. Manual re-seeding of data required (if seed data exists). |
| Preconditions | Write access to the DynamoDB table (not currently available from the application, but available via AWS console or CLI with appropriate IAM permissions). |
| Existing Controls to Bypass | ECSTaskRole has read-only DynamoDB access (good). Deletion requires direct AWS console/CLI access with different IAM permissions. |
| Likelihood | **2** -- The application has read-only DynamoDB access, so accidental deletion from the app is not possible. Requires AWS console or CLI access. The data is a simple product catalog that can likely be re-seeded from the initialization scripts. |
| Impact | **2** -- Product catalog data is low-sensitivity and likely reproducible. The impact is primarily operational disruption while data is restored. No customer data loss, no regulatory implications. Driving dimension: Operational (temporary data loss). |
| Risk Score | **4** |
| Severity | **LOW** |

### TM-011: No VPC Flow Logs or Network Monitoring

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-2 (Malicious Insider), TA-1 (Opportunistic) |
| Attack Path Summary | 1. Attacker gains access to VPC (via compromised ECS task or other vector). 2. Performs network reconnaissance and lateral movement. 3. All network activity is invisible -- no flow logs, no detection, no alerting. 4. Attacker operates undetected for extended period. |
| Preconditions | An attacker must first gain a foothold in the VPC. This is a secondary finding that amplifies the impact of other threats. |
| Existing Controls to Bypass | N/A -- there are no network monitoring controls to bypass. |
| Likelihood | **3** -- VPC Flow Logs are a basic AWS security control, and their absence is a common finding. The likelihood is derived from the probability of needing forensic evidence after an incident (moderate for internet-facing applications). |
| Impact | **3** -- Without flow logs, incident response and forensic investigation are severely hampered. Attackers can operate undetected, and there is no evidence trail for post-incident analysis. This does not cause direct damage but significantly amplifies the impact of other threats. Driving dimension: Operational (blind spot in detection and response). |
| Risk Score | **9** |
| Severity | **MEDIUM** |

### TM-012: Error Handler Information Leakage and Code Bug

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-1 (Opportunistic) |
| Attack Path Summary | 1. Send requests to nonexistent endpoints or trigger DynamoDB errors. 2. Read error responses that contain internal error codes and messages. 3. DynamoDB SDK errors may reveal table names, region, and SDK version. 4. The JavaScript labeled statement bug on line 85 may cause unexpected behavior (status always defaults to error.code or undefined). |
| Preconditions | Internet access to the server ALB. |
| Existing Controls to Bypass | None -- error handler directly returns internal details. |
| Likelihood | **4** -- Trivially triggerable by any request to a nonexistent path. Error messages are returned without any sanitization. |
| Impact | **2** -- Information leakage is low-impact for this application (product catalog). DynamoDB table names and SDK details provide reconnaissance value. The code bug may cause occasional 500 errors or undefined status codes. Driving dimension: Confidentiality (minor information leakage). |
| Risk Score | **8** |
| Severity | **MEDIUM** |

### TM-013: CodeBuild Privileged Docker Mode

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-2 (Malicious Insider) |
| Attack Path Summary | This is a force multiplier for TM-004. When an attacker modifies the buildspec: 1. Commands execute in a privileged Docker container. 2. Privileged mode grants elevated Linux capabilities. 3. Combined with the DevOps IAM role, the attacker has both OS-level root and broad AWS API access. |
| Preconditions | Same as TM-004 -- GitHub push access. Privileged mode is already enabled. |
| Existing Controls to Bypass | None -- privileged mode is explicitly configured in the CodeBuild project. |
| Likelihood | **4** -- Same as TM-004 (this finding is inseparable from it). Privileged mode is required for Docker builds, so the configuration is intentional, but it increases the blast radius of TM-004. |
| Impact | **4** -- Amplifies TM-004's impact. Privileged containers can access host resources, mount filesystems, and perform operations that non-privileged containers cannot. However, CodeBuild's managed environment already limits the impact compared to self-hosted runners. Driving dimension: All dimensions (force multiplier). |
| Risk Score | **16** |
| Severity | **HIGH** |

### TM-014: No Pipeline Approval Gates or Security Scanning

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-2 (Malicious Insider), TA-3 (Supply Chain) |
| Attack Path Summary | 1. Any commit to main branch triggers full pipeline. 2. Source stage has no verification beyond GitHub polling. 3. Build stage has no SAST, SCA, or container scanning. 4. No manual approval between build and deploy. 5. Code flows directly from commit to production without human review or automated security checks. |
| Preconditions | Push access to the repository's main branch. |
| Existing Controls to Bypass | None -- the pipeline has no gates of any kind. |
| Likelihood | **4** -- The absence of gates is a certainty. The likelihood score reflects how easily a malicious or buggy commit reaches production. With no approval step and no branch protection, every push to main is an automatic production deployment. |
| Impact | **4** -- Malicious code or vulnerable dependencies can reach production undetected. The blue/green deployment with auto-rollback on DEPLOYMENT_FAILURE provides some protection against broken deployments but not against subtle malicious changes that pass health checks. Driving dimension: Integrity (untrusted code in production). |
| Risk Score | **16** |
| Severity | **HIGH** |

### TM-015: Outdated and Vulnerable Dependencies

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-3 (Supply Chain), TA-1 (Opportunistic) |
| Attack Path Summary | 1. Identify outdated dependency versions (Express 4.16.4, aws-sdk v2, Axios 0.21.2). 2. Cross-reference with public CVE databases. 3. Exploit known vulnerability in a publicly facing component. 4. Gain code execution in ServerECS or ClientECS. |
| Preconditions | A known CVE in one of the deployed dependency versions that is exploitable in this application's usage context. |
| Existing Controls to Bypass | Fargate isolation limits container escape. Security groups limit lateral movement from ECS tasks. However, the application runs as root with writable filesystem (TM-017). |
| Likelihood | **3** -- Outdated dependencies are a known risk, but exploitation depends on whether the specific versions contain exploitable CVEs in the code paths this application uses. Express 4.16.x is several major versions behind, and Axios 0.21.x had known SSRF vulnerabilities. Without running `npm audit`, exact CVE applicability is uncertain. |
| Impact | **3** -- Code execution in ServerECS provides access to DynamoDB, S3, and the PassRole * permission chain (TM-003). Code execution in ClientECS is lower impact (Nginx serving static files). Driving dimension: Confidentiality + Integrity (through IAM role exploitation). |
| Risk Score | **9** |
| Severity | **MEDIUM** |

### TM-016: Swagger API Documentation Publicly Exposed

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-1 (Opportunistic) |
| Attack Path Summary | 1. Navigate to `{ServerALB}/api/docs`. 2. Enumerate all API endpoints, request/response schemas, and parameter types. 3. Use this information to craft targeted attacks against the API. |
| Preconditions | Internet access to the server ALB. |
| Existing Controls to Bypass | None -- endpoint is completely public. |
| Likelihood | **5** -- Trivially accessible. Swagger UI is a well-known path that automated scanners check. |
| Impact | **1** -- The current API has only two functional endpoints (getAllProducts and status). The Swagger documentation reveals nothing beyond what basic API enumeration would discover. Impact would increase if the API grows. Driving dimension: Confidentiality (minor reconnaissance value). |
| Risk Score | **5** |
| Severity | **MEDIUM** |

### TM-017: ECS Container Hardening Deficiencies

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-3 (Supply Chain), TA-1 (Opportunistic) |
| Attack Path Summary | 1. Achieve code execution in a container (via dependency vulnerability or other vector). 2. Root access allows installing additional tools (curl, wget, nmap). 3. Writable filesystem allows modifying application code, writing persistence mechanisms. 4. No health check means malicious modifications may not trigger service restart. |
| Preconditions | Code execution within the container. This finding amplifies other threats. |
| Existing Controls to Bypass | Fargate isolation prevents host-level escape. awsvpc network mode limits network-level lateral movement via security groups. |
| Likelihood | **3** -- Requires initial code execution (achievable through dependency vulnerabilities or supply chain compromise). This is a secondary finding that amplifies the blast radius of other threats. |
| Impact | **3** -- Root access in a container with ECSTaskRole (DynamoDB + S3 + PassRole *). Writable filesystem allows tool installation and application modification. The Fargate isolation limits container escape but does not limit IAM API abuse. Driving dimension: All dimensions (amplifier finding). |
| Risk Score | **9** |
| Severity | **MEDIUM** |

### TM-018: Single NAT Gateway Creates Single Point of Failure

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-1 (Opportunistic -- targeting availability) |
| Attack Path Summary | 1. AZ hosting the NAT Gateway experiences an outage (AWS AZ failure, or targeted attack against NAT GW). 2. All private subnet instances lose outbound internet connectivity. 3. ECS tasks cannot reach DynamoDB, S3, ECR, or CloudWatch (no VPC endpoints configured). 4. Application becomes completely non-functional. |
| Preconditions | AZ failure or NAT Gateway failure. This is a reliability/availability concern rather than a targeted attack. |
| Existing Controls to Bypass | N/A -- this is an availability design gap, not an attack that bypasses controls. |
| Likelihood | **2** -- AWS AZ failures are rare but do occur. The combination of single NAT GW and no VPC endpoints means a single AZ failure causes a complete outage. For a demo application, this is acceptable. For production, it is not. |
| Impact | **3** -- Complete application outage. All backend API calls fail (DynamoDB and S3 unreachable). Application is non-functional until NAT GW or AZ recovers. Driving dimension: Operational (complete outage). |
| Risk Score | **6** |
| Severity | **MEDIUM** |

### TM-019: No VPC Endpoints for AWS Services

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-4 (Network-Position Attacker) |
| Attack Path Summary | 1. AWS SDK calls from ECS tasks traverse NAT GW to public internet to AWS endpoints. 2. While HTTPS is used (encrypted), traffic exits the VPC unnecessarily. 3. Increases dependency on NAT GW (amplifies TM-018). 4. Higher latency for AWS API calls. |
| Preconditions | N/A -- this is an architectural design gap. |
| Existing Controls to Bypass | AWS SDK uses HTTPS by default, providing encryption in transit. This mitigates the confidentiality risk. |
| Likelihood | **2** -- The confidentiality risk is low because AWS SDK uses HTTPS. The primary risks are availability (NAT GW dependency) and cost (data transfer charges through NAT GW). |
| Impact | **2** -- HTTPS encryption protects data in transit. The main impact is availability (amplifies TM-018) and cost (unnecessary NAT GW data transfer charges). Driving dimension: Operational + Financial (minor). |
| Risk Score | **4** |
| Severity | **LOW** |

### TM-020: SNS Topic with No Subscribers and No Encryption

| Field | Value |
|-------|-------|
| Threat Actor(s) | TA-5 (Negligent Insider -- missing operational alerting) |
| Attack Path Summary | Not an active attack path. The risk is operational: deployment events are published to a topic with no subscribers, so no one is notified of deployments (successful or failed). This means suspicious deployments (potentially triggered by TM-004) go unnoticed. |
| Preconditions | N/A -- this is a monitoring gap. |
| Existing Controls to Bypass | N/A. |
| Likelihood | **3** -- The gap exists with certainty. The likelihood score reflects the probability of needing deployment alerting (moderate for any CI/CD pipeline). |
| Impact | **1** -- Low direct impact. Deployment metadata (application name, deployment group, status) is low-sensitivity. The operational impact is reduced visibility into deployment activity. Driving dimension: Operational (minor -- reduced visibility). |
| Risk Score | **3** |
| Severity | **LOW** |

### TM-021: No Container Insights or Application Monitoring

| Field | Value |
|-------|-------|
| Threat Actor(s) | All actors (this gap benefits all attackers by reducing detection) |
| Attack Path Summary | Not an active attack path. The gap means anomalous behavior (unusual API call patterns, resource exhaustion, error spikes) goes undetected. Attackers exploiting other vulnerabilities can operate without triggering alerts. |
| Preconditions | N/A -- monitoring gap. |
| Existing Controls to Bypass | CloudWatch Logs receive container stdout/stderr, but no analysis or alerting is configured. Autoscaling metrics exist but only trigger scaling, not security alerts. |
| Likelihood | **3** -- The gap exists with certainty. Any attacker activity benefits from the absence of monitoring. |
| Impact | **2** -- Does not cause direct damage but reduces detection capability. Mean time to detect (MTTD) for any security incident is significantly increased. Driving dimension: Operational (detection gap). |
| Risk Score | **6** |
| Severity | **MEDIUM** |

---

## Risk Summary Table

| ID | Threat | L | I | Score | Severity | Confidence |
|----|--------|---|---|-------|----------|------------|
| TM-004 | Repository-Sourced Buildspec with Broad IAM | 5 | 5 | 25 | CRITICAL | HIGH |
| TM-003 | Overly Broad IAM PassRole Permissions | 4 | 5 | 20 | CRITICAL | HIGH |
| TM-013 | CodeBuild Privileged Docker Mode | 4 | 4 | 16 | HIGH | HIGH |
| TM-014 | No Pipeline Approval Gates or Security Scanning | 4 | 4 | 16 | HIGH | HIGH |
| TM-001 | No TLS/HTTPS on Public-Facing ALBs | 5 | 3 | 15 | HIGH | HIGH |
| TM-002 | Complete Absence of Authentication/Authorization | 5 | 3 | 15 | HIGH | HIGH |
| TM-005 | GitHub OAuth Token in Terraform State | 3 | 5 | 15 | HIGH | HIGH |
| TM-006 | Mutable ECR Image Tags + Latest Pattern | 3 | 5 | 15 | HIGH | MEDIUM |
| TM-007 | No WAF or Rate Limiting | 4 | 3 | 12 | HIGH | HIGH |
| TM-009 | S3 Buckets Missing Security Controls | 3 | 3 | 9 | MEDIUM | MEDIUM |
| TM-011 | No VPC Flow Logs | 3 | 3 | 9 | MEDIUM | HIGH |
| TM-015 | Outdated and Vulnerable Dependencies | 3 | 3 | 9 | MEDIUM | MEDIUM |
| TM-017 | ECS Container Hardening Deficiencies | 3 | 3 | 9 | MEDIUM | HIGH |
| TM-008 | Unrestricted CORS Configuration | 3 | 2 | 6 | MEDIUM | HIGH |
| TM-012 | Error Handler Information Leakage | 4 | 2 | 8 | MEDIUM | HIGH |
| TM-018 | Single NAT Gateway (SPOF) | 2 | 3 | 6 | MEDIUM | HIGH |
| TM-021 | No Container Insights/Monitoring | 3 | 2 | 6 | MEDIUM | HIGH |
| TM-016 | Swagger Docs Publicly Exposed | 5 | 1 | 5 | MEDIUM | HIGH |
| TM-010 | DynamoDB Missing PITR and CMK | 2 | 2 | 4 | LOW | HIGH |
| TM-019 | No VPC Endpoints | 2 | 2 | 4 | LOW | HIGH |
| TM-020 | SNS No Subscribers/Encryption | 3 | 1 | 3 | LOW | HIGH |

**Distribution**: 2 CRITICAL, 7 HIGH, 9 MEDIUM, 3 LOW
