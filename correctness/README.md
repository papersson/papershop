# correctness

A Claude Code skill for finding bugs in stateful, concurrent or message-driven code that example
tests rarely reach. The procedure is in
[`skills/correctness/SKILL.md`](skills/correctness/SKILL.md), and the reason for each part is in
[`skills/correctness/DESIGN.md`](skills/correctness/DESIGN.md). This page explains how the work is
split between agents, people and programs, and why.

## How the work is divided

The skill tests one component with everything it talks to replaced by a fake: a small in-memory
replacement that behaves like the real dependency. The test generates random sequences of
actions and checks a property, a statement that must hold after every step.

Here is one such test. A worker takes jobs from a queue. Each job asks for a report to be posted
to a channel. The worker takes a job, posts the report, and acknowledges the job afterwards. The
property: each report is posted at most once. The test was run against two fakes of the queue,
which differ in one line:

```python
return taken_at is None                               # fake A: a taken job stays hidden
return taken_at is None or now - taken_at >= TIMEOUT  # fake B: it comes back after 30 seconds
```

| Fake | Same actions, same property, 300 generated sequences |
|---|---|
| A | passes |
| B | fails, with a counterexample of four steps |

The four steps:

1. A report is requested, and its job goes on the queue.
2. A worker takes the job and posts the report. It has not acknowledged the job yet.
3. Thirty seconds pass.
4. A worker takes the same job and posts the report again.

Fake A is what "take a job" suggests. Fake B is what a queue with a visibility timeout does, so
that a job is not lost when the worker holding it crashes. Nothing inside the test can say which
fake matches the queue this worker will run against. The same holds for the property (may a
report ever be posted twice?) and for what the worker assumes about the services around it. That
knowledge has to come from outside the test, so the work is divided by who can supply it.

| | Who | Does what | Why them |
|---|---|---|---|
| **Propose** | an agent | Reads the code, logs, incident reports and recorded traffic. Drafts the properties, the assumptions and the fakes. Cites evidence for every claim and marks what it could not settle. | There is a lot to read, and an agent can read it. It cannot know what the owners intend. |
| **Confirm** | the people who own the code or the service | Answer concrete scenarios, such as the four steps above followed by "does the queue hand the job out again in step 4?" | A concrete case is easier to judge than an abstract statement, which is easy to approve without reading closely. |
| **Check** | a program, with no judgement involved | Sends the same inputs to the fake and to the real service, where it can be reached, and compares. Breaks the code on purpose to see whether the properties notice. Runs the properties over the data production has stored. | It needs nobody's opinion, so it can catch a wrong proposal that was also confirmed. |

A proposal is a lead until a run or a record shows it, and so is an owner's answer. Owners are
sometimes wrong and services change, so the three rows are repeated whenever the code, the
service or the evidence changes.

## Status

The script behind the example is below. The skill has not yet been run end to end on a
production system, and the confirm step has not been tried with an owning team.
[`refs/sources.md`](skills/correctness/refs/sources.md) lists what was read, what was verified
and what was not.

<details>
<summary>The script behind the example (<code>uv run two_fakes.py</code>)</summary>

```python
# /// script
# requires-python = ">=3.11"
# dependencies = ["hypothesis==6.170.15"]
# ///
"""One worker, one property, two fakes of the queue it takes jobs from."""
import unittest

from hypothesis import settings, strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

TIMEOUT = 30  # seconds


def hidden_until_acknowledged(taken_at, now):  # fake A
    return taken_at is None


def hidden_until_timeout(taken_at, now):  # fake B
    return taken_at is None or now - taken_at >= TIMEOUT


class FakeQueue:
    def __init__(self, can_take):
        self.can_take, self.jobs = can_take, {}  # job -> when it was last taken, or None

    def put(self, job):
        self.jobs[job] = None

    def take(self, now):
        for job, taken_at in self.jobs.items():
            if self.can_take(taken_at, now):
                self.jobs[job] = now
                return job

    def acknowledge(self, job):
        self.jobs.pop(job, None)


def work(queue, now, channel):
    """The code under test: take a job and post its report. The caller acknowledges later."""
    job = queue.take(now)
    if job is not None:
        channel.append(job)
    return job


class Machine(RuleBasedStateMachine):
    can_take = None

    def __init__(self):
        super().__init__()
        self.queue, self.now = FakeQueue(type(self).can_take), 0
        self.channel, self.unacknowledged, self.requested = [], [], 0

    @rule()
    def request_report(self):
        self.requested += 1
        self.queue.put(f"report {self.requested}")

    @rule()
    def worker_takes_job_and_posts(self):
        job = work(self.queue, self.now, self.channel)
        if job is not None:
            self.unacknowledged.append(job)

    @rule()
    def worker_acknowledges(self):
        if self.unacknowledged:
            self.queue.acknowledge(self.unacknowledged.pop(0))

    @rule(seconds=st.sampled_from([1, 10, 30]))
    def time_passes(self, seconds):
        self.now += seconds

    @invariant()
    def each_report_is_posted_at_most_once(self):
        assert len(self.channel) == len(set(self.channel)), f"posted twice: {self.channel}"


class WithFakeA(Machine):
    can_take = staticmethod(hidden_until_acknowledged)


class WithFakeB(Machine):
    can_take = staticmethod(hidden_until_timeout)


for machine in (WithFakeA, WithFakeB):
    machine.TestCase.settings = settings(max_examples=300, derandomize=True)
TestFakeA, TestFakeB = WithFakeA.TestCase, WithFakeB.TestCase

if __name__ == "__main__":
    unittest.main()
```

It prints one failure, for fake B, with the four steps. Fake A passes.

</details>
