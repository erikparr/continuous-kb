#!/usr/bin/env bash
# Build + serve the browsable knowledge-base site from wiki/ using Quartz v4.
# The wiki/ markdown is the source of truth; quartz/ is a generated view (gitignored).
#
# Usage: ./scripts/serve-site.sh   ->  http://localhost:8080
set -euo pipefail
cd "$(dirname "$0")/.."

# Quartz v4 needs Node >= 22. Prefer a Homebrew node if the default is older.
if [ -x /opt/homebrew/bin/node ] && [ "$(/opt/homebrew/bin/node -e 'process.stdout.write(String(process.versions.node.split(".")[0]))')" -ge 22 ]; then
  export PATH=/opt/homebrew/bin:$PATH
fi
NODE_MAJOR="$(node -e 'process.stdout.write(String(process.versions.node.split(".")[0]))')"
if [ "$NODE_MAJOR" -lt 22 ]; then
  echo "Need Node >= 22 (have $(node --version)). Install/select Node 22+ and retry." >&2
  exit 1
fi

# One-time: fetch Quartz v4 and install deps.
if [ ! -d quartz ]; then
  echo "Cloning Quartz v4..."
  git clone -q -b v4 --depth 1 https://github.com/jackyzha0/quartz.git quartz
  rm -rf quartz/.git
  ( cd quartz && npm install --no-audit --no-fund )
fi

# Build from wiki/ and serve with hot reload.
# Quartz must run from inside its own dir (it reads ./package.json); -d ../wiki points back to content.
cd quartz
exec node ./quartz/bootstrap-cli.mjs build -d ../wiki --serve --port 8080
