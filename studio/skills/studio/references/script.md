# Write the narration

Read this before writing narration and again before revising it. The narration is a person
talking to one curious viewer who is watching by choice and will leave when it drags. The test
is whether the viewer wants the next sentence, all the way through; clarity is the floor. They should finish feeling they worked something out with a smart friend, able to
explain it to someone else, and remembering at least one line.

Judge every script by reading it aloud yourself. A flat synthetic voice hides good writing and
bad writing alike, so the synthesized take settles timing, never quality.

## What went wrong, measured

In October 2026 we measured our eleven most recent scripts against the human-made captions of 26
popular explainers (about 95,000 words; 400 million views between them): 3Blue1Brown,
Veritasium, Sebastian Lague, Kurzgesagt, Vsauce, Primer, Steve Mould, Tom Scott, Branch Education,
Ben Eater, Computerphile, minutephysics, Kit Langton, Mark Rober and Secret Base. Rates are per
thousand words.

| Measure | Our scripts (median) | Corpus (median) | Corpus range |
|---|---|---|---|
| Contractions | 0 | 23 | 8 to 56, never absent |
| "I" | 0 | 12 | 0 (Branch Education only) to 54 |
| "you" | 0 | 16 | 0.4 to 93 |
| "we" | 11 | 14 | 5 to 64 |
| Sentences that are questions | 1% | 4% | 0 to 27% |
| Mean sentence length, words | 14 | 19 | 6 to 31 |
| Spread of sentence length, words | 5 | 12 | 4 to 17, after one caption artefact |

"We" was never our gap: we already said it as often as they do. The gap is everything that makes
a voice sound like a person: contractions, "I", "you", real questions, and sentences that run on
and then stop short. Ten of our eleven scripts contained no contraction at all, and the user's
verdict, beside the Mollick AI-origins film, was "too sterile". Caption punctuation is a
transcriber's choice, so treat sentence lengths as rough. These numbers are diagnostics, not
quotas; a script can hit all of them and still be dull.

## Principles

