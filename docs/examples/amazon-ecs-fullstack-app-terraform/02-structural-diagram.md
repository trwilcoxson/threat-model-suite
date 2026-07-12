# Diagram Specialist — Phase 2 Structural Diagram

## Metadata
| Field | Value |
|-------|-------|
| Agent | diagram-specialist |
| Phase | 2 (Structural — L1/L2/L3, no risk overlay) |
| Date | 2026-07-11 |
| Target System | AWS ECS Fullstack App (Terraform Demo) |
| Layer strategy | **Full 4-layer** (medium system: 13 components → 6-20 band, mermaid-layers.md §6). L1/L2/L3 produced here; **L4 threat overlay deferred to Phase 7** (findings not yet scored). |
| Node-id contract | Reuses canonical `recon.json` ids: C1-C13, D1-D6, E1-E5, TB1-TB6, R0-R5, X1-X5. |
| Rendering | All three layers render clean with `@mermaid-js/mermaid-cli` + `mermaid-config.json` (`-w 3000 --scale 2`); PNG sizes 0.59-1.37 MB (no 67-byte stubs). |
| Scope note | Phase 2 forbids risk content. No risk colors, no `⚠`/L×I annotations, no attack-path overlays, no `:::highRisk`/`medRisk`/`lowRisk`. Those are Phase 7. |

## Summary
Three structural Mermaid flowcharts, one concern per layer, shared node ids so specialists and Phase 7 cross-reference cleanly:

- **L1 — Architecture** (`ecs-fullstack-L1-architecture.mmd`): factual C4-level topology. Every process (C1-C13), data store (D1-D6), and external entity/dependency, with tech + ownership markers, inside VPC/subnet network zones and a CI/CD control plane. Typed data / control / build-deploy edges only.
- **L2 — Trust & Identity** (`ecs-fullstack-L2-trust-identity.mmd`): all six trust boundaries (TB1-TB6) as dashed, trust-level-colored subgraphs; the four IAM roles (R1-R4) as identity diamonds; the present security controls (open SG, private-subnet SG chaining, ALB health check, blue/green rollback) as control subroutines; AUTH / ADMIN / KEY / CTRL edges.
- **L3 — Data** (`ecs-fullstack-L3-data.mmd`): three data-classification zones (INTERNAL/PUBLIC, CONFIDENTIAL, RESTRICTED); encryption state (`[ENC]`/`[PLAIN]`) on **every** edge — the headline that all app-layer HTTP is `[PLAIN]`; the lone GitHub PAT secret (no vault/KMS) as a secrets hexagon; `[KEY]` credential flows; at-rest posture and 30-day retention in node labels.

---

## L1 — Architecture

Factual topology. Neutral styling only. Network zones (VPC `10.120.0.0/16`, public/private subnets) and the CI/CD control plane are structural grouping subgraphs, not trust boundaries (those are L2). Every edge is typed (Data `-->`, Control `-.-> [CTRL]`, Build/Deploy `--> [BUILD]`, Async `--> [ASYNC]`, Admin `-.-> [ADMIN]`) and carries protocol + sensitivity.

