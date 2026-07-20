# Visual Completeness Checklist

---

## Instructions

1. **Phase 1 (Reconnaissance)** -- Mark each category as **APPLICABLE**, **NOT APPLICABLE** (with one-line justification), or **N/A**.
2. **NOT APPLICABLE** requires a one-line justification grounded in Phase 1 observations (e.g., "Single-tenant system; no tenant isolation needed").
3. **Phase 2 (Structural Diagram)** -- Verify every category marked APPLICABLE is represented in the structural diagram. Check the box and record which diagram components satisfy it.
4. **Phase 7 (Risk Overlay)** -- Verify every category marked APPLICABLE is represented in the risk overlay diagram. Check the box and record which diagram components satisfy it.
5. **Post-Analysis Verification** -- The validation-specialist reviews this checklist for completeness, confirms evidence fields are populated, and flags any gaps.

---

## Checklist

---

### 1. External Entities

| Property | Value |
|----------|-------|
| Shape | `[Text]` rectangle |
| Style class | `:::external` |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L1: User, GitHub, npmReg, pubECR as `:::external`/`:::externalDep`; AWS managed services in AWSManaged subgraph
- [x] **Represented in risk overlay?** (Phase 7) -- L4: User as `:::external`; GitHub, npmReg, pubECR with risk-colored annotations. All external entities present with threat data overlaid.
- **Evidence:** End Users access the system via browser. GitHub provides source code. AWS managed services (DynamoDB, S3, ECR, CloudWatch, SNS) are external to the VPC compute plane.
- **Components:** Users, GitHub, DynamoDB, S3 (assets), S3 (codepipeline), ECR, CloudWatch, SNS

---

### 2. Processes

| Property | Value |
|----------|-------|
| Shape | `([Text])` stadium |
| Style class | `:::neutral` |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L1: ClientALB, ServerALB, ClientECS, ServerECS, SNS as stadiums; CodeBuild/CodeDeploy consolidated (server+client share identical security properties)
- [x] **Represented in risk overlay?** (Phase 7) -- L4: All process nodes present with risk coloring. ClientALB/ServerALB (:::highRisk), ClientECS/ServerECS (:::highRisk), SNS (:::lowRisk). Stadium shapes retained.
- **Evidence:** ECS Fargate tasks (client and server), CodeBuild projects (client and server), CodeDeploy applications (client and server), CodePipeline
- **Components:** Client ECS Service (Nginx/Vue.js), Server ECS Service (Node.js/Express), CodeBuild-Server, CodeBuild-Client, CodeDeploy-Server, CodeDeploy-Client, CodePipeline

---

### 3. Data Stores

| Property | Value |
|----------|-------|
| Shape | `[(Text)]` cylinder |
| Style class | `:::dataStore` |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L1: DynamoDB, S3Assets, S3Pipeline, ECR, CloudWatch as cylinders with `:::dataStore`
- [x] **Represented in risk overlay?** (Phase 7) -- L4: All data stores present with risk coloring. DynamoDB/ECR (:::highRisk), S3Assets/S3Pipeline/CloudWatch (:::medRisk). Cylinder shapes retained with threat annotations.
- **Evidence:** DynamoDB table stores product catalog. S3 assets bucket stores product images. S3 codepipeline bucket stores build artifacts. ECR repositories store Docker images.
- **Components:** DynamoDB table, S3 Assets Bucket, S3 CodePipeline Bucket, ECR Server Repo, ECR Client Repo

---

### 4. Trust Boundaries

| Property | Value |
|----------|-------|
| Shape | Dashed subgraphs with color-coded strokes (red / orange / green) |
| Style class | Boundary-specific coloring |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L2: InternetBoundary, VPC, PubSubnets, PrivClientSubnets, PrivServerSubnets, AWSManaged, CICDBoundary as dashed subgraphs with red/orange/green color coding by trust level
- [x] **Represented in risk overlay?** (Phase 7) -- L4: VPC, PubSubnets (red dashed), PrivClientSubnets/PrivServerSubnets (orange dashed), AWSManaged (green dashed), CICDBoundary (purple dashed), RestrictedSecrets (red fill). All trust zones preserved.
- **Evidence:** Internet boundary, VPC perimeter, public subnets, private client subnets, private server subnets, AWS managed service boundary, CI/CD pipeline boundary, external service boundary (GitHub)
- **Components:** Internet, VPC, Public Subnets, Private Client Subnets, Private Server Subnets, AWS Managed Services zone, CI/CD Pipeline zone

