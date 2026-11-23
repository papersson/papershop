# Quick mode in detail

Read this when a line of the card or a part of the shape needs more than SKILL.md gives it. One
invented example runs through the file: a nightly data load that finished too late for the
analysts, made faster in an afternoon. `scripts/samples/pass-quick.md` is its presentation and
`scripts/samples/fail-quick.md` the same work told badly.

## The card, line by line

| Line | Rule | The failure it prevents |
|---|---|---|
| Goal | The request in the reader's own words, as one clause. Not the task list. | A report of activity with no measure of success. |
| Answer | What is now true, as a plain statement, with the comparison that makes its number mean something. | An answer spread across paragraphs, or a number nobody can weigh. |
| Why | What the diff cannot show: the problem behind the request, the alternative rejected and why, the tradeoff accepted. Answer the question the reader would ask: why this, rather than what they expected? | A description that recites the code and omits the framing. |
| Key idea | The one idea a colleague would need to have done this themselves, with one concrete case. "Routine" when the work had none. | A result that is correct and teaches nothing. |
| The catch | The single limitation, gap or departure from the request that changes what the reader should do. If there is none, there is none. | The decisive limitation filed at the end, where no one reads it. |
| Opaque | What works but is not understood: a fix found by trying, a number that cannot yet be explained. | A confident report over a part nobody can explain. |
| Next | What the reader has to decide or do, ranked by what it gains for what it costs, and the result that would reorder it. | An ending that lists options, or ends on the result. |

The card for the example:

```
Goal:      the data ready before the analysts start at 07:00
Answer:    it finishes by 05:40 on staging, against 08:50 the week before
Why:       the time went into rereading unchanged files; a faster disk made no difference
Key idea:  skip a file whose fingerprint (a code computed from its contents) matches last night's
The catch: a provider format change changes every fingerprint, so that night is slow again
Opaque:    two nights read four more files than the others, and I don't know why
Next:      decide whether to run it on production tonight; then split the reload by season
```

## The shape, paragraph by paragraph

1. **Goal, answer, catch.** The first sentence names the goal. The second gives the answer with
   its comparison and what that means for the goal ("so there's an hour to spare"). The catch
   follows at once. A reader who stops here has the answer and the one thing that could change
   their decision.
2. **Why and the key idea.** Lead with the cause, then the idea that answered it, introduced by a
   concrete case before any name. One sentence for the alternative that was rejected, if it
   explains the choice. Anything opaque goes here, in the first person and plainly ("I don't yet
   know why two nights read more files").
3. **Next.** What the reader decides or does, ranked. An if-then names the result that would
   change the order.

## Explain, don't prove

The report explains the work; it does not audit it. Test runs, commands, counts of passing tests
and "I made sure that" belong in the report only when the reader asked for them, or when the catch
is that something didn't work ("the import job still fails on old files"). Everything else the
reader can ask for, and asking is cheap in a conversation.

## What to leave out

- The order of the session: what was read first, what was tried next.
- Everything tried that did not change the answer, beyond one sentence.
- The diff in prose: function by function, file by file.
- Proof nobody asked for: test runs, commands, how you made sure.
- Private names: the session's names for its own ideas and runs. Plain words replace them.
- Offers of further help and summaries of the summary.