```mermaid
flowchart TD
    %% Version: 2026-07-11 | Phase: 2 | System: AWS ECS Fullstack Demo | Layer: L1
    R0["Anonymous Internet User\n(browser · no credential)"]:::external
    R5["Terraform Operator / Developer\n(AWS creds + GitHub PAT)"]:::external
    X1["GitHub Repository\n[vendor:GitHub] source + PAT"]:::externalDep
    X4["Docker Base Images\nbitnami/node:latest, nginx:latest\n[vendor:public-ECR]"]:::externalDep

    subgraph VPC["VPC 10.120.0.0/16 · AWS Account · Single Region · 2 AZ"]
        subgraph PUB["Public Subnets — ALB tier"]
            C4(["Client ALB\nAWS ALB · internet-facing · HTTP:80\n[vendor:AWS] [managed]"]):::neutral
            C5(["Server / API ALB\nAWS ALB · internet-facing · HTTP:80\n[vendor:AWS] [managed]"]):::neutral
        end
        subgraph PRIV["Private Subnets — ECS Fargate task tier"]
            C6(["ECS Cluster\nAmazon ECS on Fargate\n[vendor:AWS] [managed]"]):::neutral
            C7(["ECS Service — client task\nawsvpc · Fargate\n[vendor:AWS] [managed]"]):::neutral
            C8(["ECS Service — server task\nawsvpc · Fargate\n[vendor:AWS] [managed]"]):::neutral
            C1(["Client SPA\nVue.js 2 · bootstrap-vue · Nginx\n[self-managed]"]):::neutral
            C2(["Server API\nNode.js · Express 4 · aws-sdk v2\n[self-managed]"]):::neutral
            C3(["Swagger / API Docs\nswagger-ui-express · /api/docs\n[self-managed]"]):::neutral
        end
    end

    subgraph CICD["CI/CD Control Plane"]
        C9[/"CodePipeline\nSource/Build/Deploy · GitHub v1\n[vendor:AWS] [managed]"/]:::pipeline
        C10[/"CodeBuild (server + client)\nstandard:4.0 · privileged_mode\n[vendor:AWS] [managed]"/]:::pipeline
        C11[/"CodeDeploy\nblue/green ECS · ECSAllAtOnce\n[vendor:AWS] [managed]"/]:::pipeline
        C12(["ECS Autoscaling + CloudWatch\nApp Auto Scaling · CPU/mem target\n[vendor:AWS] [managed]"]):::neutral
        C13(["SNS Topic\ndeployment notifications\n[vendor:AWS] [managed]"]):::neutral
    end

    D1[("DynamoDB\nproduct catalog · PAY_PER_REQUEST\n[vendor:AWS] [managed]")]:::dataStore
    D2[("S3 assets bucket\nproduct images · acl=private\n[vendor:AWS] [managed]")]:::dataStore
    D3[("S3 artifact bucket\nsource + build artifacts\n[vendor:AWS] [managed]")]:::dataStore
    D4[("ECR repositories\nserver + client images · MUTABLE\n[vendor:AWS] [managed]")]:::dataStore
    D5[("CloudWatch Logs\nawslogs · 30-day retention\n[vendor:AWS] [managed]")]:::dataStore
    D6[("Terraform State\nlocal file · contains github_token\n[self-managed]")]:::dataStore

    R0 -->|"HTTP: SPA page load [PUBLIC] [PLAIN]"| C4
    C4 -->|"HTTP: forward to client task [INTERNAL] [PLAIN]"| C7
    C7 -.->|"[CTRL] ECS runs SPA container [INTERNAL]"| C1
    R0 -->|"HTTP: GET /api/getAllProducts,/status [PUBLIC] [PLAIN]"| C5
    C5 -->|"HTTP: forward to server task [INTERNAL] [PLAIN]"| C8
    C8 -.->|"[CTRL] ECS runs API container [INTERNAL]"| C2
    C2 -.->|"[CTRL] serves /api/docs [PUBLIC]"| C3
    C2 -->|"HTTPS: DocumentClient.scan catalog [INTERNAL]"| D1
    R0 -->|"HTTPS: product image fetch [INTERNAL]"| D2
    C7 -->|"HTTP: awslogs task logs [INTERNAL]"| D5
    C8 -->|"HTTP: awslogs task logs [INTERNAL]"| D5
    R5 -->|"[BUILD] git push to main [INTERNAL]"| X1
    R5 -.->|"[ADMIN] terraform apply · local state [RESTRICTED]"| D6
    X1 -->|"[BUILD] source poll PollForSourceChanges [CONFIDENTIAL]"| C9
    C9 -->|"[BUILD] store source + artifacts [CONFIDENTIAL]"| D3
    C9 -->|"[BUILD] trigger build stage [INTERNAL]"| C10
    X4 -->|"[BUILD] pull base image :latest [INTERNAL]"| C10
    C10 -->|"[BUILD] docker build/push [CONFIDENTIAL]"| D4
    C10 -->|"[BUILD] build logs [INTERNAL]"| D5
    C9 -->|"[BUILD] trigger deploy stage [INTERNAL]"| C11
    C11 -.->|"[CTRL] blue/green deploy [INTERNAL]"| C6
    D4 -.->|"[CTRL] image pull on task start [INTERNAL]"| C6
    C6 -.->|"[CTRL] schedule client tasks [INTERNAL]"| C7
    C6 -.->|"[CTRL] schedule server tasks [INTERNAL]"| C8
    C11 -->|"[ASYNC] deploy notifications [INTERNAL]"| C13
    C12 -.->|"[CTRL] autoscaling CPU/mem [INTERNAL]"| C8

    subgraph Legend["Legend — L1 Symbols & Edge Types"]
        LG1["[ ] External Entity / Dependency"]:::external
        LG2["([ ]) Process / Service"]:::neutral
        LG3["[( )] Data Store"]:::dataStore
        LG4["[/ /] CI/CD Pipeline"]:::pipeline
        LG5["--> Data flow (default)"]
        LG6["-.-> [CTRL] Control/API"]
        LG7["--> [BUILD] Build/Deploy (orange)"]
        LG8["--> [ASYNC] Async/Event (green)"]
        LG9["-.-> [ADMIN] Admin/Ops (red)"]
    end

    linkStyle 11,13,14,15,16,17,18,19 stroke:#f39c12,stroke-width:2px
    linkStyle 12 stroke:#cc0000,stroke-width:2px
    linkStyle 24 stroke:#27ae60,stroke-width:2px

    classDef neutral fill:#f5f5f5,stroke:#666,stroke-width:1px,color:#000
    classDef external fill:#cce5ff,stroke:#004085,stroke-width:1px,color:#000
    classDef dataStore fill:#e2e3e5,stroke:#383d41,stroke-width:1px,color:#000
    classDef pipeline fill:#d5dbdb,stroke:#7f8c8d,stroke-width:1px,color:#000
    classDef externalDep fill:#f5f5f5,stroke:#333,stroke-width:3px,stroke-dasharray:3,color:#000
```

