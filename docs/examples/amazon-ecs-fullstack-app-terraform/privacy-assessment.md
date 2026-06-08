# Privacy Specialist -- Privacy Impact Assessment

## Metadata
| Field | Value |
|-------|-------|
| Agent | privacy-specialist |
| Date | 2026-02-18 |
| Target System | Amazon ECS Fullstack App (Terraform Demo) |
| Scope | Full system: Vue.js frontend, Node.js/Express backend, AWS infrastructure (ALB, ECS Fargate, DynamoDB, S3, CloudWatch, CI/CD pipeline), Terraform IaC (14 modules) |
| Methodology | LINDDUN Privacy Threat Modeling, Privacy by Design (7 Principles), GDPR/CCPA/HIPAA Regulatory Gap Analysis |
| Scoring System | Qualitative (LINDDUN-based) |

## Summary
- Total findings: 10 (2 critical, 3 high, 3 medium, 2 low)
- Top 3 risks: (1) All personal data transmitted in plaintext over HTTP, enabling interception of IP addresses, browsing behavior, and any future user data; (2) Deceptive login form collects credentials with no authentication, no privacy notice, and no disclosure of what happens to input data; (3) Developer personal data (name, email) hardcoded in source code and exposed via public Swagger endpoint
- Key recommendation: Before any production use, implement TLS on all ALB listeners and remove or properly implement the login form -- these address the two highest-impact privacy risks with the lowest effort-to-benefit ratio

---

## 1. Data Inventory

### 1.1 Personal Data Identified

Despite being a product catalog demo, the system processes several categories of personal data:

| Data Category | Specific Elements | Source | Purpose | Legal Basis | Retention | Recipients | Cross-Border? | Transfer Mechanism |
|---|---|---|---|---|---|---|---|---|
| Network Identifiers | Client IP addresses, User-Agent strings, HTTP headers | Automatic collection via ALB and Nginx access logs | Infrastructure operation, load balancing, logging | Legitimate interest (GDPR Art. 6(1)(f)) | 30 days (CloudWatch log retention) | AWS (processor), DevOps engineers | Potentially -- depends on AWS region selected | AWS DPA; SCCs if applicable |
| Browsing Behavior | Pages visited, API calls made, timestamps | ALB access logs, CloudWatch container logs, Nginx access logs | Operational monitoring, debugging | Legitimate interest (GDPR Art. 6(1)(f)) | 30 days (CloudWatch); indefinite (Nginx default) | AWS (processor), DevOps engineers | Same as above | AWS DPA |
| User Credentials (Entered) | Username, password typed into login form | User input via Login.vue form | None -- data is collected but discarded client-side | No valid legal basis -- no processing purpose | Not retained (client-side only, not transmitted to server) | None (stays in browser memory) | No | N/A |
| Developer Identity | Full name ("Marina Burkhardt"), email (burkhmar@amazon.de) | Hardcoded in package.json (author field) and swagger.js (contact.email) | API documentation, package metadata | Consent (assumed -- developer authored the code) | Indefinite (in source code and deployed artifacts) | Anyone accessing Swagger endpoint or source code | Yes -- code hosted on GitHub, deployed to AWS | N/A (public information in open-source context) |
| Error Context | Request paths, error messages, stack traces (via console.error) | Application error handler in app.js:79 | Debugging, operational monitoring | Legitimate interest (GDPR Art. 6(1)(f)) | 30 days (CloudWatch) | AWS (processor), DevOps engineers | Depends on region | AWS DPA |
| Infrastructure Metadata | AWS Account ID, IAM role ARNs, resource names | CodeBuild environment variables, Terraform state | Infrastructure operation | Legitimate interest | Indefinite (in Terraform state and build logs) | DevOps engineers, AWS | Within AWS account | N/A |

### 1.2 Data Not Currently Collected (but Risk Exists)

The system architecture creates collection points that could be activated without code changes:

- **ALB Access Logs**: Not explicitly enabled in Terraform, but ALB natively passes client IP to targets via `X-Forwarded-For` header. If ALB access logging is enabled (a single Terraform attribute change), full request logs including client IPs would be stored in S3.
- **DynamoDB**: Currently stores only product data, but the ECS task role has `Scan`, `Query`, `GetItem`, `BatchGetItem` permissions. If the schema is extended to include user data, no IAM changes would be needed.
- **S3 Assets Bucket**: Currently stores product images. `force_destroy = true` means all data (including any future personal data) can be deleted without protection.

---

## 2. Data Flow Analysis

### 2.1 Annotated Data Flow

The following annotates the system's data flows with privacy-relevant observations:

```
[End User Browser]
    |
    | (1) HTTP (PLAINTEXT) -- Client IP, User-Agent, browsing behavior exposed
    | **PRIVACY: No TLS. IP addresses (personal data per CJEU C-582/14) transmitted in cleartext**
    | **PRIVACY: No privacy notice or cookie banner at any point**
    |
    v
[Client ALB -- Public Subnet]
    |
    | (2) HTTP -- X-Forwarded-For header adds client IP
    | **PRIVACY: ALB injects client IP into forwarded request**
    |
    v
[Client ECS (Nginx) -- Private Subnet]
    |
    | **PRIVACY: Nginx access logs contain client IPs by default**
    | **PRIVACY: Logs sent to CloudWatch (30-day retention)**
    |
    | (3) User browser makes API call via JavaScript
    |
    v
[End User Browser] ---HTTP (PLAINTEXT)---> [Server ALB -- Public Subnet]
    |
    | (4) HTTP -- Again, no TLS
    | **PRIVACY: API responses containing product data transit in cleartext**
    |
    v
[Server ECS (Node.js/Express) -- Private Subnet]
    |
    | (5) Express error handler logs errors via console.error
    | **PRIVACY: Error logs may contain request context (paths, parameters)**
    | **PRIVACY: Logs sent to CloudWatch (30-day retention)**
    |
    | (6) DynamoDB SDK call via NAT Gateway
    | **PRIVACY: Product data only -- no personal data currently**
    |
    v
[DynamoDB -- AWS Managed]
    | **PRIVACY: AWS-owned encryption key (no customer control)**
    | **PRIVACY: No PITR -- data recovery limitations**

[Swagger Endpoint /api/docs]
    | **PRIVACY: Publicly accessible, no authentication**
    | **PRIVACY: Exposes developer email (burkhmar@amazon.de) -- personal data**

[Login Form -- Client-Side Only]
    | **PRIVACY: Collects username/password but discards them**
    | **PRIVACY: No notice that credentials are not processed**
    | **PRIVACY: Deceptive UI pattern -- appears to authenticate but does not**
```

