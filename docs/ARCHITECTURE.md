# Architecture Design Document: Claude Code Threat Modeling System

## 1. Overview

This system is a structured security assessment pipeline built entirely on Claude Code primitives: **skills**, **agents**, and **reference files**. It produces architectural threat models with data flow diagrams, multi-framework threat identification, risk quantification, and consolidated multi-format reports.

The system transforms a codebase or architecture description into a comprehensive security assessment delivered in four formats (HTML, Word, PDF, PPTX) through a pipeline of specialized AI agents, each with domain-specific expertise and standardized output contracts.

### What It Produces

| Output | Description |
|--------|-------------|
| 8 phase files (`01-reconnaissance.md` through `08-threat-model-report.md`) | Structured threat model following STRIDE-LM, PASTA, and OWASP Risk Rating methodologies |
| Mermaid data flow diagrams (L1-L4) | 4-layer architecture diagrams: structural topology, trust boundaries, data classification, risk overlay |
| `privacy-assessment.md` | LINDDUN privacy impact assessment with regulatory analysis (team mode) |
| `compliance-gap-analysis.md` | Multi-framework compliance mapping and gap analysis (team mode) |
| `code-security-review.md` | CVSS-scored code-level vulnerability findings (team mode) |
| `validation-report.md` | Cross-agent deduplication, consistency checks, framework ID verification (team mode) |
| `report.html` | Interactive web report with inline Mermaid rendering, filtering, zoom/pan |
| `report.docx` | Professional Word document with TOC, cover page, embedded diagram PNGs |
| `report.pdf` | Print-ready PDF |
| `executive-summary.pptx` | 9-11 slide executive presentation with severity charts and diagram embeds |

### What It's Good For

- **Pre-launch security reviews**: Comprehensive assessment before deploying to production
- **Architecture design reviews**: Evaluate security posture of proposed designs before implementation
- **Compliance readiness**: Map controls to SOC 2, PCI-DSS, HIPAA, ISO 27001, NIST CSF
- **Due diligence**: Structured security assessment for M&A, vendor evaluation, or audit preparation
- **Threat modeling as code**: Repeatable, version-controlled security analysis that evolves with the codebase

---

## 2. System Architecture

### Core Principle: Flat Orchestration

All agents are spawned as **flat peers by the parent conversation**. No agent spawns other agents. The parent conversation reads the skill file (SKILL.md), which contains the orchestration logic, and uses its full tool access (Task, TaskOutput, etc.) to manage the pipeline.

```mermaid
flowchart TB
    User(["User: Run a threat model"])

    subgraph Parent["Parent Conversation — Full Tool Access"]
        direction TB
        SKILL["<b>SKILL.md</b><br/>Orchestration Guide<br/>+ 8-Phase Methodology"]
        Decide{"Solo or<br/>Team?"}
        SKILL --> Decide
    end

    subgraph Core["Core Pipeline — Sequential"]
        direction LR
        SA["<b>security-architect</b><br/><i>Phase 1, 3-6, 8s</i><br/>STRIDE-LM, PASTA"]
        DS["<b>diagram-specialist</b><br/><i>Phases 2, 7</i><br/>Mermaid DFDs"]
    end

    subgraph Specialists["Specialist Agents — Parallel (Team only)"]
        direction LR
        PA["<b>privacy-agent</b><br/><i>PIA, LINDDUN</i><br/>GDPR, CCPA, HIPAA"]
        GRC["<b>grc-agent</b><br/><i>Compliance Mapping</i><br/>SOC 2, PCI-DSS, NIST"]
        CR["<b>code-review-agent</b><br/><i>CVSS v3.1</i><br/>Code Evidence"]
    end

    subgraph PostProcess["Post-Processing — Sequential"]
        direction LR
        VS["<b>validation-specialist</b><br/><i>Deduplication</i><br/>Framework ID Verify<br/>Severity Consistency"]
        RA["<b>report-analyst</b><br/><i>QA Review</i><br/>HTML, DOCX, PDF, PPTX"]
        VS --> RA
    end

    subgraph FS["Shared Filesystem: threat-model-output/"]
        direction LR
        Phases["01-08<br/>Phase Files"]
        TeamOut["privacy-assessment.md<br/>compliance-gap-analysis.md<br/>code-security-review.md"]
        ValOut["validation-report.md"]
        Reports["report.html<br/>report.docx<br/>report.pdf<br/>executive-summary.pptx"]
    end

    subgraph Refs["Reference Files — Institutional Knowledge"]
        direction LR
        R1["<b>frameworks.md</b><br/>STRIDE-LM, MITRE<br/>CWE, OWASP"]
        R2["<b>mermaid-spec.md</b><br/>+ 4 diagram refs"]
        R3["<b>report-template.md</b><br/>Sections I-XIV"]
        R4["<b>agent-output-</b><br/><b>protocol.md</b>"]
    end

    User --> Parent
    Parent -->|"spawns core agents"| Core
    Parent -->|"spawns specialists"| Specialists
    Parent -->|"spawns sequentially"| PostProcess
    Core -->|"write"| FS
    Specialists -->|"write"| FS
    PostProcess -->|"read all, write"| FS
    SA -.->|"consult"| R1
    DS -.->|"consult"| R2
    Specialists -.->|"consult"| Refs
    RA -.->|"consult"| R3
    PostProcess -.->|"consult"| Refs

    classDef parent fill:#dbeafe,stroke:#3b82f6,stroke-width:2px,color:#1e3a5f
    classDef agent fill:#f0fdf4,stroke:#22c55e,stroke-width:1.5px,color:#14532d
    classDef diagram fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px,color:#0c4a6e
    classDef post fill:#fef3c7,stroke:#f59e0b,stroke-width:1.5px,color:#78350f
    classDef fs fill:#f3e8ff,stroke:#a855f7,stroke-width:1.5px,color:#581c87
    classDef ref fill:#fff1f2,stroke:#f43f5e,stroke-width:1px,color:#881337
    classDef user fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0c4a6e

    class Parent parent
    class SA,PA,GRC,CR agent
    class DS diagram
    class VS,RA post
    class FS,Phases,TeamOut,ValOut,Reports fs
    class Refs,R1,R2,R3,R4 ref
    class User user
```