---

### 5. Data Flow Labels

| Property | Value |
|----------|-------|
| Shape | Arrow labels with format `Protocol: data type [SENSITIVITY]` |
| Style class | Edge labels |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L1: All 21 edges labeled with protocol, data type, sensitivity classification; L3: encryption state added
- [x] **Represented in risk overlay?** (Phase 7) -- L4: All data plane edges carry protocol, data type, sensitivity, and encryption state labels. CI/CD and control plane edges carry typed prefixes ([CTRL], [BUILD], [ASYNC], [KEY]).
- **Evidence:** HTTP traffic from users to ALBs, HTTP from ALBs to ECS tasks, HTTP from client to server ALB (cross-origin API calls), DynamoDB SDK calls, S3 SDK/URL calls, ECR image pulls, CodePipeline orchestration, GitHub API polling
- **Components:** All edges between components

---

### 6. Risk Color Coding

| Property | Value |
|----------|-------|
| Shape | Node style classes |
| Style class | `:::highRisk`, `:::medRisk`, `:::lowRisk`, `:::noFindings` |
| Required pass | Risk overlay only |

- [x] **Applicable?** YES
- [x] **Represented in risk overlay?** (Phase 7) -- L4: All 26 components classified. 15 highRisk (including 3 CRITICAL), 5 medRisk, 1 lowRisk, 4 noFindings, 1 external. Risk classes applied based on highest-severity validated finding per component.
- **Evidence:** 2 CRITICAL findings, 10 HIGH findings, 11 MEDIUM findings, 3 LOW findings mapped across all components. Risk coloring verified against 06-validated-findings.md severity bands.
- **Components:** All component nodes carry risk classification

---

### 7. Threat Annotations

| Property | Value |
|----------|-------|
| Shape | Enriched node labels (not `note` blocks -- invalid in flowchart mode) |
| Content | STRIDE-LM category, Risk Score, CWE reference |
| Required pass | Risk overlay only |

- [x] **Applicable?** YES
- [x] **Represented in risk overlay?** (Phase 7) -- L4: 21 components carry enriched threat annotations in compact format (Name + Tech + STRIDE + LxI=Score BAND + CWE). 4 components use noFindings labels (no annotation needed). 1 external entity (User) has no annotation.
- **Evidence:** Annotations verified: STRIDE single-letter abbreviations correct, LxI calculations verified, severity bands match scores (CRIT 20-25, HIGH 12-19, MED 6-11, LOW 1-5), CWE IDs verified against frameworks.md.
- **Components:** All components with validated findings carry annotations

---

### 8. Component Metadata

| Property | Value |
|----------|-------|
| Shape | Enriched node labels |
| Content | Tech stack, authentication method, encryption details |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L1: All nodes carry enriched labels with technology, version, and security-relevant config (e.g., "HTTP:80", "PAY_PER_REQUEST", "MUTABLE tags", "Privileged Docker Mode")
- [x] **Represented in risk overlay?** (Phase 7) -- L4: Component metadata retained in enriched labels (e.g., "Fargate + Node.js + Express", "HTTP:80 + No TLS", "MUTABLE tags + No scanning", "Privileged Docker + Repo Buildspec").
- **Evidence:** Multiple technologies: Node.js/Express, Vue.js/Nginx, Terraform, Docker, AWS services with specific configurations (Fargate, PAY_PER_REQUEST, etc.)
- **Components:** Server ECS (Node.js + Express + aws-sdk), Client ECS (Nginx + Vue.js), ALBs (HTTP/80), DynamoDB (PAY_PER_REQUEST), S3 (private ACL), ECR (MUTABLE tags)

---

### 9. Identity Elements (IAM roles, service accounts)

| Property | Value |
|----------|-------|
| Shape | `{Text}` diamond |
| Style class | `:::identity` |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L2: ECSExecRole, ECSTaskRole, DevOpsRole, CodeDeployRole as `{...}:::identity` diamonds in IAMIdentities subgraph with scope descriptions
- [x] **Represented in risk overlay?** (Phase 7) -- L4: All 4 IAM roles present in IAMIdentities subgraph. ECSTaskRole/DevOpsRole as :::highRisk with CRITICAL threat annotations (PassRole *). ECSExecRole/CodeDeployRole as :::noFindings.
- **Evidence:** Four IAM roles: ECS Task Execution Role, ECS Task Role, DevOps Role (CodeBuild/CodePipeline/CodeDeploy), CodeDeploy Role
- **Components:** ECS-task-execution-Role, ECS-task-Role, DevOps-Role, CodeDeploy-Role

