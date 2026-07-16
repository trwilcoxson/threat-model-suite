# Semantic-source spike — recon.json + typed edges → deterministic D2

**Question (from `OTM-EVAL.md`):** the boundary the owner wants — *agent emits pure meaning, a
deterministic layer owns 100% of layout & aesthetics* — comes from a **structured semantic source**,
not from OTM. `recon.json` is already that hard-gate-validated JSON; it lacks one thing: a typed-edges
array. This spike adds it and proves the render + the checks.

**Verdict: the spike proves out. Adopt it as a small openspec change.** Render quality matches the
hand-authored D2 on every axis that a deterministic *offline* pipeline can own; the checks got strictly
simpler (regex-over-a-picture → JSON reference/membership); and the extension fields are fully
back-compatible (every committed recon still conforms, `check_sample_runs` stays `32 0`).

---

## The pipeline

```
agent authors ──► recon.json                       deterministic layer owns ──► render + checks
  meaning only    { components[].type   (typed nodes)        recon_to_d2.py ──► .d2 ──d2 --layout elk──► .svg ──► .png
                    dataflows[]          (typed edges)        checks.py::recon_semantic_checks ──► JSON gate
                    elements[].zone      (containment) }
```

- **Agent side (semantic source).** Three OPTIONAL, additive fields on `recon.json`
  (`schema/recon.schema.json`):
  - `dataflows[]` — each `{id, source, destination, type(data|control|build|async|admin),
    protocol, sensitivity(PUBLIC|INTERNAL|CONFIDENTIAL|RESTRICTED), enc(ENC|PLAIN), label, evidence[]}`.
    `source`/`destination` are ids of declared elements.
  - `components[].type` — a node-type token from the vocabulary catalog (`references/node-type-icons.json`).
  - `elements[].zone` — the trust-boundary id that contains this element (a boundary whose `zone`
    points at another boundary nests inside it). This is the containment primitive the deterministic
    nesting needs; it is a natural companion to `type`, and like `type`/`dataflows` it is optional.
- **Deterministic side.** `scripts/recon_to_d2.py` reads the recon and owns **100%** of layout,
  shapes, colors, and nesting. Pure/deterministic (sorted iteration, no randomness, no network) — the
  self-check asserts byte-stability across runs. It follows `references/d2-spec.md` and emits within the
  eval-facing D2 subset (§7). The agent never writes a line of `.d2`.

## The rendered proof — `05-recon-to-d2.png` vs the hand-authored `01-d2-structural.png`

`poc/recon-with-dataflows.json` is the flagship recon (`docs/examples/amazon-ecs-fullstack-app-terraform/recon.json`)
**copied** and augmented with 26 `dataflows[]` derived edge-for-edge from `structural-diagram.mmd`,
`component.type`s, container trust-boundaries (VPC / Public / Private subnets / CI-CD plane), and
`zone` membership. (The committed flagship recon is untouched.) Then:

```bash
python3 skills/threat-model/scripts/recon_to_d2.py \
    docs/research/visual-engine-2026-07/poc/recon-with-dataflows.json \
    docs/research/visual-engine-2026-07/poc/05-recon-to-d2.d2
d2 --layout elk poc/05-recon-to-d2.d2 poc/05-recon-to-d2.svg
rsvg-convert poc/05-recon-to-d2.svg -o poc/05-recon-to-d2.png
```

| Axis | Hand-authored `01-d2-structural.png` | Generated `05-recon-to-d2.png` |
|------|--------------------------------------|--------------------------------|
| Structure / nesting | VPC → Public/Private subnets, CI-CD plane | **identical** (deterministically produced) |
| Edges | all typed, colored, annotated | **all 26**, typed/colored/annotated, full `[SENS] [ENC\|PLAIN]` labels |
| Node typing | per-node shapes + **AWS brand icons** | per-type built-in **shapes** (person/cylinder/package/parallelogram/queue) |
| Offline / deterministic | **NO** — brand icons fetched over the network at render time (violates `d2-spec.md §1`; silent 403 → broken icon) | **YES** — fully offline, byte-stable |
| Authored by | a human, by hand | the deterministic transform, from JSON |

**Honest assessment.** The generated diagram is structurally identical to the hand-authored one and
carries the *complete* annotated edge set. The one visible gap is brand-icon pixels: `01` shows AWS
service glyphs, `05` shows generic typed shapes. But `01` got those icons only by fetching remote SVGs
at render time — exactly the non-offline path `d2-spec.md §1` forbids (a 403 renders a broken icon while
the CLI exits 0). `05` is fully offline. When the vendored SVG set lands (`node-type-icons.md §5`), a
local `icon:` path drops into the transform's `classes` block per type and `05` reaches identical
fidelity — deterministically, offline, for free. Both diagrams show the same minor ELK label/border
overlaps. **Net: render quality ≥ hand-authored on every axis a deterministic offline pipeline owns.**

