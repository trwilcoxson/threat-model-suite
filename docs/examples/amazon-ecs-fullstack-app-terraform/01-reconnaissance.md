# Security Architect -- Phase 1 Reconnaissance

## Metadata
| Field | Value |
|-------|-------|
| Agent | security-architect |
| Date | 2026-02-18 |
| Target System | Amazon ECS Fullstack App (Terraform Demo) |
| Scope | Full system: Terraform IaC (14 modules), Node.js backend, Vue.js frontend, AWS CI/CD pipeline, networking, IAM, data stores |
| Methodology | STRIDE-LM + PASTA (reconnaissance phase) |
| Scoring System | OWASP Risk Rating (scoring deferred to Phase 4) |

## Summary
- **System type**: AWS ECS Fargate-based fullstack web application with CI/CD pipeline, deployed via Terraform
- **Architecture complexity**: Medium (~18 components, ~25 data flows) -- full 4-layer diagram warranted
- **Key risk areas identified**: No TLS on ALBs (HTTP only), no authentication/authorization, overly broad IAM policies (iam:PassRole on *), mutable ECR image tags, GitHub OAuth token in pipeline state, buildspec sourced from repository, CORS wide open, no WAF, no encryption configuration for data stores
- **Compliance posture**: No compliance controls observed. This is explicitly a demo/reference architecture with security shortcuts noted in the README
- **Business context**: AWS demo/reference architecture intended to demonstrate ECS + DevOps patterns. Not designed for production use, but organizations may fork it as a starting point

---

## 1.1 Visual Comprehension

Two architecture diagrams were provided in `Documentation_assets/`:

### Infrastructure Architecture Diagram
- Shows Users accessing the system through a VPC containing two tiers
- **Frontend tier**: Application Load Balancer (Frontend) distributes to ECS Cluster with Fargate tasks across two Availability Zones (Private subnet A and B for Front-end), with Autoscaling policies
- **Backend tier**: Application Load Balancer (Backend) distributes to ECS Cluster with Fargate tasks across two Availability Zones (Private subnet A and B for Back-end), with Autoscaling policies
- Both tiers share a single IAM Role
- Backend connects to Amazon DynamoDB and Amazon S3 (outside VPC)
- All within a single Region

### CI/CD Architecture Diagram
- AWS CodePipeline orchestrates the pipeline
- Source: GitHub repository
- Build: AWS CodeBuild (pushes images to Amazon ECR)
- Deploy: AWS CodeDeploy (deploys to Amazon ECS)
- Amazon SNS for deployment notifications

**Observations from diagrams**:
- No WAF or Shield shown in front of ALBs
- No HTTPS/TLS indicators on any connection
- Single NAT Gateway visible (single AZ)
- No VPC endpoints shown for AWS service access
- IAM Role appears shared between frontend and backend tasks

---

## 1.2 Documentation Review

### README Analysis
- Explicitly states this is a **demo** project: "intended to be used to run a demo"
- Notes "Infrastructure considerations due to demo proposals" -- hardcoded memory/CPU values in task definitions
- Terraform state stored **locally** (no remote backend configured)
- Requires a **GitHub personal access token** passed as a Terraform variable
- Login component explicitly notes: "*No auth was implemented, just a Vue.js demo component*"
- Swagger endpoint exposed at `{server_alb}/api/docs`
- Application serves product catalog data from DynamoDB with images from S3

### Stated Constraints
- Terraform v0.13+ required (versions.tf pins AWS provider ~> 3.38, which is significantly outdated)
- AWS credentials expected in `~/.aws/credentials` file
- GitHub token required for CodePipeline integration

### Security Requirements
- None stated. README references `CONTRIBUTING.md` for security issue notifications but does not define security requirements for the application itself

---

## 1.3 Code Scanning

### Entry Points

