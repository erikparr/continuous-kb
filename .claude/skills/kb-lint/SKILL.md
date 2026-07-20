---
name: kb-lint
description: Full-wiki backstop lint — deterministic checks plus model judgment passes (contradiction sweep, stale synthesis, what's missing). Use when asked for a "full lint", "sweep", or "health check" of the knowledge base.
---

# kb-lint — full-wiki backstop

Scoped lint happens on every ingest; this is the periodic whole-wiki sweep. Expect to
run it occasionally, not per-ingest.

## Procedure

1. **Deterministic pass:** run `python3 scripts/kb-lint.py --json` and triage every
   finding. Fix mechanical issues directly (broken wikilinks, index mismatches, missing
   frontmatter keys, uncited raw sources → create the missing summary page).
2. **Contradiction sweep (model judgment):** walk the wiki by cluster (a hub page plus
   its neighbors at a time — not one giant read) and look for claims that conflict
   across pages. Add §5 status blocks where found.
3. **Stale-synthesis check:** for each page, compare its `updated:` date and claims
   against the newest sources in its `sources:` list and their newer versions in
   `raw/sources/`. Confident-but-stale synthesis is the #1 failure mode — apply §4
   supersession where a newer source changed the facts.
4. **"What's missing" pass:** broken wikilinks that recur are pages worth creating;
   entities/concepts mentioned repeatedly in raw sources but absent from the wiki get
   flagged (or created, if approved).
5. **Log:** append a lint entry to `wiki/log.md` — date, checks run, findings, what was
   fixed vs. flagged.
6. **Commit** through the gate as usual.
