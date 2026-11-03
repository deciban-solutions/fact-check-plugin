---
name: fact-check
description: 'Use when the user asks "did this really happen", "is this true", "did they really say that", "fact-check this" or "verify this", or pastes a story, post, quote, statistic, chatbot answer or article and wants to know whether its claims hold up, with a cited verdict they can read and share.'
---

## Step 0 — Priming (before anything else)

Read and adopt `${CLAUDE_PLUGIN_ROOT}/skills/fact-check/references/priming.md`.
This applies whether you are the main agent or a subagent running this skill.
If you dispatch a subagent for any part of the check, its prompt must begin
by telling it to read and adopt that file. When you run as a subagent and
your dispatch prompt states what to return, return that.

# Fact Check — Verify a Claim Against the Record

This skill checks whether a claim matches the documentary record. It is not a
full Bayesian Framework for Intellectual Honesty (BFIH) analysis: its
hypothesis weights are judgements stated in words, not computed
probabilities, and it runs no independent paradigm elicitation and no
adversarial challenge. When the verdict turns on contested interpretation
rather than on what records say, it settles the factual rows and refers the
rest to a full analysis (Step 4).

The output is a verdict on the claim, a claim-by-claim table, and a page built
from `references/page-template.html`. You read every source on that page
yourself, through its own text. Search-result summaries and fetch-tool answers
are leads for finding sources, never evidence.

Files in this skill (`${CLAUDE_PLUGIN_ROOT}/skills/fact-check/`):

- `references/priming.md`: the disposition (Step 0)
- `references/mandate.md`: the five-step reconsideration mandate
- `references/page-template.html`: the page
- `scripts/fetch_text.py`: reads a source's own text (needs `pypdf` for PDFs)
- `scripts/link_citations.py`: links every `[N]` to its source entry

## Step 1 — Read the mandate, type the claim, split it

1. Read `${CLAUDE_PLUGIN_ROOT}/skills/fact-check/references/mandate.md` in
   full. Its five steps govern the whole check. This skill says how to carry
   them out; it never relaxes one.
2. Decide the claim type. It sets the rows, hypotheses and levels below.
   - **Event account:** something happened, with dates, numbers, actors and
     causes (a disaster, a historical episode, a news story).
   - **Attribution:** a named person said, believes or wants something (a
     quote, a paraphrase of a view, a "they think that…" post).
   - **Statistic:** a number about the world ("the average person…", "X% of…").
   - **Practice with a label:** an actor routinely does something, and the
     claim characterizes it ("unlawfully", "illegally", "fraudulently",
     "systematically").
   A mixed claim takes the type of the part the verdict turns on; type the
   other parts' rows by their own kind.
3. Split the claim into rows, keeping its wording:
   - Event account: one row per date, quantity, named actor, causal statement
     and attribution.
   - Attribution: one row per separable proposition in the paraphrase, plus a
     row for the verb itself ("believes", "said", "wants") judged against how
     often and how firmly the person expressed it.
   - Statistic: one row for the number, one for its population and unit, and
     one for the source the claim names or implies.
   - Practice with a label: one row each for the actor, the conduct, its
     frequency, its scope (who, where), its timing, and the label.
   Flag claims that are internally inconsistent, such as a count and a
   percentage that imply different totals.
4. Note signs of the claim's origin, such as a chatbot's closing offer to
   tell more or a viral headline's wording. Mention any you find in the
   verdict, since they bear on the hypotheses.

## Step 2 — Context, hypotheses, paradigms, levels (mandate steps 1–4)

**Context.** Scale it to the claim. A one-line claim needs its dates, place or
setting, and a definition of each term whose meaning changes the answer, each
cited. A broad account needs the fuller treatment the mandate describes.

**Hypotheses.** Start from the set for the claim type and adjust to the case.
If you change it, say how on the page (the template has a slot).

