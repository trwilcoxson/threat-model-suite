# Tasks

## 1. Render seam (extension dispatch)
- [x] 1.1 Add `skills/threat-model/scripts/render_diagrams.sh`: dispatch by file extension (`.mmd` → mmdc, `.d2` → d2/resvg), iterate over diagram artifacts in the output dir, phase-agnostic
- [x] 1.2 Behavior-identical for `.mmd` on day one (same `-w 3000 --scale 2 -b white -c mermaid-config.json` args as today)
- [x] 1.3 Unknown extension → exit nonzero naming the offending path (never silently skip a diagram)
- [x] 1.4 agent-prompts.md: replace the inline `npx … @mermaid-js/mermaid-cli` in both report-analyst prompts (lines ~55, ~103) with a call to `scripts/render_diagrams.sh`
- [x] 1.5 mermaid-diagrams.md §"Rendering Companion Diagrams": point at the seam instead of the raw CLI

## 2. Offline SVG in HTML + CDN gate
- [x] 2.1 Renderer: produce D2 SVG (`d2 --layout … in.d2 out.svg`) and inline it into `report.html` (seam emits the offline SVG per `.d2`; the report-analyst inlines it per report-template.md — verified: real d2 produced a 24KB offline SVG in ~44ms, no browser/network)
- [x] 2.2 report-template.md: resolve the CDN-vs-"live render" contradiction (lines 84/99 vs 353) — HTML embeds inline SVG (D2) or PNG; never a Mermaid CDN
- [x] 2.3 `scripts/verify_run.sh`: accept an inline `<svg>` diagram as satisfying the embed check (today line 29 requires `<img>`); keep the Mermaid-CDN/runtime ban (lines 31-32) unchanged
- [x] 2.4 agent-prompts.md HTML GENERATION RULES: allow inline `<svg>` for diagrams alongside `<img>` PNG

## 3. Two-tier offline PNG
- [x] 3.1 Renderer primary tier: `d2 in.d2 out.png` via the one-time-warmed, cached headless browser (offline after warm-up) — seam logic complete; running it needs a warmed browser cache
- [x] 3.2 Renderer fallback tier: `d2 → svg → resvg → png`, browser-free — seam logic complete; running it needs the `resvg` binary
- [x] 3.3 Record per-PNG engine + tier + fidelity mode in `report-generation-log.md` (seam writes `{output_dir}/.render-tiers`; the report-analyst prompt folds it into the generation log)
- [x] 3.4 Keep PNG for docx/pdf/pptx embeds (Office formats need raster)

## 4. Silent-blank guards (the primary risk)
- [x] 4.1 diagram_checks.py: when the resvg tier is active (`TM_RENDER_TIER=fallback`), reject `|md|`/multi-line/foreignObject labels — annotation moves to the adjacent matrix (advisory; abstains when the tier is not declared active)
- [x] 4.2 Renderer: verify each rasterized PNG is non-degenerate (non-blank) and fail loud if blank (PNG magic bytes + size floor; verified against an 8-byte degenerate PNG)
- [x] 4.3 diagram-specialist prompt: state the plain-single-line-label constraint when the fallback tier is declared active

## 5. Fail-loud air-gap preflight
- [x] 5.1 Add `skills/threat-model/scripts/ensure_renderer.sh`: verify `d2`, `resvg`, vendored icons + font present; exit nonzero naming any missing dependency
- [x] 5.2 Preflight verifies the warmed browser cache for the primary tier; if absent but resvg deps present, declare the fallback tier active (which enforces §4)
- [x] 5.3 SKILL.md: run the preflight at pipeline start (fail loud early, not at Step 2.5)

## 6. Hermetic deterministic config
- [ ] 6.1 Vendor the local icon set + Source Sans Pro under the plugin; reference icons by local file path — ASSET VENDORING (binary/asset packaging); the preflight already fails loud when they are absent and d2-spec.md documents local-path usage
- [x] 6.2 Reject remote `icon:` URLs at preflight/render (network + air-gap failure, silent-broken-icon trap) — seam rejects `icon: http(s)://` and fails loud (verified)
- [x] 6.3 Pin a free offline deterministic layout (dagre or ELK); forbid TALA — seam uses `--layout ${D2_LAYOUT:-elk}`, never TALA; engine-version pin rides on the vendored binary (task 7.1)

## 7. Packaging
- [ ] 7.1 `.claude-plugin/`: vendor the `d2` + `resvg` static binaries (or the install-on-preflight path) and, for air-gap, a pre-warmed browser cache — BINARY PACKAGING (environment-dependent)
- [ ] 7.2 Update plugin.json / marketplace.json descriptions if the render toolchain becomes a declared dependency — follows 7.1

## 8. Incremental migration behind the parser
- [x] 8.1 Keep `.mmd` an accepted seam input indefinitely (committed worked-examples never break) — seam dispatches `.mmd` unchanged; spec requirement asserts it
- [ ] 8.2 Pilot: convert the Phase-2 L1 structural diagram to `.d2` once its property parser lands; switch HTML to inline D2 SVG for it; other diagrams stay Mermaid — MIGRATION ACTION (rollout; would touch a committed worked-example)
- [ ] 8.3 Convert the rest diagram-by-diagram behind their eval-parser support; keep sequence `alt`/failure fragments and AND/OR attack-tree gates in Mermaid/PlantUML — MIGRATION ACTION (rollout)

## 9. Verify
- [x] 9.1 `openspec validate add-offline-render-pipeline --strict` → exit 0
- [x] 9.2 Fresh-host preflight fails loud with a clear missing-dependency message (verified: names missing icons/font/resvg tier and exits 1)
- [ ] 9.3 Air-gap render smoke: network blocked, resvg tier produces non-blank PNGs and the plain-label constraint holds — SVG-offline + fallback-fail-loud verified; the resvg non-blank-PNG leg needs the `resvg` binary installed
- [ ] 9.4 A re-run produces `report.html` with an inline `<svg>` diagram, no Mermaid CDN, and `verify_run.sh` passes — `verify_run.sh` acceptance verified in isolation (inline-SVG-only report PASSes, CDN ref still FAILs); a full pipeline re-run needs the agents + binaries
