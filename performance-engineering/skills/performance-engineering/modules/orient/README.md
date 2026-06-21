# orient — understand the terrain first

Mid-level index (progressive disclosure). Enter at the start of any perf task to place the problem on the stack and pick local-vs-prod context.

## Leaves
- `software-stack.md` — the stack as a where-map (app→libs→syscalls→kernel→hardware + distributed tier map). [READY]
- `work-taxonomy.md` — classify the workload with 5 lenses. [READY]
- `latency-numbers.md` — latency/bandwidth/cost cheat-sheet + back-of-envelope estimation. [READY — consolidate]
- `bound-types.md` — diagnose what kind of bottleneck you have (CPU/memory/IO/lock/...). [READY]

## Fit
First stop in the SKILL.md loop: before measuring or fixing anything, locate the problem on the stack, name the work, and decide whether you are in a local or production context. Routes onward to diagnose/ and to environment/.
