# Concern 9: Coordination and tail — restate the problem vs manage it with machinery

## The tension

Two entangled disputes: whether coordination should be eliminated or managed, and whether the
latency distribution is part of the product.

- **Restate until coordination disappears.** Coordination is only *required* where the program is
  non-monotone — where an answer could be invalidated by later information; restate the logic
  monotonically and the same outcome needs no consensus round at all (Hellerstein & Alvaro,
  "Keeping CALM"). And before distributing anything, check the denominator: published distributed
  systems are routinely outperformed by one competent thread, so the honest baseline is a
  single node, with distribution justified against it (McSherry, Isard & Murray, "Scalability!
  But at what COST?"). Machinery you avoided is machinery that never pages you.
- **Some agreement is essential — build the machinery well.** Some invariants are genuinely
  non-monotone: a seat reserved at most once, a balance never negative, a lock with one holder.
  No restatement removes them; the choice is between machinery designed deliberately — consensus,
  leases, fencing — and the same agreement re-implemented accidentally and wrong. On the tail
  side: when one request fans out to N backends, the caller experiences the *worst* of N draws,
  so rare slowness compounds into common slowness — a sold p99 is a feature that must be
  engineered, not an ops metric. Against that, tail machinery without a consumer is speculative
  weight that itself adds latency modes.

## Decided by

Exactly two axes; the pair covers the concern without overlap.

- **Tail obligation (primary for the tail half):** SOLD → the latency distribution is a shipped
  feature: restate first (remove the fan-out or the coordination that creates the tail), then
  budget machinery for the remainder — hedging, deadlines, load shedding. NONE/SOFT → tail
  machinery is speculative weight; a template alert is not a consumer.
- **Writer topology (primary for the machinery half):** essential MULTI-NODE → restate before
  reaching for machinery; where agreement survives restatement, the contention answer picks which
  machinery is load-bearing. CONVERGENT → agreement machinery is the wrong move (it kills
  availability under partition, which is the product); build convergence instead: CRDT-class or
  three-way merge semantics per field, causality metadata, tombstone GC, conflict-surfacing UX.
  EXCLUSIVE → a single agreed order is the component: leader leases, fencing tokens on failover,
  bounded unavailability under partition, consensus where truly needed. Pre-sliced → un-slice
  before optimizing the slices. SINGLE-WRITER → machinery is dead weight. State holding both
  kinds splits per object — the reservation ledger goes EXCLUSIVE while the cart stays
  CONVERGENT. Translation for the common web topology: a serializable shared store already *is*
  single-order commit — N stateless replicas over one transactional database have their EXCLUSIVE
  machinery supplied by the database, and building consensus beside it is double payment.

## What each pole implies concretely

**Restate:** recast operations as commutative, associative, idempotent where the domain allows;
monotone accumulation instead of read-check-write; size the single-node baseline honestly before
distributing; un-slice pre-sliced topologies; delete queues and locks whose only job was
compensating for a non-monotone formulation.

**Machinery (and tail-as-product):** for EXCLUSIVE state, deliberate agreement — leases with
fencing tokens, a designed partition story with bounded unavailability; for CONVERGENT state,
merge semantics and causality metadata as first-class design; where SOLD, a written latency
budget per hop, hedged or deadline-bounded fan-out, load shedding ahead of collapse, and the p99
on a dashboard someone owns.

## Default when undecided

Restate, on a single node, with no tail machinery — and record the artifact that would flip each
half (a qualifying percentile consumer; an exclusivity invariant surviving restatement). This
default degrades gracefully: machinery can be added when the artifact appears, and the
restatement work is never wasted because it shrinks whatever machinery eventually arrives.
Premature machinery degrades badly — it is permanent operational surface, its failure modes are
new product defects, and its cost is paid whether or not anyone needed it.
