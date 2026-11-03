"""Fetch one source and print its own text: metadata, opening, keyword contexts, full passages.

The fact-check skill reads sources through this script for anything it will
quote or rely on. WebFetch returns a small model's answer about a page (capped
quotes, sometimes only the headline, sometimes its own judgement); this script
returns the page's words. It downloads the URL with a browser User-Agent into
a fresh directory, extracts text from HTML (dropping nav, header, footer and
aside) or PDF (needs pypdf: pip install pypdf), and prints:

  - the HTTP status, content type and saved path
  - citation_* / DC.* / og:* meta tags and byline-style tags (HTML), or the
    PDF /Info metadata, for building the citation
  - the first --head characters of text
  - each --grep keyword in context, with overlapping hits merged
  - each --around phrase as one unbroken passage of --chars characters,
    for quoting at length

Usage:
  python3 -I scripts/fetch_text.py URL \
      [--grep KEYWORD ...] [--around PHRASE ...] [--chars 1500] \
      [--head 800] [--context 300] [--max-hits 4] [--dump FILE] [--out-dir DIR]

  URL may also be a local file already downloaded (for example the PDF path
  WebFetch reports saving).

Exit codes: 0 text extracted; 2 BLOCKED (bot wall: find another copy);
3 HTTP ERROR (404, 410, 5xx: the URL is wrong or gone).
"""
from __future__ import annotations

import argparse
import html
import http.client
import json
import os
import re
import shutil
import sys
import tempfile
import urllib.error
import urllib.request

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
WALL_MARKERS = ("just a moment", "verifying you are human", "verifying connection",
                "access denied", "enable javascript and cookies", "are you a robot",
                "captcha")
META_NAMES = r"(?:citation_[a-z_]+|DC\.[A-Za-z.]+|dc\.[a-z.]+|author|byl|parsely-author|article:published_time|og:title|og:site_name|date)"


def download(url: str, out_dir: str) -> tuple[int, str, str]:
    path = os.path.join(out_dir, "source.bin")
    if os.path.exists(url):
        shutil.copyfile(url, path)
        return 200, "", path
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                status, ctype = resp.status, resp.headers.get("Content-Type", "")
                try:
                    data = resp.read()
                except http.client.IncompleteRead as e:
                    if attempt == 1:
                        continue  # the server cut the body short; retry once
                    data = e.partial
                    print(f"WARNING: body truncated ({len(data)} bytes kept); "
                          "text near the end may be missing.", file=sys.stderr)
            break
        except urllib.error.HTTPError as e:
            status, ctype, data = e.code, e.headers.get("Content-Type", ""), e.read()
            break
    with open(path, "wb") as fh:
        fh.write(data)
    return status, ctype, path


def pdf_text(path: str) -> tuple[str, str]:
    try:
        import pypdf
    except ImportError:
        sys.exit("Reading PDFs needs pypdf, which this Python lacks. Install it with: python3 -m pip install pypdf")
    reader = pypdf.PdfReader(path)
    meta = f"pages={len(reader.pages)} metadata={dict(reader.metadata or {})}"
    text = "".join(f"\n[page {i + 1}]\n" + (p.extract_text() or "")
                   for i, p in enumerate(reader.pages))
    return meta, text