### 2.2 CI/CD Pipeline Data Flow (Privacy Relevant)

```
[GitHub Repository]
    |
    | GitHub OAuth Token (personal access token -- tied to individual)
    | **PRIVACY: Token in Terraform state (plaintext, local filesystem)**
    |
    v
[CodePipeline] --> [CodeBuild]
    |
    | **PRIVACY: Build logs may contain environment variables**
    | **PRIVACY: SERVER_ALB_URL, AWS_ACCOUNT_ID in plaintext env vars**
    |
    v
[CloudWatch Build Logs]
    | **PRIVACY: No explicit retention period on build log group**
```

---

## 3. LINDDUN Privacy Threat Assessment

### 3.1 Threat Analysis Table

| Threat | Category | Affected Data/Flow | Severity | Existing Controls | Gap | Regulatory Impact |
|---|---|---|---|---|---|---|
| Client IP addresses logged by ALB and Nginx, linkable across sessions | L (Linkability) | Network identifiers in access logs | Medium | None | No IP anonymization/truncation, no documented legal basis | GDPR Art. 5(1)(c) data minimization; CJEU C-582/14 |
| User browsing behavior across pages trackable via logs | L (Linkability) | CloudWatch logs, Nginx access logs | Medium | 30-day retention on CloudWatch | No purpose limitation on log usage, no access controls on log analysis | GDPR Art. 5(1)(b) purpose limitation |
| IP addresses are direct network identifiers; combined with User-Agent can identify individuals | I (Identifiability) | HTTP headers in all requests | High | None | No pseudonymization, no IP truncation, HTTP exposes all headers to network observers | GDPR Art. 25 privacy by default; Art. 32 security |
| Developer identified by name and email in Swagger and package.json | I (Identifiability) | Developer PII in source code | Low | None | Personal data unnecessary for application function | GDPR Art. 5(1)(c) data minimization |
| Login form creates non-repudiable record of user intent to authenticate | N (Non-repudiation) | Username/password entered in Login.vue | Low | Data not transmitted to server | Misleading -- user believes authentication occurred | GDPR Art. 5(1)(a) fairness |
| HTTP traffic detectable and content readable by any network observer | D (Detectability) | All HTTP traffic between user and ALBs | Critical | None | No TLS on any endpoint; all traffic plaintext | GDPR Art. 32(1)(a) encryption; CCPA 1798.150 |
| Full API responses visible to network observers | D (Disclosure) | Product data, error messages, Swagger spec | High | Private subnets for ECS tasks | No encryption in transit (user to ALB, ALB to ALB); Swagger exposes full API surface | GDPR Art. 32; CCPA reasonable security |
| Error handler returns internal error details to client | D (Disclosure) | Error codes and messages in app.js:78-88 | Medium | Error caught and formatted | Raw error messages may leak internal details (DynamoDB table names, SDK errors) | CWE-209; GDPR Art. 32 |
| No privacy notice, no cookie information, no data processing transparency | U (Unawareness) | All personal data processing | High | None | Complete absence of privacy notice at any collection point | GDPR Art. 13/14; CCPA 1798.100(b) |
| Login form collects credentials without disclosing they are not processed | U (Unawareness) | Credentials entered in login form | Medium | Asterisk note: "*No auth was implemented" | Note is ambiguous -- does not explain what happens to entered data | GDPR Art. 5(1)(a) transparency; EDPB Guidelines 3/2022 |
| No mechanism for data subject rights (access, deletion, portability) | N (Non-compliance) | All personal data (IP addresses, logs) | High | None | No data subject rights infrastructure | GDPR Art. 15-22; CCPA 1798.100-125 |
| No records of processing activities | N (Non-compliance) | All processing activities | Medium | None | No ROPA maintained | GDPR Art. 30 |
| No Data Processing Agreement documentation for AWS | N (Non-compliance) | All data processed by AWS services | Medium | AWS offers standard DPA | No evidence DPA was executed or reviewed | GDPR Art. 28 |

---

## 4. Findings

### CRITICAL PA-001: All Personal Data Transmitted in Plaintext (No TLS)

| Field | Value |
|-------|-------|
| ID | PA-001 |
| Severity | CRITICAL |
| Confidence | HIGH |
| Affected Component(s) | Client ALB, Server ALB, Client ECS, Server ECS |
| Scoring System | Qualitative (LINDDUN-based) |
| Score | N/A |
| Cross-Framework | CWE-319 | OWASP A02:2021 (Cryptographic Failures) |

**Description**: All communication between end users and the application occurs over unencrypted HTTP. The ALB module has an `enable_https` variable that defaults to `false`, and no HTTPS listener is configured. The Swagger definition explicitly uses `schemes: ['http']`. This exposes all personal data in transit -- including client IP addresses (personal data per CJEU C-582/14 Breyer v. Germany), User-Agent strings, browsing patterns, and any data entered into forms -- to interception by any network-position observer.

Under GDPR Art. 32(1)(a), controllers MUST implement "encryption" as an appropriate technical measure. Under CCPA Section 1798.150, the failure to implement "reasonable security procedures" including encryption creates a private right of action for data breaches.

**Evidence**:
- `Infrastructure/Modules/ALB/variables.tf:28`: `enable_https` defaults to `false`
- `Infrastructure/Modules/ALB/main.tf:38-53`: Only HTTP listener on port 80 is created
- `Infrastructure/main.tf` never sets `enable_https = true` for either ALB
- `Code/server/src/swagger/swagger.js:24`: `schemes: ['http']`
- `Code/client/src/services/RestServices.js:6`: `let serverUrl = "http://<SERVER_ALB_URL>"`
- No ACM certificate resource defined anywhere in Terraform code

**Attack Scenario**:
1. User on shared WiFi (coffee shop, hotel, airport) accesses the application
2. Network-position attacker captures HTTP traffic using standard tools (Wireshark, tcpdump)
3. Attacker obtains user's IP address, browsing behavior, any form inputs, and full API response data
4. If the application is extended to handle actual user accounts or payment data, all such data would be immediately exposed

**Existing Mitigations**: ECS tasks are in private subnets (mitigates internal east-west interception), but user-to-ALB traffic traverses the public internet unencrypted.

