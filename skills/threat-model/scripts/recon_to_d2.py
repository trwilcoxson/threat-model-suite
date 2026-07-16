#!/usr/bin/env python3
"""recon.json -> D2 (deterministic structural-diagram render) — the semantic-source spike.

The agent authors ONLY meaning in recon.json: typed nodes (`element.type`), typed edges
(`dataflows[]`), and containment (`element.zone`). THIS script owns 100% of layout, shapes,
colors, and nesting. It is pure/deterministic — sorted iteration, no randomness, no network —
so re-running it on the same recon yields byte-identical D2 (see references/d2-spec.md).

Usage:  recon_to_d2.py <recon.json> [out.d2]   # writes out.d2 (or stdout with '-')

Node typing:  element.type (a token from references/node-type-icons.json) when present, else a
per-array default is INFERRED (components->service, data_stores->datastore, external_deps->
external-dep, entry_points->gateway, trust_boundaries->trust-boundary, roles->external-actor).
Each type binds to a built-in D2 SHAPE (offline, no vendored SVGs yet — see node-type-icons.md
§5; a vendored `icon:` path drops into the classes block once the SVG set lands).

Only elements that PARTICIPATE in a dataflow are drawn (matches the flow graph the agent authored,
no floating nodes); if a recon carries no dataflows, every element is drawn instead. A trust
boundary is drawn as a container iff it encloses >=1 drawn element or child boundary — so semantic
crossing-only boundaries never render as empty boxes.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# type token -> built-in D2 shape + fill/stroke. Shapes are the OFFLINE typed glyphs (cylinder,
# person, package, ...); a vendored SVG `icon:` per type slots in here later (node-type-icons.md §5).
TYPE_SPEC = {
    "service":        {"shape": "rectangle",     "fill": "#f5f5f5", "stroke": "#666666"},
    "process":        {"shape": "rectangle",     "fill": "#f5f5f5", "stroke": "#666666"},
    "datastore":      {"shape": "cylinder",      "fill": "#e2e3e5", "stroke": "#383d41"},
    "queue":          {"shape": "queue",         "fill": "#d5dbdb", "stroke": "#7f8c8d"},
    "external-actor": {"shape": "person",        "fill": "#cce5ff", "stroke": "#004085"},
    "external-dep":   {"shape": "package",       "fill": "#f5f5f5", "stroke": "#333333", "dash": 3},
    "identity":       {"shape": "hexagon",       "fill": "#fdf2e2", "stroke": "#a5713b"},
    "secret":         {"shape": "hexagon",       "fill": "#fdeaea", "stroke": "#cc0000"},
    "control":        {"shape": "hexagon",       "fill": "#e2f0e2", "stroke": "#2f7d32"},
    "pipeline":       {"shape": "parallelogram", "fill": "#d5dbdb", "stroke": "#7f8c8d"},
    "gateway":        {"shape": "diamond",       "fill": "#f5f5f5", "stroke": "#666666"},
    "neutral":        {"shape": "rectangle",     "fill": "#f5f5f5", "stroke": "#666666"},
    "unknown":        {"shape": "rectangle",     "fill": "#fafafa", "stroke": "#999999"},
    "other":          {"shape": "rectangle",     "fill": "#fafafa", "stroke": "#999999"},
}
# node-type token inferred per source array when element.type is absent.
INFER = {"components": "service", "data_stores": "datastore", "external_deps": "external-dep",
         "entry_points": "gateway", "trust_boundaries": "trust-boundary", "roles": "external-actor"}
LEAF_ARRAYS = ["components", "data_stores", "entry_points", "external_deps", "roles"]

# dataflow.type -> label prefix + edge style. Mirrors references/d2-spec.md §4 exactly.
EDGE_PREFIX = {"data": "", "control": "[CTRL]", "build": "[BUILD]", "async": "[ASYNC]", "admin": "[ADMIN]"}
EDGE_STYLE = {
    "data":    {},
    "control": {"stroke-dash": 3},
    "build":   {"stroke": "#f39c12", "stroke-width": 2},
    "async":   {"stroke": "#27ae60", "stroke-width": 2},
    "admin":   {"stroke": "#cc0000", "stroke-width": 2, "stroke-dash": 3},
}
# deterministic container tint palette, assigned in sorted-encounter order (fill, stroke).
CONTAINER_PALETTE = [
    ("#eaf2fb", "#004085"), ("#fff8f0", "#a5713b"), ("#f3f0fb", "#6f42c1"),
    ("#eef7ee", "#2f7d32"), ("#f9eef2", "#a5316b"),
]


def natural_key(s: str) -> list:
    """Sort C2 before C10 (digit runs compared numerically). Keeps output stable AND readable."""
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", str(s))]


def _q(text: str) -> str:
    """A safe single-line D2 double-quoted label."""
    return '"' + str(text).replace('"', "'").replace("\n", " ").strip() + '"'


def _type_of(el: dict, array: str) -> str:
    return (el.get("type") or "").strip() or INFER[array]


def _class_of(type_token: str) -> str:
    """The D2 class name for a type token — the token itself when it has a shape/style, else neutral."""
    return type_token if type_token in TYPE_SPEC else "neutral"


def build(recon: dict) -> str:
    boundaries = {b["id"]: b for b in recon.get("trust_boundaries", []) if "id" in b}
    # leaves = every drawable non-boundary element/role, keyed by id, with its source array.
    leaves: dict[str, tuple[str, dict]] = {}
    for arr in LEAF_ARRAYS:
        for el in recon.get(arr, []):
            if "id" in el:
                leaves[el["id"]] = (arr, el)

    flows = recon.get("dataflows", []) or []
    # drawn set = flow participants (no floating nodes); or everything when there are no flows.
    if flows:
        drawn = {ep for f in flows for ep in (f.get("source"), f.get("destination"))
                 if ep in leaves or ep in boundaries}
    else:
        drawn = set(leaves) | set(boundaries)

    # a boundary is drawn iff it (transitively) contains a drawn leaf or a drawn child boundary.
    def bchildren(bid: str) -> list[str]:
        return sorted((k for k, b in boundaries.items() if b.get("zone") == bid), key=natural_key)

    def boundary_drawn(bid: str, seen: frozenset = frozenset()) -> bool:
        if bid in seen:
            return False
        if any(a_el[1] and lid in drawn and a_el[1].get("zone") == bid for lid, a_el in leaves.items()):
            return True
        return any(boundary_drawn(c, seen | {bid}) for c in bchildren(bid))

    drawn_boundaries = {bid for bid in boundaries if boundary_drawn(bid)}

    # ---- emit -------------------------------------------------------------
    out: list[str] = []
    name = recon.get("system_name", "system")
    out.append(f"# Version: generated | Phase: 2 | System: {name} | Layer: L1")
    out.append("# Deterministic render of recon.json by scripts/recon_to_d2.py — DO NOT hand-edit.")
    out.append("vars: { d2-config: { layout-engine: elk } }")
    out.append("")

    # classes: one per type actually used by a drawn leaf (sorted). Vendored `icon:` slots in here.
    used_types = sorted({_class_of(_type_of(leaves[lid][1], leaves[lid][0])) for lid in drawn if lid in leaves})
    out.append("classes: {")
    for t in used_types:
        spec = TYPE_SPEC.get(t, TYPE_SPEC["neutral"])
        style = f'fill: "{spec["fill"]}"; stroke: "{spec["stroke"]}"'
        if spec.get("dash"):
            style += f'; stroke-dash: {spec["dash"]}'
        out.append(f'  {t}: {{ shape: {spec["shape"]}; style: {{ {style} }} }}')
    out.append("}")
    out.append("")

    id_path: dict[str, str] = {}  # element id -> full dotted D2 path (for edge wiring)

    def emit_leaf(lid: str, chain: list[str], indent: str) -> None:
        array, el = leaves[lid]
        cls = _class_of(_type_of(el, array))
        label = el.get("name", lid)
        tech = (el.get("tech") or "").strip()
        if tech:
            label = f"{label}\\n{tech}"
        id_path[lid] = ".".join(chain + [lid])
        out.append(f'{indent}{lid}: {_q(label)} {{ class: {cls} }}')

    def emit_boundary(bid: str, chain: list[str], indent: str, palette_i: list[int]) -> None:
        b = boundaries[bid]
        fill, stroke = CONTAINER_PALETTE[palette_i[0] % len(CONTAINER_PALETTE)]
        palette_i[0] += 1
        out.append(f'{indent}{bid}: {_q(b.get("name", bid))} {{')
        out.append(f'{indent}  style: {{ fill: "{fill}"; stroke: "{stroke}"; stroke-dash: 4; border-radius: 8 }}')
        for cb in bchildren(bid):
            if cb in drawn_boundaries:
                emit_boundary(cb, chain + [bid], indent + "  ", palette_i)
        for lid in sorted((l for l in drawn if l in leaves and leaves[l][1].get("zone") == bid), key=natural_key):
            emit_leaf(lid, chain + [bid], indent + "  ")
        out.append(f"{indent}}}")

    # top-level leaves (no zone, or a zone that isn't a drawn boundary) then top-level containers.
    top_leaves = sorted((l for l in drawn if l in leaves
                         and leaves[l][1].get("zone") not in drawn_boundaries), key=natural_key)
    for lid in top_leaves:
        emit_leaf(lid, [], "")
    out.append("")
    palette_i = [0]
    for bid in sorted((b for b in drawn_boundaries if boundaries[b].get("zone") not in drawn_boundaries),
                      key=natural_key):
        emit_boundary(bid, [], "", palette_i)

    # ---- typed + annotated edges (d2-spec §4). Endpoints resolved to full dotted paths so a nested
    # node is never phantom-created; a dangling endpoint (flagged by checks.py) is skipped, not drawn.
    out.append("")
    for f in sorted(flows, key=lambda f: natural_key(f.get("id", ""))):
        s, dst = f.get("source"), f.get("destination")
        if s not in id_path or dst not in id_path:
            continue
        out.append(f'{id_path[s]} -> {id_path[dst]}: {_edge_label(f)}{_edge_style(f)}')
    return "\n".join(out) + "\n"


def _edge_label(f: dict) -> str:
    pre = EDGE_PREFIX.get(f.get("type"), "")
    mid = " · ".join(p for p in [(f.get("protocol") or "").strip(), (f.get("label") or "").strip()] if p)
    head = " ".join(p for p in [pre, mid] if p)
    tail = " ".join(t for t in [f"[{f['sensitivity']}]" if f.get("sensitivity") else "",
                                f"[{f['enc']}]" if f.get("enc") else ""] if t)
    return _q(" ".join(p for p in [head, tail] if p) or f.get("type", "flow"))


def _edge_style(f: dict) -> str:
    style = EDGE_STYLE.get(f.get("type"), {})
    if not style:
        return ""
    body = "; ".join(f'{k}: "{v}"' if k == "stroke" else f"{k}: {v}" for k, v in style.items())
    return f" {{ style: {{ {body} }} }}"


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("usage: recon_to_d2.py <recon.json> [out.d2|-]")
    recon = json.loads(Path(sys.argv[1]).read_text())
    d2 = build(recon)
    if len(sys.argv) >= 3 and sys.argv[2] != "-":
        Path(sys.argv[2]).write_text(d2)
        print(f"wrote {sys.argv[2]} ({d2.count(chr(10))} lines)")
    else:
        sys.stdout.write(d2)


if __name__ == "__main__":
    main()
