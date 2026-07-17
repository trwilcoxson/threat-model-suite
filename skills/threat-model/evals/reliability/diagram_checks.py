"""Deterministic verification of the threat-model DIAGRAM against the skill's own spec.

Parses the Mermaid blocks the run produced (in report.md) and checks the taxonomy a robust
threat model must have: the required layers (L1-L4 per scaling), fully annotated/typed flows,
trust-boundary subgraphs, component metadata (ownership markers), and an L4 risk layer that
links to the findings (TM-NNN). Maps to the five diagram requirements; semantic correctness
(are boundaries placed right, are annotations accurate) is left to prompts/diagram-judge.md.

The analytical-visuals block (`analytical_checks`) also enforces coverage PROPERTIES over the
model's own emitted facts — reference-free, no answer key. The per-element STRIDE matrix and the
boundary-crossing STRIDE matrix each prove exhaustive consideration (every element / every
trust-boundary-crossing edge reaches a decided, grounded row); which threats are *correct* stays
with the diagram judge.

Verification stays REFERENCE-FREE ACROSS ENGINES. A per-engine extractor (chosen from the declared
```mermaid / ```d2 fence, never sniffed) turns each diagram's source into one normalized model;
the property assertions run over that model, so no check compares a diagram to a golden/reference
diagram and no check changes meaning between Mermaid and D2. Every verdict rests only on the
model's own well-formedness, id resolution within its own source, vocabulary membership, or
arithmetic recomputed from values the model stated — and honest abstention (`unknown`/`other`
types, `n/a`/`clean` cells, a check skipped because its precondition is false) stays a passing
outcome on every check.
"""
from __future__ import annotations

import difflib
import functools
import json as _json
import os
import re
from pathlib import Path
from typing import Any

# Technique-id regexes. ATTACK_TID matches an ATT&CK T#### only when it is NOT preceded by a letter or
# a dot — so the `T0051` inside an ATLAS `AML.T0051` id never registers as an ATT&CK technique (the two
# layer detectors stay separate; determinism-boundary constraint). ATLAS_TID is the ATLAS technique shape.
ATTACK_TID = r"(?<![A-Za-z.])T\d{4}(?:\.\d{3})?"
ATLAS_TID = r"AML\.T\d{4}(?:\.\d{3})?"
EDGE_OPS = r"(?:-->|-\.->|--o|==>|--x|<-->)"
SENSITIVITY = r"\[(?:PUBLIC|INTERNAL|CONFIDENTIAL|RESTRICTED)\]"
TYPED_PREFIX = r"\[(?:CTRL|AUTH|KEY|ADMIN|ASYNC|REPL|BUILD)\]"
OWNERSHIP = r"\[(?:team:|vendor:|managed|self-managed|control-owner:)"
RISK_CLASS = r":::(?:critical|high|med|medium|low)Risk|classDef\s+(?:critical|high|med|medium|low)Risk"
THREAT_ANNOT = r"⚠|×\s*\d|\d×\d|=\d+\s*(?:CRITICAL|HIGH|MEDIUM|LOW)"


def _blocks(report_text: str) -> list[str]:
    return re.findall(r"```mermaid\s(.*?)```", report_text, re.DOTALL)


def _layer_of(block: str) -> str | None:
    # Declared stamp only — never infer a diagram's layer from its prose. A block with no
    # `Layer: L{N}` stamp is left unclassified; its absence is already surfaced by
    # no-version-stamp / missing-layers, not silently guessed from keywords (determinism boundary).
    m = re.search(r"Layer:\s*(L[1-4])", block)
    return m.group(1) if m else None


def _edges(block: str) -> list[tuple[str, str | None]]:
    """Return (raw_line, label-or-None) for each real edge.

    An arrow glyph inside a quoted node label (e.g. the spec-required legend nodes
    `L5["-->  Data flow"]`, `RL6["==> Attack Path"]`) is label text, not an edge. Strip the
    double-quoted spans first; only an operator that survives is a real edge. Real labeled edges
    keep their glyph outside the quotes (`A -->|"HTTPS [ENC]"| B` -> `A -->|| B` still has `-->`).
    """
    out = []
    for line in block.splitlines():
        bare = re.sub(r'"[^"]*"', "", line)  # drop quoted label text before testing for an edge op
        if re.search(EDGE_OPS, bare):
            lbl = re.search(r"\|\s*\"?(.*?)\"?\s*\|", line)
            out.append((line.strip(), lbl.group(1) if lbl else None))
    return out


def _nodes(block: str) -> list[str]:
    # node definition lines: an id followed by a shape opener, or any :::class assignment
    out = []
    for line in block.splitlines():
        s = line.strip()
        if s.startswith(("%%", "classDef", "linkStyle", "style", "subgraph", "end", "class ")):
            continue
        if re.search(r"\w+\s*(?:\(\[|\[\(|\[\[|\{\{|\[/|\[|\(|\{)", s) or ":::" in s:
            out.append(s)
    return out


def _edge_endpoints(line: str) -> tuple[str, str] | None:
    """(source_id, dest_id) for a real edge line, else None. Endpoints are the bare node ids the DFDs
    use on edge lines (`R0 -->|"HTTP [PLAIN]"| C4`). Quoted label text is stripped first (same guard as
    `_edges`) so a glyph or `|` inside a label is never read as the operator or a second endpoint."""
    bare = re.sub(r'"[^"]*"', "", line)  # drop quoted label text before finding endpoints
    m = re.search(r"([A-Za-z_]\w*)\s*" + EDGE_OPS + r"\s*(?:\|[^|]*\|)?\s*([A-Za-z_]\w*)", bare)
    return (m.group(1), m.group(2)) if m else None


def _node_zones(block: str) -> dict[str, str | None]:
    """Map each node id to its INNERMOST enclosing `subgraph` — the most specific trust zone it is
    drawn in — or None when it sits outside every subgraph (the implicit untrusted/external zone).
    Nested subgraphs are handled with a stack, so `id[label]` and bare `id` defs alike keep the
    tightest zone. A structural read of the DFD the agent drew; it never decides where a zone *belongs*."""
    zones: dict[str, str | None] = {}
    stack: list[str] = []
    for line in block.splitlines():
        s = line.strip()
        sg = re.match(r'subgraph\s+(?:"([^"]+)"|([A-Za-z_]\w*))', s)
        if sg:
            stack.append(sg.group(1) or sg.group(2))
            continue
        if s == "end" or s.startswith("end "):
            if stack:
                stack.pop()
            continue
        nd = re.match(r"([A-Za-z_]\w*)\s*(?:\(\[|\[\(|\[\[|\{\{|\[/|\[|\(|\{)", s)  # id + a shape opener
        if nd:
            zones[nd.group(1)] = stack[-1] if stack else None
    return zones


