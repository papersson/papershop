# The kit

Run every command through the absolute path to `bin/studio` beside the skill. `studio --help`
lists commands and `studio COMMAND --help` lists arguments. VIDEO is a path containing
`video.json`. File arguments resolve against the caller's working directory.

## Setup and files

`studio preflight [VIDEO]` checks prerequisites without downloads or browser/model launches.
For a new explainer it checks live, Kokoro and alignment. `--engine remotion` checks that engine;
`--silent` omits speech prerequisites. `studio doctor [VIDEO]` diagnoses the environment and
prints fixes. Its `--net` checks download hosts and `--speech` tests synthesis and recognition.

The launcher enters the plugin's Nix environment with Python, uv, Node, ffmpeg and sox, and caches
that environment against its lock file. Python dependencies are pinned in `kit/uv.lock`; engine
packages have their own lock files. Kokoro, audio processing and alignment are Python extras.
Use the printed setup command for missing dependencies. If the configured package index has no
spaCy model wheel, set `STUDIO_SPACY_MODEL` to an explicitly chosen wheel URL or local path
compatible with the installed spaCy major/minor version, then rerun the printed doctor command. Explain downloads and paid services
before initiating work outside the user's authorization. Never silently substitute a paid voice.

`studio doctor --fetch --engine live --extra kokoro --extra align` prepares the engine and speech
packages. `studio doctor --fetch --sounds` fetches verified CC0 sound packs. Browser discovery uses
`STUDIO_BROWSER` when set, then the headless shell or an installed browser. CPU WebGL is the
stable default; `video.json.gl: "gpu"` uses the machine's GPU. The backend enters render keys.
Blender is needed only for videos configured with plates. Use available tools and report anything
that could not run; a missing renderer is not evidence that its frames passed.

`studio new NAME [--dir PATH] [--title TITLE] [--source REPO] [--engine live|remotion]` creates the
folder. `--duration SECONDS` creates a silent scene test. `--from VIDEO` inherits the look and
lexicon for a series; repeat `--include RELATIVE_PATH` for explicit dependencies. The default
engine is live. Existing videos keep the kit they were made with.

| Path | What belongs there |
|---|---|
| `research/brief.md` | The agreed one-page story and its lock decision. |
| `SCRIPT.md` | Beats, quoted narration, screen notes and source evidence. |
| `narration.json`, `lexicon.json` | Voice, pronunciation and deliberate holds. |
| `audio/timings.json`, `audio/words.json` | Synthesized sentence timing and recognized word alignment. |
| `cues/<clip>.json` | One chapter's named events. An existing `cues.json` is also read. |
| `scenes/<clip>.js`, `data/<clip>/` | One live chapter's picture and its data. |
| `layout.json`, `video.json` | Frame, caption band, engine, legend and optional plates. |
| `boards/boards.json` | Rough picture layouts held to narration in the reel. |
| `audio/sfx.json`, `audio/tracks.json` | Effects and additional audio tracks, owned by the main session. |
| `timeline.json` | The generated shared timeline; direct edits are replaced on build. |
| `assets/provenance.json` | Sources and licenses of captures, images and recordings. |
| `research/reviews/`, `research/shoot/` | Plain findings, review bundles and chapter jobs. |
| `review/notes.jsonl`, `review/status.json` | The desk's notes and progress. |
| `cuts/cutN/`, `out/`, `.cache/` | Saved versions, publish outputs and disposable build caches. |
| `sims/` | Reproducible evidence or shared build helpers. |

Use `studio run VIDEO SCRIPT [ARGS...]` for Python or Node helpers in the video. Python sees the
kit and its packages. The working directory is VIDEO and arguments pass through unchanged.
Keep temporary work inside the video. Chapter helpers may write only their assigned files.

The implementation is in `kit/src/studio_kit/`, commands in `cli.py`, and tests in `kit/tests/`.
The scene engines are `engines/live/` and `engines/remotion/`; timing and motion helpers shared
by them live in `engines/shared/`. Templates show real API calls and are useful to copy selectively.

## Narration, captions and the beat sheet

