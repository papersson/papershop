# Develop the story

Read `taste.md`. Start with the user's question and the viewer's assumed knowledge. Ask about
unknowns that would change the explanation, such as the intended audience, length or a reference
they want to match. Infer routine choices.

Before drafting anything, run `/elicit:elicit` with the user's request and what you know of the
context as its arguments. Follow that skill yourself: its panel and rich brief are raw material,
not a second production plan. Save the panel and its brief in `research/elicit.md`, so the user
can see whose judgement shaped the video. These are model-derived principles, not consultations
with those people. Elicit does no research; verify its factual uncertainties during the story step.

Precedence is simple: the user's own words in the request win over both. `taste.md` wins wherever
it disagrees with the elicit brief, because the user's taste is the one thing the model cannot
know; elicit draws on what the model knows in general.

If elicit is absent from the available skills, use this short method; never ask for installation:
- Name four to six masters whose judgement this video needs, covering the subject's field,
  explanation, motion, sound, and someone who questions whether this is the right video.
- Say what each would insist on and why; names alone contribute nothing.
- Settle the real goal and audience, including what the viewer should be able to predict.
- Describe two to four memorable moments beat by beat in picture and sound, with settled holds.
- Draw the line between delightful and tacky, and decide what to cut.
- Save this panel and raw material in `research/elicit.md`, labelled fallback, then write the brief.

Convert the raw material into a one-page story brief: three or four ideas, one example, the hero
moments and explicit omissions. Elicit reaches for more; this conversion cuts scope and never craft.
Keep the action, framing, sound and breathing room that make each retained moment work. For each
chapter, save just its described hero moment and relevant panel principles with their reasons in
`research/story/<clip>.md`. `studio shoot` includes that excerpt in its chapter job, never the whole
elicit brief. Show the short story draft quickly, with picture and sound beside each idea.

Create a video with `studio new NAME`. Write the one-page brief in `research/brief.md` in language
the user would use. Keep one central question and a small example. Set `video.json.target_minutes`
when there is an agreed length so the reel can compare its runtime with it. Level and tone are
sentences in the brief. An explicit request for comedy also calls for `taste/comic.md`.

```markdown
# Working title

We are making this for [viewer and prior knowledge]. We want to answer [one question].
The viewer starts with [current intuition] and leaves able to [explain or predict something].
We will explain it at [level] in about [length], with [tone].

Our three or four ideas are [ideas in the order the viewer needs them]. We will carry them
through [small toy example], using [few meaningful quantities].

We follow [protagonist]. It needs [stake], is blocked by [obstacle], and the ending shows [payoff].

Our hero moments are:
- In [chapter], [action] becomes [visible result]. We see [framing and motion], hear [sound],
  then hold [settled picture] while the voice adds [explanation].

We leave out [details], because [reason]. We need to verify [specific claims or uncertainties].

Story lock: [who agreed, when, and the agreed scope].
```

When the video presents finished work with a `STORY.md`, use its question, results, example and
vocabulary to draft the brief. Keep its facts tied to the same evidence.

Gather evidence for claims that need it. For a repository explanation, read the implementation
and record paths and revisions; run the small example when possible. For unfamiliar facts, use
primary sources. Keep source notes and reproducible helpers in `research/` and `sims/`, results in
`data/`. The script's Evidence table ties claims to their sources. Distinguish measured output,
inference and a deliberately simplified example.

Write the beats before filling the narration. Use this table in `SCRIPT.md`, one row per visible
change or hold. Include the chapter id so an agent can identify its part of the story.

| Chapter | Beat | Question | Picture introduced | Action and sound | Settled hold | Voice adds | Exit state |
|---|---|---|---|---|---|---|---|
| s1 | s1-open | Why is this pixel red? | One large pixel and its input. | The input changes with a key click. | Hold the new colour. | Explain how the input selects it. | The viewer can predict a second input. |

Silence is a beat. Plan introduce → settle → explain. Write full spoken paragraphs beneath
`## Script` and `### 1. Chapter title`. Each `> ` line is a narration paragraph. Add `*Screen:*`
notes with the picture, framing, sound and hero event; `s1_01` means the first sentence of chapter
one. A note without ids belongs to the paragraph above it. Use `[pause 2]`, `[predict 3]` or
`[beat]` after a complete sentence to reserve time in the actual narration.

Draw rough frames in `boards/boards.json` so the user can judge the picture's scale and density.
The schema is in `kit.md`. Screen notes fill gaps, but a page of notes cannot show whether the
subject fills the frame. Make the main picture and each hero moment visible in the boards.

Run `studio reel VIDEO`. It synthesizes the real voice, builds the timeline and holds the boards
to it. Read the pacing report for runtime, chapter lengths, long unchanged pictures and missing
pictures. A long hold can be intentional; decide by the explanation. Start `studio desk VIDEO`,
give the user its local address and show the reel within minutes of the first draft.

Run `studio panel VIDEO` once during this story session. Expert, viewer and editor each read the
brief and the script if present, in parallel and in an empty working folder. They ask about factual
claims, prerequisites and the shape of the explanation. Their findings are saved together as
`research/reviews/panel-<n>.md`. Bring the useful questions and missing readings to the user.
An empty reviewer folder limits context leakage; it is not a filesystem sandbox. A model viewer's
reaction is a diagnostic, and the real user's response settles the level and pace.

Revise the brief, beats, script and boards together from the user's response. Run the reel again
when the story changes; unchanged paragraphs reuse speech. Apply fact corrections or narrow the
claim. Let the user see disputed advice. The panel has one reading per role and makes no decision
about whether production may continue.

Ask for story lock when the user has seen the brief and reel and the open questions are clear.
Record their agreement in the brief. Honor any authorization they already gave. Then proceed to
`shoot.md`; there are no additional routine decisions before the first playable cut.
