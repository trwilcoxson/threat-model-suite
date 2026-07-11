# threat-model — reliability run: TerraGoat (AWS IaC)

A second target of a **deliberately different type** — Infrastructure-as-Code, not application
logic — run through the same harness with **zero code changes**: only a new `targets/terragoat.yaml`
(id + repo subpath). This is the "point it at lots of different kinds of things" test. Target:
[TerraGoat](https://github.com/bridgecrewio/terragoat) AWS module (S3, KMS, RDS, IAM, EKS, Lambda,
EC2, ELB, ES, Neptune). 3 runs, Claude Opus 4.8, no answer key.

## Verdict

**Reliable structure, stable on the CRITICAL cloud misconfigurations, real recall gaps found.** The
harness behaves the same on Terraform as on a web app: the deterministic contract held on every run,
the crown-jewel misconfigs are stable across runs, and an independent red team surfaced HIGH gaps —
all without a single line of harness change.

## Deterministic contract (per run) — held on every run

| Run | Structure | Consistency | Grounding | Coverage | Findings | Defects |
|---|---|---|---|---|---|---|
| 1 | pass | pass | 1.00 | 1.00 | 22 | 0 |
| 2 | pass | pass | 1.00 | 1.00 | 17 | 0 |
| 3 | pass | pass | 1.00 | 1.00 | 14 | 0 |

`severity == band(L×I)` held on every finding; every recon element (Terraform resources, providers,
state, modules) resolved in the real `.tf` files; every discovered surface was addressed.

## Stability (LLM-matched)

**8 of 15 distinct high-severity issues in all 3 runs; overlap 0.665.** All six CRITICAL cloud
misconfigurations are stable every run: hardcoded AWS access keys, publicly accessible + unencrypted
RDS, security group opening SSH/HTTP to `0.0.0.0/0`, Elasticsearch `es:*` to any principal,
wildcard IAM, and a public unencrypted S3 bucket holding `customer-master.xlsx`. The tail (EBS/Neptune
encryption, public-subnet auto-IP, static IAM keys, lateral-movement framing) varies run to run —
the expected breadth variance, not a crown-jewel miss.

> **Honest negative:** the "public unencrypted S3 bucket" item above is stable but **over-scoped**. The harness's own quality judge flagged it (`agents/quality.json`, TM-007) as indefensible at CRITICAL — `aws_s3_bucket.data` (s3.tf:1-21) sets no ACL and no public-access resource, so the bucket is private by AWS default; the L5/I5 "unauthenticated internet users download `customer-master.xlsx`, no exploitation required" path rests only on a `# bucket is public` source comment the report elsewhere treats as untrusted data. The defensible finding is missing encryption/logging/versioning, not internet-public exposure. Its clustering every run is the harness catching a **stable over-claim**, not confirming it — which is why mean soundness is 0.85, not 1.0.

## Reasoning quality (judged)

Mean soundness **0.85** (proportionate; findings traced to real `.tf` resources, no invented
infrastructure).

## Adversarial recall (no answer key)

3 confirmed HIGH gaps, generated from the target: production RDS holding employee PII with **no
backups / no deletion protection**; sensitive S3 buckets with **no versioning + `force_destroy=true`**
(destructive-loss exposure); an unencrypted/unversioned **VPC flow-log sink bucket**. Different class
of gaps than NodeGoat's — availability/data-durability and logging-integrity, appropriate to IaC.

## Recon completeness

**0 missed subsystems** — recon enumerated the full Terraform surface, so the coverage denominator is
trustworthy here.

## Why this matters

NodeGoat and TerraGoat are different kinds of systems (runtime web app vs declarative cloud infra),
yet the same harness produced a coherent reliability profile on both with no per-target tuning. That
is the dynamic, reference-free property: add a `targets/*.yaml`, point, run.
