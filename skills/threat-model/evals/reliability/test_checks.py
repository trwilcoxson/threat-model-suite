#!/usr/bin/env python3
"""Assert-based self-checks for the reliability-harness fixes. Run: `python3 test_checks.py`.

One runnable check per non-trivial fix — each fails loudly if the logic regresses. No framework.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import checks
import dashboard_checks
import diagram_checks as dc
import report
import schema_checks

_FLAGSHIP = Path(__file__).resolve().parents[4] / "docs/examples/amazon-ecs-fullstack-app-terraform"

# The deterministic recon->D2 transform lives next to the skill scripts, not on the eval path.
_R2D2 = Path(__file__).resolve().parent.parent.parent / "scripts" / "recon_to_d2.py"
_spec = importlib.util.spec_from_file_location("recon_to_d2", _R2D2)
recon_to_d2 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(recon_to_d2)


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


def t_boundary_crossing_matrix():
    """Boundary-crossing STRIDE matrix (add-boundary-crossing-stride-matrix): coverage + grounding over
    the crossings the DFD draws — structure only. A crossing = endpoints in different trust zones (a node
    in no subgraph = external); every crossing needs exactly one decided, grounded row; intra-zone edges
    don't; nested subgraphs assign the innermost zone; no crossing => the whole check is skipped."""
    dfd = ("flowchart TD\n"
           "    %% Version: x | Layer: L1\n"
           '    R0["User"]:::external\n'
           '    subgraph Z1["Public"]\n        C4(["ALB"])\n    end\n'
           '    subgraph Z2["Private"]\n        C7(["Task"])\n        C1(["SPA"])\n    end\n'
           '    R0 -->|"HTTP [PUBLIC]"| C4\n'
           '    C4 -->|"HTTP [INTERNAL]"| C7\n'
           '    C7 -.->|"[CTRL]"| C1\n')
    # structural read: two crossings (R0->C4 external->public, C4->public->C7 private); C7->C1 is intra-zone
    assert set(dc._crossing_edges(dfd)) == {("R0", "C4"), ("C4", "C7")}, dc._crossing_edges(dfd)

    recon = {"components": [{"id": "C4"}, {"id": "C7"}, {"id": "C1"}], "entry_points": [{"id": "R0"}],
             "data_stores": [], "trust_boundaries": [], "external_deps": []}
    fdoc = {"findings": [{"id": "TM-001"}]}
    hdr = ("## STRIDE-per-Interaction (Boundary-Crossing) Coverage Matrix\n"
           "| Edge (src → dst) | S | T | R | I | D | E | LM |\n"
           "|---|---|---|---|---|---|---|----|\n")

    def run(report, blocks=None, fd=fdoc):
        return dc.analytical_checks(report, blocks if blocks is not None else [dfd], recon, fd)

    # 1. both crossings covered, cells filled, TM grounded -> passes; visual present; intra-zone C7->C1
    #    is NOT demanded as a row (it never appears yet the matrix passes)
    good = hdr + ("| R0 → C4 | TM-001 | clean | clean | clean | clean | n-a | clean |\n"
                  "| C4 → C7 | clean | clean | clean | clean | clean | clean | clean |\n")
    res = run(good)
    codes = {d["code"] for d in res["defects"]}
    assert not (codes & {"no-boundary-crossing-matrix", "missing-crossing-row", "duplicate-crossing-row",
                         "crossing-matrix-blanks", "crossing-matrix-ungrounded-finding"}), codes
    assert "boundary-crossing-matrix" in res["stats"]["analytical_present"]

    # 2. a crossing edge with no row -> missing-crossing-row (C4->C7 left uncovered)
    missing = hdr + "| R0 → C4 | TM-001 | clean | clean | clean | clean | n-a | clean |\n"
    assert "missing-crossing-row" in {d["code"] for d in run(missing)["defects"]}

    # 3. crossings exist but no matrix -> no-boundary-crossing-matrix, as a diagram-layer (advisory) flag
    nomx = dc.analytical_checks("# r\n", [dfd], recon, fdoc)["defects"]
    assert any(d["code"] == "no-boundary-crossing-matrix" and d["layer"] == "diagram" for d in nomx)

    # 4. a fully clean/n-a row is honest coverage — passes with no finding required
    clean = hdr + ("| R0 → C4 | clean | clean | clean | clean | clean | n-a | clean |\n"
                   "| C4 → C7 | clean | n-a | clean | clean | clean | clean | clean |\n")
    assert "missing-crossing-row" not in {d["code"] for d in run(clean, fd={"findings": []})["defects"]}

    # 5. a blank cell -> crossing-matrix-blanks
    blank = hdr + ("| R0 → C4 | TM-001 | clean | clean |  | clean | n-a | clean |\n"
                   "| C4 → C7 | clean | clean | clean | clean | clean | clean | clean |\n")
    assert "crossing-matrix-blanks" in {d["code"] for d in run(blank)["defects"]}

    # 6. a cell TM-NNN absent from findings -> crossing-matrix-ungrounded-finding (finding-id grounding is
    #    a real defect; endpoint->recon grounding is only a warning — see below)
    ungr = hdr + ("| R0 → C4 | TM-999 | clean | clean | clean | clean | n-a | clean |\n"
                  "| C4 → C7 | clean | clean | clean | clean | clean | clean | clean |\n")
    assert "crossing-matrix-ungrounded-finding" in {d["code"] for d in run(ungr)["defects"]}

    # 6b. an endpoint absent from recon warns, never a defect (matches the sequence-participant posture)
    thin_recon = {"components": [{"id": "C4"}], "entry_points": [], "data_stores": [],
                  "trust_boundaries": [], "external_deps": []}
    wres = dc.analytical_checks(good, [dfd], thin_recon, fdoc)
    assert "crossing-row-ungrounded" not in {d["code"] for d in wres["defects"]}
    assert any("do not map to recon ids" in w for w in wres["warnings"]), wres["warnings"]

    # 7. single-zone DFD (no crossing) -> whole check skipped, not failed, even with no matrix
    one_zone = ("flowchart TD\n    %% Version: x | Layer: L1\n"
                '    subgraph Z["Zone"]\n        A(["A"])\n        B(["B"])\n    end\n    A -->|"x"| B\n')
    sz = dc.analytical_checks("# r\n", [one_zone], recon, fdoc)
    assert "no-boundary-crossing-matrix" not in {d["code"] for d in sz["defects"]}
    assert "boundary-crossing-matrix" not in sz["stats"]["analytical_present"]

    # 8. nested subgraphs: innermost zone wins — deeply-nested siblings share a zone (no crossing),
    #    an inner-vs-outer pair crosses
    nested = ("flowchart TD\n    %% Version: x | Layer: L1\n"
              '    subgraph VPC["VPC"]\n'
              '        subgraph PRIV["Private"]\n            A(["A"])\n            B(["B"])\n        end\n'
              '        C(["C"])\n    end\n    A -->|"x"| B\n    A -->|"x"| C\n')
    assert dc._node_zones(nested) == {"A": "PRIV", "B": "PRIV", "C": "VPC"}, dc._node_zones(nested)
    assert set(dc._crossing_edges(nested)) == {("A", "C")}, dc._crossing_edges(nested)

    # 9. selector collision (design decision 4): a report with BOTH S…LM matrices -> per-element grabs the
    #    Element table, boundary-crossing grabs the Edge table; both register present, neither "missing" fires
    per_elem = ("## STRIDE-per-Element Coverage Matrix\n"
                "| Element | S | T | R | I | D | E | LM |\n"
                "|---|---|---|---|---|---|---|----|\n"
                "| C4 ALB | TM-001 | clean | clean | clean | clean | n-a | clean |\n")
    bres = dc.analytical_checks(per_elem + "\n" + good, [dfd], recon, fdoc)
    bcodes = {d["code"] for d in bres["defects"]}
    assert "no-stride-matrix" not in bcodes and "no-boundary-crossing-matrix" not in bcodes, bcodes
    assert {"stride-matrix", "boundary-crossing-matrix"} <= set(bres["stats"]["analytical_present"])


