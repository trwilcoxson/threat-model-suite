# Code Security Specialist -- Code Security Review

## Metadata
| Field | Value |
|-------|-------|
| Agent | code-security-specialist |
| Date | 2026-02-18 |
| Target System | Amazon ECS Fullstack App (Terraform Demo) |
| Scope | Top 5 high-risk components from reconnaissance: IAM module, CodePipeline/CodeBuild pipeline, S3 module, Node.js server application, ALB module. Supporting files: ECR, ECS TaskDefinition, Dockerfiles, buildspec, SecurityGroup, Networking, DynamoDB modules |
| Methodology | CVSS v3.1, OWASP Top 10 (2021), OWASP API Security Top 10 (2023), CWE |
| Scoring System | CVSS v3.1 |

## Summary
- Total findings: 12 (3 critical, 4 high, 4 medium, 1 low)
- Top 3 risks: (1) `iam:PassRole` on `*` enables full privilege escalation from CI/CD and ECS task roles; (2) Repository-sourced buildspec with privileged Docker mode allows arbitrary code execution with DevOps IAM role; (3) GitHub OAuth token stored in plaintext Terraform state and CodePipeline configuration
- Key recommendation: Immediately scope `iam:PassRole` to specific role ARNs in both the DevOps and ECS task IAM policies

## Findings

### CRITICAL CR-001: iam:PassRole on Resource "*" Enables Full Privilege Escalation

| Field | Value |
|-------|-------|
| ID | CR-001 |
| Severity | CRITICAL |
| Confidence | HIGH |
| Affected Component(s) | IAM Module (DevOps Role Policy, ECS Task Role Policy) |
| Scoring System | CVSS v3.1 |
| Score | 9.9 (AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H) |
| Cross-Framework | CWE-269 (Improper Privilege Management) / OWASP A01:2021 (Broken Access Control) |

**Description**: The IAM policy document for the DevOps role grants `iam:PassRole` on resource `"*"` (line 288-293 of `IAM/main.tf`). This is compounded by the fact that the same DevOps role also has `ecs:RegisterTaskDefinition`, `ecs:RunTask`, and `ecs:StartTask` on resource `"*"` (lines 262-284). An attacker who compromises the DevOps role (via CodeBuild -- see CR-002) can register a new ECS task definition that passes *any* IAM role in the account (including admin roles) as the task role, then run that task to assume those privileges. The ECS task role (`role_policy_ecs_task_role`, lines 306-337) also has `iam:PassRole` on `"*"`, which is unnecessary for a backend application that only reads DynamoDB and S3.

**Evidence**:
```hcl
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Modules/IAM/main.tf
# Lines 287-293 (DevOps role policy)
  statement {
    sid    = "AllowIAMPassRole"
    effect = "Allow"
    actions = [
      "iam:PassRole"
    ]
    resources = ["*"]
  }

# Lines 317-323 (ECS task role policy)
  statement {
    sid    = "AllowIAMPassRole"
    effect = "Allow"
    actions = [
      "iam:PassRole"
    ]
    resources = ["*"]
  }

# Lines 262-284 (ECS actions on *)
  statement {
    sid    = "AllowCECSServiceActions"
    effect = "Allow"
    actions = [
      "ecs:RegisterTaskDefinition",
      "ecs:RunTask",
      "ecs:StartTask",
      # ... plus UpdateService, CreateTaskSet, etc.
    ]
    resources = ["*"]
  }
```

**Attack Scenario**:
1. Attacker gains access to the DevOps role (e.g., via compromised buildspec -- see CR-002, or compromised developer credentials)
2. Attacker calls `ecs:RegisterTaskDefinition` with `taskRoleArn` set to any high-privilege role ARN in the account (e.g., an admin role or the OrganizationsFullAccess role)
3. Attacker calls `ecs:RunTask` with the new task definition, which launches a container with the arbitrary role
4. Container's credentials (available via the task metadata endpoint at 169.254.170.2) grant full account takeover

**Existing Mitigations**: The ECS services run in private subnets with security groups limiting ingress. However, the CodeBuild environment can directly invoke these API calls, and a compromised ECS task can also invoke them via the task role.

**Recommendation**: Scope `iam:PassRole` to only the specific role ARNs that are legitimately needed. Remove `iam:PassRole` entirely from the ECS task role (it has no legitimate need to pass roles). For the DevOps role, restrict PassRole to the ECS execution and task role ARNs only:

```hcl
# DevOps role policy - restrict PassRole
  statement {
    sid    = "AllowIAMPassRole"
    effect = "Allow"
    actions = [
      "iam:PassRole"
    ]
    resources = [
      aws_iam_role.ecs_task_excecution_role[0].arn,
      aws_iam_role.ecs_task_role[0].arn,
    ]
    condition {
      test     = "StringEquals"
      variable = "iam:PassedToService"
      values   = ["ecs-tasks.amazonaws.com"]
    }
  }

# ECS task role policy - REMOVE the iam:PassRole statement entirely
```

Additionally, scope the ECS actions (`ecs:RegisterTaskDefinition`, `ecs:RunTask`, etc.) to the specific cluster ARN rather than `"*"`.

---

### CRITICAL CR-002: Repository-Sourced Buildspec with Privileged Mode Enables Arbitrary Code Execution

| Field | Value |
|-------|-------|
| ID | CR-002 |
| Severity | CRITICAL |
| Confidence | HIGH |
| Affected Component(s) | CodeBuild Module, CodePipeline Module |
| Scoring System | CVSS v3.1 |
| Score | 9.8 (AV:N/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H) |
| Cross-Framework | CWE-94 (Improper Control of Generation of Code) / OWASP A08:2021 (Software and Data Integrity Failures) |