**L1 note — backend ALB is public.** Both `R0 --> C4` and `R0 --> C5` originate at the browser: the SPA's `RestServices.js` calls `http://<SERVER_ALB>/api/getAllProducts` directly, so the API ALB (C5) is reached from the Internet, not brokered by the front-end. This corrects the provided architecture PNG's implied front→back internal hop.

---

## L2 — Trust & Identity

Trust boundaries as dashed subgraphs, colored by trust level (red = low/Internet, orange = medium/VPC, blue = identity mediation, purple = account). All six recon boundaries appear. IAM roles are identity diamonds; present controls are control subroutines. AUTH (`--o`, blue), ADMIN (`-.->`, red), KEY (`==>`), and CTRL (`-.->`) edges.

```mermaid
flowchart TD
    %% Version: 2026-07-11 | Phase: 2 | System: AWS ECS Fullstack Demo | Layer: L2
    R0["Anonymous Internet User\n(no credential)"]:::external
    R5["Terraform Operator / Developer\n(AWS creds + GitHub PAT)"]:::external

    subgraph TB5["TB5 · AWS Account / Region boundary"]
        style TB5 stroke:#8e44ad,stroke-width:2px,stroke-dasharray: 5 5

        subgraph TB1["TB1 · Internet edge — public ALBs (0.0.0.0/0:80 HTTP)"]
            style TB1 stroke:#e74c3c,stroke-width:2px,stroke-dasharray: 5 5
            C4(["Client ALB\ninternet-facing · HTTP:80"]):::neutral
            C5(["Server / API ALB\ninternet-facing · HTTP:80"]):::neutral
            SGpub[["Security Group\n0.0.0.0/0:80 open · no WAF · no TLS\n[control-owner:none]"]]:::control
        end

        subgraph TB6["TB6 · VPC perimeter (IGW / single NAT egress)"]
            style TB6 stroke:#f39c12,stroke-width:2px,stroke-dasharray: 5 5
            subgraph TB2["TB2 · Public subnet -> Private subnet (ECS tasks)"]
                style TB2 stroke:#f39c12,stroke-width:2px,stroke-dasharray: 5 5
                C6(["ECS Cluster\nFargate"]):::neutral
                C7(["ECS client task\nVue/Nginx"]):::neutral
                C8(["ECS server task\nExpress · aws-sdk v2"]):::neutral
                PrivCtl[["Private Subnets + SG chaining\ntasks reachable only from ALB SG\n[control-owner:Platform]"]]:::control
                HC[["ALB Health Check\nGET /status , /\n[control-owner:Platform]"]]:::control
            end
        end

        subgraph TB3["TB3 · ECS task -> AWS services via IAM task role"]
            style TB3 stroke:#2980b9,stroke-width:2px,stroke-dasharray: 5 5
            R1{"ECS execution role\nECR pull · log write\n[vendor:AWS]"}:::identity
            R2{"ECS task role\nDynamoDB/S3 scoped\niam:PassRole * (broad)\n[vendor:AWS]"}:::identity
            D1[("DynamoDB\nproduct catalog")]:::dataStore
            D2[("S3 assets\nproduct images")]:::dataStore
        end

        subgraph TB4["TB4 · CI/CD supply chain (GitHub -> Pipeline -> ECR -> ECS)"]
            style TB4 stroke:#e67e22,stroke-width:2px,stroke-dasharray: 5 5
            X1["GitHub Repo\nsource + OAuth PAT"]:::externalDep
            C9[/"CodePipeline\nGitHub v1 · PollForSourceChanges"/]:::pipeline
            C10[/"CodeBuild\nprivileged_mode · standard:4.0"/]:::pipeline
            C11[/"CodeDeploy\nblue/green ECS"/]:::pipeline
            R3{"DevOps role\ns3:*/ecs:*/iam:PassRole *\n[vendor:AWS]"}:::identity
            R4{"CodeDeploy role\nAWSCodeDeployRoleForECS\n[vendor:AWS]"}:::identity
            D4[("ECR\nMUTABLE · no scan-on-push")]:::dataStore
            BG[["Blue/Green Deploy\nauto-rollback on failure\n[control-owner:Platform]"]]:::control
        end

        D6[("Terraform State\nlocal · plaintext PAT")]:::dataStore
    end

    R0 -->|"HTTP: anonymous, no credential [PUBLIC] [PLAIN]"| C4
    R0 -->|"HTTP: anonymous API call [PUBLIC] [PLAIN]"| C5
    SGpub -.->|"[CTRL] allow 0.0.0.0/0:80, no WAF/TLS [PUBLIC]"| C5
    C4 -->|"HTTP: forward to task [INTERNAL] [PLAIN]"| C7
    C5 -->|"HTTP: forward to task [INTERNAL] [PLAIN]"| C8
    PrivCtl -.->|"[CTRL] ingress only from ALB SG [INTERNAL]"| C8
    HC -.->|"[CTRL] health check GET /status [INTERNAL]"| C8
    C8 --o|"[AUTH] assumes ECS task role [RESTRICTED]"| R2
    C8 --o|"[AUTH] image pull via execution role [INTERNAL]"| R1
    R2 -.->|"[CTRL] IAM: Get/Query/Scan catalog [INTERNAL]"| D1
    R2 -.->|"[CTRL] IAM: GetObject/ListBucket [INTERNAL]"| D2
    X1 ==>|"[KEY] OAuth PAT, long-lived [RESTRICTED]"| C9
    C10 --o|"[AUTH] assumes DevOps role [RESTRICTED]"| R3
    R3 -.->|"[ADMIN] s3:*/ecs:*/iam:PassRole * [RESTRICTED]"| D4
    C11 --o|"[AUTH] assumes CodeDeploy role [INTERNAL]"| R4
    R4 -.->|"[CTRL] blue/green register + deploy [INTERNAL]"| C6
    BG -.->|"[CTRL] auto-rollback on failure [INTERNAL]"| C6
    R5 -.->|"[ADMIN] terraform apply · PAT to local state [RESTRICTED]"| D6

    subgraph Legend["Legend — L2 Trust & Identity"]
        LG1["--- dashed subgraph = Trust Boundary"]
        LG2["{ } Identity / IAM role"]:::identity
        LG3["[[ ]] Security Control"]:::control
        LG4["--o [AUTH] AuthN/AuthZ (blue)"]
        LG5["==> [KEY] Secrets/Keys"]
        LG6["-.-> [ADMIN] Admin/Ops (red)"]
        LG7["-.-> [CTRL] Control/API"]
    end

    linkStyle 7,8,12,14 stroke:#2980b9,stroke-width:2px
    linkStyle 13,17 stroke:#cc0000,stroke-width:2px

    classDef neutral fill:#f5f5f5,stroke:#666,stroke-width:1px,color:#000
    classDef external fill:#cce5ff,stroke:#004085,stroke-width:1px,color:#000
    classDef dataStore fill:#e2e3e5,stroke:#383d41,stroke-width:1px,color:#000
    classDef identity fill:#d4e6f1,stroke:#2980b9,stroke-width:1px,color:#000
    classDef control fill:#abebc6,stroke:#27ae60,stroke-width:1px,color:#000
    classDef pipeline fill:#d5dbdb,stroke:#7f8c8d,stroke-width:1px,color:#000
    classDef externalDep fill:#f5f5f5,stroke:#333,stroke-width:3px,stroke-dasharray:3,color:#000
```

