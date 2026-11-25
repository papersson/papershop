# Ubiquitous-language glossary & term-conflict map

**Status:** CORE
**Loaded when:** different people use the same word for different things, or different words for the
same thing, and a build is about to harden one of those meanings into a field name.

This leaf reduces one uncertainty: **does the team actually share a language, or only appear to?** The
shared-language illusion is the expensive kind — everyone nods at "the order," ships, and discovers in
week one that dispatch's order and billing's order were never the same object. Capture the real,
contested vocabulary and hunt the fractures: homonyms (one word, several meanings across teams) and
synonyms (several words, one thing). This borrows Evans' ubiquitous language discipline only. The
fractures are future field names and candidate bounded-context seams, but **naming the seams is
engineering's job** — you surface them, you do not draw them.

Hold the integrity rules from SKILL.md here especially hard. A term conflict you infer is a
**proposal for the human to confirm, never an assertion**. Shipping a confidently wrong "these two
words mean the same thing" silently merges two real concepts into one column, and the cost surfaces
far downstream where it is dear to undo.

## In the loop — BEFORE / DURING / AFTER

1. **BEFORE.** Scan whatever already encodes the language — tickets, schemas, exports, the field
   labels in the legacy UI, the SOP — and pre-seed candidate terms with the team that uses each. Flag
   suspected collisions as questions, not findings. Build term-probe prompts that force the boundary:
   "When you say *active case*, what exactly counts as active, and what's the last thing you saw that
   you'd say is *not* active anymore?" Phrase for the concrete instance, never the dictionary.
2. **DURING.** Structure the human's typed, dictated, or recorded notes into the glossary rows as
   terms land, each with the speaker's own definition and their team. When a definition contradicts a
   prior interviewee's, flag it in the moment so the human can ask the disambiguating follow-up while
   the person is still in the room — not three interviews later.
3. **AFTER.** Diff definitions across interviews, draft the conflict map, and **propose** which
   clashes are genuine seams (two teams genuinely mean different things and both are right) versus
   sloppiness to standardize (one term drifted and the team would happily converge). Read the proposed
   conflicts back to the human to confirm before any of it feeds the data model.

## Artifact — glossary & term-conflict map

One row per term-as-used. The same word said by two teams with two meanings gets two rows, each
flagged against the other.

| term | meaning as given | team/role | example sentence | conflict flag (homonym/synonym + colliding term) |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

**Disambiguate before coding** — the short list the data model must resolve first:

- *[term]* — [team A means X / team B means Y]; proposed seam, confirm with [who].
- *[term]* / *[term]* — proposed synonyms for the same thing; confirm before they become two columns.
- *[term]* — meaning drifted across [N] interviews; propose standardizing on [definition], confirm.

Mark the artifact **"input to architecture, not the design."** The conflict map says where the
language fractures; it does not name the bounded contexts, and it does not draw the schema.

## When to skip

Skip for a single-team tool with a small vocabulary the team explicitly owns and already uses
consistently — manufacturing term conflicts where none exist is its own waste. But **never skip both
this and systems-of-record**: one of language or source-of-truth is almost always the
buildability-deciding uncertainty, and if you skip this one, the other had better be live.