**Description**: The CodeBuild project sources its buildspec from the repository (`var.buildspec_path` which defaults to `./Infrastructure/Templates/buildspec.yml`). Combined with `privileged_mode = true` (line 22 of `CodeBuild/main.tf`) and no pipeline approval gates, any developer with push access to the repository can modify the buildspec to execute arbitrary commands with the full permissions of the DevOps IAM role. The pipeline uses `PollForSourceChanges = true` (line 33 of `CodePipeline/main.tf`), meaning changes are automatically picked up without human review.

**Evidence**:
```hcl
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Modules/CodeBuild/main.tf
# Lines 18-23
  environment {
    compute_type    = "BUILD_GENERAL1_SMALL"
    image           = "aws/codebuild/standard:4.0"
    type            = "LINUX_CONTAINER"
    privileged_mode = true
    # ...
  }

# Lines 92-95
  source {
    type      = "CODEPIPELINE"
    buildspec = var.buildspec_path
  }
```

```hcl
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Modules/CodePipeline/main.tf
# Lines 28-34 (no approval stage between Source and Build)
      configuration = {
        OAuthToken           = var.github_token
        Owner                = var.repo_owner
        Repo                 = var.repo_name
        Branch               = var.branch
        PollForSourceChanges = true
      }
```

**Attack Scenario**:
1. A malicious insider or an attacker who compromises a developer's GitHub credentials pushes a modified `buildspec.yml` to the configured branch
2. CodePipeline automatically detects the change via polling and triggers a build
3. CodeBuild executes the modified buildspec with the DevOps IAM role, which has broad AWS permissions (S3, ECR, ECS, CodeDeploy, iam:PassRole on *, CloudWatch)
4. Attacker exfiltrates AWS credentials, modifies infrastructure, deploys backdoored containers, or escalates privileges (chaining with CR-001)

**Existing Mitigations**: None. There are no approval gates between the Source and Build stages, no branch protection enforced by the pipeline, and no restriction on buildspec modifications.

**Recommendation**:
1. Move the buildspec inline into the CodeBuild Terraform resource instead of sourcing it from the repository:
```hcl
  source {
    type      = "CODEPIPELINE"
    buildspec = file("${path.module}/../../Templates/buildspec.yml")
  }
```
2. Add a manual approval stage between Source and Build in the CodePipeline:
```hcl
  stage {
    name = "Approval"
    action {
      name     = "ManualApproval"
      category = "Approval"
      owner    = "AWS"
      provider = "Manual"
      version  = "1"
      configuration = {
        NotificationArn = var.sns_topic_arn
      }
    }
  }
```
3. Set `privileged_mode = false` unless Docker-in-Docker is strictly required (consider using Kaniko or ECR credential helper instead).
4. Enforce GitHub branch protection rules with required reviews on the configured branch.

---

### CRITICAL CR-003: GitHub OAuth Token Stored in Plaintext Terraform State

| Field | Value |
|-------|-------|
| ID | CR-003 |
| Severity | CRITICAL |
| Confidence | HIGH |
| Affected Component(s) | CodePipeline Module, Root Terraform Configuration |
| Scoring System | CVSS v3.1 |
| Score | 9.1 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N) |
| Cross-Framework | CWE-312 (Cleartext Storage of Sensitive Information) / OWASP A02:2021 (Cryptographic Failures) |

**Description**: The GitHub personal access token is passed as a Terraform variable (marked `sensitive = true`) and used directly in the CodePipeline GitHub source configuration. The `sensitive = true` flag only prevents the value from appearing in `terraform plan` output; it does NOT encrypt the value in the state file. Since the project has no remote backend configured (`versions.tf` contains no backend block), the state file is stored locally as `terraform.tfstate` in plaintext. Additionally, CodePipeline's GitHub v1 source action stores the OAuth token in the AWS API configuration, making it retrievable via `aws codepipeline get-pipeline`. The `ignore_changes` lifecycle rule on line 111 only prevents Terraform diffs, not token exposure.

**Evidence**:
```hcl
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/variables.tf
# Lines 24-28
variable "github_token" {
  description = "Personal access token from Github"
  type        = string
  sensitive   = true
}

# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/versions.tf
# Lines 4-11 -- NO backend block configured
terraform {
  required_version = ">= 0.13"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.38"
    }
  }
}

# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Modules/CodePipeline/main.tf
# Line 29
        OAuthToken           = var.github_token
```

**Attack Scenario**:
1. An attacker gains access to the deployer's workstation or a shared filesystem where Terraform was executed
2. Attacker reads `terraform.tfstate` which contains the GitHub OAuth token in plaintext
3. With the GitHub token, attacker can: push malicious code to the repository (triggering the pipeline -- chain with CR-002), access private repositories, modify branch protection settings, or create webhooks for persistent access
4. Alternatively, anyone with `codepipeline:GetPipeline` permissions can retrieve the token from the AWS API

**Existing Mitigations**: The `sensitive = true` flag suppresses the token in CLI plan output. The `ignore_changes` lifecycle rule prevents token-related Terraform diffs. Neither addresses the core storage issue.

**Recommendation**:
1. Migrate from GitHub v1 source (OAuth token) to AWS CodeStar Connections (v2), which uses AWS-managed OAuth and does not expose tokens:
```hcl
  stage {
    name = "Source"
    action {
      name             = "Source"
      category         = "Source"
      owner            = "AWS"
      provider         = "CodeStarSourceConnection"
      version          = "1"
      output_artifacts = ["SourceArtifact"]
      configuration = {
        ConnectionArn    = aws_codestarconnections_connection.github.arn
        FullRepositoryId = "${var.repo_owner}/${var.repo_name}"
        BranchName       = var.branch
      }
    }
  }
```
2. Configure a remote Terraform backend with encryption:
```hcl
terraform {
  backend "s3" {
    bucket         = "terraform-state-bucket"
    key            = "ecs-demo/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}
```
3. If v1 source must be used, store the token in AWS Secrets Manager and reference it dynamically.

---

### HIGH CR-004: All Traffic Served Over HTTP Without TLS

