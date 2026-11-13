# Fakes

**Use when:** a dependency cannot run where the workload runs, and the in-process run mode needs
something in its place.
**Emits:** the fake, and `fakes/{dependency}.md` recording the evidence for each behaviour and how
the fake was verified.

A fake is a working in-memory implementation of a dependency. A workload's verdict is only as
good as its fakes: the same driver and the same property can pass against a fake that does what
you assumed and fail against one that does what the real service does. Treat a fake as a claim
about someone else's system, and hold it to the evidence standard in
`modules/research/validating-claims.md`.

## What a fake must do

- **Implement the operations the SUT uses**, with real behaviour (state, return values, errors),
  not canned answers.
- **Be able to misbehave on request.** For every row in `assumptions.md` about this dependency,
  the fake needs a switch the driver can use to make the assumption false: deliver late, twice or
  out of order; fail a call; apply a request later than it was made; return a stale read.
- **Take all its choices from the driver.** No clock, randomness or threads of its own.
- **Stay small.** If a fake needs more than a few dozen lines per operation, it is modelling more
  than the SUT depends on.

## Three passes

**1. Propose, with evidence.** For each operation, write down what the real dependency does:
normally, on failure, on repeat, and when its inputs changed between request and effect. Sources,
strongest first: recorded requests and responses; logs; the dependency's source at the *deployed*
version; behaviour observed in a test environment; its docs. Every behaviour cites one. Pay most
attention to anything done "at apply time" from current state: that is where a fake most often
tells a kinder story than the service.

**2. Confirm with the owners.** Give the owning team the evidence file and the open questions
tagged `(needs human input)`. Their answers are stronger than a doc and still a lead; where an
answer and the observed behaviour differ, record both.

**3. Verify mechanically.** Send the same inputs to the fake and to the real dependency, and
compare the answers. A small set of such checks, run against both, is a contract test, and a fake
that passes it is a verified fake. Where the real dependency cannot be called, replay recorded
traffic against the fake instead. Record what was compared and what could not be.

## Where recorded behaviour is found

- the broker's own topics or queues, within their retention
- the version history of stores that keep one
- request logs and traces (often without bodies)
- a recording proxy in front of the dependency in a test environment
- past incidents: write-ups, tickets, chat channels, fix and revert commits

Production payloads may be sensitive. Prefer a test environment, or strip the data first.

## Done when

- [ ] Every behaviour of the fake cites evidence, or is listed as unverified.
- [ ] Every assumption about this dependency can be made false by the driver.
- [ ] The fake was compared with the real dependency or with recordings, and the result is recorded.
- [ ] The evidence file says what the fake does *not* model.
