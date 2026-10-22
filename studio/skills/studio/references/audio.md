# Sound: effects, the mix and the listening check

The voice carries an explainer; sound serves it. Effects go on the events a viewer should feel
(`taste/delight.md`) and nowhere else; "no music" stays the plain default. This file is the
mechanics: placing effects, the mix and finish, what `studio audio-check` measures, and the one
listening the user does.

## Effects

- **Effects belong in pauses.** A loud effect decays before the next word; a quiet one under speech
  stays below -24 dBFS at the master's level. `studio check` fails on a louder one under a spoken
  word, so `publish` stops on it: the finish limits peaks, it does not unmask a word.
- **One sound per kind of event, chosen by listening.** The types (`studio sfx` and the docstrings in
  `sfx.py`): click, soft-tick, tap, key-tick and counter-tick for steps and typing; pop, pop-small,
  pop-large and shimmer for things appearing; confirm and error for a result; snap, card-flip, drop,
  thump and low-hit for things landing or set down; whoosh, slide-in, slide-out and paper-slide for
  moves; chime for a milestone; glitch for something wrong; riser and swell for a build. The sound
  kit adds question, page-turn, stack, dice and toggle.
- **Recordings when an effect matters, synths as the quick default.** Synthesised beeps were the
  weak point of agent-made soundtracks. The sound kit holds about 150 curated CC0 recordings
  (Kenney's packs), each with a type, fetched once with `studio doctor --fetch --sounds`; a cue plays
  one with `"sound": "kit"` (its type's default) or `"kit:ID"` (one the lab offered). A recording
  lands on its cue at its transient peak, not its first sample, since a recording has a lead-in; the
  peak was measured once and sits in `soundkit.json`. `studio sfx` copies each one into
  `assets/sounds/` with its provenance, and the page credits the packs. A cue with a type and no
  `sound` keeps the synth voice of that name (a synth build, riser or swell, ends on its cue, every
  other voice starts on it), so recordings are opt-in cue by cue. `studio sound-lab` plays each type's
  synth candidates and kit recordings alone and in a pause of the narration; listen before choosing.
- **Time picture and sound from one event** (`taste/delight.md`): an effect names the cue the
  scene's move uses, and `studio audio-check` reports each one's offset from its frame (a warning past
  one). Tag an effect with what the picture does on its frame: `cut`, `move` (at its fastest), `land`
  (motion ends), `appear` (motion starts). The beat sheet still sets the time; the tag is checked
  against the cut (a cut within 1 frame, a move's peak within 3, a landing or an appearance within
  2). A whoosh on a slide's first frame is off by half the slide: put it on the cue where the slide
  is fastest, or tag it `appear`.
- **Start every effect at gain 0.** Kit recordings are trimmed to the level of their synth voice, so
  gain 0 sits where the synth would, and the effects follow the narration's loudness, so a quiet or
  loud voice keeps them in place; adjust from there. audio-check warns an effect more than 13.5 dB
  over the voice's loudness (its loudest 10 ms against the voice's integrated loudness; the loudest
  default, thump, sits at +12).
- **A repeated sound varies.** A cue's `sound` may be a pool, a list of sounds: each cue plays one,
  never the one the cue before it with the same pool played, a little higher or lower and louder or
  softer (`"jitter": false` turns that off). Footsteps, keys and ticks are pools.
- **The video's own recordings play on cues too**: `"sound": "asset:sounds/door/latch.wav"`, a file
  under `assets/` added with `studio asset add VIDEO FILE --kind … --source … --name sounds/…`. It
  lands on its transient like a kit recording; `studio sfx` measures it when it keeps the cue. Put a
  sound in `audio/tracks.json` at fixed seconds only when nothing on screen times it (a room tone).
- **Many small events are one stream.** Typing is hundreds of keystrokes, too many for cues (each
  gets a still and a review window), so one effect carries them: `"events": [[seconds after the cue,
  kind], …]` and `"sounds"` per kind, where a kind's sound may be `"grains:kit:keys-typing-cherry-blue"`
  (key-sized grains of a take of real typing; `#low` for a space bar, `#high` for a backspace). Each
  event plays a different variant than the last, crowded events thin out, and events under a spoken
  word step back by `under_speech` dB (-6), so fast typing is a texture and the voice stays on top
  (`kit/src/studio_kit/streams.py`). `studio typing` writes these for typed code; a generator of
  your own (gait contacts, a counter) can too. Generated effects carry `"source"`, and `studio sfx`
  keeps them when it rewrites the rest.
- **A bed only when asked.** `studio music VIDEO --bed [--key Am] [--bpm 72]` generates a quiet pad of
  slow chords on a soft pulse, registers it as a music track 20 LU under the voice (so it ducks), and
  writes its beat grid, so `beat_N` and `downbeat_N` cues land on it. No melody: a motif per
  character belongs to a comic video, made by hand.

## The mix and the finish

The mix puts effects and music in one small shared room (a few early reflections), dips their
1-4 kHz band about 3 dB while the narration speaks, and ducks music 8 to 9 dB under speech; the
narration stays dry. video.json `sound` turns each off (`room` also scales the room, 0 to 2). A
narration alone is mixed exactly as before. The desk's live view plays this mix, as a cut does.

The finish is `studio audio` (run by `publish` and `export`), on the whole mix: 48 kHz via soxr, one
fixed gain to -16 LUFS measured over the whole mix, and a limiter that touches only the peaks over
the -1.5 dBTP ceiling (fixed gain alone pushed the raw voice to about +6.5 dBTP on a few samples; an
effect over the voice goes further). It is not one-pass `loudnorm`: that filter is dynamic, so it
raised the room tone and breaths in every pause, and the learner heard "a constant background
noise". Social destinations use -14 LUFS.

## Measured: studio audio-check

The kit cannot judge sound by ear, so it measures it. `studio audio-check VIDEO [--cut N]` writes
`out/audio-check.json` and a line a row, each ok or a warning, on stems the kit renders itself (each
role's sub-bus as it sits in the mix, at the master's level):

- **sync**: each effect on a named event (a cue name or anchor in `audio/sfx.json`), its onset
  against the event's frame (a kit recording's transient peak, since its file has a lead-in); a
  warning past one frame. With a rendered cut, a tagged effect is judged against the picture frame
  by frame, and an untagged one gets the nearest start or end of picture motion, or a cut, noted
  beside it.
