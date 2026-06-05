---
name: prose
description: >
  Improve the STYLE of writing without changing what it says: strip the signatures of AI/LLM text
  and bad prose, and move toward careful human writing (especially technical and explanatory).
  Two modes: `rewrite` returns clean prose silently; `review` returns a located, attributed
  critique that teaches. Use when authoring or refining any human-facing prose (READMEs, docs,
  essays, design notes, reports, commit messages, PR descriptions, substantial comments or
  docstrings), or when asked to refine, humanize, de-slop, tighten, or critique writing. Style
  only: it never alters facts, claims, or argument.
---

# prose

Improve how writing reads without touching what it says. This skill changes style only. It never
alters facts, claims, arguments, or meaning. Its two jobs are to strip the signatures of
machine-generated text and to move prose toward the qualities of careful human writing, with weight
on technical and explanatory work.

`reference.md` (alongside this skill) holds the full catalog of tells and the principles, attributed,
with calibrated before/after pairs. Read it for depth; the essentials are below.

## Two modes — pick one

**`rewrite`** (default). Triggered by "clean this up", "refine", "humanize", "de-slop", "tighten",
"make this read well", or by drafting new prose. **Your entire response is the rewritten text.** No
preamble, no "here's what I changed", no trailing notes. If the user wants to know what changed,
that is `review`. When drafting from scratch, apply the principles silently as you write.

**`review`** (the teacher). Triggered by "what's wrong with this", "critique", "review my writing",
"help me improve", "teach me". Output a **located** critique and do not rewrite the whole piece
unless asked. For each issue, give: the quoted span, the tell or pathology, the principle it
violates (attributed), and the targeted fix. Lead with what already works so the writer keeps it;
order findings by impact. This mode exists to build the writer's sense, so **name the pattern,
don't just fix it** — a writer learns from "this buries the verb in a nominalization (Sword's
zombie noun): 'I investigated', not 'I conducted an investigation of'", not from a silent edit.

If the request is ambiguous between the two and the choice changes the output, ask once. Otherwise
default to `rewrite`. A combined "coach" request (critique then rewrite) is fine when asked for;
keep the critique and the prose visibly separate.

**The contract, held firm:** never leak commentary into `rewrite`, and never silently rewrite in
`review`. The most common failure of a de-slopping tool is becoming chatty — producing slop about
removing slop. Keep explanation quarantined in `review`.

## Style only

Preserve facts, claims, the line of argument, and meaning exactly. You may split or join sentences
and reorder for flow, but every proposition must survive. Do not invent specifics, soften a claim,
or add a hedge the author didn't make. If the prose is murky because the *thinking* is murky
(Orwell's point: the great enemy of clear language is insincerity), say so in `review`; don't paper
over it with borrowed clarity. In `rewrite`, keep the author's commitments intact.

## Context sets the target

"Good" is relative to register. Calibrate before editing: a commit message wants terse; reference
docs want austere neutral description; a tutorial wants warm second person; an essay wants voice
and rhythm. Infer the register from the text and where it's going. When genuinely unsure and it
changes the edit, ask. Do not flatten everything into one house voice.

## Detect and remove

The tell is **density and predictability**, not any single word. A human uses any of these
sometimes; machine text uses them constantly.

- **Lexical tells:** the inflated cluster (*delve, crucial, pivotal, tapestry, testament,
  underscore, showcase, vibrant, intricate, leverage, foster, garner, seamless, robust*); copula
  avoidance ("serves as a", "stands as", "represents" where "is" belongs); marketing verbs
  (*boasts, offers, features* for *has*).
- **Structural tells:** negative parallelism ("not only X but also Y"); the rule of three (three
  approximate words for one precise one); participial synthesis ("...highlighting the need for
  further research"); the challenge/future-directions coda; hollow significance ("groundbreaking",
  "vital", "invaluable").
- **Pathologies (older than LLMs, and why the tells fail):** vagueness and abstraction; Latinate
  inflation; nominalizations (zombie nouns) that hide the actor; the curse of knowledge; clutter;
  dead metaphors; verbal false limbs ("give rise to", "make contact with"); ritual hedging as
  social armor; metadiscourse (prose about the prose).
- **Statistical:** low burstiness (uniform sentence length and shape). Exception: precision genres
  (legal, reference, API docs) are uniformly dense by design; there it is not a tell.

## Move toward

Six themes (full attribution in `reference.md`):

- **Concreteness** — specific over abstract; name the thing; the concrete carries the argument, not
  just the illustration (Strunk, Orwell, Clark).
- **Cadence** — vary sentence length deliberately; read it aloud; parallelism by choice, not by
  accident (Provost, Graham).
- **Coherence** — open with the known, extend to the new; connect through content, not "Furthermore"
  (Pinker).
- **Voice** — write close to how you'd say it; treat the reader as an equal, neither condescending
  nor obsequious (Graham, Zinsser, Thomas & Turner).
- **Cutting** — every word earns its place; active voice with a named actor (passive only when the
  agent is unknown or irrelevant); short Anglo-Saxon over long Latinate (Zinsser, Strunk, Orwell).
- **Honesty** — make claims as strong as they can be without becoming false; hedge only real
  uncertainty; commit (Graham, Alexander, Feynman).

For technical and explanatory writing specifically: build the reader's mental model rather than
recording your own; put the concrete image before the abstract label (scene before symbol);
demonstrate interest, don't announce it ("notably", "interestingly" signal the opposite).

## The biggest risk: over-correction

De-slopping has its own tell. Prose sanded into uniform short clipped declaratives, voice flattened,
every texture removed, reads as machine-made too. **Cut the slop, keep the human.** Preserve
idiosyncrasy, deliberate rhythm, contractions, the occasional long winding sentence, the writer's
actual voice. If removing a "tell" would also remove personality and the tell isn't dense, leave it.
The goal is to remove the signature *density* of machine text, not to launder prose into one safe
register.

## Process

**rewrite:** read and infer register → diagnose (the grep-able tells first, then the judgment calls:
rhythm, abstraction, voice) → treat top-down (structure, then paragraph, then sentence, then word)
→ preserve meaning, facts, and voice → self-check against over-correction → return only the prose.

**review:** read and infer register → diagnose → emit located findings, each as `"span" — [tell or
pathology] · principle (Author). Fix: ...` → lead with what works, order by impact → show the
targeted fix per finding, not a wholesale rewrite.

**Verify (high-stakes or long pieces only):** do a fresh-eyes pass as if you'd never seen it. Did
the rewrite introduce new tells (swapping one for another is common)? Did meaning and voice survive?
Does it still read like a person wrote it? For a long document this is where a separate
detector-and-verifier workflow earns its cost; most edits don't need it.
