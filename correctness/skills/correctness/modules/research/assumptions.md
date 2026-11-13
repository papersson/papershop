# Guarantees and assumptions

Two kinds of statement come out of research, and they need different handling.

| | A guarantee | An assumption |
|---|---|---|
| What it is | something the SUT's own code must ensure | something the SUT relies on a dependency to do |
| Example | "only a pending item can be decided" | "a request I send is applied as I sent it" |
| What you do | enforce it, and check it with the workload | detect when it is false, or stop relying on it |

Incidents that surprise a team usually sit in the second column, in an assumption nobody wrote
down. So write them down.

## Finding assumptions

For each dependency the SUT calls or receives from, ask of the SUT's code:

- **Delivery.** Does it assume every message arrives? Exactly once? In order? Within some time?
- **Effect.** When it asks for something to be done, does it assume the thing is done as asked,
  immediately, and with nothing else done alongside?
- **Reads.** Does it assume a read reflects the latest write? That the state has not moved between
  a read and the write that depends on it?
- **Failure.** When a call fails or times out, does it assume the call had no effect? That it will
  be retried by someone?
- **Versions.** Does it assume every consumer of what it writes understands it?

Each "yes" is a row in the register.

## The register

Write `assumptions.md` from `templates/assumption-register.md`. One row per assumption: the
statement, the evidence that the SUT relies on it (file and line), what is known about whether the
dependency really behaves that way, how its being false would be noticed, who confirmed it, and
when. A row with no confirmation is marked unverified, and stays that way until someone checks.

## What each row feeds

- **The fake** of that dependency must be able to violate the assumption, or the workload will
  never test what happens when it is false (`modules/fakes/`).
- **The workload** gets an action for each way the assumption can fail (`modules/workload/faults.md`).
- **The audit** gets a check that finds, in stored data, the traces a false assumption leaves
  (`modules/audit/`).
