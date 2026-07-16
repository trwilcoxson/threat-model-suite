#!/usr/bin/env bash
# Fail-loud air-gap render PREFLIGHT (add-offline-render-pipeline). Runs at PIPELINE START so a
# missing renderer surfaces as a startup error — never as a silent blank five agents deep at Step 2.5.
#
# Verifies the offline render dependencies are present LOCALLY and DECLARES which PNG tier is active:
#   - d2 binary + a free deterministic layout   (SVG for HTML + PNG for Office)
#   - the tier's rasterizer:
#       * warmed headless-browser cache          -> PRIMARY tier (full label fidelity), OR
#       * rsvg-convert (librsvg) or resvg         -> FALLBACK tier (browser-free, plain single-line labels)
#   - vendored local icon set + font            (hermetic, no remote fetch)
#
# When the warmed browser cache is absent but a browser-free rasterizer (rsvg-convert or resvg) is
# present, the FALLBACK tier is declared active, which in turn enforces the plain-single-line-label
# constraint on the diagram source (the diagram check reads TM_RENDER_TIER=fallback and rejects
# |md|/multi-line/foreignObject labels that a browser-free rasterizer would silently blank).
#
# Usage: ensure_renderer.sh [refs_dir]
# Output (stdout, on success): `TM_RENDER_TIER=primary|fallback` — the orchestrator exports it into
#         the run environment so downstream render + eval steps see the declared tier.
# Exit:  0 renderer usable (tier printed to stdout); nonzero listing every missing hard dependency.
set -u
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REFS="${1:-$SELF_DIR/../references}"
ICONS="${TM_ICON_DIR:-$REFS/icons}"
FONT="${TM_FONT:-$REFS/fonts/SourceSansPro-Regular.ttf}"

fail=0
bad()  { echo "PREFLIGHT FAIL: $*" >&2; fail=1; }
have() { command -v "$1" >/dev/null 2>&1; }

# --- hard dep: without d2 no D2 diagram renders at all
have d2 || bad "'d2' binary not found — the D2 render toolchain is not installed (offline SVG + PNG both need it)"

# --- vendored, hermetic assets (referenced by LOCAL path so no network fetch happens at render time)
[ -d "$ICONS" ] || bad "vendored icon set absent ($ICONS) — icons must be local files; a remote icon breaks air-gap and renders broken while exiting 0"
[ -f "$FONT" ]  || bad "vendored font absent ($FONT) — a pinned local font keeps layout metrics deterministic"

# --- PNG tier: primary (warmed browser) if its cache is present; else a browser-free rasterizer
#     (librsvg's rsvg-convert or resvg) drives the fallback tier.
tier=""
if [ -n "${TM_BROWSER_CACHE:-}" ] && [ -e "${TM_BROWSER_CACHE}" ]; then
  tier="primary"
elif have rsvg-convert || have resvg; then
  tier="fallback"
else
  bad "no PNG tier available — provide a warmed headless-browser cache (set TM_BROWSER_CACHE for the primary tier) or install a browser-free rasterizer ('rsvg-convert' or 'resvg', fallback tier)"
fi

if [ "$fail" -ne 0 ]; then
  echo "PREFLIGHT: FAIL — fix the dependency/dependencies above before running the pipeline." >&2
  echo "(Intentional: fail loud at startup, not a blank diagram at Step 2.5 five agents deep.)" >&2
  exit 1
fi

echo "TM_RENDER_TIER=$tier"
echo "PREFLIGHT: OK — offline renderer present; '$tier' PNG tier active." >&2
[ "$tier" = "fallback" ] && \
  echo "PREFLIGHT: fallback tier active -> diagram sources are constrained to PLAIN single-line labels (rich annotations move to the adjacent matrix)." >&2
exit 0