def _atlas_layer(*ids):
    """A minimal ATLAS Navigator layer (domain atlas-atlas) showing the given technique ids."""
    techs = ", ".join('{"techniqueID": "%s", "score": 10}' % i for i in ids)
    return "## MITRE ATLAS Technique Layer\n```json\n" \
           '{ "domain": "atlas-atlas", "techniques": [' + techs + "] }\n```\n"


def t_atlas_layer():
    """ATLAS layer grounding (T4-03): shown technique ids MUST be a subset of the findings' own
    atlas[] ids; discriminated by domain atlas-atlas + AML. prefix; skipped when there is no AI surface."""
    ai = {"context": {"has_ai_ml": True}}
    fdoc = {"findings": [{"id": "TM-001", "atlas": ["AML.T0051"]}]}

    def codes(report, fd=fdoc, cov=ai):
        return {d["code"] for d in dc.analytical_checks(report, [], _recon(1, 0), fd, cov)["defects"]}

    # grounded + well-formed -> no atlas defect, layer registered as present
    ok = dc.analytical_checks(_atlas_layer("AML.T0051"), [], _recon(1, 0), fdoc, ai)
    okc = {d["code"] for d in ok["defects"]}
    assert "atlas-layer-ungrounded" not in okc and "malformed-atlas-layer-id" not in okc, okc
    assert "atlas-layer" in ok["stats"]["analytical_present"]

    # ungrounded: a technique on the layer that no finding maps to -> defect
    assert "atlas-layer-ungrounded" in codes(_atlas_layer("AML.T0051", "AML.T0043"))
    # malformed techniqueID on the layer (not AML.T#### shaped) -> defect
    assert "malformed-atlas-layer-id" in codes(_atlas_layer("AML.T999"))
    # sub-technique shown without its parent technique -> orphan defect
    sub = {"findings": [{"id": "TM-001", "atlas": ["AML.T0051.000"]}]}
    assert "atlas-layer-orphan-subtechnique" in codes(_atlas_layer("AML.T0051.000"), fd=sub)
    # findings declare ATLAS ids but no layer rendered -> no-atlas-layer
    assert "no-atlas-layer" in codes("# r\n")

    # non-AI run: has_ai_ml false AND no finding declares atlas -> whole block skipped (even if a
    # stray atlas json block is present), never penalized for the layer's absence.
    non_ai = dc.analytical_checks(_atlas_layer("AML.T0051"), [], _recon(1, 0),
                                  {"findings": [{"id": "TM-001"}]}, {"context": {"has_ai_ml": False}})
    ncodes = {d["code"] for d in non_ai["defects"]}
    assert not any(c.startswith("atlas-layer") or c == "no-atlas-layer" or c == "malformed-atlas-layer-id"
                   for c in ncodes), ncodes
    assert "atlas-layer" not in non_ai["stats"]["analytical_present"]
    # and no coverage at all (coverage=None) with no atlas ids -> also skipped
    assert "atlas-layer" not in dc.analytical_checks(_atlas_layer("AML.T0051"), [], _recon(1, 0),
                                                     {"findings": [{"id": "TM-001"}]})["stats"]["analytical_present"]


def _run_codes(report_body, findings=None):
    """Full run_checks over a synthetic run dir; returns the set of defect codes. The report is padded
    past the 500-byte floor so run_checks reads it (else report_text is empty)."""
    with tempfile.TemporaryDirectory() as td:
        run = Path(td)
        (run / "recon.json").write_text("{}")
        fdoc = {"findings": findings or [],
                "summary_counts": {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0},
                "no_issue_surface": []}
        (run / "findings.json").write_text(json.dumps(fdoc))
        (run / "report.md").write_text(report_body + "\n<!-- " + "pad " * 160 + "-->\n")
        return {d["code"] for d in checks.run_checks(run, run)["defects"]}


