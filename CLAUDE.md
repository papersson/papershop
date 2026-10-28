# papershop

A Claude Code plugin marketplace: `.claude-plugin/marketplace.json` lists the plugins, each in its own
folder with `.claude-plugin/plugin.json`, `skills/`, and sometimes `hooks/`. Studio is the only plugin
with a real build (a Python kit under uv, Node engines, a Nix flake for system tools).

## Entry points

- `script/bootstrap`: makes a fresh clone ready; idempotent. `--kokoro` adds local narration (GBs,
  weights from huggingface.co), `--studio` adds studio's browser, live engine and sounds.
- `script/test [suite...]`: the pins check and every plugin's tests (worklog, present-your-work,
  studio). Studio's take
  one to two minutes (11 in a container without Nix) and need Node 22, ffmpeg and sox; with Nix
  installed the script takes them from the flake's studio shell itself.
- `script/doctor`: one line saying what is ready and what is not, with the fix.
- `script/secrets`: the encrypted keys and which machines can read them (`init`, `cloud`, `set`, `rekey`).
- `script/clean-check`: clones HEAD into a container with nothing of mine in it and runs bootstrap and
  test. Run it after adding a dependency; `--nix` is closest to the cloud, whose image has Nix, and
  `--offline` tests without a network.
- `script/receipt [--tools]`: what this checkout runs with, one line each; `script/compare a.txt b.txt`
  lines two machines' receipts up and marks what differs. `script/output-receipt` does the same for a
  rendered fixture's output, layer by layer.

A SessionStart hook (`.claude/settings.json` → `script/session-start`) bootstraps cloud sessions, puts
the pinned uv first on PATH, prints the doctor line, and records the receipt in every session's
transcript. CI (`.github/workflows/check.yml`) runs bootstrap, receipt and tests on every push.

## Keeping it reproducible

The standard: a fresh clone on any machine (the Mac, z840, a Claude cloud session, CI) bootstraps
with `script/bootstrap`, passes `script/test` with nothing set up by hand, and makes the same output
from the same input. Every change keeps it that way.

- Declare each dependency where it is pinned, never by relying on this Mac (Homebrew, `~/.claude`,
  a path outside the repo): Python packages in the studio kit's `pyproject.toml` and `uv.lock`, script
  dependencies as exact `==` versions in their PEP 723 header, Node packages in a `package-lock.json`,
  system tools in `studio/shell.nix`, downloaded models and assets at a pinned commit or checksum.
- A new tool or download also gets a line in `script/bootstrap` (install), `script/doctor` (ready or
  not, with the fix) and `script/receipt` (its version).
- After adding or moving a dependency, run `script/clean-check` (and `--nix`, the closest to the
  cloud); before calling work done, run `script/test`. CI runs bootstrap and tests on every push, and
  a red CI is a reproducibility bug to fix, not to retry.
- Tests that need a tool check for it once, in a conftest, and stop with one line naming the fix.
- Outputs must not depend on chance or the machine's state: seed anything random, pass times and
  locales explicitly, and key caches on content, not mtime (Linux mtimes tick coarsely).
- Secrets are committed encrypted, never in plain text: `secrets/secrets.json` is sops-encrypted to
  one age key per machine (`secrets/recipients`), so a machine needs only its own age key (a file on
  the Mac and z840, `SOPS_AGE_KEY` in a cloud environment's variables) and `script/secrets` does the
  rest. Builds and tests never need the ElevenLabs key; only new ElevenLabs narration does, which
  decrypts it at that moment and commits its `audio/elevenlabs_cache/` with the video, so nothing pays
  twice and a keyless machine builds. Nothing ever prints a value: no `env`, `printenv`, `sops decrypt`
  to the terminal or inline `KEY=… cmd`, since transcripts and worklog keep everything; `script/doctor`
  and the receipt say present or absent.
- The flake is the source of versions: nixpkgs (`flake.lock`) fixes uv, Python and the system tools;
  `uv.toml` names the same uv (scripts and sessions run exactly it from `.cache/tools`; a newer
  one in a terminal is accepted) and keeps uv on its managed Python; `.python-version` (root and studio
  kit) pins the same Python; Kokoro's weights are pinned to a commit in `narration.py`. To move a
  pin, update `flake.lock` first and the rest to match; `script/check-pins` (the `pins` suite) fails
  while they disagree.

Known gaps: Mac and Linux renders differ from the layout layer on (likely fonts, not yet
investigated); the cloud's default network blocks huggingface.co and api.elevenlabs.io, so Kokoro and new
ElevenLabs narration there need them allowed.

## Skills come from the working tree

`.claude/skills/` symlinks the skills of the plugins enabled day to day, and `.claude/settings.json`
turns off their installed copies inside this repo. Claude's cloud sessions don't install plugins, so
this is how they get the skills, and locally it means a session here always uses the version being
edited. Plugin hooks don't run this way: studio's shoot-activity hook only matters inside a shoot in
`~/studio`, and `script/bootstrap` installs the worklog CLI that worklog's hook would.

## Working here

- Verify visual work with studio's own stills and sheets (`bin/studio still`, `sheets`), which run
  headless on any machine; agent-browser is not installed in cloud sessions.
- Stage by explicit path and commit only what you changed: other sessions may share this checkout.

## Releasing a plugin

Bump the version in the plugin's `.claude-plugin/plugin.json` and in its `marketplace.json` entry
together, and add a `HISTORY.md` entry where the plugin keeps one. Commit message: `<plugin> <version>:
<what changed>`.
