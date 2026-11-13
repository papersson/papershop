# Design

Why each part is there.

**Modules, not one procedure.** The tasks differ too much for one sequence: a codebase new to
this, a single handler, the aftermath of an incident, a suite that has gone quiet. SKILL.md gates,
makes three decisions, and names the modules the task needs.

**One file per module, and the common path read together.** Research, fakes, workload and the
review of inputs are needed by almost every task and together are a few thousand words, so they
are read in full, not on demand. A step kept in a separate file is a step that gets skipped:
fault injection is a section of the workload file for that reason. Everything else is read when the task
reaches it.

**Antithesis's vocabulary.** Their skills and plugin are where this method is being worked out in
public. Using their terms (SUT, workload, driver, property, assertion types, fault, property
catalog, evidence file) lets a reader move between their material and this skill, and lets work
done here carry over if their platform becomes available. The platform itself is not assumed.

**Run modes before modules.** Their material assumes the whole system runs in containers under
their control. Many teams can change one component and little else, and do not control the
environments it runs in. So the first decision is what can be run at all, and the default is the
smallest thing that gives exact replay: one component in process, with faked dependencies.

**Fakes get a module of their own.** With the dependencies faked, the fake decides the verdict.
The same driver and property can pass against a fake that does what was assumed and fail against
one that does what the service does. So a fake is treated as a claim about another system, with
evidence, owners' confirmation and a mechanical comparison.

**Guarantees and assumptions are kept apart.** An assumption cannot be enforced by the SUT, only
detected or avoided. Listing them separately is what exposes the ones nobody wrote down, and each
row gives the fake a switch, the workload an action and the audit a check.

**People confirm, by scenario.** An agent can read everything and still not know what the owners
intend, and agents are reported to be poor at choosing properties and good at implementing them
(Wayne, in `refs/sources.md`).
So every property and every fake starts as a proposal. A person confirms it by answering one
concrete scenario, because people judge a case well and approve an abstract statement without
reading it closely. Where two candidates exist, the scenario is one on which they disagree, so
each question removes a candidate. Until then a property is recorded, not enforced: its
violations become the next questions. The question is an artifact with a template, like every
other step's output.

**Fakes use the whole contract.** A fake written from observed behaviour is as punctual and
orderly as the service usually is, and the SUT is then never tested against what the service is
allowed to do. Switches for the rare, permitted behaviour, drawn in every test case, close that
gap. This is separate from the switches that make an assumption false.

**An audit module.** Every generated test case starts from a state the generator can build.
Production got to its state by other routes. Properties written as functions over stores can be
run against that state, read-only, with no harness, which makes the audit the cheapest first step
on an existing system.

**Production already states some properties.** An alert that pages someone is a property the
team agreed on, checked after the damage. Stored data shows which proposed properties hold
almost everywhere, and the exceptions are concrete cases to ask about. Both are cheaper sources
of candidates than reading code, and both come with an owner.

**Review of inputs and mutation testing are separate.** One asks whether the workload reaches the
states that matter; the other asks whether a property would notice a bug once there. A surviving
mutant whose marker never fired is a finding about inputs, not about the property, and the verdict
ladder keeps the two apart.

**`Sometimes` is in the rules.** A passing run is only evidence about what it generated. Requiring
the workload to assert that it reached the states it exists to reach turns "print the statistics
and look" into a check that fails.

**A module on fixing by design.** Some properties stop needing a test once the data is redesigned,
and which ones is predictable: what is about the shape of data can be enforced by construction,
and what relates run-time values, stores or moments cannot. The parts of Antithesis's skills read for this one have nothing on
it, since they test systems as they are. It is kept to one short module beside triage, a field in the
property template and a step in mutation testing, so the skill stays a testing skill and does not
turn into a design guide.

**Refactorings are checked differentially.** Once a seam exists, the old and new versions of the
SUT can run on the same generated sequences against the same fakes, which checks a refactoring
on orderings no characterization test lists. It matters most for a fix by design, where the
change is large.

**A program checks what a program can.** Whether every property has an evidence file, every row
of the fault inventory a status, every safety property a row in the mutation report and every finding a way to replay it
are questions with exact answers, so a script answers them and prints one line per failure with
the fix. The templates and the script name the same fields and values, and a test fails when they
drift apart. A template's guidance sits in comments, which the script ignores, so an unfilled
field reads as empty. What is left for a reader is what needs judgement.

**An independent reviewer.** Whoever built a workload knows what it was meant to cover and reads
that into the artifacts, so the last step belongs to a reader without that knowledge: a fresh
agent that gets the review brief and the artifacts and nothing else. It writes down the
properties and faults it expects before reading the catalog, reruns the workload and replays the
findings, and goes through a list of what is usually skipped. It reports and repairs nothing, so
that no fix goes unreviewed. The fault inventory is a file of its own for the same reason: an
omission has to be written down as `not tried` with a reason, where both the script and the
reviewer will find it.

**Hegel and Bombadil as defaults.** Both are open source and run without the platform
(`refs/tools.md` names the versions verified). Hegel has the same stateful shape across languages, with swarm testing
built in, and its drivers are what the Antithesis plugin itself writes. Other libraries are
listed for stacks where it does not fit.

**Model checking is small and last.** It answers a different question (is the design sound) and
pays only for ordering logic. It is here because a proposed fix can be checked in minutes before
it is written.

**How to test this skill.** Give it a small system with known defects and known minimal
counterexamples, and see whether research proposes the properties, the workload finds the
defects, and mutation testing reports the properties that are too weak. A skill that cannot
rediscover a known bug in a small system is not ready for a large one.