def t_atlas_vocab():
    """Controlled-vocabulary id guardrail (T4-07), keyed on the DECLARED framework field:
    malformed-atlas over the atlas[] field, malformed-owasp-llm over the OWASP-LLM checklist column."""
    base = {"id": "TM-001", "title": "t", "stride_lm": ["S"], "likelihood": 3, "impact": 3,
            "severity": "MEDIUM", "asset_refs": [], "surface_refs": [], "attack_path": "p", "remediation": "r"}

    def fcodes(f):
        return {d["code"] for d in _cvss_defect_codes(f)}

    # malformed ATLAS id in the atlas[] field -> flagged; a well-formed one passes; absence never flags
    assert "malformed-atlas" in fcodes({**base, "atlas": ["AML.T99999"]})
    assert "malformed-atlas" not in fcodes({**base, "atlas": ["AML.T0051"]})
    assert "malformed-atlas" not in fcodes({**base})
    assert "malformed-atlas" not in fcodes({**base, "atlas": None})
    # a bare ATT&CK-shaped token is NOT a valid ATLAS id (keyed on framework, no cross-namespace pass)
    assert "malformed-atlas" in fcodes({**base, "atlas": ["T1190"]})

    # OWASP-LLM checklist column: a malformed class id -> flagged; the full 2025 ids pass. Detected by
    # the "OWASP-LLM" header cell, so a finding's OWASP-category cell elsewhere is never mis-read.
    good_checklist = ("## OWASP-LLM Top-10 Coverage Checklist\n"
                      "| OWASP-LLM | Class | Coverage |\n"
                      "|-----------|-------|----------|\n"
                      "| LLM01:2025 | Prompt Injection | TM-001 |\n"
                      "| LLM10:2025 | Unbounded Consumption | n-a |\n")
    assert "malformed-owasp-llm" not in _run_codes(good_checklist)
    bad_checklist = good_checklist + "| LLM99:2025 | Bogus | clean |\n"
    assert "malformed-owasp-llm" in _run_codes(bad_checklist)
    # a bare LLM class id in a NON-checklist table (no OWASP-LLM header) is not flagged (scoping)
    other_table = ("## Finding Detail\n"
                   "| Attribute | Value |\n"
                   "|-----------|-------|\n"
                   "| OWASP Category | A03:2021 Injection (LLM01/LLM06 indirect) |\n")
    assert "malformed-owasp-llm" not in _run_codes(other_table)


def t_atlas_schema():
    """Additive atlas[] field: omitted/null validate; a malformed AML.T99999 fails on shape."""
    schema = schema_checks.load_schema("findings.schema.json")
    f = {"id": "TM-001", "title": "t", "stride_lm": ["S"], "likelihood": 3, "impact": 3,
         "severity": "MEDIUM", "asset_refs": [], "surface_refs": [], "attack_path": "p", "remediation": "r"}

    def doc(finding):
        return {"findings": [finding], "summary_counts": {"LOW": 0, "MEDIUM": 1, "HIGH": 0, "CRITICAL": 0},
                "no_issue_surface": []}

    assert schema_checks.violations(schema, doc(f)) == [], "omitted atlas must validate"
    assert schema_checks.violations(schema, doc({**f, "atlas": None})) == [], "null atlas must validate"
    assert schema_checks.violations(schema, doc({**f, "atlas": ["AML.T0051"]})) == [], "well-formed atlas validates"
    bad = schema_checks.violations(schema, doc({**f, "atlas": ["AML.T99999"]}))
    assert any("atlas" in v and "pattern" in v for v in bad), bad


def t_schema():
    """Schema conformance: every committed recon/findings manifest still validates."""
    res = schema_checks.check_sample_runs(schema_checks.HERE / "sample-runs")
    core = {k: v for k, v in res["nonconforming"].items() if k.endswith(("recon.json", "findings.json"))}
    assert not core, f"nonconforming manifests: {core}"
    assert res["conform"] >= 32, f"expected >=32 conforming manifests, got {res['conform']}"


def t_mermaid_extractor_identity():
    """Per-engine extractor (T5-05): the Mermaid extractor is a behavior-preserving delegate — its
    primitives return byte-identical results to the module functions, so the Mermaid path is
    zero-change after the split. Engine is read from the DECLARED fence, never sniffed."""
    src = ("flowchart TD\n    %% Version: x | Layer: L2\n"
           '    subgraph Z["Z"]\n        A(["a [managed]"]):::neutral\n    end\n'
           '    A -->|"HTTP [PUBLIC]"| B\n'
           "    classDef neutral fill:#eee\n")
    ex = dc._MERMAID
    assert ex.layer_of(src) == dc._layer_of(src) == "L2"
    assert ex.edges(src) == dc._edges(src)
    assert ex.crossing_edges(src) == dc._crossing_edges(src) == [("A", "B")]
    assert ex.component_nodes(src) == [n for n in dc._nodes(src) if re.search(r"\(\[|\[\(", n)]
    assert ex.boundary_count(src) == 1
    assert ex.has_version_stamp(src) and ex.has_class_defs(src)
    # fence dispatch: the engine is the DECLARED ```mermaid / ```d2 fence, not the syntax inside
    rep = "```mermaid\n" + src + "```\n```d2\n# Layer: L1\nX: \"x\" { class: svc }\n```\n"
    assert [b.engine for b in dc._engine_blocks(rep)] == ["mermaid", "d2"]


# One threat model, authored once in each engine, used to prove the property assertions produce
# the SAME verdict shape regardless of engine (cross-engine parity, tasks 1.4 / 9.2).
_PARITY_MERMAID = """## Structural
```mermaid
flowchart TD
    %% Version: 2026-07-15 | Phase: 2 | System: Demo | Layer: L1
    R0["User"]:::external
    subgraph Z1["Public"]
        C4(["ALB [managed]"]):::neutral
    end
    subgraph Z2["Private"]
        C7(["Task [self-managed]"]):::neutral
        D1[("DB [managed]")]:::dataStore
    end
    R0 -->|"HTTP [PUBLIC]"| C4
    C4 -->|"HTTP [INTERNAL]"| C7
    C7 -->|"HTTPS [CONFIDENTIAL]"| D1
    classDef external fill:#cce5ff
    classDef neutral fill:#f5f5f5
    classDef dataStore fill:#e2e3e5
```
"""

