# papershop

A Claude Code plugin marketplace: `.claude-plugin/marketplace.json` lists the plugins, each in its own
folder with `.claude-plugin/plugin.json`, `skills/`, and sometimes `hooks/`. Studio is the only plugin
with a real build (a Python kit under uv, Node engines, a Nix flake for system tools).

## Entry points

- `script/bootstrap`: makes a fresh clone ready; idempotent. `--kokoro` adds local narration (GBs,
  weights from huggingface.co), `--studio` adds studio's browser, live engine and sounds.
- `script/test [suite...]`: every plugin's tests (worklog, present-your-work, studio). Studio's take
  one to two minutes (11 in a container without Nix) and need Node 22, ffmpeg and sox; with Nix
  installed the script takes them from the flake's studio shell itself.
- `script/doctor`: one line saying what is ready and what is not, with the fix.
- `script/clean-check`: clones HEAD into a container with nothing of mine in it and runs bootstrap and
  test. Run it after adding a dependency; `--nix` is closest to the cloud, whose image has Nix.

A SessionStart hook (`.claude/settings.json` → `script/session-start`) bootstraps cloud sessions and
prints the doctor line in every session.

## Skills come from the working tree

`.claude/skills/` symlinks the skills of the plugins enabled day to day, and `.claude/settings.json`
turns off their installed copies inside this repo. Claude's cloud sessions don't install plugins, so
this is how they get the skills, and locally it means a session here always uses the version being
edited. Plugin hooks don't run this way: studio's shoot-activity hook only matters inside a shoot in
`~/studio`, and `script/bootstrap` installs the worklog CLI that worklog's hook would.

## Releasing a plugin

Bump the version in the plugin's `.claude-plugin/plugin.json` and in its `marketplace.json` entry
together, and add a `HISTORY.md` entry where the plugin keeps one. Commit message: `<plugin> <version>:
<what changed>`.
