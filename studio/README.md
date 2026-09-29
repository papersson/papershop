# studio

Narrated, animated videos made by an agent and improved in rounds. The narrative is settled with
you first; scenes are code on one timeline, rendered by Remotion; you watch each cut on a local
review page and leave notes against the exact sentence on screen, and only what a note touches is
re-rendered. It replaces the tutor plugin.

```
claude plugin install studio@papershop
```

Then ask for a video from anywhere ("make an explainer of how this repo's sync engine works",
"teach me Raft as a video"). The skill asks whether you know the subject (you give notes) or are
learning it (fresh-context research and reviewers check it for you).

## Environment

Everything runs through `skills/studio/bin/studio`, which enters the plugin's own flake
(`flake.nix`, with the shell in `shell.nix`: Python, uv, Node 22, ffmpeg, sox) and caches it per
lock file. Python packages are pinned by `kit/uv.lock`, the engine's by
`engines/remotion/package-lock.json`. On a new machine:

```
skills/studio/bin/studio doctor --fetch --extra kokoro --extra align
```

installs the engine's packages and its headless browser, local narration (Kokoro, with torch) and
the voice check (faster-whisper). `doctor` alone checks every layer and prints fixes. The browser is
the engine's headless shell (four times faster per frame than a full Chrome in headless mode), else
`STUDIO_BROWSER`, else an installed Chrome. Without Nix, set `STUDIO_NO_NIX=1` and install the tools
yourself. ElevenLabs narration needs `ELEVENLABS_API_KEY`.

Videos go to `$STUDIO_HOME/NAME` (default `~/studio`), which also holds `learner.md`, the learner
model the student reviewer plays.

See [`skills/studio/SKILL.md`](skills/studio/SKILL.md), and [`DESIGN.md`](skills/studio/DESIGN.md)
for why it is shaped this way.