**L2 note — no AuthN/AuthZ at the application edge.** TB1 carries anonymous `[PLAIN]` traffic straight through; there is no auth gateway node because none exists in the system (Login.vue is an inert stub). The identity mediation (`--o [AUTH]`) that *does* exist is all machine-to-cloud: task→role and pipeline→role assumption. `iam:PassRole *` on both the task role (R2) and DevOps role (R3) is drawn as the broad grant it is. No `sequenceDiagram` companion is warranted (recon §1.9: auth sequence N/A).

---

## L3 — Data

Data-classification zones by sensitivity; encryption state on every edge. The system's defining data fact — all application HTTP is unencrypted — is visible as `[PLAIN]` on every ingress/east-west edge, while AWS-SDK/API calls to managed services are `[ENC]` (AWS-managed TLS). The single secret (GitHub PAT) is a secrets hexagon with an explicit "no vault/KMS" annotation; its `[KEY]` flow lands in unencrypted local Terraform state.

```mermaid
flowchart TD
    %% Version: 2026-07-11 | Phase: 2 | System: AWS ECS Fullstack Demo | Layer: L3
    R0["Anonymous Internet User\n(browser)"]:::external
    R5["Terraform Operator\n(writes state)"]:::external
    X1["GitHub Repo\n+ OAuth PAT"]:::externalDep
    C5(["Server / API ALB\nHTTP:80 · no TLS listener"]):::neutral
    C8(["ECS server task\nExpress · aws-sdk v2"]):::neutral
    C9[/"CodePipeline"/]:::pipeline
    C10[/"CodeBuild"/]:::pipeline

    subgraph ZPUB["INTERNAL / PUBLIC Data Zone — default AWS-managed encryption"]
        style ZPUB fill:#e8f8f5,stroke:#1abc9c,stroke-width:1px
        D1[("DynamoDB\ncatalog id/path/title · [INTERNAL]\nSSE: AWS-managed default [ENC]\nno PITR · no explicit KMS")]:::dataStore
        D2[("S3 assets\nproduct images · [INTERNAL/PUBLIC]\nSSE: AWS-managed default [ENC]\nno public-access-block · no versioning")]:::dataStore
        D5[("CloudWatch Logs\ntask + build logs · [INTERNAL]\nSSE: AWS-managed [ENC]\nretention: 30 days")]:::dataStore
    end

    subgraph ZCONF["CONFIDENTIAL Data Zone"]
        style ZCONF fill:#fef9e7,stroke:#f39c12,stroke-width:2px
        D3[("S3 artifacts\nsource + build output · [CONFIDENTIAL]\nSSE: AWS-managed [ENC] · force_destroy")]:::dataStore
        D4[("ECR\nserver + client images · [CONFIDENTIAL]\nSSE: AWS-managed [ENC] · MUTABLE tags")]:::dataStore
    end

    subgraph ZREST["RESTRICTED Data Zone — no vault / no KMS"]
        style ZREST fill:#fdedec,stroke:#e74c3c,stroke-width:2px
        PAT{{"GitHub PAT\nsole secret · no Secrets Manager/KMS\nno rotation"}}:::secrets
        D6[("Terraform State\nlocal terraform.tfstate · [RESTRICTED]\nunencrypted at rest [PLAIN] · no locking")]:::dataStore
    end

    R0 -->|"HTTP: API + image request [PUBLIC] [PLAIN]"| C5
    C5 -->|"HTTP: proxied to API task [INTERNAL] [PLAIN]"| C8
    C8 -->|"HTTPS: DynamoDB scan [INTERNAL] [ENC]"| D1
    C8 -->|"HTTPS: S3 GetObject [INTERNAL] [ENC]"| D2
    C8 -->|"HTTPS: awslogs stream [INTERNAL] [ENC]"| D5
    C10 -->|"HTTPS: docker push image [CONFIDENTIAL] [ENC]"| D4
    C9 -->|"HTTPS: source + artifacts [CONFIDENTIAL] [ENC]"| D3
    R0 -->|"HTTPS: direct image fetch [INTERNAL] [ENC]"| D2
    R5 ==>|"[KEY] terraform writes PAT [RESTRICTED] [PLAIN]"| PAT
    PAT ==>|"[KEY] persisted into local state [RESTRICTED] [PLAIN]"| D6
    X1 ==>|"[KEY] OAuth PAT to pipeline config [RESTRICTED] [PLAIN]"| C9

    subgraph Legend["Legend — L3 Data & Encryption"]
        LG1["shaded subgraph = Data Classification Zone"]
        LG2["{{ }} Secret (no KMS/vault)"]:::secrets
        LG3["[( )] Data Store"]:::dataStore
        LG4["[ENC] = encrypted transit/at-rest"]
        LG5["[PLAIN] = unencrypted (headline: all HTTP is PLAIN)"]
        LG6["==> [KEY] Secrets/Keys flow"]
    end

    classDef neutral fill:#f5f5f5,stroke:#666,stroke-width:1px,color:#000
    classDef external fill:#cce5ff,stroke:#004085,stroke-width:1px,color:#000
    classDef dataStore fill:#e2e3e5,stroke:#383d41,stroke-width:1px,color:#000
    classDef secrets fill:#f9e79f,stroke:#f39c12,stroke-width:2px,color:#000
    classDef pipeline fill:#d5dbdb,stroke:#7f8c8d,stroke-width:1px,color:#000
    classDef externalDep fill:#f5f5f5,stroke:#333,stroke-width:3px,stroke-dasharray:3,color:#000
```