| Field | Value |
|-------|-------|
| ID | CR-004 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | ALB Module (Server ALB, Client ALB) |
| Scoring System | CVSS v3.1 |
| Score | 7.5 (AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N) |
| Cross-Framework | CWE-319 (Cleartext Transmission of Sensitive Information) / OWASP A02:2021 (Cryptographic Failures) |

**Description**: Both the server and client ALBs are configured with HTTP-only listeners (port 80). The HTTPS listener exists in the ALB module but is gated behind `enable_https` which defaults to `false` and is never set to `true` in the root `main.tf`. The HTTPS listener also has no `certificate_arn` parameter, so even if enabled it would fail. All user traffic, API responses, and inter-service communication between the frontend and backend traverse the public internet in plaintext. The client-side code explicitly hardcodes `http://` in the server URL template.

**Evidence**:
```hcl
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Modules/ALB/variables.tf
# Lines 27-31
variable "enable_https" {
  description = "Set to true to create a HTTPS listener"
  type        = bool
  default     = false
}

# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Modules/ALB/main.tf
# Lines 38-53 (HTTP listener -- always created)
resource "aws_alb_listener" "http_listener" {
  count             = var.create_alb == true ? 1 : 0
  load_balancer_arn = aws_alb.alb[0].id
  port              = "80"
  protocol          = "HTTP"
  default_action {
    target_group_arn = var.target_group
    type             = "forward"
  }
}

# HTTPS listener (lines 20-35) -- never created because enable_https is never set to true
```

```javascript
// File: /Users/dev/amazon-ecs-fullstack-app-terraform/Code/client/src/services/RestServices.js
// Line 6
let serverUrl = "http://<SERVER_ALB_URL>"
```

**Attack Scenario**:
1. A user browses to the application over a public/shared network (coffee shop, corporate guest WiFi, compromised ISP)
2. An attacker in a network position intercepts the HTTP traffic between the user's browser and the client ALB
3. Attacker reads all API responses (product data), injects malicious JavaScript into the HTML/JS responses (achieving persistent client-side compromise), or redirects the user to a phishing page
4. The client-to-server ALB communication (frontend fetching from backend API) is also HTTP, enabling the same attacks on the inter-service data flow

**Existing Mitigations**: None. The ALB module has scaffolding for HTTPS but it is not enabled, not configured with a certificate, and the HTTP listener has no redirect-to-HTTPS action.

**Recommendation**:
1. Provision an ACM certificate and enable HTTPS:
```hcl
resource "aws_acm_certificate" "cert" {
  domain_name       = var.domain_name
  validation_method = "DNS"
}

module "alb_server" {
  source         = "./Modules/ALB"
  create_alb     = true
  enable_https   = true
  certificate_arn = aws_acm_certificate.cert.arn
  # ...
}
```
2. Add a `certificate_arn` variable to the ALB module and attach it to the HTTPS listener.
3. Change the HTTP listener to redirect to HTTPS:
```hcl
resource "aws_alb_listener" "http_listener" {
  # ...
  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}
```
4. Update `RestServices.js` to use `https://` in the server URL template.

---

### HIGH CR-005: S3 Buckets Missing Encryption, Public Access Block, and Versioning

| Field | Value |
|-------|-------|
| ID | CR-005 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | S3 Module (CodePipeline Artifacts Bucket, Assets Bucket) |
| Scoring System | CVSS v3.1 |
| Score | 7.1 (AV:N/AC:H/PR:L/UI:N/S:U/C:H/I:H/A:N) |
| Cross-Framework | CWE-311 (Missing Encryption of Sensitive Data) / CWE-732 (Incorrect Permission Assignment for Critical Resource) / OWASP A05:2021 (Security Misconfiguration) |

**Description**: The S3 module creates buckets with minimal security configuration. It uses the deprecated `acl = "private"` parameter (which is being replaced by S3 ownership controls and public access blocks as of April 2023), has no `aws_s3_bucket_public_access_block` to prevent accidental public exposure, no explicit server-side encryption configuration, no bucket versioning, and `force_destroy = true` which allows irrecoverable deletion of all objects. The CodePipeline artifacts bucket stores build artifacts and the assets bucket stores application data, both of which should be protected.

**Evidence**:
```hcl
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Modules/S3/main.tf
# Lines 8-14 -- entire S3 module
resource "aws_s3_bucket" "s3_bucket" {
  bucket        = var.bucket_name
  acl           = "private"
  force_destroy = true
  tags = {
    Name = var.bucket_name
  }
}
```

Missing resources that should be present:
- `aws_s3_bucket_public_access_block`
- `aws_s3_bucket_server_side_encryption_configuration`
- `aws_s3_bucket_versioning`
- `aws_s3_bucket_lifecycle_configuration`

**Attack Scenario**:
1. A misconfigured IAM policy or bucket policy inadvertently grants public access to the CodePipeline artifacts bucket (no `aws_s3_bucket_public_access_block` to serve as a guardrail)
2. Attacker discovers the predictable bucket name (`codepipeline-{region}-{4-hex-chars}`) and accesses build artifacts containing source code, Docker images, and deployment configurations
3. Build artifacts may contain embedded environment variables (from buildspec `sed` replacements) including DynamoDB table names, IAM role names, and internal ALB DNS names
4. The `force_destroy = true` flag means a `terraform destroy` or a compromised deployer could permanently delete all pipeline artifacts with no recovery path

**Existing Mitigations**: Buckets have `acl = "private"` which sets a default private ACL, but this is a weak control that can be overridden by bucket policies or IAM policies. AWS defaults to SSE-S3 encryption for new objects since January 2023, providing a partial backstop.

