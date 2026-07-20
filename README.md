# continuous-kb

A template for a self-maintaining markdown knowledge base. An agent (Claude Code) ingests
source documents into an interlinked wiki — one page per entity, concept, and source —
with provenance on every claim, explicit supersession when sources get versioned, and
contradiction tracking that can block commits until conflicts are resolved.

Built from a validated single-project pilot (a client engagement KB fed by Google Drive),
then generalized: any source channel works as long as documents land in `raw/` as clean
markdown.

## How it's put together

Three layers, one owner each:

| Layer     | Where              | What                                                                                                       |
| --------- | ------------------ | ---------------------------------------------------------------------------------------------------------- |
| Schema    | `CLAUDE.md`        | Durable conventions: layout, page frontmatter, wikilinks, supersession, contradiction statuses. Fill in §0. |
| Procedure | `.claude/skills/`  | `/kb-sync` (find new docs, report first), `/kb-ingest` (scoped wiki rewrite), `/kb-lint` (full sweep).      |
| Tooling   | `scripts/`         | Deterministic bookkeeping — no model judgment involved.                                                     |

`raw/` is the immutable input (converted sources + originals); `wiki/` is the
agent-owned output. The agent never edits `raw/`, and humans rarely need to edit `wiki/`.

## Quickstart

1. **Use this template** on GitHub, clone your new repo.
2. Fill in **§0 Project config** in `CLAUDE.md` — project name and the source-channel
   table (Drive folder IDs, a local drop folder, export directory, …).
3. Run `./scripts/install-hooks.sh` once to install the commit gate.
4. Open the repo in Claude Code and run `/kb-sync` — it enumerates your channels,
   reports what it found, and (on your approval) ingests into the wiki.
5. Browse with `./scripts/serve-site.sh` → http://localhost:8080 (Quartz v4, needs
   Node ≥ 22; fetched on first run).

## Scripts

| Script             | Does                                                                                  | Exit codes                    |
| ------------------ | ------------------------------------------------------------------------------------- | ----------------------------- |
| `kb-lint.py`       | Broken wikilinks, orphans, bad frontmatter, dead source paths, index drift, uncited raw docs. `--json` for machine use. | 0 clean / 1 findings / 2 usage |
| `kb-gate.sh`       | Blocks commits while any **hard** contradiction is `Status: Unresolved`.               | 0 clean / 1 blocked / 2 usage  |
| `install-hooks.sh` | Installs `kb-gate.sh` as the pre-commit hook.                                          | —                             |
| `serve-site.sh`    | Builds and serves the wiki as a browsable site.                                        | —                             |

Tests: `python3 tests/test_kb_lint.py` and `bash tests/test_kb_gate.sh`.

## The two rules that matter

- **Report before ingest.** A sync reports what's new and stops; ingest runs on approval.
- **No confident-but-stale synthesis.** Newer source versions supersede loudly
  (`Superseded: old → new`), and unresolved factual conflicts block the commit.
