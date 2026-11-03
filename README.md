# Fact Check

A Claude Code plug-in that checks a claim against the documentary record. Paste a story, a quote, a statistic, a chatbot answer or a post, and ask "did this really happen?" Claude splits the claim into checkable parts, finds the primary sources, reads each one in full, and gives you a verdict plus a shareable page with a claim-by-claim table and linked citations.

## What makes it different

- **Every cited source is read in its own words.** Search-result summaries and the answers of web-fetch tools only serve to find sources. A bundled script downloads each page or PDF and extracts its text, so quotes and citation details come from the document itself, never from memory.
- **Competing explanations, weighed openly.** Each check sets up competing hypotheses for the claim's type (an event account, an attribution, a statistic, or a practice with a label such as "unlawfully"), states the reasoning paradigm it works under and the realistic opposing ones, and weighs each hypothesis in plain words: ruled out, unlikely, open, favored, or clearly favored.
- **It knows its limits.** When the answer turns on contested interpretation (legality, intent, causation, values) rather than on what records say, the check settles the facts and refers the interpretive question to a deeper analysis instead of pretending to decide it.
- **A page you can share.** The page follows a fixed layout: verdict, scope note, claim-by-claim table, omissions, method, sources with a note on how each was read, and remaining uncertainty. Every `[n]` links to its source.

The method follows a five-step reconsideration mandate written by Michael L. Thompson (context, hypotheses, paradigms, evidence gathered across levels of abstraction, and weighing), included in full in `plugins/fact-check/skills/fact-check/references/mandate.md`. It draws on the Bayesian Framework for Intellectual Honesty (BFIH). It is deliberately lighter than a full BFIH analysis: the weights are judgements in words, not computed probabilities, and every page says so.

## Install

In Claude Code:

```
/plugin marketplace add deciban-solutions/fact-check-plugin
/plugin install fact-check@deciban-solutions
```

Or from your shell:

```bash
claude plugin marketplace add deciban-solutions/fact-check-plugin
claude plugin install fact-check@deciban-solutions
```

## Use

Ask in your own words, for example "did this really happen?" with the text pasted in, or run the skill by name:

```
/fact-check:fact-check Sam Altman says computer owners shouldn't have RAM.
```

A thorough check takes a few minutes and a few dozen searches and page reads.

## Examples

[`examples/`](examples/) holds three reports the skill produced, one per kind of claim. Clone the repository and open `examples/index.html` in a browser to browse them.

- [The 1973 PBB Mix-Up](examples/pbb-1973-feed-contamination.html): an event account. True in substance, with an invented cause and some loose figures. ([published version](https://claude.ai/artifact/9mWysBde6H1qBabVmapCmU))
- [Altman and Your RAM](examples/altman-ram-remark.html): an attribution. A real remark, materially exaggerated. ([published version](https://claude.ai/artifact/DguRVdk2f6TgxRSvAS9b5j))
- [ICE Instant Re-arrests](examples/ice-immediate-rearrests.html): a practice with a legal label. The conduct is established, and the legal question is referred to a full analysis.

## Requirements

- Claude Code with web search and web fetch available.
- Python 3.9 or later on your `PATH` as `python3`.
- For PDF sources, the `pypdf` package: `python3 -m pip install pypdf`. Without it, HTML sources still work, and the script prints the install command when it meets a PDF.
- If your Claude Code sandbox filters network access by host, allow the source hosts when the fetch script asks.

Where Claude can publish Artifacts (claude.ai), the page is published as a private artifact for you to share. Elsewhere it is saved as a single self-contained HTML file.

## Repository layout

```
.claude-plugin/marketplace.json          marketplace listing for this repository
plugins/fact-check/
  .claude-plugin/plugin.json             plug-in manifest
  skills/fact-check/
    SKILL.md                             the procedure Claude follows
    references/priming.md                how to engage: calibration, steelmanning, reading sources
    references/mandate.md                the five-step reconsideration mandate
    references/page-template.html        the shareable page
    scripts/fetch_text.py                reads a source's own text, HTML or PDF
    scripts/link_citations.py            links every [n] to its source entry
examples/                                example reports and an index page
tests/test_scripts.py                    offline tests for both scripts
tests/test_examples.py                   checks on the example reports
```

## Development

```bash
python3 -m unittest discover -s tests -v   # offline script tests
claude plugin validate .                   # marketplace and manifest
claude plugin validate ./plugins/fact-check
```

To try local changes without installing: `claude --plugin-dir ./plugins/fact-check`.

## License

MIT, © 2026 Deciban Solutions LLC. See `LICENSE`.
