# Concern 4: Crash aftermath — drain the bug vs supervise and restart

## The tension

Both poles agree on more than they dispute: a detected programming error should crash the process
rather than limp onward (an assertion firing is the mechanism working, not failing), there should
be one way to stop (crash) and one way to start (recovery), so the recovery path is the code that
always runs (Candea & Fox, "Crash-Only Software"), and bugs versus recoverable errors deserve
different mechanisms — abandonment for bugs, typed errors for expected conditions; one exception
funnel for both gets reliability structurally wrong (Joe Duffy, "The Error Model").

The split is what happens *after* the crash:

- **Drain the bug.** Every crash is a defect to eliminate, under a zero-tolerance policy
  (Joran Dirk Greef, "TigerStyle"). Economical exactly when every crash is a replayable case —
  deterministic simulation turns a week-long reproduction into a rerun.
- **Supervise and restart.** Field data says most production software faults are transient — 131
  of 132 in Jim Gray's classic Tandem sample ("Why Do Computers Stop and What Can Be Done About
  It?") — so restart-from-known-state is a legitimate handling mechanism, and supervision trees
  are a notation for declaring where state may safely be lost (Fred Hébert, "The Zen of Erlang").

Read as bug economics rather than values, the dispute dissolves: a defect population that replays
deterministically is drainable; one entangled with a nondeterministic environment is an operating
condition.

## Decided by

- **Fault reproducibility (primary — picks the pole):** REPLAYABLE/SEEDED → drain.
  ENVIRONMENTAL → supervise the transient class. Layered → drain the core, supervise the shell.
- **Writer topology (picks the supervision unit):** the restart-blast-radius flag decides *what*
  restarts — PER-REQUEST means process death is nearly free; SESSION-MASS(N) means a restart is a
  thundering herd of N reconnections, which must be a designed, tested scenario, not an ops
  surprise. MULTI-NODE makes partial failure a normal input: restart-and-recover paths are
  mandatory regardless of pole.
- **Defect consequence (override):** HARM/UNRECOVERABLE overrides restart-and-hope in both
  directions — you drain what you can *and* supervise what you can't, and the loss bound prices
  how hard to hunt. BOUNDED-LOSS with a cheap bound licenses more supervision, less hunting.
- **Data gravity's ADVERSARIAL flag:** an attacker who found a crashing input will replay it on
  purpose; "transient" is not a category attackers respect. Eliminate the crash class, and
  sandbox for containment while you do.

## What each pole implies concretely

**Drain:** crash on violated invariants (assertions on, in production); every crash captured as a
replayable seed/case; a bug backlog with a draining policy, not a tolerance; recovery code
exercised constantly because crash is the only stop path.

**Supervise:** an explicit supervision hierarchy declaring where state may be lost and what
restarts together; restart-from-known-stable-state as a designed transition; budget the herd
(SESSION-MASS); alerting on restart *rate*, not restart *events*; and the discipline gate that
precedes both poles — the cheapest reliability win is handling the non-fatal errors the software
already signals (empty catch blocks and TODO handlers are where a large share of catastrophic
failures start; Yuan et al., "Simple Testing Can Prevent Most Critical Failures").

## Default when undecided

If fault reproducibility landed DEFERRED or contested: supervise now (it degrades gracefully when
wrong), and record the drain decision as blocked on the determinism commitment — drain is only
economical after the replay substrate exists, and that substrate is a design-time purchase.