| # | Entry Point | Location | Protocol | Handler |
|---|-------------|----------|----------|---------|
| 1 | GET /status | `Code/server/src/app.js:28` | HTTP | Health check endpoint |
| 2 | GET /api/getAllProducts | `Code/server/src/app.js:47` | HTTP | DynamoDB scan, returns all products |
| 3 | GET /api/docs | `Code/server/src/app.js:13` | HTTP | Swagger UI documentation |
| 4 | GET /api/docs/json | `Code/server/src/swagger/swagger.js:37` | HTTP | Raw Swagger spec JSON |
| 5 | Vue.js SPA routes (/, /main, /about, /search) | `Code/client/src/router/index.js` | HTTP | Client-side routing |
| 6 | Client ALB (port 80) | Terraform `module.alb_client` | HTTP | Public-facing frontend load balancer |
| 7 | Server ALB (port 80) | Terraform `module.alb_server` | HTTP | Public-facing backend load balancer |

### Authentication and Authorization
- **No authentication implemented.** The Login.vue component is purely cosmetic -- it accepts any username/password and navigates to `/main` via client-side routing without any server validation
- **No authorization checks** on any API endpoint
- **No API keys, tokens, or session management** of any kind
- Express CORS middleware used with `app.use(cors())` -- no options specified, which **allows all origins**

### Configuration
- **Environment variables in CodeBuild**: AWS_REGION, AWS_ACCOUNT_ID, REPO_URL, IMAGE_TAG (hardcoded "latest"), DYNAMODB_TABLE, TASK_DEFINITION_FAMILY, CONTAINER_NAME, SERVICE_PORT, FOLDER_PATH, ECS_ROLE, ECS_TASK_ROLE, SERVER_ALB_URL
- **Terraform variables**: aws_profile, aws_region, environment_name, github_token (sensitive), port_app_server (3001), port_app_client (80), buildspec_path, folder paths, container names, IAM role names, repository_owner, repository_name, repository_branch (default: main)
- **No secrets management service** (no AWS Secrets Manager, SSM Parameter Store, or HashiCorp Vault)
- GitHub token passed as plaintext Terraform variable (marked sensitive but stored in state)

### Infrastructure as Code (Terraform)

**Modules analyzed (14 total)**:
1. **Networking** -- VPC (10.120.0.0/16), 2 public subnets, 2 private client subnets, 2 private server subnets, IGW, single NAT GW, route tables
2. **ALB** -- Application Load Balancers with HTTP listeners (port 80), HTTPS listener defined but `enable_https` defaults to false
3. **SecurityGroup** -- SGs for ALBs (ingress 0.0.0.0/0 on port 80) and ECS tasks (ingress from ALB SG only)
4. **ECR** -- Docker image repositories with `image_tag_mutability = "MUTABLE"`
5. **ECS/Cluster** -- Single ECS cluster, no container insights enabled
6. **ECS/Service** -- Fargate services with CODE_DEPLOY deployment controller, no `assign_public_ip` (defaults to false -- good)
7. **ECS/TaskDefinition** -- Task definitions with CloudWatch Logs, no resource limits beyond CPU/memory, no `readonlyRootFilesystem`, no `user` specified
8. **ECS/Autoscaling** -- Target tracking on CPU and memory (50% threshold), min 1 / max 4
9. **IAM** -- Four roles (ECS execution, ECS task, DevOps, CodeDeploy) with associated policies
10. **S3** -- Two buckets (codepipeline artifacts, assets), ACL "private", force_destroy=true, no encryption config, no versioning, no public_access_block
11. **DynamoDB** -- Single table, PAY_PER_REQUEST billing, no encryption config (defaults to AWS-owned key), no PITR
12. **SNS** -- Notification topic for deployments, no encryption
13. **CodeBuild** -- Build projects with privileged Docker mode, buildspec sourced from repository
14. **CodePipeline** -- GitHub v1 source with OAuth token, PollForSourceChanges=true
15. **CodeDeploy** -- Blue/Green deployment with auto-rollback on failure

### Data Schemas
- **DynamoDB table structure**: `id` (N, hash key), `path` (S -- S3 object URL), `title` (S)
- **API response format**: `{ products: [{ id, path, title }] }`
- No input validation schemas defined
- Swagger spec documents endpoints but no request validation

### External Integrations
- **GitHub** -- Source repository via CodePipeline (OAuth v1 token)
- **AWS DynamoDB** -- Product catalog data store
- **AWS S3** -- Asset storage (images referenced by URL in DynamoDB records)
- **AWS ECR** -- Docker image registry
- **AWS CloudWatch Logs** -- Container and build logging
- **AWS SNS** -- Deployment notifications (no subscribers configured)

