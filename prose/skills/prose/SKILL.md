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
that is `review`. When drafting from scratch, apply the principles silently as you write. When you
revise existing prose and the edit is more than trivial, also write a **revision artifact** (see
below) and end with one line giving its path — the only commentary `rewrite` permits.

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
removing slop. Keep explanation quarantined in `review` and in the revision artifact. The single
permitted line in `rewrite` is the artifact's path; the reasoning lives inside the file, never in the
prose or around it.

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

## The revision artifact

`rewrite` returns clean prose, which gives the writer nothing to inspect. So when the edit is more
than trivial, also write a self-contained HTML diff to `/tmp` and tell the user its path. This is the
only thing `rewrite` ships besides the prose. The artifact is where the reasoning lives, so the
response itself stays silent — explanation quarantined, contract intact. Skip it for a one-line touch-up
where there is nothing to show.

Unlike `review`, the artifact does not teach in prose; it lets the reader *see* the change and, on
hover, read the one reason behind it. Keep each reason short and **name the tell or the principle** in
our own vocabulary, so the diff carries the pedagogy `review` would: `"copula avoidance → 'is'
(Steere)"`, `"nominalization, find the actor (Williams)"`, `"clutter, every word earns its place
(Zinsser)"`. That naming is what makes ours more than a generic diff.

Build a sentence-level change list grouped by paragraph. Each entry is one of:

- **keep** — unchanged. Fields: `type: "keep"`, `text`.
- **edit** — rewritten. Fields: `type: "edit"`, `old`, `new`, `why`.
- **del** — cut (a pure tell or pure clutter; never a proposition). Fields: `type: "del"`, `old`, `why`.

```json
[
  { "para": 1, "items": [
    { "type": "edit", "old": "...", "new": "...", "why": "copula avoidance → 'is' (Steere)" },
    { "type": "del",  "old": "...", "why": "metadiscourse, the argument is stronger without it (Zinsser)" }
  ]},
  { "para": 2, "items": [ { "type": "keep", "text": "..." } ] }
]
```

Take `assets/revision_template.html` (alongside this skill), replace the exact line
`const DATA = __DATA__;` with `const DATA = <json>;`, and save to a new file like
`/tmp/prose-revision-<short-name>.html`. Do not write into the skill folder, and confirm no `__DATA__`
remains. The file opens to three tabs — Original, Rewrite, Diff — with cuts in red, rewrites in green,
and the reason on hover. Because the `rewrite` view is reconstructed from the entries, every
proposition in the original must survive into an `edit` or `keep`; only true filler becomes a `del`.
This is the same style-only invariant, made checkable.

## Depth: inline or a workflow

Gate every request. Most prose is short and low-stakes; handle it **inline** in one pass. Fire a
**dynamic workflow** when the piece is long (a full document or essay), high-stakes (being published,
or something the writer clearly cares about), or when the user asks for it (`/prose deep ...`).

The reason is not size, it's bias. A single context that rewrites and then judges its own rewrite
carries self-preferential bias: the same model that produced the prose cannot reliably tell whether
it still reads like AI, because its own output sits at the mode of "fine." The workflow breaks this
by handing diagnosis and verification to separate agents that never see each other's reasoning. That
separation is the whole point; an inline pass cannot give you it.

## Inline process

**rewrite:** read and infer register → diagnose (grep-able tells first, then the judgment calls:
rhythm, abstraction, voice) → treat top-down (structure, then paragraph, then sentence, then word) →
preserve meaning, facts, and voice → self-check against over-correction → return the prose, and for a
non-trivial edit also write the revision artifact and give its path.

**review:** read and infer register → diagnose → emit located findings, each as `"span" — [tell or
pathology] · principle (Author). Fix: ...` → lead with what works, order by impact → show the
targeted fix per finding, not a wholesale rewrite.

## The deep path (dynamic workflow)

When the gate calls for it, construct and fire a workflow. The graph is a **diamond → loop**
compound (fan-out diagnose, converge at a plan barrier, then a verify loop). The verifier is
**soft**: a rubric plus a panel of fresh agents (signal-hierarchy rung 3), driven against the prose
reference — style is only softly verifiable, so it is never faked as a pass/fail boolean. Shape:

1. **Diagnose (fan-out, separate contexts).** One critic agent per lens — AI-tells, concreteness,
   cadence, coherence, voice/register, cutting, honesty, plus a technical-explanation lens for
   technical writing — each reading the whole text and returning *located* findings (span, problem,
   principle, severity, fix) across word / sentence / paragraph / document granularity. Separate
   contexts so the lenses don't contaminate one another.
2. **Adversarial smell-test.** A dedicated agent reading as a skeptical human: does this sound
   AI-written? Find every tell, including ones no checklist names. Plus a refuter that challenges
   weak or over-zealous findings, so the pass doesn't over-correct.
3. **Plan (barrier).** Synthesize all findings: dedupe, resolve conflicts (cadence wants to split a
   sentence, cohesion wants it joined — adjudicate), order edits top-down, honor the register and the
   over-correction guard. Output a concrete edit plan.
4. **Branch by mode.**
   - **review:** return the synthesized, located critique as the teaching output. Stop here.
   - **rewrite:** apply the plan, then **verify with fresh agents that never saw the original** —
     (a) tells removed without new ones introduced (swapping one tell for another is common),
     (b) meaning, facts, and argument intact (style only), (c) voice preserved, not flattened,
     (d) it reads as a human wrote it (a fresh smell-test). Loop with a **divergence guard**: if
     revising re-introduces a tell while fixing another, or flattens voice, that is oscillation —
     compare consecutive drafts, cap the rounds, and **on cap return BLOCKED** ("can't satisfy
     tells-removed and voice-preserved at once; here are the two candidate edits") rather than
     shipping a flattened over-corrected draft. Stop when two consecutive passes are clean. Return
     the prose, and write the revision artifact (the verified change list maps directly onto its
     keep/edit/del entries) with its path.

The fresh-eyes verification in step 4 is the structural answer to self-preferential bias. If the
`orchestrate` skill is installed you can hand it this shape; otherwise fire it directly.
