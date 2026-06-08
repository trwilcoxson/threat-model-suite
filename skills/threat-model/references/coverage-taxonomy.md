# Coverage Taxonomy

The production-grade item set a threat model should address — the structure behind the **coverage
ledger**. The skill attempts every *applicable* item and records a terminal state in `coverage.json`:
`present` (+source) / `partial` (+source) / `absent` (+reason) / `not-applicable` (+reason) /
`unknown` (+note on what was searched). `unknown` is first-class — it means *checked, the sources
don't say* — so gaps surface as open questions instead of being hidden.

**Tiers.** Tier 1 always applies. Tier 2 applies only when its precondition holds; the skill declares
which hold in `coverage.json` `context` (e.g. `has_api`, `multi_tenant`, `has_ai_ml`). The eval
(`evals/reliability/coverage_checks.py`) verifies structure only — every applicable item reached a
terminal state, `present` is grounded, `unknown` is noted — and **never requires a specific item to
be present** (availability varies). Correctness of the states is the coverage judge's job.

Machine source: [`coverage-taxonomy.json`](coverage-taxonomy.json) — 225 items across 52 sections.

## 1. Threat model document metadata
- `document-metadata.identity-version` — What is the threat model's identifier, title, version, and last-revision date, and is it under version control?
- `document-metadata.ownership` — Who owns this threat model and which authors/contributors produced it?
- `document-metadata.review-cadence` — When was the model last reviewed/approved by whom, and what triggers or schedule drives the next review?
- `document-metadata.scope-status` — What system/release is in scope, what is explicitly out of scope, and what is the document status (draft/reviewed/approved)?

## 2. System context
- `system-context.assumptions-constraints` — What key assumptions, constraints, and pre-existing security controls frame the system's context?
- `system-context.deployment-environment` — Where and how is the system deployed (environments, hosting model, network exposure)?
- `system-context.external-dependencies` — What external systems, services, and dependencies does the system interact with at the context level?
- `system-context.purpose` — What does the system do, what business/mission purpose does it serve, and who are its users?

## 3. Assets to protect
- `assets.inventory` — What are the system's protectable assets (data, credentials, keys, intellectual property, infrastructure, reputation)?
- `assets.ownership` — Who owns or is accountable for each asset?
- `assets.security-objectives` — Which CIA (confidentiality/integrity/availability) and other security objectives apply to each asset?
- `assets.value-impact` — What is the business value and the impact of compromise for each asset?

## 4. Data classification
- `data-classification.handling-requirements` — What handling, encryption, and access requirements apply to each classification level (at rest and in transit)?
- `data-classification.levels` — What classification levels (e.g. public/internal/confidential/restricted) exist and how is each data type assigned a level?
- `data-classification.retention` — What are the retention and disposal/deletion requirements per classification level?
- `data-classification.sensitive-data-types` — Which specific sensitive data types (PII, PHI, financial, secrets) are present and how are they tagged?

## 5. Actors and principals
- `actors.inventory` — Who/what are the actors and principals (human users, admins, services, external parties, attackers) interacting with the system?
- `actors.roles-privileges` — What roles and privilege levels does each actor hold, and what is the highest privilege available?
- `actors.threat-agents` — Which adversarial threat agents are modeled and what capabilities/motivations are attributed to them?
- `actors.trust-level` — What trust level is assigned to each actor (trusted, semi-trusted, untrusted/anonymous)?

## 6. Trust boundaries
- `trust-boundaries.controls` — What controls (authentication, validation, authorization) enforce each trust boundary crossing?
- `trust-boundaries.crossings` — Which data flows and components cross each trust boundary, and what is being trusted at the crossing?
- `trust-boundaries.identification` — Where are the trust boundaries in the system (between zones of differing trust, privilege, or ownership)?
- `trust-boundaries.privilege-changes` — Where do privilege-level or security-context changes occur across boundaries?

## 7. Architecture diagrams
- `architecture-diagrams.completeness` — Do the diagrams depict all components, data stores, flows, and external entities in scope?
- `architecture-diagrams.levels-of-detail` — Are appropriate levels of decomposition (context vs detailed/DFD levels) provided?
- `architecture-diagrams.presence-currency` — Does a current architecture/data-flow diagram exist that matches the deployed system?

