---
name: kb-sync
description: Check the configured source channels for new or changed documents, diff against wiki/log.md, and report findings. Use when asked to "sync", "check for new docs", "any new documents?", or "what's landed?". Reports first — never ingests without approval.
---

# kb-sync — find new sources, report, stop

## Contract

**Report before ingest.** A sync request — even "any new docs today?" — is a report
request. Find what's new, say what it is and what it would change, then STOP and ask
whether to ingest. Only an explicit combined request ("sync and ingest") covers the full
pipeline; past approvals of individual ingests are not standing permission.

## Procedure

1. **Read the channel table** in `CLAUDE.md` §0. Each row names a channel, its kind, and
   its locator. If the table is empty, help the user fill it in (see intake options below).
2. **Enumerate each channel** using the kind-specific method, collecting name, modified
   time, and type for every document.
3. **Diff against the wiki**: `wiki/log.md` records every past ingest with its sources.
   A doc is *new* if never ingested, *changed* if its modified time is later than its last
   ingest entry.
4. **Report**: list new/changed docs, and for each say in one line what it likely
   changes or resolves in the wiki (read titles/metadata only — don't deep-read yet).
   Then ask whether to ingest.
5. **On approval**: convert each doc to clean markdown in `raw/sources/` (originals and
   binaries to `raw/assets/`), then invoke `/kb-ingest` for the converted set.

## Intake options by channel kind

- **drive** — Google Drive via MCP tools (search_files / list children by folder ID,
  read_file_content or download_file_content). Docs export as text/markdown; Sheets read
  as CSV per tab; Slides need per-slide text extraction. Record folder IDs in the §0
  table so no session has to rediscover them.
- **local** — a drop folder on disk. Enumerate with `ls -lt`; convert PDFs/docx with
  available tools (pandoc, pdftotext) into `raw/sources/`.
- **export** — Notion / Confluence / wiki exports. User exports to a folder; treat like
  local, but strip export artifacts (UUID suffixes in filenames, broken relative links).
- **transcripts / email** — pasted or dropped files (meeting transcripts, email threads).
  Save each as its own dated markdown file; the date prefix comes from the meeting/send
  date, not today.

## Conversion rules

- One `.md` file per source doc, kebab-case slug; prefix with `YYYY-MM-DD-` when the doc
  is inherently dated (meetings, emails, dated versions).
- Clean markdown: keep headings, tables, and lists; strip export junk, tracking cruft,
  and boilerplate. Content must read as the document, not as a scrape.
- Never overwrite an existing raw file for a *changed* doc silently — land the new
  version and let ingest apply the §4 supersession rules.