`studio narrate VIDEO` synthesizes the quoted paragraphs in `SCRIPT.md`, caches each paragraph
and writes the narration and timeline. `--list` prints sentence ids, `--plan` reports cached work,
and `--estimate` builds approximate timings without sound. Use real narration for reels and cuts.

Kokoro defaults to `af_heart` in paragraph mode. New videos use speed 0.95 and explicit chapter
spacing. Keep the configured voice and speed constant. `narration.json` supports `holds` by
sentence id, `spoken` text replacements, `spoken_by_id`, `phonemes` and `phonemes_by_id`.
A lexicon snapshot supplies shared pronunciations; per-video settings and then per-sentence
settings override it. `studio lexicon add WORD --spoken TEXT [--phonemes IPA]` promotes a fix.

`studio voice-check VIDEO` transcribes sentences and scores them against the script; `--all`
checks all again, while normal runs reuse unchanged results. Investigate low scores and missing
speech. `studio align VIDEO` attaches recognized words and rechunks captions. Pronunciation still
needs judgment: recognition can miss the difference between an acronym spoken as letters or a word.

ElevenLabs remains available in `narration.json.engine`, with its settings under `elevenlabs`.
Choose it before scene timing when the user asks. `--plan` reports work, `--fetch-only` fills the
response cache, and `--yes` authorizes spending beyond the command's confirmation threshold.
Keep `audio/elevenlabs_cache/` so a rebuild can reuse paid responses. Do not change the voice as
an incidental finishing step.

`studio timeline VIDEO --events` rebuilds the shared timeline and prints each cue's absolute time,
frame, chapter, local time and anchor. A chapter cue file is an object:

```json
{
  "s1-enter": {"sentence": "s1_01", "at": "end", "offset": 0.4, "weight": 3},
  "s1-result": {"sentence": "s1_02", "phrase": "the new colour"}
}
```

A value can be absolute seconds or an anchor with `sentence`, `at` (`start`, `end`, `word` or
`phrase`), `word` index, `phrase` and `offset`. A phrase can follow a sentence renumbering when it
has one unambiguous match. `weight` describes emphasis; `hitstop` records a physical contact's
hold in frames. Both leave the event time unchanged. Cue names are unique across files. Chapter
cues stay inside their chapter. The build snaps cues to the same frame grid the engines use.

The scene's `cue(name)` and its sound use that one event. Use literal cue names so incremental
keys can identify dependencies. Inline holds create `reveal:s1_01` cues at their end. Times in
source cue files are absolute; scene helpers return clip-local times.

Captions come from narration words, broken at phrase boundaries into up to two lines of about
42 characters, held at least 1.2 seconds. `layout.json.band` reserves their space, 160 px at 1080p
by default. A zero-height band removes it. `captions.json` can preserve edited chunks using
`anchor: {sentence, words: [first, last], text}`; fixed start/end chunks warn after narration changes.
Keep scene content above the band. Export formats wrap their own caption lines from the same words.

## Boards and the reel

`studio reel VIDEO` narrates, builds the timeline and holds boards to the real voice, then prints
a pacing report. `studio boards VIDEO` and `studio animatic VIDEO --boards` remain useful lower
level operations. Scene cuts fall back to boards for a chapter with no scene file.

A rough board uses stage units centered on the picture, y up, eight units high:

```json
{"s1": [{"from": "s1_01", "elements": [
  {"box": "pixel", "at": [0, 0], "w": 5, "h": 5},
  {"text": "input", "at": [-5, 0], "size": 0.4},
  {"arrow": [[-4, 0], [-2.5, 0]]}
]}]}
```

A board holds until the next `from` sentence. Screen notes supply text where a board is missing.
Use enough actual layout to judge scale, then inspect the reel's runtime, long holds and empty
sentences. The schema and renderer live in `boards.py` and the engines' board modules.

## Live scene API

Write `scenes/s1.js` with `export default function draw(c)`. Every frame depends only on time;
use seeded randomness and direct time evaluation. The SVG stage uses pixels, with origin at
the top left, x right and y down. `c.W` and `c.H` exclude the caption band; `c.unit` is `H / 8`.
This differs from board and Remotion stage coordinates.

