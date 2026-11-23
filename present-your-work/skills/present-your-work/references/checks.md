# The check script

```
python3 scripts/check_draft.py DRAFT [--changed PATH ...] [--changed-from FILE|-]
    [--glossary GLOSSARY.md] [--known TERM ...] [--known-file FILE] [--all]
```

It reads Markdown or HTML, uses only Python's standard library, runs in well under a second, and
exits 0 when every rule holds, 1 when one is broken and 2 on a usage error.
`python3 scripts/test_check_draft.py` runs its tests.

The main text is the whole draft, or everything before an appendix: a line `Evidence:`, a heading
"Evidence", "Details" or "Appendix", or the comment `<!-- appendix -->`. A quick presentation has
no appendix; the marker is for a longer draft that keeps one.

| Rule | What it counts | What it leaves out |
|---|---|---|
| words | Words of prose in the main text; 60 to 300, ten percent either side passes | Headings, tables, an appendix |
| terms | Distinct terms defined in the main text (a `<dfn>`, a short italic or bold span, "long form (ABC)"); at most 2 | Terms passed with `--known`; run-in headings |
| numbers | Distinct numerals in the main text, with units, percentages and clock times; at most 3 | Code spans, years, dates, citation brackets, "Section 4" |
| labels | The glossary's labels; letters mixed with digits (v2, B8); snake_case; camelCase; file names and paths; acronyms neither common, known nor defined | Anything in a code span; numbers with units; common acronyms; `--known` |
| order | A term used before the text defines it | Uses in an appendix |
| tone | Superlatives and self-praise: robust, comprehensive, seamless, significantly, fully, and the like | Code spans |
| evidence | A sentence that claims a check (passes, verified, confirmed, tested, green) with no code span and no number in it | Negated sentences ("not tested on Linux") |
| tests | A changed test file (from `--changed` or `--changed-from`) that the draft never names, by file name or stem | Changed files that are not tests |
| log | Three or more markers of chronology: first, then, after that, finally, a weekday | |
| voice | Colons and semicolons in sentences (labelled lead-ins, colon reveals), em dashes, "not X, but Y", a trailing "-ing" comment clause, a sign-off offer, "checked", "verified", "validated" or "confirmed" where the action should be named, a sentence over 30 words, and two or more of the words models now overuse (specifically, essential, though, furthermore, vital, alongside, crucial, additionally, notably, ensure, leverage, key) | Code spans; clock times; a single overused word |

What the draft does so the script can see it:

- Names from the code go in code spans. A code span is a reference the reader can look up, so the
  script reads it as neither a label nor a number.
- A new term is marked once, where it is defined, and bold and italic are used for nothing else.

What it cannot see:

- A private name that is an ordinary word ("the sheet", "the check") unless a glossary lists it.
- Whether the answer is first, whether the catch is the right one, or whether the why is true.
- A claim that is backed by evidence that does not support it.

How to fix what it reports:

| Finding | Fix |
|---|---|
| A label | Replace it with plain words, or put a real code name in a code span. Never add a definition. |
| A term before its definition | Move the definition to the first use, or use plain words earlier. |
| Too many terms or numbers | Keep the ones the answer needs and cut the rest; the reader can ask. |
| Too many words | Cut what the card does not need: the order of the session, what was tried, the diff in prose. |
| A superlative | Say what was measured instead. |
| A check without evidence | Put the command in a code span or the result as a number in the same sentence, or say it was not run. |
| A test file not named | Say what changed in it and why, by name. |
| Told as a log | Reorder by the argument: the answer first, the why second. |
| A voice mark | Say it the way you would out loud. A label becomes a sentence ("There's one catch."), a colon or semicolon becomes a full stop, a long sentence becomes two. |
