## ADDED Requirements

### Requirement: D2 is the flagship diagram-as-code engine
The skill SHALL author its structural (L1-L3), risk-overlay (L4), and SBOM/dependency diagrams as
declarative D2 (`.d2`) source, rendered offline to SVG by the pinned `d2` CLI. The agent SHALL write the
D2 source; no deterministic layer SHALL infer, lay out, or edit diagram content — the renderer and
layout engine SHALL only place and rasterize what the agent declared.

#### Scenario: Structural diagram authored in D2
- **WHEN** Phase 2 produces the structural data-flow diagram
- **THEN** it is emitted as `.d2` source in the phase output and rendered to SVG with no network fetch

#### Scenario: Agent owns all content
- **WHEN** the D2 source is rendered
- **THEN** the renderer and layout engine add no nodes, edges, annotations, or coordinates beyond what
  the agent declared in the source

### Requirement: Mermaid icon-shape plus ELK is the phase-1 legibility path
The skill SHALL support a Mermaid path that adds a per-node-type icon via the `flowchart`
`@{shape: icon}` node form and ELK layout while preserving `flowchart` / `-->` / `subgraph` / `classDef`
/ `:::` syntax verbatim, so the existing diagram eval requires no change on this path. The
`architecture-beta` diagram type SHALL NOT be used, because its `group`/`service`/`edge` syntax omits the
tokens the eval and the diagram spec require.

#### Scenario: Icons without an eval change
- **WHEN** a diagram is authored on the Mermaid path with `@{shape: icon}` nodes
- **THEN** every `-->`, `subgraph`, `classDef`, and `:::` token the eval parses is still present and the
  eval verdict is unchanged from the equivalent pre-icon diagram

#### Scenario: architecture-beta rejected
- **WHEN** a diagram is written using `architecture-beta`
- **THEN** it is rejected as non-conformant because it omits the `-->` / `subgraph` / `classDef` tokens
  the eval and spec require

### Requirement: A controlled node-type to icon vocabulary
The skill SHALL ship a versioned map from node type (for example service, datastore, queue,
external-actor, secret, boundary, plus cloud-provider logos) to a locally vendored SVG icon. The agent
SHALL choose each node's type; the vocabulary SHALL be a fixed, closed set that includes an explicit
`unknown`/`other` member so the agent is never forced to invent a type it cannot justify.

#### Scenario: Type drawn from the vocabulary
- **WHEN** the agent assigns a type to a node
- **THEN** the type token is one of the controlled vocabulary members and resolves to a vendored local
  icon path

#### Scenario: Honest abstention on type
- **WHEN** the agent cannot justify a specific type for a node
- **THEN** it may type the node `unknown`/`other` and the node is still valid

### Requirement: Renders are hermetic, offline, and deterministic
Diagram rendering SHALL reference only locally vendored icon files, SHALL pin the engine version, and
SHALL use a free, offline, deterministic auto-layout (ELK or dagre). It SHALL NOT reference a remote
icon URL and SHALL NOT use a proprietary, watermarked, or network-dependent layout (TALA). Re-rendering
the same source with the same pinned toolchain SHALL produce the same diagram.

#### Scenario: No network at render time
- **WHEN** a diagram is rendered with the network unavailable
- **THEN** it renders successfully because every icon is a local file and the layout engine runs locally

#### Scenario: Remote icon reference rejected
- **WHEN** diagram source references a remote icon URL
- **THEN** it is rejected, because a remote reference breaks offline rendering and can silently render a
  broken icon while the CLI exits successfully

#### Scenario: Deterministic auto-layout
- **WHEN** a dense data-flow diagram is laid out
- **THEN** ELK (or dagre) places it deterministically with no manual coordinate nudging, so the same
  source yields the same layout

### Requirement: Mermaid remains an accepted input in a mixed-engine suite
The renderer and the eval SHALL continue to accept Mermaid (`.mmd`) source throughout the migration,
dispatching by the declared engine (fence or file extension). Sequence diagrams (authentication flows)
SHALL remain Mermaid, which provides the `alt`/`opt` fragment primitives D2 lacks. Committed `.mmd`
worked-example artifacts SHALL keep rendering.

#### Scenario: Mixed-engine run
- **WHEN** a run emits a D2 structural diagram and a Mermaid authentication-sequence diagram
- **THEN** both render and both are accepted inputs to the renderer and the eval

#### Scenario: Back-compatible Mermaid
- **WHEN** a committed `.mmd` example is rendered
- **THEN** it still renders through the extension-dispatching renderer without modification
