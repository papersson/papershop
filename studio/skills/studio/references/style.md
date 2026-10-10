# Style: what a finished explainer looks and sounds like

These came from a learner's reactions to fourteen videos and two work projects, and from what
people found when they studied what made generated motion design look cheap. Each rule has its
reason; keep the reason when you bend the rule.

## Dry, with an identity

The learner compared a "cinematic" attempt with the best explainer channels, found it nowhere
close, and asked for something drier: diagrams, labels, narration that explains while the picture
shows. No title cards between chapters, no music, no flourishes. Dry means no decoration; it does
not mean no identity. The biggest single improvement in the work projects was giving the thing the
video follows a visual identity:

- **A protagonist.** Give the thing the video follows (a request, a record, a payment) a token with
  a glyph that changes with its state, and keep it on screen. A proposed change can be a
  translucent "ghost" of it.
- **Real imagery beats illustration**: a screenshot, a real capture, a real location as a
  full-bleed background. Treat it as evidence: record its source and capture parameters.

This is the plain tone, and "fun" or "engaging" asks for it done well. A comic video (video.json
`tone: comic`, only on request) adds gags, acting and layered sound on top of these rules:
`styles/comic.md`.

## Map and close-ups

The older rule, one diagram that builds up across the video with details beside it, produced
clutter: by minute eight one frame held a category list, a table, a record's fields and buttons.
"The macro view needs to be super clean."

- **The map** is the system overview: component names only, plus state (which box or arrow is lit,
  where the token is). The test: any text on the map that isn't a component name is a bug.
- The map's layout is fixed, but the frame isn't: the camera frames the boxes that exist so far
  and stays centred as boxes appear, so early chapters aren't top-heavy. When the layout has a
  header strip (a chapter label, a title), framing keeps it clear the way it keeps the band clear.
- **The camera moves on keys.** A push-in, a pull back, a pan or a move to frame a group is one
  declaration (`camAt` in live, `<Camera keys>` in Remotion; `engines.md`), so it renders at any
  frame. The element the narration names stays in frame while it is named (`studio check` warns).
  The default minimap highlight is ice; a close-up's `accent` changes it only where the video gives
  the explained thing another colour.
- **A close-up** is one component or one record, full screen, opened from its box: the box lights
  just before the zoom (anticipation). A corner minimap has no labels and fills only the source
  box. The header is the item's name only: no breadcrumb, no subtitle.
- Zooming back out returns to the same map with one state change. Nothing from the close-up stays.
- Hypothetical content is marked by the narration ("suppose", "if the reviewer approves"), not by
  tags or dashed outlines, which were tried and removed as clutter. A value on screen that is
  neither real nor framed as supposed is removed, not labelled.

## Colour

One meaning per colour for the whole video: amber for cost or a number to watch, ice blue for the
thing being explained or the current selection, coral for failure, grey for idle. A colour used for
two things was the most common frame-review finding; in one video two colours swapped roles
between chapters.

## Line weight

Outer contours are heavier than inner detail: a box's outline is heavier than the dividers between
its fields, a table's outline heavier than its cell lines, a close-up's panel heavier than its
minimap. Equal weights flatten a diagram into a grid, and the eye can no longer find where one
thing ends. The kit's components follow it (live boxes 3 over 1.5 dividers; Remotion close-up 2 px
over a 1 px minimap as rendered, a table 3 px over single 1 px dividers); a lit or selected element may be heavier still,
since that weight is state, not structure. The look sheet shows it.

## The look sheet

The model sheet (`studio look-sheet`, `engines.md`) is drawn at the look stage, before scenes: every
element in each of its states, in the video's theme and layout. Scenes draw what is on it; a new
element or state goes on the sheet first. The motion review checks drawings are on sheet.

## Motion

- Motion preserves the actual mechanism. A copy creates another record; it does not move a road
  to a new geographic location. When place/record or value/reference are different views, show
  both and link them. Transform only when identity really persists; cut/fade when that is clearer.
  Inspect transition frames, not just endpoints, for a false implication.
- Springs with at most a tiny overshoot on UI-like things, none on type. A value that changes
  target several times sums one spring per change.
