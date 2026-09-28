# Style: what the finished video looks and sounds like

These came from the learner's reactions to eleven lessons. Each rule has its reason; keep the reason when you bend the rule.

## Dry and diagram-led

The learner compared an early attempt at a "cinematic" style with the best explainer channels and found it nowhere close, and asked for something drier. So: one clear diagram that builds up across the whole video, plainly drawn, and narration that explains while the picture shows. No flourishes, no title cards between chapters, no music.

- **One picture, fixed geography.** Decide the diagram's layout (what sits left, top, right) in the first chapter it appears and never move it; the viewer learns where to look. Each chapter adds to it or zooms into a part of it. When a chapter needs a different picture (a timeline, a chart), it sits in the free space below or beside the diagram, or the diagram shrinks to a corner and comes back.
- **One meaning per colour.** Amber for cost or a number to watch, ice blue for the thing being explained or the current selection, coral for failure, grey for idle. A colour used for two things in one video was the most common frame-review finding; between chapters 6 and 8 of one lesson, two colours swapped roles.
- **Objects move rather than cut.** Transform the thing on screen into the next state where the viewer should see what stays the same; fade through the background only between chapters that start a new picture.

## Text on screen

- **Labels, not captions.** On-screen text names things and shows real numbers. It never repeats a sentence the narration is saying; a sentence-length caption is the sign of a picture that isn't doing its job.
- **Terms get labelled when introduced,** at the place in the diagram they refer to, and a glossary card can close the lesson.
- **Real quotes are short.** A quoted line of model output or documentation earns its place only when the narration discusses it; a wall of quoted text is skipped.
- **Legible at 1080p:** axis labels and small annotations at 18 px or more, with contrast of at least 4.5:1. Frame reviews flagged 14 px grey-on-black axis labels as unreadable.
- **Nothing floats inside a plot area.** Status text over a time axis reads as an event at that time. Put it below the axis or beside the chart.

## Narration

- **Written for the ear:** short clauses, one new number per sentence, parameter names spoken as words, formulas described rather than read.
- **Evergreen.** The narration never refers to how the lesson was made: no "we ran", "our simulation", no tool or CLI names from the sims. Present evidence as what it is ("a small open model", "a public test collection of medical abstracts"); provenance lives in the Evidence table. A learner noticed the lesson referring to the session that built it and asked for it gone.
- **Concrete before abstract, and the wrong intuition shown failing** rather than argued against. A general claim follows the concrete case that demonstrated it, and it is scoped to what was shown: "in a task group, when one fails…" not "in structured concurrency, when one fails…" (an expert caught that overgeneralisation).
- **Say what is skipped**, once, in one sentence, rather than letting the viewer wonder.

## Voice

Kokoro `af_heart` at speed 1.0 in **paragraph mode**: each paragraph is one synthesis call, so intonation carries across sentences and pauses follow the punctuation. Per-sentence synthesis made every sentence start at the same pitch after the same 0.45 s gap, which the learner heard as robotic; paragraph mode doubled the sentence-to-sentence pitch variation at no cost. A more expressive open model (Kyutai Pocket TTS) was tried and the learner preferred Kokoro.

**ElevenLabs** is the hosted option (`"engine": "elevenlabs"` in narration.json). Use `eleven_multilingual_v2`: `eleven_v3` is more expressive but returns no timestamps, and the scenes cue off sentence timings. Develop with Kokoro (free, deterministic) and switch at the end, once the script is locked and the scenes are right: the scenes follow the new timings, but a faster voice can shorten a sentence below the animation written for it, so re-check the contact sheets after the switch. A lesson is about 5,000–7,000 characters, about one credit each.

Holds (`narration.json`) give the picture time after a reveal; the voice's own pauses do the rest.

## Length

Aim for what the argument needs after the deletion test; the learner's lessons run 4½ to 8 minutes, and the two longest (10–11 minutes) were the two they liked least. When a narrative answers two questions, it is two lessons.