## 8. Diagram annotations
- `diagram-annotations.legend-traceability` — Do diagrams include a legend and consistent labels that trace to the component/flow inventory?
- `diagram-annotations.protocols-data` — Are flows annotated with protocols, ports, data classification, and authentication on each connection?
- `diagram-annotations.trust-boundaries` — Are trust boundaries explicitly drawn/annotated on the diagrams?

## 9. Component inventory
- `component-inventory.dependencies` — What internal/external dependencies does each component have?
- `component-inventory.enumeration` — Is every component (services, processes, libraries, infrastructure elements) enumerated with a unique identifier?
- `component-inventory.responsibility-tech` — For each component, what is its responsibility, technology/runtime, and owner?
- `component-inventory.trust-classification` — What trust zone, exposure, and criticality is assigned to each component?

## 10. Data stores
- `data-stores.access-control` — Who/what can read or write each data store and how is that access controlled?
- `data-stores.backup-integrity` — How are backups, retention, and data integrity handled for each store?
- `data-stores.classification-encryption` — What data classification does each store hold and how is it protected at rest (encryption, key management)?
- `data-stores.inventory` — What data stores exist (databases, caches, queues, file/object storage, secrets stores) and what does each hold?

## 11. Data flows
- `data-flows.authn-authz` — How is each flow authenticated and authorized between endpoints?
- `data-flows.classification-direction` — What data classification and directionality applies to each flow, and which trust boundaries does it cross?
- `data-flows.enumeration` — Is each data flow enumerated with source, destination, and the data it carries?
- `data-flows.protocol-transport` — What protocol and transport protection (e.g. TLS) secures each flow in transit?

## 12. Entry points
- `entry-points.enumeration` — What are all entry points where data/requests enter the system (UIs, APIs, endpoints, ports, file uploads, message consumers)?
- `entry-points.exposure-trust` — What is the exposure (internal vs internet-facing) and trust level of each entry point?
- `entry-points.input-validation` — What authentication and input validation/sanitization gates each entry point?

## 13. Exit points
- `exit-points.data-exposure` — What data classification leaves at each exit point and how is over-exposure/leakage prevented (output encoding, redaction)?
- `exit-points.destination-trust` — What destination and trust level does each exit point send to, and how is the transfer protected?
- `exit-points.enumeration` — What are all exit points where data leaves the system (responses, outbound calls, logs, exports, notifications)?

## 14. Authentication model
- `authentication-model.credential-management` — How are credentials stored, rotated, recovered, and protected (hashing, secret storage, reset flows)?
- `authentication-model.identity-provider` — What identity provider(s) and federation/trust relationships underpin authentication, and how is provider trust established?
- `authentication-model.mechanisms` — What authentication mechanisms are used for each actor type (passwords, MFA, SSO/federation, certificates, API keys, service identities)?
- `authentication-model.session-management` — How are sessions/tokens issued, validated, scoped, expired, and revoked?

## 15. Authorization model
- `authorization-model.delegation-impersonation` — How are delegation, impersonation, and on-behalf-of access governed, scoped, and audited?
- `authorization-model.enforcement-points` — Where are authorization checks enforced (gateway, service, data layer) and is enforcement consistent across UI, API, and background jobs?
- `authorization-model.model-type` — What authorization model is used (RBAC, ABAC, ReBAC, ACLs) and where are policy decisions made (centralized PDP vs. scattered in code)?
- `authorization-model.object-level-authz` — How is object-level (per-resource) authorization enforced to prevent IDOR, and is it applied on every access path?
- `authorization-model.policy-lifecycle` — How are authorization policies and role/permission assignments reviewed, tested, and changed over time (policy lifecycle and recertification)?
- `authorization-model.privilege-escalation` — What controls prevent horizontal and vertical privilege escalation, including default-deny and least-privilege role definitions?

## 16. Identity and access management
- `identity-access-management.authentication-methods` — What authentication methods exist for users and services (passwords, MFA, passwordless, SSO/federation) and what is the assurance level?
- `identity-access-management.credential-recovery` — How do account recovery, password reset, and credential rotation work without becoming an authentication bypass?
- `identity-access-management.federation-trust` — What identity providers and federation/trust relationships exist (SAML/OIDC), and how is IdP trust, token validation, and account linking secured?
- `identity-access-management.identity-lifecycle` — How are identities provisioned, deprovisioned, and joiner/mover/leaver transitions handled for users and service/machine identities?
- `identity-access-management.privileged-access` — How is privileged/administrative access controlled (MFA enforcement, just-in-time elevation, break-glass accounts)?
- `identity-access-management.session-management` — How are sessions and tokens issued, scoped, refreshed, expired, and revoked, and how is session fixation/hijacking mitigated?

