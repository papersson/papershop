# Design

Why each part is there.

**A router, not a procedure.** The tasks differ too much for one sequence: a codebase new to this,
a single handler, the aftermath of an incident, a suite that has gone quiet. SKILL.md gates, makes
three decisions, and sends the reader to one module.

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

**An audit module.** Every generated test case starts from a state the generator can build.
Production got to its state by other routes. Properties written as functions over stores can be
run against that state, read-only, with no harness, which makes the audit the cheapest first step
on an existing system.

**Review of inputs and mutation testing are separate.** One asks whether the workload reaches the
states that matter; the other asks whether a property would notice a bug once there. A surviving
mutant whose marker never fired is a finding about inputs, not about the property, and the verdict
ladder keeps the two apart.

**`Sometimes` is in the rules.** A passing run is only evidence about what it generated. Requiring
the workload to assert that it reached the states it exists to reach turns "print the statistics
and look" into a check that fails.

**Hegel and Bombadil as defaults.** Both are open source, run without the platform, and were run
before being named here. Hegel has the same stateful shape across languages, with swarm testing
built in, and its drivers are what the Antithesis plugin itself writes. Other libraries are
listed for stacks where it does not fit.

**Model checking is small and last.** It answers a different question (is the design sound) and
pays only for ordering logic. It is here because a proposed fix can be checked in minutes before
it is written.

**How to test this skill.** Give it a small system with known defects and known minimal
counterexamples, and see whether research proposes the properties, the workload finds the
defects, and mutation testing reports the properties that are too weak. A skill that cannot
rediscover a known bug on a toy is not ready for a real system.
