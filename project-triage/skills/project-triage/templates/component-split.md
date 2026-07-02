# Component split — decomposition worksheet

The unit of triage is the component, not the project. Fill this before any axis question. The
most expensive misclassification is treating a component by the rules of its surroundings — the
payment core engineered like the settings page, the "temporary" import script engineered like
neither.

## How to split

Split along **state boundaries** — what owns which mutable state and which persisted data — not
along team, repo, or deployment boundaries. Two modules in one service that own different state
with different consumers can be different regimes; five microservices sharing one database and one
fate can be one.

Heuristic pass, in order:

1. List everything the project touches that holds state: stores, tables, queues, files, in-memory
   session state, external systems written to.
2. Group code by which of that state it owns (writes authoritatively).
3. Each group is a candidate component. Merge groups that would answer every axis identically.
4. **Composite flag:** if any candidate component would answer *any* axis differently across its
   parts, split it further. That axis disagreement is the definition of "distinct regimes".

## The worksheet

| Candidate component | State it owns | Would any axis answer differ from its neighbors? | Verdict |
|---|---|---|---|
| _name_ | _stores / tables / none_ | _which axis, why — or "no"_ | separate record / merge into _X_ / triage later |

## Rules

- **One record per surviving component.** A shared record for two regimes is two wrong records.
- **"Triage later" is legal** for components not being worked on now — but name the event that
  triggers their triage (first change request touching them).
- **The boring shell counts.** A deterministic core inside an environmental shell (parser inside a
  network service, pure pipeline stage inside an orchestrator) is often the split that matters
  most — layered answers on the fault-reproducibility axis exist for exactly this shape, and they
  only work if the shell and core were named here.
- If the split reveals the problem itself is unframed (nobody can say what state a component owns
  because nobody knows what it does), stop: that is discovery work, not triage.