- **audible**: each effect in a window around its contact. A warning when it lifts the narration
  and music there by under 6 dB, wideband and in its own band (masked), or when its loudest 10 ms
  is more than 30 dB under the voice's level (too quiet).
- **loud**: an effect's loudest 10 ms (K-weighted) more than 13.5 dB over the voice's integrated
  loudness. With no narration, loud and audible measure against the music; with neither, a row says
  they were not measured.
- **ducking**: the music under speech against the music in the pauses; a warning under 6 dB.
- **masking**: per spoken word, effects and music in 1-4 kHz against the narration there; a warning
  within 10 dB.
- **pauses** (fails): an effect over -24 dBFS during a spoken word, at the master's gain before its
  limiter; the row names the part of the word it covers and its peak there. `studio check` runs this
  guard whenever there are effects (`audio/sfx.json`, or a `tracks.json` entry with role `sfx`) and
  a narration, so publish's full-check gate stops on it. Both keep the target the mix was last
  finished to, so a check after `export --lufs -14` stays at -14.
- **loudness**: the master against its target and ceiling, and the web copy's true peak.

It also draws `out/audio-sheet.png` (waveform, spectrogram, sentence bands and a marker per effect,
red where a row flagged it) and close-ups of the featured effects (those on weight-3 events first,
then the tagged and the loudest) in
`out/audio-sheet/`, with the frame grid and the frame where the picture does what the tag says.
Look at them before asking for the listen. And it picks about five timecodes for that listen, each
with its reason: the tagged effect furthest from its picture, the closest masking margin, the
loudest effect, the music's entry, the featured effects.

## Heard once: the listening check

With effects or music, before publishing, ask the user to play the finished mix (the desk's latest
cut, `audio/final.wav` after `studio audio`, or `out/master.mp4` once a publish has made it) at the
timecodes audio-check printed, and record what they said: `studio review-status VIDEO listen passed
--reason "…" [--at 0:02.8,0:16.1]` (without `--at` the receipt keeps the timecodes chosen for this
mix), or `waived` with their reason. The receipt is bound to the soundtrack's stamp, so a new mix
makes it stale. Publish warns, not stops, when none stands, naming the timecodes, and the handoff
lists it as a next step. A narration alone needs no listening unless the user wants one. Never
record a listening nobody did: say that nobody has listened.
