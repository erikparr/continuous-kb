# Continuous Knowledge Base — Schema & Workflows

This repo is a self-maintaining, interlinked markdown wiki built from source documents.
You (the agent) are its disciplined maintainer. This file is the load-bearing config.
Read it fully before any sync, ingest, query, or lint.

Durable conventions live here. Step-by-step procedure lives in the project skills:
`/kb-sync` (find new sources), `/kb-ingest` (fold them into the wiki), `/kb-lint`
(full-wiki backstop).

---

## 0. Project config (fill in per instance)

This section is the only per-instance edit this file needs. Everything below it is the
format itself.

```
Project:        <name of the engagement / effort this KB covers>
Ingest cadence: <on-demand | daily | per-meeting | ...>
```

**Source channels** — where documents come from. One row per channel; `/kb-sync` reads
this table.

| Channel | Kind                          | Locator (folder ID / path / URL) | Notes |
| ------- | ----------------------------- | -------------------------------- | ----- |
| <name>  | drive \| local \| export \| … | <id-or-path>                     |       |

---

## 1. Layout & ownership

```
raw/        IMMUTABLE source of truth. You READ, never edit.
  sources/    Source docs converted to clean markdown (one .md per doc;
              subdirectories per channel are fine, e.g. raw/sources/drive/).
  assets/     Original PDFs, images, binaries kept for provenance.
wiki/       You OWN this entirely — generated, maintained, linted.
  index.md      Content catalog: every page + one-line summary. Updated every ingest.
  log.md        Append-only chronological record of ingests and lints.
  entities/     One page per person / org / system / component / artifact.
  concepts/     One page per idea / topic / decision / process.
  summaries/    One page per source document.
CLAUDE.md   This schema.
```

Hard rule: **never write under `raw/` except when landing approved intake.** If a source
is wrong, flag it in the wiki — don't edit the source.

---

## 2. Page conventions

Every wiki page starts with frontmatter:

```markdown
---
title: <human title>
type: entity | concept | summary
sources: [raw/sources/<file>.md, ...]  # provenance — which raw docs this page draws on
updated: <YYYY-MM-DD>                  # last ingest that touched this page
status: ok                             # or: Status: Unresolved (see §5)
---
```

- **Wikilinks:** link related pages with `[[page-slug]]` using the filename without
  extension or directory. A link to a page that doesn't exist yet is fine — it marks a
  page worth creating.
- **Slugs:** kebab-case, stable. Don't rename a page without updating inbound links.
- **One thing per page.** A person, an org, a single concept. Split rather than bloat.
- **Anchor claims to sources.** Material claims should trace to a source. Prefer a short
  quote + provenance over unsourced synthesis. This is what lets contradictions be caught.

---

## 3. Workflows

- **`/kb-sync`** — enumerate the §0 source channels, diff against the ingest records in
  `wiki/log.md`, and **report what's new, then stop**. Ingest runs only on approval; an
  explicit "sync and ingest" request covers both.
- **`/kb-ingest`** — scoped rewrite: load only the pages a source touches plus their
  1st/2nd-degree wikilink neighbors (typically 8–15 pages, never the whole wiki). Always
  create one `summaries/<source-slug>.md` per source doc. Update `index.md`, append to
  `log.md`, run the deterministic checks, commit through the gate. Keeping the rewrite
  scoped is the core discipline that keeps ingest cheap.
- **`/kb-lint`** — periodic full-wiki backstop (see §7).

---

## 4. Supersession (critical)

Sources are often **versioned** (contract v5 → v6; proposal in multiple formats). When a
newer source supersedes an older claim:

- Update the page to the newer claim.
- Record the change: `Superseded: <old claim> → <new claim> (source: vN → vM, <date>)`.
- Never silently keep the old claim. Confident-but-stale synthesis is the #1 failure mode
  of this format.

---

## 5. Contradiction status lines

When a source contradicts existing wiki content, add a machine-readable block to the page:

```
Contradiction severity: hard | soft
Status: Unresolved — flagged for review
Detail: <one line — what conflicts, which sources>
```

- **hard** = factual conflict that must be resolved before the wiki is trustworthy
  (e.g. two different contract dollar figures). Holds the commit (§6).
- **soft** = tension or ambiguity worth a human glance, doesn't block.
Resolve by editing to the correct claim and changing `Status:` to `Resolved — <how>`.

---

## 6. Deterministic vs. model split

Keep bookkeeping OUT of the model. The scripts do it:

- `scripts/kb-lint.py [--json] [root]` — broken wikilinks, orphan pages, bad frontmatter,
  dead `sources:` paths, index mismatches, uncited raw sources. Exit 0 clean / 1 findings
  / 2 usage error.
- `scripts/kb-gate.sh [wiki-dir]` — commit gate: any unresolved **hard** contradiction
  blocks. Exit 0 / 1 blocked / 2 usage error. Installed as a pre-commit hook by
  `scripts/install-hooks.sh` (run once after instantiating the template).
- `scripts/serve-site.sh` — browsable site from `wiki/` via Quartz v4 at
  `http://localhost:8080`.

Reserve the model for judgment only: entity synthesis, contradiction reasoning,
cross-referencing, "what's missing" during lint.

---

## 7. Lint

- **Scoped lint** runs on every ingest: contradiction check over touched pages + neighbors.
- **Full lint** (`/kb-lint`) runs periodically / on request: whole-wiki contradiction
  sweep, stale-synthesis check, orphan + broken-link pass via `kb-lint.py`. A backstop,
  not the primary defense.

Append every lint to `log.md`.