def _crossing_edges(block: str) -> list[tuple[str, str]]:
    """Edges whose two endpoints sit in different trust zones — the boundary crossings. A node in no
    subgraph is the implicit external zone, so an external-entity -> internal-process edge counts as a
    crossing, not just an inter-subgraph one. Derived from the emitted DFD only (design decision 2)."""
    zones = _node_zones(block)
    out = []
    for line in block.splitlines():
        ep = _edge_endpoints(line)
        if ep and zones.get(ep[0]) != zones.get(ep[1]):
            out.append(ep)
    return out


def _md_tables(text: str) -> list[dict]:
    """Extract GitHub-flavored markdown tables as {header:[...], rows:[[...]]}."""
    out, lines, i = [], text.splitlines(), 0
    while i < len(lines):
        sep = i + 1 < len(lines) and re.match(r"^\s*\|?[\s:|-]*-[\s:|-]*\|?\s*$", lines[i + 1])
        if "|" in lines[i] and sep:
            header = [c.strip() for c in lines[i].strip().strip("|").split("|")]
            rows, j = [], i + 2
            while j < len(lines) and "|" in lines[j] and lines[j].strip():
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            out.append({"header": header, "rows": rows})
            i = j
        else:
            i += 1
    return out


def _edge_keyed(header: list[str]) -> bool:
    """True when a table's first column keys rows by an edge/interaction (the boundary-crossing STRIDE
    matrix), not by a single element (the per-element STRIDE matrix). Both matrices share the S…LM
    columns, so the two are told apart by their FIRST-column header — analytical-visuals.md §1a,
    design decision 4 (asserted in the tasks to avoid a selector collision)."""
    h = header[0].lower() if header else ""
    return any(k in h for k in ("edge", "interaction", "src", "→", "->"))


def _section(text: str, *keywords: str) -> str:
    """Text from the first heading containing any keyword up to the next heading."""
    out, capture = [], False
    for ln in text.splitlines():
        if re.match(r"^#{1,6}\s", ln):
            if capture:
                break
            if any(k.lower() in ln.lower() for k in keywords):
                capture = True
            continue
        if capture:
            out.append(ln)
    return "\n".join(out)


def _typed(blocks: list[str], *types: str) -> list[str]:
    """Blocks whose diagram-type stamp matches any of `types`, in EITHER documented form:
      - bare:        `%% type: attack-flow`
      - §5 stamp:    `%% Version: ... | Type: Attack Flow | Chain: KC1`   (type after a `|` field sep)
    Words tolerate hyphen or space ("attack-flow" == "Attack Flow"); matching is case-insensitive.
    See references/mermaid-diagrams.md §5 and references/analytical-visuals.md §5 for the stamp.
    """
    # `type:` may follow either `%%` (bare) or a `|` field separator inside a `%% Version: ...` line.
    pats = [r"(?:%%|\|)\s*type:\s*" + re.escape(t).replace(r"\-", "[- ]") for t in types]
    return [b for b in blocks if any(re.search(p, b.lower()) for p in pats)]


# ===========================================================================================
# Per-engine extractor seam (T5-05 / T1-06)
#
# The property assertions in check()/analytical_checks() are ENGINE-AGNOSTIC; only EXTRACTION
# (source text -> normalized model) is engine-specific. An extractor turns one diagram block's
# source into the primitives the assertions consume: the declared layer stamp, typed edges (line
# + label), boundary containers, component nodes (for ownership), node-type tokens (for the
# vocabulary check), and styling presence. The engine is chosen from the DECLARED fence
# (``` ```mermaid ``` vs ``` ```d2 ```), never sniffed from syntax — matching the existing rule
# that _layer_of reads a declared `Layer: L{N}` stamp and never infers from prose.
#
# The Mermaid extractor DELEGATES to the byte-identical module functions above, so the Mermaid
# path has ZERO behavior change (regression-locked in test_checks.t_mermaid_extractor_identity).
# The D2 extractor parses D2's container/edge/class grammar onto the SAME normalized model, so no
# property assertion changes meaning across engines (parity-locked in t_d2_extractor_parity).
# ===========================================================================================


class Block:
    """One declared diagram block: its engine (from the fence) + its raw source."""
    __slots__ = ("engine", "src")

    def __init__(self, engine: str, src: str):
        self.engine = engine
        self.src = src


def _engine_blocks(report_text: str) -> list[Block]:
    """Every ```mermaid / ```d2 fenced block, tagged with its DECLARED engine (a declared fact)."""
    return [Block(m.group(1), m.group(2))
            for m in re.finditer(r"```(mermaid|d2)\s(.*?)```", report_text, re.DOTALL)]


def _src(b: Any) -> str:
    """Source of a block. A bare str is legacy Mermaid input (tests pass raw strings) -> Mermaid."""
    return b.src if isinstance(b, Block) else b


def _ex(b: Any):
    return _D2 if (isinstance(b, Block) and b.engine == "d2") else _MERMAID


class _MermaidExtractor:
    """The Mermaid extractor is the current regex logic, verbatim (delegates to the module funcs)."""
    engine = "mermaid"

    def layer_of(self, src): return _layer_of(src)
    def edges(self, src): return _edges(src)
    def crossing_edges(self, src): return _crossing_edges(src)
    def has_version_stamp(self, src): return bool(re.search(r"%%\s*Version:", src))
    def has_class_defs(self, src): return bool(re.search(r"classDef", src))
    def boundary_count(self, src): return len(re.findall(r"\bsubgraph\b", src))
    def has_risk_styling(self, src): return bool(re.search(RISK_CLASS, src))

    def component_nodes(self, src):
        # process ([..]) / data store [(..)] nodes — the shapes the ownership check inspects.
        return [n for n in _nodes(src) if re.search(r"\(\[|\[\(", n)]

    def node_type_tokens(self, src):
        """(node_id, type_token|None, icon|None) for each drawn node. The type token is the
        `:::class` assignment; classical Mermaid nodes carry no per-node icon (icon comes from the
        classDef), so icon is None and the icon-consistency check abstains on the Mermaid path.
        `_nodes` also returns edge lines whose labels contain `[` (e.g. `A -->|"x [PUBLIC]"| B`);
        those are excluded here with the same quoted-label-stripped edge-op guard `_edges` uses, so
        an edge is never miscounted as an untyped node."""
        out = []
        for n in _nodes(src):
            if re.search(EDGE_OPS, re.sub(r'"[^"]*"', "", n)):   # an edge line, not a node def
                continue
            idm = re.match(r"([A-Za-z_]\w*)", n)
            if not idm:
                continue
            tok = re.search(r":::(\w+)", n)
            out.append((idm.group(1), tok.group(1) if tok else None, None))
        return out


