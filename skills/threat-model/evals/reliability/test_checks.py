#!/usr/bin/env python3
"""Assert-based self-checks for the reliability-harness fixes. Run: `python3 test_checks.py`.

One runnable check per non-trivial fix — each fails loudly if the logic regresses. No framework.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import checks
import diagram_checks as dc
import report
import schema_checks


def t_attackflow():
    """F-ATTACKFLOW: _typed accepts the documented `| Type: Attack Flow` stamp, not only `%% type:`."""
    documented = ("flowchart LR\n"
                  "    %% Version: 2026-06-07 | Phase: 5 | System: X | Type: Attack Flow | Chain: KC1\n"
                  '    IA["access"] --> OBJ["goal"]\n')
    bare = "flowchart LR\n    %% type: attack-flow\n    A --> B\n"
    non_flow = ("flowchart TD\n"
                "    %% Version: 2026-06-07 | Phase: 2 | System: X | Layer: L1\n"
                "    A --> B\n")
    assert dc._typed([documented], "attack-flow") == [documented], "documented stamp must match"
    assert dc._typed([bare], "attack-flow") == [bare], "bare %% type: line must still match"
    assert dc._typed([non_flow], "attack-flow") == [], "an L1 layer diagram is not an attack flow"
    # other kinds, documented form
    tree = "flowchart TD\n    %% Version: x | Type: Attack Tree | Chain: KC2\n    G{AND}\n"
    sbom = "flowchart TD\n    %% Version: x | Phase: 1 | Type: SBOM\n    App --> Dep\n"
    assert dc._typed([tree], "attack-tree") == [tree]
    assert dc._typed([sbom], "sbom", "dependency") == [sbom]
    assert dc._typed([tree], "attack-flow") == [], "attack-tree must not match attack-flow"


def t_legendedges():
    """F-LEGENDEDGES: arrow glyphs inside quoted node labels (the legend) are not counted as edges."""
    block = ("flowchart LR\n"
             '    A --> |"HTTPS [ENC]"| B\n'
             '    B --> |"TCP [PLAIN]"| C\n'
             '    L1["-->  Data flow"]:::neutral\n'
             '    L2["==> Attack Path"]:::neutral\n'
             '    L3["-.-> Async"]:::neutral\n'
             '    L4["--x Blocked"]:::neutral\n')
    edges = dc._edges(block)
    unlabeled = [e for e in edges if not e[1]]
    assert len(edges) == 2, f"expected 2 real edges, got {len(edges)}: {edges}"
    assert len(unlabeled) == 0, f"expected 0 unlabeled, got {len(unlabeled)}: {unlabeled}"
    # a genuinely unlabeled real edge must still be counted
    assert len(dc._edges("flowchart LR\n    A --> B\n")) == 1


def t_contentsniff_layer():
    """F-CONTENTSNIFF(b): _layer_of relies on the stamp only — no prose keyword inference."""
    stamped = "flowchart TD\n    %% Version: x | Layer: L4\n    A --> B\n"
    prose_only = "flowchart TD\n    %% risk threat overlay for the system\n    trust and identity zones\n    A --> B\n"
    assert dc._layer_of(stamped) == "L4"
    assert dc._layer_of(prose_only) is None, "an unstamped block must not be classified from prose"


def t_contentsniff_auth():
    """F-CONTENTSNIFF(a): auth-sequence gates on a DECLARED fact (roles[] / S-E finding), not a name."""
    # blocks has no sequenceDiagram, so the defect appears exactly when the gate fires.
    rep = "# r\n"
    name_only = {"entry_points": [{"id": "E1", "name": "tokenizer", "evidence": ["x"]}], "roles": []}
    no_findings = {"findings": []}
    codes = {d["code"] for d in dc.analytical_checks(rep, [], name_only, no_findings)["defects"]}
    assert "no-auth-sequence" not in codes, "an entry point named 'tokenizer' must NOT force an auth sequence"

    with_roles = {"entry_points": [{"id": "E1", "name": "home", "evidence": ["x"]}],
                  "roles": [{"id": "u", "name": "user"}]}
    codes = {d["code"] for d in dc.analytical_checks(rep, [], with_roles, no_findings)["defects"]}
    assert "no-auth-sequence" in codes, "declared roles[] must require an auth sequence"

    se_finding = {"findings": [{"id": "TM-001", "stride_lm": ["S"]}]}
    codes = {d["code"] for d in dc.analytical_checks(rep, [], name_only, se_finding)["defects"]}
    assert "no-auth-sequence" in codes, "an S/E finding must require an auth sequence"


def t_grounding():
    """F-GROUNDING: empty / absolute / invented paths don't resolve; real path + path:line + glob do."""
    with tempfile.TemporaryDirectory() as td:
        repo = Path(td)
        (repo / "app" / "routes").mkdir(parents=True)
        (repo / "app" / "routes" / "x.js").write_text("const z = 'MAGIC_LITERAL_XYZ';\n")
        (repo / "package.json").write_text('{"name":"real"}\n')
        R = checks._resolves_in_repo
        # must NOT resolve
        assert R(repo, "") is False
        assert R(repo, "   ") is False
        assert R(repo, "/etc/passwd") is False, "absolute path escapes the repo"
        assert R(repo, "made/up/nonexistent-xyz.json") is False
        assert R(repo, "totally/invented/package.json") is False, "common basename must not ground an invented path"
        # must resolve
        assert R(repo, "app/routes/x.js") is True
        assert R(repo, "app/routes/x.js:42") is True, "path:line grounds via its path"
        assert R(repo, "app/routes/x.js:42:7") is True, "path:line:col grounds via its path"
        assert R(repo, "package.json") is True
        assert R(repo, "app/routes/*.js") is True, "glob resolves"
        assert R(repo, "MAGIC_LITERAL_XYZ") is True, "literal source substring grounds via grep"