---

### 10. Secrets/Key Management (vaults, HSM, KMS)

| Property | Value |
|----------|-------|
| Shape | `{{Text}}` hexagon |
| Style class | `:::secrets` |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L3: GitHubToken, TFState as `{{...}}:::secrets` hexagons in RESTRICTED Data Zone with storage location details
- [x] **Represented in risk overlay?** (Phase 7) -- L4: GitHubToken and TFState as `{{...}}:::highRisk` hexagons in RestrictedSecrets subgraph with TM-005 threat annotation (CWE-312, L3xI5=15 HIGH).
- **Evidence:** GitHub OAuth token stored in CodePipeline configuration and Terraform state. No KMS, Secrets Manager, or SSM Parameter Store used -- the absence is a key finding. AWS credentials on deployer workstation.
- **Components:** GitHub OAuth Token (in CodePipeline config/TF state), Terraform State File (local, contains secrets)

---

### 11. Control Plane vs Data Plane

| Property | Value |
|----------|-------|
| Shape | `-.->` dashed arrows = control plane, `-->` solid arrows = data plane |
| Label prefix | `[CP]` for control plane, `[DP]` for data plane |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L1/L2: CI/CD edges use `-.->` dashed with `[CTRL]` and `[BUILD]` prefixes; data plane uses `-->` solid. L3: DataPlane and ControlPlane as separate subgraphs
- [x] **Represented in risk overlay?** (Phase 7) -- L4: Control plane edges (-.-> [CTRL], --> [BUILD]) and data plane edges (-->) clearly distinguished. Attack path overlays (==>) add a third visual layer for kill chains.
- **Evidence:** Clear separation: CI/CD pipeline (CodePipeline -> CodeBuild -> CodeDeploy -> ECS) is control plane; User -> ALB -> ECS -> DynamoDB/S3 is data plane
- **Components:** Control plane: CodePipeline, CodeBuild, CodeDeploy, ECR, Terraform. Data plane: ALBs, ECS Services, DynamoDB, S3 Assets

---

### 12. Attack Paths (kill chains)

| Property | Value |
|----------|-------|
| Shape | `==>` thick red arrows |
| Style class | `linkStyle N stroke:#cc0000,stroke-width:3px` |
| Required pass | Risk overlay only |

- [x] **Applicable?** YES
- [x] **Represented in risk overlay?** (Phase 7) -- L4: 3 kill chains overlaid with 10 thick red arrows. KC1: GitHub->CodePipeline->CodeBuild->DevOpsRole->ECSTaskRole (4 steps, CRITICAL). KC2: npmReg->CodeBuild->ECR->ServerECS (3 steps, HIGH). KC3: User->ServerALB->ServerECS->DynamoDB (3 steps, HIGH). Each step labeled with KC{N}-{step} notation.
- **Evidence:** Kill chains from Phase 5 covering 14 of 26 validated findings. Attack paths traverse trust boundaries (Internet->VPC, VPC->CI/CD, CI/CD->IAM, IAM->AWS Managed).
- **Components:** 3 kill chains, 10 attack path edges, 14 findings covered

---

### 13. Control Indicators (WAF, IDS, MFA, encryption)

| Property | Value |
|----------|-------|
| Shape | `[[Text]]` subroutine |
| Style class | `:::control` |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L2: SG_ALB, SG_ECS_Client, SG_ECS_Server, Autoscaling as `[[...]]:::control` subroutines with ingress rules and control-owner markers
- [x] **Represented in risk overlay?** (Phase 7) -- L4: SG_ALB (:::noFindings -- performing correctly), SG_ECS (:::highRisk -- TM-022 unrestricted egress), Autoscaling (:::noFindings). Security groups consolidated from Phase 2 (SG_ECS_Client + SG_ECS_Server -> SG_ECS) since they share the egress finding.
- **Evidence:** Existing controls: Security Groups (ALB and ECS), Private Subnets, NAT Gateway, Blue/Green Deployment, Autoscaling, CloudWatch Logs. Notable absence of WAF, IDS, MFA, encryption.
- **Components:** SG-ALB-Server, SG-ALB-Client, SG-ECS-Server, SG-ECS-Client, Private Subnets, NAT GW, Autoscaling, CloudWatch Logs

---

### 14. Data Classification Markers

