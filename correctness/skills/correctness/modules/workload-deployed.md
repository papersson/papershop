# Deployed workload

**Use when:** the run mode is a deployed SUT with the driver alongside. It adds to "Workload" in
`SKILL.md`.
**Emits:** the same as "Workload".

The SUT runs as it does in production, in its containers, with its real dependencies or as many
of them as can be started. The driver is one more program beside it, sending requests over the
network and checking the responses against its model.

## Confirm access first

Before designing anything, get answers, in writing, from whoever owns the environment:

- May you start the SUT and its dependencies somewhere isolated (a compose file on a workstation,
  a namespace of your own)?
- Can the driver reach the SUT's endpoints and queues from where it runs?
- May you stop, pause or restart containers there, or disrupt the network between them?
- Can you read the SUT's logs and its stores?

If the answer to the first is no, this run mode is closed. Use the in-process mode and the audit.

## The driver

- One program, the main process of its own container or job, written as a state machine with the
  testing library's main entry point so that it runs as one long test case.
- **Startup, in order:** wait until every node answers requests; run any setup the system needs
  (schema, topics, users), retrying until it succeeds and treating "already exists" as success;
  wait until the system serves the workload's own requests; only then start drawing.
- **Requests and the model:** record a request as sent before sending it. A request that fails or
  times out stays unacknowledged, and may still land. Judge each read against every write that
  overlapped it. Keep timeouts short so one unreachable node costs a moment, not the run.
- **Never abort on a failed assertion.** Record it with the values needed to debug it, and carry on.

## Faults

Without a deterministic platform, faults are whatever you are permitted to do: stop or restart a
container, pause it, delay or drop traffic through a proxy, fill a disk. Draw each from the
driver so the choice is at least recorded, and log the time of every fault next to the requests.

## What this mode does not give you

Exact replay. The same seed sends the same requests, but threads, the network and the clock are
not under the driver's control, so a failure may not recur. Record enough (requests, responses,
fault times, logs) to diagnose from one occurrence, and where possible reduce the finding to an
in-process reproduction, which can be replayed.
