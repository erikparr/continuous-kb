# Continuous KB Template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `continuous-kb` GitHub template repository: generalized schema, three workflow skills, deterministic lint/gate scripts, and skeleton, then publish it as a template under `erikparr`.

**Architecture:** Three layers — durable schema in `CLAUDE.md`, procedure in `.claude/skills/` (kb-sync, kb-ingest, kb-lint), deterministic tooling in `scripts/` (python lint checker, bash commit gate, hooks installer, Quartz viewer). `raw/` is immutable source input; `wiki/` is agent-owned output.

**Tech Stack:** Python 3 (stdlib only), bash, git hooks, Quartz v4 (fetched at runtime, not vendored), gh CLI.

## Global Constraints

- Repo root: `/Users/erikparr/Documents/continuous-kb` (branch `main`, already initialized, spec committed).
- Scripts must be stdlib/POSIX-tool only — no pip installs, no npm deps outside the runtime-cloned `quartz/`.
- `kb-lint.py` exits 0 clean / 1 findings / 2 usage error; `kb-gate.sh` exits 0 clean / 1 blocked / 2 usage error.
- Never reference "Lennox" or client specifics anywhere in the template content.
- All commits end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.
- Publish target: public repo `erikparr/continuous-kb`, `is_template=true`, no license file.

---

### Task 1: Repo skeleton

**Files:**
- Create: `.gitignore`, `raw/sources/.gitkeep`, `raw/assets/.gitkeep`, `wiki/entities/.gitkeep`, `wiki/concepts/.gitkeep`, `wiki/summaries/.gitkeep`, `wiki/index.md`, `wiki/log.md`

**Interfaces:**
- Produces: directory layout that `kb-lint.py` (Task 2), `kb-gate.sh` (Task 3), and all docs assume. `wiki/index.md` catalog lines use `- [[slug]] — one-line summary` under `## Entities` / `## Concepts` / `## Summaries` headings.

- [ ] **Step 1: Write `.gitignore`**

```gitignore
.DS_Store
.obsidian/
quartz/
node_modules/
```

- [ ] **Step 2: Write seeded `wiki/index.md`**

```markdown
# Index

Catalog of every wiki page, one line each: `- [[slug]] — one-line summary`.
Updated on every ingest.

## Entities

## Concepts

## Summaries
```

- [ ] **Step 3: Write seeded `wiki/log.md`**

```markdown
# Log

Append-only chronological record of ingests and lints. Newest entry last.
Each entry: date, action (ingest | scoped lint | full lint), sources involved,
pages touched.

---
```

- [ ] **Step 4: Create `.gitkeep` files**

Run: `mkdir -p raw/sources raw/assets wiki/entities wiki/concepts wiki/summaries && touch raw/sources/.gitkeep raw/assets/.gitkeep wiki/entities/.gitkeep wiki/concepts/.gitkeep wiki/summaries/.gitkeep`

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "Add repo skeleton: raw/, wiki/ seeded index and log"
```

### Task 2: `kb-lint.py` deterministic checker (TDD)

**Files:**
- Create: `scripts/kb-lint.py`
- Test: `tests/test_kb_lint.py`

**Interfaces:**
- Produces: `scripts/kb-lint.py [--json] [root]`. Findings are `{check, page, detail}`; checks: `broken-wikilink`, `orphan`, `frontmatter`, `missing-source`, `index-mismatch`, `missing-summary`. Exit 0/1/2 per Global Constraints. Task 6 skills and Task 5 schema reference it by this path and contract.

- [ ] **Step 1: Write the failing test**

`tests/test_kb_lint.py`:

```python
#!/usr/bin/env python3
"""Fixture tests for scripts/kb-lint.py. Stdlib only. Run: python3 tests/test_kb_lint.py"""
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "kb-lint.py"


def page(title, ptype, sources, body, updated="updated: 2026-07-19\n"):
    src = "[" + ", ".join(sources) + "]"
    return f"---\ntitle: {title}\ntype: {ptype}\nsources: {src}\n{updated}status: ok\n---\n\n{body}\n"


def run_lint(root):
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--json", str(root)],
        capture_output=True, text=True,
    )
    return proc.returncode, json.loads(proc.stdout) if proc.stdout.strip() else []