def _d2_defs(src: str) -> list[dict]:
    """Parse a D2 block into node/container definitions on the normalized model.

    Returns one record per declared id: {id, path(=enclosing container ids), label, cls, icon}.
    A record whose id appears in another record's `path` is a container (a trust boundary); leaf
    records are the drawn nodes. Documented D2 subset (see references/d2-spec.md): one statement
    per line; `#` line comments; trust-boundary containers open with a trailing `{` and close with
    a `}` on its own line; leaf nodes carry an inline single-line `{ class: T; icon: P }` body;
    `classes:`/`vars:`/`style:` bodies are skipped. A naive line parser — it does not follow D2's
    full grammar (imperative overrides, glob selectors); it covers the eval-facing subset.
    ponytail: line/brace parser, upgrade to a real D2 grammar only if authored diagrams need it.
    """
    ATTR = {"class", "icon", "shape", "label", "near", "tooltip", "link", "width", "height",
            "direction", "constraint", "source-arrowhead", "target-arrowhead"}
    SKIP_KEYS = {"classes", "vars", "style"}
    defs: dict[str, dict] = {}
    order: list[str] = []
    cstack: list[str] = []   # open container ids, outermost first
    skip = 0                 # brace depth of a classes/vars/style region we are ignoring
    for raw in src.splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        net = s.count("{") - s.count("}")
        if skip > 0:                                  # inside an ignored classes/vars/style body
            skip = max(0, skip + net)
            continue
        if "->" in s or "<->" in s:                   # an edge, not a node
            continue
        if s.startswith("}"):                         # close the innermost open container
            if cstack:
                cstack.pop()
            continue
        m = re.match(r"^([A-Za-z_][\w-]*)\s*:\s*(.*)$", s)
        if not m:
            continue
        key, rest = m.group(1), m.group(2).strip()
        if key in SKIP_KEYS:
            if net > 0:
                skip = net
            continue
        if key in ATTR:                               # attribute of the current container
            if cstack and cstack[-1] in defs:
                host = defs[cstack[-1]]
                if key == "class" and rest:
                    host["cls"] = rest.strip("{} ").split()[0]
                elif key == "icon" and rest:
                    host["icon"] = rest
            if net > 0:
                skip = net
            continue
        # node / container definition
        inline_body = ""
        if "{" in rest and rest.rstrip().endswith("}"):       # single-line leaf body
            inline_body = rest[rest.index("{") + 1:rest.rindex("}")]
            label = rest[:rest.index("{")]
        elif rest.endswith("{"):                              # opens a multi-line container
            label = rest[:-1]
        else:
            label = rest
        label = label.strip().strip('"')
        rec = defs.setdefault(key, {"id": key, "path": tuple(cstack),
                                    "label": "", "cls": None, "icon": None})
        if label and not rec["label"]:
            rec["label"] = label
        if inline_body:
            cm = re.search(r"class\s*:\s*([A-Za-z_][\w-]*)", inline_body)
            if cm:
                rec["cls"] = cm.group(1)
            im = re.search(r"icon\s*:\s*(\S+)", inline_body)
            if im:
                rec["icon"] = im.group(1)
        order.append(key)
        if net > 0 and not inline_body:
            cstack.append(key)
    return [defs[k] for k in dict.fromkeys(order)]


def _d2_edge_paths(line: str) -> tuple[str, str] | None:
    """(source_path, dest_path) for a D2 edge line — dotted paths kept intact, trailing style
    block and label stripped. `VPC.PUB.C4 -> VPC.PRIV.C7: "label" { style }` -> (VPC.PUB.C4, VPC.PRIV.C7)."""
    body = re.sub(r"\{[^{}]*\}\s*$", "", line).strip()      # drop a trailing style block
    m = re.match(r"(.+?)\s*-+>\s*(.+)", body)
    if not m:
        return None
    lhs = m.group(1).strip()
    rhs = m.group(2).strip()
    rhs = rhs.split(":", 1)[0].strip()                      # drop the edge label
    src_id = lhs.split()[-1] if lhs else ""
    dst_id = rhs.split()[0] if rhs else ""
    if not src_id or not dst_id:
        return None
    return (src_id, dst_id)


class _D2Extractor:
    """Parses the D2 container/edge/class grammar onto the same normalized model as Mermaid."""
    engine = "d2"

    def layer_of(self, src):
        # Same DECLARED `Layer: L{N}` stamp; in D2 it rides a `#`-comment stamp line.
        m = re.search(r"Layer:\s*(L[1-4])", src)
        return m.group(1) if m else None

    def has_version_stamp(self, src):
        return bool(re.search(r"#.*\bVersion:", src))

    def has_class_defs(self, src):
        return bool(re.search(r"\bclasses\s*:", src))

    def boundary_count(self, src):
        # A container = an id that encloses >=1 child node (appears in some record's path).
        recs = _d2_defs(src)
        return len({p for r in recs for p in r["path"]})

    def has_risk_styling(self, src):
        return bool(re.search(r"(?:critical|high|med|medium|low)Risk", src))

    def edges(self, src):
        out = []
        for line in src.splitlines():
            s = line.strip()
            if s.startswith("#") or "->" not in s:
                continue
            body = re.sub(r"\{[^{}]*\}\s*$", "", s).strip()
            lbl = re.search(r":\s*\"?(.*?)\"?\s*$", body.split("->", 1)[1]) if "->" in body else None
            out.append((s, lbl.group(1) if lbl and lbl.group(1) else None))
        return out

    def crossing_edges(self, src):
        """Edges whose endpoints sit in different trust zones. In D2 the zone is the FULL container
        path — every dotted segment EXCEPT the leaf id: `VPC.PRIV.C7` -> zone `(VPC, PRIV)`; a bare id
        -> the external zone (None). Comparing the whole path (not just the innermost container key)
        keeps `A.PRIV.x -> B.PRIV.y` a crossing: two `PRIV` containers under different parents are
        different zones. Structural read of the DFD the agent drew; never decides where a zone belongs."""
        out = []
        for line in src.splitlines():
            s = line.strip()
            if s.startswith("#") or "->" not in s:
                continue
            ep = _d2_edge_paths(s)
            if not ep:
                continue
            z1 = tuple(ep[0].split(".")[:-1]) if "." in ep[0] else None
            z2 = tuple(ep[1].split(".")[:-1]) if "." in ep[1] else None
            if z1 != z2:
                out.append((ep[0].split(".")[-1], ep[1].split(".")[-1]))
        return out

    def component_nodes(self, src):
        COMP = {"svc", "service", "store", "datastore", "pipe", "pipeline", "queue", "process"}
        return [r["label"] for r in _d2_defs(src) if (r["cls"] or "").lower() in COMP]

    def node_type_tokens(self, src):
        recs = _d2_defs(src)
        parents = {p for r in recs for p in r["path"]}       # container ids are not drawn nodes
        return [(r["id"], r["cls"], r["icon"]) for r in recs if r["id"] not in parents]