**Recommendation**:
```hcl
resource "aws_s3_bucket" "s3_bucket" {
  bucket        = var.bucket_name
  force_destroy = false  # Prevent irrecoverable data loss
  tags = {
    Name = var.bucket_name
  }
}

resource "aws_s3_bucket_public_access_block" "s3_bucket" {
  bucket = aws_s3_bucket.s3_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "s3_bucket" {
  bucket = aws_s3_bucket.s3_bucket.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
    bucket_key_enabled = true
  }
}

resource "aws_s3_bucket_versioning" "s3_bucket" {
  bucket = aws_s3_bucket.s3_bucket.id
  versioning_configuration {
    status = "Enabled"
  }
}
```

---

### HIGH CR-006: ECR Repositories with Mutable Image Tags Enable Image Replacement Attacks

| Field | Value |
|-------|-------|
| ID | CR-006 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | ECR Module, CodeBuild Module |
| Scoring System | CVSS v3.1 |
| Score | 7.3 (AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N) |
| Cross-Framework | CWE-345 (Insufficient Verification of Data Authenticity) / OWASP A08:2021 (Software and Data Integrity Failures) |

**Description**: ECR repositories are created with `image_tag_mutability = "MUTABLE"` (line 10 of `ECR/main.tf`), and the CodeBuild project hardcodes the image tag to `"latest"` (line 42 of `CodeBuild/main.tf`). This combination means: (1) any principal with `ecr:PutImage` permission can overwrite the `latest` tag with a different image, and (2) the ECS task definitions reference the repository URL without a digest, so they will pull whatever image the `latest` tag currently points to. There is also no ECR image scanning configured, so pushed images are not checked for known vulnerabilities.

**Evidence**:
```hcl
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Modules/ECR/main.tf
# Lines 8-11
resource "aws_ecr_repository" "ecr_repository" {
  name                 = var.name
  image_tag_mutability = "MUTABLE"
}
```

```hcl
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Modules/CodeBuild/main.tf
# Lines 39-42
    environment_variable {
      name  = "IMAGE_TAG"
      value = "latest"
    }
```

```yaml
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Templates/buildspec.yml
# Line 33
      - docker push $REPO_URL:$IMAGE_TAG
```

**Attack Scenario**:
1. Attacker compromises a principal with ECR push permissions (the DevOps role, or chained from CR-001/CR-002)
2. Attacker builds a backdoored Docker image and pushes it to the ECR repository with the `latest` tag, overwriting the legitimate image
3. On the next ECS task launch (scale-out event, deployment, or task restart), the backdoored image is pulled and executed
4. The backdoored container runs with the ECS task role permissions (DynamoDB read, S3 read, iam:PassRole on *)

**Existing Mitigations**: None. No image scanning, no immutable tags, no image signing or verification.

**Recommendation**:
```hcl
resource "aws_ecr_repository" "ecr_repository" {
  name                 = var.name
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "KMS"
  }
}
```

Additionally, update the buildspec to use unique image tags (e.g., git commit SHA) instead of `latest`:
```yaml
    environment_variable {
      name  = "IMAGE_TAG"
      value = "latest"  # Change to use $CODEBUILD_RESOLVED_SOURCE_VERSION
    }
```

---

### HIGH CR-007: Unrestricted CORS Policy Allows Cross-Origin Data Theft

| Field | Value |
|-------|-------|
| ID | CR-007 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | Server Application (Node.js/Express) |
| Scoring System | CVSS v3.1 |
| Score | 7.5 (AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:H/A:N) |
| Cross-Framework | CWE-942 (Permissive Cross-domain Policy with Untrusted Domains) / OWASP A05:2021 (Security Misconfiguration) |

**Description**: The Express server uses `app.use(cors())` with no configuration options (line 10 of `app.js`). When `cors()` is called with no arguments, it sets `Access-Control-Allow-Origin: *`, which allows any website to make cross-origin requests to the API and read the responses. While the current API only serves product catalog data (low sensitivity), this pattern is dangerous because: (1) if the API is extended with authenticated or sensitive endpoints, the CORS policy will silently permit cross-origin access, and (2) any malicious website can enumerate the API surface via the Swagger endpoint.

**Evidence**:
```javascript
// File: /Users/dev/amazon-ecs-fullstack-app-terraform/Code/server/src/app.js
// Line 6 and 10
var cors = require('cors');
// ...
app.use(cors());
```

The `cors` npm package, when called with no arguments, responds to all requests with:
- `Access-Control-Allow-Origin: *`
- No `Access-Control-Allow-Credentials` header
- Allows all methods and headers in preflight

**Attack Scenario**:
1. User visits a malicious website while also having a tab open to the application
2. Malicious JavaScript on the attacker's site makes `fetch()` requests to the backend API at `http://{server-alb}/api/getAllProducts`
3. Due to `Access-Control-Allow-Origin: *`, the browser permits the malicious site to read the response
4. If the API is later extended with user-specific data or admin endpoints, the same CORS policy would expose that data to any origin

**Existing Mitigations**: None. The current API does not handle authentication tokens or cookies, which limits the immediate impact. However, this is still a security misconfiguration that will become critical as the application evolves.

**Recommendation**:
```javascript
// Replace app.use(cors()) with a restrictive CORS configuration
const corsOptions = {
  origin: process.env.ALLOWED_ORIGIN || 'https://your-frontend-domain.com',
  methods: ['GET'],
  allowedHeaders: ['Content-Type'],
  maxAge: 86400, // Cache preflight for 24h
};
app.use(cors(corsOptions));
```

---

### MEDIUM CR-008: Error Handler Exposes Internal Error Details and Contains a JavaScript Bug

| Field | Value |
|-------|-------|
| ID | CR-008 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | Server Application (Node.js/Express) |
| Scoring System | CVSS v3.1 |
| Score | 5.3 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:N/A:N) |
| Cross-Framework | CWE-209 (Generation of Error Message Containing Sensitive Information) / CWE-670 (Always-Incorrect Control Flow Implementation) / OWASP A04:2021 (Insecure Design) |

