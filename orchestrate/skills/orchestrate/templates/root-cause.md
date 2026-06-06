# Template: root-cause

Find why something breaks — a flaky test, a failed pipeline, a production incident, a metric
regression. Use when one context window would fall into self-preferential bias: fixating on its
first hypothesis instead of genuinely testing competing ones. This template is not just for code;
it works for any post-mortem (why did sales drop in March, why did this pipeline fail).

## Graph and verifier

Primitives: scatter-gather (hypotheses from disjoint evidence) → diamond (test each, isolated) →
loop (panel refutes; regenerate until one holds). Verifier: rung 1 — a theory counts only when it
**reliably reproduces and explains** the symptom (a deterministic repro, not an agent's opinion).
Divergence guard: cap the rounds. BLOCKED: on cap with no theory holding, return the evidence and the
surviving candidates rather than shipping a guess as the root cause.

## Shape

Independent hypotheses from disjoint evidence, each adversarially tested, looping until one holds:

1. **Generate hypotheses** — spawn agents over *disjoint* evidence sources (logs, code, data,
   recent changes) so each forms theories from a different angle and they don't cross-contaminate.
2. **Test (fan-out, isolated)** — one agent per hypothesis, each in its own worktree if it needs
   to reproduce or mutate, attempting to confirm or kill that theory. Each returns: theory,
   test performed, result, verdict.
3. **Panel** — for surviving theories, a panel of verifiers and refuters argues each; keep one
   only if it withstands refutation.
4. **Loop until done** — if no theory holds, feed what was learned back and generate a fresh
   round. Stop when a theory is confirmed (reproduced and explained), not when you're tired.

## Fill these in

- **Symptom** — the precise failure, and how to observe/reproduce it (the command, the trace, the metric).
- **Evidence sources** — what the disjoint hypothesis-generating agents each get to look at.
- **Confirmation bar** — what counts as "solved" (reliably reproduced and explained? fix verified?).
- **Stop condition** — a theory confirmed, OR a bounded number of rounds with an honest "not found" if it runs dry.
- **Isolation** — worktrees for any agent that reproduces or edits, so parallel tests don't collide.

## Defaults

- Hypothesis generation and testing: Sonnet; hard reproduction or subtle reasoning: Opus.
- Refuters default to "refuted unless proven" — bias the panel toward skepticism.
- Tell agents to avoid resource-intensive commands so tests can run maximally parallel without
  exhausting the machine.

## Ready-to-fire example

> This test fails maybe 1 in 50 runs. Use a workflow to reproduce it, then spawn agents that form
> independent theories from disjoint evidence — one from the test logs, one from the test code,
> one from recent git history. Test each theory in its own worktree, and have separate refuter
> agents try to kill each one. Loop, generating new theories from what's learned, and don't stop
> until one theory reliably reproduces and explains the flake. Avoid heavy commands so tests
> parallelize.
