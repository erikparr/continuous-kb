#!/usr/bin/env bash
# Install the pre-commit hook that runs the contradiction commit gate.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d .git ] || { echo "install-hooks: not a git repo" >&2; exit 1; }
mkdir -p .git/hooks
cat > .git/hooks/pre-commit <<'EOF'
#!/usr/bin/env bash
exec "$(git rev-parse --show-toplevel)/scripts/kb-gate.sh"
EOF
chmod +x .git/hooks/pre-commit
echo "install-hooks: pre-commit gate installed"
