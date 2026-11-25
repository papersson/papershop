# The self-driving research loop

`research_loop.js` is the automated meta loop. It is a Workflow script (run by the
orchestrate/Workflow harness, not by node). One invocation runs several research
iterations with no human in between.

## What one iteration does

1. **Read state** — parse `THEORY.md`, `CLAIMS.md`, `LOG.md` into open items.
2. **Plan** — a value function picks the single highest-value open claim and
   designs a concrete, runnable experiment (with a tool preflight).
3. **Snapshot** — record spine hashes so any change can be judged independently.
4. **Implement** — write `experiments/<name>/` and run it for real; reuse the
   spine; allowed to evolve the spine only as documented infrastructure.
5. **Verify** — a separate agent re-runs it, checks artifacts and spine integrity,
   and judges the claim outcome. Bounded fix loop if it's a fixable bug.
6. **Record** — write findings back into the notebook (a refutation is a result).
7. **Critic** — an adversarial "target generator" tries to break the framework
   and lists remaining high-value work; if it comes up **dry**, the loop stops.

Stop conditions: the critic goes dry, no tractable plan remains, or the iteration
cap (`MAX_ITERS`, currently 3) is hit. Each run writes a meta-report to
`/tmp/orchestrate-reports/`.

## Run it

```
Workflow({ scriptPath: "<repo>/research/research_loop.js",
           args: "perf-harness-research-loop" })
```

Tune `MAX_ITERS` at the top of the script. This is the L3 step on the
automate-out-of-the-loop ladder; the human role shrinks to setting the goal and
auditing the report.
