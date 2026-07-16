# Node-Type → Icon Vocabulary (T1-05)

The controlled, versioned map from a node's **type** to a **locally vendored SVG icon**. It is a
**fixed, closed set** with an explicit `unknown`/`other` member. The agent still chooses each node's
type; the vocabulary is the closed set those choices must come from. This is what turns "pretty" into
*consistently* pretty — the same type renders the same icon in every diagram, on either engine.

The machine-readable ground truth is [`node-type-icons.json`](./node-type-icons.json). The eval's
membership validator (`evals/reliability/diagram_checks.py::_node_type_checks`) loads that JSON and
checks every node's declared type token against it, with fuzzy-match suggestions on a miss — the
`drawio-ai-kit` `checkRef` shape (membership over the emitted facts + suggestions), engine-independent.

---

## §1 Why a closed set

- **Consistency guarantee.** Same type token → same icon across all diagrams. An open set (letting the
  agent mint types) defeats this and the grounding check, so the set is closed.
- **Grounding, not scripting.** The check counts *typed vs untyped* and *token ∈ catalog* — it never
  asserts *which* type a node ought to be. Semantic correctness ("is this really a datastore?") stays
  with `prompts/diagram-judge.md`.
- **Honest abstention.** `unknown`/`other` is a first-class *passing* member, so the agent is never
  forced to invent a type it cannot justify.

## §2 The vocabulary

Permissive/generic types (engine- and cloud-agnostic). The **Icon id** column below is the upstream
MDI source glyph (`mdi:*`); each is vendored locally as `icons/<type>.svg` — that local path is what
`node-type-icons.json` now carries and what both engines reference (§5). **No AWS/Azure/GCP brand
icons live in the core** (a licensing decision — see §5).

| Type | Icon id | Aliases (folded onto the type) | Meaning |
|------|---------|--------------------------------|---------|
| `service` | `mdi:server` | `svc` | Application, API, compute, running process-as-service |
| `process` | `mdi:cog` | — | A DFD process / transformation |
| `datastore` | `mdi:database` | `store`, `dataStore` | Database, cache, bucket, file store |
| `queue` | `mdi:tray-full` | — | Message queue / topic / event bus |
| `external-actor` | `mdi:account` | `actor`, `external`, `external-entity` | Human/third-party actor outside the trust boundary |
| `external-dep` | `mdi:package-variant` | `extdep`, `externalDep`, `external-dependency` | Third-party SaaS / API / package dependency |
| `identity` | `mdi:account-key` | `iam` | IAM role, service account, IdP |
| `secret` | `mdi:key` | `secrets`, `kms` | Vault, HSM, KMS, cert authority |
| `control` | `mdi:shield-check` | — | WAF, IDS, MFA, rate limiter |
| `pipeline` | `mdi:pipe` | `pipe` | CI/CD, container registry, build/deploy |
| `trust-boundary` | `mdi:fence` | `boundary` | Trust-zone container (VPC, subnet, tenant) |
| `gateway` | `mdi:call-split` | `decision` | Auth check / routing decision |
| `neutral` | `mdi:shape` | — | Structural default when no sharper type fits |
| **`unknown`** | `mdi:help-circle` | — | Abstention — passing member |
| **`other`** | `mdi:dots-horizontal` | — | Abstention — passing member |

**Styling classes** (accepted, non-type, need no icon): `highRisk`, `criticalRisk`, `medRisk`,
`mediumRisk`, `lowRisk`, `noFindings`, `attackPath`, `outOfScope`. These are risk-overlay/scoping
styles, not node types; the validator accepts them so an L4 `:::highRisk` node is never mis-flagged as
a hallucinated type.

The aliases fold the incumbent Mermaid `classDef` names (§3 of `mermaid-spec.md`) and the D2 POC class
names onto the same type set, so the Mermaid and D2 paths share one vocabulary.

## §3 How each engine binds a type to its icon

- **Mermaid `@{shape: icon}` path.** The node's `classDef` class *is* its type token; the icon is
  attached via the `@{shape: icon, icon: "<id>"}` node form (see `mermaid-spec.md §3`). Classical
  Mermaid nodes carry no per-node icon, so the icon-consistency check abstains on that sub-path.
- **D2 path.** Bind the icon into the `classes` block so every node of a type inherits its vendored
  icon deterministically (see `d2-spec.md §2`): `classes: { datastore: { icon: <local-path> } }`, then
  `D1: "..." { class: datastore }`. Reference icons **by local file path only** — never a remote URL
  (a 403 renders a broken icon while the CLI exits 0).

## §4 The compliance check (what the eval enforces)

Reference-free, ADVISORY (diagram layer), abstains when no type token is present:

| Check | Rule | Defect vs warning |
|-------|------|-------------------|
| `node-type-untyped` | every drawn node carries a type token | `>10%` untyped → defect, else warning (mirrors `untyped-edges`) |
| `node-type-unknown-token` | every token ∈ the catalog (name or alias) | miss → defect **with a fuzzy suggestion**; `unknown`/`other` pass |
| `icon-inconsistency` | same type token → one icon across the report | two icons for one type → defect |
| legend coverage | every used type appears in the legend | warning only |

## §5 SVG asset vendoring (DONE)

The permissive SVG set is now vendored under [`references/icons/`](./icons/) — one `<type>.svg` per
vocabulary member (15 files), sourced from **Material Design Icons** (Pictogrammers `@mdi/svg`,
**Apache-2.0**; see [`icons/LICENSE`](./icons/LICENSE) for attribution + the type→MDI-name mapping).
Each `icon` field in `node-type-icons.json` is now the **local path** `icons/<type>.svg` (relative to
this `references/` dir); **no remote URLs, no AWS/Azure/GCP brand icons**.

- **D2 path** binds each type's local icon into the `classes` block — `scripts/recon_to_d2.py` emits
  `icon: <rel-path>/<type>.svg` per used type, resolved relative to the output `.d2` (d2 resolves
  `icon:` against the `.d2` file, not the CWD) and embedded as a base64 data URI at render time (fully
  offline). A missing local icon makes `d2` fail loud (`failed to bundle local images`), so a broken
  path can never silently render blank — unlike a remote URL.
- **Mermaid path** references the same `icons/<type>.svg` via `@{shape: icon}` (mermaid-spec.md §3).

Still optional / not vendored: a per-cloud-provider logo layer (RDS/KMS/SQS) as a *separate, opt-in*
set — it improves fidelity but grows the licensing surface, so it stays out of the generic core.
