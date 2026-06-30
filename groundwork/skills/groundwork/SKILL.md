---
name: groundwork
description: >
  Run the pre-coding discovery for internal platform and operational tooling, as the partner to a
  human who conducts the real user interviews — prep the question banks before, structure the capture
  during, synthesize between. Use when the user is about to build or scope an internal tool (dispatch,
  back-office, compliance, data-ops, assistance) and wants to "do discovery", "figure out what to
  build", "map the as-is process", "prep questions for an operator interview", map the
  operator-vs-commissioner politics, pin the domain language and systems of record, or scope a thin
  first slice. NOT for consumer-product or market-demand discovery (here the work already exists and
  the need is assumed known — it gates on this and will decline), and NOT for the coding or
  architecture itself — it stops clean at the engineering handoff and hands over artifacts, not a
  schema.
---

# groundwork

This file is a router for the work between "we should build something" and "we write the production
code" — for an internal or operational tool, where a known set of staff already run the real process
today on a mix of legacy software, spreadsheets, and memory. You assist a human who runs the real
interviews: you prep before, structure during, synthesize between and after.

**You are the structuring instrument; the human is the field instrument.** They go and watch the
work; you draft the questions, capture what comes back, and make sense of it across sessions. Never
narrate the work as if you observed it, and mark every conflict you infer as a proposal for the human
to confirm. Every leaf below emits one concrete artifact — understanding is not a deliverable.

Read this, orient, then descend the one or two branches that could sink *this* build.

## Gate — is there groundwork to do?

Run first, every time. The skill earns its cost only in a specific situation:

- **A captive, knowable set of users runs a real process today**, on legacy tools, spreadsheets, and
  tribal knowledge. That is the case this is built for.
- If the question is **"do people want this?"** — consumer or market demand — say so and decline.
  That is a different playbook; the need here is assumed known, and the whole skill is reweighted
  around that one fact.
- If the ask is **the build itself** — schema, architecture, code — hand to the engineering skills.
  groundwork stops at the handoff.
- If the **first deploy is cheap and fully reversible**, say so and offer to skip most of this and go
  straight to a thin slice you can ship and watch (→ `modules/slice/`).
- If **no real users are reachable**, flag that the interview-assist loop runs degraded — everything
  rests on accounts from memory — and lower every downstream confidence with a written caveat.

## Orient — three reads before any interview

**1. The work already exists.** You are recovering the real process, not validating demand. This one
fact reweights everything: market scans and synthesized personas collapse, while as-is process
recovery, the politics between the people, the domain's vocabulary, and what the existing systems
allow all become the main event. Read once: `refs/why-internal-tooling-is-different.md`.

**2. Set the reversibility dial.** How irreversible and high-stakes is the first live action the tool
will take? A wrong automation in dispatch or assistance is a real operational failure, not a bounced
metric — so the more irreversible the first deploy, the more as-is and domain understanding is "enough"
before you slice. A cheap, reversible first deploy earns the opposite: ship thin and learn. The dial
governs how much you front-load and how much weight `modules/slice/` carries. The worked grid is in
`modules/slice/thin-slice-pilot.md`.

**3. The users are nameable.** Segment by organizational role and the metric each role is measured on
— operator, commissioner, and usually a third (auditor, admin, downstream consumer). **Never
synthesize an archetype of a person you can name.** You have a dozen real users; go talk to them.

## The interview-assist loop — run this around every interview

This is the one genuinely sequential thing in the skill. It runs the same three beats around every
interview, and each branch restates it concretely with its own probes.

1. **BEFORE** — draft the question bank from the brief and prior snapshots, phrased so the person
   retells one concrete episode rather than the official version, seeded with the branch's
   workaround and exception probes. (→ `templates/interview-guide.md`)
2. **DURING** — structure the human's typed, dictated, or recorded notes into the branch's artifact
   so they can stay present; flag summary language ("usually," "we always") for a follow-up that
   asks for the last actual time; offer the next probe. (→ `templates/interview-snapshot.md`)
3. **AFTER / BETWEEN** — draft the snapshot, fold it into the running synthesis, diff it against
   earlier interviews, resharpen the guide, and call saturation when fresh signal stops.
   (→ `templates/roster.md`)

## Interview integrity — non-negotiable in every branch

Violating these produces confident, wrong discovery:

