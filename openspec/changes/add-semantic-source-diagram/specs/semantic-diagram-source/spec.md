## ADDED Requirements

### Requirement: recon.json carries an optional typed edge model
The reconnaissance manifest SHALL support an optional `dataflows[]` array whose items each declare
`{id, source, destination, type, protocol, sensitivity, enc, label, evidence[]}`, where `source` and
`destination` reference the `id` of a declared element, and SHALL support an optional `element.type`
(node-type token) and `element.zone` (trust-boundary containment) on elements. These fields SHALL be
optional so that a `recon.json` without them still conforms to the schema.

#### Scenario: Legacy recon without edges still conforms
- **WHEN** a `recon.json` that declares no `dataflows[]`, `type`, or `zone` is validated against the schema
- **THEN** it conforms, and no semantic-source check fires

#### Scenario: Typed edge references declared elements
- **WHEN** a `dataflows[]` item declares `source` and `destination`
- **THEN** each is the `id` of an element declared elsewhere in the same `recon.json`

### Requirement: A deterministic transform renders the semantic source
The suite SHALL provide a deterministic transform that renders a `recon.json` (with `dataflows[]`) to a
diagram, owning all presentation — shapes, node-type icons, colours, trust-boundary nesting, and layout —
so the authoring agent makes no presentation choice. The transform SHALL be pure: the same `recon.json`
SHALL produce byte-identical diagram source, and it SHALL bind node-type icons as offline local references
with no remote fetch.

#### Scenario: Same source renders identically
- **WHEN** the transform is run twice on the same `recon.json`
- **THEN** it emits byte-identical diagram source both times

#### Scenario: Presentation is owned by the transform, not the agent
- **WHEN** the agent authors a `recon.json` with elements, `type`s, `zone`s and `dataflows[]`
- **THEN** the rendered diagram's shapes, icons, colours, nesting and layout are determined solely by the
  transform and the controlled icon vocabulary, and the render resolves every icon from a local asset

### Requirement: Structural diagram checks are reference-free JSON property checks
When a `recon.json` carries the relevant semantic fields, the deterministic layer SHALL verify structural
properties over the JSON rather than over rendered diagram text: every dataflow `source`/`destination`
SHALL resolve to a declared element id, each `element.type` SHALL be a member of the controlled node-type
vocabulary (a non-member SHALL be flagged with a suggestion, never silently accepted or auto-corrected),
and each dataflow SHALL carry grounding evidence. These checks SHALL NOT judge whether an edge or type is
the *correct* choice, and each sub-check SHALL abstain when its OWN field is absent — the dataflow
endpoint/grounding checks when `dataflows[]` is absent, the node-type check when no `element.type` is
declared.

#### Scenario: Dangling edge endpoint is caught
- **WHEN** a dataflow's `source` or `destination` does not resolve to any declared element id
- **THEN** an endpoint-integrity defect is reported

#### Scenario: Unknown node type is flagged, not scripted
- **WHEN** an `element.type` is not a member of the controlled vocabulary
- **THEN** it is flagged with a fuzzy-match suggestion, while `unknown`/`other` pass as first-class values

#### Scenario: Each sub-check abstains when its own field is absent
- **WHEN** a `recon.json` declares no `dataflows[]` and no `element.type`
- **THEN** the dataflow endpoint/grounding checks and the node-type check each stay inert, and the run is
  validated exactly as before
