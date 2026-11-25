# Axis 1: Fault reproducibility

**Quick question.** When this component fails, can the failure be reproduced exactly — or is the
environment part of the fault? Gut answer from the component's dependency list; then verify with
the inventory below if the answer drives a contested call.

## Full question (deep pass)

Inventory the component's nondeterminism sources: clock, randomness, thread/task scheduling,
network peers, disk, third-party services, human/user timing. Classify each as **capturable**
(record-and-replay), **injectable behind a seam** (fakeable in a harness at a cost you would pay),
or **not virtualizable at acceptable cost** — and for that last class, name the concrete source
(partition behavior, disk corruption, a partner API's undocumented semantics, human timing).

## Answers

- **REPLAYABLE** — every source captured; any failure replays bit-for-bit from recorded inputs.
- **SEEDED** — every source injectable behind seams; determinism is a *design commitment* you are
  recording here (single-threaded core, simulated clock/net/disk). Write it down as a commitment,
  because it cannot be retrofitted: a threaded, nondeterministic codebase does not acquire
  determinism later.
- **ENVIRONMENTAL** — the fault population is not enumerable or not virtualizable at a cost you'd
  pay; the environment is part of the fault model.
- **Layered** — record as `<core>/<shell>`, e.g. SEEDED-core/ENVIRONMENTAL-shell, and **REPLAYABLE
  cores are legal**: a batch pipeline that replays from captured files inside an environmental
  ingestion shell is REPLAYABLE-core/ENVIRONMENTAL-shell. The layered answer only exists if the
  component split named the core and shell as parts — if you want the layered answer, go back and
  split.

## Day-one checkability

Read the dependency list and the deployment plan; no measurement needed. The honest tell: for each
dependency, ask "could a test hand this a fake?" If the answer requires architecture that doesn't
exist yet, you are choosing between SEEDED (commit now) and ENVIRONMENTAL (accept now) — that
choice is this axis's real output for greenfield work.

## Decides

- **Concern 4, crash aftermath (primary — picks the pole):** REPLAYABLE/SEEDED → hunt and
  eliminate every bug (each crash is a replayable case; draining the population is economical).
  ENVIRONMENTAL → supervise-and-restart for the transient class (bugs entangled with the
  environment cannot be economically eliminated). Layered → eliminate inside the core, supervise
  the shell. Note: this axis picks the *pole*; the supervision *unit* comes from writer topology's
  restart-blast-radius flag.
- **Concern 6, test evidence (joint with writer topology):** SEEDED + multi-node → whole-system
  deterministic simulation pays. REPLAYABLE and simple → generated property tests. ENVIRONMENTAL
  without seams → curated examples plus fault injection, with coverage recorded as explicitly soft.
- **Concern 1, invariant placement (partial):** ENVIRONMENTAL → runtime assertions crashing into a
  supervisor earn their keep (the environment will produce states no proof anticipated).
  REPLAYABLE → static proof pays (the input space is closed enough to reason about).
- **Concern 10, agent delegation (partial):** a replay harness is substrate an agent can iterate
  against — failures become test cases automatically. Without one, a human must adjudicate
  bug-versus-weather on every agent-reported failure.
- **Concern 3, values vs places (partial):** SEEDED pushes event-sourced, immutable inputs at the
  boundary — the log of inputs *is* the replay mechanism.

## Re-fire trigger

First nondeterminism source added that is **not** injectable behind an existing seam — a new
third-party dependency, a hardware peripheral, a peer protocol. This demotes SEEDED/REPLAYABLE and
must be caught at dependency-add time, not at first irreproducible bug.

## Translations and misfits

- **Batch pipelines:** usually REPLAYABLE-core (rerun from captured input files) with an
  ENVIRONMENTAL ingestion shell (SFTP drops arriving late, malformed, or twice). Classify the
  layers separately; don't let flaky ingestion talk you out of a fully replayable transform.
- **Managed runtimes / orchestrators (Spark-style):** the engine's physical scheduling is
  nondeterministic, but if the component's output is a pure function of committed inputs, the
  *component* is still REPLAYABLE. Classify your semantics, not the engine's internals.

## Skip when

Never skip the quick question — it is one sentence and decides concern 4. The deep inventory can
be skipped when the quick answer is uncontested (a pure library: REPLAYABLE; a service orchestrating
three partner APIs: ENVIRONMENTAL) and no downstream call is close.