```js
export default function draw(c) {
  const {S, W, H, kit} = c
  const p = c.P(c.cue('s1-enter') - 0.35, 0.35, kit.ease.out)
  S.rect('pixel', W * 0.25, H * 0.12, W * 0.5, H * 0.76, {
    fill: kit.C.cold, stroke: kit.C.edge, op: p, box: 'pixel', means: 'subject',
  })
  S.text('pixel-label', W / 2, H * 0.52, 'pixel', {
    size: 56, anchor: 'middle', op: p,
  })
}
```

Nodes have stable keys. A node not drawn in a frame is hidden, and attributes reset between
frames. Text keys identify text to the checks; name a shape with `{box: 'pixel'}` so bounds and
visibility checks can see it. `means` tags a legend meaning. Declare the meaning-to-theme-colour
mapping in `video.json.legend` and keep it consistent in every chapter.

| Context or helper | Use |
|---|---|
| `c.t`, `c.dur` | Current clip time and duration in seconds. |
| `c.at('01')`, `c.end('01')`, `c.word('01', 2)`, `c.phrase('01', 'new colour')` | Narration times within the clip. |
| `c.cue('s1-enter')`, `c.P(start, seconds, ease)` | An event's local time and animation progress. |
| `c.S.rect`, `circle`, `text`, `line`, `path` | Keyed SVG primitives; templates show signatures and options. |
| `c.S.strike`, `callout`, `closeUp`, `blur`, `el` | Subject treatments and an escape hatch for SVG elements. |
| `c.asset(file)` | An asset URL that works on the desk and in the renderer. |
| `c.header`, `c.view` | Reserved header height and the usable `[x, y, w, h]` below it. |
| `c.camAt(keys)`, `c.frameOn(region, options)` | A time-based camera and a region fitted into the view. |
| `c.sentences`, `c.chapters`, `c.title`, `c.index` | Context from the shared timeline. |

`c.camAt([[t0, {x, y, z}], [t1, c.frameOn([x0, y0, x1, y1]), 'heavy']])` moves between keyed
camera states. The center is in pixels and `z` is zoom. `bg`, `main` and `fx` layers move with the
camera; `over` and `ui` stay fixed. An optional `scenes/overlay.js` draws over all chapters and
is owned by the main session.

`c.kit` supplies `C` theme colours, `ease`, `lerp`, `clamp`, `keyed`, `stagger`, `pulse`, `spring`,
`track`, `countUp`, `follow`, `settle`, `wobble` and `rng(seed)`. `keyed(t, keys)` interpolates
numbers or arrays. `follow(t, fn, lag, stiffness, damping)` trails a time-based source;
`settle(t, contact, amplitude, frequency, decay)` adds a decaying physical settle. Use these where
the subject earns them. Named eases include `out`, `in`, `inOut`, `smooth`, `back`, `heavy`,
`float` and `snap`. `studio glossary [--term WORD]` connects motion words to helpers and examples.

Import live helpers through `@studio/`, such as `@studio/kit.js`. Import three.js through `three`
or `three/addons/...`. The desk and renderer resolve those names together. Absolute `/engine/`
imports will break that agreement. See `templates/live/scenes/example-chapter.js` and
`engines/live/src/` for complete primitive signatures.

## Depth, light and plates

`c.G` draws keyed 3D objects below the SVG stage. `G.mesh(key, kind, params, options)` supports
box, cylinder, tube, sphere, ring and extrude geometry. Options include `at`, `rot` in degrees,
`scale`, `color`, `op`, `edges`, `box`, `means` and `view`. `G.line` draws a 3D polyline.
The flat look uses three face tones and pixel outlines. Call `G.lit({key, intensity, shadows})`
before the solids to use physical materials, soft shadows, roughness and metalness.

A shot is `{target: [x, y, z], az, el, span, fov}`, with world y up. `c.shot(keys)` interpolates
shots; `G.camera(shot)` sets one directly. `c.flatShot()` maps world `(x, 0, z)` onto stage `(x, z)`.
Use the same coordinates to open a diagram into depth. `G.project(point)` returns stage pixels
for an upright SVG label; `G.scaleAt(point)` gives its scale. `c.frameOn3(points, options)` fits
world points in view. `G.camera(shot, {view, rect})` creates a separate panel camera. The worked
example is `templates/live/scenes/example-3d.js`; physical impact helpers are in `example-feel.js`.

