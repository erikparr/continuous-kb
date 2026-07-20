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
        subdir = wiki / d
        if subdir.is_dir():
            for p in sorted(subdir.glob("*.md")):
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