## 17. Network architecture
- `network-architecture.edge-exposure` — What is exposed at the network edge (load balancers, gateways, WAF, DDoS protection) and what is the externally reachable attack surface?
- `network-architecture.ingress-egress` — How are ingress and egress controlled (firewalls, security groups, allowlists) and is outbound traffic restricted to prevent exfiltration?
- `network-architecture.internal-traffic-protection` — How is internal/east-west traffic authenticated and encrypted (mTLS, service mesh, zero-trust) rather than implicitly trusted?
- `network-architecture.remote-access` — How is administrative and remote network access provided (VPN, bastion/jump hosts, private endpoints) and protected?
- `network-architecture.segmentation` — How is the network segmented into zones/tiers, and what trust boundaries separate public, internal, and sensitive segments?

## 18. Cryptography
- `cryptography.algorithm-selection` — Are approved, standard algorithms and primitives used (no home-grown crypto, no deprecated algorithms) with proper randomness sources?
- `cryptography.data-at-rest` — How is data encrypted at rest (databases, storage, backups) and what algorithms and key strengths are used?
- `cryptography.data-in-transit` — How is data protected in transit (TLS versions, cipher suites, certificate validation, mTLS) across all channels?
- `cryptography.integrity-signing` — How are integrity, authenticity, and non-repudiation provided (signing, MACs, hashing of credentials) where required?
- `cryptography.key-management` — How are cryptographic keys generated, stored (KMS/HSM), rotated, and destroyed, and who can access them?

## 19. Secrets management
- `secrets-management.access-control` — How is access to secrets authorized, scoped to least privilege, and audited (who/what can read each secret)?
- `secrets-management.distribution-injection` — How are secrets distributed to and injected into workloads at runtime without exposure in logs, images, or process listings?
- `secrets-management.rotation-revocation` — How are secrets rotated and revoked, including on compromise, and are short-lived/dynamic credentials used where possible?
- `secrets-management.storage` — Where and how are secrets stored (vault/secret manager vs. code, config, env vars) and are any secrets hardcoded or in version control?

## 20. Application security controls
- `application-security-controls.business-logic-abuse` — What controls protect business logic and workflows from abuse (rate limiting, anti-automation, state/transaction integrity)?
- `application-security-controls.error-handling-logging` — How do error handling and application logging avoid leaking sensitive data while capturing security-relevant events?
- `application-security-controls.file-handling` — How are file uploads/downloads and SSRF-prone operations validated, sandboxed, and constrained?
- `application-security-controls.input-validation` — How is untrusted input validated and sanitized, and how are injection classes (SQL, command, template, deserialization) prevented?
- `application-security-controls.output-encoding` — How is output encoding/escaping applied to prevent XSS and content-type confusion across rendering contexts?
- `application-security-controls.security-headers` — What security headers and browser protections are set (CSP, HSTS, frame options, cookie flags) and CSRF defenses applied?

## 21. API security
- `api-security.authentication` — How are API clients authenticated (keys, OAuth2/OIDC, mTLS) and how are tokens scoped and validated per request?  _(tier 2 — when `has_api`)_
- `api-security.inventory-versioning` — Is there a complete API inventory covering versioning, deprecated/shadow/undocumented endpoints, and documentation accuracy?  _(tier 2 — when `has_api`)_
- `api-security.object-level-authz` — How is broken object-level authorization (BOLA/IDOR) and object-property-level authorization prevented at API endpoints?  _(tier 2 — when `has_api`)_
- `api-security.rate-limiting-quotas` — How are rate limiting, throttling, quotas, and resource-consumption limits enforced to prevent abuse and DoS?  _(tier 2 — when `has_api`)_
- `api-security.schema-input-validation` — How are API request/response schemas validated and mass-assignment, excessive data exposure, and parameter tampering prevented?  _(tier 2 — when `has_api`)_

## 22. Client-side security
- `client-side-security.dependency-supply-chain` — How are client-side dependencies, third-party scripts, and SDKs controlled (SRI, CSP, vetted libraries) against supply-chain tampering?  _(tier 2 — when `has_client`)_
- `client-side-security.local-data-storage` — How is sensitive data stored and protected on the client (local/secure storage, cache, tokens) and cleared appropriately?  _(tier 2 — when `has_client`)_
- `client-side-security.platform-hardening` — What platform hardening is applied for the client type (mobile: jailbreak/root detection, cert pinning; web: anti-clickjacking, DOM XSS defenses)?  _(tier 2 — when `has_client`)_
- `client-side-security.untrusted-environment` — How does the design account for the client being an untrusted environment, ensuring no security decisions rely solely on the client?  _(tier 2 — when `has_client`)_

