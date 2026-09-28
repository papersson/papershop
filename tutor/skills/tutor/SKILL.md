---
name: tutor
description: >
  Build and publish narrated, animated video lessons that teach one technical idea to one learner:
  fresh-context research, a narrative the learner approves, a script that independent reviewers
  must pass, real measured evidence, Manim animation cut to a TTS narration, a frame-by-frame check,
  and a private page that collects "lost me here" notes, then revisions from those notes. Use this
  whenever the user asks for a video lesson, an explainer, a primer, or "teach me X" as a video,
  wants to propose, review or iterate on a lesson narrative, wants a lesson re-voiced, re-rendered
  or republished, or wants to act on a lesson's feedback notes. Also use it for the setup of the
  lesson pipeline in a repo. NOT for a plain chat explanation, a slide deck, a single diagram, or a
  document.
---

# tutor

You turn "teach me X" into a narrated, animated explainer video that a learner can trust: its claims come from research in fresh contexts, its numbers from real runs, its script from reviewers who never saw the draft being written, and its frames from a check against the script. The video ships on a page with a "Lost me here" button, and the notes drive revisions.

Three things decide whether a lesson is good, and everything here serves them:

1. **The narrative is the bottleneck.** A polished video of the wrong argument is worthless, so the narrative is settled with the learner before any script exists, and the build treats it as fixed.
2. **Nothing in the build context can judge the content.** A context holding a draft anchors every later judgment to it. So research, competing narratives, script reviews and the frame review all run in fresh contexts, and each reviewer sees only what it needs.
3. **The lesson is for one learner.** It starts from their model (`learner.md`), and their notes on the page revise the chapters they point at.

## Modes

Pick the mode from what the user asks; when a lesson is new, it is always `propose` first, then `build` only on their approval.

| Mode | When | What you do |
|---|---|---|
| **setup** | first use in a repo, or the kit is missing | Run `scripts/setup.sh PROJECT_DIR`. It copies `kit/` and `templates/` into `PROJECT_DIR/tutor/` and creates the venv. The copy is deliberate: a lesson always rebuilds with the kit it was made with, whatever the plugin later becomes. Fill in `learner.md`'s Background with the user before the first lesson. |
| **propose** | a new lesson | Read `references/narrative.md`. Ask whether the learner knows the topic; that picks the co-author track (iterate with them) or the trust track (competing drafts, narrative reviews, risk flags). Ends with an approved `research/narrative.md`. No script, no build. |
| **build** | the narrative is approved | Spawn ONE background agent with `prompts/build_agent.md`, filling in the paths; it follows `references/build.md` end to end. Don't build inline: it takes hours, and your context (the narrative conversation) is exactly what the script reviewers must not see. Relay its report. |
| **revise** | notes on the page, or feedback in chat | `references/publishing.md`, "Reading the notes": map each note to its sentence, update `learner.md`, fix only the chapters pointed at, re-review, re-render those chapters, republish at the same link. |
| **revoice** | a voice or timing change | Edit `narration.json`, then `narration.py` → `voice_check.py` → full `build.py` → `sheets.py` → `make_page.py` → republish. |
| **status** | "where did the build get to" | Read the lesson's `SCRIPT.md` status line, `research/reviews/`, and `out/`; report the last completed stage; resume the build agent from there. |

## The lesson folder

```
tutor/
├── kit/            the pipeline (copied by setup; see below)
├── templates/      SCRIPT.md, narration.json, lesson.json, scenes/
├── learner.md      who the learner is; the student reviewer plays them
└── lessons/NAME/
    ├── SCRIPT.md         Argument · Chain · Format · Ledgers · Script · Evidence · Review log
    ├── research/         the two research reports, narrative.md, reviews/, frame_review/
    ├── sims/  data/      every run behind every number on screen
    ├── scenes/           lkit.py (the shared picture) + s1.py … sN.py (one CueScene per chapter)
    ├── narration.json    voice, holds, spoken respellings
    ├── audio/            narration.mp3, timings.json (sentence ids → start/end), voice_check.txt
    ├── lesson.json       title, version, poster frame, description
    └── out/              web.mp4, captions.vtt, page/ (index.html, poster.jpg)
```

