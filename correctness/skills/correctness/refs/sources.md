# Sources

What each source contributes, how much of it was read, and what this skill leaves out.

## Adapted from Antithesis's public skills

Both repositories are under the Apache License 2.0. This skill borrows their terminology,
structure and several of their strategies, restated and changed; it does not use the Antithesis
name for itself and is not affiliated with or endorsed by Antithesis.

**antithesishq/antithesis-skills**, commit 6ba10e2 of 2026-11-12.

| Their file | Read | Used here in |
|---|---|---|
| `antithesis-research/SKILL.md` | in full | "Research" in `SKILL.md`, the scratchbook layout |
| `antithesis-research/references/property-discovery.md` | in full | "Research" in `SKILL.md` (the attention focuses) |
| `antithesis-research/references/validating-claims.md` | in full | "Validating claims" in `SKILL.md` |
| `antithesis-review-inputs/SKILL.md` and `references/anti-patterns.md` | in full | `modules/review-inputs.md` |
| `antithesis-mutation-testing/references/mutant-design.md` | in full | "Mutation testing" in `SKILL.md` |
| `antithesis-mutation-testing/references/sweep-and-verdicts.md` | outline only | the idea of a verdict ladder; the rungs here are this skill's own |
| `antithesis-feature-workload/SKILL.md` | opening section | `Sometimes` and `Reachable` assertions in "Workload" in `SKILL.md` |
| the other references | not read | |

**antithesishq/antithesis-plugin**, version 0.1.0. Read: the README, the explainer,
`workload/MODULE.md`, `workload/surface.md` and the first part of `workload/driver.md`. Used in
"Workload" in `SKILL.md` (mapping the surface, the driver and its model, recording a request
as sent before sending it) and `modules/workload-deployed.md`. Not read: the launch, triage, debug
and properties modules.

Left out on purpose: everything that launches, inspects or debugs runs on the platform, the
container topology for it, and its SDK calls.

Added here, with no counterpart in the parts read: fakes and their verification, the assumption register, the
audit of stored data, the in-process run mode, model checking, and confirmation by a person.

## Other sources

- **Groce, Zhang, Eide, Chen, Regehr, "Swarm Testing", ISSTA 2012.** Per-test-case variation of
  which features are enabled, and the observation that including a feature can suppress behaviour.
- **Feathers, *Working Effectively with Legacy Code*.** Seams and characterization tests.
- **Meszaros, *xUnit Test Patterns*.** Test doubles, and the distinction between a fake and a mock.
- **Minsky, "make illegal states unrepresentable"; King, "Parse, don't validate"; Strom and
  Yemini, "Typestate" (1986).** The basis of `modules/fix-by-design.md`.
- **Yuan and others, "Simple Testing Can Prevent Most Critical Failures", OSDI 2014.** Mishandled
  errors as a cause of serious failures; the reason failure-recovery gets its own attention focus.
- **Wayne, "Intro to property-based testing for web applications", Antithesis, October 2026.**
  Slides. People choose the properties and agents implement them.
- **Brown PLT, "Human Judgment as a Specification" (PICK), blog post, June 2026.** The post, not
  the ECOOP paper behind it. Ask a person about concrete inputs on which
  candidate specifications disagree, and ask few questions. Used in research step 10, the second
  pass of "Fakes" in `SKILL.md` and `templates/question.md`.
- **Wilson with Minsky, "Why Testing is Hard and How to Fix it", Signals and Threads, March
  2026.** Transcript. Three ideas: concrete questions draw out properties that "what are your
  properties?" does not; alerts that would page are properties; a dependency should sometimes be
  made to do the worst its contract allows. Wilson calls the last "bugification". FoundationDB's
  macro is `BUGGIFY` ("Deterministic Simulation Testing: BUGGIFY", transactional.blog, 2021).
- **Fioraldi, D'Elia and Balzarotti, "The Use of Likely Invariants as Feedback for Fuzzers",
  USENIX Security 2021.** Abstract. A rule the data almost always obeys is worth treating as a
  candidate property.
- **Minsky, "Software Engineering in the Age of Agents", talk, 2026.** Transcript. His
  "differential verification" ("this diff is a noop with respect to the following properties") is
  about proofs. The differential check of a refactoring in "Workload" in `SKILL.md`
  applies the same question with generated tests, which is ordinary differential testing.
- **Tool documentation and source**, read on 2026-11-13: hegeldev/hegel (README, the Java frontend
  README and `Stateful.java`), antithesishq/bombadil (README and manual sources).

## The example in the plugin's README

The two-fakes example in the plugin's `README.md` is printed there in full and can be rerun with
`uv run`. With Hypothesis 6.170.15 on Python 3.13, derandomized, 300 test cases per fake, it
passes against the fake that hides a taken job until it is acknowledged and fails against the one
that hands it out again after a timeout, with a counterexample of four steps.

## Not verified

- The stateful APIs of Hegel's Rust, Go, Python, C++ and OCaml frontends.
- The deployed run mode.
- The differential check of a refactoring, and the whole-contract switches in fakes.
- The skill as a whole on a production system, and the confirm step with an owning team.