## 23. Cloud and infrastructure security
- `cloud-infrastructure-security.account-tenancy-isolation` — How are accounts/projects/VPCs structured to isolate environments and blast radius, including network and identity boundaries?  _(tier 2 — when `has_cloud`)_
- `cloud-infrastructure-security.configuration-baseline` — How are secure configuration baselines, drift detection, and IaC security scanning enforced across accounts/subscriptions?  _(tier 2 — when `has_cloud`)_
- `cloud-infrastructure-security.iam-config` — How are cloud IAM roles, policies, and trust relationships scoped to least privilege, and how is privilege escalation/over-permissioning prevented?  _(tier 2 — when `has_cloud`)_
- `cloud-infrastructure-security.logging-monitoring` — How is cloud control-plane and data-plane activity logged, monitored, and protected from tampering (audit logs, threat detection)?  _(tier 2 — when `has_cloud`)_
- `cloud-infrastructure-security.resource-exposure` — How are cloud resources protected from public exposure (storage buckets, databases, management interfaces, metadata service)?  _(tier 2 — when `has_cloud`)_

## 24. Container and Kubernetes security
- `container-kubernetes-security.cluster-rbac-api` — How is the Kubernetes API server secured (RBAC, authentication, admission control) and least privilege enforced for service accounts?  _(tier 2 — when `has_containers`)_
- `container-kubernetes-security.image-supply-chain` — How are container images sourced, scanned, signed, and verified, and how is base-image/registry trust maintained?  _(tier 2 — when `has_containers`)_
- `container-kubernetes-security.runtime-hardening` — How are containers hardened at runtime (non-root, read-only FS, dropped capabilities, seccomp/AppArmor, no privileged mode)?  _(tier 2 — when `has_containers`)_
- `container-kubernetes-security.secrets-config` — How are secrets and configuration handled in the orchestrator (encrypted etcd, external secret stores, no secrets in manifests)?  _(tier 2 — when `has_containers`)_
- `container-kubernetes-security.workload-isolation` — How are workloads isolated (network policies, namespaces, pod security standards) to limit lateral movement and node escape?  _(tier 2 — when `has_containers`)_

## 25. CI/CD and supply-chain security
- `cicd-supply-chain-security.artifact-registry-integrity` — How are artifact repositories/registries secured and is artifact integrity verified between build, storage, and deploy stages?  _(tier 2 — when `has_cicd`)_
- `cicd-supply-chain-security.build-integrity` — How is build integrity and provenance ensured (isolated/ephemeral builders, reproducibility, SLSA-style attestation, artifact signing)?  _(tier 2 — when `has_cicd`)_
- `cicd-supply-chain-security.dependency-management` — How are software dependencies vetted, pinned, and scanned (SCA, lockfiles, SBOM) against known vulns and malicious/typosquatted packages?  _(tier 2 — when `has_cicd`)_
- `cicd-supply-chain-security.deployment-controls` — What controls gate deployment to production (approvals, branch protection, code review, signed commits/artifacts verification)?  _(tier 2 — when `has_cicd`)_
- `cicd-supply-chain-security.pipeline-access` — How is access to CI/CD systems, pipeline definitions, and runners controlled, and how are pipeline credentials scoped and protected?  _(tier 2 — when `has_cicd`)_

## 26. Third-party and vendor risk
- `third-party-vendor-risk.assessment-due-diligence` — How are vendors security-assessed before and during use (due diligence, certifications, contractual security/privacy obligations)?  _(tier 2 — when `has_third_party`)_
- `third-party-vendor-risk.integration-access-scope` — How is vendor integration access scoped and isolated (least privilege, dedicated credentials, network restrictions) to limit blast radius?  _(tier 2 — when `has_third_party`)_
- `third-party-vendor-risk.inventory-data-sharing` — What third parties/vendors are in use, what data and access does each receive, and is there a current inventory of these relationships?  _(tier 2 — when `has_third_party`)_
- `third-party-vendor-risk.ongoing-monitoring-offboarding` — How are vendor incidents, breaches, and SLA/security posture monitored over time, and how is secure offboarding/access revocation handled?  _(tier 2 — when `has_third_party`)_