def json_ld_fields(raw: str) -> list[str]:
    """Citation fields from schema.org JSON-LD, where many news sites keep bylines."""
    found: list[str] = []

    def names(v) -> list[str]:
        items = v if isinstance(v, list) else [v]
        return [i.get("name", "") if isinstance(i, dict) else str(i) for i in items if i]

    def walk(node) -> None:
        if isinstance(node, list):
            for n in node:
                walk(n)
            return
        if not isinstance(node, dict):
            return
        if "@graph" in node:
            walk(node["@graph"])
        kind = node.get("@type", "")
        kind = " ".join(kind) if isinstance(kind, list) else str(kind)
        if any(k in kind for k in ("Article", "Report", "Posting", "WebPage", "ScholarlyArticle")):
            for field in ("headline", "datePublished", "dateModified"):
                if node.get(field):
                    found.append(f"  ld:{field}: {node[field]}")
            for field in ("author", "publisher"):
                who = [n for n in names(node.get(field)) if n]
                if who:
                    found.append(f"  ld:{field}: {'; '.join(who)}")

    for block in re.findall(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', raw):
        try:
            walk(json.loads(block.strip()))
        except ValueError:
            continue
    return list(dict.fromkeys(found))[:12]


def html_text(path: str) -> tuple[str, str]:
    raw = open(path, encoding="utf-8", errors="ignore").read()
    title = re.findall(r"<title[^>]*>(.*?)</title>", raw, re.S)
    lines = ["title=" + (html.unescape(title[0].strip()) if title else "?")]
    for tag in re.findall(r"<meta\b[^>]*>", raw, re.I):
        key = re.search(r'(?:name|property)="(' + META_NAMES + r')"', tag)
        val = re.search(r'content="([^"]*)"', tag)
        if key and val and val.group(1).strip():
            lines.append(f"  {key.group(1)}: {html.unescape(val.group(1))}")
    lines += json_ld_fields(raw)
    body = re.sub(r"(?is)<(script|style|noscript|svg|nav|header|footer|aside|form)\b[^>]*>.*?</\1>", " ", raw)
    article = re.search(r"(?is)<article\b[^>]*>(.*)</article>", body)
    if article and len(article.group(1)) > 2000:
        body = article.group(1)
    body = html.unescape(re.sub(r"<[^>]+>", " ", body))
    return "\n".join(lines[:40]), re.sub(r"\s+", " ", body).strip()


def merged_windows(text: str, kw: str, ctx: int) -> list[tuple[int, int, int]]:
    """Return (start, end, hits) windows around each match, merging overlaps."""
    windows: list[list[int]] = []
    for m in re.finditer(re.escape(kw), text, re.I):
        s, e = max(0, m.start() - ctx), min(len(text), m.end() + ctx)
        if windows and s <= windows[-1][1]:
            windows[-1][1], windows[-1][2] = max(windows[-1][1], e), windows[-1][2] + 1
        else:
            windows.append([s, e, 1])
    return [tuple(w) for w in windows]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="URL, or path to an already-downloaded file")
    ap.add_argument("--grep", nargs="+", action="extend", default=[],
                    help="keywords to show in context (case-insensitive); repeat the flag or list several")
    ap.add_argument("--around", nargs="+", action="extend", default=[],
                    help="phrases to print as full passages, one per match up to --max-hits")
    ap.add_argument("--chars", type=int, default=1500, help="passage length for --around")
    ap.add_argument("--head", type=int, default=800, help="characters of opening text to print")
    ap.add_argument("--context", type=int, default=300, help="characters either side of a --grep hit")
    ap.add_argument("--max-hits", type=int, default=4, help="merged windows shown per keyword")
    ap.add_argument("--dump", help="write the full extracted text to this file")
    ap.add_argument("--out-dir", help="download directory (default: a fresh temp dir under $TMPDIR)")
    args = ap.parse_args()

    out_dir = args.out_dir or tempfile.mkdtemp(prefix="factcheck-src-")
    os.makedirs(out_dir, exist_ok=True)
    status, ctype, path = download(args.url, out_dir)
    with open(path, "rb") as fh:
        is_pdf = fh.read(5) == b"%PDF-" or "pdf" in ctype.lower()
    meta, text = pdf_text(path) if is_pdf else html_text(path)

    print(f"URL: {args.url}\nHTTP {status}  type={ctype or '?'}  saved={path}\n{meta}\n")
    walled = not is_pdf and len(text) < 3000 and any(m in text.lower() for m in WALL_MARKERS)
    if walled or status in (401, 403, 429):
        print("BLOCKED: bot wall or access refusal. Find another copy (DOI, PubMed Central, "
              "archive scan, publisher PDF) or mark the source unverified.")
        print(text[:300])
        return 2
    if status >= 400:
        print(f"HTTP ERROR {status}: the URL is wrong or the page is gone. "
              "Search for the current URL or an archived copy.")
        return 3
    if args.dump:
        with open(args.dump, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"Full text ({len(text)} chars) written to {args.dump}\n")
    print(f"TEXT ({len(text)} chars) opening:\n{text[:args.head]}\n")
    for kw in args.grep:
        wins = merged_windows(text, kw, args.context)
        total = sum(w[2] for w in wins)
        print(f"=== '{kw}': {total} hit(s) in {len(wins)} passage(s)")
        for s, e, _ in wins[:args.max_hits]:
            print("..." + text[s:e].replace("\n", " ") + "...\n")
    for phrase in args.around:
        starts = [m.start() for m in re.finditer(re.escape(phrase), text, re.I)]
        print(f"=== passages around '{phrase}': {len(starts)} match(es)")
        if not starts:
            print("(not found)\n")
        shown_to = -1
        for n, i in enumerate(starts[:args.max_hits], 1):
            if i < shown_to:
                continue  # already inside the previous passage
            s = max(0, i - args.chars // 3)
            shown_to = s + args.chars
            print(f"--- match {n}\n{text[s:shown_to]}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
