# Sources

What each source actually contributes, what is contested, and what this skill deliberately leaves out.
SKILL.md names a source only in the one inline phrase where it authorizes a move. The full apparatus
lives here.

## The backbone

**Beyer & Holtzblatt — *Contextual Design* (contextual inquiry).** The spine of the whole skill. The
core claim: people cannot reliably narrate how they do their own work, because skilled work
automates into habit and drops below conscious access, so you go watch the work where it happens
rather than interview about it in a conference room. Two moves carry through every branch — the
master/apprentice posture (you are taught the specific case, not given the summary) and the
concrete-instance rule (anchor every account to one real episode, never the general process). The
adaptation this skill makes: the human is the field instrument who can get close to the work; Claude
is the structuring partner who cannot observe it at all. That gap is handled honestly in
`interview-craft.md` under trust-from-memory, and it is the one place this skill knowingly runs
contextual inquiry in a degraded form.

**Eric Evans — *Domain-Driven Design* (ubiquitous language).** Supplies the discipline behind the
domain branch: a domain has a real, contested vocabulary, and the words are load-bearing all the way
into the data model, so the fractures you find — same word two meanings, two words one thing — are
the future field names and the candidate seams between bounded contexts. This skill borrows the
language discipline and stops at the seam. It surfaces the fractures as a conflict map and hands them
over; it does not name the bounded contexts or draw the model. That is the engineering handoff, and
crossing it is the line the self-check guards.