**Recommendation**:
1. Enable HTTPS on both ALBs: set `enable_https = true` and provision ACM certificates
2. Add HTTP-to-HTTPS redirect on port 80 listeners
3. Implement HSTS headers (Strict-Transport-Security) on both frontend and backend responses
4. Update Swagger schemes to `['https']`
5. Update RestServices.js server URL template to use `https://`
6. Consider adding `aws_lb_listener_rule` to redirect all HTTP to HTTPS

---

### CRITICAL PA-002: Deceptive Login Form Collects Credentials Without Processing or Disclosure

| Field | Value |
|-------|-------|
| ID | PA-002 |
| Severity | CRITICAL |
| Confidence | HIGH |
| Affected Component(s) | Client ECS (Login.vue) |
| Scoring System | Qualitative (LINDDUN-based) |
| Score | N/A |
| Cross-Framework | CWE-1021 | OWASP A04:2021 (Insecure Design) |

**Description**: The Login.vue component presents a fully functional-looking login form requesting username and password. The form accepts any input, stores it in Vue.js reactive data properties (`this.user` and `this.password`), and navigates to `/main` without any server-side validation or data transmission. A small-text note states "*No auth was implemented, just a Vue.js demo component*", but this does not adequately inform users about what happens to the credentials they enter.

This constitutes a deceptive design pattern under EDPB Guidelines 3/2022 on Dark Patterns in Social Media Platforms (applicable by analogy). Under GDPR Art. 5(1)(a), processing must be "lawful, fair, and transparent." A form that appears to collect credentials but silently discards them violates the fairness principle. If users enter real credentials (which users habitually do when presented with login forms), they may believe those credentials are being securely processed and stored.

Additionally, if this demo is forked for production use, the login form represents a credential collection point with zero security infrastructure -- no HTTPS, no CSRF protection, no rate limiting, no credential storage security.

**Evidence**:
- `Code/client/src/components/Login.vue:9-16`: Form with `v-model="user"` and `v-model="password"` inputs
- `Code/client/src/components/Login.vue:46-48`: `onSubmit()` method simply navigates to `/main`
- `Code/client/src/components/Login.vue:28`: Disclaimer in `<h5>` tags below the form
- Reconnaissance confirms: "Login component explicitly notes: *No auth was implemented, just a Vue.js demo component*"

**Attack Scenario**:
1. User visits the application and encounters the login form
2. User enters their real username and password (credential reuse is common)
3. Credentials are stored in Vue.js reactive state in browser memory
4. If any browser extension, XSS vulnerability, or developer tools inspection occurs, credentials are accessible
5. User has no way to know credentials were not transmitted, processed, or stored

**Existing Mitigations**: Asterisk disclaimer below form (inadequate -- does not explain data handling). Data is not transmitted to the server (limits actual exposure).

**Recommendation**:
1. **Immediate**: Remove the login form entirely if authentication is not implemented. Replace with a direct landing page.
2. **Alternative**: If the login form must remain for demo purposes, replace password input with a clear placeholder (e.g., "Demo -- no authentication") and disable the password field. Add a prominent banner (not footnote) stating "This is a demo interface. Do not enter real credentials."
3. **If authentication will be implemented**: Add proper HTTPS (PA-001), implement server-side authentication, add CSRF protection, implement secure credential storage (bcrypt/argon2), and add a privacy notice covering credential processing.

---

### HIGH PA-003: No Privacy Notice or Transparency Mechanism

| Field | Value |
|-------|-------|
| ID | PA-003 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | Client ECS (all Vue.js routes) |
| Scoring System | Qualitative (LINDDUN-based) |
| Score | N/A |
| Cross-Framework | CWE-1059 | OWASP A04:2021 (Insecure Design) |

**Description**: The application has no privacy notice, privacy policy page, cookie banner, or any form of transparency about data processing. Under GDPR Art. 13, when personal data is collected from the data subject, the controller MUST provide specified information "at the time when personal data are obtained." Under CCPA Section 1798.100(b), businesses MUST provide notice "at or before the point of collection."

Even for a demo application, personal data is collected automatically (IP addresses via ALB/Nginx logs, browsing behavior via CloudWatch). No notice is provided about this collection.

The Vue.js router defines routes for `/`, `/main`, `/about`, and `/search` -- none include any privacy-related content. The Nav.vue component shows navigation items but no privacy link. The About.vue page contains only "Frontend layer demo" text.

**Evidence**:
- Complete absence of privacy-related Vue components, routes, or content
- `Code/client/src/router/index.js`: No privacy policy route
- `Code/client/src/components/Nav.vue`: No privacy link in navigation
- `Code/client/src/views/About.vue`: No privacy information
- No `privacy`, `terms`, `policy`, or `cookie` strings found in any frontend code

**Attack Scenario**:
1. EU-based user visits the application
2. IP address and browsing behavior are logged (CloudWatch, ALB, Nginx)
3. User has received no information about: identity of controller, purposes of processing, legal basis, retention periods, data subject rights, or right to lodge a complaint
4. This constitutes a violation of GDPR Art. 13 for every page view by every user

**Existing Mitigations**: None.

**Recommendation**:
1. Create a privacy notice page accessible from all application pages (footer link)
2. Privacy notice MUST include all elements required by GDPR Art. 13(1) and (2): controller identity, DPO contact, processing purposes, legal basis, recipients, retention periods, data subject rights, right to complaint, and whether provision of data is statutory/contractual
3. If the application will serve EU users, implement a cookie consent mechanism (ePrivacy Directive Art. 5(3))
4. For CCPA compliance, include a "Do Not Sell or Share My Personal Information" link if applicable
5. Display notice at or before the first point of data collection (i.e., on page load, since IP logging begins immediately)

---

### HIGH PA-004: Developer Personal Data Exposed in Public Swagger Endpoint

| Field | Value |
|-------|-------|
| ID | PA-004 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | Server ECS (Swagger endpoint) |
| Scoring System | Qualitative (LINDDUN-based) |
| Score | N/A |
| Cross-Framework | CWE-200 | OWASP A01:2021 (Broken Access Control) |

**Description**: The Swagger API documentation endpoint (`/api/docs`) is publicly accessible without authentication and contains developer personal data: the contact email `burkhmar@amazon.de` in `swagger.js:15`. The package.json files for both client and server also contain the developer's full name ("Marina Burkhardt") in the `author` field. While the package.json is not served to end users directly, it is included in the Docker image (via `COPY . .` in the server Dockerfile) and could be accessed if the container filesystem is compromised.