def _recon(n_comp, n_store):
    return {"components": [{"id": f"C{i}"} for i in range(n_comp)],
            "data_stores": [{"id": f"D{i}"} for i in range(n_store)],
            "entry_points": [], "trust_boundaries": [], "external_deps": []}


def t_layersize():
    """F-LAYERSIZE: layer scaling counts components only (not + data_stores)."""
    rep = ("## Executive Summary\n"
           "```mermaid\nflowchart TD\n    %% Version: x | Layer: L1\n    A --> B\n```\n"
           "```mermaid\nflowchart TD\n    %% Version: x | Layer: L4\n    C --> D\n```\n")
    small = {d["code"] for d in dc.check(rep, _recon(4, 3), {"findings": []})["defects"]}
    assert "missing-layers" not in small, "4 components + 3 stores is a legit 2-layer system (L1+L4)"
    big = {d["code"] for d in dc.check(rep, _recon(6, 0), {"findings": []})["defects"]}
    assert "missing-layers" in big, "6 components requires the full 4-layer set"


def t_sectionkeyword():
    """F-SECTIONKEYWORD: the heat-map section match no longer collides with a 'Likelihood' heading."""
    rep = ("# R\n"
           "## Likelihood Scoring\n"
           "We rate likelihood 1-5 here. No finding ids in this methodology section.\n"
           "## Risk Heat Map (Likelihood x Impact)\n"
           "The map plots TM-001 at (4,5).\n")
    good = dc._section(rep, "heat map", "heatmap", "risk matrix")
    assert "TM-001" in good, "must capture the real heat-map section"
    bad = dc._section(rep, "heat map", "heatmap", "risk matrix", "likelihood")
    assert "TM-001" not in bad, "the old broad keyword grabbed the wrong (Likelihood Scoring) section"
    # integration: a scored finding with a real heat map -> no no-risk-heatmap defect
    fdoc = {"findings": [{"id": "TM-001", "likelihood": 4, "impact": 5}]}
    codes = {d["code"] for d in dc.analytical_checks(rep, [], _recon(1, 0), fdoc)["defects"]}
    assert "no-risk-heatmap" not in codes


