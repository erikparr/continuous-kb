---
name: kb-ingest
description: Fold new or changed raw sources into the wiki with a scoped rewrite — entity/concept/summary pages, supersession, contradiction check, index/log update, lint, gated commit. Use after kb-sync approval or when asked to "ingest" specific sources.
---

# kb-ingest — scoped wiki rewrite

Run once per approved batch of new/changed sources in `raw/sources/`.

## Procedure

1. **Read** the changed source(s) fully.
2. **Scope.** Load only the wiki pages the source touches, plus their 1st/2nd-degree
   wikilink neighbors. NOT the whole wiki. A single source typically touches 8–15 pages.
   This scoping is the core discipline that keeps ingest cheap — resist widening it.
3. **Write/update pages** per the `CLAUDE.md` §2 conventions:
   - Always create one `summaries/<source-slug>.md` per source doc.
   - Update or create the entity/concept pages the source materially affects.
   - Anchor claims: short quote + source path beats unsourced synthesis.
   - **Supersession (§4):** when a newer source version replaces a claim, update the page
     and record `Superseded: <old> → <new> (source: vN → vM, <date>)`. Never silently
     keep a stale claim.
4. **Contradiction check** against the scoped neighbor set only. On conflict, add the §5
   status block (`Contradiction severity: hard|soft` / `Status: Unresolved — flagged for
   review` / `Detail: …`) to the affected page.
5. **Bookkeeping:** add/update the catalog line for every touched page in
   `wiki/index.md`; append an entry to `wiki/log.md` (date, sources, pages touched).
6. **Deterministic check:** run `python3 scripts/kb-lint.py`. Fix findings (broken links,
   index mismatches, missing summaries) and re-run until clean or every remaining finding
   is deliberate.
7. **Commit.** The pre-commit hook runs `scripts/kb-gate.sh`; an unresolved **hard**
   contradiction blocks the commit by design. Either resolve it (edit to the correct
   claim, set `Status: Resolved — <how>`) or stop and surface it to the user — never
   bypass the gate with `--no-verify`.