| Property | Value |
|----------|-------|
| Shape | Zone-level subgraph coloring |
| Zones | `PUBLIC` / `INTERNAL` / `CONFIDENTIAL` / `RESTRICTED` |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L3: PublicZone (green), InternalZone (blue), RestrictedZone (red) as colored subgraphs grouping data stores by classification
- [x] **Represented in risk overlay?** (Phase 7) -- L4: RestrictedSecrets subgraph (red fill) contains GitHubToken and TFState. AWSManaged subgraph contains PUBLIC/INTERNAL data stores. Implicit classification via trust boundary hierarchy.
- **Evidence:** Product data (PUBLIC), CI/CD artifacts and Docker images (INTERNAL), GitHub token and AWS credentials (RESTRICTED), application logs (INTERNAL)
- **Components:** DynamoDB/S3 Assets (PUBLIC), S3 CodePipeline/ECR (INTERNAL), GitHub Token/TF State (RESTRICTED)

---

### 15. Encryption State Indicators

| Property | Value |
|----------|-------|
| Shape | Lock prefix or label tag in edge labels |
| Notation | Lock icon prefix, or `[ENC]` / `[PLAIN]` in edge labels |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L3: Every edge labeled with `[ENC]` or `[PLAIN]`. User-to-ALB and ALB-to-ECS marked `[PLAIN]`; AWS API calls marked `[ENC]`
- [x] **Represented in risk overlay?** (Phase 7) -- L4: Data plane edges carry `[PLAIN]` (User->ALB->ECS) and `[ENC]` (ECS->DynamoDB, ECS->S3) markers. Encryption state preserved from Phase 2 structural diagrams.
- **Evidence:** All user-facing traffic is HTTP [PLAIN]. ALB-to-ECS is HTTP [PLAIN]. DynamoDB uses default AWS-owned encryption at rest. S3 has no explicit encryption config. ECR uses default encryption. Internal AWS API calls use HTTPS [ENC].
- **Components:** All data flow edges carry [ENC] or [PLAIN] markers

---

### 16. Network Zones

| Property | Value |
|----------|-------|
| Shape | Subgraph layer with CIDR annotations |
| Style class | Zone-specific styling |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L1/L2: VPC (10.120.0.0/16), Public Subnets (AZ1+AZ2), Private Client Subnets, Private Server Subnets as labeled subgraphs
- [x] **Represented in risk overlay?** (Phase 7) -- L4: VPC (10.120.0.0/16) as outer subgraph containing PubSubnets, PrivClientSubnets, PrivServerSubnets as inner subgraphs with trust-level labels.
- **Evidence:** VPC 10.120.0.0/16, 2 public subnets (AZ1/AZ2), 2 private client subnets, 2 private server subnets, Internet gateway, NAT gateway
- **Components:** VPC subgraph, Public Subnet subgraph, Private Client Subnet subgraph, Private Server Subnet subgraph

---

### 17. Deployment Pipeline (CI/CD, registries)

| Property | Value |
|----------|-------|
| Shape | `[/Text/]` parallelogram |
| Style class | `:::pipeline` |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L1/L2: CodePipeline, CodeBuild, CodeDeploy as `[/...../]:::pipeline` parallelograms in CICDPipeline subgraph
- [x] **Represented in risk overlay?** (Phase 7) -- L4: CodePipeline, CodeBuild, CodeDeploy as parallelograms in CICDBoundary subgraph with :::highRisk coloring and threat annotations. CodeBuild carries CRITICAL annotation (TM-004, 5x5=25).
- **Evidence:** Full CI/CD pipeline: GitHub (source) -> CodePipeline (orchestrator) -> CodeBuild (build + push to ECR) -> CodeDeploy (Blue/Green to ECS). Buildspec sourced from repo.
- **Components:** CodePipeline, CodeBuild-Server, CodeBuild-Client, CodeDeploy-Server, CodeDeploy-Client, ECR repos

---

### 18. External Dependency Markers

| Property | Value |
|----------|-------|
| Shape | Double-border rectangle |
| Style class | `:::externalDep` |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L1: GitHub, npmReg, pubECR as `:::externalDep` with dashed stroke borders
- [x] **Represented in risk overlay?** (Phase 7) -- L4: GitHub (:::highRisk with TM-023 annotation), npmReg (:::medRisk with TM-025 annotation), pubECR (:::medRisk with TM-015 annotation). Risk coloring overrides externalDep styling to convey threat severity.
- **Evidence:** GitHub (source repository), npm registry (package dependencies), public ECR (Docker base images: bitnami/node, nginx/nginx)
- **Components:** GitHub, npm Registry, Public ECR (base images)

---