- Every animation finishes by the word it illustrates. Camera moves and content changes are staged,
  not simultaneous.
- **Hold after a move.** After a significant move, hold at least 0.5 s before the next one starts:
  the eye needs that long to land on the result before something else pulls it away. Moves that
  overlap or follow each other within a beat read as one move (a stagger), and a hold may carry
  ambient motion (a ticking counter, a drifting dot). `studio check` measures it on the rendered
  stage and warns at each shorter hold.
- **Time picture and sound from one event.** Name each contact (a landing, a strike, a count
  changing) in `cues.json`, anchored to the word it belongs to, and have the scene's `cue(name)` and
  the effect both use it: in one build every sound landed within a frame of its picture this way.
  Each event gets its own still, two frames after the contact, where its result should show.
- **Secondary motion when something has weight or hangs on something.** A tag on a box, a cable,
  a label on a moving token follows through (`follow`); a heavy thing landing settles (`settle`);
  a held picture that should feel alive drifts (`wobble`, a few pixels). Leave it off type, data and
  anything the viewer must read while it moves, and off the map at rest: secondary motion is for
  the protagonist and the moment of contact, not decoration.

## Text on screen

- **Labels, not captions.** On-screen text names things and shows real numbers. It never repeats a
  sentence the narration is saying.
- **Captions are a layout primitive.** They are burned in, in a reserved band at the bottom (160 px
  at 1080p, opaque by default), and nothing else enters it. The band is a subtitle layer, so "no
  text repeating the narration" applies to the stage, not the band. Chunks: at most two lines of
  about 42 characters, broken at phrase boundaries, held at least 1.2 s; the kit does this.