**Description**: The Express error handler (lines 78-88 of `app.js`) sends raw error messages (`err.message`) to clients, which can expose internal implementation details such as stack traces, file paths, or database error messages. Additionally, line 85 contains a JavaScript labeled statement bug: `status: err.status || 500` is parsed as a label statement (label `status` applied to the expression `err.status || 500`) rather than a property assignment. This means the HTTP status code fallback to 500 is never actually applied, and `res.status(error.code)` will use `undefined` (from `err.status` on line 73 which is `undefined` for non-HTTP errors), causing Express to default to 200 for unhandled errors.

**Evidence**:
```javascript
// File: /Users/dev/amazon-ecs-fullstack-app-terraform/Code/server/src/app.js
// Lines 78-88
app.use(function (err, req, res, next) {
    console.error(`Error catched! ${err}`)

    let error = {
        code: err.status,
        description: err.message    // Exposes internal error text to client
    }
    status: err.status || 500       // BUG: This is a label statement, not assignment

    res.status(error.code).send(error)  // error.code may be undefined
  })
```

The DynamoDB error handler (lines 55-59) also sends raw AWS SDK error messages to clients:
```javascript
    docClient.scan(params, function(err, data) {
      if (err) {
        res.send({
          code: err.status,
          description: err.message  // Raw AWS SDK error message
        });
      }
    });
```

**Attack Scenario**:
1. Attacker sends crafted requests that trigger errors (e.g., forcing DynamoDB scan failures by overwhelming the table)
2. Error responses contain AWS SDK error messages that reveal internal details: DynamoDB table name, region, error type, and potentially IAM permission details
3. Attacker uses this information to map internal architecture and tailor further attacks
4. The status code bug means some error responses are sent with status 200, potentially confusing monitoring systems and masking real errors

**Existing Mitigations**: CloudWatch logging captures the `console.error` output, providing an audit trail of errors. However, the error details are still sent to the client.

**Recommendation**:
```javascript
// Corrected error handler with generic messages
app.use(function (err, req, res, next) {
    console.error(`Error caught: ${err.stack || err}`);

    const statusCode = err.status || 500;
    const isProduction = process.env.NODE_ENV === 'production';

    res.status(statusCode).send({
        code: statusCode,
        description: isProduction ? 'An internal error occurred' : err.message
    });
});
```

For the DynamoDB handler:
```javascript
    docClient.scan(params, function(err, data) {
      if (err) {
        console.error('DynamoDB scan error:', err);
        res.status(500).send({
          code: 500,
          description: 'Failed to retrieve products'
        });
      }
    });
```

---

### MEDIUM CR-009: Docker Images Built from Unpinned Base Images with Root User

| Field | Value |
|-------|-------|
| ID | CR-009 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | Server Dockerfile, Client Dockerfile, ECS TaskDefinition Module |
| Scoring System | CVSS v3.1 |
| Score | 6.3 (AV:N/AC:H/PR:N/UI:N/S:U/C:L/I:H/A:L) |
| Cross-Framework | CWE-250 (Execution with Unnecessary Privileges) / CWE-829 (Inclusion of Functionality from Untrusted Control Sphere) / OWASP A06:2021 (Vulnerable and Outdated Components) |

**Description**: Both Dockerfiles use `:latest` tags for base images (server: `public.ecr.aws/bitnami/node:latest`, client production stage: `public.ecr.aws/nginx/nginx:latest`), use `npm install` instead of `npm ci` (which ignores the lockfile), and neither sets a non-root `USER` directive. The ECS task definitions also lack `readonlyRootFilesystem` and `user` fields in the container definitions. This combination means: (1) builds are not reproducible and are vulnerable to supply chain attacks via tag replacement on the public registry, (2) container processes run as root, increasing the impact of any container escape or application vulnerability, and (3) `npm install` may resolve to different dependency versions than what was tested.

**Evidence**:
```dockerfile
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Code/server/Dockerfile
# Line 4 -- unpinned base image
FROM public.ecr.aws/bitnami/node:latest
# Line 12 -- npm install instead of npm ci
RUN npm install
# No USER directive -- runs as root
```

```dockerfile
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Code/client/Dockerfile
# Line 5 -- partially pinned build stage
FROM public.ecr.aws/bitnami/node:16 as build-stage
# Line 8 -- npm install instead of npm ci
RUN npm install
# Line 13 -- unpinned production stage
FROM public.ecr.aws/nginx/nginx:latest as production-stage
# No USER directive -- runs as root
```

```hcl
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Modules/ECS/TaskDefinition/main.tf
# Lines 17-41 -- container definition lacks "user" and "readonlyRootFilesystem"
  container_definitions = <<DEFINITION
    [{
        "image": "${var.docker_repo}",
        "name": "${var.container_name}",
        # No "user": "1000:1000"
        # No "readonlyRootFilesystem": true
    }]
    DEFINITION
```

**Attack Scenario**:
1. An attacker compromises the `public.ecr.aws/bitnami/node` or `public.ecr.aws/nginx/nginx` public repository (supply chain attack)
2. The `latest` tag is updated to point to a backdoored image
3. The next CodeBuild execution pulls the compromised base image and builds the application on top of it
4. The backdoored container runs as root inside the Fargate task, with full filesystem write access and the ECS task role permissions

**Existing Mitigations**: Fargate provides hypervisor-level isolation, limiting the blast radius of a container escape. The containers run in private subnets with security groups restricting inbound access.

**Recommendation**:
```dockerfile
# Pin base images to digest
FROM public.ecr.aws/bitnami/node:20@sha256:<known-good-digest> AS build
WORKDIR /home/node/app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
USER node
EXPOSE 3001
CMD ["npm", "start"]
```

Add container hardening to the task definition:
```json
{
  "user": "1000:1000",
  "readonlyRootFilesystem": true,
  "linuxParameters": {
    "initProcessEnabled": true
  }
}
```

---

### MEDIUM CR-010: Outdated and Vulnerable Dependencies

