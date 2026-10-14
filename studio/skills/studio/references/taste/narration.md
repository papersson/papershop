# The narration and the voice

What the narration says and how it sounds. The mechanics (markers, narrate, voice-check, the
lexicon) are in `../explainer.md` (Stages 4 and 6).

## Written for the ear

- **Short clauses,** one new number per sentence, parameter names as words.
- **Evergreen.** The narration does not refer to production decisions, briefs or sessions. Code/tool
  names that are the subject of the explanation are legitimate; names from production-only sims are
  not. Provenance lives in the Evidence table.
- **Concrete before abstract, and the wrong intuition shown failing.** A general claim is scoped to
  what was shown ("in a task group, when one fails…", not "in structured concurrency…").
- **Say what is skipped**, once, in one sentence.
- **Don't narrate the picture.** "The head is in place. So why are we still waiting?" said what the
  viewer could already see, and the user cut it. A sentence earns its place by telling the viewer
  something the picture cannot: why, how much, what would go wrong.

## Sounds like a person

Three script reviewers passed lines the user then called "LLM speak", most of all near the end.
The tells: a correction framed as "X doesn't mean Y" ("Reading the sector doesn't mean touching
it"); a hedge that protects the sentence instead of informing ("in normal operation"); a closing
recap that announces what was learned; three parallel items where one would do; abstract nouns
where a verb would do. Plain and direct reads better: "The head never touches the platter. It flies
a few nanometres above it."

- **Write the script, then make a style pass** with the prose skill (papershop's `prose`, in rewrite
  mode) when it is installed: it changes how the script says things, never what it claims. The user
  twice asked for this pass to be written by Claude Opus through `claude -p` with that skill; when a
  user names a writer, use it, keep its brief and its output in `research/`, and run the script
  review again on the result.
- **End on the picture, not a recap.** A last chapter that shows the whole mechanism working once
  more, with one sentence, closes better than a summary of the chapters.

## The voice

Kokoro `af_heart` in paragraph mode: intonation carries across a paragraph and pauses follow the
punctuation. One sentence per call made every sentence start at the same pitch after the same gap,
which the learner heard as robotic. Kokoro is the voice from the first narration to the finished
video. ElevenLabs (`eleven_multilingual_v2`, or `eleven_v4`) is the hosted option when the user asks
for it, chosen before scenes are timed, since a new voice moves every word; `eleven_v3` returns no
timestamps, which the scenes cue from.

Keep the configured voice and speed constant throughout. Automatic role-based speed changes and
pauses sounded unnatural in use ("I don't like that the AI voice has different speeds… be
consistent") and were removed two days after they shipped. Let punctuation shape the paragraph's
natural speech; use explicit `[pause]`, `[predict]` or `[beat]` holds where the viewer needs time.
Do not add variation merely to match another narrator's rate or pause statistics.

Names and terms are said right. A learner heard "uh reads one" for "A reads one", and "id" said as
the Freudian id: a lone capital letter is read as the article, a lowercase abbreviation as a word.
The pronunciation lint lists these before any audio exists, and every finding gets a fix or a
decision (`../explainer.md`, Stage 6).