## 27. Multi-tenancy
- `multi-tenancy.data-segregation` — How is tenant data segregated and how is every data access scoped by tenant to prevent cross-tenant leakage?  _(tier 2 — when `multi_tenant`)_
- `multi-tenancy.isolation-model` — What is the tenant isolation model (silo, pool, bridge) across compute, storage, and network, and where are shared resources?  _(tier 2 — when `multi_tenant`)_
- `multi-tenancy.noisy-neighbor-resource-limits` — How are per-tenant resource limits and quotas enforced to prevent noisy-neighbor and cross-tenant denial-of-service?  _(tier 2 — when `multi_tenant`)_
- `multi-tenancy.tenant-context-enforcement` — How is tenant context derived and enforced on every request, and how is tenant-ID spoofing or confused-deputy access prevented?  _(tier 2 — when `multi_tenant`)_

## 28. Admin, support, and operator access
- `admin-support-operator-access.admin-interface-surface` — How are admin/support interfaces and tooling exposed and hardened (network restriction, separate auth, no public exposure) and their attack surface managed?
- `admin-support-operator-access.auditing-accountability` — How are all admin/support/operator actions logged with individual accountability, and are logs tamper-resistant and reviewed?
- `admin-support-operator-access.privileged-access-control` — How is privileged administrative/operator access granted, scoped to least privilege, and protected (strong MFA, just-in-time elevation)?
- `admin-support-operator-access.separation-of-duties` — How are separation of duties and break-glass procedures enforced so no single operator can act unchecked on critical operations?
- `admin-support-operator-access.support-customer-data-access` — How can support staff access customer data/accounts (impersonation, debug tools), and what consent, scoping, and time-bounding controls apply?

## 29. Logging, monitoring, and detection
- `logging-monitoring.centralization-retention` — Are logs centralized/aggregated, time-synchronized, and retained for a defined period sufficient for detection and investigation?
- `logging-monitoring.detection-alerting` — What detection rules/alerts exist for suspicious activity, and how are alerts triaged and escalated?
- `logging-monitoring.incident-response-linkage` — How does monitoring feed incident response (runbooks, on-call, metrics for detection coverage/MTTD)?
- `logging-monitoring.log-integrity-protection` — How are logs protected from tampering and unauthorized access (append-only/WORM, access controls, integrity verification)?
- `logging-monitoring.security-event-coverage` — Which security-relevant events (authn, authz failures, privilege changes, config changes, data access) are logged, and is coverage complete across components?
- `logging-monitoring.sensitive-data-in-logs` — Are secrets, credentials, and sensitive/PII data prevented from being written to logs (redaction/masking)?

## 30. Auditability and non-repudiation
- `auditability-nonrepudiation.actor-attribution` — How is each action reliably attributed to an authenticated identity, including delegated/service/impersonated actions?
- `auditability-nonrepudiation.audit-access-review` — Who can read or modify audit records, and is access to the audit trail itself audited and reviewed?
- `auditability-nonrepudiation.audit-trail-coverage` — What actions produce an audit trail capturing who did what, when, from where, and to which resource?
- `auditability-nonrepudiation.non-repudiation-guarantees` — For high-value or legally significant actions, what non-repudiation guarantees exist (signed receipts, cryptographic proof of origin)?
- `auditability-nonrepudiation.tamper-evidence` — What mechanisms make audit records tamper-evident or tamper-proof (signing, hash chaining, immutable storage)?

## 31. Availability and resilience
- `availability-resilience.backup-recovery-objectives` — What are the backup, restore, RTO/RPO objectives, and how are recovery procedures tested?
- `availability-resilience.graceful-degradation` — How does the system degrade gracefully (circuit breakers, timeouts, fail-safe defaults) when dependencies fail?
- `availability-resilience.rate-limiting-load-shedding` — What rate limiting, quotas, throttling, and load-shedding protect the system under overload or abuse?
- `availability-resilience.redundancy-failover` — What redundancy and failover exist across components/zones/regions, and what are the failure domains and single points of failure?
- `availability-resilience.threats-to-availability` — What threats to availability are in scope (DoS/DDoS, resource exhaustion, dependency failure, data corruption) and how are they mitigated?

