#!/usr/bin/env python3
"""Fixture tests for scripts/kb-lint.py. Stdlib only. Run: python3 tests/test_kb_lint.py"""
import json
import subprocess
import sys
import tempfile
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