_MERMAID = _MermaidExtractor()
_D2 = _D2Extractor()


# ---- Node-type -> icon vocabulary (T1-05) --------------------------------------------------
# A ground-truth catalog of valid node-type/icon tokens + a membership validator with fuzzy-match
# suggestions on a miss — the drawio-ai-kit `checkRef` shape (membership over emitted facts +
# suggestions), engine-independent. The catalog is a permissive/generic set (no vendored AWS-brand
# icons in the core); `unknown`/`other` is an explicit passing member so typing is never coerced.
_VOCAB_JSON = Path(__file__).resolve().parent.parent.parent / "references" / "node-type-icons.json"

# Embedded fallback mirrors the vendored JSON, so the check never crashes if the file moves.
_VOCAB_FALLBACK = {
    "types": {
        "service": {"aliases": ["svc"]}, "process": {"aliases": []},
        "datastore": {"aliases": ["store", "datastores"]}, "queue": {"aliases": []},
        "external-actor": {"aliases": ["actor", "external", "external-entity"]},
        "external-dep": {"aliases": ["extdep", "externaldep", "external-dependency"]},
        "identity": {"aliases": ["iam"]}, "secret": {"aliases": ["secrets", "kms"]},
        "control": {"aliases": []}, "pipeline": {"aliases": ["pipe"]},
        "trust-boundary": {"aliases": ["boundary"]}, "gateway": {"aliases": ["decision"]},
        "neutral": {"aliases": []}, "unknown": {"aliases": []}, "other": {"aliases": []},
    },
    "styling_classes": ["highRisk", "criticalRisk", "medRisk", "mediumRisk", "lowRisk",
                        "noFindings", "attackPath", "outOfScope"],
}


@functools.lru_cache(maxsize=1)
def _load_vocab() -> tuple[frozenset, dict, frozenset]:
    """Return (members, icons, node_types).
      members    = every accepted token (types + aliases + styling classes + unknown/other), lowercased
                   — the set a diagram `:::class` / D2 `class:` may draw from.
      icons      = token -> canonical icon id where one is defined.
      node_types = the node-type tokens + aliases ONLY, EXCLUDING styling classes — the set a recon
                   `component.type` must belong to. A styling class (highRisk, outOfScope, ...) is a
                   valid diagram class but is NOT a node type, so it must not pass as a component type
                   (checks.recon_semantic_checks)."""
    data = _VOCAB_FALLBACK
    try:
        if _VOCAB_JSON.exists():
            data = _json.loads(_VOCAB_JSON.read_text())
    except (OSError, ValueError):
        data = _VOCAB_FALLBACK
    members: set[str] = set()
    node_types: set[str] = set()
    icons: dict[str, str] = {}
    for t, meta in (data.get("types") or {}).items():
        members.add(t.lower())
        node_types.add(t.lower())
        icon = (meta or {}).get("icon")
        if icon:
            icons[t.lower()] = icon
        for a in (meta or {}).get("aliases", []) or []:
            members.add(a.lower())
            node_types.add(a.lower())
            if icon:
                icons[a.lower()] = icon
    for c in data.get("styling_classes") or []:
        members.add(c.lower())
    return frozenset(members), icons, frozenset(node_types)


def _node_type_checks(eblocks: list[Block], report_text: str) -> tuple[list[tuple[str, str]], list[str]]:
    """T4-01 / T1-05 node-type vocabulary compliance — a GROUNDING + CONSISTENCY check, ADVISORY
    (diagram layer). It counts typed-vs-untyped nodes and vocabulary membership only; it never
    asserts WHICH type a node ought to be. `unknown`/`other` counts as typed and passes. Degrades
    gracefully: when NO node carries a type token the vocabulary is simply not in use on this
    report, so the whole check is skipped (an honest abstention, mirroring the precondition gates
    elsewhere) — it therefore cannot flip a diagram that carries no type tokens yet."""
    members, _icons, _node_types = _load_vocab()   # diagram :::class draws from the full set (incl. styling)
    defects: list[tuple[str, str]] = []
    warnings: list[str] = []

    triples = [t for b in eblocks for t in _ex(b).node_type_tokens(_src(b))]
    tokens = [tok for (_id, tok, _icon) in triples]
    typed = [t for t in tokens if t]
    if not typed:                      # vocabulary not in use -> abstain (do not gate)
        return defects, warnings

    total = len(tokens)
    untyped = total - len(typed)
    if total and untyped / total > 0.10:      # mirror the untyped-edges ratio threshold
        defects.append(("node-type-untyped",
                        f"{untyped}/{total} drawn nodes carry no type token (>10%)"))
    elif untyped:
        warnings.append(f"{untyped}/{total} drawn nodes carry no type token")

    # membership: every type token in the controlled catalog; fuzzy suggestion on a miss
    for t in sorted(set(typed)):
        if t.lower() in members:
            continue
        sugg = difflib.get_close_matches(t.lower(), sorted(members), n=1)
        hint = f" (did you mean '{sugg[0]}'?)" if sugg else ""
        defects.append(("node-type-unknown-token",
                        f"node type '{t}' is not in the controlled node-type vocabulary{hint}"))

    # consistency: the same type token -> one icon across the whole report
    per_type: dict[str, set] = {}
    for (_id, tok, icon) in triples:
        if tok and icon:
            per_type.setdefault(tok.lower(), set()).add(icon)
    for tok, icons in per_type.items():
        if len(icons) > 1:
            defects.append(("icon-inconsistency",
                            f"type '{tok}' maps to {len(icons)} different icons: {sorted(icons)[:3]}"))

    # legend coverage (warning only): every used type token appears in the legend region
    if "legend" in report_text.lower():
        legend = _section(report_text, "legend") or report_text
        low = legend.lower()
        missing = sorted({t for t in set(typed) if t.lower() not in low})
        if missing:
            warnings.append(f"legend does not mention type(s): {missing[:5]}")

    return defects, warnings


# ---- Browser-free (resvg) raster-tier plain-label constraint (add-offline-render-pipeline) --------
# TRUE foreignObject markers a BROWSER-FREE rasterizer (resvg / librsvg) DROPS: D2 renders `|md ...|` /
# block-string labels via <foreignObject>, and Mermaid `<br>` line breaks are htmlLabels -> foreignObject
# too. Rasterized on the fallback tier these come out BLANK while d2/resvg exit 0 — the one silent failure
# this change exists to prevent. A plain quoted `\n` label is NOT flagged: D2 renders it as a multi-line
# SVG <tspan> (not foreignObject) and resvg/rsvg-convert draw it fine, so `\n` alone is no risk.
_FOREIGN_LABEL = re.compile(
    r"\|\s*md\b"        # D2 markdown block label:  label: |md ... |
    r"|\|\s*`"          # D2 code/block-string label: |`...`|
    r"|<br\s*/?>"       # HTML line break (Mermaid/D2 htmlLabels -> foreignObject)
    r"|```",            # fenced markdown inside a block string
    re.IGNORECASE,
)