## 32. Privacy
- `privacy.anonymization-sharing` — How is personal data anonymized/pseudonymized, and what controls govern third-party sharing and cross-border transfer?  _(tier 2 — when `has_personal_data`)_
- `privacy.data-inventory-classification` — What personal data is collected, where does it flow/reside, and how is it classified by sensitivity?  _(tier 2 — when `has_personal_data`)_
- `privacy.data-subject-rights` — How are data subject rights (access, correction, portability, objection) supported and identity-verified?  _(tier 2 — when `has_personal_data`)_
- `privacy.purpose-minimization-consent` — Is data collection limited to a stated purpose with a lawful basis/consent, and is data minimization enforced?  _(tier 2 — when `has_personal_data`)_
- `privacy.retention-deletion` — What are the retention limits, and how are deletion and right-to-erasure requests fulfilled across all stores and backups?  _(tier 2 — when `has_personal_data`)_

## 33. Compliance and governance
- `compliance-governance.applicable-frameworks` — Which regulatory, legal, and contractual frameworks (e.g. GDPR, HIPAA, PCI-DSS, SOC 2) apply to the system, and what is in scope?  _(tier 2 — when `has_regulatory`)_
- `compliance-governance.control-mapping` — How are required controls mapped to system features, and how is compliance evidenced and audited?  _(tier 2 — when `has_regulatory`)_
- `compliance-governance.policy-ownership` — Who owns security/privacy policy, risk acceptance, and exception approval, and how is governance enforced?  _(tier 2 — when `has_regulatory`)_
- `compliance-governance.regulatory-reporting` — What breach-notification and regulatory-reporting obligations apply, and what triggers/timelines/processes meet them?  _(tier 2 — when `has_regulatory`)_

## 34. Threat enumeration
- `threat-enumeration.completeness-review` — How is enumeration completeness checked, and how is it kept current as the system and threat landscape change?
- `threat-enumeration.methodology` — What methodology (STRIDE, attack trees, kill chain, etc.) is used to systematically enumerate threats per component and trust boundary?
- `threat-enumeration.per-boundary-threats` — For each trust boundary and data flow, what specific threats (spoofing, tampering, disclosure, DoS, EoP) have been identified?
- `threat-enumeration.threat-actors` — Which threat actors (external attacker, malicious insider, compromised dependency, etc.) and their capabilities/motivations are considered?
- `threat-enumeration.threat-metadata` — Is each enumerated threat recorded with affected asset, attack vector, impact, and status (mitigated/accepted/open)?

## 35. Abuse cases and misuse cases
- `abuse-misuse-cases.abuse-case-catalog` — What abuse/misuse cases describe how an attacker subverts intended functionality or business logic?
- `abuse-misuse-cases.abuse-to-control-mapping` — Is each abuse/misuse case linked to detective and preventive controls and acceptance criteria for handling it?
- `abuse-misuse-cases.business-logic-abuse` — How could legitimate features be abused at scale (fraud, scraping, account takeover, spam, resource abuse) and what limits this?
- `abuse-misuse-cases.misuse-by-authorized-users` — How could authorized users or insiders misuse their legitimate access, and what controls detect/prevent it?

## 36. Security controls
- `security-controls.control-effectiveness-ownership` — Who owns each control, how is its effectiveness measured/tested, and how are gaps tracked to remediation?
- `security-controls.control-inventory` — What security controls exist, classified as preventive, detective, and corrective, and where do they sit in the architecture?
- `security-controls.defense-in-depth` — Are controls layered (defense in depth) with no critical reliance on a single control, and are fail-safe defaults used?
- `security-controls.threat-to-control-traceability` — Does each control trace to one or more threats it mitigates, and does each threat have at least one control or explicit acceptance?

## 37. Risk assessment
- `risk-assessment.likelihood-impact-rating` — Is each threat rated for likelihood and impact with documented rationale, and inherent vs residual risk distinguished?
- `risk-assessment.prioritization-treatment` — How are risks prioritized and treated (mitigate, transfer, avoid, accept), and how is remediation tracked?
- `risk-assessment.risk-acceptance-ownership` — Who has authority to accept residual risk, and are accepted risks documented with justification and review dates?
- `risk-assessment.scoring-methodology` — What methodology scores risk (e.g. likelihood x impact, CVSS, DREAD) and how are levels defined consistently?