The Swagger endpoint actively serves this personal data to anyone on the internet. Under GDPR Art. 5(1)(c) (data minimization), personal data must be "adequate, relevant and limited to what is necessary." A developer's personal email address is not necessary for API documentation to function.

**Evidence**:
- `Code/server/src/swagger/swagger.js:14-16`: `contact: { email: 'burkhmar@amazon.de' }`
- `Code/client/package.json:6`: `"author": "Marina Burkhardt"`
- `Code/server/package.json:6`: `"author": "Marina Burkhardt"`
- Swagger endpoint served at `/api/docs` (unauthenticated, per reconnaissance entry point #3)
- `/api/docs/json` returns raw JSON including the email

**Attack Scenario**:
1. Anyone accesses `{server_alb}/api/docs/json`
2. Full Swagger spec is returned, including developer email address
3. Email can be used for targeted phishing, social engineering, or spam
4. Developer's association with specific AWS infrastructure is revealed

**Existing Mitigations**: None. Endpoint is fully public with no authentication (reconnaissance confirms CORS allows all origins).

**Recommendation**:
1. Replace the personal email with a team or organization contact (e.g., `aws-demos@amazon.com` or remove the contact block entirely)
2. Consider replacing the `author` field in package.json with the organization name
3. Restrict Swagger endpoint access: either add authentication, limit to internal networks, or disable in production deployments
4. Add `.swagger-ui` to production deployment exclusions if not needed

---

### HIGH PA-005: No Data Subject Rights Infrastructure

| Field | Value |
|-------|-------|
| ID | PA-005 |
| Severity | HIGH |
| Confidence | HIGH |
| Affected Component(s) | Entire system |
| Scoring System | Qualitative (LINDDUN-based) |
| Score | N/A |
| Cross-Framework | CWE-1059 | OWASP A04:2021 |

**Description**: The system provides no mechanism for data subjects to exercise their rights under GDPR (Art. 15-22) or CCPA (Sections 1798.100-125). Even though the system currently processes limited personal data (IP addresses, browsing behavior in logs), data subjects have the right to:
- **Access** (GDPR Art. 15 / CCPA 1798.100): Request what personal data is held about them
- **Deletion** (GDPR Art. 17 / CCPA 1798.105): Request erasure of their personal data
- **Portability** (GDPR Art. 20): Receive their data in a portable format
- **Object** (GDPR Art. 21): Object to processing based on legitimate interest
- **Restriction** (GDPR Art. 18): Request restriction of processing

CloudWatch Logs does not support selective record deletion (you can delete an entire log group or stream, but not individual log entries). This means complying with deletion requests for IP addresses in logs would require either deleting entire log groups (affecting operational data) or implementing log anonymization at ingestion.

**Evidence**:
- No API endpoints for data subject requests
- No contact mechanism for privacy requests (no privacy email, no web form)
- No process documented for handling access or deletion requests
- CloudWatch Log retention set to 30 days (`TaskDefinition/main.tf:47`), but no selective deletion capability
- No privacy contact in any user-facing component

**Attack Scenario**:
1. EU data subject submits a GDPR Art. 15 Subject Access Request
2. Organization has no process to identify what data is held about the individual
3. IP address-based log data cannot be efficiently searched or extracted
4. Organization cannot respond within the 30-day deadline (GDPR Art. 12(3))
5. Data subject complaints to supervisory authority; potential enforcement action

**Existing Mitigations**: CloudWatch log retention of 30 days provides a natural data lifecycle (logs older than 30 days are automatically deleted). However, this does not address the right to access or the right to deletion within that 30-day window.

**Recommendation**:
1. **Immediate (if processing EU/CA data)**: Establish a privacy contact email and document it in a privacy notice
2. **Process**: Create internal procedures for handling data subject requests (access, deletion, portability)
3. **Technical**: Implement IP anonymization at the application/ALB level to reduce the scope of personal data requiring rights infrastructure. Consider truncating the last octet of IPv4 addresses in logs.
4. **Technical**: Consider using VPC Flow Logs with anonymization rather than ALB access logs if network monitoring is needed
5. **Policy**: Document the 30-day CloudWatch retention as a data lifecycle control that supports the right to erasure (after 30 days, data is automatically deleted)

---

### MEDIUM PA-006: Error Handler May Disclose Internal System Details

| Field | Value |
|-------|-------|
| ID | PA-006 |
| Severity | MEDIUM |
| Confidence | MEDIUM |
| Affected Component(s) | Server ECS (app.js error handler) |
| Scoring System | Qualitative (LINDDUN-based) |
| Score | N/A |
| Cross-Framework | CWE-209 | OWASP A05:2021 (Security Misconfiguration) |

**Description**: The Express error handler at `app.js:78-88` returns error details directly to the client, including `err.status` and `err.message`. When the DynamoDB SDK encounters errors, these messages may include internal details such as table names, AWS region, credential issues, or resource ARNs. The `console.error` call at line 79 also logs the full error object (including potential stack traces) to CloudWatch.

While not directly a privacy issue for end users, exposure of internal infrastructure details facilitates targeted attacks that could ultimately compromise personal data. Additionally, the logged error context in CloudWatch may contain request details that include personal data (IP from request headers, request paths).

**Evidence**:
- `Code/server/src/app.js:78-88`: Error handler returns `err.message` to client
- `Code/server/src/app.js:79`: `console.error(\`Error catched! ${err}\`)` logs full error
- DynamoDB SDK errors include table names and AWS-specific error codes
- No error sanitization before client response

**Attack Scenario**:
1. Attacker sends malformed request to `/api/getAllProducts`
2. DynamoDB SDK throws error containing table name (e.g., "assets-table-demo")
3. Error message returned to attacker, revealing internal resource naming
4. Attacker uses information to craft targeted attacks against AWS resources

**Existing Mitigations**: Error handler catches errors and structures the response (prevents raw stack traces from reaching the client in most cases).

**Recommendation**:
1. Return generic error messages to clients (e.g., "An internal error occurred. Please try again later.")
2. Log detailed errors server-side only (current `console.error` is acceptable for this)
3. Sanitize error logs to remove or mask any personal data from request context
4. Implement structured error logging that separates system errors from request context

---

### MEDIUM PA-007: CloudWatch Logs Contain Personal Data Without Documented Controls

| Field | Value |
|-------|-------|
| ID | PA-007 |
| Severity | MEDIUM |
| Confidence | HIGH |
| Affected Component(s) | CloudWatch Log Groups, Server ECS, Client ECS |
| Scoring System | Qualitative (LINDDUN-based) |
| Score | N/A |
| Cross-Framework | CWE-532 | OWASP A09:2021 (Security Logging and Monitoring Failures) |

**Description**: CloudWatch Log Groups receive container logs from both frontend (Nginx) and backend (Node.js) ECS tasks. Nginx logs client IP addresses by default in its access log format. The Node.js `console.error` calls log error context. These logs are retained for 30 days (configured in Terraform) but:

1. No documented legal basis for the log retention of personal data
2. No access controls documented beyond default CloudWatch IAM permissions
3. No log anonymization or pseudonymization configured
4. Build log groups (`log-group/log-stream` in CodeBuild) have no explicit retention period (default: indefinite)
5. Logs encrypted only with CloudWatch default encryption (AWS-managed key, no CMK)

Under GDPR Art. 5(1)(e) (storage limitation), personal data must be "kept in a form which permits identification of data subjects for no longer than is necessary." The 30-day retention for container logs is reasonable, but the build log groups have no retention configured, potentially retaining personal data indefinitely.

**Evidence**:
- `Infrastructure/Modules/ECS/TaskDefinition/main.tf:45-47`: 30-day retention on container log groups
- `Infrastructure/Modules/CodeBuild/main.tf:86-89`: `logs_config` with no retention period specified
- Nginx default access log format includes `$remote_addr` (client IP)
- No CloudWatch Logs encryption configuration (KMS) in any Terraform module

**Attack Scenario**:
1. Personal data (IP addresses) accumulates in CloudWatch Logs
2. Overly broad IAM policy (DevOps role has `logs:*` on `"*"`) allows broad log access
3. Internal user with DevOps role access queries logs containing personal data without authorization
4. No audit trail of who accessed which log data (CloudWatch does not log read access by default)

**Existing Mitigations**: 30-day retention on container logs (automatic deletion). Private subnets ensure ECS tasks are not directly accessible. IAM roles required for CloudWatch access.

**Recommendation**:
1. Set explicit retention periods on ALL log groups, including CodeBuild logs
2. Implement CloudWatch Logs encryption with a customer-managed KMS key
3. Configure Nginx to truncate or anonymize IP addresses in access logs (e.g., using `map` directive to mask last octet)
4. Document log retention as a data processing activity in the ROPA
5. Restrict CloudWatch Logs access using IAM policies scoped to specific log groups (not `"*"`)
6. Enable AWS CloudTrail for CloudWatch Logs API calls to audit log access

---

### MEDIUM PA-008: No Data Processing Agreement Documentation

| Field | Value |
|-------|-------|
| ID | PA-008 |
| Severity | MEDIUM |
| Confidence | MEDIUM |
| Affected Component(s) | Entire AWS infrastructure, GitHub integration |
| Scoring System | Qualitative (LINDDUN-based) |
| Score | N/A |
| Cross-Framework | N/A (organizational control) |

**Description**: The system relies on AWS as a data processor for all personal data processing (CloudWatch Logs, ALB, ECS, DynamoDB). Under GDPR Art. 28(3), processing by a processor must be governed by a contract or other legal act. AWS offers a Data Processing Addendum (AWS DPA) and GDPR-specific addendum, but there is no evidence in the codebase or documentation that:

1. The AWS DPA has been executed
2. The data processing activities have been documented
3. Sub-processor disclosures have been reviewed
4. GitHub's data processing terms have been reviewed (for the CI/CD pipeline integration)

Additionally, the GitHub OAuth token integration means GitHub has access to repository metadata and webhook payloads, which could include CI/CD artifacts.

**Evidence**:
- No DPA or data processing documentation found in the repository
- No `CONTRIBUTING.md` with privacy considerations
- GitHub integration via OAuth token (`Infrastructure/Modules/CodePipeline/main.tf:29`)
- AWS services used: ECS, ALB, CloudWatch, DynamoDB, S3, CodeBuild, CodePipeline, CodeDeploy, ECR, SNS

**Attack Scenario**: This is a compliance risk rather than a technical attack scenario. If the system processes EU personal data without documented processor agreements, the data controller is in violation of GDPR Art. 28. Supervisory authorities have issued fines for inadequate processor agreements.

**Existing Mitigations**: AWS provides standard DPA and GDPR addendum available for execution. AWS maintains SOC 2 Type II and ISO 27001 certifications.

**Recommendation**:
1. Execute the AWS DPA (available in AWS Artifact console)
2. Document the specific AWS services used as data processors
3. Review and execute GitHub's DPA for the CI/CD integration
4. Maintain a processor register as part of ROPA (GDPR Art. 30)
5. Review AWS sub-processor list periodically

---

### LOW PA-009: GitHub Personal Access Token Tied to Individual Developer

| Field | Value |
|-------|-------|
| ID | PA-009 |
| Severity | LOW |
| Confidence | HIGH |
| Affected Component(s) | CodePipeline, Terraform state |
| Scoring System | Qualitative (LINDDUN-based) |
| Score | N/A |
| Cross-Framework | CWE-798 |

**Description**: The CI/CD pipeline requires a GitHub Personal Access Token (PAT) passed as a Terraform variable. PATs are tied to individual GitHub accounts, meaning a specific developer's identity is embedded in the infrastructure. The token is stored in the local Terraform state file in plaintext. This creates privacy concerns for the developer:

1. Their identity is tied to infrastructure operations
2. Their token (which grants access to their personal GitHub account) is stored insecurely
3. If the Terraform state is compromised, the developer's GitHub account is at risk

While this is primarily a security concern, it has privacy implications for the developer whose credentials are used.

**Evidence**:
- `Infrastructure/variables.tf:24-28`: `github_token` variable marked sensitive
- `Infrastructure/Modules/CodePipeline/main.tf:29`: `OAuthToken = var.github_token`
- Reconnaissance notes: "Terraform state stored locally (no remote backend configured)"
- Reconnaissance notes: "GitHub token passed as plaintext Terraform variable (marked sensitive but stored in state)"

**Attack Scenario**:
1. Terraform state file is accessed by unauthorized party (local filesystem)
2. GitHub PAT extracted from state
3. Attacker gains access to developer's personal GitHub account
4. Developer's personal repositories, contributions, and identity exposed

**Existing Mitigations**: Variable marked as `sensitive = true` (prevents display in Terraform plan output). `ignore_changes` on pipeline configuration prevents token from appearing in diffs.

**Recommendation**:
1. Use a GitHub App or machine account token instead of a personal access token
2. Store the token in AWS Secrets Manager or SSM Parameter Store
3. Use a remote Terraform backend with encryption (S3 + DynamoDB locking)
4. Implement token rotation policy
5. Consider migrating to GitHub Actions or AWS CodeStar Connection (eliminates PAT requirement)

---

### LOW PA-010: Unrestricted CORS Enables Cross-Origin Data Access

| Field | Value |
|-------|-------|
| ID | PA-010 |
| Severity | LOW |
| Confidence | HIGH |
| Affected Component(s) | Server ECS (Express app) |
| Scoring System | Qualitative (LINDDUN-based) |
| Score | N/A |
| Cross-Framework | CWE-942 | OWASP A05:2021 |

**Description**: The Express server uses `app.use(cors())` with no configuration, which allows any origin to make cross-origin requests to all API endpoints. While the current API only serves public product data, unrestricted CORS means any third-party website could embed requests to this API and access the responses. If the API is extended to serve personal data or implement authentication, the lack of CORS restrictions would allow any website to access user-specific data in the context of the user's session.

From a privacy perspective, unrestricted CORS enables third-party websites to make the user's browser act as a proxy, potentially enabling data collection about user interactions without the user's awareness.

**Evidence**:
- `Code/server/src/app.js:10`: `app.use(cors())` with no options
- Reconnaissance confirms: "Express CORS middleware used with app.use(cors()) -- no options specified, which allows all origins"

**Attack Scenario**:
1. Third-party website includes JavaScript that calls the API
2. User visits the third-party website
3. User's browser makes cross-origin request to the API
4. API response (product data, or future personal data) is accessible to the third-party website
5. Third-party website can correlate user's visit with their API data

**Existing Mitigations**: API currently serves only public product data (limited privacy impact). No authentication means no user context to exploit.

**Recommendation**:
1. Configure CORS to allow only the client ALB origin: `app.use(cors({ origin: 'https://client-alb-dns' }))`
2. If multiple origins are needed, implement a whitelist
3. Restrict CORS headers to only necessary methods and headers

---

## 5. Regulatory Compliance Matrix

### 5.1 GDPR Compliance (Applicable if EU Data Subjects Access the Application)

| Requirement | Regulation & Article | Status | Evidence | Remediation Needed |
|---|---|---|---|---|
| Lawful basis for processing | GDPR Art. 6 | Non-Compliant | No legal basis documented for IP address collection and logging | Document legitimate interest assessment for operational logging |
| Transparency / Privacy notice | GDPR Art. 13 | Non-Compliant | No privacy notice anywhere in the application | Create and display comprehensive privacy notice |
| Data minimization | GDPR Art. 5(1)(c) | Partially Compliant | Product data is minimal; however, IP addresses logged without minimization; developer email exposed unnecessarily | Truncate IPs in logs; remove developer PII from Swagger |
| Purpose limitation | GDPR Art. 5(1)(b) | Non-Compliant | No documented purposes for any data processing | Document processing purposes in ROPA |
| Storage limitation | GDPR Art. 5(1)(e) | Partially Compliant | 30-day CloudWatch retention exists but not all log groups have retention; no documented rationale | Set retention on all log groups; document rationale |
| Security of processing | GDPR Art. 32 | Non-Compliant | No TLS, no encryption at rest (CMK), no access logging, wide CORS, no WAF | Implement TLS, CMK encryption, WAF, restrict CORS |
| Privacy by design & default | GDPR Art. 25 | Non-Compliant | No privacy measures incorporated into design | See Privacy by Design assessment (Section 7) |
| Data processor agreements | GDPR Art. 28 | Non-Compliant | No documented DPA with AWS or GitHub | Execute DPAs with all processors |
| Records of processing | GDPR Art. 30 | Non-Compliant | No ROPA maintained | Create ROPA covering all processing activities |
| Data subject rights | GDPR Art. 15-22 | Non-Compliant | No mechanism for any data subject right | Implement rights handling process and contact |
| DPIA | GDPR Art. 35 | Not Assessed | DPIA required if processing is likely high risk; not applicable for current demo scope | Assess DPIA requirement if system handles user accounts |
| Breach notification | GDPR Art. 33-34 | Non-Compliant | No breach detection, notification process, or incident response | Implement breach detection and notification process |
| International transfers | GDPR Art. 44-49 | Not Assessed | Depends on AWS region and user location; no transfer mechanism documented | Document transfer mechanism if applicable |

### 5.2 CCPA/CPRA Compliance (Applicable if California Residents Access the Application)

| Requirement | Regulation & Article | Status | Evidence | Remediation Needed |
|---|---|---|---|---|
| Notice at collection | CCPA 1798.100(b) | Non-Compliant | No notice of any kind | Provide notice at or before collection |
| Right to know | CCPA 1798.100(a) | Non-Compliant | No mechanism for consumer requests | Implement request handling process |
| Right to delete | CCPA 1798.105 | Non-Compliant | No deletion mechanism; CloudWatch selective deletion not possible | Implement deletion process; consider log anonymization |
| Right to opt-out | CCPA 1798.120 | Not Assessed | Application does not appear to "sell" or "share" data | Assess if any third-party analytics or tracking constitutes "sharing" |
| Reasonable security | CCPA 1798.150 | Non-Compliant | No TLS, no encryption configuration | Implement reasonable security measures (TLS, encryption) |

### 5.3 HIPAA Assessment

**Determination**: HIPAA is **not applicable** to this system. The application is a product catalog demo that does not process any Protected Health Information (PHI). There is no healthcare context, no covered entity relationship, and no health-related data categories. No further HIPAA analysis is warranted unless the system's purpose changes to include health data.

---

## 6. Privacy by Design Assessment

### Principle 1: Proactive not Reactive; Preventative not Remedial

**Rating**: NOT MET

The system contains no proactive privacy measures. Privacy considerations were not part of the design process. All personal data handling (IP logging, error handling) is incidental to operational needs with no privacy assessment conducted beforehand. The login form was added as a UI demo without considering the privacy implications of collecting credentials.

**Recommendation**: Conduct a privacy impact assessment before any production deployment. Include privacy requirements in the system design documentation.

### Principle 2: Privacy as the Default Setting

**Rating**: NOT MET

The default settings are privacy-hostile:
- HTTPS is disabled by default (`enable_https = false`)
- CORS allows all origins by default
- Full IP addresses are logged by default (Nginx)
- Swagger endpoint is public by default (no authentication)
- Error details are returned to clients by default

**Recommendation**: Change defaults to the most privacy-protective options. HTTPS should be enabled by default. CORS should be restrictive by default. Log anonymization should be the default.

### Principle 3: Privacy Embedded into Design

**Rating**: NOT MET

Privacy is not embedded into any system component. There are no data flow restrictions, no data classification mechanisms, no consent management, no access controls on personal data, and no privacy-aware logging configuration.

**Recommendation**: Integrate privacy into the architecture: add data classification tags to Terraform resources, implement purpose-based access controls, configure privacy-preserving log formats.

### Principle 4: Full Functionality -- Positive-Sum, not Zero-Sum

**Rating**: PARTIALLY MET

The system demonstrates that a product catalog can function without collecting excessive personal data. The DynamoDB schema contains only product data (id, title, path). However, the login form demonstrates a zero-sum tradeoff -- it provides a UI demo at the cost of user confusion and potential credential exposure.

**Recommendation**: Remove the deceptive login form. The product catalog functionality does not require credential collection.

### Principle 5: End-to-End Security -- Full Lifecycle Protection

**Rating**: NOT MET

Personal data (IP addresses in logs) has no security controls throughout its lifecycle:
- **Collection**: Unencrypted (HTTP)
- **Transmission**: Unencrypted
- **Storage**: Default encryption only (AWS-managed keys)
- **Processing**: No access controls documented
- **Deletion**: 30-day retention on some (not all) log groups; no selective deletion

**Recommendation**: Implement TLS for collection/transmission, CMK encryption for storage, IAM scoped access for processing, and documented retention with deletion verification.

### Principle 6: Visibility and Transparency

**Rating**: NOT MET

Zero transparency:
- No privacy notice
- No cookie information
- No data processing documentation
- No ROPA
- No audit logging of data access
- No mechanism for data subjects to inquire about processing

**Recommendation**: Create comprehensive privacy documentation. Implement audit logging. Publish privacy notice.

### Principle 7: Respect for User Privacy -- Keep it User-Centric

**Rating**: NOT MET

The system provides no user-centric privacy features:
- No ability to control data collection
- No ability to access personal data
- No ability to request deletion
- Deceptive login form undermines user trust
- No consent mechanism for any processing activity

**Recommendation**: Implement data subject rights mechanisms. Remove deceptive UI patterns. Provide meaningful privacy controls.

---

## 7. Risk Register

| Risk ID | Risk Description | LINDDUN Category | Likelihood | Impact on Individuals | Severity | Recommended Mitigation | Regulatory Citation |
|---|---|---|---|---|---|---|---|
| PA-001 | All traffic in plaintext; IP addresses and browsing behavior exposed to network observers | D (Detectability) + D (Disclosure) | High | Surveillance, behavioral profiling, identity exposure on shared networks | Critical | Enable TLS on all ALBs; add HSTS | GDPR Art. 32(1)(a); CCPA 1798.150 |
| PA-002 | Deceptive login form collects credentials without processing or disclosure | U (Unawareness) | High | Credential exposure if reused; loss of trust; psychological harm from deception | Critical | Remove form or add clear disclosure | GDPR Art. 5(1)(a); EDPB Guidelines 3/2022 |
| PA-003 | No privacy notice at any data collection point | U (Unawareness) + N (Non-compliance) | High | Individuals unaware of data processing; cannot exercise rights | High | Create GDPR Art. 13 compliant privacy notice | GDPR Art. 13; CCPA 1798.100(b) |
| PA-004 | Developer personal data (email) exposed via public Swagger endpoint | I (Identifiability) + D (Disclosure) | Medium | Targeted phishing, spam, social engineering against developer | High | Remove personal email; restrict Swagger access | GDPR Art. 5(1)(c) |
| PA-005 | No data subject rights handling infrastructure | N (Non-compliance) | Medium | Individuals cannot access, delete, or port their data | High | Implement rights handling process and technical controls | GDPR Art. 15-22; CCPA 1798.100-125 |
| PA-006 | Error handler discloses internal system details | D (Disclosure) | Medium | Indirect -- facilitates attacks that could compromise personal data | Medium | Return generic errors to clients | GDPR Art. 32 |
| PA-007 | CloudWatch Logs contain IP addresses without documented controls | L (Linkability) + I (Identifiability) | Medium | IP-based tracking, behavior profiling via log analysis | Medium | Anonymize IPs; encrypt with CMK; restrict access | GDPR Art. 5(1)(c)(e); Art. 32 |
| PA-008 | No documented data processing agreements | N (Non-compliance) | Low | Regulatory non-compliance; no contractual protection for personal data | Medium | Execute AWS DPA and GitHub DPA | GDPR Art. 28(3) |
| PA-009 | GitHub PAT tied to individual developer stored in plaintext Terraform state | I (Identifiability) | Low | Developer account compromise; identity exposure | Low | Use machine account; encrypt state | GDPR Art. 32 |
| PA-010 | Unrestricted CORS allows any origin to access API | D (Disclosure) | Low | Third-party data access if API extended to personal data | Low | Restrict CORS to known origins | GDPR Art. 25 |

---

## 8. Observations

### Positive Observations

1. **Data Minimization in Core Design**: The DynamoDB schema stores only product catalog data (id, title, image path). No user accounts, preferences, or behavioral data is stored in the database. This is a good privacy-by-design pattern for a product catalog application.

2. **Private Subnets for Compute**: ECS tasks run in private subnets, reducing the attack surface for personal data in transit between internal services. This is a meaningful architectural control.

3. **CloudWatch Log Retention**: Container log groups have an explicit 30-day retention period, providing automatic data lifecycle management. This supports the storage limitation principle.

4. **No Cookies or Client-Side Tracking**: The application does not use cookies, localStorage, sessionStorage, or any client-side tracking mechanisms. No analytics scripts, no third-party trackers, no fingerprinting. This is a privacy-positive design choice.

5. **No User Account Data Store**: The absence of a user database means there is no repository of user credentials, profiles, or preferences to secure, breach-notify about, or provide access/deletion for.

6. **Terraform Sensitive Variable**: The GitHub token is marked as `sensitive = true`, showing awareness of credential protection (even though the implementation is insufficient).

7. **Security Group Segmentation**: ECS tasks accept ingress only from their respective ALB security groups, limiting the blast radius of any compromise.

---

## 9. Assumptions & Limitations

### Assumptions

1. **AWS Region**: The assessment assumes the system could be deployed in any AWS region. If deployed in an EU region for EU users, GDPR applies fully. If deployed in a US region, CCPA may apply to California residents.

2. **Data Subjects**: The assessment assumes end users could include EU residents and California residents, triggering GDPR and CCPA applicability. If the system is restricted to internal use by a specific team, some regulatory requirements may not apply.

3. **Demo Context**: The system is explicitly a demo/reference architecture. The assessment evaluates it both in its current demo context and as a potential production starting point (since organizations may fork it). Findings note where a gap is expected for a demo but unacceptable for production.

4. **No Additional Services**: The assessment assumes no additional AWS services (WAF, GuardDuty, Config, CloudTrail, Macie) are configured outside this Terraform code.

5. **ALB Access Logging**: ALB access logging is not explicitly enabled in Terraform, but Nginx access logs within containers still capture client IPs. The assessment considers both sources.

6. **Current vs. Future State**: Several findings (PA-005, PA-010) are based on the system's potential future state if extended for production use. This is noted in each finding.

### Limitations

1. **No Runtime Analysis**: This assessment is based on static code and configuration review. No live traffic was inspected, no log samples were reviewed, and no penetration testing was conducted.

2. **No Organizational Context**: The assessment cannot determine whether organizational privacy policies, DPAs, or ROPA exist outside the codebase.

3. **No Browser Behavior Analysis**: The assessment did not analyze browser-side behavior (cookies set by Nginx, caching headers, referrer policies) that could have privacy implications.

4. **HIPAA Scope**: HIPAA was determined not applicable based on the current system purpose. If the system's scope changes to include health-related data, a separate HIPAA assessment would be needed.

---

## 10. Cross-References

### Related Threat Model Findings

| Privacy Finding | Related Security Finding | Relationship |
|---|---|---|
| PA-001 (No TLS) | TM-001 (likely: No HTTPS on ALBs) | Same root cause; privacy impact adds regulatory dimension |
| PA-002 (Deceptive Login) | TM-xxx (No Authentication) | Login form is the privacy dimension of the authentication gap |
| PA-004 (Developer PII in Swagger) | TM-xxx (Swagger exposure) | Privacy dimension of the information disclosure finding |
| PA-006 (Error Disclosure) | TM-xxx (Verbose errors) | Privacy adds the data leakage angle to the security finding |
| PA-009 (PAT in state) | TM-xxx (GitHub token exposure) | Privacy concern for the developer whose credentials are exposed |
| PA-010 (Unrestricted CORS) | TM-xxx (Wide CORS) | Privacy angle of the cross-origin access control gap |

### Framework Mapping

| Finding | GDPR | CCPA | LINDDUN | OWASP Top 10 | CWE |
|---|---|---|---|---|---|
| PA-001 | Art. 32(1)(a) | 1798.150 | Detectability, Disclosure | A02:2021 | CWE-319 |
| PA-002 | Art. 5(1)(a) | - | Unawareness | A04:2021 | CWE-1021 |
| PA-003 | Art. 13/14 | 1798.100(b) | Unawareness, Non-compliance | A04:2021 | CWE-1059 |
| PA-004 | Art. 5(1)(c) | - | Identifiability, Disclosure | A01:2021 | CWE-200 |
| PA-005 | Art. 15-22 | 1798.100-125 | Non-compliance | A04:2021 | CWE-1059 |
| PA-006 | Art. 32 | - | Disclosure | A05:2021 | CWE-209 |
| PA-007 | Art. 5(1)(c)(e), 32 | - | Linkability, Identifiability | A09:2021 | CWE-532 |
| PA-008 | Art. 28(3) | - | Non-compliance | - | - |
| PA-009 | Art. 32 | - | Identifiability | - | CWE-798 |
| PA-010 | Art. 25 | - | Disclosure | A05:2021 | CWE-942 |

---

## Execution Log

### Process Health
| Metric | Value |
|--------|-------|
| Files Read | 28 |
| Files Written | 1 |
| Errors Encountered | 0 |
| Items Skipped | 0 |
| Self-Assessed Output Quality | HIGH |

### What Went Well
- Reconnaissance document was comprehensive and well-structured, providing an excellent foundation for the privacy assessment
- Complete access to all Terraform modules, application code, and configuration files
- The demo nature of the project was clearly documented, allowing accurate contextualization of findings
- The system has a relatively small data footprint (product catalog only), making the data inventory and flow analysis straightforward
- All 14 Terraform modules, both Dockerfiles, both application codebases, and all templates were reviewed

### Issues Encountered
- No issues encountered. All files were readable and the project structure was clear.

### What Was Skipped or Incomplete
- **Runtime log analysis**: No actual CloudWatch logs were reviewed to confirm IP address logging patterns. The assessment infers Nginx IP logging from standard default behavior. Impact: Low -- Nginx default access logging is well-documented and consistently includes client IPs.
- **Browser behavior analysis**: Did not inspect actual HTTP responses for privacy-relevant headers (Cache-Control, Referrer-Policy, Permissions-Policy). Impact: Low -- the absence of TLS (PA-001) is a larger concern that subsumes header-level privacy controls.
- **npm audit / dependency privacy analysis**: Did not audit npm packages for privacy-invasive telemetry or analytics collection. Impact: Low -- no analytics or tracking libraries were identified in package.json dependencies.
- **DPIA necessity assessment**: Did not conduct a full DPIA threshold analysis per GDPR Art. 35(1). The system's limited personal data processing likely does not trigger mandatory DPIA, but this should be formally assessed if the system is extended.

### Assumptions Made
- Assumed Nginx uses default access log format (which includes `$remote_addr`) since no custom Nginx configuration was found in the client Dockerfile or codebase
- Assumed ALB access logging is not enabled since `access_logs` block is not present in the ALB Terraform resource (confirmed by absence in `Modules/ALB/main.tf`)
- Assumed the AWS DPA has not been executed since no DPA documentation was found in the repository (organizational context may differ)
- Assumed HIPAA non-applicability based on the product catalog use case and absence of health data categories
- Assumed the developer email in swagger.js (`burkhmar@amazon.de`) is real personal data belonging to the code author, consistent with the `author` field in package.json ("Marina Burkhardt")