def _fallback_tier_active() -> bool:
    """True when the browser-free resvg raster tier was DECLARED active by the preflight
    (`ensure_renderer.sh` -> `TM_RENDER_TIER=fallback`). A run-level CONFIGURATION fact, not model
    content — reading it keeps the determinism boundary intact: the check inspects the emitted source
    against the active renderer's KNOWN capability, never a golden diagram. Default (unset) is False, so
    the flagship (committed Mermaid, full-fidelity browser render) is never subjected to the constraint."""
    return os.environ.get("TM_RENDER_TIER", "").strip().lower() == "fallback"


def _plain_label_checks(eblocks: list, fallback_active: bool) -> list[tuple[str, str]]:
    """The browser-free (resvg) raster-tier plain-label guard — the ONE failure this change prevents:
    a `|md|` / multi-line / <foreignObject> label rasterizes BLANK (d2/resvg exit 0), so a broken
    diagram silently reaches docx/pdf/pptx. When the fallback tier is DECLARED active, such a label must
    not carry the annotation into the raster — move it to the adjacent machine-parseable matrix and use
    a plain single-line label.

    ADVISORY (diagram layer) and REFERENCE-FREE: it checks the emitted SOURCE against the ACTIVE
    renderer's KNOWN capability (resvg drops foreignObject), never against expected label text, and the
    honest escape hatch (declare no fallback tier / move the annotation to the matrix) is always
    available. It ABSTAINS ENTIRELY when the fallback tier is not active, so a full-fidelity browser run
    is never flipped by it."""
    if not fallback_active:
        return []                       # tier not active -> abstain (never gate the flagship)
    defects: list[tuple[str, str]] = []
    for b in eblocks:
        for ln in _src(b).splitlines():
            m = _FOREIGN_LABEL.search(ln)
            if m:
                defects.append(("fallback-tier-rich-label",
                                f"browser-free (resvg) render tier is active but a label uses "
                                f"'{m.group(0).strip()}' (markdown/multi-line/foreignObject), which "
                                f"rasterizes BLANK — move the annotation to the adjacent matrix and use "
                                f"a plain single-line label: {ln.strip()[:80]}"))
    return defects


