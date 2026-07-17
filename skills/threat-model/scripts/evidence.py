#!/usr/bin/env python3
"""Deterministic evidence resolution + excerpt extraction — the single implementation shared by the
dashboard generator (embed) and the dashboard checks (re-extract to validate the embed matches source).

A finding's evidence item carries a FINDABLE REFERENCE (`ref`) that resolves in the target source; at
BUILD time we resolve it and EXTRACT the excerpt so the offline output embeds the proof without the repo.
This module owns that transform. It is presentation of an agent-cited fact — it reads the real file the
agent pointed at and never invents content: a ref that does not resolve yields `resolved=False` and no
excerpt (the caller surfaces the honest no-evidence / unresolved state, never a fabricated snippet).

Reference forms handled (mirrors checks.py grounding):
  path                      -> file exists; excerpt = head of the file (or the located `quote`)
  path:line                 -> that one line (+ a little context)
  path:line-range           -> the cited line range (path:LA-LB, trailing :col tolerated)
  glob (e.g. app/*.js)      -> first match; located as a file, no line excerpt
  recon/diagram node id     -> C1/D1/E1/X1/TB1… : a diagram-element reference, resolved against recon
"""
from __future__ import annotations

import glob as _glob
import os
import re

_NODE_ID = re.compile(r"^(?:[RCDEX]\d+|TB\d+)$")   # recon element / diagram node id
_PATH_LINE = re.compile(r"^(?P<path>.+?):(?P<a>\d+)(?:-(?P<b>\d+))?(?::\d+)?$")
_CTX = 2          # context lines around a single cited line
_MAX_LINES = 40   # excerpt cap (keep the embed bounded + the drawer readable)
_MAX_CHARS = 2400


def parse_ref(ref: str):
    """(path, line_start, line_end) for a path/path:line(-range) ref; (None, None, None) otherwise
    (a bare node id or unparseable). Path keeps globs intact; a trailing :col is tolerated + dropped."""
    ref = (ref or "").strip()
    if not ref or _NODE_ID.match(ref):
        return None, None, None
    m = _PATH_LINE.match(ref)
    if m:
        a = int(m.group("a"))
        b = int(m.group("b")) if m.group("b") else a
        return m.group("path"), a, b
    return ref, None, None   # bare path or glob


def _resolve_path(repo: str, path: str):
    """The real file for a repo-relative path or glob, or None. Absolute paths are rejected (they escape
    the repo) — mirrors checks.py::_resolves_in_repo."""
    if not path or os.path.isabs(path):
        return None
    direct = os.path.join(repo, path)
    if os.path.isfile(direct):
        return direct
    hits = sorted(p for p in _glob.glob(os.path.join(repo, path)) if os.path.isfile(p))
    return hits[0] if hits else None


def _clip(text: str) -> str:
    lines = text.splitlines()
    if len(lines) > _MAX_LINES:
        lines = lines[:_MAX_LINES] + ["…"]
    out = "\n".join(lines)
    return out if len(out) <= _MAX_CHARS else out[:_MAX_CHARS].rstrip() + " …"


def extract(repo, ref, quote=None, kind=None, no_direct_evidence=False):
    """Resolve one evidence item against `repo` and extract its excerpt.

    Returns a dict:
      {ref, kind, resolved(bool), is_node(bool), excerpt(str|None), line_start, line_end,
       no_direct_evidence(bool), unresolved(bool)}
    Deterministic + defensive: a missing repo/file/line degrades to resolved=False, excerpt=None — the
    caller renders the honest unresolved/no-evidence state. Never raises on a bad ref."""
    ref = (ref or "").strip() or None
    out = {"ref": ref, "kind": kind, "resolved": False, "is_node": False,
           "excerpt": None, "line_start": None, "line_end": None,
           "no_direct_evidence": bool(no_direct_evidence), "unresolved": False}

    if no_direct_evidence:
        return out  # honest blank — nothing to extract, nothing fabricated
    if not ref:
        out["unresolved"] = True
        return out

    if _NODE_ID.match(ref):
        # a diagram/recon node reference — resolved by the caller against recon (it holds the id map).
        out.update(is_node=True, resolved=True, kind=kind or "diagram")
        return out

    path, a, b = parse_ref(ref)
    fp = _resolve_path(repo, path) if path else None
    if not fp:
        out["unresolved"] = True
        return out
    out["resolved"] = True
    out["kind"] = kind or ("config" if re.search(r"\.(ya?ml|json|tf|toml|ini|env|conf)$", path, re.I)
                           else "doc" if re.search(r"\.(md|txt|rst|adoc)$", path, re.I) else "code")
    try:
        content = open(fp, encoding="utf-8", errors="replace").read()
    except OSError:
        out["resolved"] = False
        out["unresolved"] = True
        return out
    lines = content.splitlines()
    n = len(lines)
    if a is not None:
        lo = max(1, a - (_CTX if a == b else 0))
        hi = min(n, b + (_CTX if a == b else 0))
        out["line_start"], out["line_end"] = lo, hi
        out["excerpt"] = _clip("\n".join(lines[lo - 1:hi]))
    elif quote and quote.strip() and quote in content:
        # a bare path + a verbatim quote the agent copied -> embed the quote, grounded (it IS in the file)
        out["excerpt"] = _clip(quote.strip())
    else:
        out["excerpt"] = _clip("\n".join(lines[:12]))
    return out


def extract_item(repo, item, recon_names=None):
    """Extract for a schema evidence item (dict) + attach the diagram node id when the ref is one and
    a recon name map is given. `recon_names` = {id: name}."""
    if not isinstance(item, dict):
        return {"ref": None, "resolved": False, "unresolved": True, "excerpt": None,
                "no_direct_evidence": False, "is_node": False, "kind": None,
                "line_start": None, "line_end": None}
    res = extract(repo, item.get("ref"), item.get("quote"), item.get("kind"),
                  bool(item.get("no_direct_evidence")))
    res["justification"] = (item.get("justification") or "").strip() or None
    if res.get("is_node") and recon_names is not None:
        nid = res["ref"]
        res["node"] = nid
        res["excerpt"] = recon_names.get(nid, nid)
    return res
