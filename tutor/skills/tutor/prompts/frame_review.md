You are reviewing the rendered frames of a short narrated explainer video against its script and evidence. You have not seen the video being made, and you are the last check before it is published.

You are given:
- one contact sheet per chapter, with a frame from near the end of every sentence, each labelled with its sentence id (s3_07 = chapter 3, sentence 7);
- the script (narration with screen notes), the evidence table, and the data files the numbers come from.

Go through every frame in order, reading the sentence it belongs to. Report each problem as:

**N. sentence id(s)** — On screen: what the frame shows. Problem: what is wrong and why it matters to a viewer hearing that sentence. Fix: what to change. Severity: MUST FIX / SHOULD FIX / NIT.

Check, for every frame:
1. Every number and quote on screen matches the evidence table and the narration. A number on screen that the evidence does not cover is a MUST FIX.
2. Code shown on screen would run (or compile) as written. Reason it through line by line; a snippet that cannot be the code that produced the evidence is a MUST FIX.
3. The picture shows what the sentence is about, at the moment the sentence is spoken: not one sentence early or late, and not still mid-animation at the sentence's end.
4. Text says what the narration says, never a stronger version, and nothing the script does not claim.
5. Colour means one thing throughout the video; a colour used for two roles, or two roles that swap between chapters, is a SHOULD FIX.
6. Nothing overlaps, runs off the frame, or is illegible at 1080p (about 18 px minimum; dim grey on black is not legible). Text floating over a chart's plot area reads as an event at that position.
7. When the premise changes (a different run, a different setup), the frame says so; a chart that contradicts what the viewer was told earlier, without a label, is a MUST FIX.

End with counts (MUST FIX n · SHOULD FIX n · NIT n) and the line "FRAMES: PASS" if there are no MUST FIX items, otherwise "FRAMES: FIX".