<details>
<summary>PNG fallback (if Mermaid doesn't render)</summary>

![System Architecture](diagrams/system-architecture.png)
</details>

### Component Inventory

| Component | Type | Claude Code Primitive | Built-in Agent Type | Purpose |
|-----------|------|----------------------|--------------------|---------|
| `SKILL.md` | Skill | `~/.claude/skills/threat-model/SKILL.md` | N/A | 8-phase threat model methodology + orchestration guide |
| `security-architect` | Agent | `~/.claude/agents/security-architect.md` | `security-architect` | Executes Phase 1 (recon), Phases 3-6 (analysis), Phase 8 (summary) |
| `diagram-specialist` | Agent | `~/.claude/agents/diagram-specialist.md` | `security-architect` | Executes Phase 2 (structural DFDs) and Phase 7 (risk overlay) |
| `privacy-agent` | Agent | `~/.claude/agents/privacy-agent.md` | `privacy-agent` | Privacy impact assessment |
| `grc-agent` | Agent | `~/.claude/agents/grc-agent.md` | `grc-agent` | Compliance gap analysis |
| `code-review-agent` | Agent | `~/.claude/agents/code-review-agent.md` | `code-review-agent` | Code-level vulnerability analysis |
| `validation-specialist` | Agent | `~/.claude/agents/validation-specialist.md` | None (spawned as `general-purpose`) | Cross-agent validation and deduplication |
| `report-analyst` | Agent | `~/.claude/agents/report-analyst.md` | `report-analyst` | QA review + 4-format report generation |
| 11 reference files | Reference | `references/*.md` + `mermaid-config.json` | N/A | Frameworks, checklists, diagram specs, report template |

### Two Execution Modes

**Solo Mode** — for small, focused systems:
```
Parent → security-architect (Phase 1)
       → diagram-specialist (Phase 2)
       → security-architect (Phases 3-6, 8 summary)
       → diagram-specialist (Phase 7)
       → report-analyst (blocking)
```

**Team Mode** — for complex systems (default):
```
Parent → security-architect (Phase 1)
       → diagram-specialist (Phase 2)
       → security-architect (Phases 3-6, 8 summary)
       → diagram-specialist (Phase 7)
       → privacy-agent + grc-agent + code-review-agent (parallel, background)
       → wait for all 3
       → validation-specialist (blocking)
       → report-analyst (blocking)
```

The mode is selected by the parent based on system characteristics discovered during lightweight reconnaissance (see SKILL.md § "Solo vs Team Decision").

---

## 3. How It Works Technically

### 3.1 Invocation

The user asks for a threat model or security assessment. The parent conversation loads the `threat-model` skill, which injects SKILL.md into the parent's context. The parent then follows the orchestration instructions.

```
User: "Run a threat model on this project"
  → Parent loads SKILL.md
  → Parent does lightweight recon (Glob/Grep for IaC, APIs, data stores)
  → Parent decides solo vs team
  → Parent spawns agents sequentially/parallel per workflow
```

### 3.2 Agent Spawning

Each agent is spawned via the `Task` tool with specific parameters:

```
Task(
  subagent_type: "security-architect",    // built-in agent type
  name: "threat-modeler",                 // display name
  prompt: "Execute all 8 phases...",      // instructions + paths
  run_in_background: false                // blocking (or true for parallel)
)
```

The agent's `.md` file (in `~/.claude/agents/`) customizes the built-in type with domain-specific instructions, personality, model selection, and skill access.

### 3.3 Inter-Agent Communication

Agents do **not** communicate with each other directly. All coordination happens through the **shared filesystem**:

```
{project_root}/threat-model-output/
├── 01-reconnaissance.md          ← security-architect writes
├── 02-structural-diagram.md      ← security-architect writes
├── ...
├── 08-threat-model-report.md     ← security-architect writes
├── privacy-assessment.md         ← privacy-agent reads 01, writes this
├── compliance-gap-analysis.md    ← grc-agent reads 01, writes this
├── code-security-review.md       ← code-review-agent reads 01, writes this
├── validation-report.md          ← validation-specialist reads all, writes this
├── consolidated-report.md        ← report-analyst reads all, writes this
├── report.html                   ← report-analyst generates
├── report.docx                   ← report-analyst generates
├── report.pdf                    ← report-analyst generates
└── executive-summary.pptx        ← report-analyst generates
```

This design is intentional — see § 4.3 for justification.

### 3.4 The Agent Output Protocol

All specialist agents follow a standardized output format defined in `references/agent-output-protocol.md`. This contract ensures downstream agents (validation-specialist, report-analyst) can reliably parse and cross-reference outputs.

Key elements:
- **Structured metadata block** (agent name, date, scope, methodology, scoring system)
- **Prefixed finding IDs** (`TM-001`, `CR-001`, `PA-001`, `GRC-001`) for cross-referencing
- **Standardized finding format** (severity, confidence, affected components, cross-framework IDs, evidence, attack scenario, recommendation)
- **Scoring system preservation** — OWASP Risk Rating (threat model), CVSS v3.1 (code review), and qualitative (GRC) are never converted between each other

### 3.5 The Reference File System

The skill carries 11 reference files that provide deterministic, verifiable foundations:

| File | Role |
|------|------|
| `frameworks.md` | Canonical STRIDE-LM, PASTA, MITRE ATT&CK, CWE, OWASP definitions and lookup tables |
| `analysis-checklists.md` | Per-phase completeness checklists |
| `mermaid-spec.md` | Symbol taxonomy, typed edges, classDefs, annotation format |
| `mermaid-layers.md` | 4-layer separation (L1 Architecture → L4 Threat Overlay) |
| `mermaid-diagrams.md` | Companion diagram types (attack trees, auth sequences) |
| `mermaid-templates.md` | Copy-paste starter templates for common architectures |
| `mermaid-review-checklist.md` | Pre-submission diagram quality gates |
| `mermaid-config.json` | Rendering configuration (fonts, spacing, curves) for consistent output |
| `visual-completeness-checklist.md` | 26-category coverage tracker for diagram completeness |
| `report-template.md` | Canonical report structure (sections I-XIV) |
| `agent-output-protocol.md` | Standardized finding format for all agents |

These files serve as the system's **institutional knowledge** — they prevent hallucination of framework IDs, enforce consistent diagram conventions, and ensure report structure is deterministic across runs.

### 3.6 Report Generation Pipeline

The report-analyst executes a 3-step pipeline:

```
Step 1: QA Pass
  Read all phase files + team outputs
  Validate: structure, finding counts, framework IDs, cross-references
  Fix critical issues inline

Step 2: Consolidation
  Deduplicate findings across agents (component + CWE matching)
  Cross-key everything (findings ↔ diagrams ↔ remediation ↔ components)
  Produce consolidated-report.md following report-template.md exactly

Step 2.5: Render Diagram PNGs
  Extract Mermaid code from phase files → .mmd files
  Pre-process (strip invalid syntax like ~~> arrows)
  Render via: npx @mermaid-js/mermaid-cli -i file.mmd -o file.png
  Verify PNGs are >100 bytes (not placeholder stubs)

Step 3: Multi-Format Generation
  HTML:  Single-file interactive report with live Mermaid rendering, zoom/pan
  DOCX:  python-docx with TOC, cover page, embedded PNGs on landscape pages
  PDF:   Convert from DOCX via LibreOffice or generate with ReportLab
  PPTX:  python-pptx executive presentation with severity charts + diagram embeds
```

---

## 4. Design Decisions and Justifications

### 4.1 Why Flat Orchestration (Not Nested Agent Spawning)

**Decision**: The parent conversation spawns all agents. No agent spawns other agents.

**Constraint discovered**: Claude Code custom agents (defined in `~/.claude/agents/`) can customize description, model, color, memory, and skills for built-in agent types, but **cannot add tools** beyond the built-in type's set. The `tools:` frontmatter field only **restricts** — it never expands.

The built-in `security-architect` type has 6 tools: Bash, Read, Write, Edit, Grep, Glob. Listing Task, TeamCreate, or SendMessage in its frontmatter was silently ignored. The agent literally could not spawn subagents.

**Additional constraint**: The `validation-specialist` has no built-in agent type counterpart. It cannot be spawned as `subagent_type: "validation-specialist"` — it must be spawned as `general-purpose` with custom instructions pointing to its `.md` file.

**Resolution**: Move all orchestration logic to SKILL.md, which runs in the parent conversation. The parent has access to all tools. Every agent becomes a focused specialist that reads inputs, does its work, and writes outputs.

**Benefit**: This architecture is actually cleaner than nested spawning. Every agent is visible to the user. There's no hidden orchestration happening inside an agent. The pipeline is transparent and debuggable.

### 4.2 Why a Skill (Not Just an Agent)

**Decision**: The threat modeling methodology lives in a skill (`SKILL.md`), not embedded in the security-architect agent.

**Justification**:
- **Separation of concerns**: The methodology (8 phases, reference files, checklists) is distinct from the agent's personality and capabilities. The skill defines *what* to do; the agent defines *who* does it.
- **Reusability**: The skill could theoretically be attached to different agents or invoked in different contexts.
- **Context injection**: Skills are loaded into the parent conversation's context, giving the parent access to the orchestration logic and reference file paths. An agent's instructions only affect that agent — they can't guide the parent.
- **Reference file co-location**: The skill carries 11 reference files in its `references/` directory. These are domain knowledge (framework definitions, diagram specs, report templates) that multiple agents need. Co-locating them with the skill keeps the knowledge graph coherent.

### 4.3 Why Filesystem-Based Communication (Not Message Passing)

**Decision**: Agents communicate through shared files in `{output_dir}/`, not through SendMessage or other IPC mechanisms.

**Justification**:
- **Tool constraints**: Most built-in agent types don't have SendMessage. Filesystem I/O (Read/Write) is universally available.
- **Auditability**: Every intermediate artifact is a readable markdown file on disk. The user can inspect, edit, or re-run any stage.
- **Idempotency**: If an agent fails, its output file is either absent (re-run) or partially written (inspect and decide). There's no hidden message queue state.
- **Context preservation**: Agents can read as much or as little of the prior outputs as they need. The validation-specialist reads everything; the privacy-agent only reads `01-reconnaissance.md`.
- **Debugging**: When something goes wrong, you can `ls` the output directory and see exactly which stages completed and what they produced.

### 4.4 Why Sequential Threat Modeling Before Parallel Specialists

**Decision**: The security-architect runs all 8 phases to completion before any specialist agents start.

**Justification**:
- **Dependency**: All specialists depend on `01-reconnaissance.md` for system context (components, data flows, technology stack, threat actors). They need the full picture before doing domain-specific analysis.
- **Phase integrity**: The 8 phases are designed as a sequential cognitive pipeline — each phase builds on the previous. Phase 3 (Threat Identification) reads Phase 2 (Structural Diagram). Phase 4 (Risk Quantification) reads Phase 3. Breaking this sequence would compromise quality.
- **Parallel specialists are independent**: Once reconnaissance is complete, privacy, compliance, and code review are genuinely independent — they analyze different aspects of the same system. Running them in parallel is safe and efficient.

### 4.5 Why a Separate Validation Step

**Decision**: A dedicated validation-specialist runs between the specialists and the report-analyst.

**Justification**:
- **Cross-agent deduplication**: The same vulnerability often appears in multiple agent outputs with different terminology (e.g., "weak password hashing" from code review = "password storage" from privacy = "CWE-327" from architecture). Without deduplication, the final report would contain redundant findings.
- **Framework ID verification**: LLMs hallucinate MITRE ATT&CK and CWE IDs. A dedicated verification step cross-references every cited ID against the canonical tables in `references/frameworks.md`.
- **Severity consistency**: Different agents may rate the same issue differently. The validation step detects and documents these conflicts so the report-analyst can resolve them.
- **Quality gate**: The validation-specialist is the "QA before QA" — it catches issues that would otherwise require the report-analyst to do detective work during consolidation.

### 4.6 Why `general-purpose` for the Validation Specialist

**Decision**: The validation-specialist is spawned as `subagent_type: "general-purpose"` rather than a custom agent type.

**Constraint**: Claude Code only allows spawning agents whose `subagent_type` matches a built-in agent type. There is no built-in `validation-specialist` type. Attempting to spawn it as its custom type silently fails.

**Resolution**: Spawn as `general-purpose` (which has access to all tools) and pass custom instructions in the prompt that point to the agent's `.md` file: "Read your full instructions from `/path/to/validation-specialist.md`".

**Trade-off**: The agent doesn't get automatic loading of its `.md` file — it must explicitly read it. But it gains access to all tools, which is more than adequate for validation work (Read, Write, Grep, Glob, Bash).

### 4.7 Why 11 Reference Files (Not Inline Instructions)

**Decision**: Domain knowledge lives in standalone reference files, not embedded in agent instructions or the skill file.

**Justification**:
- **Token efficiency**: Reference files are loaded on demand. An agent only reads the files it needs. Embedding everything in instructions would bloat every agent's context.
- **Single source of truth**: Framework definitions, diagram conventions, and report structure are defined once and referenced by all agents. Changes propagate automatically.
- **Verifiability**: Framework IDs can be checked against the reference tables. If `frameworks.md` says CWE-89 is SQL Injection, and an agent cites CWE-89 for an XSS finding, the validation-specialist can catch the misattribution.
- **Modularity**: The Mermaid diagram system is split into 5 files (spec, layers, diagrams, templates, review checklist) because each serves a different purpose at a different phase. The spec defines *what* to draw. The layers define *when* to draw it. The templates provide *starting points*. The review checklist validates *correctness*.

### 4.8 Why Four Report Formats

**Decision**: Every assessment produces HTML, DOCX, PDF, and PPTX.

**Justification**: Different stakeholders consume security reports differently:
- **Engineers** want the interactive HTML report — they can filter findings, click through cross-references, and zoom into diagrams.
- **Security teams** want the Word document — they can edit it, add annotations, and include it in their own documentation.
- **Executives** want the PPTX — a 10-slide deck they can present in a meeting.
- **Compliance/audit** wants the PDF — an immutable, distributable record.

Generating all four from the same consolidated source ensures consistency across formats.

---

## 5. File Layout and Component Relationships

```mermaid
flowchart LR
    subgraph Skill["Skill: threat-model"]
        direction TB
        SKILL["<b>SKILL.md</b><br/>8 phases + orchestration"]

        subgraph RefFiles["references/ — 11 files"]
            direction TB
            FW["<b>frameworks.md</b><br/>STRIDE-LM, PASTA, MITRE,<br/>CWE, OWASP lookups"]
            AOP["<b>agent-output-protocol.md</b><br/>Standardized finding format"]
            RT["<b>report-template.md</b><br/>Sections I-XIV structure"]
            AC["<b>analysis-checklists.md</b><br/>Per-phase completeness"]
            VCC["<b>visual-completeness-checklist.md</b><br/>26 diagram categories"]

            subgraph MermaidRefs["Mermaid Diagram System — 6 files"]
                direction LR
                MS["mermaid-spec.md<br/><i>Symbols, edges, classDefs</i>"]
                ML["mermaid-layers.md<br/><i>4-layer separation</i>"]
                MD["mermaid-diagrams.md<br/><i>Attack trees, auth seq</i>"]
                MT["mermaid-templates.md<br/><i>Starter patterns</i>"]
                MRC["mermaid-review-checklist.md"]
                MC["mermaid-config.json<br/><i>Rendering theme</i>"]
            end
        end
    end

    subgraph Agents["Agent Definitions — ~/.claude/agents/"]
        direction TB
        SA["<b>security-architect.md</b><br/>Type: security-architect<br/>Phases: 1, 3-6, 8s<br/>Skills: threat-model"]
        DS["<b>diagram-specialist.md</b><br/>Type: security-architect<br/>Phases: 2, 7<br/>Skills: threat-model"]
        RA["<b>report-analyst.md</b><br/>Type: report-analyst<br/>Skills: docx, pdf, pptx, frontend-design"]
        CR["<b>code-review-agent.md</b><br/>Type: code-review-agent"]
        PA["<b>privacy-agent.md</b><br/>Type: privacy-agent"]
        GRC["<b>grc-agent.md</b><br/>Type: grc-agent"]
        VS["<b>validation-specialist.md</b><br/><i>No built-in type</i><br/>Spawned as: general-purpose"]
    end

    subgraph Output["Output: threat-model-output/"]
        direction TB
        P["<b>8 Phase Files</b><br/>01-reconnaissance.md<br/>through<br/>08-threat-model-report.md"]
        T["<b>Team Outputs</b><br/>privacy-assessment.md<br/>compliance-gap-analysis.md<br/>code-security-review.md<br/>validation-report.md"]
        R["<b>Report Deliverables</b><br/>report.html<br/>report.docx<br/>report.pdf<br/>executive-summary.pptx"]
    end

    SA -->|"writes 01, 03-06, 08"| P
    DS -->|"writes 02, 07"| P
    PA -->|"writes"| T
    GRC -->|"writes"| T
    CR -->|"writes"| T
    VS -->|"writes"| T
    RA -->|"generates"| R

    SA -.->|"follows"| SKILL
    SA -.->|"consults"| FW
    DS -.->|"consults"| MermaidRefs
    DS -.->|"consults"| VCC
    RA -.->|"follows"| RT
    VS -.->|"verifies against"| FW
    VS -.->|"checks"| AOP

    classDef skill fill:#dbeafe,stroke:#3b82f6,stroke-width:2px,color:#1e3a5f
    classDef ref fill:#fff1f2,stroke:#f43f5e,stroke-width:1px,color:#881337
    classDef mermaid fill:#fce7f3,stroke:#ec4899,stroke-width:1px,color:#831843
    classDef agent fill:#f0fdf4,stroke:#22c55e,stroke-width:1.5px,color:#14532d
    classDef diagram fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px,color:#0c4a6e
    classDef special fill:#fef3c7,stroke:#f59e0b,stroke-width:1.5px,color:#78350f
    classDef output fill:#f3e8ff,stroke:#a855f7,stroke-width:1.5px,color:#581c87

    class Skill skill
    class RefFiles,FW,AOP,RT,AC,VCC ref
    class MermaidRefs,MS,ML,MD,MT,MRC,MC mermaid
    class SA,RA,CR,PA,GRC agent
    class DS diagram
    class VS special
    class Output,P,T,R output
```

<details>
<summary>PNG fallback (if Mermaid doesn't render)</summary>

![Component Map](diagrams/component-map.png)
</details>

### Directory Tree

```
~/.claude/
├── agents/
│   ├── security-architect.md        # Threat model analysis: Phases 1, 3-6, 8 (6 tools)
│   ├── diagram-specialist.md        # Mermaid DFDs: Phases 2, 7 (6 tools)
│   ├── report-analyst.md            # QA + 4-format report generation
│   ├── code-review-agent.md         # Code-level vulnerability analysis
│   ├── privacy-agent.md             # Privacy impact assessment
│   ├── grc-agent.md                 # Governance, risk & compliance
│   ├── validation-specialist.md     # Cross-agent validation (spawned as general-purpose)
│   └── security-reviewer.md         # Standalone code security review
│
└── skills/
    └── threat-model/
        ├── SKILL.md                 # Methodology (8 phases) + orchestration guide
        └── references/
            ├── frameworks.md            # STRIDE-LM, PASTA, MITRE, CWE, OWASP definitions
            ├── analysis-checklists.md   # Per-phase completeness checklists
            ├── agent-output-protocol.md # Standardized finding format for all agents
            ├── report-template.md       # Canonical report structure (sections I-XIV)
            ├── mermaid-spec.md          # Symbol taxonomy, edges, classDefs, annotations
            ├── mermaid-layers.md        # 4-layer diagram separation rules
            ├── mermaid-diagrams.md      # Companion diagram types (attack trees, sequences)
            ├── mermaid-templates.md     # Starter templates for common architectures
            ├── mermaid-review-checklist.md  # Diagram quality gates
            ├── mermaid-config.json      # Rendering config (fonts, spacing, curves)
            └── visual-completeness-checklist.md  # 26-category diagram coverage tracker
```

---

## 6. Data Flow

### Both Paths (Solo + Team)

```mermaid
flowchart TD
    Start(["User Request"]) --> Recon["Parent does lightweight recon<br/><i>Glob/Grep for IaC, APIs, data stores</i>"]
    Recon --> Mode{"Solo or Team?"}

    Mode -->|"Small system,<br/>no sensitive data,<br/>no IaC"| Solo_SA1["<b>security-architect</b><br/><i>blocking</i><br/>Phase 1 only"]
    Solo_SA1 -->|"01-reconnaissance.md"| Solo_DS1["<b>diagram-specialist</b><br/><i>blocking</i><br/>Phase 2: structural DFDs"]
    Solo_DS1 -->|"02-structural-diagram.md"| Solo_SA2["<b>security-architect</b><br/><i>blocking</i><br/>Phases 3-6, 8 summary"]
    Solo_SA2 -->|"03-06.md, 08.md"| Solo_DS2["<b>diagram-specialist</b><br/><i>blocking</i><br/>Phase 7: risk overlay"]
    Solo_DS2 -->|"07-final-diagram.md"| Solo_RA["<b>report-analyst</b><br/><i>blocking</i><br/>QA + Generate 4 formats"]
    Solo_RA --> Solo_Done(["Solo Complete<br/><b>report.html, .docx, .pdf, .pptx</b>"])

    Mode -->|"Complex system,<br/>PII/PHI, cloud IaC,<br/>compliance needs"| Team_SA1["<b>security-architect</b><br/><i>blocking</i><br/>Phase 1 only"]

    Team_SA1 -->|"01-reconnaissance.md"| Team_DS1["<b>diagram-specialist</b><br/><i>blocking</i><br/>Phase 2: structural DFDs"]
    Team_DS1 -->|"02-structural-diagram.md"| Team_SA2["<b>security-architect</b><br/><i>blocking</i><br/>Phases 3-6, 8 summary"]
    Team_SA2 -->|"03-06.md, 08.md"| Team_DS2["<b>diagram-specialist</b><br/><i>blocking</i><br/>Phase 7: risk overlay"]

    Team_DS2 -->|"07-final-diagram.md"| Fork["Parent spawns<br/>3 agents in parallel"]

    Fork --> PA["<b>privacy-agent</b><br/><i>background</i>"]
    Fork --> GRC["<b>grc-agent</b><br/><i>background</i>"]
    Fork --> CR["<b>code-review-agent</b><br/><i>background</i>"]

    PA -->|"privacy-assessment.md"| Join["Parent waits for all 3<br/><i>TaskOutput, block=true</i>"]
    GRC -->|"compliance-gap-analysis.md"| Join
    CR -->|"code-security-review.md"| Join

    Join --> VS["<b>validation-specialist</b><br/><i>blocking, as general-purpose</i><br/>Dedup, verify IDs,<br/>severity consistency"]

    VS -->|"validation-report.md"| Team_RA["<b>report-analyst</b><br/><i>blocking</i><br/>QA + Consolidate +<br/>Generate 4 formats"]

    Team_RA --> Team_Done(["Team Complete<br/><b>report.html, .docx, .pdf, .pptx</b>"])

    Solo_Done --> Verify["Parent verifies all files<br/>exist and are non-empty"]
    Team_Done --> Verify

    classDef start fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0c4a6e
    classDef decision fill:#fef3c7,stroke:#f59e0b,stroke-width:2px,color:#78350f
    classDef agent fill:#f0fdf4,stroke:#22c55e,stroke-width:1.5px,color:#14532d
    classDef diagram fill:#e0f2fe,stroke:#0284c7,stroke-width:1.5px,color:#0c4a6e
    classDef post fill:#fef3c7,stroke:#f59e0b,stroke-width:1.5px,color:#78350f
    classDef control fill:#f3e8ff,stroke:#a855f7,stroke-width:1.5px,color:#581c87

    class Start,Solo_Done,Team_Done,Verify start
    class Mode decision
    class Solo_SA1,Solo_SA2,Team_SA1,Team_SA2,PA,GRC,CR,Solo_RA,Team_RA agent
    class Solo_DS1,Solo_DS2,Team_DS1,Team_DS2 diagram
    class Fork,Join control
    class VS post
```

<details>
<summary>PNG fallback (if Mermaid doesn't render)</summary>

![Pipeline Flow](diagrams/pipeline-flow.png)
</details>

---

## 7. Scaling Model

The system adapts analysis depth to system complexity:

| System Size | Components | Diagram Strategy | Phase Adjustments |
|-------------|-----------|-----------------|-------------------|
| Small | ≤5 | 2-layer (L1+L4) | Lightweight recon, 1-2 kill chains, combined report sections |
| Medium | 6-20 | Full 4-layer (L1-L4) | Standard depth, group STRIDE-LM by trust zone |
| Large | >20 | 4-layer + sub-diagrams | Per-zone diagrams, batched threat identification, 5+ kill chains |

The scaling rules are defined in SKILL.md § "Scaling Guidelines" and enforced through the Mermaid layer strategy in `references/mermaid-layers.md`.

---

## 8. Constraints and Limitations

### Claude Code Platform Constraints

| Constraint | Impact | Mitigation |
|-----------|--------|------------|
| Custom agents cannot add tools beyond built-in set | No nested agent spawning | Flat orchestration in SKILL.md |
| Custom-only agents (no built-in type) can't be spawned by name | validation-specialist requires workaround | Spawn as `general-purpose` with custom prompt |
| `tools:` frontmatter only restricts, never expands | Listed tools silently ignored if not in built-in set | Only list tools that exist in the built-in type |
| Agent context windows are independent | Each agent starts fresh — no shared memory | Filesystem-based communication via output files |
| Mermaid rendering requires Node.js | `npx @mermaid-js/mermaid-cli` must be available | Documented as prerequisite |
| macOS managed Python (PEP 668) | `pip install` fails outside venv | All Python usage wrapped in `python3 -m venv` |

### Methodology Limitations

- **Framework ID accuracy**: Despite reference table verification, IDs are only as accurate as the reference file. The `frameworks.md` file covers common IDs but is not exhaustive.
- **Scoring system incompatibility**: OWASP Risk Rating (1-25), CVSS v3.1 (0-10), and qualitative scales cannot be meaningfully compared. The system preserves original scores rather than converting.
- **Diagram complexity ceiling**: Mermaid flowcharts become unreadable beyond ~30-40 nodes. Large systems require sub-diagrams, which add complexity to cross-referencing.
- **Single-pass analysis**: Each agent analyzes independently. There is no iterative refinement loop where findings from one agent inform another's analysis (except through the validation step).

---

## 9. Security Considerations

This system analyzes security — it should also be secure in its operation:

- **No secrets in outputs**: Agents are instructed to never include actual credentials, API keys, or secrets in findings — only references to their locations.
- **Local execution**: All processing happens locally through Claude Code. No data is sent to external services beyond the Claude API itself.
- **File-scoped outputs**: All outputs go to a single `{output_dir}/` directory that the user controls. No files are written elsewhere.
- **No network access by agents**: Agents interact only with the local filesystem (Read, Write, Grep, Glob, Bash). They do not make HTTP requests or access external services.

---

## 10. Evolution History

| Version | Change | Motivation |
|---------|--------|------------|
| v1 | Monolithic security-architect with embedded team orchestration | Initial design — agent does everything |
| v2 | Added validation-specialist, agent-output-protocol, reference files | Quality problems: duplicate findings, hallucinated IDs, inconsistent severity |
| v3 | Split Mermaid conventions into 5 modular files | Single file was too large and mixed concerns (what vs when vs how) |
| v4 | **Flat orchestration restructure** — moved team coordination from agent to SKILL.md | Discovered custom agents cannot add tools beyond built-in set. Entire team orchestration was silently broken. |
| v5 | **Diagram-specialist extraction** — split Phases 2,7 into diagram-specialist; slimmed Phase 8 to summary-only | Context rot: security-architect accumulated ~137K tokens by Phase 7-8. Extracting diagrams removes ~38K tokens of Mermaid refs, reducing peak context to ~80-90K. |

The current architecture (v5) extracts diagram production into a dedicated agent, reducing the security-architect's context window by ~35-42%. The flat orchestration model from v4 made this split trivial — no agent-to-agent communication changes were needed, only new spawn points in SKILL.md.
