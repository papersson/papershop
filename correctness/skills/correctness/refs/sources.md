# Sources

What each source contributes, what was actually read, and what this skill leaves out.

## Adapted from Antithesis's public skills

Both repositories are under the Apache License 2.0. This skill borrows their terminology,
structure and several of their strategies, restated and changed; it does not use the Antithesis
name for itself and is not affiliated with or endorsed by Antithesis.

**antithesishq/antithesis-skills**, version "2026-11-12 6ba10e2".

| Their file | Read | Used here in |
|---|---|---|
| `antithesis-research/SKILL.md` | in full | `modules/research.md`, the scratchbook layout |
| `antithesis-research/references/property-discovery.md` | in full | `modules/research.md` (the attention focuses) |
| `antithesis-research/references/validating-claims.md` | in full | `modules/research.md`, "Validating claims" |
| `antithesis-review-inputs/SKILL.md` and `references/anti-patterns.md` | in full | `modules/review-inputs.md` |
| `antithesis-mutation-testing/references/mutant-design.md` | in full | `modules/mutation.md` |
| `antithesis-mutation-testing/references/sweep-and-verdicts.md` | outline only | the idea of a verdict ladder; the rungs here are this skill's own |
| `antithesis-feature-workload/SKILL.md` | opening only | reach claims in `modules/workload.md` |
| the other references | not read | |

**antithesishq/antithesis-plugin**, version 0.1.0. Read: the README, the explainer,
`workload/MODULE.md`, `workload/surface.md` and the first part of `workload/driver.md`. Used in
`modules/workload.md` (mapping the surface, the driver and its model, recording a request
as sent before sending it) and `modules/workload-deployed.md`. Not read: the launch, triage, debug
and properties modules.

Left out on purpose: everything that launches, inspects or debugs runs on the platform, the
container topology for it, and its SDK calls.

Added here, with no counterpart there: fakes and their verification, the assumption register, the
audit of stored data, the in-process run mode, model checking, and confirmation by a person.

## Other sources

- **Groce, Zhang, Eide, Chen, Regehr, "Swarm Testing", ISSTA 2012.** Per-test-case variation of
  which features are enabled, and the observation that including a feature can suppress behaviour.
- **Feathers, *Working Effectively with Legacy Code*.** Seams and characterization tests.
- **Meszaros, *xUnit Test Patterns*.** Test doubles, and the distinction between a fake and a mock.
- **Minsky, "make illegal states unrepresentable"; King, "Parse, don't validate"; Strom and
  Yemini, "Typestate" (1986).** The basis of `modules/fix-by-design.md`. Which properties a
  redesign made redundant in the author's course was established by rerunning mutants: one
  property became unrepresentable, one was half covered because the language is structurally
  typed, and two still needed the workload.
- **Yuan and others, "Simple Testing Can Prevent Most Critical Failures", OSDI 2014.** Mishandled
  errors as a cause of serious failures; the reason failure-recovery gets its own attention focus.
- **Wayne, "Intro to property-based testing for web applications", Antithesis, October 2026.**
  Slide text only; the recording was not watched. People choose the properties and agents
  implement them.
- **Brown PLT, "Human Judgment as a Specification" (PICK), blog post, June 2026.** Read as a
  summary of the post; the ECOOP paper was not read. Ask a person about concrete inputs on which
  candidate specifications disagree, and ask few questions. Used in research step 10, the second
  pass of `modules/fakes.md` and `templates/question.md`.
- **Wilson with Minsky, "Why Testing is Hard and How to Fix it", Signals and Threads, March
  2026.** Transcript. Three ideas: concrete questions draw out properties that "what are your
  properties?" does not; alerts that would page are properties; a dependency should sometimes be
  made to do the worst its contract allows. Wilson calls the last "bugification". FoundationDB's
  macro is `BUGGIFY`, checked against a summary of the article "Deterministic Simulation Testing:
  BUGGIFY" (transactional.blog, 2021), not against FoundationDB's source.
- **Fioraldi, D'Elia and Balzarotti, "The Use of Likely Invariants as Feedback for Fuzzers",
  USENIX Security 2021.** Abstract only. The nearest published form found of the idea that a rule
  the data almost always obeys is worth treating as a candidate property. Wilson mentions
  "speculative properties" from "a paper somewhere"; that term was not traced to a source.
- **Minsky, "Software Engineering in the Age of Agents", talk, 2026.** Transcript. His
  "differential verification" ("this diff is a noop with respect to the following properties") is
  about proofs. The differential check of a refactoring in `modules/workload.md`
  applies the same question with generated tests, which is ordinary differential testing.
- **Tool documentation and source**, read on 2026-11-13: hegeldev/hegel (README, the Java frontend
  README and `Stateful.java`), antithesishq/bombadil (README and manual sources).

## Measurements quoted

The figures in `refs/anti-patterns.md` under "Large uniform pools" were measured
by the author on a 164-line toy pipeline in a private course repository, with Hypothesis 6.170.15:
runs reaching ten actions on one record were 5.29% of 20,000 uniform runs with 3 records, 0 of
20,000 with 12 records, and 44.2% of 2,000 test cases with a pool of one to three records drawn
per case. They illustrate the effect; they are not a general law.

The two-fakes example in the plugin's `README.md` was written for that page and is printed
there in full. Run on 2026-11-13 with Hypothesis 6.170.15 on Python 3.13, derandomized, 300 test
cases per fake: it passes against the fake that hides a taken job until it is acknowledged and
fails against the one that hands it out again after a timeout, with a counterexample of four
steps. The pass is not empty: counted once, separately, in 36 of the cases generated against the
first fake a worker asked for a job while another had been out for the full timeout.

## What is not established

- The stateful APIs of Hegel's Rust, Go, Python, C++ and OCaml frontends were not run.
- The deployed run mode was not exercised at all in preparing this skill.
- The skill has not yet been run end to end on a real system.
- The confirm step and `templates/question.md` have not been used with a real owning team.
- The differential check of a refactoring and the whole-contract switches were not run in
  preparing this skill.
