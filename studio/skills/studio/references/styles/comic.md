# Comic: an explainer played for laughs

Read this only when video.json `tone` is `comic`, which is set only when the user asks for a comic,
cartoon, silly or slapstick video. "Fun", "delightful" or "engaging" ask for the plain polish in
`style.md`, not for this. The technique below came from one long session that made a polished comic
explainer, where the builders invented it on top of the kit. Everything in `style.md` still holds
unless a rule here says otherwise: comic adds gags, acting and sound to an explainer; it does not
loosen what the explainer must get right.

## The gag serves the sentence

- **Every gag acts out the sentence just spoken.** The viewer hears the idea, then sees it happen
  to someone. A gag about something else competes with the narration and loses the idea.
- **A gag must not imply a wrong mechanism.** The `style.md` motion rule applies to jokes too: a
  record that a character drags out of the database and into the cache says the database lost it;
  for a copy, the character photocopies it and the original stays put. A wrong mechanism told as a
  joke is remembered better than a right one.
- **Screen notes state what each gag means**: `*Screen:* s2_03: the resolver hands the second
  asker the kept slip without looking up (means: a cached answer, nobody asks upstream).`
  Reviewers check that meaning against the sentence; a gag whose meaning cannot be written in one
  clause is cut.

## The diagram stays clean

The map keeps component names only, and each colour keeps its one meaning for the whole video.
Gags happen to characters and props on or beside the map, never as text on it, and the map itself
changes only by the one state change the story calls for. A comic video that clutters the map has
traded the explanation for the joke.

## Structure

- **Setup, then payoff.** Plant the thing the joke turns on before it is needed.
- **Anticipation and the pause before the punch.** A wind-up, then a held beat (`[beat]` in the
  script, so the pause is in the narration timing and the animatic shows it), then the hit. Without
  the pause the punch lands on top of the next word.
- **The rule of three, and escalation.** Two of a pattern set the expectation; the third breaks it.
  Each repeat is bigger than the last.
- **Smash cut to the aftermath.** Cut from just before the disaster to its result; the viewer
  supplies the middle, and a cut costs less than animating it.
- **Reaction shots.** A character's response tells the viewer how to read what happened.
- **Callbacks and running props.** A prop introduced early returns at the moment its idea returns,
  so the joke doubles as a reminder.
- **The finale settles.** The last gag resolves into a calm recap frame (the map, its state, no
  characters moving), so the video ends on the key ideas, not on the noise.

## Acting

- **Takes**: a double take for surprise, an extreme take (eyes and body stretched) for the biggest
  one; save extremes for the moments that earn them.
- **Eyes lead**: an eye dart before a character moves, a blink when it has a thought. The viewer
  reads intent before the action.
- **Line of action**: one clear curve through each key pose; a stiff, symmetrical pose reads as a
  diagram element, not a character.
- **Readable silhouettes**: a pose must read as a filled shape at phone size.
- **Shape language per character**: round for friendly, square for steady or slow, spiky for a
  threat or a failure. Keep each character's shape for the whole video, as colours keep theirs.

## Effects

The kit ships no comic effects library. Build each effect in the video's scenes with the kit's
motion helpers: `keyed`, `settle`, `wobble`, `follow`, and the named eases `heavy`, `float`,
`back` and `snap` (`studio glossary` lists them, with the words a note can use). Keep frames a
pure function of t and scatter with `rng(seed)`. A helper several scenes share goes in one small
file; changing it re-renders every user.

- Inked puffs for a departure or a landing, impact stars for a hit, speed lines and smears for
  fast moves (a smear is a stretched in-between frame, not motion blur).
- **Impact frames** (one or two high-contrast frames) on the one or two biggest hits only; on
  every hit they stop registering.
- **Shake scaled to the hit**, decaying fast. The camera never shakes under a label someone has
  to read.

## Sound

- **Loud effects only in narration pauses**, decaying before the next word. Quiet effects under
  speech stay below -24 dBFS: the finish limits peaks, it does not unmask a word.
- **Layer each hit**: a transient (the click or crack), a body (the thud), a tail (the room), all
  in the same room so the layers read as one event.
- **A small motif per character**: two or three notes or one signature sound, reused whenever it
  acts. It works like shape language for the ear.
- **Time sounds from events, not by ear.** Name every contact in `cues.json`, anchored to the
  narration (a sentence's start or end, a word or a phrase, plus an offset into the pause), and
  cue the scene's move from the same name, so picture and sound start on the same frame and follow
  the words when the narration moves. `studio timeline VIDEO --events` prints the beat sheet (each
  cue's time, frame, clip and anchor). Place effects with `studio sfx VIDEO CUES` on those names
  and choose them with `studio sound-lab`. A contact lands within a frame of the picture: check
  the hit with `studio sheets VIDEO OUT --strip CLIP T`.

## Cost

Comic passes add runtime (pauses before punches, reaction shots, the settled finale) and production
time (acting, effects, sound layers). Say so at the proposal, set `target_minutes` with the extra
runtime in it, and set the budget up front: a video.json `budget` per stage (`"scenes"`,
`"sound"`, and any comic pass you mark as its own stage), so a background build stops rather than
polishing gags without end.

## Motion review: comic questions

This section is written to be included in the motion review prompt when `tone` is `comic`. Ask, for
the cut under review:

1. **Is it funny?** Score each gag 1–5 with a one-line reason (timing, setup, the pause, the take,
   the sound). A gag scoring 2 or less is cut or rebuilt, not polished.
2. **Does it read in one viewing?** At normal speed and phone size, without pausing, does the
   viewer see what happened?
3. **Is it tied to the explanation?** Does each gag act out the sentence it follows, and does its
   screen note's meaning match the mechanism?
4. **Does it steal the focal point?** While the narration names an idea, is the eye on that idea,
   or on a character, an effect or a shake?
