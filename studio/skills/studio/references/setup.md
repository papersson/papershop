# First use and environment repair

Run this procedure before production on a new machine, when preflight fails, or when the user asks
for setup. Use the installed skill's absolute `bin/studio` path; examples below abbreviate it as
`studio`. Do not assume it is on PATH. `studio preflight` is safe before approval: it does not
enter Nix, run uv sync, write caches, install packages, contact hosts or launch a browser/model.
Exit 1 means setup is needed, not that the plugin cannot be used.

## Agree on the missing work

Infer the minimum requirements from the requested task. A normal narrated explainer needs the live
engine, Remotion's shared renderer/browser, Kokoro and alignment. A silent motion piece needs its
engine without speech packages (`preflight --engine remotion --silent`). ElevenLabs is only for
an explicit request, needs the `audio` and `align` extras and the user's API key, and has usage costs.
Motion Canvas and 3D are optional; do not install them just because doctor reports an optional
warning. The recorded sound kit (`doctor --fetch --sounds`, CC0 recordings, a small download) is
optional too, but a video with hero moments uses it (`taste/delight.md`): include it in the plan
when the video will have effects.

Tell the user what was found and what is missing, then ask one concrete setup question, for example:

> Studio needs its rendering packages, a headless browser and the local speech models on this
> machine. These are free and run locally; the initial download can take several minutes and use
> several GB. They live in the plugin's environment and normal model caches; videos go in
> `~/studio` unless you choose another folder. May I install these and run a short test?

Tailor that message to the actual check. Include any missing system tools and the proposed package
manager in the plan; don't install a new system package manager without including it in the
confirmation. Say if administrator interaction will be needed. Keep an already approved plan in
effect across retries. If the user declines, offer narrative/boards planning and leave production
pending; do not repeatedly ask or claim an estimated timeline is a rendered video.

## Prepare the system layer

The bundled Nix flake provides Python 3.12, uv, Node 22, ffmpeg and sox on Apple silicon macOS and
x86_64/aarch64 Linux. Native Windows has no launcher; use a Linux environment such as WSL2. Intel
macOS is not in this flake's platform list; use the manual path and verify it rather than promising
a supported Nix setup. The current setup has been exercised locally on Apple silicon; a clean
machine test is still needed before claiming other platforms are verified.

- If Nix is present, the approved `doctor --fetch` command enters the pinned environment. The
  launcher enables the required Nix command/flakes features for that invocation; it does not edit
  global Nix configuration. A first run may download the system packages as well.
- If Nix is absent, offer [Nix's installer](https://github.com/NixOS/nix-installer) or the user's
  existing package manager. Inspect the official installer instructions before executing them.
  Nix installation may require the user to complete an administrator prompt and restart the shell.
- For an existing toolchain, set `STUDIO_NO_NIX=1` on studio commands and provide Python 3.12,
  [uv](https://docs.astral.sh/uv/getting-started/installation/), Node 22+ with npm, ffmpeg 6+ with
  ffprobe, and sox. uv can obtain Python 3.12 during the approved bootstrap. Use the platform's
  package manager; don't guess one command for every operating system. Preserve the environment
  choice for this session and record it in a handoff if work continues elsewhere.

`STUDIO_HOME` selects the video directory (default `~/studio`); report it, don't require a folder
choice. Check available disk space before a large first download. Existing package indexes/proxies
are intentional: do not bypass them on failure. The network diagnostics are opt-in (`doctor --net`).

## Install the agreed packages

After confirmation, for the default narrated explainer:

```sh
studio doctor --fetch --engine live --extra kokoro --extra align
```

This installs the pinned Node/Python packages, headless browser and spaCy language model. Include
`--engine motion-canvas` only for that engine. Omit speech extras for a silent piece. Remotion is
always installed because all engines use its renderer/browser. `doctor --fetch --sounds` is a
separate optional download for recorded effects. Don't rerun `--fetch` on every invocation: it
runs `npm ci` again.

**spaCy model source:** the default installer uses `UV_INDEX_URL` (or `PIP_INDEX_URL`), and a mirror
must carry a compatible `en-core-web-sm` wheel. Public installs can explicitly choose the official
wheel listed by [spaCy](https://spacy.io/models/en#en_core_web_sm), including that source in the
agreed download plan. For the currently locked spaCy 3.8 family:

```sh
STUDIO_SPACY_MODEL=https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl \
  studio doctor --fetch --engine live --extra kokoro --extra align
```

`STUDIO_SPACY_MODEL` also accepts a local wheel path. Check the model's compatibility when the
Python lock changes. There is no silent GitHub fallback if a configured source fails. A failed
download should produce a specific repair or a request for missing network access; stop repeating
the same failed command. Preserve completed downloads and resume from the failed layer.

## Verify before a full video

```sh
studio preflight
studio doctor --engine live --extra kokoro --extra align --speech
```

Use the selected engine/extras here too; omit `--speech` for silent or ElevenLabs-only work.
`doctor` tests a browser launch and, with live installed, renders one frame through the actual
engine. `--speech` synthesises a short Kokoro sample and recognises it with faster-whisper;
it may download Kokoro/Whisper model weights on first use, which must be included in setup approval.
This costs no API credits and creates no user video. Missing native libraries, inaccessible model
hosts and recognition failures must be resolved before promising narration is ready. Preflight
checks package presence, not model weights or successful execution; a pass alone is insufficient
on first use. For another engine, also render a small still with that engine before a long build.

Summarise the tested engine, narration, workspace path and any optional limitations. Then resume
the requested video; keep the first preview small enough that the user can judge the voice and
look before a long render. Reviewers are a separate capability: establish access to fresh review
processes before promising required independent reviews, and report unavailable ones honestly.

## Existing videos and upgrades

Passing a video to ordinary commands routes to its pinned `.studio/bin/studio`. The installed
`preflight VIDEO` deliberately checks the installed kit without executing an unknown older
launcher. If the video has a pin, inspect its launcher; use its own `preflight` when available,
then its doctor. An old launcher without preflight can bootstrap downloads even for `doctor`, so
include that in the agreed plan. Do not update a pin merely to make diagnostics pass. Protect cuts
before an authorized `studio init VIDEO --update`, then check the updated kit's dependencies.

New narration uses one configured voice and speed. Old `timing.pause`, `kokoro.role_speed` and
role markers are ignored by the current narration code. Existing audio stays intact until
re-narrated; after doing so rebuild the timeline and inspect affected scenes before publishing.
