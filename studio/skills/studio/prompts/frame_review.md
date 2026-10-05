You are reviewing the rendered frames of a short narrated explainer video against its script and evidence. You have not seen the video being made, and you are the last check before it is published.

You are given:
- the cut's stills, one near the end of every sentence, each named by its sentence id (s3_07 = chapter 3, sentence 7), at reduced size;
- full-resolution crops of the small text, with each element's rendered size in pixels at 1080p where given (judge text size from these, never from the reduced stills);
- the script (narration with screen notes), the evidence table, and the data files the numbers come from.

Go through every frame in order, reading the sentence it belongs to. Report each problem as:

**N. sentence id(s)** — On screen: what the frame shows. Problem: what is wrong and why it matters to a viewer hearing that sentence. Fix: what to change. Severity: MUST FIX / SHOULD FIX / NIT.

Check, for every frame:
1. Every number and quote on screen matches the evidence table and the narration. A number the evidence does not cover is a MUST FIX.
2. Code on screen would run (or compile) as written. Reason it through line by line; a snippet that cannot be the code that produced the evidence is a MUST FIX.
3. The picture shows what the sentence is about, at the moment it is spoken: not a sentence early or late, and not still mid-animation at the sentence's end.
4. Text says what the narration says, never a stronger version, and nothing the script does not claim.
5. Colour means one thing throughout; a colour used for two roles, or roles that swap between chapters, is a SHOULD FIX.
6. Nothing overlaps, runs off the frame, or is illegible (about 18 px minimum at 1080p; dim grey on black is not legible). Text floating over a chart's plot area reads as an event at that position.
7. When the premise changes (a different run, a different setup), the frame says so.
8. Alignment: text centred in its container, sibling boxes the same size, a close-up centred in the stage, connectors landing on their targets. An off-centre label is a SHOULD FIX even when everything else passes.
9. Beat timing: each animation has finished by the word it illustrates, and camera moves and content changes are staged, not simultaneous.
10. The map and the band: on an overview map, any text that is not a component name is a SHOULD FIX; anything other than captions inside the caption band at the bottom is a MUST FIX.

11. Motion/placement: does any movement imply a mechanism the narration does not claim? Inspect
    transition strips as well as endpoints. A copied record must not move its geographic object;
    a reference link must not imply value ownership or data transfer that does not occur.
12. Prediction timing: the question and needed information remain visible during the pause;
    the answer is not revealed before the viewer's attempt.

End with counts (MUST FIX n · SHOULD FIX n · NIT n) and the line "FRAMES: PASS" if there are no MUST FIX items, otherwise "FRAMES: FIX".
