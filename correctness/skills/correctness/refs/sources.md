# Sources

What each source contributes, what was actually read, and what this skill leaves out.

## Adapted from Antithesis's public skills

Both repositories are under the Apache License 2.0. This skill borrows their terminology,
structure and several of their strategies, restated and changed; it does not use the Antithesis
name for itself and is not affiliated with or endorsed by Antithesis.

**antithesishq/antithesis-skills**, version "2026-11-12 6ba10e2".

| Their file | Read | Used here in |
|---|---|---|
| `antithesis-research/SKILL.md` | in full | `modules/research/README.md`, the scratchbook layout |
| `antithesis-research/references/property-discovery.md` | in full | `modules/research/property-discovery.md` (the attention focuses) |
| `antithesis-research/references/validating-claims.md` | in full | `modules/research/validating-claims.md` |
| `antithesis-review-inputs/SKILL.md` and `references/anti-patterns.md` | in full | `modules/review-inputs/` |
| `antithesis-mutation-testing/references/mutant-design.md` | in full | `modules/mutation/README.md` |
| `antithesis-mutation-testing/references/sweep-and-verdicts.md` | outline only | the idea of a verdict ladder; the rungs here are this skill's own |
| `antithesis-feature-workload/SKILL.md` | opening only | reach claims in `modules/workload/README.md` |
| the other references | not read | |

**antithesishq/antithesis-plugin**, version 0.1.0. Read: the README, the explainer,
`workload/MODULE.md`, `workload/surface.md` and the first part of `workload/driver.md`. Used in
`modules/workload/README.md` (mapping the surface, the driver and its model, recording a request
as sent before sending it) and `modules/workload/deployed.md`. Not read: the launch, triage, debug
and properties modules.

Left out on purpose: everything that launches, inspects or debugs runs on the platform, the
container topology for it, and its SDK calls.

Added here, with no counterpart there: fakes and their verification, the assumption register, the
audit of stored data, the in-process run mode, and model checking.

## Other sources

- **Groce, Zhang, Eide, Chen, Regehr, "Swarm Testing", ISSTA 2012.** Per-test-case variation of
  which features are enabled, and the observation that including a feature can suppress behaviour.
- **Feathers, *Working Effectively with Legacy Code*.** Seams and characterization tests.
- **Meszaros, *xUnit Test Patterns*.** Test doubles, and the distinction between a fake and a mock.
- **Minsky, "make illegal states unrepresentable"; King, "Parse, don't validate"; Strom and
  Yemini, "Typestate" (1986).** The basis of `modules/triage/fix-by-design.md`. Which properties a
  redesign made redundant in the author's course was established by rerunning mutants: one
  property became unrepresentable, one was half covered because the language is structurally
  typed, and two still needed the workload.
- **Yuan and others, "Simple Testing Can Prevent Most Critical Failures", OSDI 2014.** Mishandled
  errors as a cause of serious failures; the reason failure-recovery gets its own attention focus.
- **Tool documentation and source**, read on 2026-11-13: hegeldev/hegel (README, the Java frontend
  README and `Stateful.java`), antithesishq/bombadil (README and manual sources).

## Measurements quoted

The figures in `modules/review-inputs/anti-patterns.md` under "Large uniform pools" were measured
by the author on a 164-line toy pipeline in a private course repository, with Hypothesis 6.170.15:
runs reaching ten actions on one record were 5.29% of 20,000 uniform runs with 3 records, 0 of
20,000 with 12 records, and 44.2% of 2,000 test cases with a pool of one to three records drawn
per case. They illustrate the effect; they are not a general law.

## What is not established

- The stateful APIs of Hegel's Rust, Go, Python, C++ and OCaml frontends were not run.
- The deployed run mode was not exercised at all in preparing this skill.
- The skill has not yet been run end to end on a real system.