| Type | H1 | H2 | H3 | H4 | H0 |
|---|---|---|---|---|---|
| Event account | Accurate in every material respect | Core events true; at least one material detail wrong or invented | Core events false or legendary | — | Other: a different cause, deliberate fabrication |
| Attribution | Fairly states a view the person expressed | A real remark, materially exaggerated or stripped of its conditions | No such remark; invented or misattributed | — | Other: a different speaker or occasion, satire taken literally |
| Statistic | Accurate, with a traceable source | A real figure, distorted (wrong population, unit, date or rounding) | No real source; invented or circular | — | Other: unmeasurable as stated, or true for reasons the claim does not give |
| Practice with a label | The conduct happens as described and the label holds | The conduct is real and the label holds where tested, but scope or settledness is overstated | The conduct is real but the label is wrong (lawful, justified, not as characterized) | No such practice: isolated errors or invented cases | Other |

For an attribution, the standard of faithfulness is: the person stated the
position, or it follows plainly from what they stated. A position inferred
only from their interests or business model raises or lowers the prior; it
does not make the paraphrase faithful.

For a label, name the authority that decides it and how far it has decided:
for a legal label, an appellate holding outranks a trial ruling, a final
ruling outranks an interim one, and a party's position is not a ruling. If
the authority has not settled the question, the label's row is "Unsettled"
and the escalation rule in Step 4 applies.

**Paradigms.** State your governing paradigm and at least one realistic
opposing paradigm. Each gets a 5–15 word phrase per dimension, and each pair
differs on at least three dimensions.

**Levels.** Lay out the evidence levels with the mandate's two-way adjacency
test, and say which level the hypotheses predict most directly. Typical
layouts:

- Event account: frameworks → the account → population patterns →
  documented figures and records → named people and acts. The hypotheses
  usually predict the documented figures most directly.
- Attribution: how to read attributions → the belief → the person's pattern
  of statements over time → coverage of the remark → the words spoken. The
  last two form a chain of transmission: test whether the coverage's wording
  appears in the words spoken. The hypotheses predict the words spoken most
  directly.
- Statistic: measurement method → the figure → independent estimates →
  the original study or dataset → the first appearance of the figure. The
  hypotheses predict the original study and the first appearance most
  directly.
- Practice with a label: the governing rule (law, policy, standard) → the
  claim → the pattern of cases → rulings or findings in specific cases →
  named acts. The hypotheses predict the rulings most directly, so read the
  rulings themselves where you can.

## Step 3 — Gather evidence (mandate step 4)

Search to discriminate between the hypotheses, starting with the claims most
likely to be wrong: precise figures, causes, attributions, dates, labels. Go
to the primary record first: the transcript or video for an attribution, the
first appearance for a statistic, the court order or official finding for a
label. Send independent searches together. Web-search budgets are often
shared across a session and its subagents, so prefer one good query per claim.

Search results and fetch-tool answers (such as WebFetch) both serve only to
locate sources. A fetch tool that answers through a model caps quotes,
sometimes returns only the headline, and adds judgements of its own. Never put
either tool's own sentences on the page as a source's words.

Read each source you intend to cite through this ladder:

1. **The script, for anything you quote or rely on.** Run
   `python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/fact-check/scripts/fetch_text.py URL --around "PHRASE" --grep KEYWORD1 KEYWORD2`.
   If your environment filters network access per host, allow the source's
   host for that command. `--around` prints an unbroken passage at each
   match, for quoting; `--grep` shows keyword contexts; the metadata lines
   give the citation fields, including bylines from the page's structured
   data; `--dump FILE` saves the full text. It also reads a local file, such
   as a PDF another tool has saved. If it reports that `pypdf` is missing,
   tell the user the install command it prints.
2. **On exit 2 (BLOCKED)**, find another copy:
   - papers: the DOI, PubMed Central, the publisher's PDF;
   - news: the outlet's print or AMP version (often `.print` or `/amp` on the
     URL), a syndicated copy, or the primary record the story reports on;
   - court matters: the court's own opinion page or a public docket mirror.
3. **On exit 3 (HTTP ERROR)**, search for the current URL or an archived copy.
4. **If no readable copy exists**, drop the source or keep it as
   "unverified" with no weight in the verdict.

