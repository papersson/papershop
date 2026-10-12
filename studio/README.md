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

On invocation the skill runs `skills/studio/bin/studio preflight`, a read-only check that works
before the environment is installed. On first use it explains the missing tools and downloads,
asks for your confirmation, installs the agreed set, then tests rendering and local speech before
starting the video. Expect several minutes and several GB for a fresh local narration setup.

The launcher uses the plugin's pinned Nix environment (Python 3.12, uv, Node 22, ffmpeg, sox) when
Nix is present, or an existing toolchain with `STUDIO_NO_NIX=1`. The flake covers Apple silicon
macOS and x86_64/aarch64 Linux; native Windows needs a Linux environment. Python packages are
pinned by `kit/uv.lock` and engine packages by their `package-lock.json` files. After setup approval,
the usual install is:

```sh
skills/studio/bin/studio doctor --fetch --engine live --extra kokoro --extra align
skills/studio/bin/studio doctor --engine live --extra kokoro --extra align --speech
```

The first command installs packages, a headless browser and the language model; the second renders
a test frame and synthesises/recognises a short sample, fetching speech model weights if needed.
Public installs must explicitly select spaCy's official model wheel if their package index does
not carry it. See the [setup guide](skills/studio/references/setup.md) for that command, system-tool
installation, proxies, optional dependencies and existing pinned videos. `preflight` doesn't
verify model weights or launch tools; the first-run smoke tests do. Later invocations check what
is present without reinstalling everything.

Kokoro needs no API key or paid account. ElevenLabs is used only on request and needs
`ELEVENLABS_API_KEY`. Sound packs and other rendering engines are installed only when needed.

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
