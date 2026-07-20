#!/usr/bin/env bash
# Fixture tests for scripts/kb-gate.sh. Run: bash tests/test_kb_gate.sh
set -u
GATE="$(cd "$(dirname "$0")/.." && pwd)/scripts/kb-gate.sh"
fails=0

check() { # desc expected_exit dir
  bash "$GATE" "$3" >/dev/null 2>&1
  got=$?
  if [ "$got" -ne "$2" ]; then echo "FAIL: $1 (want exit $2, got $got)"; fails=1; else echo "ok: $1"; fi
}

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

mkdir -p "$tmp/hard/entities"
cat > "$tmp/hard/entities/x.md" <<'EOF'
---
title: X
---
Contradiction severity: hard
Status: Unresolved — flagged for review
Detail: fee is $10k in v5 but $12k in v6
EOF
check "hard unresolved blocks" 1 "$tmp/hard"

mkdir -p "$tmp/soft/entities"
cat > "$tmp/soft/entities/x.md" <<'EOF'
---
title: X
---
Contradiction severity: soft
Status: Unresolved — flagged for review
Detail: naming tension between two decks
EOF
check "soft unresolved passes" 0 "$tmp/soft"

mkdir -p "$tmp/resolved/entities"
cat > "$tmp/resolved/entities/x.md" <<'EOF'
---
title: X
---
Contradiction severity: hard
Status: Resolved — v6 figure confirmed by countersigned copy
Detail: fee is $12k
EOF
check "resolved hard passes" 0 "$tmp/resolved"

check "missing dir is usage error" 2 "$tmp/nope"

exit $fails