_PARITY_D2 = """## Structural
```d2
# Version: 2026-07-15 | Phase: 2 | System: Demo | Layer: L1
classes: {
  external: { style: { fill: "#cce5ff" } }
  svc: { style: { fill: "#f5f5f5" } }
  store: { shape: cylinder }
}
R0: "User" { class: external }
Z1: "Public" {
  C4: "ALB [managed]" { class: svc }
}
Z2: "Private" {
  C7: "Task [self-managed]" { class: svc }
  D1: "DB [managed]" { class: store }
}
R0 -> Z1.C4: "HTTP [PUBLIC]"
Z1.C4 -> Z2.C7: "HTTP [INTERNAL]"
Z2.C7 -> Z2.D1: "HTTPS [CONFIDENTIAL]"
```
"""


def t_d2_extractor_parity():
    """Per-engine extractor (T5-05 / T1-06): the D2 extractor maps D2's container/edge/class grammar
    onto the same normalized model, so the SAME reference-free property assertions produce the same
    verdict on the equivalent D2 diagram — no property check changes meaning across engines."""
    recon = {"components": [{"id": "C4"}, {"id": "C7"}], "data_stores": [{"id": "D1"}],
             "entry_points": [{"id": "R0"}], "trust_boundaries": [{"id": "t1"}, {"id": "t2"}],
             "external_deps": []}
    fdoc = {"findings": []}
    rm = dc.check(_PARITY_MERMAID, recon, fdoc)
    rd = dc.check(_PARITY_D2, recon, fdoc)
    codes_m = sorted(d["code"] for d in rm["defects"])
    codes_d = sorted(d["code"] for d in rd["defects"])
    assert codes_m == codes_d, f"engine verdicts diverge: mermaid={codes_m} d2={codes_d}"
    for k in ("layers", "edges", "edges_annotated_frac", "components", "ownership_frac", "subgraphs"):
        assert rm["stats"][k] == rd["stats"][k], f"stat {k} differs: {rm['stats'][k]} vs {rd['stats'][k]}"
    # the D2 extractor read the structure correctly (not vacuously equal)
    assert rd["stats"]["subgraphs"] == 2 and rd["stats"]["edges"] == 3 and rd["stats"]["layers"] == ["L1"]


def t_node_type_vocab():
    """Node-type vocabulary compliance (T4-01 / T1-05): membership over a ground-truth catalog with
    fuzzy suggestions; `unknown`/`other` passes; ADVISORY and abstains when no type token is present
    (so it never flips a not-yet-typed diagram). It counts typed-vs-untyped, never WHICH type."""
    def run(body):
        return dc._node_type_checks([dc.Block("mermaid", body)], "legend: service datastore")

    # valid tokens -> in catalog, all typed -> no membership/ratio defect
    valid = 'flowchart TD\n  A(["x"]):::service\n  B(["y"]):::datastore\n  A --> B\n'
    d, w = run(valid)
    assert not any(c == "node-type-unknown-token" for c, _ in d), d
    assert not any(c == "node-type-untyped" for c, _ in d), d

    # hallucinated token -> flagged with a fuzzy-match suggestion (drawio-ai-kit checkRef shape)
    bad = 'flowchart TD\n  A(["x"]):::servise\n  B(["y"]):::datastore\n  A --> B\n'
    d, w = run(bad)
    hits = [detail for c, detail in d if c == "node-type-unknown-token"]
    assert hits and "servise" in hits[0] and "did you mean 'service'" in hits[0], (d, w)

    # no type tokens at all -> the vocabulary is not in use -> whole check abstains (advisory/skip)
    d, w = run("flowchart TD\n  A --> B\n  C --> D\n")
    assert d == [] and w == [], (d, w)

    # unknown / other are first-class PASSING members (typing is never coerced)
    d, w = run('flowchart TD\n  A(["x"]):::unknown\n  B(["y"]):::other\n  A --> B\n')
    assert not any(c == "node-type-unknown-token" for c, _ in d), d

    # D2 icon-consistency: same type -> same icon; a type bound to two icons is flagged
    inconsistent = ('X1: "a" { class: store; icon: iconA }\n'
                    'X2: "b" { class: store; icon: iconB }\n')
    d, w = dc._node_type_checks([dc.Block("d2", inconsistent)], "")
    assert any(c == "icon-inconsistency" for c, _ in d), (d, w)


def t_plain_label_fallback():
    """Browser-free (resvg) raster-tier plain-label guard (add-offline-render-pipeline): a `|md|` /
    multi-line / foreignObject label is REJECTED only when the fallback tier is DECLARED active; a plain
    single-line label passes; an inactive fallback tier makes the whole check ABSTAIN — so the flagship
    (committed Mermaid, full-fidelity browser render) is never flipped. Reference-free: emitted source vs
    the active renderer's known incapability, never a golden diagram."""
    # a rich D2 label that uses a TRUE foreignObject trigger (an |md markdown block) — resvg blanks it
    rich_d2 = ('# Layer: L1\n'
               'C5: |md **Server API** S,T,I,E 4x4=16 HIGH TM-004 | { class: highRisk }\n')
    plain_d2 = ('# Layer: L1\n'
                'C5: "Server API ALB [managed]" { class: service }\n')
    rich = [dc.Block("d2", rich_d2)]
    plain = [dc.Block("d2", plain_d2)]

    # fallback active + rich (foreignObject) label -> flagged
    d = dc._plain_label_checks(rich, fallback_active=True)
    assert any(c == "fallback-tier-rich-label" for c, _ in d), d

    # fallback active + plain single-line label -> passes
    assert dc._plain_label_checks(plain, fallback_active=True) == []

    # fallback NOT active -> abstain entirely (even the rich label) — the flagship is never flipped
    assert dc._plain_label_checks(rich, fallback_active=False) == []

    # a `|md|` D2 block label and a Mermaid `<br>` are both caught on the active tier
    md = [dc.Block("d2", '# Layer: L1\nN1: |md **bold** | { class: service }\n')]
    assert any(c == "fallback-tier-rich-label" for c, _ in dc._plain_label_checks(md, True)), md
    br = [dc.Block("mermaid", 'flowchart TD\n  A["line1<br/>line2"] --> B\n')]
    assert any(c == "fallback-tier-rich-label" for c, _ in dc._plain_label_checks(br, True)), br

    # a normal Mermaid single-line edge label (`-->|"x"| B`) is NOT a foreignObject -> not flagged
    edge = [dc.Block("mermaid", 'flowchart TD\n  A -->|"HTTPS [INTERNAL]"| B\n')]
    assert dc._plain_label_checks(edge, fallback_active=True) == []

    # env-driven default is "not active" -> check() abstains by default (flagship stays green)
    assert dc._fallback_tier_active() is False


