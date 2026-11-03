"""Turn every in-text [N] on a /fact-check page into a link to Sources entry N.

Deterministic post-processing for Step 5 of the fact-check skill. Run it on
the filled page after the prose is final and before publishing:

  python3 -I scripts/link_citations.py PAGE.html [--check]

What it does, in place:
  - gives the Nth <li> of <ol class="refs"> the id "ref-N"
  - rewrites each bare [N] in body text (not inside tags, <style>, <script>,
    comments or existing links) as <a class="cite" href="#ref-N">[N]</a>
  - adds a small <style id="cite-links"> block once, so links read as
    citations and the target entry is highlighted when jumped to
  - is idempotent: running it twice gives the same file

It exits 1, changing nothing, when a cited N has no Sources entry. It
prints, without failing, any Sources entry that is never cited.
--check reports the same problems without writing.
--standalone also adds a doctype, a UTF-8 charset and a viewport line, for a
page saved as a file instead of published as an Artifact.
"""
from __future__ import annotations

import argparse
import re
import sys

# An Artifact host wraps the page in its own document head. A page saved as a
# plain file has no such wrapper, and without a declared charset a browser
# may read its curly quotes and dashes in a legacy encoding.
STANDALONE_HEAD = """<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
"""

CITE_CSS = """<style id="cite-links">
a.cite { text-decoration: none; font-variant-numeric: tabular-nums; }
a.cite:hover, a.cite:focus-visible { text-decoration: underline; }
.refs li { scroll-margin-top: 1.5rem; }
.refs li:target { background: var(--kraft-soft, #e7dcc8); outline: 2px solid var(--kraft, #8a6131); outline-offset: 4px; border-radius: 2px; }
</style>"""

TOKEN = re.compile(r"(<!--.*?-->|<[^>]+>)", re.S)
BARE = re.compile(r"\[(\d{1,3})\]")
LINKED = re.compile(r'<a class="cite" href="#ref-(\d+)">\[\1\]</a>')


def number_refs(page: str) -> tuple[str, int]:
    m = re.search(r'(<ol class="refs"[^>]*>)(.*?)(</ol>)', page, re.S)
    if not m:
        sys.exit('no <ol class="refs"> list found; is this a fact-check page?')
    count = 0

    def tag_li(li: re.Match) -> str:
        nonlocal count
        count += 1
        attrs = re.sub(r'\s+id="ref-\d+"', "", li.group(1) or "")
        return f'<li id="ref-{count}"{attrs}>'

    body = re.sub(r"<li(\s[^>]*)?>", tag_li, m.group(2))
    return page[:m.start(2)] + body + page[m.end(2):], count


def link_text(page: str) -> tuple[str, set[int]]:
    page = LINKED.sub(lambda m: f"[{m.group(1)}]", page)  # undo earlier runs
    cited: set[int] = set()
    out, skip_depth, in_link = [], None, 0
    for part in TOKEN.split(page):
        if part.startswith("<"):
            low = part.lower()
            if skip_depth is None and re.match(r"<(style|script)\b", low):
                skip_depth = re.match(r"<(\w+)", low).group(1)
            elif skip_depth and low.startswith(f"</{skip_depth}"):
                skip_depth = None
            elif re.match(r"<a\b", low):
                in_link += 1
            elif low.startswith("</a"):
                in_link = max(0, in_link - 1)
            out.append(part)
            continue
        if skip_depth or in_link:
            out.append(part)
            continue

        def link(m: re.Match) -> str:
            cited.add(int(m.group(1)))
            return f'<a class="cite" href="#ref-{m.group(1)}">[{m.group(1)}]</a>'
        out.append(BARE.sub(link, part))
    return "".join(out), cited


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("page")
    ap.add_argument("--check", action="store_true", help="report problems without writing")
    ap.add_argument("--standalone", action="store_true",
                    help="also add a doctype, UTF-8 charset and viewport, for a page saved as a "
                         "file rather than published as an Artifact")
    args = ap.parse_args()

    page = open(args.page, encoding="utf-8").read()
    page, n_refs = number_refs(page)
    page, cited = link_text(page)
    missing = sorted(n for n in cited if n < 1 or n > n_refs)
    uncited = sorted(set(range(1, n_refs + 1)) - cited)
    print(f"{n_refs} Sources entries; {len(cited)} distinct numbers cited.")
    if uncited:
        print("Never cited in the text: " + ", ".join(f"[{n}]" for n in uncited))
    if missing:
        print("ERROR: cited but no Sources entry: " + ", ".join(f"[{n}]" for n in missing))
        return 1
    if args.check:
        return 0
    if 'id="cite-links"' not in page:
        page = page.replace("</style>", "</style>\n" + CITE_CSS, 1)
    if args.standalone and not page.lstrip().lower().startswith("<!doctype"):
        page = STANDALONE_HEAD + page.lstrip()
    with open(args.page, "w", encoding="utf-8") as fh:
        fh.write(page)
    print(f"Linked citations written to {args.page}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