## 38. Attack paths
- `attack-paths.choke-points-controls` — Where are the choke points/controls that break each attack path, and which paths remain unbroken?
- `attack-paths.crown-jewel-exposure` — What is the shortest/most-likely path to the system's crown-jewel assets, and how is that exposure reduced?
- `attack-paths.end-to-end-chains` — What end-to-end attack paths chain individual threats from entry point to high-value asset or impact?
- `attack-paths.lateral-movement-escalation` — How could an attacker move laterally or escalate privilege across trust boundaries once an initial foothold is gained?

## 39. Security invariants
- `security-invariants.enforcement-mechanism` — How is each invariant enforced and where (code, schema, infra, policy), rather than relying on convention?
- `security-invariants.stated-invariants` — What security invariants must always hold (e.g. tenant isolation, no plaintext secrets at rest, authz on every access)?
- `security-invariants.verification-tests` — How is each invariant continuously verified (tests, assertions, monitoring) and what happens on violation?

## 40. Assumptions and dependencies
- `assumptions-dependencies.assumption-failure-impact` — What is the security impact if a key assumption or dependency fails or is compromised, and how is that detected?
- `assumptions-dependencies.external-dependencies` — What external dependencies (services, libraries, infra, identity providers) is security inherited from, and what is their trust level?
- `assumptions-dependencies.trust-assumptions` — What security assumptions does the model rely on (trusted networks, trusted callers, platform guarantees) and are they valid?

## 41. Known limitations and gaps
- `known-limitations-gaps.remediation-roadmap` — For each known gap, what is the planned remediation, owner, target date, or documented acceptance?
- `known-limitations-gaps.scope-exclusions` — What is explicitly out of scope for this threat model, and why, so reviewers know the boundaries of coverage?
- `known-limitations-gaps.unmitigated-threats` — What known threats or weaknesses are currently unmitigated or only partially mitigated?

## 42. Validation and evidence
- `validation-evidence.control-verification-artifacts` — What artifacts demonstrate that key controls and invariants actually work as claimed (results, logs, attestations)?
- `validation-evidence.open-followup-tracking` — How are validation findings, open items, and follow-up actions tracked to closure?
- `validation-evidence.review-coverage` — Who reviewed/validated the threat model, when, and how is it kept current with system changes?
- `validation-evidence.testing-evidence` — What testing evidence (pentest, SAST/DAST, fuzzing, red team) backs the claimed mitigations and their effectiveness?

## 43. Mitigation plan
- `mitigation-plan.compensating-controls` — Where a primary control cannot be implemented, what compensating controls are in place and are they documented?
- `mitigation-plan.control-mapping` — Is each identified threat mapped to one or more specific mitigating controls (preventive, detective, or corrective)?
- `mitigation-plan.control-status` — What is the implementation status of each control (planned, in-progress, implemented, verified)?
- `mitigation-plan.ownership-and-deadline` — Who owns each mitigation and what is its target remediation date or priority?
- `mitigation-plan.residual-risk` — What is the residual risk after the mitigation is applied, and has it been explicitly accepted, transferred, or deferred?
- `mitigation-plan.verification-method` — How is each mitigation verified to be effective (test, scan, review, monitoring) rather than merely assumed?

## 44. Incident response readiness
- `incident-response.breach-notification` — Are breach-notification obligations and communication procedures (legal, customer, regulator) identified for this system?
- `incident-response.containment-and-recovery` — What containment, eradication, and recovery capabilities exist (isolation, key/credential rotation, restore from backup)?
- `incident-response.detection-and-alerting` — What detection and alerting exists to surface a security incident affecting this system, and who receives the alerts?
- `incident-response.forensic-readiness` — Are logs, audit trails, and evidence retained with sufficient fidelity and duration to support investigation and forensics?
- `incident-response.roles-and-escalation` — Are incident roles, on-call ownership, and escalation paths defined for this system?
- `incident-response.runbooks-and-playbooks` — Are there documented runbooks/playbooks for the most likely incident scenarios for this system?

## 45. Operational security
- `operational-security.access-and-privileged-ops` — How is operational/administrative access granted, scoped (least privilege), reviewed, and audited?
- `operational-security.backup-and-recovery` — Are backups taken, encrypted, access-controlled, and periodically restore-tested to a known RPO/RTO?
- `operational-security.change-management` — What change-management and configuration-drift controls govern production changes (review, approval, rollback)?
- `operational-security.logging-and-monitoring` — What security-relevant events are logged, where are logs centralized, and how is log integrity protected?
- `operational-security.patch-management` — How are OS, runtime, and dependency patches tracked and applied, and what is the SLA for critical vulnerabilities?
- `operational-security.secrets-rotation` — How are operational secrets and keys stored, rotated, and revoked over the system's lifecycle?