def t_recon_dataflow_integrity():
    """Semantic-source spike: dataflow endpoint integrity is a JSON id set-membership (replaces the
    diagram-text 'boundary-crossing endpoint(s) do not map to recon ids' regex). A dangling endpoint
    is a HARD (consistency) defect; endpoints that resolve to declared element OR role ids pass."""
    base = {"components": [{"id": "C1", "name": "svc", "evidence": ["a"]}],
            "data_stores": [{"id": "D1", "name": "db", "evidence": ["b"]}],
            "roles": [{"id": "R0", "name": "anon"}]}
    valid = {**base, "dataflows": [{"id": "F1", "source": "R0", "destination": "C1", "type": "data",
                                    "evidence": ["x"]},
                                   {"id": "F2", "source": "C1", "destination": "D1", "type": "data",
                                    "evidence": ["y"]}]}
    assert not [d for d in checks.recon_semantic_checks(valid)
                if d["code"] == "dataflow-endpoint-integrity"], "valid endpoints (incl. a role) must pass"

    dangling = {**base, "dataflows": [{"id": "F9", "source": "C1", "destination": "C404", "type": "data",
                                       "evidence": ["z"]}]}
    hits = [d for d in checks.recon_semantic_checks(dangling) if d["code"] == "dataflow-endpoint-integrity"]
    assert hits and hits[0]["layer"] == "consistency" and "C404" in hits[0]["detail"], hits


def t_recon_node_type_membership():
    """Semantic-source spike: component.type membership is a JSON check over the SAME catalog the
    diagram check uses (replaces 'node-type-unknown-token' scraped from the picture). A bad token is
    flagged with a fuzzy suggestion; a valid vocabulary token (incl. an alias) passes."""
    valid = {"components": [{"id": "C1", "name": "a", "evidence": ["e"], "type": "datastore"},
                            {"id": "C2", "name": "b", "evidence": ["e"], "type": "svc"}]}  # alias of service
    assert not [d for d in checks.recon_semantic_checks(valid)
                if d["code"] == "recon-node-type-unknown"], "vocabulary token + alias must pass"

    bad = {"components": [{"id": "C1", "name": "a", "evidence": ["e"], "type": "datastoer"}]}
    hits = [d for d in checks.recon_semantic_checks(bad) if d["code"] == "recon-node-type-unknown"]
    assert hits and "datastore" in hits[0]["detail"], f"bad token needs a fuzzy suggestion: {hits}"
    assert hits[0]["layer"] == "recon", "node-type membership is advisory (recon layer), not gated"


def t_recon_semantic_backcompat():
    """Back-compat: a recon with NO dataflows and NO component.type yields zero semantic defects — the
    checks are inert, so every committed recon is unaffected and the production gate is unchanged."""
    plain = {"components": [{"id": "C1", "name": "a", "evidence": ["e"]}],
             "data_stores": [], "entry_points": [], "trust_boundaries": [], "external_deps": []}
    assert checks.recon_semantic_checks(plain) == [], "no dataflows/type -> no defects"
    assert checks.recon_semantic_checks(None) == [] and checks.recon_semantic_checks({}) == []
    # the real flagship recon (committed, no dataflows) must also stay inert
    flagship = json.loads((Path(__file__).resolve().parents[4]
                           / "docs/examples/amazon-ecs-fullstack-app-terraform/recon.json").read_text())
    assert checks.recon_semantic_checks(flagship) == [], "committed flagship recon must be inert"


def t_recon_to_d2_smoke():
    """The deterministic transform emits VALID D2: `d2` parses/renders it (rc 0), it is byte-stable
    across runs, and endpoints resolve to full nested dotted paths (no phantom top-level node)."""
    recon = {"system_name": "Tiny",
             "components": [{"id": "C1", "name": "API", "evidence": ["e"], "type": "service", "zone": "TB1"}],
             "data_stores": [{"id": "D1", "name": "DB", "evidence": ["e"]}],
             "trust_boundaries": [{"id": "TB1", "name": "VPC", "kind": "network", "evidence": ["e"]}],
             "external_deps": [], "entry_points": [],
             "roles": [{"id": "R0", "name": "user"}],
             "dataflows": [{"id": "F1", "source": "R0", "destination": "C1", "type": "data",
                            "protocol": "HTTPS", "sensitivity": "PUBLIC", "enc": "ENC", "label": "login"},
                           {"id": "F2", "source": "C1", "destination": "D1", "type": "control"}]}
    d2 = recon_to_d2.build(recon)
    assert recon_to_d2.build(recon) == d2, "transform must be deterministic (byte-stable)"
    assert "TB1.C1" in d2, "a nested node's edge endpoint must use its full dotted path"
    assert "[PUBLIC] [ENC]" in d2 and "[CTRL]" in d2, "typed/annotated edge labels expected"

    if not shutil.which("d2"):
        return  # d2 absent in this env -> skip the render-parse leg (still covered by the assertions above)
    with tempfile.TemporaryDirectory() as td:
        src, svg = Path(td) / "t.d2", Path(td) / "t.svg"
        src.write_text(d2)
        r = subprocess.run(["d2", "--layout", "elk", str(src), str(svg)], capture_output=True, text=True)
        assert r.returncode == 0, f"d2 failed to parse the emitted D2:\n{r.stderr}"
        assert svg.exists() and svg.stat().st_size > 0
        # icon wiring: with the vendored set present, every used type binds its LOCAL icon and d2 must
        # bundle it (a missing local icon makes d2 fail loud, so a green render + a data: URI in the SVG
        # proves the paths resolve and embed offline — no remote fetch).
        if recon_to_d2.ICONS_DIR.is_dir():
            iconed = recon_to_d2.build(recon, recon_to_d2._icon_base(src))
            assert "icon: " in iconed, "each used type should bind its vendored local icon"
            src.write_text(iconed)
            isvg = Path(td) / "i.svg"
            ri = subprocess.run(["d2", "--layout", "elk", str(src), str(isvg)], capture_output=True, text=True)
            assert ri.returncode == 0, f"d2 failed to bundle the vendored local icons:\n{ri.stderr}"
            assert "data:image/svg" in isvg.read_text(), "vendored icons must embed offline as data URIs"