**Teresa Torres — *Continuous Discovery Habits*.** Two contributions. The argument against waterfall
discovery — you cannot specify your way to correctness upfront, so interleave discovery with delivery
rather than completing a research phase before building — which underwrites "components are
uncertainties, not phases." And the Opportunity Solution Tree as a cross-interview synthesis
container. This skill re-roots the tree: a single business-outcome root quietly collapses to the
commissioner's metric and buries operator pain, so the tree is rooted at *both* the commissioner's
metric and operator friction to keep the people split visible inside the synthesis artifact itself.
Torres also supplies the assumption-mapping / smallest-test discipline behind the slice branch,
tilted here toward feasibility (in ops the riskiest assumption is usually "the source system exposes
clean data," not "people want this").

**Eric Ries — *The Lean Startup* (concierge / Wizard-of-Oz).** The thin-validation move: run the
process manually or semi-manually for the operators before automating any of it, which validates your
model of the work *and* ships value on day one at almost no build cost. This skill keeps the move and
gates it on stakes — a human wizard standing in for a real operational decision makes real errors, so
WoZ is bounded by the reversibility dial, not applied universally. Ries also frames the lean critique
of upfront work, which this skill explicitly argues applies *less* to high-stakes operations than to
consumer apps.

**G. Lynn Shostack — service blueprint (*HBR*, 1984).** Originator of the service blueprint and the
line of visibility. The contribution this skill leans on: backstage matters. In operations the value
and the workarounds live *below* the line of visibility — support processes, legacy-dependent steps,
informal handoffs — so the blueprint is re-pointed downward as an extraction tool, used to surface
where the documented process forks from the real one, not to draw a tidy onstage flow.

## The foils — frames considered and rejected

**Jesse James Garrett — *The Elements of User Experience* (five planes).** Strategy → Scope →
Structure → Skeleton → Surface, building from the abstract up to the visible. Considered as the spine
for this skill and rejected: it is too surface-weighted for operational tooling. Three of its five
planes are about the produced interface, which is exactly the layer that thins to "legible, fast,
doesn't fight the user" here. Building the skill on Garrett's planes would budget attention in
inverse proportion to where the value sits. Kept only as the foil that names what this skill is *not*
organized around.

**Design Council — Double Diamond** (Discover → Define → Develop → Deliver). One durable move worth
borrowing: the deliberate Define convergence, the act of narrowing from all the pain you found to one
framed problem. The frame branch uses exactly that, kept re-openable as a gate rather than a one-way
door. Not adopted wholesale, because the four-diamond march reads as a process flavor — a
waterfall in disguise — which is the shape "components are uncertainties, not phases" exists to
reject. Take the Define vocabulary; leave the pipeline.

## The persona lineage

The people branch resolves the persona question by type, and the resolution rests on a real lineage
worth knowing.

**Alan Cooper — *About Face* / *The Inmates Are Running the Asylum*.** Invented the persona: a
synthesized archetype standing in for a user segment you cannot interview individually, used to give a
design team a concrete person to build for instead of an elastic "the user." A genuine advance for
consumer software, where users number in the thousands and are strangers.

**Grudin & Pruitt — critique and extension.** Pushed back on personas drifting into fiction
disconnected from data, and argued for grounding them in real research and engaging the actual people
behind the segment. The critique matters here because it points at the failure mode this skill treats
as disqualifying: a persona that has floated free of any nameable user.

**Adkisson — performance-driver segmentation.** The idea this skill actually keeps: segment a role by
the metric it is measured on. The performance driver — the number a person's work is judged against —
predicts behavior better than demographics or attitude. That is what turns the operator/commissioner
split from a label into a tool: each role carries the metric it is measured on, and the divergence
between those metrics *is* the politics.

**The resolution: synthesized archetypes die; role-segmentation-keyed-to-metric survives.** When you
have a dozen real, nameable users, inventing a composite of them is theatre — and it is widely seen as
theatre even in consumer work where real users are *not* nameable, which is the contested point worth
flagging. What survives is not a persona at all. It is organizational role (operator / commissioner /
third role — auditor, admin, downstream consumer) keyed to Adkisson's performance driver. That is a
factual segmentation you can check against named people, not an archetype you invented. The invariant
in Orient — never synthesize an archetype of a person you can name — is this resolution stated as a
rule.

## Deliberately skipped — the generic stack

Named so the skill can say *why* it skips them, rather than leaving a reader to wonder if they were
forgotten. All three are sound for the question they answer; all three answer the question internal
tooling already has answered.

**Christensen / Ulwick — Jobs-to-be-Done.** Surfaces the underlying job a customer "hires" a product
to do, in spaces where the job is latent and the product is new. Down-weighted here: the job is not
latent. It is a known process people perform daily, and you recover it by extracting the real work
(contextual inquiry), not by abstracting a job statement.

**Osterwalder — Value Proposition Canvas.** Aligns a proposed value proposition against customer
jobs, pains, and gains, for a product seeking a market. There is no market to fit here; the users are
assigned and the value is the friction you remove. The canvas would formalize an alignment that the
as-is and people branches establish more directly.

**BABOK / Wiegers — requirements elicitation.** The heavyweight requirements-engineering tradition.
Its core assumption — that requirements are to be elicited and specified upfront — is the waterfall
shape this skill refuses. The workaround register inverts it: requirements are *discovered in
disguise* inside the exceptions and workarounds, not solicited as a list. Useful as a rigor reference
if a procurement or compliance gate demands a formal spec; not the operating method.

## The etymological frame — interpretive, not sourced

Used as a lens in the design, flagged here as scaffolding rather than a claim to cite.

The word *design* fuses two strands French still keeps separate: *dessein* — intent, the plan held in
the head — and *dessin* — the drawing, the visible artifact. Both descend from Latin *designare*, "to
mark out, to indicate," from *signum*, a sign. The lens this affords: pre-coding work spans the full
range, from holding the purpose (*dessein*), through marking out the user's path (*designare* in its
most literal sense — wayfinding is sign-making), to the produced surface (*dessin*) — and it runs in
that order. Conceptual first, visual last, not the reverse. That is why this skill front-loads the
work, the people, and the domain, and thins the surface to almost nothing.

Mark it for what it is: an interpretive frame that makes the priorities memorable, not evidence for
them. The priorities are argued from the one fact that the work already exists
(`why-internal-tooling-is-different.md`); the etymology only gives that argument a shape to hang on.
Do not cite it as if the Latin proved anything about how to build operational tooling.
