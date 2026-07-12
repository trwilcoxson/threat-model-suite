# Visual Completeness Checklist — AWS ECS Fullstack App (Terraform Demo)

Filled during **Phase 1** (applicability). Phase 2 (structural) and Phase 7 (risk overlay) columns are checked by the diagram-specialist; the validation-specialist confirms completeness afterward. System archetype for the Applicability Guide: **Cloud-native single-region fullstack web-app** (between "Single-service" and "Cloud-native" columns).

Legend: **YES** = represent in diagrams · **NO** = not applicable (one-line justification) · Phase 2 / Phase 7 checkboxes filled by the diagram-specialist.

| # | Category | Applicable? | Justification / Evidence (Phase 1) | Intended diagram components |
|---|----------|:-----------:|-----------------------------------|-----------------------------|
| 1 | External Entities | **YES** | Anonymous Internet users, GitHub (source), browsers consuming S3 image URLs. | `Users`, `GitHub` as `:::external` rectangles |
| 2 | Processes | **YES** | 13 processes (SPA, API, Swagger, 2 ALBs, ECS cluster/services, CodePipeline/Build/Deploy, Autoscaling, SNS). | C1-C13 stadium nodes |
| 3 | Data Stores | **YES** | 6 stores: DynamoDB, S3 assets, S3 artifacts, ECR, CloudWatch Logs, local TF state. | D1-D6 cylinders |
| 4 | Trust Boundaries | **YES** | 6 boundaries (Internet→ALB, public→private subnet, task→AWS via IAM, CI/CD, account/region, VPC). | TB1-TB6 dashed subgraphs |
| 5 | Data Flow Labels | **YES** | Distinct flows carry protocol + sensitivity (HTTP catalog, IAM-signed DynamoDB/S3, GitHub source). | Edge labels `Protocol: data [SENSITIVITY]` |
| 6 | Risk Color Coding | **YES** | Findings expected across all components; risk classes applied in Phase 7. | `:::highRisk/medRisk/lowRisk/noFindings` (Phase 7) |
| 7 | Threat Annotations | **YES** | STRIDE-LM findings will attach to public ALBs, API, IAM, pipeline. | Enriched node labels (Phase 7) |
| 8 | Component Metadata | **YES** | Tech stack known per node (Vue/Nginx, Express/aws-sdk, Fargate, ALB…). | Multi-line node labels |
| 9 | Identity Elements (IAM) | **YES** | 4 IAM roles are central (task-exec, task with `PassRole *`, devops, codedeploy). | R1-R4 `:::identity` diamonds |
| 10 | Secrets/Key Mgmt | **NO** | No vault/HSM/KMS in the design; only a GitHub PAT in local TF state + build-time `sed` templating — there is no secrets-management node to draw (its absence is a finding, not a diagram element). | — |
| 11 | Control Plane vs Data Plane | **YES** | CI/CD (CodePipeline/Deploy/Autoscaling) is a distinct control plane vs runtime request/data plane. | `-.->` control edges vs `-->` data edges |
| 12 | Attack Paths (kill chains) | **YES** | ≥3 multi-step chains expected (public HTTP API, supply chain, task-role pivot). | `==>` red overlays (Phase 7) |
| 13 | Control Indicators | **YES** | Present controls to show: security groups, private subnets, blue/green rollback, health checks, autoscaling. (Notable absences — WAF/TLS — annotated too.) | `[[SG]]`, `[[HealthCheck]]`, `[[Blue/Green]]` `:::control` |
| 14 | Data Classification Markers | **YES** | Data spans INTERNAL (catalog/images), CONFIDENTIAL (artifacts/ECR), RESTRICTED (TF state + PAT). | Classification zone subgraphs |
| 15 | Encryption State Indicators | **YES** | Headline: all HTTP is plaintext (no TLS); at-rest is default-managed only. | `[PLAIN]` on all ingress/east-west edges, `[ENC]` where AWS-managed |
| 16 | Network Zones | **YES** | VPC `10.120.0.0/16`, 2 public + 4 private subnets, IGW, single NAT. | VPC / public / private subnet subgraphs with CIDRs |
| 17 | Deployment Pipeline | **YES** | Full CodePipeline → CodeBuild → ECR / CodeDeploy → ECS with GitHub source. | C9-C11 + ECR `:::pipeline` parallelograms |
| 18 | External Dependency Markers | **YES** | GitHub, npm (server+client), public ECR base images (`:latest`), CodeBuild image. | X1-X5 `:::externalDep` double-border |
| 19 | Tenant Boundaries | **NO** | Single-tenant demo; no tenancy model, tenant IDs, or per-tenant isolation anywhere in code/IaC. | — |
| 20 | Region Boundaries | **NO** | Single-region deployment (one `aws_region` var, no multi-region/replication resources). | — |
| 21 | Typed Edges | **YES** | Flows span Data, Control/API, AuthN (build OAuth), Secrets (PAT), Admin/Ops, Build/Deploy types. | All edges use §4 typed prefixes |
| 22 | Ownership Markers | **YES** | Clear split: self-managed app code (SPA/API) vs AWS-`[managed]` services vs `[vendor:GitHub]`. | `[managed]`/`[self-managed]`/`[vendor:X]` on nodes |
| 23 | Machine-Parseable Annotations | **YES** | Phase 7 threat labels use `⚠ STRIDE · LxI=Score BAND` + CWE format. | Enriched labels on risk-bearing nodes (Phase 7) |
| 24 | Version Stamp | **YES** | Always applicable. | `%% Version: 2026-07-11 \| Phase: N \| System: AWS ECS Fullstack Demo` |
| 25 | Density Compliance | **YES** | Always applicable; 13 components < 25 total, but CI/CD + runtime may need subgraph grouping (≤15/subgraph). | Node/subgraph counts within limits |
| 26 | Companion Diagrams | **YES** | **Attack tree** (Phase 5, ≥3 kill chains) applicable. **Auth sequence NOT applicable** — no AuthN/AuthZ exists. **Data lifecycle** omitted — no personal data. | `*-attack-tree-N.mmd`, `*-attack-flow-N.mmd` |

