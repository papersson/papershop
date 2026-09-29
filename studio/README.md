# studio

An agent-driven video studio. Scenes are code on one timeline, an engine renders them (Remotion
first), and the user reviews each cut on a local page and leaves notes that drive the next cut.

```
claude plugin install studio@papershop
```

## Environment

Everything runs through `skills/studio/bin/studio`, which loads the flake's `studio` shell (Python,
uv, Node 22, ffmpeg, sox) and caches it per `flake.lock`. Python packages are pinned by
`kit/uv.lock`, the engine's by `engines/remotion/package-lock.json`. Then:

```
skills/studio/bin/studio doctor --fetch     # engine packages and its headless shell
skills/studio/bin/studio doctor             # every check, with fixes
```

The browser is the engine's downloaded headless shell (four times faster per frame than a full
Chrome in headless mode), else `STUDIO_BROWSER`, else an installed Chrome. Without Nix, set
`STUDIO_NO_NIX=1` and install the tools yourself; `doctor` says what is missing.

## Status

Phase 0 of the redesign: the timeline contract, the engine interface with its Remotion engine,
cuts with per-clip re-renders, word alignment, and the review page. See
[`skills/studio/SKILL.md`](skills/studio/SKILL.md).