def t_ragged_matrix_blanks():
    """FIX (blank-cell undercount): a ragged markdown row that OMITS trailing cells escaped the
    per-present-cell blank count. Omitted cells now count as blank against the header width, on BOTH
    the per-element STRIDE matrix and the boundary-crossing matrix — a row narrower than the header
    is itself a blank-cell defect."""
    fdoc = {"findings": [{"id": "TM-001"}]}

    # --- per-element STRIDE matrix: a row with 4 of 8 cells present -> stride-matrix-blanks
    ragged = ("## STRIDE-per-Element Coverage Matrix\n"
              "| Element | S | T | R | I | D | E | LM |\n"
              "|---|---|---|---|---|---|---|----|\n"
              "| C1 | TM-001 | clean | clean |\n")   # omits I,D,E,LM entirely
    codes = {d["code"] for d in dc.analytical_checks(ragged, [], _recon(1, 0), fdoc)["defects"]}
    assert "stride-matrix-blanks" in codes, f"a ragged per-element row must be caught: {codes}"
    # a fully-populated row does NOT trip it (guard against over-counting)
    full = ("## STRIDE-per-Element Coverage Matrix\n"
            "| Element | S | T | R | I | D | E | LM |\n"
            "|---|---|---|---|---|---|---|----|\n"
            "| C1 | TM-001 | clean | clean | clean | clean | n-a | clean |\n")
    codes = {d["code"] for d in dc.analytical_checks(full, [], _recon(1, 0), fdoc)["defects"]}
    assert "stride-matrix-blanks" not in codes, codes

    # --- boundary-crossing matrix: same ragged guard over the crossing rows
    dfd = ("flowchart TD\n    %% Version: x | Layer: L1\n"
           '    R0["User"]:::external\n'
           '    subgraph Z1["Public"]\n        C4(["ALB"])\n    end\n'
           '    R0 -->|"HTTP"| C4\n')   # one crossing: R0 (external) -> C4 (public zone)
    recon = {"components": [{"id": "C4"}], "entry_points": [{"id": "R0"}],
             "data_stores": [], "trust_boundaries": [], "external_deps": []}
    bcm_ragged = ("## STRIDE-per-Interaction (Boundary-Crossing) Coverage Matrix\n"
                  "| Edge (src → dst) | S | T | R | I | D | E | LM |\n"
                  "|---|---|---|---|---|---|---|----|\n"
                  "| R0 → C4 | TM-001 | clean |\n")   # omits 6 trailing cells
    codes = {d["code"] for d in dc.analytical_checks(bcm_ragged, [dfd], recon, fdoc)["defects"]}
    assert "crossing-matrix-blanks" in codes, f"a ragged crossing row must be caught: {codes}"


def t_foreign_label_plain_newline():
    """FIX (_FOREIGN_LABEL false positive): a plain quoted `\\n` D2 label renders as a multi-line SVG
    <tspan> (NOT foreignObject) and resvg/rsvg-convert draw it fine, so `\\n` alone must NOT trip the
    fallback-tier plain-label guard. TRUE foreignObject triggers (|md, block string, <br>) still fire."""
    nl = [dc.Block("d2", '# Layer: L1\nC5: "Server API\\nALB [managed]" { class: service }\n')]
    assert dc._plain_label_checks(nl, fallback_active=True) == [], "a plain \\n label is a tspan, not foreignObject"
    # genuine foreignObject triggers must STILL fire (the guard is not disabled, only the \\n alternative)
    assert dc._plain_label_checks([dc.Block("d2", '# Layer: L1\nN: |md **x** | { class: service }\n')], True), "|md| must fire"
    assert dc._plain_label_checks([dc.Block("mermaid", 'flowchart TD\n  A["a<br/>b"] --> B\n')], True), "<br> must fire"


def t_d2_crossing_full_path():
    """FIX (D2 crossing zone-collision): the crossing test compares the FULL container path, not just
    the innermost container key — so `A.PRIV.x -> B.PRIV.y` (two DIFFERENT `PRIV` containers under
    different parents) is a real boundary crossing, not a false intra-zone edge."""
    cross = dc._D2.crossing_edges("# Layer: L1\nA.PRIV.x -> B.PRIV.y: \"flow\"\n")
    assert ("x", "y") in cross, f"A.PRIV.x -> B.PRIV.y must cross (different parent paths): {cross}"
    # genuinely the same full path -> NOT a crossing (guard against over-flagging)
    same = dc._D2.crossing_edges("# Layer: L1\nA.PRIV.x -> A.PRIV.y: \"flow\"\n")
    assert same == [], f"same container path is intra-zone: {same}"


