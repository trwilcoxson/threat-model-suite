#!/usr/bin/env bash
# Extension-dispatching render seam for threat-model diagrams (add-offline-render-pipeline).
#
# Renders every diagram artifact in an output dir BY FILE EXTENSION — `.mmd` -> mermaid-cli,
# `.d2` -> the offline D2 toolchain — independent of which phase emitted it. This is the migration
# seam: both engines coexist, `.mmd` stays renderable forever (committed worked-examples never
# break), and a diagram source in an extension no renderer handles fails LOUD (never a report
# silently missing a diagram). All rendering is offline; a missing binary is the air-gap preflight
# surfacing at render time as a clear, named failure rather than a blank output.
#
# Usage: render_diagrams.sh <output_dir> [refs_dir]
# Env:   TM_RENDER_TIER  = primary | fallback   which PNG tier for .d2 (default: auto-detect)
#        TM_BROWSER_CACHE = path                 warmed headless-browser cache (primary tier)
#        D2_LAYOUT        = elk | dagre          pinned free/offline/deterministic layout (default: elk)
# Exit:  0 all diagrams rendered; nonzero on the FIRST hard failure — missing binary, unknown
#        extension, remote icon URL, or a blank/degenerate raster — naming the offending item.
set -euo pipefail

OUT="${1:?usage: render_diagrams.sh <output_dir> [refs_dir]}"
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REFS="${2:-$SELF_DIR/../references}"
CONFIG="$REFS/mermaid-config.json"
LAYOUT="${D2_LAYOUT:-elk}"          # free, offline, deterministic — never TALA, never a network layout
PNG_FLOOR=1024                      # a genuinely blank/degenerate PNG is tiny (bytes)
TIERS="$OUT/.render-tiers"          # per-diagram engine + tier + fidelity, folded into the generation log

die()  { echo "RENDER FAIL: $*" >&2; exit 1; }
log()  { echo "render: $*"; }

# Fail loud if a required binary is absent — this IS the air-gap preflight, at render time.
need() {
  command -v "$1" >/dev/null 2>&1 || \
    die "'$1' not found on PATH — offline renderer missing. Install it, or run scripts/ensure_renderer.sh at pipeline start so this surfaces as a startup error instead."
}

# The fallback tier's browser-free SVG->PNG rasterizer: librsvg's rsvg-convert or resvg — either
# satisfies the tier (both pure/offline, no headless browser). Echoes the tool name; empty if neither.
fallback_rasterizer() {
  if command -v rsvg-convert >/dev/null 2>&1; then echo rsvg-convert
  elif command -v resvg >/dev/null 2>&1; then echo resvg
  fi
}

# A rasterized PNG must be a real, non-degenerate image — never embed a silent blank.
verify_png_nonblank() {
  local png="$1"
  [ -s "$png" ] || die "no PNG produced: $png"
  local sig; sig=$(head -c 8 "$png" | od -An -tx1 | tr -d ' \n')
  [ "$sig" = "89504e470d0a1a0a" ] || die "not a valid PNG (bad magic bytes): $png"
  local bytes; bytes=$(wc -c < "$png")
  [ "$bytes" -ge "$PNG_FLOOR" ] || \
    die "PNG is degenerate/blank ($bytes bytes < ${PNG_FLOOR} floor): $png — a browser-free rasterizer likely dropped a foreignObject label. Move the annotation to the adjacent matrix and use a plain single-line label."
  # ponytail: magic-byte + size-floor guard; upgrade to a pixel-variance check only if a byte-sized blank slips through.
}

# .mmd -> .png  (behaviour-identical to the pre-seam inline `npx ... mermaid-cli` call)
render_mmd() {
  local mmd="$1" png="${1%.mmd}.png"
  need npx
  log "mmd -> png: $mmd"
  npx -y @mermaid-js/mermaid-cli -i "$mmd" -o "$png" -c "$CONFIG" -w 3000 --scale 2 -b white \
    || die "mermaid-cli failed on $mmd"
  verify_png_nonblank "$png"
  printf '%s | mermaid | %s | full-fidelity\n' "$(basename "$mmd")" "$(basename "$png")" >> "$TIERS"
}