## 46. AI/ML-specific items
- `ai-ml.adversarial-robustness` — How is the model assessed for adversarial examples, evasion, model extraction, and abuse (excessive cost/agency)?  _(tier 2 — when `has_ai_ml`)_
- `ai-ml.data-leakage-and-privacy` — What controls prevent leakage of sensitive/training data via model responses, embeddings, or memorization?  _(tier 2 — when `has_ai_ml`)_
- `ai-ml.model-supply-chain` — What is the provenance and integrity of pretrained models, weights, and ML dependencies (model supply chain)?  _(tier 2 — when `has_ai_ml`)_
- `ai-ml.output-handling-and-guardrails` — How are model outputs validated, filtered, and constrained before being trusted, displayed, or used to trigger actions?  _(tier 2 — when `has_ai_ml`)_
- `ai-ml.prompt-injection` — How is the system protected against prompt injection and untrusted content reaching the model as instructions?  _(tier 2 — when `has_ai_ml`)_
- `ai-ml.training-data-integrity` — What is the provenance, integrity, and poisoning exposure of training/fine-tuning data?  _(tier 2 — when `has_ai_ml`)_

## 47. Physical and hardware context
- `physical-hardware.device-tampering` — What tamper-resistance/tamper-evidence and theft/loss protections exist for hardware components?  _(tier 2 — when `has_hardware`)_
- `physical-hardware.environmental-and-supply-chain` — What environmental and hardware-supply-chain risks (counterfeit parts, untrusted manufacturing, disposal/decommission) are considered?  _(tier 2 — when `has_hardware`)_
- `physical-hardware.peripheral-and-side-channel` — What is the exposure to peripheral/debug interfaces (JTAG, USB), removable media, and side-channel attacks?  _(tier 2 — when `has_hardware`)_
- `physical-hardware.physical-access` — What physical access controls protect devices, facilities, and ports, and what is the threat from physical access?  _(tier 2 — when `has_hardware`)_
- `physical-hardware.secure-boot-and-firmware` — Are secure boot, firmware integrity, and trusted hardware roots of trust (TPM/HSM/secure element) in place?  _(tier 2 — when `has_hardware`)_

## 48. Diagram legend and notation
- `diagram-legend.annotations-and-protocols` — Are flow annotations (protocol, direction, authentication, encryption) and their meanings defined in the legend?
- `diagram-legend.consistency-and-keying` — Are diagram elements consistently labeled/keyed so they map unambiguously to the component, flow, and threat inventories?
- `diagram-legend.element-shapes` — Does the diagram define the notation/shapes for the core element types (process, data store, external entity, data flow)?
- `diagram-legend.trust-boundary-notation` — Is the notation for trust boundaries (and how crossings are marked) explicitly defined in the legend?

## 49. Minimum metadata per component
- `metadata-component.identity-and-type` — Does each component have a unique identifier, name, and type (process, data store, external entity)?
- `metadata-component.owner-and-tech` — Does each component record its owner and its technology/runtime stack?
- `metadata-component.trust-level-and-data` — Does each component record its trust level/privilege and the data classification it handles?

## 50. Minimum metadata per data flow
- `metadata-dataflow.authn-and-encryption` — Does each data flow record its authentication mechanism and encryption (in-transit) status?
- `metadata-dataflow.endpoints-and-direction` — Does each data flow record its source, destination, and direction?
- `metadata-dataflow.protocol-and-data` — Does each data flow record the protocol used and the classification/sensitivity of data carried?

## 51. Minimum metadata per trust boundary
- `metadata-trust-boundary.controls` — Does each trust boundary record the controls enforced at the crossing (authentication, authorization, validation, filtering)?
- `metadata-trust-boundary.crossings` — Does each trust boundary enumerate the flows/components that cross it?
- `metadata-trust-boundary.identity-and-scope` — Does each trust boundary have an identifier and a clear description of the privilege/trust transition it represents?

## 52. Minimum metadata per threat
- `metadata-threat.category-and-rating` — Does each threat record its category (e.g. STRIDE) and a risk rating (likelihood/impact)?
- `metadata-threat.identity-and-description` — Does each threat have a unique identifier, description, and the affected component/flow/boundary?
- `metadata-threat.mitigation-and-status` — Does each threat link to its mitigation(s) and record a status (open, mitigated, accepted)?