def t_verdict():
    """F-VERDICT: judge CONTENT softens green->amber (caveat), never hard-fails, never crashes."""
    clean = [{"defects": []}]
    green = report._verdict(clean, {}, None)
    assert "banner green" in green and "Reliable on this target" in green

    amber = report._verdict(clean, {"quality": {"mean_soundness": 0.4}}, None)
    assert "banner amber" in amber and "soundness" in amber

    amber2 = report._verdict(clean, {"quality": {"proportionality": "inflated"}}, None)
    assert "banner amber" in amber2 and "inflated" in amber2

    amber3 = report._verdict(clean, {"recon_audit": {"missed_subsystems": ["billing"]}}, None)
    assert "banner amber" in amber3 and "missed" in amber3

    # high soundness -> stays green (no false caveat)
    assert "banner green" in report._verdict(clean, {"quality": {"mean_soundness": 0.95}}, None)

    # a real defect stays RED; the caveat is appended, generation does not crash
    red = report._verdict([{"defects": [{"code": "x"}]}], {"quality": {"mean_soundness": 0.4}}, None)
    assert "banner red" in red

    # guarded against malformed/odd judge payloads (must not raise)
    for bad in ("not-a-dict", ["x"], None, {"mean_soundness": "NaN"}, {"mean_soundness": True}):
        report._verdict(clean, {"quality": bad, "recall": bad, "recon_audit": bad}, None)
    report._judge_block("not-a-dict", "diagram_soundness")
    report._judge_block({"diagram_soundness": 0.9, "verdict": "robust",
                         "issues": [{"area": "flows", "severity": "low", "detail": "x"}]}, "diagram_soundness")


def _cvss_defect_codes(finding):
    """Run the full findings pipeline over one finding and return the set of defect codes.
    Only the cvss_* codes are asserted on; the throwaway run trips unrelated defects we ignore."""
    with tempfile.TemporaryDirectory() as td:
        run = Path(td)
        (run / "recon.json").write_text("{}")
        fdoc = {"findings": [finding],
                "summary_counts": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
                "no_issue_surface": []}
        (run / "findings.json").write_text(json.dumps(fdoc))
        (run / "report.md").write_text("stub")
        out = checks.run_checks(run, run)
        return out["defects"]


def t_cvss():
    """cvss-likelihood: recompute exploitability over the finding's OWN vector, compare to its OWN band."""
    # worked examples lock the frameworks.md mapping table against drift
    assert checks.exploitability_band("AV:N/AC:L/PR:N/UI:N") == 5
    assert checks.exploitability_band("AV:N/AC:L/PR:N/UI:R") == 4
    assert checks.exploitability_band("AV:N/AC:H/PR:L/UI:N") == 3
    assert checks.exploitability_band("AV:L/AC:H/PR:H/UI:R") == 1

    base = {"id": "TM-001", "title": "t", "stride_lm": ["S"], "impact": 3, "severity": "MEDIUM",
            "asset_refs": [], "surface_refs": [], "attack_path": "p", "remediation": "r"}

    def codes(f):
        return {d["code"] for d in _cvss_defect_codes(f)}

    # consistent vector + band -> no cvss-likelihood defect
    assert "cvss-likelihood" not in codes({**base, "likelihood": 4, "cvss_vector": "AV:N/AC:L/PR:N/UI:R"})
    # stated likelihood disagrees with the vector's band -> exactly one cvss-likelihood defect
    bad = _cvss_defect_codes({**base, "likelihood": 2, "cvss_vector": "AV:N/AC:L/PR:N/UI:R"})
    assert sum(d["code"] == "cvss-likelihood" for d in bad) == 1, bad
    # absent vector (omitted, and explicit null) -> check does not fire (back-compat / abstention)
    assert "cvss-likelihood" not in codes({**base, "likelihood": 4})
    assert "cvss-likelihood" not in codes({**base, "likelihood": 4, "cvss_vector": None})
    # a partial vector that slipped past the schema -> structure defect, never a silent pass
    assert "bad-cvss-vector" in codes({**base, "likelihood": 4, "cvss_vector": "AV:N/AC:L/PR:N"})


