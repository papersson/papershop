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

## Map and close-ups

The older rule, one diagram that builds up across the video with details beside it, produced
clutter: by minute eight one frame held a category list, a table, a record's fields and buttons.
"The macro view needs to be super clean."

- **The map** is the system overview: component names only, plus state (which box or arrow is lit,
  where the token is). The test: any text on the map that isn't a component name is a bug.
- The map's layout is fixed, but the frame isn't: the camera frames the boxes that exist so far
  and stays centred as boxes appear, so early chapters aren't top-heavy.
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

## Motion

- Motion preserves the actual mechanism. A copy creates another record; it does not move a road
  to a new geographic location. When place/record or value/reference are different views, show
  both and link them. Transform only when identity really persists; cut/fade when that is clearer.
  Inspect transition frames, not just endpoints, for a false implication.
- Springs with at most a tiny overshoot on UI-like things, none on type. A value that changes
  target several times sums one spring per change.
- Every animation finishes by the word it illustrates. Camera moves and content changes are staged,
  not simultaneous.

## Text on screen

- **Labels, not captions.** On-screen text names things and shows real numbers. It never repeats a
  sentence the narration is saying.
- **Captions are a layout primitive.** They are burned in, in a reserved band at the bottom (160 px
  at 1080p, opaque by default), and nothing else enters it. The band is a subtitle layer, so "no
  text repeating the narration" applies to the stage, not the band. Chunks: at most two lines of
  about 42 characters, broken at phrase boundaries, held at least 1.2 s; the kit does this.
- **Legible at phone width:** labels at least 18 px at 1080p (earlier builds used 26 px), contrast
  at least 4.5:1. Frame reviews flagged 14 px grey-on-black as unreadable.
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

The finish is `studio audio` (run by `publish`): 48 kHz via soxr, one fixed gain to -16 LUFS
measured over the whole file, and a limiter that touches only the peaks over the -1.5 dBTP ceiling
(fixed gain alone pushed the raw voice to about +6.5 dBTP on a few samples). It is not room tone and
not one-pass `loudnorm`: that filter is dynamic, so it raised the room tone and breaths in every
pause, and the learner heard "a constant background noise" (an A/B of delivered, raw and clean
audio settled it at once). Social destinations use -14 LUFS. Sound effects are off by default,
placed in pauses, and chosen with `studio sound-lab`.

## Length

Choose it from the learning brief and the deletion test in `pedagogy.md`. Give longer arcs local
closure. Keep optional reference separate from the main story; engagement alone is not learning.
