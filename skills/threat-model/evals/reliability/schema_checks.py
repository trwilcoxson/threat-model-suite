"""Dependency-free JSON-Schema validation for the emitted manifests.

The schema/*.json files are the STRUCTURAL contract — the file-based analog of a strict
tool schema. Because an agent writes the manifests as files (no constrained decoding), the
contract is enforced POST-HOC here instead of at generation time. This validator walks a
schema and reports structural violations; it interprets only the JSON-Schema keywords these
three schemas actually use, so it needs no third-party `jsonschema` package.

Supported: type (string or list, incl. "null"), required, properties, additionalProperties
(false), items, enum, pattern (full match), minimum, maximum, minItems, and local $ref to
"#/$defs/<name>". Structure only — semantic checks (severity == band(L x I), counts, grounding,
coverage) stay in checks.py / coverage_checks.py over the now-validated structure.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

SCHEMA_DIR = Path(__file__).resolve().parent / "schema"

_TYPE_OK = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def load_schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text())


def _type_matches(types: Any, value: Any) -> bool:
    names = types if isinstance(types, list) else [types]
    return any(_TYPE_OK.get(t, lambda _v: True)(value) for t in names)


def _resolve(node: dict, root: dict) -> dict:
    ref = node.get("$ref")
    if not ref:
        return node
    if not ref.startswith("#/"):
        return node  # only local refs are used
    cur: Any = root
    for part in ref[2:].split("/"):
        cur = cur.get(part, {})
    return cur if isinstance(cur, dict) else node


def _walk(schema: dict, value: Any, path: str, root: dict, out: list[str]) -> None:
    schema = _resolve(schema, root)

    if "type" in schema and not _type_matches(schema["type"], value):
        out.append(f"{path or '$'}: expected type {schema['type']}, got {type(value).__name__}")
        return  # wrong container type — downstream keyword checks would be noise

    if "enum" in schema and value not in schema["enum"]:
        out.append(f"{path or '$'}: {value!r} not in enum {schema['enum']}")

    if "pattern" in schema and isinstance(value, str) and not re.fullmatch(schema["pattern"], value):
        out.append(f"{path or '$'}: {value!r} does not match pattern {schema['pattern']!r}")

    if "minimum" in schema and isinstance(value, (int, float)) and not isinstance(value, bool) and value < schema["minimum"]:
        out.append(f"{path or '$'}: {value} < minimum {schema['minimum']}")
    if "maximum" in schema and isinstance(value, (int, float)) and not isinstance(value, bool) and value > schema["maximum"]:
        out.append(f"{path or '$'}: {value} > maximum {schema['maximum']}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            out.append(f"{path or '$'}: array has {len(value)} item(s) < minItems {schema['minItems']}")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(value):
                _walk(item_schema, item, f"{path}[{i}]", root, out)

    if isinstance(value, dict):
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                out.append(f"{path or '$'}: missing required property '{req}'")
        if schema.get("additionalProperties") is False:
            for k in value:
                if k not in props:
                    out.append(f"{path or '$'}: additional property '{k}' not permitted")
        for k, sub in props.items():
            if k in value and isinstance(sub, dict):
                _walk(sub, value[k], f"{path}.{k}" if path else k, root, out)


def violations(schema: dict, data: Any) -> list[str]:
    """Return a list of human-readable structural violations (empty == conforms)."""
    out: list[str] = []
    _walk(schema, data, "", schema, out)
    return out


HERE = Path(__file__).resolve().parent

_SCHEMA_FOR = {"recon.json": "recon.schema.json", "findings.json": "findings.schema.json",
               "coverage.json": "coverage.schema.json", "run-plan.json": "run-plan.schema.json"}


def check_sample_runs(root: Path) -> dict:
    """Validate every emitted manifest under `root` against its schema. Returns
    {conform, nonconforming: {relpath: [violations]}} — used by the self-check to prove the tightened
    schemas break nothing retroactively."""
    root = Path(root)
    conform = 0
    nonconforming: dict[str, list[str]] = {}
    for f in sorted(root.rglob("*.json")):
        schema_name = _SCHEMA_FOR.get(f.name)
        if not schema_name:
            continue
        try:
            vs = violations(load_schema(schema_name), json.loads(f.read_text()))
        except (OSError, ValueError) as e:
            vs = [f"load error: {e}"]
        rel = str(f.relative_to(root))
        if vs:
            nonconforming[rel] = vs
        else:
            conform += 1
    return {"conform": conform, "nonconforming": nonconforming}


if __name__ == "__main__":
    import sys

    sch = load_schema(sys.argv[1])
    inst = json.loads(Path(sys.argv[2]).read_text())
    vs = violations(sch, inst)
    if not vs:
        print("conforms")
    else:
        for v in vs:
            print("VIOLATION", v)
        sys.exit(1)
