#!/usr/bin/env bash
# kb-gate: block commits while any HARD contradiction is unresolved.
# A page blocks when "Contradiction severity: hard" is followed within 3 lines
# by "Status: Unresolved". Soft contradictions never block.
# Usage: kb-gate.sh [wiki-dir]     Exit: 0 clean, 1 blocked, 2 usage error.
set -euo pipefail
WIKI_DIR="${1:-wiki}"
[ -d "$WIKI_DIR" ] || { echo "kb-gate: no such dir: $WIKI_DIR" >&2; exit 2; }

blocked=0
while IFS= read -r -d '' f; do
  if awk '
    /Contradiction severity:[[:space:]]*hard/ { armed = NR }
    armed && NR <= armed + 3 && /Status:[[:space:]]*Unresolved/ { found = 1; exit }
    END { exit !found }
  ' "$f"; then
    echo "kb-gate: HARD unresolved contradiction in $f"
    grep -n "Detail:" "$f" | head -3 | sed 's/^/  /'
    blocked=1
  fi
done < <(find "$WIKI_DIR" -name '*.md' -print0)

if [ "$blocked" -eq 1 ]; then
  echo "kb-gate: commit blocked — resolve hard contradictions (set 'Status: Resolved — <how>')." >&2
  exit 1
fi
echo "kb-gate: clean"
