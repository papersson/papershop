# Terminology

The vocabulary follows Antithesis's public skills and plugin, so their material can be read
alongside this skill. Where a term means something narrower without their platform, the last
column says so.

| Term | Meaning | Without the platform |
|---|---|---|
| SUT | the system under test | usually one component, not the whole deployment |
| Workload | everything added to exercise the SUT | the same |
| Driver | the program that picks actions, sends them, and checks responses | in-process: a state machine test; deployed: a program beside the SUT |
| Model | what the driver records about what the SUT should contain | the same |
| Property | a statement that must hold, checked over many executions | checked over the test cases generated, not a whole multiverse |
| Guarantee | something the SUT promises; implemented as one or more properties | the same |
| Assumption | something the SUT relies on a dependency to do | a term this skill adds |
| Assertion | the call that checks a property | a library assertion, an invariant, or a recorded event |
| Fault | a disruption injected on purpose | an action of the driver, through a fake or whatever you may disrupt |
| Timeline | one continuous simulated execution | one test case |
| Test case | one generated sequence of actions | the same |
| Counterexample | an execution in which a property fails | printed minimal, after shrinking |
| Property catalog | the list of properties with priorities | the same |
| Evidence file | per property: code paths, scenario, observations, open questions | the same |
| Scratchbook | the directory holding research artifacts | `correctness/scratchbook/` |
| Fake | a working in-memory replacement for a dependency | a term this skill adds; a kind of test double |
| Seam | a place where behaviour can be altered without editing the code there | from Feathers; where a test supplies a dependency |

## Kinds of property

- **Safety**: a bad thing never happens. "An acknowledged write is never lost."
- **Liveness**: a good thing eventually happens. "Every accepted request is eventually answered."
- **Reachability**: a state or code path is reached, or is never reached.

## Assertion types

Choose the type by what the property means, and record the reason in the catalog.

| Type | Passes when | Use for | How to write it without the platform |
|---|---|---|---|
| `Always` | reached at least once, and true every time | safety | an invariant checked after every step |
| `AlwaysOrUnreachable` | true every time it is reached; never reaching it is fine | safety on a path that may not run | an assertion inside the path |
| `Sometimes` | true at least once across the run | liveness, and proof that an interesting state was reached | a recorded event whose count over the run must be above zero |
| `Reachable` | the line is executed at least once | proof a path was exercised | a recorded event at that line |
| `Unreachable` | the line is never executed | a path that must not run | an assertion that fails if reached |

**"Every X is eventually Y"** has no assertion type of its own. In a finite test, write it as a
safety property at quiescence: once the driver has stopped injecting faults and nothing is
pending, every X is Y. Pair it with a `Sometimes` that quiescence with at least one X was reached,
so the check is known to have run. The table's `AlwaysOrUnreachable` is the type for the first
half.

`Sometimes` is not a weak `Always`. It is the check that a passing run was not vacuous: if the
workload exists to reach "two messages for the same record pending at once", assert that it
sometimes does. A library that prints per-run event statistics gives you the count; a run where a
`Sometimes` count is zero has failed, whatever else passed.

## Type system terms

- **Algebraic data types**: types built from **sum types** (one of several cases; also called
  tagged or discriminated unions, or variants) and **product types** (several fields at once).
- **Exhaustive pattern matching**: a match over a sum type that the compiler rejects when a case
  is missing.
- **Making illegal states unrepresentable**: designing a type so that a bad state has no value.
- **Typestate**: encoding an object's state in its type, so an operation exists only where it is
  legal.
- **Nominal and structural typing**: whether two types are the same by name or by shape. Under
  structural typing a value with the right shape is accepted whoever built it.
- **Newtype**: a distinct type over an existing representation, such as an id over a string.
- **Abstract (opaque) type**: a type whose representation is hidden outside its module.
- **Smart constructor**: the only function that can build a value of an abstract type; it checks
  a predicate once. Slogan: parse, don't validate.
- **Representation invariant**: what a module keeps true of its own data, such that code outside
  cannot break it.
- **Refinement type**: a type together with a predicate on its values. **Dependent type**: a type
  that depends on a value. Both can state relations between values statically.
- **Linear and affine types**: values that must be used exactly once, or at most once.
- **Effect type**: the part of a function's type that says what it needs or may do.
- **Negative compilation test**: a file that is expected not to compile, kept to show a mistake is
  rejected.
- **Stillborn mutant**: a mutant that does not compile.

## Property-based testing terms

- **Generator**: produces test inputs from the library's randomness.
- **Shrinking**: the library's search for a smaller failing input. A search, not a guarantee.
- **Stateful property-based testing**: the input is a sequence of rules; properties are checked
  between steps.
- **Swarm testing**: each test case enables a different random subset of rules.
- **Mutation testing**: small deliberate changes to the SUT, to see whether the properties fail.
- **Characterization test**: a test that records what existing code does today.
- **Deterministic simulation testing**: running a system so every source of nondeterminism is
  drawn from a seed. The in-process mode does this for one component with faked dependencies.
