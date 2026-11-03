"""Checks on the example reports in examples/ and on link_citations --standalone.

Run from the repository root:  python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
LINK = ROOT / "plugins" / "fact-check" / "skills" / "fact-check" / "scripts" / "link_citations.py"


def link_check(page: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(LINK), str(page), "--check"],
                          capture_output=True, text=True, timeout=60)


class Examples(unittest.TestCase):
    def reports(self) -> list[Path]:
        return sorted(p for p in EXAMPLES.glob("*.html") if p.name != "index.html")

    def test_index_links_every_report_and_nothing_missing(self):
        index = (EXAMPLES / "index.html").read_text(encoding="utf-8")
        local = {h for h in re.findall(r'href="([^"#:]+\.html)"', index)}
        for href in local:
            self.assertTrue((EXAMPLES / href).exists(), f"index links a missing page: {href}")
        self.assertEqual(local, {p.name for p in self.reports()},
                         "index and examples/ disagree about which reports exist")

    def test_every_page_is_standalone_utf8(self):
        for page in [EXAMPLES / "index.html", *self.reports()]:
            head = page.read_text(encoding="utf-8")[:300].lower()
            self.assertTrue(head.startswith("<!doctype html>"), page.name)
            self.assertIn('<meta charset="utf-8">', head, page.name)

    def test_reports_have_scope_note_and_clean_citations(self):
        for page in self.reports():
            text = page.read_text(encoding="utf-8")
            self.assertIn('class="scope"', text, page.name)
            self.assertIn("not a full Bayesian Framework for Intellectual Honesty", text, page.name)
            r = link_check(page)
            self.assertEqual(r.returncode, 0, f"{page.name}: {r.stdout}")
            self.assertNotIn("Never cited", r.stdout, page.name)

    def test_reports_give_no_percentage_weights(self):
        for page in self.reports():
            text = page.read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"\bAbout \d+[–-]\d+%|\bI put about \d", text), page.name)


class Standalone(unittest.TestCase):
    PAGE = '<title>T</title>\n<style>p{}</style>\n<p>Claim [1] — “quoted”.</p>\n<ol class="refs"><li>Source.</li></ol>\n'

    def test_adds_head_once_and_keeps_text(self):
        p = Path(tempfile.mkdtemp()) / "page.html"
        p.write_text(self.PAGE, encoding="utf-8")
        for _ in range(2):
            subprocess.run([sys.executable, "-I", str(LINK), str(p), "--standalone"],
                           check=True, capture_output=True, timeout=60)
        out = p.read_text(encoding="utf-8")
        self.assertTrue(out.startswith("<!doctype html>"))
        self.assertEqual(out.count('<meta charset="utf-8">'), 1)
        self.assertIn("— “quoted”", out)

    def test_default_run_adds_no_head(self):
        p = Path(tempfile.mkdtemp()) / "page.html"
        p.write_text(self.PAGE, encoding="utf-8")
        subprocess.run([sys.executable, "-I", str(LINK), str(p)], check=True,
                       capture_output=True, timeout=60)
        self.assertFalse(p.read_text(encoding="utf-8").lower().startswith("<!doctype"))


if __name__ == "__main__":
    unittest.main()
