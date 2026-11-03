"""Offline tests for the fact-check skill's scripts.

Run from the repository root:  python3 -m unittest discover -s tests -v
No network access and no third-party packages are needed.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "plugins" / "fact-check" / "skills" / "fact-check"
FETCH = SKILL / "scripts" / "fetch_text.py"
LINK = SKILL / "scripts" / "link_citations.py"
TEMPLATE = SKILL / "references" / "page-template.html"


def run(script: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", str(script), *args],
                          capture_output=True, text=True, timeout=60)


PAGE = """<title>Test</title>
<style>p { color: red; }</style>
<main>
<p>First claim [1]. Second claim [2][1]. A bracketed word [sic] stays.</p>
<p>A quoted aside "people buy [intelligence]" stays too.</p>
<ol class="refs">
  <li>Source one.</li>
  <li class="x">Source two.</li>
</ol>
</main>
"""


class LinkCitations(unittest.TestCase):
    def write(self, text: str) -> Path:
        d = Path(tempfile.mkdtemp())
        p = d / "page.html"
        p.write_text(text, encoding="utf-8")
        return p

    def test_links_numbers_and_ids(self):
        p = self.write(PAGE)
        r = run(LINK, str(p))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        out = p.read_text()
        self.assertIn('<a class="cite" href="#ref-1">[1]</a>', out)
        self.assertIn('<a class="cite" href="#ref-2">[2]</a><a class="cite" href="#ref-1">[1]</a>', out)
        self.assertIn('<li id="ref-1">Source one.</li>', out)
        self.assertIn('<li id="ref-2" class="x">Source two.</li>', out)
        self.assertIn("[sic]", out)
        self.assertIn("[intelligence]", out)
        self.assertIn('<style id="cite-links">', out)

    def test_idempotent(self):
        p = self.write(PAGE)
        run(LINK, str(p))
        first = p.read_text()
        run(LINK, str(p))
        self.assertEqual(first, p.read_text())

    def test_dangling_number_fails_without_writing(self):
        p = self.write(PAGE.replace("Second claim [2][1]", "Second claim [3]"))
        before = p.read_text()
        r = run(LINK, str(p))
        self.assertEqual(r.returncode, 1)
        self.assertIn("[3]", r.stdout)
        self.assertEqual(before, p.read_text())

    def test_uncited_entry_is_reported(self):
        p = self.write(PAGE.replace("Second claim [2][1]", "Second claim [1]"))
        r = run(LINK, str(p))
        self.assertEqual(r.returncode, 0)
        self.assertIn("Never cited in the text: [2]", r.stdout)

    def test_template_keeps_one_cite_style_block(self):
        filled = TEMPLATE.read_text().replace("{{APA 7 entry with linked URL or DOI}}", "Entry")
        filled = filled.replace("{{a material omission, cited}} [N]", "Omission [1]")
        p = self.write(filled)
        r = run(LINK, str(p))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(p.read_text().count('id="cite-links"'), 1)


ARTICLE = """<html><head><title>Story | Outlet</title>
<meta property="og:title" content="Story headline">
<script type="application/ld+json">{}</script>
</head><body>
<nav>Home News Sports</nav>
<article>{}</article>
<footer>Copyright</footer>
</body></html>"""


class FetchText(unittest.TestCase):
    def page(self, body: str, ld: dict | None = None) -> Path:
        d = Path(tempfile.mkdtemp())
        p = d / "story.html"
        p.write_text(ARTICLE.format(json.dumps(ld or {}), body), encoding="utf-8")
        return p

    def test_local_file_metadata_and_byline(self):
        ld = {"@type": "NewsArticle", "headline": "Story headline",
              "datePublished": "2026-10-13", "author": [{"name": "A. Writer"}, {"name": "B. Writer"}]}
        p = self.page("Body text. " * 300, ld)
        r = run(FETCH, str(p), "--head", "50")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("ld:author: A. Writer; B. Writer", r.stdout)
        self.assertIn("ld:datePublished: 2026-10-13", r.stdout)
        self.assertIn("og:title: Story headline", r.stdout)
        self.assertNotIn("Home News Sports", r.stdout)

    def test_repeated_grep_flags_combine_and_overlaps_merge(self):
        p = self.page("filler " * 400 + "alpha beta alpha " + "filler " * 400 + "gamma")
        r = run(FETCH, str(p), "--grep", "alpha", "--grep", "gamma", "--head", "0", "--context", "40")
        self.assertIn("=== 'alpha': 2 hit(s) in 1 passage(s)", r.stdout)
        self.assertIn("=== 'gamma': 1 hit(s) in 1 passage(s)", r.stdout)

    def test_around_shows_every_match(self):
        p = self.page("filler " * 400 + "key phrase one " + "filler " * 400 + "key phrase two")
        r = run(FETCH, str(p), "--around", "key phrase", "--chars", "60", "--head", "0")
        self.assertIn("passages around 'key phrase': 2 match(es)", r.stdout)
        self.assertIn("--- match 2", r.stdout)

    def test_bot_wall_reports_blocked(self):
        p = self.page("Just a moment... Enable JavaScript and cookies to continue")
        r = run(FETCH, str(p))
        self.assertEqual(r.returncode, 2)
        self.assertIn("BLOCKED", r.stdout)


if __name__ == "__main__":
    unittest.main()