def analytical_checks(report_text: str, blocks: list, recon: dict | None, findings_doc: dict | None,
                      coverage: dict | None = None) -> dict[str, Any]:
    """Presence/shape/consistency of the analytical & communication visuals.

    Each visual is gated by a precondition derived from SKILL-DECLARED facts (kill_chains, roles,
    dep manifest, finding STRIDE/MITRE) — never from inferring content. Structure-only: a visual that
    is present and internally consistent passes even if its analysis is wrong (the judge handles that).
    """
    defects: list[dict[str, str]] = []
    warnings: list[str] = []

    def D(code: str, detail: str) -> None:
        defects.append({"layer": "diagram", "code": code, "detail": detail})

    # Normalize block access across engines: a bare-str block (legacy Mermaid, as tests pass) is
    # the Mermaid engine; a Block carries its declared engine. The Mermaid-syntax visual detectors
    # below (AND/OR gates, sequenceDiagram) run over the source of whatever engine drew the block —
    # D2 structural blocks legitimately match none of them, which is correct.
    srcs = [_src(b) for b in blocks]

    recon = recon or {}
    findings_doc = findings_doc or {}
    findings = findings_doc.get("findings", [])
    kill_chains = findings_doc.get("kill_chains", [])
    roles = recon.get("roles", [])
    deps = recon.get("external_deps", [])
    recon_ids = {e["id"] for b in ("components", "data_stores", "entry_points", "trust_boundaries", "external_deps")
                 for e in recon.get(b, []) if isinstance(e, dict) and "id" in e}
    all_mitre = {m for f in findings for m in (f.get("mitre") or [])}
    present: list[str] = []

    # attack tree + attack-flow — gate: >=3 declared kill chains
    if len(kill_chains) >= 3:
        trees = [x for x in srcs if re.search(r"\{\s*(AND|OR)\s*\}", x)] + _typed(srcs, "attack-tree")
        trees = list(dict.fromkeys(trees))
        if not trees:
            D("no-attack-tree", f"{len(kill_chains)} kill chains declared but no attack tree (flowchart with AND/OR gates)")
        else:
            present.append("attack-tree")
            extra = {t for b in trees for t in re.findall(ATTACK_TID, b)} - all_mitre
            if extra:
                warnings.append(f"attack tree references techniques absent from findings: {sorted(extra)[:5]}")
            if len(trees) < min(len(kill_chains), 5):
                warnings.append(f"{len(trees)} attack tree(s) for {len(kill_chains)} declared kill chains")
        flows = _typed(srcs, "attack-flow", "kill-chain")
        if not flows:
            D("no-attack-flow", f"{len(kill_chains)} kill chains declared but no attack-flow / kill-chain graph")
        else:
            present.append("attack-flow")

    # auth sequence — gate: DECLARED auth fact only (an S/E finding, or declared roles[]). No name/
    # content sniffing of entry-point strings — an entry point *named* "tokenizer" must not force a
    # sequenceDiagram (determinism boundary: gate on skill-declared facts, never inferred content).
    auth_finding = any("S" in f.get("stride_lm", []) or "E" in f.get("stride_lm", []) for f in findings)
    if auth_finding or roles:
        seqs = [x for x in srcs if "sequencediagram" in x.lower()]
        if not seqs:
            D("no-auth-sequence", "auth surface present but no sequenceDiagram rendered")
        else:
            present.append("auth-sequence")
            b = seqs[0]
            parts = re.findall(r"participant\s+(\w+)", b)
            if len(parts) < 2:
                D("auth-sequence-thin", f"sequence diagram has {len(parts)} participant(s) (<2)")
            if not re.search(r"--?>>?|->|-x", b):
                D("auth-sequence-no-arrows", "sequence diagram has no message arrows")
            opens = len(re.findall(r"\b(?:alt|opt|loop|par|rect)\b", b))
            if opens and len(re.findall(r"\bend\b", b)) < opens:
                warnings.append("sequence diagram block keywords (alt/opt/.../end) unbalanced")
            if recon_ids and parts and all(p not in recon_ids for p in parts):
                warnings.append("sequence participants do not map to recon ids")

    # STRIDE-per-element coverage matrix — gate: always. Selected by its S…LM columns AND a
    # non-edge-keyed first column, so the boundary-crossing matrix below (same columns) is never grabbed.
    stride = {"S", "T", "R", "I", "D", "E", "LM"}
    matrix = next((t for t in _md_tables(report_text)
                   if stride.issubset({c.strip().upper() for c in t["header"]}) and not _edge_keyed(t["header"])), None)
    if not matrix:
        D("no-stride-matrix", "no STRIDE-per-element coverage matrix (table with S,T,R,I,D,E,LM columns)")
    else:
        present.append("stride-matrix")
        # Blank cells = empty present cells + cells the row OMITS entirely (a ragged row shorter than
        # the header is itself a blank-cell defect — it must not escape the count by not being there).
        header = matrix["header"]
        blanks = (sum(1 for r in matrix["rows"] for c in r[1:] if not c.strip())
                  + sum(max(0, len(header) - len(r)) for r in matrix["rows"]))
        if blanks:
            D("stride-matrix-blanks", f"STRIDE matrix has {blanks} blank cell(s); every cell must be TM-id / n/a / clean")
        body = " ".join(c for r in matrix["rows"] for c in r)
        miss = [f["id"] for f in findings if f["id"] not in body]
        if miss:
            warnings.append(f"{len(miss)} finding(s) not placed in STRIDE matrix: {miss[:5]}")

    # Boundary-crossing STRIDE-LM interaction matrix — gate: >=1 edge crossing a trust zone in the
    # emitted DFD layers (analytical-visuals.md §1a). The interaction-level dual of the per-element matrix.
    # STRUCTURE + GROUNDING ONLY (determinism boundary): every crossing edge the agent DREW has exactly
    # one decided row, no blank cells, and every TM-NNN placed in a cell resolves in findings.json. The
    # check never asserts a threat exists or that the STRIDE category/edge is "right" (diagram judge), so a
    # fully clean/n-a row passes. Endpoint->recon grounding is a WARNING, matching the sequence-participant
    # posture above (DFD node ids vs recon ids are WARN, not a gate — brief constraint 4). No crossing edge
    # => the visual is NOT APPLICABLE and the whole block is skipped, not failed (declared-fact gate).
    crossings = {e: True for b in blocks if _ex(b).layer_of(_src(b)) for e in _ex(b).crossing_edges(_src(b))}
    if crossings:
        bcm = next((t for t in _md_tables(report_text)
                    if stride.issubset({c.strip().upper() for c in t["header"]}) and _edge_keyed(t["header"])), None)
        if not bcm:
            D("no-boundary-crossing-matrix",
              f"{len(crossings)} boundary-crossing edge(s) in the DFD but no boundary-crossing STRIDE-LM "
              "matrix (table with an Edge/Interaction/src→dst first column + S,T,R,I,D,E,LM columns)")
        else:
            present.append("boundary-crossing-matrix")
            # Same ragged-row guard as the per-element matrix: omitted trailing cells count as blank.
            bh = bcm["header"]
            blanks = (sum(1 for r in bcm["rows"] for c in r[1:] if not c.strip())
                      + sum(max(0, len(bh) - len(r)) for r in bcm["rows"]))
            if blanks:
                D("crossing-matrix-blanks",
                  f"boundary-crossing matrix has {blanks} blank cell(s); every cell must be TM-id / n-a / clean")
            keys = [r[0] for r in bcm["rows"]]
            for src, dst in crossings:
                covering = sum(1 for k in keys
                               if re.search(rf"\b{re.escape(src)}\b", k) and re.search(rf"\b{re.escape(dst)}\b", k))
                if covering == 0:
                    D("missing-crossing-row", f"crossing edge {src} -> {dst} has no row in the boundary-crossing matrix")
                elif covering > 1:
                    D("duplicate-crossing-row", f"crossing edge {src} -> {dst} has {covering} rows (expected exactly one)")
            placed_tm = {t for r in bcm["rows"] for c in r[1:] for t in re.findall(r"TM-\d{3}", c)}
            ungrounded = placed_tm - {f["id"] for f in findings}
            if ungrounded:
                D("crossing-matrix-ungrounded-finding",
                  f"boundary-crossing matrix cites finding id(s) absent from findings.json: {sorted(ungrounded)[:5]}")
            ungrounded_ep = sorted({f"{s}->{d}" for s, d in crossings if s not in recon_ids or d not in recon_ids})
            if ungrounded_ep:  # WARN, not a defect — matches the sequence-participant recon posture
                warnings.append(f"boundary-crossing edge endpoint(s) do not map to recon ids: {ungrounded_ep[:5]}")

    # L×I risk heat map — gate: >=1 scored finding
    scored = [f for f in findings if isinstance(f.get("likelihood"), int) and isinstance(f.get("impact"), int)]
    if scored:
        # Match the heat-map heading specifically — NOT a bare "likelihood", which also matches an
        # earlier "Likelihood Scoring" methodology heading and made _section grab the wrong section.
        hm = _section(report_text, "heat map", "heatmap", "risk matrix")
        if not hm or not re.search(r"TM-\d{3}", hm):
            D("no-risk-heatmap", "scored findings exist but no Likelihood×Impact heat map plotting them")
        else:
            present.append("risk-heatmap")
            miss = [f["id"] for f in scored if f["id"] not in hm]
            if miss:
                warnings.append(f"{len(miss)} scored finding(s) not plotted on heat map: {miss[:5]}")

    # MITRE ATT&CK technique layer — gate: >=1 finding with a technique.
    # The ATT&CK layer is told apart from the ATLAS layer ONLY by domain: an atlas-atlas block is
    # EXCLUDED from `nav`, and the ATT&CK T\d{4} regex uses ATTACK_TID (no-letter/no-dot lookbehind) so
    # the `T0051` inside an `AML.T0051` ATLAS id is never read as an ATT&CK technique (design decision 2).
    if all_mitre:
        nav = [b for b in re.findall(r"```json\s(.*?)```", report_text, re.DOTALL)
               if '"techniques"' in b and '"domain"' in b and '"atlas-atlas"' not in b]
        att = _section(report_text, "att&ck", "attack navigator", "mitre att", "technique heatmap")
        if not nav and not re.search(ATTACK_TID, att):
            D("no-attack-layer", "findings map to ATT&CK techniques but no ATT&CK technique layer/heatmap rendered")
        else:
            present.append("attack-layer")
            shown = {t for src in ([att] + nav) for t in re.findall(ATTACK_TID, src)}
            if all_mitre - shown:
                warnings.append(f"ATT&CK layer missing techniques from findings: {sorted(all_mitre - shown)[:5]}")

    # MITRE ATLAS technique layer — gate: declared has_ai_ml OR >=1 finding with an ATLAS id.
    # Reuses the ATT&CK Navigator emitter with domain=="atlas-atlas"; discriminated from the ATT&CK
    # layer ONLY by that domain + the AML. prefix. Grounding, well-formedness, and abstention mirror the
    # ATT&CK block: the shown technique ids MUST be a subset of the findings' own atlas[] ids (never
    # "technique X must appear"); with no AI surface the whole block is skipped.
    all_atlas = {a for f in findings for a in (f.get("atlas") or [])}
    has_ai_ml = bool((coverage or {}).get("context", {}).get("has_ai_ml"))
    if all_atlas or has_ai_ml:
        atlas_navs = [b for b in re.findall(r"```json\s(.*?)```", report_text, re.DOTALL)
                      if '"atlas-atlas"' in b]
        if all_atlas and not atlas_navs:
            D("no-atlas-layer", f"findings map to {len(all_atlas)} ATLAS technique(s) but no ATLAS Navigator "
                                'layer (json with domain "atlas-atlas") rendered')
        elif atlas_navs:
            present.append("atlas-layer")
            tids = {t for src in atlas_navs for t in re.findall(r'"techniqueID"\s*:\s*"([^"]+)"', src)}
            # well-formedness: every techniqueID on the layer is AML.T#### shaped
            malformed = {t for t in tids if not re.fullmatch(ATLAS_TID, t)}
            if malformed:
                D("malformed-atlas-layer-id", f"ATLAS layer techniqueID(s) not AML.T#### shaped: {sorted(malformed)[:5]}")
            shown = {t for t in tids if re.fullmatch(ATLAS_TID, t)}
            # grounding: shown ids MUST be a subset of the distinct findings' atlas[] ids
            ungrounded = shown - all_atlas
            if ungrounded:
                D("atlas-layer-ungrounded",
                  f"ATLAS layer shows technique(s) no finding maps to: {sorted(ungrounded)[:5]}")
            # every sub-technique's parent technique must be present on the layer
            orphan = {t for t in shown if "." in t and re.sub(r"\.\d{3}$", "", t) not in shown}
            if orphan:
                D("atlas-layer-orphan-subtechnique",
                  f"ATLAS sub-technique(s) shown without their parent technique: {sorted(orphan)[:5]}")

    # RBAC / authorization matrix — gate: >=2 declared roles
    if len(roles) >= 2:
        rbac = _section(report_text, "rbac", "authorization matrix", "access control matrix", "role-by-resource")
        if not rbac or not re.search(r"anon|unauth", rbac.lower()):
            D("no-rbac-matrix", f"{len(roles)} roles declared but no RBAC/authorization matrix with an anonymous row")
        else:
            present.append("rbac-matrix")

    # SBOM / dependency graph — gate: external deps backed by a manifest
    if deps and any(e.get("manifest") for e in deps):
        sbom = _typed(srcs, "sbom", "dependency")
        sec = _section(report_text, "sbom", "dependency", "software bill")
        if not sbom and not (sec and "externaldep" in sec.lower()):
            D("no-sbom-graph", "external dependencies with a manifest but no SBOM / dependency graph")
        else:
            present.append("sbom")

    # Threat-to-Control coverage matrix — gate: >=1 finding. The defensive dual of the STRIDE matrix.
    # Detected by its column set (a Control + a Disposition column); presence/projection only — never
    # whether the listed control is the *correct* remediation. A zero-control finding must show `GAP`.
    if findings:
        cm = next((t for t in _md_tables(report_text)
                   if any("control" in c.lower() for c in t["header"])
                   and any("disposition" in c.lower() for c in t["header"])), None)
        if not cm:
            D("no-control-matrix", "findings exist but no Threat-to-Control Coverage Matrix (table with Control + Disposition columns)")
        else:
            present.append("control-matrix")
            miss = [f["id"] for f in findings if not any(f["id"] in " ".join(r) for r in cm["rows"])]
            if miss:
                warnings.append(f"{len(miss)} finding(s) not placed in control matrix: {miss[:5]}")
            for f in findings:
                if f.get("controls") or []:
                    continue  # controlled finding: no GAP expected
                row = next((r for r in cm["rows"] if f["id"] in " ".join(r)), None)
                if row and "GAP" not in " ".join(row).upper():
                    D("control-matrix-gap-missing", f"{f['id']} has no controls but its matrix row shows no GAP cell")

    return {"defects": defects, "warnings": warnings,
            "stats": {"analytical_present": present, "kill_chains": len(kill_chains), "roles": len(roles)}}