| Field | Value |
|-------|-------|
| ID | CR-010 |
| Severity | MEDIUM |
| Confidence | MEDIUM |
| Affected Component(s) | Server package.json, Client package.json, Terraform AWS Provider |
| Scoring System | CVSS v3.1 |
| Score | 6.5 (AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:L) |
| Cross-Framework | CWE-1104 (Use of Unmaintained Third Party Components) / OWASP A06:2021 (Vulnerable and Outdated Components) |

**Description**: Multiple dependencies are significantly outdated and likely contain known vulnerabilities. The server uses Express 4.16.4 (released October 2018), aws-sdk v2 (end-of-life announced, v3 is current), and includes `artillery` (a load testing tool) as a production dependency. The client uses axios 0.21.2 which has known prototype pollution vulnerabilities in older versions, Vue.js 2.6.11 (Vue 2 reached end of life December 2023), and an unnecessary `aws-sdk` dependency for a static SPA. The Terraform AWS provider is pinned to `~> 3.38` while the current major version is 5.x, meaning security-related resources and features are unavailable.

**Evidence**:
```json
// File: /Users/dev/amazon-ecs-fullstack-app-terraform/Code/server/package.json
{
  "dependencies": {
    "artillery": "^1.6.2",       // Load testing tool in production deps
    "aws-sdk": "^2.876.0",      // v2 EOL, should use @aws-sdk/client-* v3
    "express": "^4.16.4",       // ~4 years old, multiple CVEs since
    "swagger-jsdoc": "6.0.0",
    "swagger-ui-express": "^4.1.6"
  }
}
```

```json
// File: /Users/dev/amazon-ecs-fullstack-app-terraform/Code/client/package.json
{
  "dependencies": {
    "aws-sdk": "^2.885.0",      // Unnecessary in a browser SPA
    "axios": "^0.21.2",         // Known CVEs in older 0.x versions
    "vue": "^2.6.11",           // Vue 2 EOL since Dec 2023
  }
}
```

```hcl
// File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/versions.tf
    aws = {
      source  = "hashicorp/aws"
      version = "~> 3.38"       // Current is 5.x, missing S3 ownership controls, etc.
    }
```

**Attack Scenario**:
1. Attacker identifies the application uses Express 4.16.x via the Swagger endpoint or HTTP headers
2. Attacker exploits known vulnerabilities in the outdated Express version (e.g., CVE-2022-24999 -- qs prototype pollution in Express < 4.17.3)
3. The `artillery` package in production dependencies inflates the Docker image attack surface with unnecessary binaries and sub-dependencies
4. The outdated Terraform AWS provider prevents using modern S3 security features (bucket ownership controls, default encryption enforcement), leaving infrastructure vulnerable

**Existing Mitigations**: None. No dependency scanning is configured in the CI/CD pipeline.

**Recommendation**:
1. Update server dependencies:
```json
{
  "dependencies": {
    "@aws-sdk/client-dynamodb": "^3.x",
    "@aws-sdk/lib-dynamodb": "^3.x",
    "cors": "^2.8.5",
    "express": "^4.21.0",
    "swagger-jsdoc": "^6.2.8",
    "swagger-ui-express": "^5.0.0"
  },
  "devDependencies": {
    "artillery": "^2.x"
  }
}
```
2. Remove `aws-sdk` from the client `package.json`.
3. Update the Terraform AWS provider to `~> 5.0`.
4. Add `npm audit` to the buildspec and fail the build on HIGH/CRITICAL findings.

---

### MEDIUM CR-011: ECS Task Role Has Unnecessary Permissions (s3:ListBucket on Default Wildcard)

| Field | Value |
|-------|-------|
| ID | CR-011 |
| Severity | MEDIUM |
| Confidence | MEDIUM |
| Affected Component(s) | IAM Module (ECS Task Role Policy) |
| Scoring System | CVSS v3.1 |
| Score | 5.4 (AV:N/AC:L/PR:L/UI:N/S:U/C:L/I:L/A:N) |
| Cross-Framework | CWE-732 (Incorrect Permission Assignment for Critical Resource) / OWASP A01:2021 (Broken Access Control) |

**Description**: The IAM module's variables define defaults of `["*"]` for several resource scopes including `s3_bucket_assets`, `dynamodb_table`, `ecr_repositories`, `code_build_projects`, and `code_deploy_resources`. While the root `main.tf` does pass the specific DynamoDB table ARN for the ECS role (line 135), it does NOT pass the `s3_bucket_assets` variable, meaning it defaults to `["*"]`. This grants the ECS task role `s3:GetObject` and `s3:ListBucket` on ALL S3 buckets in the account, rather than only the assets bucket.

**Evidence**:
```hcl
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Modules/IAM/variables.tf
# Lines 76-80
variable "s3_bucket_assets" {
  description = "The name of the S3 bucket to which grant IAM access"
  type        = list(string)
  default     = ["*"]    # Defaults to all S3 buckets
}
```

```hcl
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/main.tf
# Lines 130-136 -- s3_bucket_assets is NOT passed, falling to default ["*"]
module "ecs_role" {
  source             = "./Modules/IAM"
  create_ecs_role    = true
  name               = var.iam_role_name["ecs"]
  name_ecs_task_role = var.iam_role_name["ecs_task_role"]
  dynamodb_table     = [module.dynamodb_table.dynamodb_table_arn]
  # s3_bucket_assets is missing -- defaults to ["*"]
}
```

```hcl
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Modules/IAM/main.tf
# Lines 306-315
data "aws_iam_policy_document" "role_policy_ecs_task_role" {
  statement {
    sid    = "AllowS3Actions"
    effect = "Allow"
    actions = [
      "s3:GetObject",
      "s3:ListBucket"
    ]
    resources = var.s3_bucket_assets   # Resolves to ["*"]
  }
```

