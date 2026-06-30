# Workaround & exception register

**Status:** CORE
**Loaded when:** the as-is branch, every interview where a real process is being recovered — the loop's first and highest-value capture.

This is the core leaf of the skill. The one uncertainty it reduces: what does the current system *fail to do*, such that a human has to step in and route around it. **The as-is gold is the unhappy path.** Happy-path-only discovery ships a tool that is useless in week one, because week one is when the first exception arrives and the operator reaches, by reflex, for the workaround the tool never heard of. Each workaround is two things at once — a requirement in disguise, and a documented failure of the system that exists today. Capture both.

## The loop, for this leaf

1. **BEFORE** — draft a domain-specific "what happens when it goes wrong" probe bank from the brief and prior snapshots. Phrase every probe for one concrete instance: "show me the last time a case wouldn't go through," not "what do you do when a case won't go through." Seed the exits people forget they use — the manual override, the side channel, the person they ping, the spreadsheet that shadows the system of record.
2. **DURING** — structure the human's typed, dictated, or recorded notes into the register's rows as exceptions surface, and feed back a short nudge list that keeps the interviewer off the happy path: *what blocks this? who do you escalate to? what does the system not let you do? what do you do outside it?* When you hear "usually" or "we always," flag it — that is summary language papering over a specific episode; the follow-up asks for the last actual time.
3. **AFTER** — convert each captured workaround into a candidate requirement, name the system failure it documents, and increment its recurrence count against earlier interviews. The same Sven named in five interviews is a structural gap, not an anecdote — recurrence is the signal that promotes a workaround from "one operator's habit" to "the thing the tool must absorb." Propose each implied requirement for the human to confirm; do not assert it.

## The artifact

One register per process, accreting rows across interviews. Recurrence is the column that does the work — sort by it and the build's real requirements rise to the top.

| Triggering exception event | Current workaround performed | Who/what it routes to (human dependency / shadow tool) | Implied requirement | System failure it documents | Recurrence (across interviews) |
|---|---|---|---|---|---|
| Case arrives with no postcode | Operator hand-looks it in an external map site, pastes it back | Shadow tool: maps.example | Tool must geocode or accept a manual location with provenance | Intake form accepts records the downstream step can't process | 4 |
| Customer flagged "VIP" but system has no such field | Operator emails Sven, who "knows the ones that matter" | Human dependency: Sven | Tool must hold the priority attribute the business already acts on | No field for a status the work clearly depends on | 5 |
| Two systems disagree on the balance | Operator trusts the spreadsheet, not the ERP | Shadow tool: the team spreadsheet | Tool must name an authoritative source per field (→ domain/systems-of-record) | ERP is stale; the real source of truth is undocumented | 3 |
|  |  |  |  |  |  |

Fill it for real. Each row earns its place by being a thing an operator *actually did* in a *specific episode*, not a thing they say they "would" do. A row whose recurrence is 1 is a watch item; a row at 4 or 5 is a requirement you would be negligent to ship without.

Hand the human-dependency rows to `modules/people/` (every named Sven is a role and a single point of failure), the shadow-tool rows to `modules/domain/` (every spreadsheet is a candidate system of record and a vocabulary source), and the highest-recurrence rows to `modules/frame/` as the pains most likely to be the problem worth solving.

## When to skip

Rarely, for operational tooling — this is the leaf the branch exists for. Skip only when the tool replaces no existing process at all (genuinely greenfield, which is rare here and should make you re-check the gate: if the work already exists, so does its unhappy path). If the process is so short and linear that a handful of workaround rows capture it whole, you can skip the companion `service-blueprint.md` and let this register stand as the entire as-is record.
