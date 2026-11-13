# Fix by design

**Loaded when:** a finding is classed as a SUT defect, before a guard is proposed as the fix.

A guard is a check someone can forget, as the finding has just shown. Some properties can instead
be enforced by construction: the data is redesigned so that the bad state has no value, and the
compiler rejects code that tries to build it. Then the property needs no test, because it cannot
fail. Other properties cannot be carried by types at all, and still need the workload. This module
is how to tell which is which.

A design change alters the SUT far more than a seam does. Propose it; do not make it without the
user's agreement.

## Classify the property first

| The property is about | Can a type carry it? | Then |
|---|---|---|
| which cases exist, which fields go together, how many of a thing there can be | yes, by the data type's definition | make the illegal state unrepresentable |
| which operation is legal in which state | yes, with typestate | define the operation only on the state where it is legal |
| a predicate on one value (non-empty, positive, well-formed) | partly: checked once at run time, then carried by the type | an abstract type with a smart constructor |
| a relation between run-time values (this version is newer than that one) | only with refinement or dependent types | confine the check to one constructor, and keep the property |
| agreement between two stores or two services | no | keep the property; consider deriving one from the other |
| what happens over time (never changes, eventually happens) | no, beyond what typestate gives | keep the property |
| interleavings of concurrent operations | no | keep the property; fix with atomicity, not types |
| what a dependency does | no | it is an assumption: keep the fake honest and audit |

Record the answer in the property's catalog entry (`templates/property.md`, "Enforceable by
construction").

## Techniques

| Technique | What it rules out | Its limit |
|---|---|---|
| **Sum type with exhaustive pattern matching** (tagged union, variant) in place of flags and nullable fields | field combinations that mean nothing; forgetting a case when a new one is added | says nothing about values inside a case |
| **Typestate**: a type per state, and transition functions only from the states that allow them (`Pending -> Approved`) | calling an operation in the wrong state | with structural typing a value of the right shape can be built by hand; without linear or affine types an old value can be used twice |
| **Cardinality in the product type**: one optional field instead of a collection, a non-empty list type | "more than one", "none at all" | the relation of that one value to others |
| **Newtype** (a nominal wrapper, an opaque type alias) for identifiers and units | passing one kind of id or number where another is expected | no predicate by itself |
| **Abstract type with a smart constructor** ("parse, don't validate") | a value that fails the predicate existing anywhere past the constructor; the representation invariant is maintained in one module | the check still runs at run time, once; test the constructor |
| **Refinement or dependent types** | a relation between values, statically | available in few languages |
| **Linear or affine types** (ownership, move semantics) | using a value twice; using it after it was handed on | available in few languages |
| **Effect types or capability passing**: dependencies appear in the function's signature | a handler acquiring a dependency nobody noticed; a test missing a seam | says what may be touched, not that it is used correctly |
| **Derived data**: compute one store from another instead of writing both | two copies disagreeing; a half-finished double write | a design choice, not a type; trades inconsistency for staleness |

## Steps

1. **Port the properties first.** They are the safety net for the redesign. Run them against the
   old design and keep them running against the new one.
2. **Sketch the redesigned types** and say, per property, which technique is meant to carry it.
3. **Show the defect no longer type-checks.** Write the offending code as a small file that is
   expected not to compile (a negative compilation test), and record the compiler's error. That
   error is the counterexample's replacement.
4. **Rerun mutation testing** (`modules/mutation.md`, "After a design fix"). A mutant that
   no longer compiles is stillborn: its property is now enforced by construction. A mutant that
   still compiles and is killed shows a property that is still needed. A mutant that compiles and
   survives is a hole in the types and in the tests.
5. **Keep a cheap backstop** wherever the type system has a known hole: a hand-built value under
   structural typing, a reused value without linear types.
6. **Report both fixes side by side**: the guard, and the design change, with what each costs and
   which properties each makes redundant.

## What to say plainly

Types check the shape of data and the signatures of functions. They do not check that two stores
agree, that a message arrived in order, or that a dependency behaves. Most of the defects this
skill hunts live there, so a design fix reduces the catalog; it does not replace the workload.
