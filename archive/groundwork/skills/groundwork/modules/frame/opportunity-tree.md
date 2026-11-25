# Opportunity tree — dual-rooted, so the people split stays visible

**Status:** READY
**Loaded when:** AFTER a few interviews have stacked up and the snapshots need a container — a place where the divergent pain organizes into opportunities and candidate solutions without losing whose pain it was.

This is the cross-interview synthesis container. The uncertainty it reduces is **how the scattered evidence relates** — which pains are the same opportunity wearing two faces, which candidate solution serves which opportunity, and, the one this re-rooting protects, **whose interest each branch actually serves.** Borrow Torres's Opportunity Solution Tree and change one thing: the root.

A single business-outcome root quietly defaults to the commissioner's metric — throughput, cost, visibility — and buries operator friction as a means to that end. Then every opportunity that helps the operator but not the dashboard looks like a distraction, and the tool ships as surveillance. So **root the tree at BOTH the commissioner's operational metric and operator friction**, side by side. Keep them as two roots, not one blended objective. The split between them is the most important thing the artifact carries, and a single root erases exactly that.

This is a living container, not a finale. **Refresh it every few interviews, not once at the end** — it is where saturation becomes legible, because the interview that adds no new opportunity branch is telling you something.

## The loop around this leaf

1. **AFTER (primary)** — cluster pains across the accumulated snapshots into opportunities, and **attach the verbatim evidence to each branch** — the exact line, with who said it, so an opportunity can never drift loose from the account that justified it. An opportunity with no quote under it is a hunch; mark it as one or cut it.
2. **AFTER** — branch each opportunity down to candidate solutions, kept as options, not commitments — naming the solution is not choosing it.
3. **AFTER** — walk both roots and **surface every branch that serves one root but not the other**: the opportunity that moves the commissioner's metric while adding operator touches, or the one that relieves the operator while doing nothing the dashboard reads. Hand that tension to the human to decide whose interest the solution serves. Do not resolve it silently; **propose, don't assert** — you are showing the split, not picking the winner.
4. **BETWEEN** — at each refresh, note whether the latest interviews added any new opportunity branch. When they stop, that is saturation talking; carry the read to the roster.

## The artifact

A dual-rooted tree, copyable as nested text. Each opportunity tagged with verbatim evidence and the role it came from; each cross-tagged where it serves one root and not the other.

```
OPPORTUNITY TREE — [tool / process] — refreshed [date, interviews N]

ROOT A (commissioner): [the operational metric the commissioner is measured
                        on — e.g. cases closed per week, cost per case, SLA hit rate]

  Opportunity A1: [operator-stated pain, framed as an opportunity]
    evidence: "[verbatim line]" — [name / role]
    evidence: "[verbatim line]" — [name / role]
    └─ Solution candidate: [option]
    └─ Solution candidate: [option]
      ⚠ serves commissioner, costs operator: [how — e.g. adds a logging
         step that feeds the dashboard but slows the close]

  Opportunity A2: [...]
    evidence: "[verbatim line]" — [name / role]
    └─ Solution candidate: [option]

ROOT B (operator): [the friction the operator lives in — the workaround
                    they run every day, the system they route around]

  Opportunity B1: [operator-stated pain, framed as an opportunity]
    evidence: "[verbatim line]" — [name / role]
    └─ Solution candidate: [option]
      ⚠ serves operator, invisible to commissioner: [how — relieves the
         operator but moves no metric the commissioner reads]

  Opportunity B2: [...]
    evidence: "[verbatim line]" — [name / role]
    └─ Solution candidate: [option]

SHARED (serves both roots): [opportunities that move the metric AND relieve
                             friction — the ones to look at hardest]
  Opportunity S1: [...]
    evidence: "[verbatim line]" — [name / role]
    └─ Solution candidate: [option]

— refresh log —
[date, interviews N]: new branches added: [list, or "none — saturating"]
```

Mark the tree **input to the build decision, not the design** — it organizes evidence and surfaces whose-interest; it does not commit to a solution. It feeds the problem-frame (which picks one branch and writes the success line) and `modules/slice/` (which tests the riskiest candidate). The shared branches and the flagged tensions are what the human reads first.

## When to skip

Skip on a small single-workflow tool where the problem frame already names the one opportunity — a tree over a single branch is ceremony. Skip too when commissioner and operator are the same person (a tool someone builds for their own work): there is no people split to keep visible, so the dual root buys nothing — note it and let the problem-frame carry the convergence alone.
