# Axis 4: Writer topology

**Quick question.** From the deployment plan, take the maximum over all mutable state: one logical
writer, multiple threads in one process, or network-separated writers? Two replicas behind a load
balancer sharing a row count as MULTI-NODE — unless coordination is delegated to a single
transactional store (see translations).

## Full question (deep pass)

From the deployment plan, take the maximum over all mutable state: one logical writer; multiple
threads/tasks in one process; or network-separated writers. Two replicas behind a load balancer
sharing a row count as MULTI-NODE — each replica looks single-threaded, and engineers reliably miss
this unless prompted.

**If MULTI-NODE:** essential (write rate × state size exceeds one node, or survive-node-loss is
required) or pre-sliced?

**If MULTI-NODE (either kind), contention sub-question:** pick the most contended object and ask: if
two partitioned sides both accept a write to it, is there a merge that violates no business rule
(**CONVERGENT**), or does some invariant require exclusivity or a single agreed order — a unit
reserved at most once, a balance never negative, a lock with one holder (**EXCLUSIVE**)? State
containing both kinds of object splits per object.

**Rider — restart blast radius** (carried in the same deployment-plan pass): for each process,
inventory what dies with it — live sessions/connections, accumulated in-memory state and where it
rebuilds from — and write down the survivors' next 60 seconds: do N clients synchronously reconnect,
re-authenticate, or recompute through a shared dependency? **PER-REQUEST** if a process death loses
at most in-flight requests that retry through a balancer; **SESSION-MASS(N)** if one process death
drops a nameable population of live sessions or discards state whose synchronized rebuild stampedes
a shared dependency. (Recorded bet: the first walk where writer-counting causes session mass to be
skipped promotes this rider to a standalone axis verbatim.)

## Answers

- **SINGLE-WRITER** | **MULTI-WRITER-ONE-NODE** | **MULTI-NODE** (essential | pre-sliced;
  contention: **CONVERGENT** — with falsifier: first exclusivity/single-order rule attaching to this
  state — | **EXCLUSIVE**).
- Restart flag: **PER-REQUEST** | **SESSION-MASS(N named)**.

## Day-one checkability

Read the topology *forced by requirements* (availability, geography, offline, data volume), not the
topology someone sketched by habit — the essential-vs-pre-sliced sub-question is the guard against
circularity, since topology is partly a design choice the triage output could itself inform.

## Decides

- **Concern 3, values vs places (primary for the safety half; resource pressure supplies the
  motive):** SINGLE-WRITER → in-place mutation safe wherever heat wants it. MULTI-WRITER → immutable
  values at sharing boundaries. MULTI-NODE → state moves as values.
- **Concern 9, coordination (primary for the machinery half):** essential → restate before
  machinery, then the contention answer picks *which* machinery is load-bearing. EXCLUSIVE →
  agreement machinery IS the component once restatement fails: single-order commit, leader leases,
  fencing tokens on failover, bounded unavailability during partition. CONVERGENT → agreement
  machinery is the wrong move (it kills availability under partition, which is the product); build
  convergence instead: CRDT or three-way merge semantics per field, causality metadata, tombstone
  GC, conflict-surfacing UX. Pre-sliced → un-slice (the pattern of the well-documented Segment
  microservices-to-monolith reversal). SINGLE-WRITER → machinery is dead weight.
- **Concern 4, crash aftermath (partial):** MULTI-NODE → partial failure is a normal input;
  restart-and-recover paths are mandatory, and the contention answer picks their kind — CONVERGENT →
  resume cursors and anti-entropy merge on reconnect; EXCLUSIVE → lease expiry, leadership handoff,
  fencing on failover.
- **Concern 4, granularity (joint with fault reproducibility):** that axis picks the pole; the
  restart flag picks the supervision *unit*. PER-REQUEST → process-granularity crash-freely: assert
  liberally, let the supervisor restart the process, blast radius is one request. SESSION-MASS → the
  fault domain must shrink to the session: assertion failures in per-session code kill the session,
  never the process; drain-and-handoff on planned restarts; process death is an incident, not a
  recovery action.
- **Concern 8, design-phase weight (partial):** SESSION-MASS combined with an EDGED/FROZEN client
  protocol → reconnect jitter, resume cursors, and backoff must be designed into the frozen protocol
  surface before first ship — they cannot be retrofitted onto deployed clients.
- **Concern 6, test evidence (joint with fault reproducibility):** MULTI-NODE + SEEDED →
  whole-system simulation pays, and the contention answer picks the first-class scenario family —
  CONVERGENT → partition-heal merge storms and divergence-then-reconcile runs; EXCLUSIVE →
  split-brain fencing races and failover under partition. SESSION-MASS adds mass-reconnect
  (thundering herd) as a first-class simulated scenario.

## Re-fire triggers

- **Main (topology-side):** any writer-count change in the deployment plan — a second writer process
  added, replication enabled, or the component newly deployed multi-region.
- **Contention (invariant-side, distinct — invariants change on the product calendar, not the
  deployment plan):** a new business rule requiring exclusivity or a single agreed order —
  reservation, quota, balance, or lock semantics — attaching to already-replicated state re-fires
  the contention question *at feature-decision time*, before the feature ships. A CONVERGENT record
  carries this as its explicit falsifier.
- **Rider:** sessions-per-process grows 10×, or a new shared dependency enters the reconnect/rebuild
  path.

## Translations and misfits

- **N stateless app instances + one transactional store** (the most common SaaS topology): the
  component is **logically single-writer via the store** — coordination is delegated to a
  serializable shared database, not sliced and not node-exceeding. Record it as SINGLE-WRITER with a
  note naming the store; do not force MULTI-NODE and then translate the EXCLUSIVE prescriptions
  (leader leases, fencing tokens) back down when "single-order commit" is just the database's
  transactions.
- **Spark-style engines and managed runtimes:** classify the *component's commit semantics*, not the
  engine's physical parallelism. A job whose output commits atomically through a transactional table
  protocol is one logical writer, however many executors ran.
- **Batch second writers people miss:** a concurrent backfill running alongside the scheduled run is
  a realistic second-writer case the deployment-plan framing does not naturally surface — ask for it
  explicitly before recording SINGLE-WRITER on any pipeline.

## Skip when

The contention sub-question is skipped below MULTI-NODE, and the essential-vs-pre-sliced question
with it. The rider is never skipped — it is one inventory carried in the same deployment-plan pass,
and skipping it is exactly the failure its recorded bet watches for.