For a Blender plate, configure `video.json.plates`:

```json
{"s1": {"script": "sims/object.py", "inputs": ["sims/object/*.py"],
        "project": ["head"], "draft": {"samples": 16}, "final": {"samples": 64}}}
```

The plate script defines `build(scene, ctx)` and `pose(scene, t, ctx)`; pose is a function of clip
time. `ctx["cues"]` is a dictionary of local cue times. Start from
`templates/blender/scene.py`. `c.plate()` draws the plate behind the live scene and
`c.plate.at('head')` gives the projected point for a live label. Hide unseen objects rather than
fading transparent geometry. `studio plate VIDEO s1 --probe` measures a few frames before a long
render; `--quality final` renders full-resolution frames. Plate caches key on the script, inputs,
profile and cues and can resume missing frames.

## Remotion and code

Remotion remains available through `studio new NAME --engine remotion`. It uses
`scenes/<clip>.tsx`, registered by the main session in `scenes/index.ts`, with imports from
`@studio`. Components use stage units centered on the picture, y up. `useClip().t`, `at`, `end`,
`word`, `phrase`, `cue`, `ramp`, `pulse` and the shared motion helpers time the picture.
See `templates/scenes/` and `engines/remotion/src/kit/` for exact component props.

`CodePanel` shows recorded source `{text, sha256}`, an optional line range, current line,
plumbing and markers. `Terminal` shows captured `{argv, stdout, stderr, exit}` runs with reveal
progress. `RowTable`, `JsonTree`, `ColumnStrips`, `GeoMap`, `VarCard` and `Thread` show explicit data.
The typed-code components are `Editor`, `RunTerminal` and `ProgramWindow`; they read the same
`data/typing.json` that times key sounds. Show the editor and its program's result in one shot.

`studio typing VIDEO PLAN.json` replays edits between recorded file versions, verifies the final
buffer byte for byte and schedules keystrokes with human rhythm. The main session runs it because
it writes shared `data/typing.json`, typing cues and `audio/sfx.json`. Plans list `sources`,
`bursts` and optional run output; operations include paste, open, put, change, subst, delete,
yank, save and run. Each can have an anchor it is `due` by, a `start` anchor and `think` time.
A text segment's `typo` asks for characters to be mistyped and corrected. Keep actual program
versions and captured run output in data. The full schema is at the top of `typecode.py`.
`codeview.py` documents optional editor folds and highlights, checked with `--only code-view`.

## Sound and the mix

Use `studio sound-lab VIDEO` to choose effects by listening in context. `studio sfx VIDEO FILE`
accepts a JSON list of effects and stores them in `audio/sfx.json`:

```json
[{"t": "s1-enter", "type": "click", "sound": "kit:interface-click-001",
  "gain": 0, "visual": "appear"}]
```

The time can be a cue name, beat name, absolute second or narration anchor. `sound` selects
`synth:NAME`, `kit:ID`, `kit` for a type's default recording, or `asset:PATH`. A list is a varied
sample pool. A type without a sound selects its synth voice when available. Recorded sounds land
on their measured transient peak, with a trim that preserves perceived level. The kit copies
recordings into the video's assets with provenance, so rendering never depends on a loose cache.
`visual` (`cut`, `move`, `land`, `appear`) tells audio-check what picture event to measure.

Dense activity uses streams: one effect with `events`, each relative to its cue and carrying a
kind, and a `sounds` mapping for those kinds. Streams preserve their exact visual event times;
recorded key grains provide texture, with accents for Enter and run. `streams.py` documents the
schema. Use gain 0 as the starting point for typing streams; their grain levels are calibrated.
Generated typing effects retain their `source` tag when other effects are replaced.

The mix bus combines narration, effects and additional tracks, with shared room, presence and
ducking. `audio/tracks.json` accepts `{file, start, gain, in, out, role}`; use music only when the
user asks. `studio beats VIDEO TRACK` records a beat grid for a supplied track. `audio.py` holds the mix contract. A finish applies one fixed gain to the whole mix, with a
true-peak limiter, preserving quiet pauses. `studio audio VIDEO` defaults to −16 LUFS and
−1.5 dBTP; `--lufs -14` is available for a requested social export.