**L3 note — `[PLAIN]` vs `[ENC]` split.** Every edge that touches the browser or crosses the ALB→task hop is `[PLAIN]` HTTP (no TLS listener is created). Everything from an ECS task or CodeBuild to a managed AWS service rides AWS-managed TLS (`[ENC]`). At rest, all AWS stores get AWS-owned default encryption (`[ENC]`, but no explicit SSE-KMS); the one store that is genuinely plaintext at rest is the **local Terraform state** holding the PAT. Category #10 (Secrets/Key Mgmt) was marked N/A in recon because there is no vault/KMS/HSM — the PAT node here draws that *absence* explicitly (the sole secret, unmanaged), rather than a managed secrets service.

---

## Node-ID Reconciliation (recon.json → diagram nodes)

Every element in the reconnaissance appears in at least one layer under its canonical id.

| recon id | Element | L1 | L2 | L3 |
|----------|---------|:--:|:--:|:--:|
| C1 | Client SPA | ✓ | (in C7) | — |
| C2 | Server API | ✓ | (in C8) | — |
| C3 | Swagger / API docs | ✓ | — | — |
| C4 | Client ALB | ✓ | ✓ | — |
| C5 | Server/API ALB | ✓ | ✓ | ✓ |
| C6 | ECS Cluster | ✓ | ✓ | — |
| C7 | ECS client service | ✓ | ✓ | — |
| C8 | ECS server service | ✓ | ✓ | ✓ |
| C9 | CodePipeline | ✓ | ✓ | ✓ |
| C10 | CodeBuild | ✓ | ✓ | ✓ |
| C11 | CodeDeploy | ✓ | ✓ | — |
| C12 | Autoscaling + CloudWatch | ✓ | — | — |
| C13 | SNS topic | ✓ | — | — |
| D1-D6 | Data stores | ✓ | D1,D2,D4,D6 | ✓ (all 6) |
| E1-E5 | Entry points | edges from R0/X1/health-check | ingress edges | ingress edges |
| TB1-TB6 | Trust boundaries | (network zones) | ✓ (all 6 subgraphs) | (data zones) |
| R0 | Anonymous user | ✓ | ✓ | ✓ |
| R1-R4 | IAM roles | (implicit in edges) | ✓ (identity diamonds) | — |
| R5 | Terraform operator | ✓ | ✓ | ✓ |
| X1 | GitHub + PAT | ✓ | ✓ | ✓ |
| X2,X3 | npm deps | (feed C10 build) | — | — |
| X4 | Docker base images | ✓ | — | — |
| X5 | CodeBuild image | (C10 label) | (C10 label) | — |