- **Legible at phone width:** labels at least 18 px at 1080p (earlier builds used 26 px), contrast
  at least 4.5:1, and lines that carry meaning (a map's arrows, idle or not) at least 3:1. Frame
  reviews flagged 14 px grey-on-black as unreadable. A long code line shrinks to fit its panel,
  down to 18 px; past that, break the line or widen the panel.
- **Nothing floats inside a plot area.** Status text over a time axis reads as an event at that time.
- **Real quotes are short**, and only when the narration discusses them.

## Banned defaults

These are the tells of generated design (from a study of 26 of them, and of what made "one prompt"
videos look alike). The craft critique hunts for them:

- labels on nearly every object, arrow and section; descriptions that repeat the heading;
  captions that explain an obvious illustration;
- decorative icons beside every point, or an icon in a coloured rounded square atop every card;
- pills for everything; rounded cards inside rounded cards; coloured strips along box edges;
- purple gradients, glows, frosted glass over blur (a frosted caption band is allowed only over
  full-bleed imagery), a different background effect per section;
- oversized headings over tiny grey descriptions; widely spaced uppercase everywhere (keep it to
  one small chapter label); short labels separated by dots; a decorative dash before labels;
- every element entering with the same fade-and-slide; continuously moving background particles;
  thin lines with glowing dots travelling between boxes (the protagonist token moves only when the
  story says so, and it is the subject, not decoration);
- centred text on a gradient; corner labels and frame borders; blinking "live" dots; a centred
  headline over three equal cards.

## Narration

- **Written for the ear:** short clauses, one new number per sentence, parameter names as words.
- **Evergreen.** The narration does not refer to production decisions, briefs or sessions. Code/tool
  names that are the subject of the explanation are legitimate; names from production-only sims are not. Provenance lives in the Evidence table.
- **Concrete before abstract, and the wrong intuition shown failing.** A general claim is scoped to
  what was shown ("in a task group, when one fails…", not "in structured concurrency…").
- **Say what is skipped**, once, in one sentence.

## Voice

Kokoro `af_heart` in paragraph mode: intonation carries across a paragraph and pauses follow the
punctuation. One sentence per call made every sentence start at the same pitch after the same gap,
which the learner heard as robotic. Kokoro is the voice from the first narration to the finished
video. ElevenLabs (`eleven_multilingual_v2`, or `eleven_v4`) is the hosted option when the user asks
for it, chosen before scenes are timed, since a new voice moves every word; `eleven_v3` returns no
timestamps, which the scenes cue from.

Names and terms are said right. A learner heard "uh reads one" for "A reads one", and "id" said as
the Freudian id: a lone capital letter is read as the article, a lowercase abbreviation as a word.
The pronunciation lint lists these before any audio exists, and every finding gets a fix or a
decision (explainer.md, Stage 6).

The finish is `studio audio` (run by `publish` and `export`), on the whole mix (narration, effects,
music): 48 kHz via soxr, one fixed gain to -16 LUFS measured over the whole mix, and a limiter that
touches only the peaks over the -1.5 dBTP ceiling (fixed gain alone pushed the raw voice to about
+6.5 dBTP on a few samples; an effect over the voice goes further). It is not room tone and
not one-pass `loudnorm`: that filter is dynamic, so it raised the room tone and breaths in every
pause, and the learner heard "a constant background noise" (an A/B of delivered, raw and clean
audio settled it at once). Social destinations use -14 LUFS.

## Sound

The voice carries an explainer; sound is optional and serves it. Effects and music are off by
default, and "no music" stays the plain default.

- **Effects belong in pauses.** A loud effect decays before the next word; a quiet one under speech
  stays below -24 dBFS at the master's level. `studio check` fails on a louder one under a spoken
  word, so `publish` stops on it: the finish limits peaks, it does not unmask a word.
- **One sound per kind of event, chosen by listening.** The types (`studio sfx` and the docstrings in
  `sfx.py`): click, soft-tick, tap, key-tick and counter-tick for steps and typing; pop, pop-small,
  pop-large and shimmer for things appearing; confirm and error for a result; snap, card-flip, drop,
  thump and low-hit for things landing or set down; whoosh, slide-in, slide-out and paper-slide for
  moves; chime for a milestone; glitch for something wrong; riser and swell for a build. The sound
  kit adds question, page-turn, stack, dice and toggle.
- **Recordings first, synths as the fallback.** Synthesised beeps were the weak point of agent-made
  soundtracks. The sound kit holds about 150 curated CC0 recordings (Kenney's packs), each with a
  type; a cue plays one with `"sound": "kit"` (its type's default) or `"kit:ID"` (one the lab
  offered). A recording lands on its cue at its transient peak, not its first sample, since a
  recording has a lead-in; the peak was measured once and sits in `soundkit.json`. `studio sfx`
  copies each one into `assets/sounds/` with its provenance, and the page credits the packs. A cue
  with a type and no `sound` keeps the synth voice of that name (a synth build, riser or swell,
  ends on its cue, every other voice starts on it), so recordings are opt-in cue by cue. `studio
  sound-lab` plays each type's synth candidates and kit recordings alone and in a pause of the
  narration; the kit was curated by measurement, so listen before choosing.
- **Time picture and sound from one event** (Motion, above): an effect names the cue the scene's
  move uses, and `studio audio-check` reports each one's offset from its frame (a warning past one).
- **One room, a clear voice.** The mix puts effects and music in one small shared room (a few early
  reflections), dips their 1-4 kHz band about 3 dB while the narration speaks, and ducks music 8 to
  9 dB under speech; the narration stays dry. video.json `sound` turns each off (`room` also scales
  the room, 0 to 2). A narration alone is mixed exactly as before.
- **A bed only when asked.** `studio music VIDEO --bed [--key Am] [--bpm 72]` generates a quiet pad of
  slow chords on a soft pulse, registers it as a music track 20 LU under the voice (so it ducks), and
  writes its beat grid, so `beat_N` and `downbeat_N` cues land on it. No melody: a motif per
  character belongs to a comic video, made by hand.
- **The kit measures; the user listens once.** `studio audio-check` measures sync, ducking, masking
  of each word in 1-4 kHz, the pauses guard and loudness on stems the kit renders itself. It cannot
  judge taste, so with effects or music the user listens once to the finished mix before publishing
  (`publishing.md`).

## Length

Choose it from the learning brief and the deletion test in `pedagogy.md`. Give longer arcs local
closure. Keep optional reference separate from the main story; engagement alone is not learning.