def check(report_text: str, recon: dict | None, findings_doc: dict | None,
          coverage: dict | None = None) -> dict[str, Any]:
    defects: list[dict[str, str]] = []
    warnings: list[str] = []

    def add(code: str, detail: str) -> None:
        defects.append({"layer": "diagram", "code": code, "detail": detail})

    def warn(detail: str) -> None:
        warnings.append(detail)

    # Route every fenced block through its DECLARED engine's extractor. On a Mermaid-only report
    # (every committed example + every self-check) each block dispatches to the Mermaid extractor,
    # whose primitives delegate to the module functions verbatim — so every assertion below returns
    # the IDENTICAL verdict it did before the per-engine split (behavior-preserving refactor).
    eblocks = _engine_blocks(report_text)
    if not eblocks:
        add("no-diagram", "report.md contains no ```mermaid / ```d2 diagram blocks")
        return {"defects": defects, "stats": {"blocks": 0}, "scores": {"diagram_pass": False}}

    layers: dict[str, list] = {}
    for b in eblocks:
        L = _ex(b).layer_of(_src(b))
        if L:
            layers.setdefault(L, []).append(b)

    # ---- requirement 1: taxonomy / required layers per scaling
    # Scale on COMPONENT count only, per mermaid-layers.md §6 / SKILL.md ("≤5 components → 2-layer;
    # 6-20 → full 4-layer"). Data stores don't drive layer strategy.
    size = len(recon.get("components", [])) if recon else 0
    required = {"L1", "L2", "L3", "L4"} if size > 5 else {"L1", "L4"}
    present = set(layers)
    missing = sorted(required - present)
    if missing:
        add("missing-layers", f"system size {size} needs {sorted(required)}; missing {missing} "
                              f"(present: {sorted(present) or 'none-tagged'})")
    if not any(_ex(b).has_version_stamp(_src(b)) for b in eblocks):
        add("no-version-stamp", "no `%% Version:` / `# Version:` stamp on any diagram (spec §6)")
    if "legend" not in report_text.lower():
        add("no-legend", "no legend subgraph found (spec §6 requires a legend)")
    if not any(_ex(b).has_class_defs(_src(b)) for b in eblocks):
        add("no-classdefs", "no classDef / classes block (spec §8) — risk/role styling absent")

    # ---- requirement 2: fully annotated / typed flows
    all_edges = [e for b in eblocks for e in _ex(b).edges(_src(b))]
    n_edges = len(all_edges)
    unlabeled = [e for e in all_edges if not e[1]]
    annotated = [e for e in all_edges if e[1] and (re.search(SENSITIVITY, e[1]) or re.search(TYPED_PREFIX, e[1]))]
    ann_frac = round(len(annotated) / n_edges, 3) if n_edges else None
    if n_edges and len(unlabeled) / n_edges > 0.10:
        add("untyped-edges", f"{len(unlabeled)}/{n_edges} edges unlabeled (>10%; spec §4: every arrow MUST be typed)")
    elif unlabeled:
        warn(f"{len(unlabeled)}/{n_edges} edges unlabeled (spec §4 wants every arrow typed)")
    if ann_frac is not None and ann_frac < 0.6:
        add("under-annotated-flows", f"only {int(ann_frac*100)}% of edges carry a sensitivity/type "
                                     f"annotation ([CONFIDENTIAL]/[AUTH]/etc.); spec §4 wants every flow annotated")

    # ---- requirement 3: trust boundaries (Mermaid subgraph zones / D2 containers)
    subgraphs = sum(_ex(b).boundary_count(_src(b)) for b in eblocks)
    n_tb = len(recon.get("trust_boundaries", [])) if recon else 0
    if size > 5 and "L2" in present and subgraphs == 0:
        add("no-trust-boundary-subgraphs", "L2 present but no subgraph/container trust-boundary zones drawn")
    if n_tb and subgraphs < min(n_tb, 2):
        add("few-trust-boundaries", f"recon lists {n_tb} trust boundaries but the diagram has {subgraphs} boundary zone(s)")

    # ---- requirement 4: component metadata / ownership markers (on L1 process/data-store nodes)
    l1_blocks = layers.get("L1") or eblocks[:1]
    comp_nodes = [n for b in l1_blocks for n in _ex(b).component_nodes(_src(b))]  # process/data-store nodes
    owned = [n for n in comp_nodes if re.search(OWNERSHIP, n)]
    own_frac = round(len(owned) / len(comp_nodes), 3) if comp_nodes else None
    if own_frac is not None and own_frac < 0.1:
        add("no-component-metadata", f"L1 components carry almost no ownership markers ({int(own_frac*100)}%); spec §7")
    elif own_frac is not None and own_frac < 0.5:
        warn(f"only {int(own_frac*100)}% of L1 components carry ownership markers ([team:]/[vendor:]/[managed]); spec §7 wants more")

    # ---- requirement 5: risk layering linked to findings (matched by TM-NNN, the shared id scheme)
    l4_blocks = layers.get("L4", [])
    l4 = "\n".join(_src(b) for b in l4_blocks)   # threat annotations / TM-NNN ids are engine-agnostic label text
    hi_tm = [f["id"] for f in (findings_doc.get("findings", []) if findings_doc else [])
             if f.get("severity") in ("HIGH", "CRITICAL")]
    if "L4" in present:
        if not any(_ex(b).has_risk_styling(_src(b)) for b in l4_blocks):
            add("no-risk-coloring", "L4 overlay has no risk-class styling (highRisk/criticalRisk)")
        if not re.search(THREAT_ANNOT, l4):
            add("no-threat-annotations", "L4 overlay nodes carry no threat annotations (⚠ / L×I=score / BAND); spec §5")
        tm_in_l4 = set(re.findall(r"TM-\d{3}", l4))
        if hi_tm and not tm_in_l4:
            add("risk-layer-not-linked", "L4 overlay references no TM-NNN finding id — risk layer not linked to findings")
        elif hi_tm:
            covered_hi = [t for t in hi_tm if t in tm_in_l4]
            if len(covered_hi) / len(hi_tm) < 0.8:
                add("high-findings-not-on-overlay",
                    f"only {len(covered_hi)}/{len(hi_tm)} HIGH+ findings are annotated in the L4 overlay")
            elif len(covered_hi) < len(hi_tm):
                warn(f"{len(hi_tm) - len(covered_hi)}/{len(hi_tm)} HIGH+ findings not annotated in L4 overlay")

    # node-type -> icon vocabulary compliance (T4-01 / T1-05). Grounding+consistency, ADVISORY:
    # every drawn node typed from the controlled set, tokens ∈ catalog (fuzzy suggestion on a miss),
    # same type -> same icon, legend covers used types. It NEVER asserts which type a node is, and it
    # abstains entirely when no node carries a type token (so it cannot flip a not-yet-typed diagram).
    vt_defects, vt_warnings = _node_type_checks(eblocks, report_text)
    for code, detail in vt_defects:
        add(code, detail)
    warnings.extend(vt_warnings)

    # browser-free (resvg) raster-tier plain-label guard (add-offline-render-pipeline). ABSTAINS unless
    # the preflight DECLARED the fallback tier (TM_RENDER_TIER=fallback), so the flagship (committed
    # Mermaid, full-fidelity browser render) is never flipped. Reference-free: emitted source vs the
    # active renderer's known incapability (resvg blanks foreignObject), never a golden diagram.
    for code, detail in _plain_label_checks(eblocks, _fallback_tier_active()):
        add(code, detail)

    # analytical & communication visuals (gated by skill-declared facts; structure-only)
    an = analytical_checks(report_text, eblocks, recon, findings_doc, coverage)
    defects.extend(an["defects"])
    warnings.extend(an["warnings"])

    diag_defect = bool(defects)
    return {
        "defects": defects,
        "stats": {"blocks": len(eblocks), "layers": sorted(present), "size": size,
                  "edges": n_edges, "edges_annotated_frac": ann_frac,
                  "components": len(comp_nodes), "ownership_frac": own_frac,
                  "subgraphs": subgraphs, "l4_links_findings": bool(re.search(r"TM-\d{3}", l4)),
                  "visuals_present": an["stats"]["analytical_present"],
                  "kill_chains": an["stats"]["kill_chains"],
                  "warnings": warnings},
        "scores": {"diagram_pass": not diag_defect,
                   "required_layers_present": not missing,
                   "flows_annotated": ann_frac,
                   "component_metadata": own_frac,
                   "risk_layer_linked": "L4" in present and bool(re.search(r"TM-\d{3}", l4)),
                   "analytical_visuals": an["stats"]["analytical_present"]},
    }


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path
    rd = sys.argv[1]
    rep = open(f"{rd}/report.md").read()
    recon = json.load(open(f"{rd}/recon.json"))
    findings = json.load(open(f"{rd}/findings.json"))
    cov_path = f"{rd}/coverage.json"
    coverage = json.load(open(cov_path)) if Path(cov_path).exists() else None
    print(json.dumps(check(rep, recon, findings, coverage), indent=2))