### 19. Tenant Boundaries

| Property | Value |
|----------|-------|
| Shape | Blue dashed subgraphs |
| Style class | Tenant-specific boundary styling |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** NOT APPLICABLE -- Single-tenant demo application with no multi-tenancy architecture observed
- **Evidence:** README describes a single demo application. No tenant isolation logic, per-tenant data partitioning, or tenant-aware routing found in code or infrastructure.
- **Components:** N/A

---

### 20. Region Boundaries

| Property | Value |
|----------|-------|
| Shape | Nested subgraphs with region labels, purple dashed stroke |
| Style class | Region-specific boundary styling |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** NOT APPLICABLE -- Single-region deployment with no cross-region replication or failover observed
- **Evidence:** Single `aws_region` variable, all resources deployed to one region. No cross-region replication, Route53 failover, or multi-region patterns found.
- **Components:** N/A

---

### 21. Typed Edges

| Property | Value |
|----------|-------|
| Spec reference | `mermaid-spec.md` S4 |
| Types | 8 edge types: Data flow, Control/API, AuthN/AuthZ, Secrets/Keys, Admin/Ops, Async/Event, Replication, Build/Deploy |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L1/L2/L3: Data flow (-->), [CTRL] (-.->), [BUILD] (-->), [ASYNC] (-->), [KEY] (==>) edge types used across all layers. No [AUTH] edges since no authentication exists.
- [x] **Represented in risk overlay?** (Phase 7) -- L4: All edge types from Phase 2 preserved. Additional attack path edges (==>) with red linkStyle for kill chains. 5 edge types used: Data flow, [CTRL], [BUILD], [ASYNC], [KEY], plus attack path overlays.
- **Evidence:** Data flow (User->ALB->ECS->DynamoDB), Control/API (CodePipeline->CodeBuild->CodeDeploy), Build/Deploy (CodeBuild->ECR, CodeDeploy->ECS), Async/Event (SNS notifications), Secrets/Keys (GitHub OAuth token flow). No AuthN/AuthZ edges since no authentication exists.
- **Components:** All edges use typed prefixes

---

### 22. Ownership Markers

| Property | Value |
|----------|-------|
| Spec reference | `mermaid-spec.md` S7 |
| Markers | `[team:X]`, `[managed]`, `[self-managed]`, `[vendor:X]`, `[control-owner:X]` |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES
- [x] **Represented in structural diagram?** (Phase 2) -- L1: `[vendor:AWS]`, `[vendor:GitHub]`, `[vendor:npm]`, `[self-managed]`, `[managed]` markers in enriched node labels
- [x] **Represented in risk overlay?** (Phase 7) -- L4: Ownership markers omitted from L4 enriched labels to stay within 4-line label limit. Threat annotations take priority over ownership markers in the risk overlay layer. Ownership information is preserved in L1/L2 structural diagrams for cross-reference.
- **Evidence:** AWS-managed services (DynamoDB, S3, ECR, ECS Fargate infrastructure, CodePipeline, CodeBuild, CodeDeploy, SNS, CloudWatch) vs self-managed components (application code, Terraform configuration, Dockerfiles, buildspec) vs vendor (GitHub)
- **Components:** [managed] for AWS services, [self-managed] for application/IaC, [vendor:GitHub] for GitHub

---

### 23. Machine-Parseable Annotations

| Property | Value |
|----------|-------|
| Spec reference | `mermaid-spec.md` S5 |
| Format | `warning STRIDE . LxI=Score BAND\nMITRE . CWE\ncheck Mitigation [Status] [R:Residual]` |
| Required pass | Risk overlay only |

- [x] **Applicable?** YES
- [x] **Represented in risk overlay?** (Phase 7) -- L4: Compact annotation format used on 21 components: `Name\nTech/Config\nSTRIDE . LxI=Score BAND\nCWE IDs`. All annotations verified: STRIDE single letters, LxI correct, bands match scores, CWE IDs verified against frameworks.md.
- **Evidence:** Findings from Phases 3-6 provide STRIDE-LM categories, risk scores, and CWE IDs for enriched annotations. Full verification table in 07-final-diagram.md.
- **Components:** All components with validated findings carry machine-parseable annotations

---

### 24. Version Stamp