def t_recon_type_excludes_styling():
    """FIX (recon node-type folds styling classes): a recon `component.type` must be a NODE type, not a
    diagram STYLING class. `highRisk`/`outOfScope` are valid diagram `:::class` tokens but NOT node
    types, so they must be flagged as unknown component types; a genuine node type still passes."""
    for styling in ("highRisk", "outOfScope"):
        styled = {"components": [{"id": "C1", "name": "a", "evidence": ["e"], "type": styling}]}
        hits = [d for d in checks.recon_semantic_checks(styled) if d["code"] == "recon-node-type-unknown"]
        assert hits, f"styling class '{styling}' must NOT pass as a component.type"
    ok = {"components": [{"id": "C1", "name": "a", "evidence": ["e"], "type": "service"}]}
    assert not [d for d in checks.recon_semantic_checks(ok) if d["code"] == "recon-node-type-unknown"], \
        "a genuine node type must still pass"


def t_dashboard_grounding_and_consistency():
    """The dashboard is GROUNDED (numbers recount the manifests) and CROSS-OUTPUT consistent (severity ==
    findings.summary_counts) — and its embedded diagram is the RUN'S real diagram (recon node ids, real
    dataflow edges), never a fabricated one. Flagship must pass clean."""
    import build_dashboard as bd
    res = dashboard_checks.check(_FLAGSHIP)
    assert not res["defects"], f"flagship dashboard must be clean: {[d['code'] for d in res['defects']]}"
    m = bd.model_for_run(str(_FLAGSHIP))
    findings = json.loads((_FLAGSHIP / "findings.json").read_text())
    # cross-output: dashboard severity == the figures the report shows (summary_counts)
    for band, n in findings["summary_counts"].items():
        assert m["severity"][band] == n, f"dashboard severity {band} != report summary_counts"
    g = m["graph"]
    assert g["source"] == "mermaid" and len(g["nodes"]) == 23 and len(g["edges"]) == 26
    recon_ids = {el["id"] for arr in bd.KIND_OF_ARRAY for el in (json.loads((_FLAGSHIP / "recon.json").read_text()).get(arr) or [])}
    assert all(n["id"] in recon_ids for n in g["nodes"]), "every diagram node must be a recon element"


def t_dashboard_flags_fabricated_diagram():
    """The consistency guard must CATCH a diagram that invents a node or an edge not in the run's real
    dataflows (the old 'System Map / finding-co-reference edge' failure mode)."""
    import build_dashboard as bd
    m = bd.model_for_run(str(_FLAGSHIP))
    m["graph"]["nodes"].append({"id": "ZZ9", "name": "ghost", "tech": "", "kind": "component",
                                "sev": "—", "count": 0, "fids": [], "label": "ghost", "evidence": 0})
    m["graph"]["edges"].append({"a": "C1", "b": "D6", "label": "invented", "etype": "data", "fids": []})
    codes = {d["code"] for d in dashboard_checks.check(_FLAGSHIP, model=m)["defects"]}
    assert "diagram-node-fabricated" in codes, f"invented node must be caught: {codes}"
    assert "diagram-edge-not-real" in codes, f"synthesized (non-dataflow) edge must be caught: {codes}"


def t_dashboard_embeds_real_visual_engine_svg():
    """When the run carries the visual-engine's rendered STRUCTURAL SVG (the D2 render), the dashboard
    EMBEDS that exact SVG (diagram_source=embedded-svg) with click hooks over its real node ids — and
    the grounding guard CATCHES an embedded SVG that references a node id not in recon. The flagship
    (no structural SVG, Mermaid only) stays on the deterministic re-render fallback, unchanged."""
    import base64
    import build_dashboard as bd

    def b64g(nid, cls):  # a D2-style <g> whose base64 class encodes the fully-qualified node key
        return f'<g class="{base64.b64encode(nid.encode()).decode()} {cls}"><g class="shape"><rect/></g><text>{nid}</text></g>'

    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "recon.json").write_text(json.dumps({
            "system_name": "T", "components": [{"id": "C1", "name": "Api", "evidence": ["e"]}],
            "data_stores": [{"id": "D1", "name": "Db", "evidence": ["e"]}]}))
        (d / "findings.json").write_text(json.dumps({
            "summary_counts": {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 0, "LOW": 0},
            "findings": [{"id": "TM-001", "title": "x", "severity": "HIGH", "likelihood": 3,
                          "impact": 4, "asset_refs": ["C1"]}], "kill_chains": []}))
        (d / "coverage.json").write_text(json.dumps({"items": []}))
        svg = ('<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg" data-d2-version="0.7.1" '
               f'viewBox="0 0 100 100">{b64g("C1","service")}{b64g("D1","datastore")}</svg>')
        (d / "sys-L1-architecture.svg").write_text(svg)

        assert bd.structural_svg_path(str(d)).endswith("sys-L1-architecture.svg")
        assert bd.svg_node_ids(svg) == {"C1", "D1"}, "only real element ids are extracted"
        m = bd.model_for_run(str(d))
        g = m["graph"]
        assert g["diagram_source"] == "embedded-svg" and g["svg_file"] == "sys-L1-architecture.svg"
        assert 'data-d2-version' in g["svg"], "the exact D2 SVG is inlined (not re-rendered)"
        # click hooks are layered onto the real nodes, and C1's fids are grounded in findings.asset_refs
        assert 'data-entity="C1" data-fids="TM-001"' in g["svg"], "node C1 wired to its grounded finding"
        assert dashboard_checks.check(str(d), model=m)["scores"]["dashboard_pass"], "clean embed passes"

        # NEGATIVE: an embedded SVG that invents an element-shaped node id (C9 ∉ recon) must be caught.
        bad_svg = svg.replace("</svg>", b64g("C9", "service") + "</svg>")
        (d / "sys-L1-architecture.svg").write_text(bad_svg)
        codes = {x["code"] for x in dashboard_checks.check(str(d))["defects"]}
        assert "embed-node-fabricated" in codes, f"invented embedded node must be caught: {codes}"

    # the flagship has no structural SVG (Mermaid only) → the faithful re-render fallback, unchanged.
    fm = bd.model_for_run(str(_FLAGSHIP))
    assert fm["graph"]["diagram_source"] == "rerender" and not fm["graph"].get("svg"), \
        "flagship must keep the deterministic re-render fallback"


