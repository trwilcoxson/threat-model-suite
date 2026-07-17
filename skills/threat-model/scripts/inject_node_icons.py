#!/usr/bin/env python3
"""Inject node-type `icon:` bindings into a hand-authored D2 diagram — deterministically.

The enhanced visual engine binds each node type to its VENDORED local glyph
(`references/icons/<type>.svg`, via the `node-type-icons.json` vocabulary). `recon_to_d2.py`
already does this for the deterministic structural render. The diagram-specialist ALSO
hand-authors D2 (attack overlays, layer views, runs whose recon carries no `dataflows[]`), and
those must be visually consistent with the engine — same typed icons, every tier. This post-
processor guarantees that without relying on the agent remembering: it walks a diagram's
`classes:` block, resolves each class to a vocabulary node-type (direct name, alias, or the
risk/camelCase folds the layer diagrams use), and splices in `icon: <base>/<type>.svg` for any
typed class that lacks one. Attack-graph classes (goal/gate/step/high/med/…) are NOT node types,
so they are left untouched — icons apply to the STRUCTURAL vocabulary only.

Deterministic + idempotent: same input -> byte-identical output; a class that already has an
`icon:` is skipped. d2 embeds the referenced SVG as a base64 data URI at render time, so the
result is fully offline regardless of the (local, relative) icon path.

Usage:
    inject_node_icons.py <file.d2> [--icon-base PATH] [-o OUT|-i]   # default: print to stdout
    inject_node_icons.py --selftest
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

REFS = Path(__file__).resolve().parent.parent / "references"
ICONS_DIR = REFS / "icons"
VOCAB = REFS / "node-type-icons.json"

# Risk-styled / camelCase class names the layer + sbom diagrams use, folded onto the vocabulary type
# whose icon they should carry (the risk is conveyed by fill colour; the icon stays the node-type).
FOLD = {
    "extactor": "external-actor", "extdep": "external-dep", "riskydep": "external-dep",
    "svc": "service", "svchigh": "service", "svcmed": "service", "svcnone": "service",
    "ds": "datastore", "dshigh": "datastore", "dsmed": "datastore", "dsnone": "datastore",
    "pipe": "pipeline", "pipehigh": "pipeline", "pipemed": "pipeline",
    "queuenone": "queue", "ctrlnone": "control",
}

# `<indent><name>: { <body> }` — one class definition line inside the `classes:` block.
_CLASS_LINE = re.compile(r'^(\s*)([A-Za-z][\w-]*)\s*:\s*\{(.*)\}\s*$')
_SHAPE = re.compile(r'(shape\s*:\s*[\w-]+\s*;?)')


def _alias_map() -> dict[str, str]:
    """token (lowercased) -> canonical vocabulary type, from node-type-icons.json + the FOLD table."""
    vocab = json.loads(VOCAB.read_text())
    amap: dict[str, str] = {}
    for t, spec in vocab["types"].items():
        amap[t.lower()] = t
        for a in spec.get("aliases", []):
            amap[a.lower()] = t
    for k, v in FOLD.items():
        amap.setdefault(k, v)
    return amap


def resolve_type(class_name: str, amap: dict[str, str]) -> str | None:
    """Vocabulary node-type for a D2 class name, or None if it isn't a typed system element."""
    return amap.get(class_name.lower())


def inject(text: str, icon_base: str, amap: dict[str, str] | None = None) -> str:
    """Return `text` with `icon:` spliced into every typed class in the `classes:` block that lacks
    one. `icon_base` is the path (relative to the .d2's own dir, where d2 resolves icons) to the
    vendored icon set — e.g. 'icons' or '../references/icons'."""
    amap = amap or _alias_map()
    out, in_block, depth = [], False, 0
    for line in text.splitlines(keepends=True):
        stripped = line.strip()
        if not in_block:
            out.append(line)
            if re.match(r'^\s*classes\s*:\s*\{\s*$', line):
                in_block, depth = True, 1
            continue
        # inside the classes block: track brace depth so we exit at the matching close.
        m = _CLASS_LINE.match(line.rstrip("\n"))
        if m and "icon:" not in line:
            indent, name, body = m.group(1), m.group(2), m.group(3)
            t = resolve_type(name, amap)
            if t and (ICONS_DIR / f"{t}.svg").exists():
                binding = f"icon: {icon_base}/{t}.svg; "
                sm = _SHAPE.search(body)
                if sm:  # place after `shape: X;` to mirror recon_to_d2's ordering
                    body = body[:sm.end()] + " " + binding.rstrip() + body[sm.end():]
                else:
                    body = " " + binding + body.lstrip()
                nl = "\n" if line.endswith("\n") else ""
                out.append(f"{indent}{name}: {{{body}}}{nl}")
                depth += line.count("{") - line.count("}")
                if depth <= 0:
                    in_block = False
                continue
        out.append(line)
        depth += line.count("{") - line.count("}")
        if depth <= 0:
            in_block = False
    return "".join(out)


def _selftest() -> None:
    amap = _alias_map()
    src = (
        "vars: { d2-config: { layout-engine: elk } }\n"
        "classes: {\n"
        '  service:   { shape: rectangle; style: { fill: "#fff" } }\n'
        '  svcHigh:   { shape: rectangle; style: { fill: "#f00" } }\n'
        '  datastore: { shape: cylinder; icon: icons/datastore.svg; style: { fill: "#eee" } }\n'
        '  goal:      { shape: circle; style: { fill: "#000" } }\n'
        "}\n"
        'C1: "x" { class: service }\n'
    )
    got = inject(src, "icons", amap)
    assert "service: { shape: rectangle; icon: icons/service.svg; style:" in got, got
    assert "svcHigh: { shape: rectangle; icon: icons/service.svg; style:" in got, got  # fold
    assert got.count("icon: icons/datastore.svg") == 1, "idempotent: existing icon untouched"
    assert "goal:      { shape: circle; style: { fill:" in got, "attack-graph class untouched"
    assert inject(got, "icons", amap) == got, "idempotent on a second pass"
    # nodes outside the classes block are never rewritten
    assert 'C1: "x" { class: service }' in got
    print("inject_node_icons selftest: OK")


def main() -> int:
    args = sys.argv[1:]
    if args == ["--selftest"]:
        _selftest()
        return 0
    icon_base = "icons"
    inplace = False
    out = None
    src = None
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--icon-base":
            icon_base = args[i + 1]; i += 2
        elif a == "-o":
            out = args[i + 1]; i += 2
        elif a == "-i":
            inplace = True; i += 1
        else:
            src = a; i += 1
    if not src:
        print(__doc__); return 1
    text = Path(src).read_text()
    result = inject(text, icon_base)
    if inplace:
        Path(src).write_text(result)
    elif out:
        Path(out).write_text(result)
    else:
        sys.stdout.write(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