---

## 1.4 Asset Inventory

### Data Assets

| # | Asset | Location | Sensitivity | At Rest | In Transit | In Processing |
|---|-------|----------|-------------|---------|------------|---------------|
| 1 | Product catalog data (id, title, path) | DynamoDB table | PUBLIC | AWS-owned encryption (default) | HTTP (plaintext) | In server memory |
| 2 | S3 asset URLs (image paths) | DynamoDB records + S3 bucket | INTERNAL | AWS-owned encryption (default) | HTTP (plaintext) | In client browser |
| 3 | Product images | S3 assets bucket | PUBLIC | Default S3 encryption | HTTP (via S3 URL) | In client browser |
| 4 | CI/CD artifacts | S3 codepipeline bucket | INTERNAL | No explicit encryption | Within AWS | In CodeBuild/Deploy |
| 5 | Docker images | ECR repositories | INTERNAL | ECR default encryption | Within AWS | In Fargate tasks |
| 6 | GitHub OAuth token | Terraform state, CodePipeline config | RESTRICTED | Plaintext in TF state | Via Terraform CLI | In CodePipeline |
| 7 | Application logs | CloudWatch Log Groups | INTERNAL | CloudWatch default encryption | Within AWS | CloudWatch |
| 8 | Terraform state file | Local filesystem | RESTRICTED | No encryption | Not transmitted (local) | Local |
| 9 | AWS credentials | ~/.aws/credentials | RESTRICTED | Plaintext on deployer machine | Via AWS API (HTTPS) | In Terraform |
| 10 | Swagger API documentation | /api/docs endpoint | PUBLIC | N/A (generated) | HTTP (plaintext) | In server memory |
| 11 | Server error messages | Error handler response | INTERNAL | N/A | HTTP (plaintext) | In server memory |

---

## 1.5 Actor Enumeration

### Human Actors
| Actor | Role | Access Level | Description |
|-------|------|-------------|-------------|
| End User | Browser user | Unauthenticated | Accesses Vue.js SPA via client ALB, views product catalog |
| DevOps Engineer | Infrastructure operator | AWS account, GitHub repo | Runs Terraform, manages infrastructure |
| Developer | Code contributor | GitHub repository | Pushes code changes that trigger CI/CD pipeline |
| AWS Account Admin | Account owner | Full AWS account | Manages IAM, billing, account-level settings |

### System Actors
| Actor | Role | Access Level | Description |
|-------|------|-------------|-------------|
| CodePipeline | CI/CD orchestrator | DevOps IAM role | Triggers builds and deployments on GitHub changes |
| CodeBuild | Build agent | DevOps IAM role (privileged Docker) | Builds Docker images, pushes to ECR |
| CodeDeploy | Deployment agent | CodeDeploy IAM role | Executes Blue/Green deployments to ECS |
| ECS Fargate (Server) | Backend compute | ECS task role | Runs Node.js server, accesses DynamoDB and S3 |
| ECS Fargate (Client) | Frontend compute | ECS execution role | Runs Nginx serving Vue.js SPA |
| ALB (Server) | Load balancer | Public network | Routes HTTP traffic to server ECS tasks |
| ALB (Client) | Load balancer | Public network | Routes HTTP traffic to client ECS tasks |
| GitHub (External) | Source provider | OAuth token | Provides source code to CodePipeline |
| CloudWatch | Monitoring | AWS-managed | Receives logs and autoscaling metrics |
| SNS | Notification | AWS-managed | Sends deployment status notifications |

---

## 1.6 Threat Actor Profiles

### TA-1: Opportunistic Attacker / Script Kiddie
| Attribute | Value |
|-----------|-------|
| Type | External |
| Motivation | Curiosity, notoriety, easy financial gain |
| Capability | 2/5 |
| Access Level | Unauthenticated external (internet) |
| Relevance | HIGH -- Both ALBs are public-facing on HTTP without authentication. Swagger docs expose full API surface. No WAF or rate limiting. This is the most likely threat actor. |

### TA-2: Malicious Insider / Compromised Developer
| Attribute | Value |
|-----------|-------|
| Type | Internal |
| Motivation | Revenge, financial gain, or account compromised by external actor |
| Capability | 3/5 |
| Access Level | GitHub repository write access, potential AWS console access |
| Relevance | HIGH -- Buildspec is sourced from the repository, so any developer with push access can execute arbitrary commands with the DevOps IAM role. No branch protection or approval gates in the pipeline. |

