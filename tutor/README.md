# tutor

Narrated, animated video lessons for one learner, built so they can be trusted: research in fresh contexts, a narrative the learner approves, a script that independent reviewers must pass, every number from a real run, Manim animation cut to a TTS narration, a frame-by-frame check, and a private page that collects "lost me here" notes for revisions.

```
claude plugin install tutor@papershop
```

## First use in a repo

The skill runs `scripts/setup.sh PROJECT_DIR`, which copies the pipeline kit and templates into `PROJECT_DIR/tutor/` and creates a Python venv there. The copy is deliberate: a lesson always rebuilds with the kit it was made with.

System dependencies: ffmpeg, espeak-ng, cairo, pango, pkg-config, the IBM Plex fonts, Python 3.11. Either install them (Debian: `ffmpeg espeak-ng libcairo2-dev libpango1.0-dev pkg-config fonts-ibm-plex`) or use the flake:

```
nix develop github:papersson/papershop#tutor
```

which provides them all plus `uv`; then `scripts/setup.sh PROJECT_DIR` creates the venv with the pinned Python packages (Manim, Kokoro, torch CPU, faster-whisper). Kokoro fetches its weights from huggingface.co on first run; torch's CPU wheels come from download.pytorch.org.

Script reviews need the `claude` CLI (each reviewer is a `claude -p` in a fresh context). Publishing the feedback page needs the Artifact tool (claude.ai sessions); elsewhere the page works locally without automatic feedback.

## Modes

`propose` (settle the narrative with the learner) → `build` (one background agent, end to end) → `revise` (from the page's notes). Also `setup`, `revoice`, `status`. See [`skills/tutor/SKILL.md`](skills/tutor/SKILL.md), and [`DESIGN.md`](skills/tutor/DESIGN.md) for why it is shaped this way.

The lessons this pipeline built, with their scripts, evidence and review logs, are in [`papersson/tutor`](https://github.com/papersson/tutor).