- **Anchor every account to one concrete instance.** "Show me the last time that happened," not "how
  do you usually handle it." People forget most of their real steps and describe the sanctioned
  version (Beyer & Holtzblatt's concrete-instance rule). The official process is the lie; the last
  real episode is the truth.
- **Hold the apprentice posture**, even when the person is the expert or the commissioner. The expert
  co-narrating the sanctioned process is the named failure mode — coach back to the specific case.
- **Voice your understanding back to be corrected, not to lead.** Repeat what you heard so they fix
  it; never feed them the answer you expect.
- **Propose, don't assert.** Every term conflict, source-of-truth contradiction, or role tension you
  infer is a proposal for the human to confirm. Shipping a confidently wrong "this is the source of
  truth" is the worst outcome here. Deep craft: `refs/interview-craft.md`.

## Components are uncertainties, not phases

You do not complete the branches. You do just enough of a few of them to responsibly pick one
workflow, then go thin through the slice and come back. On most projects most branches are skipped;
each leaf states when to skip it. There is a default reading order when you have no stronger signal —
as-is, then people, then domain, then frame, then slice — but it is a convenience for orientation,
not a pipeline to march through. The Orient triage picks the two or three branches that could
actually sink this build. The self-check asks only whether each branch you *touched* emitted its
artifact, never whether all branches are done.

## Router — which uncertainty are you reducing?

| You want to… | Go to |
|---|---|
| extract the real process, its exceptions, and its workarounds | `modules/as-is/` |
| map whose metric the tool serves versus whose hands it lives in | `modules/people/` |
| pin the vocabulary, the source of truth, and what's buildable | `modules/domain/` |
| converge on one framed problem and a measurable success line | `modules/frame/` |
| de-risk and ship the thinnest real workflow, stakes-gated | `modules/slice/` |

## Branch index

Two tags, two axes. **`[CORE]`** marks the three branches where the skill goes deep and where the
value and risk concentrate — it is the Orient triage's first suggestion, not a readiness signal.
**`[READY]`** marks the forward-motion branches that close discovery into a build decision. Most
branches are skipped on most projects; descend only on a live uncertainty.

- `modules/as-is/` — how the work really happens: the workaround/exception register (**the core of
  the skill**) and a backstage-weighted as-is service blueprint. **[CORE]**
- `modules/people/` — whose metric the tool serves versus whose hands it lives in: the role-interest
  and metric-ownership map, with the surveillance-versus-enablement read. **[CORE]**
- `modules/domain/` — the vocabulary, the source of truth, and what's buildable: ubiquitous language,
  systems of record, integration and data reality. **[CORE]**
- `modules/frame/` — converge: one framed problem with a hard success metric, and a dual-rooted
  opportunity tree. **[READY]**
- `modules/slice/` — close: the riskiest-assumption test and a thin-slice concierge pilot,
  stakes-gated. **[READY]**

Each branch README lists its leaves with a status tag and a short "Fit" note placing it in the loop.

## Templates — the interview instruments

Three cross-cutting instruments, reused by every branch. They are worked instances to adapt, not to
reinvent each time.

- `templates/interview-guide.md` — the question bank you draft before each session.
- `templates/interview-snapshot.md` — the fixed-slot record you produce per interview.
- `templates/roster.md` — coverage and saturation across the captive user set, in two sizes
  (a full campaign, or a quick spot-check).

## Handoff to engineering — where this stops

groundwork emits the artifacts engineering consumes and reaches no further. The glossary and the
systems-of-record sheet **feed** the data model but do not draw the schema; they surface where the
language fractures and leave naming the bounded contexts to architecture. The slice sketches only the
one workflow's to-be path, never the production architecture. Mark every such artifact "input to
architecture, not the design," hand it over, and stop. If you find yourself drawing tables, classes,
or services, you have crossed the line.

## Read these as you go

- `refs/why-internal-tooling-is-different.md` — the full consumer-versus-operational reweighting:
  what shrinks, what fattens, and why. The one-line version is in Orient; read this once for the
  reasoning.
- `refs/interview-craft.md` — the concrete-instance technique, the expert-interviewer trap,
  interpretation versus leading, and how far to trust accounts from memory. Open when prepping or
  coaching an interviewer.
- `refs/sources.md` — the attributed source map, the contested points, the foils this skill rejects
  (Garrett's planes, the Double Diamond as a waterfall), the persona lineage, the deliberately-skipped
  generic-stack items, and the etymological frame. Open for depth.

## Self-check before committing to a build direction

- Gate passed — the work already exists and real users are reachable (or degraded confidence flagged)?
- Reversibility dial set, and front-loading proportioned to it?
- Did you extract the unhappy path, or only the happy one? Is a recurring "we just email Sven" flagged
  as a structural gap, not an anecdote?
- Are the roles named as real operators, commissioners, and a third role, each with the metric it is
  measured on — and no synthesized archetype of anyone you can name?
- Is every term conflict and source-of-truth contradiction marked as a proposal to confirm, not
  asserted?
- Did you converge to one problem, a hard operational success metric, and an explicit out-of-scope?
- Did each branch you touched emit its artifact — or did you stop at "understanding"?
- Did you stay on discovery's side of the handoff — no schema, no architecture, no bounded contexts
  drawn?

If any answer is no, fix that one thing before handing to framing, design, or engineering.