**Attack Scenario**:
1. An attacker gains code execution within the server ECS task (e.g., via a future injection vulnerability or dependency compromise)
2. Using the task role credentials from the metadata endpoint, the attacker calls `s3:ListBucket` and `s3:GetObject` on any S3 bucket in the account
3. This could expose sensitive data in other buckets such as the CodePipeline artifacts bucket (which may contain embedded configuration values), Terraform state buckets, log buckets, or any other S3-hosted data in the same AWS account

**Existing Mitigations**: The application code currently only accesses DynamoDB (not S3 directly -- S3 URLs are stored in DynamoDB and served to the client). The ECS tasks run in private subnets.

**Recommendation**:
Pass the specific S3 bucket ARN and objects to the ECS role module:
```hcl
module "ecs_role" {
  source             = "./Modules/IAM"
  create_ecs_role    = true
  name               = var.iam_role_name["ecs"]
  name_ecs_task_role = var.iam_role_name["ecs_task_role"]
  dynamodb_table     = [module.dynamodb_table.dynamodb_table_arn]
  s3_bucket_assets   = [
    module.s3_assets.s3_bucket_arn,
    "${module.s3_assets.s3_bucket_arn}/*"
  ]
}
```

---

### LOW CR-012: No VPC Flow Logs or Container Insights for Security Monitoring

| Field | Value |
|-------|-------|
| ID | CR-012 |
| Severity | LOW |
| Confidence | HIGH |
| Affected Component(s) | Networking Module, ECS Cluster Module |
| Scoring System | CVSS v3.1 |
| Score | 3.7 (AV:N/AC:H/PR:N/UI:N/S:U/C:N/I:N/A:L) |
| Cross-Framework | CWE-778 (Insufficient Logging) / OWASP A09:2021 (Security Logging and Monitoring Failures) |

**Description**: The VPC has no VPC Flow Logs configured, meaning there is no record of network traffic patterns, connection attempts, or data transfer volumes. The ECS cluster has no Container Insights enabled, so there is no enhanced monitoring of container-level metrics, performance data, or anomaly detection. While CloudWatch log groups exist for container stdout/stderr, network-level visibility is absent. This makes incident detection, forensic investigation, and compliance auditing significantly harder.

**Evidence**:
```hcl
# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Modules/Networking/main.tf
# No aws_flow_log resource defined anywhere in the module

# File: /Users/dev/amazon-ecs-fullstack-app-terraform/Infrastructure/Modules/ECS/Cluster/main.tf
# Lines 8-10 -- No container_insights setting
resource "aws_ecs_cluster" "ecs_cluster" {
  name = "Cluster-${var.name}"
}
# Missing:
# setting {
#   name  = "containerInsights"
#   value = "enabled"
# }
```

**Attack Scenario**:
1. An attacker performs network reconnaissance or data exfiltration from a compromised ECS task
2. Without VPC Flow Logs, the unusual outbound traffic patterns (large data transfers, connections to known C2 servers) are not recorded
3. Post-incident forensics cannot determine the scope of the breach, what data was exfiltrated, or how long the attacker had access
4. Compliance auditors flag the absence of network monitoring as a control deficiency

**Existing Mitigations**: CloudWatch log groups capture application-level stdout/stderr from the containers. Autoscaling metrics track CPU and memory utilization. However, neither provides network-level visibility.

**Recommendation**:
```hcl
# Add VPC Flow Logs
resource "aws_flow_log" "vpc_flow_log" {
  iam_role_arn    = aws_iam_role.flow_log_role.arn
  log_destination = aws_cloudwatch_log_group.flow_log.arn
  traffic_type    = "ALL"
  vpc_id          = aws_vpc.aws_vpc.id
}

resource "aws_cloudwatch_log_group" "flow_log" {
  name              = "/vpc/flow-logs/${var.name}"
  retention_in_days = 90
}

# Enable Container Insights
resource "aws_ecs_cluster" "ecs_cluster" {
  name = "Cluster-${var.name}"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}
```

---

## Observations

### Positive Security Findings

1. **Network segmentation**: The architecture properly separates public subnets (ALBs only) from private subnets (ECS tasks), with distinct private subnets for client and server tiers. Security groups restrict ECS task ingress to only the respective ALB security group, preventing direct internet access to containers.

2. **Fargate isolation**: Using AWS Fargate (`launch_type = "FARGATE"`) provides hypervisor-level isolation between tasks, eliminating shared-host risks present in EC2-backed ECS clusters. The `network_mode = "awsvpc"` gives each task its own ENI for security group enforcement.

3. **Blue/Green deployments with auto-rollback**: CodeDeploy is configured for Blue/Green deployments with automatic rollback on failure, reducing the risk of deploying broken or malicious code to production without a recovery path.

4. **Separate execution and task roles**: The architecture correctly separates the ECS execution role (used for pulling images and writing logs) from the ECS task role (used by the application at runtime), following the principle of least privilege for role separation.

5. **CloudWatch logging with retention**: All ECS tasks are configured with the `awslogs` log driver and 30-day retention, providing an audit trail for application-level events.

6. **No public IP on ECS tasks**: The ECS services do not set `assign_public_ip = true`, keeping the containers accessible only through the ALBs via private networking.

## Assumptions & Limitations

1. **Static analysis only**: This review is based on reading source code and Terraform configuration files. No `terraform plan`, `npm audit`, Docker image scan, or runtime analysis was performed.
2. **No lock files analyzed**: `package-lock.json` files were not read, so exact resolved dependency versions and transitive dependency vulnerabilities were not assessed.
3. **Demo context acknowledged**: The reconnaissance notes this is explicitly a demo project. Findings are written for the context of someone forking this as a production starting point, which is the security-relevant use case per the architect's guidance.
4. **AWS provider version constraints**: The pinned AWS provider `~> 3.38` means some recommended Terraform resources (e.g., `aws_s3_bucket_server_side_encryption_configuration` as a separate resource) may require provider upgrade to implement.
5. **GitHub branch protections**: Whether GitHub branch protection rules exist is unknown from the Terraform code alone. The pipeline does not enforce them.
6. **Assumed no external WAF, GuardDuty, or Config**: The Terraform code does not reference these services, and the reconnaissance assumes they are not configured outside this codebase.