### TA-3: Supply Chain Attacker
| Attribute | Value |
|-----------|-------|
| Type | External (indirect) |
| Motivation | Varies (financial gain, espionage) |
| Capability | 4/5 |
| Access Level | Indirect via compromised npm packages or Docker base images |
| Relevance | MEDIUM -- Dockerfiles use `npm install` (not `npm ci`), pull from public ECR base images (`public.ecr.aws/bitnami/node`, `public.ecr.aws/nginx/nginx`), and ECR tags are mutable. Dependencies include outdated packages (aws-sdk 2.x, express 4.16.x). |

### TA-4: Network-Position Attacker (Man-in-the-Middle)
| Attribute | Value |
|-----------|-------|
| Type | External |
| Motivation | Data interception, session hijacking |
| Capability | 3/5 |
| Access Level | Network position between user and ALB, or between services |
| Relevance | HIGH -- All traffic is HTTP (no TLS). Client-to-server ALB communication is HTTP. User-to-ALB is HTTP. MITM is trivial on any network segment. |

### TA-5: Negligent Insider
| Attribute | Value |
|-----------|-------|
| Type | Internal |
| Motivation | Unintentional |
| Capability | 1/5 (inadvertent) |
| Access Level | Developer or DevOps access |
| Relevance | MEDIUM -- Terraform state with secrets stored locally, no remote backend with encryption. GitHub token could be accidentally committed. No Terraform plan review gates. |

---

## 1.7 Attack Surface Catalog

| # | Entry Point | Location | Protocol | Authentication | Exposure | Input Types |
|---|-------------|----------|----------|---------------|----------|-------------|
| 1 | Client ALB | Public subnet, port 80 | HTTP | None | Internet (0.0.0.0/0) | HTTP requests |
| 2 | Server ALB | Public subnet, port 80 | HTTP | None | Internet (0.0.0.0/0) | HTTP requests |
| 3 | GET /status | Server app, port 3001 | HTTP | None | Via server ALB | None (no input) |
| 4 | GET /api/getAllProducts | Server app, port 3001 | HTTP | None | Via server ALB | None (no user input) |
| 5 | GET /api/docs | Server app, port 3001 | HTTP | None | Via server ALB | None (serves Swagger UI) |
| 6 | GET /api/docs/json | Server app, port 3001 | HTTP | None | Via server ALB | None (serves Swagger spec) |
| 7 | GitHub webhook/poll | CodePipeline source stage | HTTPS (GitHub API) | OAuth token (v1) | AWS-to-GitHub | Git repository content |
| 8 | CodeBuild buildspec | Repository-sourced | N/A | GitHub commit access | Pipeline-internal | Buildspec YAML (arbitrary commands) |
| 9 | S3 asset URLs | Referenced in DynamoDB data | HTTP(S) | S3 bucket policy | Public via URL in DynamoDB | S3 object requests |
| 10 | Terraform CLI | Deployer workstation | AWS API (HTTPS) | AWS credentials | Local | Terraform configuration |
| 11 | ECS task metadata endpoint | Fargate task network | HTTP | None (task-local) | Container-internal | IMDS queries |

---

## 1.8 Security Control Inventory