def t_dashboard_blanks_and_offline():
    """Templated-blanks + offline: an empty run builds + renders without crashing; the flagship render
    loads no external resource; absent optional fields degrade to empty states (no fabrication)."""
    import build_dashboard as bd
    import dashboard_template
    empty = bd.build_model({}, {}, {}, None)
    assert empty["posture"]["band"] == "NO FINDINGS" and empty["graph"]["nodes"] == []
    assert dashboard_template.render(empty), "empty model must still render"
    m = bd.model_for_run(str(_FLAGSHIP))
    for k in ("controls", "cvss", "atlas", "dataflows"):
        assert m["empty"][k] is True, f"flagship genuinely lacks {k} — must flag empty, not fabricate"
    htmlout = dashboard_template.render(m)
    ext = [u for u in re.findall(r'(?:href|src)\s*=\s*["\']([^"\']+)["\']', htmlout)
           if u.startswith(("http://", "https://", "//"))]
    assert not ext, f"dashboard must be offline: {ext}"


def t_run_plan_exact_match():
    """run_plan_checks: a run that produced EXACTLY the planned team + outputs passes; a missing planned
    artifact AND an extra un-planned artifact are both defects; a solo plan with a team is inconsistent."""
    import run_plan_checks as rp
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "run-plan.json").write_text(json.dumps(
            {"schema": "run-plan/v1", "mode": "team", "team": ["privacy", "code-review"],
             "outputs": ["dashboard", "report.pdf"], "confirmed": True}))
        for f in ("privacy-assessment.md", "code-security-review.md", "dashboard.html", "report.pdf"):
            (d / f).write_text("x")
        assert not rp.check(d, "post")["defects"], "exact match must pass"
        (d / "dashboard.html").unlink()           # planned but missing
        (d / "report.html").write_text("x")       # produced but not planned
        (d / "compliance-gap-analysis.md").write_text("x")  # grc ran but not planned
        codes = {x["code"] for x in rp.check(d, "post")["defects"]}
        assert {"missing-planned-output", "extra-unplanned-output", "extra-unplanned-specialist"} <= codes, codes


def t_run_plan_gate_stage_and_inert():
    """Gate stage skips planned-but-absent OUTPUTS (report-analyst has not run yet → no deadlock) but
    still catches extra/team drift; a run with no run-plan.json is wholly inert (back-compat)."""
    import run_plan_checks as rp
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        (d / "run-plan.json").write_text(json.dumps(
            {"schema": "run-plan/v1", "mode": "solo", "team": [], "outputs": ["report.pdf", "dashboard"], "confirmed": True}))
        assert not rp.check(d, "gate")["defects"], "gate must not block on outputs not generated yet"
        assert {"missing-planned-output"} <= {x["code"] for x in rp.check(d, "post")["defects"]}, "post catches missing"
    with tempfile.TemporaryDirectory() as d2:
        assert not rp.check(Path(d2), "post")["defects"], "no run-plan.json → inert"


def t_start_gate_scoping():
    """The PreToolUse start gate denies the FIRST recon spawn without a confirmed run-plan, allows it
    WITH one, and never touches other internal Task spawns (precise scoping — no pipeline wedge)."""
    gate = Path(__file__).resolve().parents[4] / "hooks" / "validate_gate.py"

    def decide(event):
        p = subprocess.run(["python3", str(gate)], input=json.dumps(event), capture_output=True, text=True)
        return "ALLOW" if not p.stdout.strip() else "DENY"
    with tempfile.TemporaryDirectory() as d:
        recon = {"tool_name": "Task", "cwd": d, "tool_input": {
            "subagent_type": "security-architect", "name": "threat-modeler-recon",
            "prompt": f"Write output to {d}/out/. against the project at /x"}}
        assert decide(recon) == "DENY", "recon spawn without a run-plan must be denied"
        out = Path(d) / "out"; out.mkdir()
        (out / "run-plan.json").write_text(json.dumps(
            {"schema": "run-plan/v1", "mode": "solo", "team": [], "outputs": ["report.html"], "confirmed": True}))
        assert decide(recon) == "ALLOW", "recon spawn with a confirmed run-plan must be allowed"
        other = {"tool_name": "Task", "cwd": d, "tool_input": {
            "subagent_type": "diagram-specialist", "name": "diagram-specialist", "prompt": "Phase 2"}}
        assert decide(other) == "ALLOW", "a non-recon internal spawn must never be gated by the start gate"


def main():
    tests = [t_attackflow, t_legendedges, t_contentsniff_layer, t_contentsniff_auth,
             t_grounding, t_layersize, t_sectionkeyword, t_cvss, t_control, t_control_matrix,
             t_boundary_crossing_matrix, t_atlas_layer, t_atlas_vocab, t_atlas_schema, t_verdict, t_schema,
             t_mermaid_extractor_identity, t_d2_extractor_parity, t_node_type_vocab,
             t_plain_label_fallback,
             t_recon_dataflow_integrity, t_recon_node_type_membership, t_recon_semantic_backcompat,
             t_recon_to_d2_smoke,
             t_ragged_matrix_blanks, t_foreign_label_plain_newline, t_d2_crossing_full_path,
             t_recon_type_excludes_styling,
             t_dashboard_grounding_and_consistency, t_dashboard_flags_fabricated_diagram,
             t_dashboard_embeds_real_visual_engine_svg,
             t_dashboard_blanks_and_offline,
             t_run_plan_exact_match, t_run_plan_gate_stage_and_inert, t_start_gate_scoping]
    for t in tests:
        t()
        print(f"ok  {t.__name__}")
    print(f"\nall {len(tests)} self-checks passed")


if __name__ == "__main__":
    main()