`studio audio-check VIDEO [--cut N]` measures sync, transient-to-picture timing, audibility,
loud effects, ducking, masking, pauses and loudness. It writes `out/audio-check.json`, a sound
sheet and listening timecodes, prioritizing hero events. It compares the actual saved cut with
its current source keys. Inspect warnings and listen where possible; measurements do not establish
that pronunciation or balance sounds right. A missing listening pass never blocks a cut.

## Commands for the loop

| Command | Result |
|---|---|
| `panel VIDEO` | Parallel expert, viewer and editor findings in a plain review file. |
| `shoot VIDEO` | Narration, timeline and chapter briefs with spawn prompts. |
| `check VIDEO --chapter CLIP` | Private chapter checks and stills under `.cache/chapters/CLIP/`. |
| `cut VIDEO [--stills-only] [--quality draft|final]` | Saved stills and an incremental playable version. |
| `review-pack VIDEO --chapter CLIP [--cut N]` | Combined frame, motion and sound evidence from that cut. |
| `suggest VIDEO FILE` | Reviewer findings as suggested desk notes. |
| `desk VIDEO`, `serve VIDEO` | The local desktop review page. |
| `notes VIDEO`, `wait VIDEO`, `status VIDEO TEXT` | The note loop described in `desk.md`. |
| `still VIDEO CLIP T --out PNG`, `boxes VIDEO CLIP T` | A clip-local frame and its named-element bounds. |
| `duration VIDEO CLIP`, `render VIDEO CLIP --out MP4` | Engine frame count and a silent chapter render. |
| `check VIDEO [--all] [--only CHECKS] [--format FORMAT]` | Length, determinism, bounds, band, contrast, legibility, overlaps, pacing and other diagnostics. |
| `sheets VIDEO OUTDIR [--strip CLIP T] [--windows FILE]` | Contact sheets, strips and label crops from a cut. |
| `look-sheet VIDEO` | Optional element and state sheets in the video's own engine. |
| `capture URL VIDEO`, `asset add|library|restore|list VIDEO` | Images and sound assets with provenance; `list --credits` prints credits. |
| `stage VIDEO NAME`, `stage VIDEO --report` | Timing marks and elapsed time; `waiting` separates user wait. |
| `publish VIDEO --by NAME` | The shipping decision, final master, web copy, poster, page and colophon. |
| `export VIDEO --formats 16:9,9:16,1:1` | Reframed formats on the same timeline with separate layout checks and caches. |
| `clean VIDEO --dry-run`, `clean VIDEO [--videos]` | Expendable caches and previews; deleting eligible old movies is explicit. |
| `commit VIDEO MESSAGE` | A source checkpoint that respects signing and preserves unrelated staged work. |

Shared commands wait on file locks. Chapter checks and review packs have disjoint work folders.
The deterministic checks catch actual frame and audio problems. Full-video checks retain optional
staging and code-view diagnostics where those files exist. Long holds and motion warnings need
interpretation against the story. Unchanged chapters reuse checks, narration and render keys.

Cuts retain their records and saved movies by default. Opened, noted, final and protected cuts
remain protected during cleanup. Inspect `clean --dry-run`; avoid manual cache deletion while
agents are using it. `studio commit` uses the video's ignore rules for generated media and caches;
asset provenance and paid narration responses remain checkpointable.

## The standing ablation

Run `studio ablation [--topic "shaders"]`. It creates two separate folders under
`$STUDIO_HOME/ablation/<date>/<run>/`, prints their prompts and launch commands, and writes
`comparison.json` for timings and user notes. The bare launch uses Claude's safe mode with skills
disabled; the Studio launch explicitly loads this plugin. Neither agent runs until a later
session launches it. Use the same model, initial topic and length. Record user waiting separately
and save the briefs each approach develops. Compare playable videos side by side for clarity,
level, breathing room, frame occupancy, performed events and sound. Keep the user's own verdict.