| # | Control | Implementation | Coverage | Strength | Notes |
|---|---------|---------------|----------|----------|-------|
| 1 | Private subnets for ECS tasks | Networking module: separate private subnets for client and server tasks | Full | GOOD | Tasks not directly exposed to internet |
| 2 | Security group segmentation | SecurityGroup module: ALB SGs allow 0.0.0.0/0:80; ECS task SGs allow ingress only from respective ALB SG | Full | MODERATE | Good east-west restriction, but no egress restrictions beyond default allow-all |
| 3 | NAT Gateway for outbound | Networking module: NAT GW in public subnet | Full | MODERATE | Single NAT GW (single AZ -- availability risk but not security critical) |
| 4 | ECS Fargate isolation | ECS Service module: launch_type = "FARGATE" | Full | GOOD | AWS-managed infrastructure, no host-level access |
| 5 | CloudWatch logging | TaskDefinition module: awslogs log driver | Full | MODERATE | 30-day retention, but no alerting configured beyond autoscaling metrics |
| 6 | Blue/Green deployments | CodeDeploy module: deployment_type = "BLUE_GREEN" with auto-rollback | Full | GOOD | Reduces deployment risk, enables quick rollback on failure |
| 7 | S3 bucket ACL | S3 module: acl = "private" | Partial | WEAK | No public_access_block, no bucket policy, no versioning, no encryption config |
| 8 | Terraform sensitive variable | Variables: github_token marked `sensitive = true` | Partial | WEAK | Prevents display in plan output but token still in state file |
| 9 | GitHub token lifecycle ignore | CodePipeline module: `ignore_changes = [stage[0].action[0].configuration]` | Partial | WEAK | Prevents token updates from causing diffs but does not protect the token |
| 10 | Autoscaling | ECS Autoscaling module: CPU and memory target tracking (50%), min 1 / max 4 | Full | MODERATE | Provides basic DoS resilience via scaling, but max 4 limits capacity |
| 11 | Network mode awsvpc | TaskDefinition module: `network_mode = "awsvpc"` | Full | GOOD | Each task gets its own ENI, enabling SG-level isolation |

### Notable Missing Controls
| # | Missing Control | Expected Location | Impact |
|---|----------------|-------------------|--------|
| 1 | TLS/HTTPS on ALBs | ALB module (enable_https=false) | All traffic in plaintext -- data interception |
| 2 | Authentication/Authorization | Application layer | Complete open access to all endpoints |
| 3 | WAF | In front of ALBs | No L7 filtering, rate limiting, or bot protection |
| 4 | S3 public_access_block | S3 module | Buckets could be made public by misconfiguration |
| 5 | S3 encryption configuration | S3 module | No explicit server-side encryption |
| 6 | S3 versioning | S3 module | No recovery from accidental deletion or corruption |
| 7 | DynamoDB PITR | DynamoDB module | No point-in-time recovery |
| 8 | DynamoDB CMK encryption | DynamoDB module | Uses AWS-owned key, no customer control |
| 9 | ECR image scanning | ECR module | No vulnerability scanning on push |
| 10 | ECR immutable tags | ECR module (MUTABLE) | Image tag overwrite risk |
| 11 | VPC Flow Logs | Networking module | No network traffic auditing |
| 12 | VPC endpoints | Networking module | Traffic to DynamoDB/S3/ECR traverses NAT GW (internet) |
| 13 | ECS container hardening | TaskDefinition module | No readonlyRootFilesystem, no non-root user |
| 14 | Pipeline approval gates | CodePipeline module | No manual approval between stages |
| 15 | Branch protection | GitHub (external) | Not enforced by Terraform |
| 16 | Remote Terraform backend | Root infrastructure | Local state with secrets |
| 17 | Billing alarm / cost controls | Not present | No spending limit or anomaly detection |
| 18 | SNS subscription | SNS module | Topic created but no subscribers |
| 19 | Container Insights | ECS Cluster module | No enhanced monitoring |
| 20 | Input validation | Server application | No request validation middleware |

---

## 1.9 Visual Completeness Assessment

See `visual-completeness-checklist.md` for the full checklist. Summary of applicability:

| Category | Applicable? | Justification |
|----------|------------|---------------|
| 1. External Entities | YES | Users, GitHub, AWS services (DynamoDB, S3) |
| 2. Processes | YES | ECS Fargate tasks (client, server), CodeBuild, CodeDeploy, CodePipeline |
| 3. Data Stores | YES | DynamoDB, S3 (x2), ECR (x2) |
| 4. Trust Boundaries | YES | Public internet, VPC, private subnets, AWS managed services |
| 5. Data Flow Labels | YES | Multiple protocols and data types across components |
| 6. Risk Color Coding | YES | Risk overlay phase |
| 7. Threat Annotations | YES | Risk overlay phase |
| 8. Component Metadata | YES | Multiple technologies (Node.js, Nginx, Terraform, Docker) |
| 9. Identity Elements | YES | 4 IAM roles, ECS execution/task roles |
| 10. Secrets/Key Mgmt | YES | GitHub OAuth token, AWS credentials (no KMS, but absence is notable) |
| 11. Control/Data Plane | YES | CI/CD is control plane, user traffic is data plane |
| 12. Attack Paths | YES | Risk overlay phase |
| 13. Control Indicators | YES | Security groups, private subnets, autoscaling (and many missing) |
| 14. Data Classification | YES | PUBLIC (products), INTERNAL (artifacts), RESTRICTED (tokens, creds) |
| 15. Encryption State | YES | Mostly PLAIN -- significant finding |
| 16. Network Zones | YES | VPC with public/private subnets across AZs |
| 17. Deployment Pipeline | YES | Full CI/CD with CodePipeline, CodeBuild, CodeDeploy |
| 18. External Dependencies | YES | GitHub, public ECR base images, npm registry |
| 19. Tenant Boundaries | NO | Single-tenant demo application |
| 20. Region Boundaries | NO | Single-region deployment |
| 21. Typed Edges | YES | Multiple edge types needed |
| 22. Ownership Markers | YES | AWS-managed vs self-managed vs vendor components |
| 23. Machine-Parseable Annotations | YES | Risk overlay phase |
| 24. Version Stamp | YES | Always applicable |
| 25. Density Compliance | YES | Always applicable |
| 26. Companion Diagrams | YES | Attack trees and auth sequence applicable |

**Applicable**: 24/26
**Not Applicable**: 2/26 (Tenant Boundaries, Region Boundaries)

---

## 1.10 Reconnaissance Summary

### Components Discovered (18)

| # | Component | Type | Technology | Location |
|---|-----------|------|-----------|----------|
| 1 | Client ALB | Load Balancer | AWS ALB | Public subnets |
| 2 | Server ALB | Load Balancer | AWS ALB | Public subnets |
| 3 | Client ECS Service | Compute | AWS Fargate + Nginx | Private client subnets |
| 4 | Server ECS Service | Compute | AWS Fargate + Node.js/Express | Private server subnets |
| 5 | ECS Cluster | Container Orchestration | AWS ECS | VPC |
| 6 | DynamoDB Table | Data Store | AWS DynamoDB | AWS Managed |
| 7 | S3 Assets Bucket | Data Store | AWS S3 | AWS Managed |
| 8 | S3 CodePipeline Bucket | Data Store | AWS S3 | AWS Managed |
| 9 | ECR Server Repo | Container Registry | AWS ECR | AWS Managed |
| 10 | ECR Client Repo | Container Registry | AWS ECR | AWS Managed |
| 11 | CodePipeline | CI/CD Orchestrator | AWS CodePipeline | AWS Managed |
| 12 | CodeBuild (Server) | Build Service | AWS CodeBuild | AWS Managed |
| 13 | CodeBuild (Client) | Build Service | AWS CodeBuild | AWS Managed |
| 14 | CodeDeploy (Server) | Deployment Service | AWS CodeDeploy | AWS Managed |
| 15 | CodeDeploy (Client) | Deployment Service | AWS CodeDeploy | AWS Managed |
| 16 | SNS Topic | Notification | AWS SNS | AWS Managed |
| 17 | VPC + Networking | Network Infrastructure | AWS VPC | Single Region |
| 18 | CloudWatch Log Groups | Monitoring | AWS CloudWatch | AWS Managed |

### Trust Boundaries Identified

| # | Boundary | Components Inside | Components Outside | Crossing Points |
|---|----------|-------------------|-------------------|-----------------|
| 1 | Internet / Public Network | End Users, External Attackers | Everything in AWS | Client ALB, Server ALB |
| 2 | VPC Perimeter | ALBs, ECS Tasks, NAT GW | AWS Managed Services, Internet | IGW, NAT GW, implicit VPC endpoints |
| 3 | Public Subnets | ALBs, NAT GW | ECS Tasks | Security Groups (ALB -> ECS Task) |
| 4 | Private Client Subnets | Client ECS Tasks | Server ECS Tasks, ALBs | Security Group ingress from Client ALB SG |
| 5 | Private Server Subnets | Server ECS Tasks | Client ECS Tasks, ALBs | Security Group ingress from Server ALB SG |
| 6 | AWS Managed Service Boundary | DynamoDB, S3, ECR, CloudWatch, SNS | VPC components | IAM policies, VPC routing (via NAT) |
| 7 | CI/CD Pipeline Boundary | CodePipeline, CodeBuild, CodeDeploy | Application runtime | Build artifacts, ECR images, ECS task definitions |
| 8 | External Service Boundary | GitHub | AWS Account | OAuth token, HTTPS API |

