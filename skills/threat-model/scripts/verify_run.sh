#!/usr/bin/env bash
# Post-assessment verification for a threat-model run. Deterministic structure checks only —
# file existence, HTML integrity, and Execution Log presence. The parent orchestrator runs this
# after the report-analyst and re-spawns it (with the specific failures) on any FAIL.
#
# Usage: verify_run.sh <output_dir>
# Exit: 0 if no core/report/HTML failure, 1 otherwise (team-only files and logs are advisory).
set -u
OUT="${1:?usage: verify_run.sh <output_dir>}"
fail=0
ok()   { echo "OK: $*"; }
bad()  { echo "FAIL: $*"; fail=1; }

echo "== Core outputs + manifests =="
for f in 01-reconnaissance.md 02-structural-diagram.md 03-threat-identification.md \
         04-risk-quantification.md 05-false-negative-hunting.md 06-validated-findings.md \
         07-final-diagram.md 08-threat-model-report.md recon.json findings.json coverage.json; do
  [ -s "$OUT/$f" ] && ok "$f" || bad "missing $f"
done

echo "== Report deliverables =="
for f in report.html report.docx report.pdf executive-summary.pptx; do
  [ -s "$OUT/$f" ] && ok "$f ($(wc -c < "$OUT/$f") bytes)" || bad "missing $f"
done

H="$OUT/report.html"
if [ -s "$H" ]; then
  echo "== HTML content validation =="
  # A diagram embed is either a pre-rendered PNG <img> OR an inline offline <svg> (D2, no browser at
  # render time). Either satisfies the embed check; the Mermaid-CDN/runtime ban below is unchanged.
  imgs=$(grep -c '<img' "$H"); svgs=$(grep -c '<svg' "$H")
  if [ "$imgs" -ge 1 ] || [ "$svgs" -ge 1 ]; then ok "diagram embeds present ($imgs <img> PNG, $svgs inline <svg>)"; else bad "report.html has no diagram embed (<img> PNG or inline <svg>)"; fi
  # Mermaid CDN / client-side render, not the mere word "mermaid" (a caption may mention it).
  grep -qiE 'mermaid[^"]*\.(js|min\.js)|cdn[^"]*mermaid|mermaid\.initialize' "$H" \
    && bad "report.html references the Mermaid CDN/runtime — embed pre-rendered PNGs" || ok "no Mermaid CDN"
  grep -q '<\\/script>' "$H" && bad 'report.html contains <\/script> (JS escape breaks the parser)' || ok "no broken script escapes"
  o=$(grep -c '<script' "$H"); c=$(grep -c '</script>' "$H")
  [ "$o" -eq "$c" ] && ok "script tags balanced ($o/$c)" || bad "mismatched script tags (open=$o close=$c)"
  grep -q '<body' "$H" && ok "body tag present" || bad "no body tag"
  grep -q '</html>' "$H" && ok "html closed" || bad "html not closed"
fi

echo "== Execution logs =="
for f in 01-reconnaissance.md 02-structural-diagram.md 05-false-negative-hunting.md \
         08-threat-model-report.md 07-final-diagram.md; do
  [ -s "$OUT/$f" ] && { grep -q '## Execution Log' "$OUT/$f" && ok "$f log" || echo "WARN: $f has no Execution Log"; }
done
for f in privacy-assessment.md compliance-gap-analysis.md code-security-review.md validation-report.md; do
  [ -s "$OUT/$f" ] && { grep -q '## Execution Log' "$OUT/$f" && ok "$f log" || echo "WARN: $f has no Execution Log"; }
done
[ -s "$OUT/report-generation-log.md" ] && ok "report-generation-log.md" || echo "WARN: no report-generation-log.md"

echo
[ "$fail" -eq 0 ] && echo "VERIFY: PASS" || echo "VERIFY: FAIL (see FAIL lines above)"
exit "$fail"