class KbLintTest(unittest.TestCase):
    def build_fixture(self, root):
        for d in ("wiki/entities", "wiki/concepts", "wiki/summaries", "raw/sources", "raw/assets"):
            (root / d).mkdir(parents=True)
        (root / "raw/sources/doc-a.md").write_text("# Doc A\n")
        (root / "raw/sources/doc-b.md").write_text("# Doc B\n")  # never cited -> missing-summary
        (root / "wiki/entities/alpha.md").write_text(
            page("Alpha", "entity", ["raw/sources/doc-a.md", "raw/sources/nope.md"],  # -> missing-source
                 "Works with [[beta]] and [[ghost]]."))  # ghost -> broken-wikilink
        (root / "wiki/concepts/beta.md").write_text(
            page("Beta", "concept", ["raw/sources/doc-a.md"], "See [[alpha]].", updated=""))  # -> frontmatter
        (root / "wiki/concepts/lonely.md").write_text(
            page("Lonely", "concept", ["raw/sources/doc-a.md"], "Nothing links here."))  # -> orphan
        (root / "wiki/summaries/doc-a.md").write_text(
            page("Doc A summary", "summary", ["raw/sources/doc-a.md"], "Covers [[alpha]]."))
        (root / "wiki/index.md").write_text(
            "# Index\n\n## Entities\n- [[alpha]] — a\n\n## Concepts\n- [[beta]] — b\n"
            "- [[legacy]] — gone\n\n## Summaries\n- [[doc-a]] — s\n")  # lonely missing, legacy dangling
        (root / "wiki/log.md").write_text("# Log\n---\n")

    def test_dirty_fixture_finds_every_check_class(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.build_fixture(root)
            code, findings = run_lint(root)
            self.assertEqual(code, 1)
            by_check = {}
            for f in findings:
                by_check.setdefault(f["check"], []).append(f)
            self.assertEqual(len(by_check.get("broken-wikilink", [])), 1)   # ghost
            self.assertEqual(len(by_check.get("missing-source", [])), 1)    # nope.md
            self.assertEqual(len(by_check.get("frontmatter", [])), 1)       # beta missing updated
            self.assertEqual(len(by_check.get("missing-summary", [])), 1)   # doc-b
            orphan_pages = {f["page"] for f in by_check.get("orphan", [])}
            self.assertIn("wiki/concepts/lonely.md", orphan_pages)
            index_details = " | ".join(f["detail"] for f in by_check.get("index-mismatch", []))
            self.assertIn("lonely", index_details)   # page not in index
            self.assertIn("legacy", index_details)   # index entry with no page

    def test_clean_skeleton_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for d in ("wiki/entities", "wiki/concepts", "wiki/summaries", "raw/sources"):
                (root / d).mkdir(parents=True)
            (root / "wiki/index.md").write_text("# Index\n\n## Entities\n\n## Concepts\n\n## Summaries\n")
            (root / "wiki/log.md").write_text("# Log\n---\n")
            code, findings = run_lint(root)
            self.assertEqual(code, 0)
            self.assertEqual(findings, [])

    def test_missing_wiki_dir_is_usage_error(self):
        with tempfile.TemporaryDirectory() as td:
            proc = subprocess.run([sys.executable, str(SCRIPT), td], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 tests/test_kb_lint.py`
Expected: errors — `scripts/kb-lint.py` does not exist.

- [ ] **Step 3: Write `scripts/kb-lint.py`**

```python
#!/usr/bin/env python3
"""kb-lint: deterministic checks for a continuous-kb wiki. Pure disk I/O — no model judgment.

Checks:
  broken-wikilink   [[slug]] with no matching wiki page
  orphan            content page with no inbound wikilink from another content page
  frontmatter       missing frontmatter block or required keys (title, type, sources, updated)
  missing-source    frontmatter `sources:` path that doesn't exist on disk
  index-mismatch    content page absent from wiki/index.md, or index entry with no page
  missing-summary   raw source doc (raw/**, excluding raw/assets/) cited by no summaries/ page

Usage: kb-lint.py [--json] [root]     Exit: 0 clean, 1 findings, 2 usage error.
"""
import argparse
import json
import re
import sys
from pathlib import Path

CONTENT_DIRS = ("entities", "concepts", "summaries")
REQUIRED_KEYS = ("title", "type", "sources", "updated")
WIKILINK_RE = re.compile(r"\[\[([^\]|#]+)(?:[#|][^\]]*)?\]\]")


def parse_frontmatter(text):
    """Minimal YAML subset: `key: value`, inline `[a, b]` lists, `- item` block lists."""
    if not text.startswith("---"):
        return {}, False
    end = text.find("\n---", 3)
    if end == -1:
        return {}, False
    data, key = {}, None
    for line in text[3:end].splitlines():
        if not line.strip() or line.strip().startswith("#"):
            continue
        m = re.match(r"^(\w[\w-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val.startswith("[") and val.endswith("]"):
                data[key] = [v.strip() for v in val[1:-1].split(",") if v.strip()]
            else:
                data[key] = val
        elif key and line.strip().startswith("- "):
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(line.strip()[2:].strip())
    return data, True


def main():
    ap = argparse.ArgumentParser(description="deterministic continuous-kb checks")
    ap.add_argument("root", nargs="?", default=".", help="repo root (default: cwd)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    wiki = root / "wiki"
    if not wiki.is_dir():
        print(f"kb-lint: no wiki/ under {root}", file=sys.stderr)
        return 2

    findings = []

    def add(check, path, detail):
        findings.append({"check": check, "page": str(path.relative_to(root)), "detail": detail})

    pages = {}
    for d in CONTENT_DIRS:
        for p in sorted((wiki / d).glob("*.md")):
            pages[p.stem] = p

    inbound = {slug: 0 for slug in pages}
    summary_cited = set()

    for slug, p in sorted(pages.items()):
        text = p.read_text(encoding="utf-8")
        fm, ok = parse_frontmatter(text)
        if not ok:
            add("frontmatter", p, "missing or unterminated frontmatter block")
        else:
            missing = [k for k in REQUIRED_KEYS if k not in fm]
            if missing:
                add("frontmatter", p, "missing keys: " + ", ".join(missing))
        srcs = fm.get("sources", [])
        if isinstance(srcs, str):
            srcs = [srcs] if srcs else []
        for s in srcs:
            if s and not (root / s).exists():
                add("missing-source", p, f"sources entry not on disk: {s}")
        if p.parent.name == "summaries":
            summary_cited.update(srcs)
        for m in WIKILINK_RE.finditer(text):
            target = m.group(1).strip()
            if target in pages:
                if target != slug:
                    inbound[target] += 1
            else:
                add("broken-wikilink", p, f"[[{target}]] has no page")

    for slug, n in sorted(inbound.items()):
        if n == 0:
            add("orphan", pages[slug], "no inbound wikilinks from content pages")

    index = wiki / "index.md"
    index_text = index.read_text(encoding="utf-8") if index.exists() else ""
    for slug, p in sorted(pages.items()):
        if slug not in index_text:
            add("index-mismatch", p, f"page not listed in wiki/index.md: {slug}")
    for m in WIKILINK_RE.finditer(index_text):
        target = m.group(1).strip()
        if target not in pages:
            add("index-mismatch", index, f"index entry with no page: [[{target}]]")

    raw = root / "raw"
    if raw.is_dir():
        for p in sorted(raw.rglob("*.md")):
            rel = p.relative_to(root)
            if rel.parts[:2] == ("raw", "assets"):
                continue
            if str(rel) not in summary_cited:
                add("missing-summary", p, "no summaries/ page cites this source")

    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        for f in findings:
            print(f"{f['check']:16} {f['page']}: {f['detail']}")
        print(f"kb-lint: {len(findings)} finding(s)" if findings else "kb-lint: clean")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
```

Then: `chmod +x scripts/kb-lint.py`

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 tests/test_kb_lint.py`
Expected: `OK` (3 tests).

- [ ] **Step 5: Commit**

```bash
git add scripts/kb-lint.py tests/test_kb_lint.py && git commit -m "Add kb-lint.py deterministic checker with fixture tests"
```

### Task 3: `kb-gate.sh` commit gate + hooks installer (TDD)

**Files:**
- Create: `scripts/kb-gate.sh`, `scripts/install-hooks.sh`
- Test: `tests/test_kb_gate.sh`

**Interfaces:**
- Consumes: schema §5 status-line format (`Contradiction severity: hard|soft` followed within 3 lines by `Status: Unresolved …`).
- Produces: `scripts/kb-gate.sh [wiki-dir]` (default `wiki`), exit 0 clean / 1 blocked / 2 usage error. `scripts/install-hooks.sh` installs it as `.git/hooks/pre-commit`. Task 5/6 docs reference both by path.

- [ ] **Step 1: Write the failing test**

`tests/test_kb_gate.sh`:

```bash
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `bash tests/test_kb_gate.sh`
Expected: FAILs — `scripts/kb-gate.sh` does not exist.

- [ ] **Step 3: Write `scripts/kb-gate.sh` and `scripts/install-hooks.sh`**

`scripts/kb-gate.sh`:

```bash
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
```

`scripts/install-hooks.sh`:

```bash
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
```

Then: `chmod +x scripts/kb-gate.sh scripts/install-hooks.sh`

- [ ] **Step 4: Run test to verify it passes**

Run: `bash tests/test_kb_gate.sh`
Expected: four `ok:` lines, exit 0.

- [ ] **Step 5: Commit**

```bash
git add scripts/kb-gate.sh scripts/install-hooks.sh tests/test_kb_gate.sh && git commit -m "Add contradiction commit gate and pre-commit hook installer"
```

### Task 4: `serve-site.sh` Quartz viewer

**Files:**
- Create: `scripts/serve-site.sh`

**Interfaces:**
- Consumes: `wiki/` as content root.
- Produces: local site at `http://localhost:8080`; `quartz/` created at runtime (gitignored by Task 1).

- [ ] **Step 1: Write `scripts/serve-site.sh`** (generalized from the pilot — identical logic, no project references)

```bash
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
```

Then: `chmod +x scripts/serve-site.sh`

- [ ] **Step 2: Syntax check**

Run: `bash -n scripts/serve-site.sh`
Expected: no output, exit 0.

- [ ] **Step 3: Commit**

```bash
git add scripts/serve-site.sh && git commit -m "Add Quartz viewer script"
```

### Task 5: Generalized `CLAUDE.md` schema

**Files:**
- Create: `CLAUDE.md`

**Interfaces:**
- Consumes: script paths/contracts from Tasks 2–4; skill names from Task 6 (`kb-sync`, `kb-ingest`, `kb-lint`).
- Produces: the load-bearing per-instance schema, with a Project config section instantiators fill in.

- [ ] **Step 1: Write `CLAUDE.md`** — full content specified in the spec's Architecture section, concretely:

Sections, in order (content adapted from the validated pilot schema, generalized):
0. **Project config** — fill-in block: project name, source channels table (channel name, kind, locator e.g. Drive folder ID or local path, notes), ingest cadence. Explicit instruction that this section is the only per-instance edit the schema needs.
1. **Layout & ownership** — `raw/` immutable (`raw/sources/` converted markdown, subdirectories per channel allowed; `raw/assets/` originals/binaries), `wiki/` agent-owned (`index.md`, `log.md`, `entities/`, `concepts/`, `summaries/`), hard rule: never write under `raw/` except via approved intake.
2. **Page conventions** — frontmatter block (title/type/sources/updated/status), wikilinks, kebab-case stable slugs, one thing per page, anchor claims to sources.
3. **Workflows** — pointers: sync = `/kb-sync` (report before ingest is the contract), ingest = `/kb-ingest` (scoped, 8–15 pages), full lint = `/kb-lint`.
4. **Supersession** — versioned-source rule with `Superseded: <old> → <new> (source: vN → vM, <date>)` line; confident-but-stale synthesis named as the #1 failure mode.
5. **Contradiction status lines** — the hard/soft machine-readable block, verbatim format from the pilot.
6. **Deterministic vs. model split** — bookkeeping in `scripts/` (`kb-lint.py` contract + exit codes, `kb-gate.sh` + `install-hooks.sh`, `serve-site.sh`); model reserved for synthesis/contradiction reasoning/what's-missing.
7. **Lint** — scoped on every ingest, full periodically; every lint appended to `log.md`.

- [ ] **Step 2: Verify no project-specific leakage**

Run: `grep -ri "lennox\|geniant\|msa\|sow" CLAUDE.md`
Expected: no matches.

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md && git commit -m "Add generalized continuous-kb schema"
```

### Task 6: Workflow skills

**Files:**
- Create: `.claude/skills/kb-sync/SKILL.md`, `.claude/skills/kb-ingest/SKILL.md`, `.claude/skills/kb-lint/SKILL.md`

**Interfaces:**
- Consumes: Project config section (Task 5), `scripts/kb-lint.py` and `scripts/kb-gate.sh` contracts (Tasks 2–3), `wiki/log.md` entry format (Task 1).
- Produces: slash-invocable `/kb-sync`, `/kb-ingest`, `/kb-lint` in any instantiated repo.

- [ ] **Step 1: Write `kb-sync/SKILL.md`** — frontmatter `name: kb-sync`, `description:` trigger on "sync", "any new docs", "check sources". Body: (a) read Project config channels; (b) list each channel via its kind-specific method; (c) diff against ingest records in `wiki/log.md`; (d) **report findings and STOP — never ingest without approval** (explicit "sync and ingest" counts as approval); (e) on approval: convert to clean markdown → `raw/sources/`, originals → `raw/assets/`, then hand to `/kb-ingest`. Includes the intake-options catalog: Google Drive (MCP tools, folder-ID listing, doc/sheet/slides export paths), local drop folder, Notion/Confluence markdown export, meeting transcripts and email (paste or file). Conversion rules: one `.md` per source doc, kebab-case filename (date-prefixed when the doc is dated), strip export junk, keep headings/tables.
- [ ] **Step 2: Write `kb-ingest/SKILL.md`** — frontmatter `name: kb-ingest`, description trigger on "ingest". Body: the scoped workflow — read changed sources; load only touched pages + 1st/2nd-degree wikilink neighbors (typically 8–15 pages, never the whole wiki); write/update entity/concept/summary pages (always one `summaries/<source-slug>.md` per source); apply supersession rule; contradiction check against the scoped neighbor set, adding §5 status lines on conflict; update `index.md` + append `log.md`; run `python3 scripts/kb-lint.py` and fix findings; commit (pre-commit gate enforces hard contradictions).
- [ ] **Step 3: Write `kb-lint/SKILL.md`** — frontmatter `name: kb-lint`, description trigger on "full lint", "sweep". Body: run `python3 scripts/kb-lint.py` and triage; model passes over the whole wiki: contradiction sweep, stale-synthesis check against newest sources, "what's missing" (entities/concepts referenced but never created); append findings + resolutions to `log.md`.
- [ ] **Step 4: Verify skill frontmatter parses**

Run: `head -5 .claude/skills/*/SKILL.md`
Expected: each begins `---` / `name: kb-…` / `description: …`.

- [ ] **Step 5: Commit**

```bash
git add .claude && git commit -m "Add kb-sync, kb-ingest, kb-lint workflow skills"
```

### Task 7: README

**Files:**
- Create: `README.md`

- [ ] **Step 1: Write `README.md`** — lean, personal-first: one-paragraph what/why (self-maintaining interlinked markdown wiki built from source documents, contradiction tracking, supersession discipline); the three-layer map (schema / skills / scripts); quickstart (Use this template → fill Project config in `CLAUDE.md` → `./scripts/install-hooks.sh` → open in Claude Code → `/kb-sync` → `./scripts/serve-site.sh`); scripts reference table with exit codes; note that `raw/` is immutable and `wiki/` is agent-owned.
- [ ] **Step 2: Commit**

```bash
git add README.md && git commit -m "Add README"
```

### Task 8: Real-world smoke test against the pilot wiki

**Files:**
- None created (read-only check).

- [ ] **Step 1: Run the checker against the pilot repo**

Run: `python3 scripts/kb-lint.py /Users/erikparr/Documents/_geniant/lennox | tail -20`
Expected: exit 1 with plausible findings (the pilot never had this checker; `missing-summary` findings expected since pilot uses `raw/drive/` naming — confirm the checker handles `raw/` subdirs generically and output is sane, not a crash).

- [ ] **Step 2: Sanity-judge output** — findings must be true statements about the pilot wiki (spot-check 2–3). Fix checker bugs revealed, re-run fixture tests, amend Task 2 commit if needed.

### Task 9: Publish to GitHub as a template

- [ ] **Step 1: Create and push**

Run: `gh repo create continuous-kb --public --source /Users/erikparr/Documents/continuous-kb --push --description "Self-maintaining markdown knowledge base — template repo: agent-maintained wiki with contradiction tracking, supersession discipline, deterministic lint"`
Expected: repo `erikparr/continuous-kb` created, `main` pushed.

- [ ] **Step 2: Flag as template**

Run: `gh api -X PATCH repos/erikparr/continuous-kb -f is_template=true --jq .is_template`
Expected: `true`

- [ ] **Step 3: Verify**

Run: `gh repo view erikparr/continuous-kb --json isTemplate,url,defaultBranchRef`
Expected: `isTemplate: true`, url present, branch `main`.