Entry points E1-E5 are represented as edges rather than nodes (they are ingress interfaces): E1 `R0→C4`, E2 `R0→C5`, E3 `C2→C3` + public reach via C5, E4 `X1→C9`, E5 `HC→C8`. X2/X3/X5 (npm/build-image supply chain) are captured in the CodeBuild node label and the `X4→C10` base-image edge; they surface as first-class `:::externalDep` nodes in the Phase-7 SBOM/dependency visual, not the structural DFD.

## Visual Completeness — Phase 2 Coverage

Structural categories from `visual-completeness-checklist.md` (risk-overlay-only categories #6/#7/#12/#23 and companion #26 are correctly deferred to Phase 7):

| # | Category | Covered | Where |
|---|----------|:-------:|-------|
| 1 | External Entities | ✓ | R0, R5, X1, X4 (L1); R0/R5 (L2/L3) |
| 2 | Processes | ✓ | C1-C13 stadiums/parallelograms (L1) |
| 3 | Data Stores | ✓ | D1-D6 cylinders (L1, L3) |
| 4 | Trust Boundaries | ✓ | TB1-TB6 dashed subgraphs (L2) |
| 5 | Data Flow Labels | ✓ | typed edges w/ protocol + sensitivity (all layers) |
| 8 | Component Metadata | ✓ | tech + ownership on every process/store (L1) |
| 9 | Identity Elements (IAM) | ✓ | R1-R4 identity diamonds (L2) |
| 11 | Control vs Data Plane | ✓ | `-.-> [CTRL]` vs `-->`; CI/CD plane subgraph (L1/L2) |
| 13 | Control Indicators | ✓ | SG, private-subnet chaining, health check, blue/green (L2) |
| 14 | Data Classification Markers | ✓ | 3 zone subgraphs (L3) |
| 15 | Encryption State | ✓ | `[ENC]`/`[PLAIN]` on every edge (L3) |
| 16 | Network Zones | ✓ | VPC 10.120.0.0/16 + public/private subnets (L1) |
| 17 | Deployment Pipeline | ✓ | C9-C11 parallelograms + ECR (L1/L2) |
| 18 | External Dependency Markers | ✓ | GitHub X1, base images X4 double-border (L1) |
| 21 | Typed Edges | ✓ | all edges use §4 typed prefixes |
| 22 | Ownership Markers | ✓ | `[managed]`/`[self-managed]`/`[vendor:X]` (L1) |
| 24 | Version Stamp | ✓ | `%% Version: ... | Layer: L{N}` on all 3 |
| 25 | Density Compliance | ✓ | ≤23 core nodes/layer, subgraph-grouped |
| 10 | Secrets/Key Mgmt | ✓ (absence) | PAT hexagon "no vault/KMS" (L3) — recon marked N/A; drawn as the finding it is |
| 6,7,12,23 | Risk color / threat annots / attack paths / machine-parseable | deferred | **Phase 7 (L4)** |
| 26 | Companion (attack tree) | deferred | **Phase 5/7** |
| 19,20 | Tenant / Region boundaries | N/A | single-tenant, single-region (justified in checklist) |

**Structural coverage: 18/18 applicable Phase-2 categories, plus #10 drawn as an explicit absence.**

## Structural Acceptance Gate (self-check)

| Gate item | Status | Evidence |
|-----------|:------:|----------|
| Layers present per scaling (13 comp → L1,L2,L3 now; L4 Phase 7) | PASS | 3 `mermaid` blocks, each stamped `Layer: L1/L2/L3` |
| Every edge typed + annotated (protocol + sensitivity; `[ENC]`/`[PLAIN]` where it varies) | PASS | 0 bare edges; 100% of edges carry a `[PUBLIC|INTERNAL|CONFIDENTIAL|RESTRICTED]` and/or typed prefix; L3 every edge carries `[ENC]`/`[PLAIN]` |
| Trust boundaries drawn (all inventory boundaries appear) | PASS | TB1-TB6 as dashed subgraphs in L2 |
| Component metadata + ownership on processes/stores | PASS | every L1 stadium/cylinder carries tech + `[managed]`/`[self-managed]`/`[vendor:X]` |
| Legend + version stamp on every diagram | PASS | per-layer Legend subgraph + `%% Version:` stamp |
| No risk content in Phase 2 | PASS | no `:::highRisk`/`medRisk`/`lowRisk`, no `⚠`/L×I, no attack-path overlays |
| Renders clean (no stub) | PASS | mmdc render: L1 1.37 MB, L2 1.08 MB, L3 0.59 MB PNG |

---

## Execution Log

### Process Health
| Metric | Value |
|--------|-------|
| Inputs read | 01-reconnaissance.md, recon.json, visual-completeness-checklist.md, SKILL.md (Phase 2 + gate), mermaid-spec.md, mermaid-layers.md, mermaid-templates.md, mermaid-review-checklist.md, mermaid-config.json, diagram_checks.py |
| Layers produced | 3 (L1 Architecture, L2 Trust & Identity, L3 Data) |
| Files written | 1 (02-structural-diagram.md); 3 `.mmd` + 3 `.png` validation artifacts in scratchpad |
| Errors encountered | 0 |
| Self-assessed output quality | HIGH |

### Diagram Complexity
| Layer | Core nodes | Edges | Subgraphs | Notes |
|-------|:----------:|:-----:|:---------:|-------|
| L1 Architecture | 23 (4 external, 13 comp, 6 store) | 26 | 4 (VPC, PUB, PRIV, CICD) + Legend | 8 BUILD, 1 ADMIN, 1 ASYNC, rest data/CTRL |
| L2 Trust & Identity | 23 (2 principal, 4 IAM, 3 ALB/task, 3 pipeline, 3 store, 4 control, 4 misc) | 18 | 6 trust boundaries (TB1-TB6) + Legend | 4 AUTH, 2 ADMIN, 1 KEY, rest CTRL/data |
| L3 Data | 14 (2 external, 1 dep, 4 process, 6 store, 1 secret) | 11 | 3 classification zones + Legend | 3 KEY, all edges carry `[ENC]`/`[PLAIN]` |

Total across layers: 55 edges, 13 content subgraphs. Each layer stays under the 25-node / 15-per-subgraph density limits (spec §6).

### Mermaid Syntax Issues Encountered
- **None material.** All three layers parsed and rendered on the first CLI pass (`@mermaid-js/mermaid-cli` + `mermaid-config.json`, `-w 3000 --scale 2`).
- Precautions taken up front to avoid known pitfalls: every node/edge label double-quoted (labels contain `(`, `/`, `:`, `*`, `.`); `classDef` blocks placed at end-of-diagram; `linkStyle` indices counted against edge-statement order only (verified in-range by successful render — an out-of-range index would have errored); legend edge-type swatches written as quoted rectangle text (not real arrows) so they neither render as stray edges nor pollute the typed-edge fraction.
- Nesting depth: L2 has one 3-level branch (TB5 › TB6 › TB2); rendered cleanly, so no flattening needed (spec §2 advises flatten "where possible", not mandatory).

### Visual Completeness Categories — Covered vs Skipped
- **Covered (18 structural + #10 as absence)**: see coverage table above. Highest-signal visuals for this system are all present — `[PLAIN]` on both public ALBs (L1/L3), the Internet→public-ALB boundary on *both* ALBs (L2 TB1), the CI/CD supply-chain boundary (L2 TB4), and the `iam:PassRole *` task/DevOps roles (L2 R2/R3).
- **Deferred to Phase 7 (correct, not skipped)**: #6 Risk Color, #7 Threat Annotations, #12 Attack Paths, #23 Machine-Parseable Annotations (all L4), #26 Companion attack tree (Phase 5/7). Phase 2 forbids risk content.
- **N/A (justified in recon/checklist)**: #19 Tenant (single-tenant), #20 Region (single-region).

### Self-Assessed Diagram Quality
- **Structural fidelity — HIGH.** All 13 components, 6 stores, 5 entry points, 6 trust boundaries, 6 roles, 5 external deps are represented under canonical recon ids; the one non-obvious topology fact (backend API ALB is Internet-reachable directly from the browser) is drawn, not smoothed over.
- **Spec compliance — HIGH.** Passes every structural acceptance-gate item and the deterministic `diagram_checks.py` structural requirements (layer stamps, ≥90% edges labeled / ≥60% annotated — actual 100%, trust-boundary subgraphs present, ownership markers on L1 process/store nodes, legend + version stamp + classDef).
- **Known limitation.** `linkStyle` edge-coloring is index-based and correct-by-render, but if a future edit reorders edges the indices must be recounted; noted for the Phase-7 L4 author who will copy the L1 structure. X2/X3/X5 supply-chain deps are folded into node labels/edges here by design (structural DFD) and become first-class nodes in the Phase-7 SBOM visual.
- **Handoff.** L4 (Phase 7) should copy the L1 node/edge skeleton verbatim and layer risk classes + `⚠ STRIDE · L×I` annotations + attack-path `==>` overlays onto it; L2/L3 boundaries and zones carry forward unchanged. Specialists (privacy/compliance/code-review) can cite any node by its recon id.