def t_control():
    """control coverage: reference-free flag over the finding's OWN facts — presence + disposition
    consistency + honest abstention. Never asserts a control is the *right* one; never hard-fails."""
    base = {"id": "TM-001", "title": "t", "stride_lm": ["S"], "likelihood": 3, "impact": 3,
            "severity": "MEDIUM", "asset_refs": [], "surface_refs": [], "attack_path": "p", "remediation": "r"}
    ctl = {"id": "CTL-001", "name": "Enforce mTLS", "counters": []}

    def defects(f):
        return _cvss_defect_codes(f)

    def codes(f):
        return {d["code"] for d in defects(f)}

    # >=1 control + mitigated -> consistent, covered (no control-layer flag)
    ok = codes({**base, "controls": [ctl], "control_disposition": "mitigated"})
    assert "control-disposition-mismatch" not in ok and "uncovered-control" not in ok, ok
    # controls present but disposition says none -> consistency defect
    assert "control-disposition-mismatch" in codes({**base, "controls": [ctl], "control_disposition": "none"})
    # empty controls + accepted-risk + note -> honest abstention passes
    abst = codes({**base, "controls": [], "control_disposition": "accepted-risk",
                  "disposition_note": "compensating monitoring in place"})
    assert "uncovered-control" not in abst and "disposition-without-note" not in abst and "control-disposition-mismatch" not in abst, abst
    # same abstention WITHOUT a note -> flagged (unknown-needs-a-note)
    assert "disposition-without-note" in codes({**base, "controls": [], "control_disposition": "accepted-risk"})
    # no controls, no disposition -> uncovered gap, and it is a FLAG (control layer, not a gate layer)
    legacy = defects({**base})
    unc = [d for d in legacy if d["code"] == "uncovered-control"]
    assert unc and unc[0]["layer"] == "control", "uncovered-control must be a non-gating flag"
    assert not [d for d in legacy if d["layer"] in ("structure", "consistency", "coverage")
                and d["code"].startswith(("control", "malformed-control", "malformed-framework"))], \
        "control checks must never sit in a gating layer"
    # malformed control id / framework_ref -> flagged on format
    assert "malformed-control-id" in codes({**base, "controls": [{"id": "CTL-1", "name": "x"}],
                                            "control_disposition": "mitigated"})
    assert "malformed-framework-ref" in codes({**base, "controls": [{"id": "CTL-002", "name": "x", "framework_ref": "nist ac three"}],
                                               "control_disposition": "mitigated"})
    # well-formed framework_ref with an unknown/other mapping -> NOT flagged by the eval (agent-verified)
    assert "malformed-framework-ref" not in codes({**base, "controls": [{"id": "CTL-003", "name": "x", "framework_ref": "SC-7"}],
                                                   "control_disposition": "mitigated"})


def t_control_matrix():
    """Threat-to-Control matrix: detected by Control+Disposition columns; faithful projection; a
    zero-control finding must show a GAP cell — presence/consistency only, never control correctness."""
    fdoc = {"findings": [{"id": "TM-001", "controls": [{"id": "CTL-001", "name": "mTLS"}]},
                         {"id": "TM-002", "controls": []}]}
    # a faithful matrix: TM-002 (no controls) shows GAP
    good = ("## Threat-to-Control Coverage Matrix\n"
            "| Finding | Control(s) | Disposition |\n"
            "|---------|------------|-------------|\n"
            "| TM-001 | CTL-001 | mitigated |\n"
            "| TM-002 | GAP |  |\n")
    codes = {d["code"] for d in dc.analytical_checks(good, [], _recon(1, 0), fdoc)["defects"]}
    assert "no-control-matrix" not in codes and "control-matrix-gap-missing" not in codes, codes
    present = dc.analytical_checks(good, [], _recon(1, 0), fdoc)["stats"]["analytical_present"]
    assert "control-matrix" in present
    # zero-control finding with a blank (not GAP) cell -> flagged
    blank = ("## Threat-to-Control Coverage Matrix\n"
             "| Finding | Control(s) | Disposition |\n"
             "|---------|------------|-------------|\n"
             "| TM-001 | CTL-001 | mitigated |\n"
             "| TM-002 |  |  |\n")
    codes = {d["code"] for d in dc.analytical_checks(blank, [], _recon(1, 0), fdoc)["defects"]}
    assert "control-matrix-gap-missing" in codes
    # no matrix at all, but findings exist -> flagged, as a diagram-layer flag (never a gate layer)
    nomatrix = dc.analytical_checks("# r\n", [], _recon(1, 0), fdoc)["defects"]
    assert any(d["code"] == "no-control-matrix" and d["layer"] == "diagram" for d in nomatrix)


def t_schema():
    """Schema conformance: every committed recon/findings manifest still validates."""
    res = schema_checks.check_sample_runs(schema_checks.HERE / "sample-runs")
    core = {k: v for k, v in res["nonconforming"].items() if k.endswith(("recon.json", "findings.json"))}
    assert not core, f"nonconforming manifests: {core}"
    assert res["conform"] >= 32, f"expected >=32 conforming manifests, got {res['conform']}"


def main():
    tests = [t_attackflow, t_legendedges, t_contentsniff_layer, t_contentsniff_auth,
             t_grounding, t_layersize, t_sectionkeyword, t_cvss, t_control, t_control_matrix,
             t_verdict, t_schema]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\nall {len(tests)} self-checks passed")


if __name__ == "__main__":
    main()