**Talk to one person** (Sebastian Lague, Grant Sanderson). Popular explainers take one of three
stances and hold it. The builder works it out beside you, in "we" and "I" (Lague, Ben Eater,
Primer, Kit Langton). The guide talks to you about your own intuitions, in "you" and "I"
(3Blue1Brown, Veritasium, Kurzgesagt). The documentary narrator stands back and says neither
(Branch Education), and even it uses contractions. Our default is the guide who also builds:
"we" when we really are working something out together ("if we number every byte, we can notice
a gap"), "you" for the viewer's experience and predictions ("you'd wait for the missing page"),
and "I" for honest wonder, opinion or admission ("that sounds like a step backwards, and I'll
admit it did to me"). Contract wherever a person would: "it's", "don't", "that's". "As we all know" is the
patronising version of "we"; never use it.

**Open a question and keep one open** (Sanderson, Andrew Stanton). Within about ten seconds the
viewer should have a concrete thing in front of them and a question they now want answered.
Never open with "In this video". When we close a question, open the next one in the same breath.
The viewer stays for an open question; a stated topic gives them nothing to wait for. Openings
that work in the corpus:

- Put the object in front of them and make it strange: 3Blue1Brown opens on a badly drawn digit
  that your brain reads instantly and a program can't.
- Make a scale felt: Branch Education fits a year of photos inside a dot of ink.
- Unpack a phrase everyone says without thinking: Tom Scott takes "tide goes in, tide goes out"
  and shows how much force "just some water" hides.
- Give the obvious answer, then take it away: minutephysics asks why the night sky is dark, lets
  "the sun isn't up" stand, then removes it.
- Ask for a commitment: Veritasium poses a circuit with a light-second of wire, lists the
  answers, and asks you to pick one before he explains.

**Give 2 + 2, not 4** (Stanton). Lay out the pieces and let the viewer add them up half a second
before we do. After a real question, `[predict 2]` gives them time to try. Answering what the
viewer has already guessed feels like a reward; explaining what they could have guessed feels
like a lecture.

**People and things before abstractions** (Richard Feynman, the Mollick film). A history is
people who wanted something: Thompson wanted to play a game on a spare computer. Give a person
one vivid, true detail rather than a list of credentials. Use one specific example before the
general rule. Use human-scale comparisons ("too big for one card") over specifications ("three gigabytes
each"). Abstract nouns such as "selective reinvention" or "a change of viewpoint" are
summaries of a story we didn't tell. Tell the story.

**Chain cause to cause** (Ira Glass, the Mollick film). Something happens, then we say what it
means, then something else happens because of it. End a sentence on the thing the next one picks
up: "Nothing gets delivered past a gap. And a gap is exactly what a lost packet leaves." Join
with "but", "so", "which means", "then", "because". "Meanwhile", "Furthermore" and "Additionally"
are the joints of an essay.

**Write for the ear** (Glass, Jad Abumrad). Vary sentence length: mostly medium, an occasional
long one that builds, and a short one that lands. Spoken explainers average nearly twenty words a
sentence, carried along by "so", "but" and "which means"; ours averaged fourteen, every one about
the same, and sounded like a list. Put the word that matters last, where a voice
naturally stresses it. Spell numbers the way they're said. Avoid parentheses and semicolons; a
listener can't see them, and the voice reads them as a stumble. Say a year only when the date is
the point. Otherwise say "seven years later" and let the screen carry the date. A fragment is
fine for punch, now and then.

**Beat the misconception** (Derek Muller). Muller found that clear explanations make viewers feel
they learned without changing what they believe. For each core idea, say the plausible wrong
intuition out loud, let it stand for a moment, then break it on screen. The strongest version is
a confession: Muller retells the analogy he used to teach, calls it a great story, then says it's
wrong. Lague tells us what he always assumed before showing why it fails. A narrator who was
fooled too gives the viewer permission to have been fooled. The best place for it is
where a sharp viewer would interrupt: say the interruption for them ("So why not just fix
TCP?") and answer it.

**Point; let the picture show** (Walter Murch, Sanderson). Never describe what the viewer can see
or narrate the camera ("Now pull back", "Follow the streams", "Watch the calls become
processes"). Say what to notice, why it matters, or nothing at all. "Look at the font bytes.
They're already here." directs attention; "Watch the font bytes arrive" describes it.

**Say it once, plainly; caveats live in the Evidence table** (Steven Pinker's classic style).
Source attributions ("the team's history records", "his release account describes"), scope
disclaimers ("this is not a claim that") and defensive pairs ("this relocates coordination; it
does not abolish it") belong in `## Evidence`, where they protect accuracy without costing
attention. In the narration, keep a limit only when the viewer would otherwise believe something
false, and state it as a fact about the world: "It can't conjure a signal in a tunnel." One per
idea at most.

**End on the opening, changed** (Stanton). The last paragraph returns to the first image or
question, and it means something new now. Don't announce a lesson ("The lesson is visible:");
let the callback carry it, then breathe.

## The moments a viewer remembers

Design every script around two to four of these, and name them in the beat table.

1. **The cold open.** A concrete thing on screen, one sentence that makes it strange, and an
   open question within about ten seconds.
2. **The turn.** We have followed the plausible intuition together. The voice stops, the picture
   shows why it fails, and the next sentence is short and lands on the word that matters, timed
   to the performed event.
3. **The callback.** The final lines return to the opening and the viewer feels it click. Reusing
   a phrase from the opening ("nothing gets past a gap") is a good way to make it audible.
4. **One honest human line.** Wit that comes from noticing something true, wonder, or a plain
   admission that nobody quite knows.

## Delightful or tacky

Delight comes from the material: a real surprise, a true irony, a detail too good to invent.
Tacky is engagement bolted on afterwards. If a line would fit any video, it's tacky; if it only
works in this one, it's earned. Cut on sight:

- YouTube tics: "Let's dive in", "But here's the thing", "But that's not the whole story",
  "buckle up", fake cliffhangers, an exclamation standing in for an idea.
- LLM tics: "X, not Y" corrective pairs, "not merely", "it's worth noting", triplets for rhythm,
  "a testament to", "plays a crucial role", announced importance ("Here is the distinction that
  will matter later"), and a rhetorical question in every paragraph. `/prose:prose` lists more;
  use its review mode on a draft.
- Lecture tics: definitions before need, "rather than" on every other line, recitations of dates,
  versions and credits, and summaries of what was just shown.

## Before and after, from our own scripts

> Their network used two GTX five eighty cards, each with three gigabytes of memory. The network
> was split across them because one card could not hold it.

> Their network was too big for one graphics card. So they cut it in half and ran it on two
> gaming cards, side by side.

The spec sheet becomes a problem and a fix. "Gaming cards" carries the story's irony; the model
number stays on screen.

> This is a documented crossing between worlds, not a claim that Akka secretly runs Erlang. Ideas
> travel; their implementation, defaults, and surrounding ecosystem can change.

> Jonas Bonér admired the way Erlang survives its own crashes, and he wanted that on the Java
> virtual machine. So he built it there. That's Akka.

A person with a want replaces a disclaimer. The scope note moves to the Evidence table.

> Here is the distinction that will matter later: Erlang is a language; BEAM is the runtime on
> which its processes execute; OTP supplies reusable structures for building systems.

> Three names come up again and again here. Erlang is the language you write. BEAM is the
> machine that runs it. And OTP is the toolkit that keeps it running when things break.

The announcement goes, the semicolons become sentences, and "you" puts the viewer in the chair.

> Now pull back, and follow another thread further into the past.

> But Ericsson wasn't the first to think of programs as crowds of independent workers.

Camera narration becomes a reason to travel. The picture does the pulling back.

> Back at the browser, the lesson is visible: a promise that served one workload became a
> constraint for another.

> That promise was never a mistake. It was made for one long conversation, and the web turned
> out to be dozens of short ones, all at once.

The announced moral becomes a callback to the opening's "dozens of things at once" and to the
letter the viewer imagined earlier.

[script-example.md](script-example.md) is a whole film rewritten this way, with notes on each
change. Read it when you're unsure what the target sounds like, but write fresh sentences: copying
its phrasing into another subject makes every film sound the same.

## Revise by ear

George Saunders's method: read the script aloud from the top, in one sitting, at speaking pace.
Mark every place your attention drifted, you stumbled, or you didn't want the next sentence. Fix
only those places, then read again from the top. Two or three passes usually reach a script that
holds. Afterwards, check:

- Read cold, does any sentence trip the tongue or need a second reading?
- After the first fifteen seconds, can you say what question the film is asking?
- Does each core idea name the wrong intuition before breaking it?
- Is any line describing what's on screen, narrating the camera, or defending a claim?
- Does the ending answer the opening?
- Is there one line you'd repeat to a friend? If not, the script is correct but forgettable.
