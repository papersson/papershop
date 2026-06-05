# Template: migrate

Mechanically transform every item in a large set — port every file to another language, apply
every fix in a report, get every module to compile, rename a symbol across a codebase. Use when
the work is many independent edits that one context can't hold and that benefit from per-unit
review. This is the shape behind large refactors and ports (e.g. rewriting a project file by file).

## Shape

Pipeline, one independent chain per unit: **do → adversarially review → apply**, with apply
deferred to a single serial barrier.

1. **Split** — serially break the work into discrete units, one per input (one file per finding,
   one source file to port, one callsite). Each agent later gets the same prompt with its own unit
   as the argument.
2. **Do (fan-out)** — one agent per unit makes the change in a clean context, following whatever
   patterns/spec you provide. **Ban slow and stateful commands** (git, build, test, package
   managers): they collide with other agents on a shared branch and exhaust the machine, killing
   the parallelism.
3. **Adversarial review** — one or two agents per unit try to refute the change and surface every
   flaw, also without stateful commands. Loop the fix if review finds problems.
4. **Apply (serial barrier)** — once all units are done and reviewed, a single step lands the
   changes together, runs the build, gets the relevant tests passing, then commits and opens the PR.

## Fill these in

- **Unit** — what one item is, and where the list comes from (a report to split, a glob of files, a list of callsites).
- **Spec / patterns** — the rules the transform must follow (a PORTING guide, a lifetimes table, a style, the target API). Point each agent at it.
- **Review rubric** — what the adversarial reviewers hunt for (correctness, missed edge cases, broken invariants).
- **Isolation** — worktree per agent (agents can build independently) OR shared branch with stateful commands banned (lighter). Pick one, don't mix.
- **Stop condition** — every unit transformed, reviewed, and applied; build green; tests passing.

## Defaults

- Per-unit transform and review: Sonnet; subtle ports or tricky reasoning: Opus.
- Reviewers default to skeptical — find flaws, don't rubber-stamp.
- Defer all build/test/commit to the final serial step; never inside the fan-out.
- Budget scales with unit count; for very large sets pair with `/loop` to continue across runs.

## Ready-to-fire example

> Write a workflow where, for each finding in `./REPORT.md`: step 1, fix the bug — do not run any
> git or build commands, to avoid stepping on another Claude in the same branch. Step 2, use two
> adversarial review agents to refute the fix and uncover every flaw, again with no git or build
> commands. After all findings are done: step 3, apply all the fixes, run the build, get the
> relevant tests to pass, then commit and open a PR. Start by splitting `./REPORT.md` into one
> file per bug and pass each file to the workflow.
