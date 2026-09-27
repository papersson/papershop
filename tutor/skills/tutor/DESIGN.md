# Why tutor is shaped this way

This plugin packages a pipeline that built eleven lessons over two days with one learner. Every rule in it traces to something that went wrong, or to a choice the learner made. This file records those, so a future change knows what it is trading away.

## The narrative stage exists because narrative quality was the bottleneck

Across eleven lessons, the learner's reactions were almost entirely about the argument: the wrong story, too much history, a chapter that did not earn its place, an opening that showed a result but not a question. The animation, evidence and voice were rarely the complaint. Iterating a narrative costs minutes; iterating a finished video costs hours. So the narrative is settled first, in the open.

Two tracks, because the learner's expertise changes who can judge it. When they know the topic, they are the best reviewer and iteration is cheap. When they don't, they can only judge whether it is what they want to learn, so correctness has to be established by fresh-context reviewers before they see it, and they get the risk flags rather than a false sense of a finished product.

## Fresh contexts everywhere a judgment is made

A context that holds a draft anchors every later judgment to it. The pipeline therefore isolates: research (two passes, neutral prompt), competing narratives (each drafted alone), script reviews (three roles, each seeing only its material), the frame review (given frames, script and evidence, nothing else). `review.py` runs each reviewer in an empty temporary folder because, in one build, reviewers with file access read earlier rounds' reviews and repeated them.

The build itself runs as a background agent for the same reason: the conversation that shaped the narrative is exactly what the reviewers must not see.

## Real evidence, and the frame review

Every number on screen comes from a run. This was the series' rule from the start, and it held. What it did not catch was the screen itself: a code card with `return` inside `except*` (a SyntaxError), and a narration line that said a plain `except` cannot catch an exception group (it can). Both survived seven passing script reviews and were caught by the first frame review, where a fresh reviewer got one frame per sentence plus the script and evidence. So the frame review is a gate, not an option. It also produces false alarms from downscaled sheets ("the panel is missing"), so findings are verified against the 1080p frame.

## Voice

Kokoro `af_heart` sounded robotic to the learner. Measurement showed why: synthesised sentence by sentence, every sentence started at the same pitch after the same 0.45 s gap. Synthesising a paragraph per call doubled the sentence-to-sentence pitch variation at no cost, and the voice's own pauses replaced the fixed gap. A more expressive open model (Kyutai Pocket TTS) was integrated with forced alignment and a retry loop, and the learner preferred Kokoro; the Pocket path was removed to keep one engine and one Python environment. Because nobody can listen, `voice_check.py` transcribes every sentence and scores it; that check is what caught a synthesis that silently dropped two sentences.

## The kit is copied, not referenced

`setup.sh` copies `kit/` into the project. A plugin update must never change how an old lesson renders: the day the narration engine grew a second mode, the old mode's timings were verified byte-identical before merging, and a copied kit makes that guarantee structural. Taking a newer kit is an explicit act (delete the copy, run setup again).

## Style is dry on purpose

The learner compared an attempt at a cinematic, discovery-order style with the best explainer channels and found it nowhere close, and asked for something drier: one diagram, labels, no captions. The eleven lessons' frame reviews then supplied the specifics: one meaning per colour, nothing floating in a plot area, 18 px minimum text, no sentence captions, evergreen narration. `style.md` keeps each rule with its reason.

## What is not here

- Pocket TTS and the forced aligner (removed; see Voice).
- A fullscreen/expand button on the page (the learner opens the page in a browser, where the player's own fullscreen works).
- Any 3Blue1Brown-style principles as requirements. They were tried once; the learner preferred the dry style.
