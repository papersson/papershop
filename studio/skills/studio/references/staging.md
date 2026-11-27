# Staging: where the eye goes

Read this before designing or reviewing any chapter. It turns "one place to look" (taste.md, "Let
the picture speak") into rules a scene author can follow and a reviewer can check.

Why it exists. Patrik, after the dark cut of the Save film's Act 4: "I want to really optimize the
'staging' aspect of it. Be extremely careful about designing the experience for my attention should
go, and make sure nothing else distracts it, and make sure I can digest whatever I'm attending."
That cut looked like a dashboard to monitor: the whole machine always on screen, the thing that
mattered a 40 px square, three or four things lit at once. Clean, for him, means focused attention,
not pale or sparse: "your eyes are drawn to the thing you need to attend to, and the stuff around it
is either blank or subtle/quiet." The rules below are what fixed it, and what the later polish
rounds on the same film kept winning with.

## The shot list comes first

Every sentence's screen note in SCRIPT.md names its subject: the one thing the eye should be on
while the sentence is spoken. The screen notes are the plan; these rules are how a scene carries
it out. If you cannot say what the eye should be on, do not draw anything new.

## The rules

1. **One subject per sentence.** The screen note names it.
2. **Size is importance (Hitchcock).** The subject is the largest lit thing and sits in the middle
   of the frame (at 1080p, screen x 360 to 1560, y 190 to 830). Its key text is at least 56 px on
   screen and a key object at least 90 px. Get there with the camera, not by drawing things bigger:
   the world keeps one geometry.
3. **Brightness is the pointer, and it has a clock.** Full ink is for the subject only. When the
   voice moves on, the subject steps down one tone, and at the next step another. Furniture is a
   hairline. At any frame, one thing is at full ink and at most two at the second tone. A coloured
   thing that is not the subject keeps its colour but is the only colour of its kind in frame, or
   sits at reduced opacity (about 0.6).
4. **One change at a time, on the word.** Every onset lands on the word that names it. No two
   changes in two places at once: sequence them at least 1.2 s apart, or make them one event in
   one place (within about 300 screen px). An onset takes 0.3 to 0.6 s; a thing travelling takes
   0.7 to 1.2 s. A group (the items of a list, a row of boxes, the rows of a table) arrives one
   item at a time in reading order, `c.kit.stagger(t0, i, 0.12)` to `0.2`: one event, read item
   by item, never all at once.
5. **Eye trace (Murch).** The next subject appears where the eye already is (within about 350
   screen px), or the eye is carried there by one visible movement: the thing itself travels, a
   line draws, or the camera follows.
6. **The camera follows the subject.** It moves only to follow something that travels, or at the
   first words of a sentence to go to that sentence's subject. One move per sentence at most, 0.8
   to 1.4 s, with a heavy ease. While it moves nothing else starts, except what the move itself
   reveals. It never moves inside a rest. No zooms for energy.
7. **Rests are still.** Every marked breath and prediction is a rest. The picture has landed
   before the rest starts and nothing moves, fades or appears until it ends: no late labels, no
   settling tones, no camera, no ambient traffic. Anything that lives on its own (a network, a
   clock) slows to a halt before the rest. Step things down when the next sentence begins.
8. **A consequence gets a still beat.** When something happens because of what came before (the
   power returns and the memory is empty), hold the camera on the result for about a second
   before it leaves. The viewer has to see the consequence before being told where it leads.
9. **Words are names on things.** A word on screen names the thing it touches, appears with it,
   and is at most four words. Do not print what the voice is saying (Mayer's redundancy
   principle). The exceptions are code, measured numbers and the hero words the screen notes
   give. Nothing is under 26 px on screen at 1080p, at every camera zoom. A label over a busy
   picture sits on a knockout in the exact ground colour, with no border.
10. **Nothing is on screen that the sentence does not need.** Layers the sentence is not about are
    out of frame or a whisper. Do not add labels, legends, captions, counters or reminders the
    notes do not ask for. Nothing the voice names is clipped by the frame edge, in any shot or
    while anything enters.
11. **One map.** Every place has its position for the whole film, and changes of place are camera
    moves along that map (grammar.md, "One map"). A thing keeps its place for the whole chapter.

Not allowed as pointing devices: glow, pulsing, vignettes, arrows that are not the motion itself,
text that types on, a second accent colour.

## The audit

The rules are judged by eye on stills at every onset and rest. A rendered draft is also measured
by `studio attention VIDEO --chapter CLIP` (the Save film's attention audit), which every chapter
agent runs on its own draft before reporting, so staging misses are fixed before review. Motion
inside a marked rest fails; the rest are warnings with the seconds to look at (`--where`). The
measures and their aims, with the Save film's Act 4 before staging in brackets:

| Measure | Aim | Before |
|---|---|---|
| lit_over2: more than two lit things on screen | under 15% of the time | 82% |
| split: change in two far places at once | under 8% of moving frames | 26% |
| far_jumps: next onset more than 30% of the frame away | under 10% | 27% |
| fast_onsets: next onset within 1.2 s | under 10% | 22% |
| hero: the largest lit thing | at least 3% of the frame | 1.6% |
| rest_motion: movement inside a marked rest | 0 s | not measured |
| bursts: three or more separate things arriving in the same 0.2 s | none | not measured |

The numbers are a proxy for where an eye goes. A camera move reads as movement over the whole
frame, and a thing travelling under a following camera reads as a far jump, so look at the frames
behind each number before trusting it. Fix what is a real second pull on the eye; report what is
the measure misreading a designed move.
