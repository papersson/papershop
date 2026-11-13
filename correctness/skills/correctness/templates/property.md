# Property catalog entry and evidence file

## In `property-catalog.md`

```
### {slug}

**Property:** one sentence.
**Kind:** safety | liveness | reachability
**Assertion:** Always | AlwaysOrUnreachable | Sometimes | Reachable | Unreachable, and why this type.
**Priority:** high | medium | low, and why.
**Enforceable by construction:** by the data type | by an abstract type with a smart constructor | no: a relation between values, cross-store, temporal, concurrent, or about a dependency
**Found under:** the attention focuses that surfaced it.
**Status:** proposed | checked by workload | checked by audit | invalidated (reason)
**Open questions:**
- (needs human input) ...
- (partial: what was found) ...
```

## In `properties/{slug}.md`

```
# {slug}

Claim:            the property, in one sentence
Kind:             guarantee the SUT makes | assumption about a dependency
Evidence:         file and line, log excerpt, or observed request and response
Failure scenario: the sequence of events in which it would be violated
Competing story:  what else would explain the evidence, and why it does not
How to check:     the assertion, audit query or model that would show it false
Where to assert:  in the driver, or at a named point inside the SUT, and whether that check exists already
Open questions:   each with why it matters and what the answer would change

## Investigation log
What was examined, what was found, what was not.
```