---

## Summary Scorecard

```
============================================
  VISUAL COMPLETENESS SCORECARD
============================================

  Total categories:                    26
  Applicable:                          23/26
  Not Applicable (with justification):  3/26   (#10 Secrets/Key Mgmt, #19 Tenant, #20 Region)
  N/A:                                  0/26

  Structural Diagram (Phase 2):        18/18 structural   (+#10 drawn as an explicit absence; done 2026-07-11)
  Risk Overlay (Phase 7):              23/23 applicable   (done 2026-07-11 — diagram-specialist)

  Not-applicable categories:           #10, #19, #20
  Risk-overlay-only categories:        #6, #7, #12, #23 — DONE in L4 (07-final-diagram.md)
  Companion caveat:                    Auth sequence N/A (no auth); data lifecycle omitted (no PII)

  Analytical visuals (Phase 7):        STRIDE matrix, L×I heat map, MITRE ATT&CK layer + Navigator JSON,
                                       RBAC matrix (R0-R5 incl. anonymous), SBOM graph — all produced.
  Companion diagrams (Phase 7):        4 attack trees + 4 attack flows (KC01-KC04); auth sequence N/A.
  Phase 7 artifacts:                   ecs-fullstack-L4-threat-overlay.mmd, ecs-fullstack-sbom.mmd,
                                       ecs-fullstack-attack-tree-{1..4}.mmd, ecs-fullstack-attack-flow-{1..4}.mmd,
                                       ecs-fullstack-attack-navigator-layer.json (all render clean, no stubs).

  Verified by:          security-architect (Phase 1); diagram-specialist (Phase 2 structural, Phase 7 overlay)
  Verification date:    2026-07-11
  Status:               COMPLETE (Phase 1 applicability + Phase 2 structural + Phase 7 risk overlay all done)
============================================
```

## Notes for Phase 2 / Phase 7
- **Scaling**: 13 components → full **4-layer** (L1-L4) approach per mermaid-layers.md §6. Consider grouping the CI/CD plane into a subgraph to stay within density limits.
- **Highest-signal visuals for this system**: encryption-state edges (all `[PLAIN]` HTTP), the Internet→public-ALB boundary on *both* ALBs, the CI/CD supply-chain boundary (TB4), and IAM identity nodes (task role `iam:PassRole *`).
- **Node-id contract**: reuse `recon.json` ids (C1-C13, D1-D6, E1-E5, TB1-TB6, R0-R5, X1-X5) as canonical Mermaid node ids so specialists and findings cross-reference cleanly.