### Technology Stack

| Layer | Technology | Version (where specified) |
|-------|-----------|--------------------------|
| Frontend Framework | Vue.js | 2.6.11 |
| Frontend Build | Vue CLI | 4.4.x |
| Frontend Runtime | Nginx | latest (from public.ecr.aws) |
| Backend Framework | Express.js | 4.16.4 |
| Backend Runtime | Node.js | latest (from public.ecr.aws/bitnami) |
| API Documentation | swagger-jsdoc + swagger-ui-express | 6.0.0 / 4.1.6 |
| HTTP Client | Axios | 0.21.2 |
| AWS SDK | aws-sdk (v2) | 2.876.0 (server), 2.885.0 (client) |
| UI Components | Bootstrap-Vue | 2.15.0 |
| IaC | Terraform | >= 0.13 |
| AWS Provider | hashicorp/aws | ~> 3.38 |
| Container Build | Docker | Standard (Dockerfile) |
| CI/CD | AWS CodePipeline + CodeBuild + CodeDeploy | V1 actions |

### Key Gaps / Information Missing

1. **No Terraform remote backend configuration** -- state stored locally with secrets
2. **No `.env` files found** -- configuration is entirely via Terraform variables and CodeBuild environment variables
3. **No test suites** beyond Artillery stress tests -- no security tests
4. **No HTTPS certificate** configuration -- ACM not referenced anywhere
5. **Outdated dependencies** -- AWS provider 3.38 (current is 5.x+), Node.js and package versions are significantly behind
6. **No error monitoring or alerting** -- CloudWatch alarms only for autoscaling, no application error alerting

### Assumptions

1. **Assumed single AWS account deployment** -- no cross-account references found
2. **Assumed single region** -- only one region variable, no multi-region configuration
3. **Assumed default VPC settings** where not explicitly configured (e.g., default NACL rules)
4. **Assumed no additional AWS services** configured outside this Terraform code (no pre-existing WAF, GuardDuty, Config, etc.)
5. **Assumed the DynamoDB table contains non-sensitive product catalog data** (titles, image URLs) based on the schema and README
6. **Assumed Fargate platform version LATEST** is used (specified in appspec.yaml)
7. **Assumed no GitHub branch protection rules** are in place since they are not managed by Terraform and the README does not mention them
8. **Assumed the `aws-sdk` inclusion in the client package.json is unnecessary** (the frontend is a static SPA served by Nginx; aws-sdk is likely a leftover dependency)

---

## Execution Log

### Process Health
| Metric | Value |
|--------|-------|
| Files Read | 42 |
| Files Written | 2 |
| Errors Encountered | 0 |
| Items Skipped | 0 |
| Self-Assessed Output Quality | HIGH |

### What Went Well
- Complete project was readable -- all 14 Terraform modules, both application codebases, all templates, Dockerfiles, and configuration files were accessible
- Architecture diagrams (PNG) provided visual confirmation of the infrastructure layout
- Code is well-organized with clear separation between Infrastructure and Code directories
- Demo nature of the project is well-documented, making it clear which security shortcuts were intentional

### Issues Encountered
- None. All files were readable and the project structure was straightforward.

### What Was Skipped or Incomplete
- **npm audit analysis** -- did not run `npm audit` against package-lock.json files. The code review agent should perform dependency vulnerability scanning.
- **Terraform plan analysis** -- did not execute `terraform plan` or `terraform validate`. Assessment is based on static code review only.
- **Docker image vulnerability scan** -- base images (`public.ecr.aws/bitnami/node:latest`, `public.ecr.aws/nginx/nginx:latest`) were not scanned for vulnerabilities. The code review agent should flag these.

### Assumptions Made
- All assumptions are documented in the "Assumptions" section above (items 1-8)
- The assessment treats this as a system that could be forked for production use, since that is the most security-relevant context for a threat model. Findings will note where something is "expected for a demo but unacceptable for production."
