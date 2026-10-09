# studio

Narrated, animated videos made by an agent and improved in rounds. The narrative is settled with
you first; scenes are code on one timeline, drawn by the live engine (or Remotion or Motion Canvas);
you watch each cut on a local desk and leave notes against the exact sentence on screen, and only what a note touches is
re-rendered. It replaces the tutor plugin.

```
claude plugin install studio@papershop
```

Then ask for a video from anywhere ("make an explainer of how this repo's sync engine works",
"teach me Raft as a video"). The skill distinguishes subject expertise from audience needs. Teaching explainers get a fresh
student script pass; learner drive or deep-dive level also gets expert/editor script review.
Every explainer gets a polish stage whose gate is a motion review on frame sequences, which stops
after a round with no must-fix findings or two rounds; deep-dive and shared videos also get
independent frame review. Code lessons build
runnable programs around motivated ideas, with recorded outputs and optional reference sidebars.

Before anything is animated, each beat gets a rough board (what is on screen, and where) and the
boards play as an animatic against the real narration, with a pacing report, so a chapter that runs
long or a stage that sits empty is fixed while it is cheap. Chapters not yet built show their boards
in every cut.

Two modes. By default an agent builds the video in the background: you approve the narrative, pick
the look and review cuts. Say you want to follow along (`--mode interactive`) and you work on the
desk instead, a page beside the terminal: the video plays with its script, you leave a note on a
sentence, the builder (woken by `studio wait`) makes the change, and the page redraws in place with
a one-line reply under your note. Explainers use the live engine, whose scenes are plain JS drawn
from time, so a change shows on the desk the moment it is saved; the motion glossary gives you
words for motion ("stagger", "overshoot", "blur together"). Narration is Kokoro, local and free,
from first draft to the published video; ElevenLabs on request, with its balance checked first.

## Environment

Everything runs through `skills/studio/bin/studio`, which enters the plugin's own flake
(`flake.nix`, with the shell in `shell.nix`: Python, uv, Node 22, ffmpeg, sox) and caches it per
lock file. Python packages are pinned by `kit/uv.lock`, the engine's by
`engines/remotion/package-lock.json`. On a new machine:

```
skills/studio/bin/studio doctor --fetch --extra kokoro --extra align   # add --engine motion-canvas if a video uses it
```

installs the engine's packages and its headless browser, local narration (Kokoro, with torch) and
the voice check (faster-whisper). `doctor` alone checks every layer and prints fixes. The browser is
the engine's headless shell (four times faster per frame than a full Chrome in headless mode), else
`STUDIO_BROWSER`, else an installed Chrome. Without Nix, set `STUDIO_NO_NIX=1` and install the tools
yourself. ElevenLabs narration, used only when you ask for it, needs `ELEVENLABS_API_KEY`.

Videos go to `$STUDIO_HOME/NAME` (default `~/studio`), which also holds `learner.md`, the learner
model the student reviewer plays. Optional `house.md` and `lexicon.json` are snapshotted into new
videos. `studio new NAME --from VIDEO --include data/example.json` starts a related episode.

Cuts and MP4s are preserved by default. `studio open VIDEO` protects a player handoff; explicit
`clean --videos` still excludes watched, final and noted cuts. Existing pinned videos need an
explicit `studio init VIDEO --update` to get the new retention policy; protect their cuts first.
`studio commit` checkpoints source separately from generated media. See the skill command index
for steps, inline pauses, ownership, review bundles and setup diagnostics.

See [`skills/studio/SKILL.md`](skills/studio/SKILL.md), and [`DESIGN.md`](skills/studio/DESIGN.md)
for why it is shaped this way.