# .d2 -> .svg (inlined into report.html, offline, no CDN) + .png (two-tier for Office)
render_d2() {
  local d2="$1" svg="${1%.d2}.svg" png="${1%.d2}.png"
  need d2
  # Hermetic: reject remote icon URLs — they break air-gap AND render a broken icon while exiting 0.
  if grep -Eiq 'icon:[[:space:]]*["'"'"']?https?://' "$d2"; then
    die "remote icon URL in $d2 — reference a vendored LOCAL icon path. A remote icon breaks offline rendering and renders broken while the CLI still exits 0."
  fi
  # SVG for the HTML report (pure-Go, fully offline; the report-analyst inlines it directly).
  log "d2 -> svg: $d2"
  d2 --layout "$LAYOUT" --theme 0 "$d2" "$svg" || die "d2 SVG render failed on $d2"
  [ -s "$svg" ] || die "no SVG produced: $svg"

  # PNG for docx/pdf/pptx — two tiers. Honour a declared tier; else auto-detect.
  local tier="${TM_RENDER_TIER:-}"
  if [ -z "$tier" ]; then
    if [ -n "${TM_BROWSER_CACHE:-}" ] && [ -e "${TM_BROWSER_CACHE}" ]; then
      tier="primary"
    elif [ -n "$(fallback_rasterizer)" ]; then
      tier="fallback"
    else
      die "no PNG tier available for $d2 — need a warmed headless-browser cache (TM_BROWSER_CACHE, primary tier) or a browser-free rasterizer ('rsvg-convert' or 'resvg', fallback tier)."
    fi
  fi
  case "$tier" in
    primary)   # cached headless browser: offline after warm-up, full label fidelity
      log "d2 -> png (primary / cached browser): $d2"
      d2 --layout "$LAYOUT" --theme 0 "$d2" "$png" || die "d2 PNG (primary tier) failed on $d2"
      verify_png_nonblank "$png"
      printf '%s | d2 | %s | primary/browser/full-fidelity\n' "$(basename "$d2")" "$(basename "$png")" >> "$TIERS" ;;
    fallback)  # browser-free d2 -> svg -> (rsvg-convert|resvg) -> png; plain single-line labels only
      local raster; raster="$(fallback_rasterizer)"
      [ -n "$raster" ] || die "fallback tier requested for $d2 but no browser-free rasterizer on PATH (install 'rsvg-convert' or 'resvg')."
      log "d2 -> svg -> $raster -> png (fallback / browser-free): $d2"
      case "$raster" in
        rsvg-convert) rsvg-convert "$svg" -o "$png" || die "rsvg-convert failed on $svg" ;;
        resvg)        resvg "$svg" "$png"           || die "resvg failed on $svg" ;;
      esac
      verify_png_nonblank "$png"
      printf '%s | d2 | %s | fallback/%s/plain-labels\n' "$(basename "$d2")" "$(basename "$png")" "$raster" >> "$TIERS" ;;
    *) die "unknown TM_RENDER_TIER='$tier' (want primary|fallback)" ;;
  esac
}

[ -d "$OUT" ] || die "output dir not found: $OUT"
: > "$TIERS"

# Discover diagram artifacts. Sources are `.mmd`/`.d2`; the diagram-family basename globs also catch a
# source authored in an UNRECOGNISED DSL (e.g. a stray `structural-diagram.puml`) so it fails loud
# rather than being silently omitted. Already-rendered `.svg`/`.png` and non-diagram files are skipped.
shopt -s nullglob
files=(
  "$OUT"/*.mmd "$OUT"/*.d2
  "$OUT"/*-diagram.*     "$OUT"/*attack-tree*.* "$OUT"/*attack-flow*.*
  "$OUT"/*kill-chain*.*  "$OUT"/*auth-sequence*.* "$OUT"/*data-lifecycle*.*
)
# Dedup across the overlapping globs (bash-3.2-safe: no associative arrays on stock macOS bash).
seen=$'\n'
rendered=0
for f in "${files[@]}"; do
  [ -f "$f" ] || continue
  case "$seen" in *$'\n'"$f"$'\n'*) continue ;; esac
  seen="$seen$f"$'\n'
  case "$f" in
    *.mmd) render_mmd "$f"; rendered=$((rendered+1)) ;;
    *.d2)  render_d2  "$f"; rendered=$((rendered+1)) ;;
    *.svg|*.png|*.json|*.md|*.txt) : ;;          # rendered output / not a diagram source — skip
    *) die "diagram artifact '$f' has an extension no renderer handles (expected .mmd or .d2) — refusing to silently omit it" ;;
  esac
done

log "rendered $rendered diagram(s); tier ledger -> $TIERS"
[ "$rendered" -gt 0 ] || echo "render: WARN no .mmd/.d2 diagram sources found under $OUT" >&2
exit 0