## The checks got strictly simpler: regex-over-a-picture → JSON reference/membership

`checks.py::recon_semantic_checks(recon)` runs inside the existing blocking gate. Each sub-check is the
JSON form of a check that previously scraped the *rendered diagram text*:

| New JSON check (`checks.py`) | Kind | Replaces (diagram-text regex) |
|------------------------------|------|-------------------------------|
| `dataflow-endpoint-integrity` — every `source`/`destination` ∈ declared element **or role** ids | id set-membership; **HARD** (consistency, gated) | `diagram_checks.analytical_checks`' *"boundary-crossing edge endpoint(s) do not map to recon ids"* — endpoints parsed out of the diagram with `_d2_edge_paths` / `_edge_endpoints`, then a `\b{id}\b` search over label cells |
| `recon-node-type-unknown` — `component.type` ∈ the catalog (fuzzy suggestion on a miss) | membership over the **same** `node-type-icons.json`; advisory (recon) | `diagram_checks._node_type_checks`' `node-type-unknown-token` — type tokens scraped from `:::class` (Mermaid) / `class:` (D2) inside the drawn nodes |
| `dataflow-ungrounded` — a flow asserted with no `evidence[]` | shape/presence; advisory (recon) | the edge analog of per-element evidence grounding (edges had *no* grounding hook before — they lived only in the picture) |

Why this is harder to fool: the endpoint/type facts are read from the **structured source the agent
committed**, not re-derived by parsing the picture the renderer drew. There is no label-quoting,
arrow-glyph-in-a-label, dotted-path, or `linkStyle`-index ambiguity to get wrong — it is `ref in ids`
and `token in catalog`. The membership check reuses the one catalog loader (`_load_vocab`) and the same
`difflib` fuzzy suggestion, so the Mermaid/D2/JSON paths share a single vocabulary.

## Back-compat (the "extension fields survive" leg)

All three fields are optional; each sub-check **abstains** when its field is absent. Evidence:

- `check_sample_runs` → **`32 0`** (every committed recon still conforms to the widened schema).
- `run.py validate` on the flagship → **PASS** (flagship has no dataflows → semantic checks inert).
- self-check `t_recon_semantic_backcompat` asserts the real committed flagship recon yields **zero**
  semantic defects.

## Self-checks (`test_checks.py`, 20 → 24)

- `t_recon_dataflow_integrity` — dangling endpoint flagged (HARD/consistency); valid endpoints
  (including a role id) pass.
- `t_recon_node_type_membership` — bad token flagged with a fuzzy suggestion; a vocabulary token and an
  alias pass; advisory layer.
- `t_recon_semantic_backcompat` — no dataflows/type ⇒ inert (incl. the real flagship, `None`, `{}`).
- `t_recon_to_d2_smoke` — the transform is byte-stable, wires nested endpoints to full dotted paths,
  emits typed/annotated labels, and produces D2 that `d2 --layout elk` parses (rc 0).

## Files

| File | Change |
|------|--------|
| `schema/recon.schema.json` | **+** optional `dataflows[]` (+ `dataflow` `$def`), `element.type`, `element.zone` |
| `scripts/recon_to_d2.py` | **new** — deterministic recon → D2 transform |
| `checks.py` | **+** `recon_semantic_checks()`, wired into `run_checks` |
| `test_checks.py` | **+** 4 self-checks |
| `poc/recon-with-dataflows.json` | **new** — flagship recon copy + 26 dataflows + types + zones |
| `poc/05-recon-to-d2.{d2,svg,png}` | **new** — the deterministic render |

## Decisions / deviations

- **Added a third optional field, `element.zone`**, beyond the `dataflows[]` + `type` the brief named.
  Nesting real trust-boundary *containers* (a required deliverable) needs per-element containment, and
  the recon model had none (its `trust_boundaries` describe crossings, not zones). `zone` is the minimal
  additive primitive; being optional, it strengthens rather than weakens the back-compat claim.
- **Typed shapes, not brand icons.** The core catalog vendors no SVGs yet (`node-type-icons.md §5`), and
  remote icon URLs break offline rendering. Shapes give offline typing now; the vendored `icon:` slot is
  already in the transform's `classes` block for when the SVG set lands.
- **Only flow participants are drawn** (no floating nodes); a trust boundary renders as a container only
  if it encloses something — so the flagship's semantic crossing-boundaries (TB1–TB6, kept in the copy)
  never render as empty boxes.