Every field of a citation (authors, year, title, venue, pages) comes from the
document's own title page, metadata or record page. Write "[unknown]" when the
document does not show a field. The one exception is an unverified source:
its fields may come from the search listing, and its status line says so. A
source cited for one narrow thing (a headline, a single figure) may be read
only that far; its status line says exactly what was read. Where sources
disagree (dates, counts, wordings), report the range and who says what.
Prefer records made at the time over later retellings, and primary documents
over news summaries.

Search again wherever a level's coverage is sparse, especially the level the
hypotheses predict most directly.

## Step 4 — Weigh, decide, escalate (mandate step 5)

For each hypothesis, say which findings it makes likely or unlikely, then
give it one weight from this scale. Use the words, never percentages:

| Weight | Meaning |
|---|---|
| Ruled out | The record directly contradicts it |
| Unlikely | Evidence counts against it and little or nothing supports it |
| Open | Consistent with the record; the evidence does not decide it |
| Favored | Fits the record best, but a rival is still open |
| Clearly favored | Fits the record best, and every rival is unlikely or ruled out |

An invented detail counts heavily against H1. A confirmed core counts
heavily against the "no such thing" hypothesis. Say which opposing-paradigm
objection has force and which does not.

**Escalation rule.** Refer the part of the claim it concerns to a full
analysis when either of these holds:

- no hypothesis is clearly favored, and the hypotheses still open differ in
  interpretation (causation, intent, legality, justification, values, a
  forecast) rather than in what documents say; or
- the claim's label is unsettled by the authority that decides it (Step 2).

When it applies, do all of this:

1. Settle every factual row as usual.
2. Give the interpretive row the status "Referred". Write what the record
   shows on each side, and say who would decide it.
3. In the verdict, separate what this check settled from what it refers. Do
   not give the referred part an overall weight of your own.
4. In the terminal, state the referred question as one answerable
   proposition (a single claim that can be true or false, with its time,
   place and key terms pinned down), and list the primary records a deeper
   analysis should open first. If the BFIH skills are installed, recommend
   running `/analyze` on that proposition.

## Step 5 — Deliver

1. In the terminal: the one-line answer, the material errors, the hypothesis
   weights in words, any referral, and the bibliography in APA 7 style.
2. Build the page: copy
   `${CLAUDE_PLUGIN_ROOT}/skills/fact-check/references/page-template.html` to
   a working directory and fill every `{{…}}` slot. Keep its sections in
   order: Verdict, scope note, Claim by claim, What the account leaves out,
   How I reached the verdict, Sources, footer. Keep the scope note's wording,
   editing only the referral sentence. Use the template's status tags only.
   Use `<i>` for titles in APA entries. Write citations as plain `[N]`.
3. Link the citations:
   `python3 -I ${CLAUDE_PLUGIN_ROOT}/skills/fact-check/scripts/link_citations.py PAGE.html`.
   It makes every `[N]` a link to Sources entry N and fails if a number has
   no entry. Fix any failure and rerun.
4. Share the page:
   - If an Artifact tool is available, publish the page with it and give the
     link. Say that the page is private until the user shares it.
   - Otherwise, save the page as `fact-check-<short-name>.html` in the
     current project (or wherever the user asks) and give its full path. It
     is a single self-contained file that opens in any browser.

When a follow-up corrects something you said earlier, say so plainly in the
terminal and on the page. Do not quietly swap the wrong claim for the right
one.

## Self-check before sharing

- [ ] Every part of the claim has a row, and every row has a status tag.
- [ ] `link_citations.py` ran clean: every `[N]` links to an entry.
- [ ] Every Sources entry says how it was read, and how far.
- [ ] Nothing quoted on the page came from a fetch-tool answer or a search summary.
- [ ] No citation field came from memory.
- [ ] Disagreements between sources are shown as ranges with attributions.
- [ ] Hypothesis weights are words from the scale; no percentage or probability is given for any hypothesis or for the verdict. (Percentages reported as evidence, such as a survey result, stay.)
- [ ] The escalation rule was checked; if it applies, the row says "Referred" and the scope note names the question.
- [ ] Anything left unverified is listed in the footer and given no weight.
