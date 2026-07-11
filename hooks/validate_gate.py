#!/usr/bin/env python3
"""PreToolUse hard gate: block report generation until the manifests deterministically pass.

Registered (via hooks/hooks.json) on the `Task` tool. It only acts when the parent is about to spawn
the `report-analyst`; for every other tool call it allows silently. When the report spawn is seen, it
runs the deterministic validator (`run.py validate`) over the emitted manifests and:
  - allows the spawn if the manifest contract holds, or
  - DENIES it, feeding the specific DEFECT lines back to the parent so it re-spawns the analysis agent
    to fix them (the file-based validate -> retry-with-specific-feedback loop, enforced by the harness
    rather than by the agent's goodwill).

The check itself is plain Python over the manifest files + repo — no model in the path, so it is
deterministic. The hook is fail-open on infrastructure problems (validator missing, unexpected error):
it never blocks report generation for a reason unrelated to the manifest contract.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


def _allow() -> None:
    # PreToolUse: no output + exit 0 == proceed.
    sys.exit(0)


def _deny(reason: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


def _find_validator() -> Path | None:
    root = os.environ.get("CLAUDE_PLUGIN_ROOT")
    candidates = []
    if root:
        candidates.append(Path(root) / "skills/threat-model/evals/reliability/run.py")
    # fallback: relative to this script (hooks/ is a sibling of skills/)
    candidates.append(Path(__file__).resolve().parent.parent / "skills/threat-model/evals/reliability/run.py")
    # fallback: installed skill location
    candidates.append(Path.home() / ".claude/skills/threat-model/evals/reliability/run.py")
    for c in candidates:
        if c.exists():
            return c
    return None


def _output_dir(tool_input: dict, cwd: str) -> Path:
    # The report-analyst prompt carries "OUTPUT DIRECTORY: <dir>" — use the exact dir the report will use.
    prompt = tool_input.get("prompt", "") or ""
    m = re.search(r"OUTPUT DIRECTORY:\s*(\S+?)/?\s", prompt)
    if m:
        p = Path(m.group(1))
        return p if p.is_absolute() else Path(cwd) / p
    return Path(cwd) / "threat-model-output"


def _project_root(tool_input: dict) -> str | None:
    # The report-analyst prompts carry "The project root is <path>." The assessed project may differ
    # from the session cwd (SKILL.md supports {project_root} != cwd); grounding must resolve evidence
    # against the assessed project, not cwd, or every evidence string fails and the gate deadlocks.
    prompt = tool_input.get("prompt", "") or ""
    m = re.search(r"[Tt]he project root is\s+(\S+?)\.?(?:\s|$)", prompt)
    return m.group(1) if m else None


def main() -> None:
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        _allow()  # can't parse the event — never block on our own failure

    if event.get("tool_name") != "Task":
        _allow()
    tool_input = event.get("tool_input", {}) or {}
    subagent = (tool_input.get("subagent_type") or "").lower()
    name = (tool_input.get("name") or "").lower()
    if "report-analyst" not in subagent and "report-generator" not in name:
        _allow()  # not the report-generation spawn — nothing to gate

    cwd = event.get("cwd") or os.getcwd()
    validator = _find_validator()
    if validator is None:
        _allow()  # validator not found (manual/partial install) — fall back to the SKILL.md soft gate

    out_dir = _output_dir(tool_input, cwd)
    # Ground against the ASSESSED project, which SKILL.md allows to differ from the session cwd. Use
    # the prompt's declared project root; only add --repo when it resolves to a real dir. Never guess
    # cwd — grounding evidence against the wrong tree fails every string and deadlocks the gate (B2).
    # Omitting --repo demotes grounding to advisory; the structure/consistency/coverage contract (the
    # gate's real job) is still enforced.
    repo = _project_root(tool_input)
    cmd = [sys.executable, str(validator), "validate", "--run", str(out_dir)]
    if repo and Path(repo).is_dir():
        cmd += ["--repo", repo]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, OSError):
        _allow()  # infra problem, not a contract failure — fail open

    if proc.returncode == 0:
        _allow()

    # Match only real defect lines ("DEFECT [layer] code: ...") — not the FAIL message's prose,
    # which also begins with the word "DEFECT" and would otherwise be fed back as a garbled defect.
    defects = "\n".join(l for l in proc.stdout.splitlines() if l.startswith("DEFECT ["))
    _deny(
        "Manifest Validation Gate FAILED — report generation is blocked until the threat-model "
        f"manifests in {out_dir} pass the deterministic contract.\n\n{defects}\n\n"
        "Re-spawn the security-architect with these exact defects as feedback (name the field, the "
        "constraint, and the actual-vs-expected value), then retry report generation. A defect that "
        "reflects information genuinely absent from the source is not retryable — record it as "
        "no_issue_surface / coverage 'unknown' / an Open Question (or leave the optional field null), "
        "do not fabricate a value to satisfy the gate."
    )


if __name__ == "__main__":
    main()
