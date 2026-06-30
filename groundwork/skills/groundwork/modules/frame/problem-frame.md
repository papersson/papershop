# Problem frame — one problem, one hard success line, re-openable

**Status:** READY
**Loaded when:** AFTER enough interviews that the pain has stopped surprising you, and a build commitment is the next move — the divergent register needs to collapse to one decision.

This is the convergence gate. The CORE branches diverged on purpose: you now hold more workarounds, tensions, and source-of-truth gaps than any one tool can fix. The uncertainty this leaf reduces is **which single problem you are building against, and what counts as having solved it** — stated hard enough that a working tool and a busy tool can be told apart six weeks after deploy.

Borrow the Double Diamond's one durable move — the deliberate Define convergence — and leave its waterfall behind. Define here is **a gate, not a one-way door.** You narrow to one frame because you cannot build five; you keep it re-openable because the next two interviews might prove you narrowed wrong. The internal-tooling gift is that your success line can be *hard* in a way consumer engagement never is: cycle time, manual touches per case, error and rework rate are real operational counters, measurable before and after. Spend that gift. A frame whose success line is "operators feel less friction" wasted it.

## The loop around this leaf

1. **BEFORE** — cluster the divergent pains from prior snapshots into two or three candidate problem frames the human can put in front of the next interviewees. Phrase each as a sentence a real operator would either nod at or correct, not as a goal statement. Draft, for each candidate, the rough operational metric it would move, so the human can sense-check measurability before committing.
2. **DURING** — help pose the tradeoff out loud: *"If we could only fix one of these this quarter, which one — and what would change for you the next morning?"* Capture which frame each role ranks first, and capture it by role, because the commissioner and the operator will rank differently and that gap is signal, not noise. Flag any frame the person reframes in their own words — their version is usually closer to the real problem than yours.
3. **AFTER** — draft the converged statement and the metric-based success line from what the snapshots actually said, not from the brief's ambition. Pull the out-of-scope list straight from pains you are deliberately *not* fixing so it reads as decisions, not omissions. Set the reversibility note against the dial from Orient. List, explicitly, **what diverging evidence would re-open this gate** — name it now, while you can still tell a surprise from a confirmation.

## The artifact

A one-page frame the build decision hangs on. Fill every slot; an empty success line means you have not converged, only summarized.

```
## Problem frame — [tool / process] — [date, interviews N]

**The problem (one paragraph).**
[One framed problem in plain operational language: who hits it, in what
work, how often, and why the current process can't absorb it. Written so
a named operator would recognize it as their Tuesday, not as a strategy
slide. One problem — if you need "and", you have two frames; pick one.]

**Success line (hard ops metrics).** We will know this worked when:
- Cycle time: [from X to Y for the named case — e.g. case close from
  3 days to same-day]
- Manual touches per case: [from N to M — the count of human steps /
  re-keyings / system hops per case]
- Error / rework rate: [from P% to Q% — re-opens, corrections, escalations
  per hundred cases]
[At least one must be a real counter you can read before and after. If a
line can't be measured, it is not a success line — cut it or make it hard.]

**Out of scope (decisions, not omissions).**
- [Pain we found and are deliberately NOT fixing in this build] — because […]
- [Role / workflow / integration explicitly excluded] — because […]

**Reversibility note (calibrated to the Orient dial).**
- First live action the tool takes: [what it does, to what, irreversibly or not]
- Stakes if wrong: [reversible annoyance ↔ physical/legal/operational harm]
- Enough-understanding read: [how much more as-is / integration-reality is
  needed before first deploy, given that stakes rating — points at
  modules/slice/ or says "ship thin and watch"]

**This gate re-opens if:**
- [A named role ranks a different frame first in the next interviews]
- [A workaround cluster recurs that this frame doesn't touch]
- [Integration-reality proves the success metric unmeasurable or the
  problem unbuildable as framed]
```

Mark the page **input to the build decision, not the design** — it names the problem and the bar; it does not name a solution. The solutions live one layer down in the opportunity tree and get tested in slice.

## When to skip

Skip only for pure exploratory discovery with no near-term build, or when the problem is already sharply framed and agreed by the people who'll be measured on it — don't manufacture a ceremony around a decision already made. **Do not skip if any build commitment follows.** This is the leaf that produces the actual decision; skipping it means building against a pile of pain with no agreed bar, which is how an ops tool ships busy and unloved.
