# Validating claims

Sources outside the code tell you things about the system. They are leads, not facts. A claim
earns a place in the analysis only when you have evidence that *exhibits* the behaviour (the code,
a log, a reproduction), not merely a source that *asserts* it.

Validate what you build on, not everything you read. The moment a claim needs validation is the
moment you would state it as something the system does, or turn it into a property.

## Two kinds of input

**Claimed guarantees.** The system's own docs, design notes and comments stating intended
behaviour ("failed messages are retried"). Turn each into a property and let the workload test it.
The one discipline: do not write that the guarantee *holds*. Write that the system claims it and
that the property checks it. Docs drift, and comments describe the code someone meant to write.

**Reports of defects.** A ticket, an incident write-up, a message in a chat channel. One person's
account of their own problem, and the reporter is often wrong about the cause. It becomes a
property only after you have read the primary evidence (the logs, the reproduction, the mechanism
in the code, the fix) and ruled out the ordinary alternatives: configuration, environment,
misunderstanding. Ground the property in the mechanism you found, not in the report's wording.

## What validation requires

1. **Name the competing explanation before you look.** For a reported bug it is nearly always
   "this was the reporter's environment or configuration, not the system".
2. **Read the evidence that tells the two apart**, past the title and first paragraph.
3. **Record the detail that settles it.** "The ticket says messages were lost" cites the claim.
   "The consumer's log shows the handler raising and the offset advancing in the same second"
   discriminates. If you cannot quote the discriminating detail, the claim is not validated.

If you cannot settle it, the claim does not become a property or a stated behaviour. Record it as
an open question tagged `(needs human input)`.

## The same standard applies to people

An owner's statement about their own service is stronger evidence than a doc, and still a lead.
Where an owner's answer and the code disagree, record both and say which you observed.
