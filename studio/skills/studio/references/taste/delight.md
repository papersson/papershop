# Motion and delight

How things move, and how the subject's events are performed with their sound. The mechanics (cues,
effects, the motion helpers) are in `../explainer.md` (Stages 10 and 11), `../audio.md` and
`../engines.md`; this file says what to aim for and why.

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
- **Motion lands with the words that explain it.** A seek that finished before the narration got to
  the coil passed a motion review: the motion was smooth and the timing told the wrong story. Each
  physical phase starts when the sentence that explains it starts.
- **Secondary motion when something has weight or hangs on something.** A tag on a box, a cable,
  a label on a moving token follows through (`follow`); a heavy thing landing settles (`settle`);
  a held picture that should feel alive drifts (`wobble`, a few pixels). Leave it off type, data and
  anything the viewer must read while it moves, and off the map at rest: secondary motion is for
  the protagonist and the moment of contact, not decoration.

## Delight: perform the subject's events

Correct and clear was not enough. A finished eleven-minute video on writing a game showed its
code, window and square appearing, with narration over silence for its first five and a half
minutes. The user wanted the code typed with the sound of keys, and said the typing was the
obvious opportunity. Game developers call this juice: abundant feedback on an action, so it feels
physical. Film sound calls the effect synchresis: a sound and an image on the same frame fuse into
one event. A video that shows states is correct; one that performs events is felt. When the same
video's code was typed in a Vim-like editor, with key sounds following the rhythm, a typo
corrected and the window answering each edit, the user's verdict was "much better".

- **Hunt for the hero moments.** Most subjects have a few events the picture can perform, with a
  sound the viewer already knows: code being typed and run, a key pressed, a window opening, a
  sector passing under a head, a packet arriving, a count ticking over, two things colliding. Look
  for every event the narration says happens, and every one with a sound in the real world. Pick
  the three to six that carry the argument, name them at the boards (`../explainer.md`, Stage 7),
  and give them more time than anything else in the polish.
- **Cause and effect in one shot.** The strongest moment shows the action and its result together:
  the edit typed in the editor and the window answering in the same frame, the click and the state
  it changes. Keep both on screen rather than cutting from one to the other.
- **Each event is set up, lands and settles**: anticipation, the contact on the cue's frame with
  its sound, then follow-through (Motion, above). An event with no build-up and no aftermath reads
  as a state change.
- **Human rhythm, not a metronome.** Typing comes in bursts with pauses at punctuation and before a
  hard line, and now and then a typo is corrected; footsteps follow the gait; a repeated sound varies
  in pitch and sample. Dense activity (typing at speed, a stream of messages) becomes a texture
  whose density follows the activity, with accents on the events that matter (Enter, save, run),
  not one identical click per item.
- **Tactile means material.** The user's word for what was missing was "tactile": a thing that
  looks like it has weight and surface, and sounds like it when it moves. A recorded sound of the
  real material beats a synthesised beep; a contact gets a small physical reaction (a recoil, a
  few pixels of shake) on its frame.
- **Silence is a choice.** Leave an event silent on purpose when the silence says something: a
  square passing through a wall that no code makes solid, a game before its chapter on sound.
- **Restraint keeps it from turning into Mickey-Mousing.** Perform the events the viewer should
  notice and leave the rest still. It never goes on decoration, title cards or text the viewer is
  reading, and the voice stays on top (`../audio.md`). Clean means no decoration; a performed event
  is the subject, not decoration.