## Cross-References

| Finding ID | Related Reconnaissance Findings | Related Threat Model Entries |
|------------|-------------------------------|------------------------------|
| CR-001 | Recon 1.3 (IAM), 1.8 #13 (Missing ECS container hardening) | TA-2 (Malicious Insider), TA-1 (Opportunistic Attacker) |
| CR-002 | Recon 1.3 (CodeBuild: privileged mode, repo-sourced buildspec), 1.8 #14 (Missing approval gates) | TA-2 (Malicious Insider) |
| CR-003 | Recon 1.4 #6 (GitHub OAuth token), 1.4 #8 (Terraform state), 1.8 #16 (Missing remote backend) | TA-5 (Negligent Insider) |
| CR-004 | Recon 1.3 (ALB HTTP only), 1.8 #1 (Missing TLS), 1.4 #1/#2 (plaintext transit) | TA-4 (MITM Attacker) |
| CR-005 | Recon 1.3 #10 (S3 module), 1.8 #4/#5/#6 (Missing S3 controls) | TA-1 (Opportunistic Attacker) |
| CR-006 | Recon 1.3 #4 (ECR MUTABLE), 1.8 #10/#11 (Missing ECR controls) | TA-3 (Supply Chain Attacker) |
| CR-007 | Recon 1.3 (CORS cors()), 1.8 #2 (Missing auth) | TA-1 (Opportunistic Attacker) |
| CR-008 | Recon 1.4 #11 (Server error messages) | TA-1 (Opportunistic Attacker) |
| CR-009 | Recon 1.3 #7 (ECS TaskDefinition), 1.8 #13 (Missing container hardening) | TA-3 (Supply Chain Attacker) |
| CR-010 | Recon 1.10 (Technology Stack - outdated versions) | TA-3 (Supply Chain Attacker) |
| CR-011 | Recon 1.3 #9 (IAM policies) | TA-2 (Malicious Insider) |
| CR-012 | Recon 1.8 #11/#19 (Missing VPC Flow Logs, Container Insights) | All threat actors |

### Remediation Priority Matrix

| Order | ID | Finding | Severity | Effort | Dependencies |
|-------|-----|---------|----------|--------|--------------|
| 1 | CR-001 | iam:PassRole on * | CRITICAL | Low | None |
| 2 | CR-002 | Repo-sourced buildspec + privileged mode | CRITICAL | Medium | None |
| 3 | CR-003 | GitHub OAuth token in state | CRITICAL | Medium | Terraform provider upgrade |
| 4 | CR-004 | HTTP-only ALBs | HIGH | Medium | ACM certificate, domain name |
| 5 | CR-006 | Mutable ECR tags + latest | HIGH | Low | None |
| 6 | CR-005 | S3 bucket hardening | HIGH | Low | Terraform provider upgrade (for separate resources) |
| 7 | CR-007 | Unrestricted CORS | HIGH | Low | Frontend domain known |
| 8 | CR-009 | Unpinned Docker images + root | MEDIUM | Medium | Determine pinned digests |
| 9 | CR-008 | Error handler info disclosure + bug | MEDIUM | Low | None |
| 10 | CR-010 | Outdated dependencies | MEDIUM | High | Regression testing |
| 11 | CR-011 | ECS task role S3 wildcard | MEDIUM | Low | S3 bucket ARN output |
| 12 | CR-012 | Missing VPC Flow Logs + Container Insights | LOW | Low | IAM role for flow logs |

---

## Execution Log

### Process Health
| Metric | Value |
|--------|-------|
| Files Read | 32 |
| Files Written | 1 |
| Errors Encountered | 0 |
| Items Skipped | 2 |
| Self-Assessed Output Quality | HIGH |

### What Went Well
- Reconnaissance file was comprehensive and accurately identified the highest-risk components, allowing efficient prioritization
- All source files were readable and the project structure was well-organized
- The code is small enough that complete coverage of all high-risk components was achievable
- Clear separation between Infrastructure (Terraform) and Code (application) directories made systematic analysis straightforward

### Issues Encountered
- No automated scanning tools (npm audit, tfsec, checkov, trivy, gitleaks) were run as part of this review. The analysis is based entirely on manual static code review. Automated tools would likely surface additional dependency-level CVEs and IaC misconfigurations in lower-risk modules that were not the focus of this review.

### What Was Skipped or Incomplete
- **Dependency vulnerability scanning**: `npm audit` was not executed against the `package-lock.json` files. The CR-010 finding is based on version inspection rather than verified CVE matching. Impact: specific CVE IDs for dependency vulnerabilities are not enumerated.
- **Terraform validation**: `terraform validate` and IaC scanning tools (tfsec, checkov) were not run. Impact: syntactic issues and additional IaC best-practice violations in lower-priority modules may be missed.
- **Client-side Vue.js component analysis**: The Login.vue and other Vue components were not deeply analyzed since the reconnaissance already confirmed there is no authentication implementation. Impact: any client-side XSS or DOM manipulation issues in Vue templates would be missed, though the framework provides default HTML escaping.

### Assumptions Made
- Assumed the `package-lock.json` files exist and are committed to the repository (standard for Node.js projects), though they were not read to verify exact resolved versions
- Assumed the AWS provider version constraint `~> 3.38` means features introduced in AWS provider 4.x and 5.x (such as separate S3 bucket configuration resources) are not available without upgrading
- Assumed no AWS-level guardrails (SCPs, Config Rules, GuardDuty) exist outside the Terraform codebase, as noted in the reconnaissance assumptions
- Assumed the `artillery` dependency in server `package.json` is a development tool mistakenly placed in production dependencies, not an intentional runtime requirement
