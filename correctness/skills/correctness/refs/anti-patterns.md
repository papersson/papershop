# Input generation anti-patterns

Structural properties of a workload that keep it from reaching regions of behaviour. Adapted from
the catalog in Antithesis's review-inputs skill (`refs/sources.md`), which grounds the first two
in the swarm testing paper (Groce and others, ISSTA 2012).

## Action selection

- **All actions always enabled.** Every test case exercises the full set. Interesting states often
  need some actions to dominate: only writes, so state accumulates; only deletes, against nothing.
  Enable a random subset per case. Many stateful libraries do this already; check
  (`refs/tools.md`).
- **Suppression unnoticed.** An action that is always present can prevent the state a bug needs: a
  pop keeps the stack from growing, a consumer keeps the queue short, a delete keeps the key
  count below the point where compaction starts. Symmetric pairs (put and delete, create and destroy) are the signal.
- **Fixed or uniform weights.** Enabled actions are chosen in the same proportions in every case.
  Draw the weights per case.
- **Fixed ordering.** The harness imposes create, use, delete. Bugs need delete before create, use
  before setup, delete twice. Select each action independently.
- **Hand-tuned bias.** A distribution tuned toward what the author thought interesting trades
  breadth for one hypothesis. Vary the bias per case instead.
- **Fixed run length.** Short runs find shallow bugs; long runs reach accumulated state. Make
  length a per-case draw.
- **Part of the surface untested.** Operations the workload never calls never interact with the
  ones it does.
- **Production thresholds in a test.** A background job set to run hourly never runs in a
  two-minute test. Scale thresholds down, and vary them.
- **Filtering to valid actions.** The workload only does what the current state "allows": never
  deletes what does not exist, never decides what is already decided. The SUT must handle those.
  Keep only the constraints the harness physically needs.

## Data generation

- **Only well-formed inputs.** No missing resources, no malformed values, no mix of good and bad.
- **Hardcoded bounds.** Ranges narrowed with no path to the wider domain the SUT accepts.
- **No boundary values.** Zero, empty, maximum, the value just past a limit.
- **One size.** Payloads and collections all in a narrow band, never empty and never huge.
- **Fixed values.** Always the same key, the same id, the same size.
- **Small fixed pools.** The same few targets in every case. Vary the pool's size and contents per
  case: some cases with one target, some with many.
- **Large uniform pools.** The opposite failure, and easy to miss: every action picks from so many
  targets that no two actions ever meet. A bug that needs many actions on one target becomes
  rare when every action picks evenly among a dozen, and common when each test case draws its
  own pool of one to three.
- **Uniform shape.** Same nesting, same field count, optional fields always present.
- **No absent values.** Nullable things always have a value, arrays are never empty.
- **Identical seed data.** The system always starts with the same initial records.
- **Related fields generated independently**, with no control over whether they are consistent.

## Structure and timing

- **Fixed concurrency.** Always one client, or always the same number.
- **Uniform pacing.** No bursts, no quiet periods.
- **Always starting from empty.** States reached only by long history, migration or old bugs are
  out of reach. Vary the starting state, including "dirty" ones.
- **State that only grows.** Thresholds are crossed once, upward, and never back.
- **One configuration.** Same cluster size, same flags, every run.

## Composition

- **Components on disjoint state.** Several clients that never touch the same things cannot
  contend.
- **Identical components.** Every client draws the same configuration, so they move in step.

## State management

- **The workload does not track what it has done.** With no memory of which things exist, it
  cannot build sequences that depend on earlier steps. This is less than a full model: enough to
  say "the things I created and have not removed".