## The kit

All run from the project with the venv active, `LESSON = tutor/lessons/NAME`:

| Command | Does |
|---|---|
| `python tutor/kit/narration.py LESSON [--list\|--estimate]` | Narration from the locked SCRIPT.md, one call per paragraph: Kokoro af_heart (local, free) by default, or ElevenLabs (`"engine": "elevenlabs"`, needs `ELEVENLABS_API_KEY`; responses are cached, `--fetch-only` fills the cache with the standard library alone). Writes `audio/timings.json` with every sentence's start and end |
| `python tutor/kit/voice_check.py LESSON` | Transcribes every sentence's clip and scores it; the audio review, since nobody can listen |
| `python tutor/kit/review.py LESSON ROUND` | One review round: expert, student, editor, each a fresh `claude -p` in an empty folder. Refuses to run unless SCRIPT.md's status line names ROUND |
| `python tutor/kit/review.py LESSON ROUND --narrative FILE` | The same three roles on a narrative outline (trust track) |
| `MEDIA_DIR=/tmp/m python tutor/kit/build.py LESSON [--preview] [--only s2,s5]` | Renders scenes (480p15 preview or 1080p30), checks each chapter's length against its narration, joins them, muxes audio, writes captions and the web encode |
| `python tutor/kit/sheets.py LESSON OUTDIR` | Contact sheets: one frame near the end of every sentence, per chapter, for the visual check |
| `python tutor/kit/make_page.py LESSON` | The page: video, chapters, captions toggle, "Lost me here" |

## Gates you don't skip

- **Script lock:** expert PASS + editor PASS + the student's retelling answers the opening question and covers every objective. After the first passing round, apply its SHOULD FIX items once and run one final round; lock on a second pass. Every finding is logged with what was done or why not.
- **Voice check** before the render: read what was heard for every sentence under 0.8. Acronyms need `spoken` respellings ("BM25" → "B M twenty-five").
- **Frame review** after the first full render (`prompts/frame_review.md`, fresh context). It has caught a code card that did not compile and a narration line that was factually wrong after seven passing script rounds. Verify findings against the 1080p frame; downscaled sheets have produced false alarms.
- **Evidence:** a number on screen without a row in the Evidence table is a bug, not a detail.

## Style, in one paragraph

Dry and diagram-led: one diagram with a fixed geography that builds up across the video, one meaning per colour, labels rather than captions, no text repeating the narration, nothing floating inside a plot area, legible at 1080p. Narration written for the ear and evergreen: it never mentions how the lesson was made. Concrete before abstract; the wrong intuition shown failing; general claims scoped to what was shown. Details and reasons in `references/style.md`.

## Standing rules

- Commit after every stage of a build, so an interrupted build (a spend limit, a lost container) resumes rather than restarts. Never commit `audio/*.wav`, `out/video.mp4`, or `scenes/media/`.
- Never put a model identifier string in a video, page, script or commit.
- Never bypass a permission check, and never route a blocked action through a subagent.
- Publishing needs the Artifact tool for the feedback page; without it, hand over `out/page/index.html` as a local page and say feedback isn't collected automatically (`references/publishing.md`).

## References

- `references/narrative.md` — the propose stage: both tracks, the narrative document, what the build gets.
- `references/build.md` — the eight build stages, with what earlier builds got wrong. The build agent's procedure.
- `references/style.md` — look, text, narration, voice, length, with the reasons.
- `references/publishing.md` — the page, publishing with and without the Artifact tool, reading notes, revising, re-voicing.
- `prompts/build_agent.md`, `prompts/frame_review.md` — the two prompts you fill in and hand to fresh contexts.
- `DESIGN.md` — why the plugin is shaped this way.