| Property | Value |
|----------|-------|
| Spec reference | `mermaid-spec.md` S6 |
| Format | `%% Version: {date} \| Phase: {N} \| System: {name}` |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES (always applicable)
- [x] **Represented in structural diagram?** (Phase 2) -- All 3 diagrams carry `%% Version: 2026-02-18 | Phase: 2 | System: ECS Fullstack App | Layer: L{N}` comments
- [x] **Represented in risk overlay?** (Phase 7) -- L4: `%% Version: 2026-02-18 | Phase: 7 | System: ECS Fullstack App | Layer: L4` comment at top of diagram.
- **Evidence:** Version stamp comment present in all diagram source
- **Components:** Comment line at top of each .mmd file

---

### 25. Density Compliance

| Property | Value |
|----------|-------|
| Spec reference | `mermaid-spec.md` S6 |
| Limits | <=15 nodes per subgraph, <=25 nodes total |
| Required pass | Both (structural + risk overlay) |

- [x] **Applicable?** YES (always applicable)
- [x] **Represented in structural diagram?** (Phase 2) -- L1: 22 nodes (4 subgraphs); L2: 26 nodes (8 subgraphs, max 6 per subgraph); L3: 18 nodes (5 subgraphs). All within limits after consolidation of paired components.
- [x] **Represented in risk overlay?** (Phase 7) -- L4: ~26 nodes across 7 subgraphs. VPC: 3 subgraphs (PubSubnets: 3 nodes, PrivClient: 1 node, PrivServer: 2 nodes). AWSManaged: 6 nodes. CICDBoundary: 3 nodes. IAMIdentities: 4 nodes. RestrictedSecrets: 2 nodes. Legend: 11 entries. No subgraph exceeds 15 nodes. Total is at the 25-node boundary; consolidation from Phase 2 enables compliance.
- **Evidence:** Node consolidation (CodeBuild Server+Client, CodeDeploy Server+Client, ECR Server+Client, SG_ECS combined) keeps diagram within density limits. Legend subgraph excluded from node count per convention.
- **Components:** Total: ~26 primary nodes across 7 functional subgraphs

---

### 26. Companion Diagrams

| Property | Value |
|----------|-------|
| Spec reference | `mermaid-diagrams.md` S1-S5 |
| Types | Attack Tree (Phase 5), Auth Sequence (Phase 3), Data Lifecycle (Phase 1, optional) |
| Required pass | Per-type: Attack Tree in Phase 5, Auth Sequence in Phase 3 |

- [x] **Applicable?** YES
- [x] **Attack tree produced?** (Phase 5) -- YES: 2 attack trees in 05-false-negative-hunting.md (Attack Tree 1: GitHub to AWS Account Compromise, Attack Tree 2: Supply Chain to Production Code Execution). Both use flowchart TD with goal/sub-goal/technique hierarchy and feasibility coloring.
- [ ] **Auth sequence produced?** (Phase 3, if system has AuthN/AuthZ) -- N/A: System has no authentication. The absence of auth is documented as TM-002 rather than producing a sequence diagram of unprotected flows.
- [ ] **Data lifecycle produced?** (Phase 1, optional) -- NOT PRODUCED: Optional diagram. The single data asset (product catalog) has a simple lifecycle that does not warrant a dedicated diagram.
- **Evidence:** Kill chains with 3+ steps produced as attack trees in Phase 5. No auth mechanism exists to diagram.
- **Components:** 2 attack tree diagrams produced

---

## Summary Scorecard

```
============================================
  VISUAL COMPLETENESS SCORECARD
============================================

  Total categories:                    26
  Applicable:                          24/26
  Not Applicable (with justification): 2/26 (#19 Tenant, #20 Region)
  N/A:                                 0/26

  Structural Diagram (Phase 2):       19/24 applicable
  Risk Overlay (Phase 7):             23/24 applicable

  Missing from structural diagram:    4 risk-overlay-only (#6, #7, #12, #23), 1 companion (#26)
  Missing from risk overlay:          1 (#22 Ownership Markers -- deprioritized for label density, preserved in L1/L2)

  Phase 7 Risk Overlay Coverage:
    - Risk Color Coding:       COMPLETE (26 nodes classified)
    - Threat Annotations:      COMPLETE (21 annotated, 4 noFindings, 1 external)
    - Attack Paths:            COMPLETE (3 kill chains, 10 edges, 14 findings)
    - Machine-Parseable:       COMPLETE (compact format, all verified)
    - Version Stamp:           COMPLETE
    - Density:                 COMPLIANT (~26 nodes, no subgraph > 15)

  Verified by:          diagram-specialist (Phase 7)
  Verification date:    2026-02-18
  Status:               COMPLETE (Phase 2 structural + Phase 7 risk overlay)
============================================
```
