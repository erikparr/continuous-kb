# Continuous KB — generalized template design

Date: 2026-07-19
Status: approved (Approach A selected in brainstorming; user directed "proceed as recommended until complete")

## Purpose

Abstract the Lennox × geniant knowledge-base pilot into a reusable GitHub **template
repository**. Any project can instantiate it, point a source channel at `raw/`, and get a
self-maintaining, interlinked markdown wiki with contradiction tracking, supersession
discipline, and deterministic lint/gate tooling.

Audience: personal reuse first (Erik spinning up KBs for future projects). Public repo,
lean docs, opinionated defaults, no license ceremony.

## What we learned from the pilot (drives the design)

- The schema `CLAUDE.md` works as the load-bearing config, but it strained to hold both
  *schema* (durable conventions) and *procedure* (how to sync, how to ingest). Split them.
- The §6 deterministic scripts (commit gate, broken-link/orphan detection) were promised
  but never built — the biggest gap between the format's claims and reality. Build them.
- Report-before-ingest became the de-facto sync contract (user feedback on 2026-07-15).
  Bake it in as the default, not a per-user memory.
- Source-channel details (Drive folder IDs) lived only in agent memory. The template gets
  a per-instance config section so this state lives in the repo.

## Architecture

Three layers, one clear owner each:

1. **Schema (`CLAUDE.md`)** — durable conventions the agent must always know: layout,
   page frontmatter, wikilinks/slugs, supersession rules, contradiction status lines,
   deterministic-vs-model split. Plus a fill-in **Project config** section (project name,
   source channels + IDs/paths, cadence). Short; procedure lives in skills.
2. **Procedure (`.claude/skills/`)** — three project-local skills, slash-invocable:
   - `kb-sync` — diff source channels against `wiki/log.md`, **report findings and stop**;
     ingest only on approval. Contains the intake-options catalog (Google Drive via MCP,
     local file drop, Notion/Confluence export, email/transcripts) with conversion
     guidance (clean markdown, one file per source doc, naming).
   - `kb-ingest` — the scoped ingest workflow: read changed sources → scope neighbor set
     (8–15 pages, not the whole wiki) → write/update entity/concept/summary pages →
     update index.md, append log.md → contradiction check → run `kb-lint.py` → commit
     through the gate.
   - `kb-lint` — full-wiki backstop: run the deterministic checker, then model-judgment
     passes (contradiction sweep, stale-synthesis check, "what's missing"), append to log.
3. **Deterministic tooling (`scripts/`)** — pure disk I/O, no model:
   - `kb-lint.py` (python3, stdlib only) — broken wikilinks, orphan pages, missing/invalid
     frontmatter, `sources:` entries pointing at nonexistent raw files, pages missing from
     `index.md` and vice versa, missing `summaries/` page per raw source. Exit non-zero on
     findings; `--json` for machine use.
   - `kb-gate.sh` — commit gate: grep `wiki/` for `Status: Unresolved` with
     `Contradiction severity: hard`; any hit blocks the commit and prints the pages.
   - `install-hooks.sh` — installs a pre-commit hook that runs `kb-gate.sh`.
   - `serve-site.sh` — Quartz v4 viewer, generalized from the pilot (clones quartz on
     first run; `quartz/` gitignored).

## Repo layout (the template itself)

```
continuous-kb/
├── README.md                 # what/why, quickstart, layer map — lean, personal-first
├── CLAUDE.md                 # schema + Project config placeholders
├── .gitignore                # quartz/, .DS_Store, .obsidian
├── .claude/skills/
│   ├── kb-sync/SKILL.md
│   ├── kb-ingest/SKILL.md
│   └── kb-lint/SKILL.md
├── scripts/
│   ├── kb-lint.py
│   ├── kb-gate.sh
│   ├── install-hooks.sh
│   └── serve-site.sh
├── raw/
│   ├── sources/.gitkeep      # converted markdown, one file per source doc (subdirs ok)
│   └── assets/.gitkeep       # originals/binaries kept for provenance
├── wiki/
│   ├── index.md              # seeded catalog header
│   ├── log.md                # seeded log header
│   ├── entities/.gitkeep
│   ├── concepts/.gitkeep
│   └── summaries/.gitkeep
└── docs/superpowers/specs/   # this spec + future plans
```

Generalizations from the pilot: `raw/drive/` → `raw/sources/` (source-agnostic; channel
subdirectories allowed), pilot context section → Project config placeholders, Drive-only
intake → catalog of intake options in `kb-sync`.

## Data flow

source channel → (kb-sync: diff vs log.md → **report → approval**) → raw/sources/ +
raw/assets/ → (kb-ingest: scoped wiki rewrite) → wiki/ → (kb-lint.py + kb-gate.sh) →
commit → (serve-site.sh) browsable site.

## Error handling

- Hard contradictions block commits at the gate; the gate prints file + Detail line.
- `kb-lint.py` findings are warnings by default inside ingest (agent fixes then re-runs);
  the gate is the only hard stop.
- Scripts degrade clearly: missing python3/node → explicit message, non-zero exit.

## Testing

- Fixture-based: a throwaway wiki with a deliberate broken wikilink, an orphan page, a
  missing summary, and one `hard` contradiction. Assert `kb-lint.py` finds each class and
  `kb-gate.sh` exits non-zero; assert clean skeleton passes both.
- Real-world smoke: run `kb-lint.py` read-only against the Lennox `wiki/` and eyeball
  that output is sane (some findings expected; the pilot never had the checker).

## Out of scope (YAGNI)

- Intake connector code (auth, quotas, per-source conversion) — intake stays agent+MCP.
- Profiles (client-engagement / code-repo / research variants).
- CI workflows, license file, example fictional corpus.
- Migrating the Lennox repo onto the template (separate task if ever desired).
