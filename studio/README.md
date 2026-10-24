# Studio

Studio makes narrated explainer videos through three verbs: develop the story, shoot and review
on the desk. You lock the story and say when to ship. The agent operates the tools.

```sh
claude plugin install studio@papershop
```

Ask for a video, such as “Create me a five-minute explainer on shaders.” The agent drafts a
one-page brief, puts boards held to the real narration on the desk and discusses the story with
you. An expert, viewer and editor read it once in parallel and bring their findings to you.

After story lock, one agent builds each chapter in parallel, with the same taste, voice and
beat sheet. Chapter files and checks are isolated. The first playable version is intended to
reach the desk in 10–15 minutes; stage timing records the actual elapsed time. One combined
motion and frame review per chapter produces suggested notes you can accept or dismiss.

The desk is a local page on your computer. Leave a note on a sentence and see the agent's reply
with the next version. Live scenes redraw as they change, cached narration preserves unchanged
paragraphs, and cuts render only changed chapters. Say “ship it” for the final master and page.

The tools keep picture and sound on one timeline. Kokoro supplies the voice; ElevenLabs remains
available on request. Recorded CC0 sounds land on their transient peaks. Typed-code streams use
real key recordings and can correct a typo before the program answers. Live 3D, the lit look and
Blender plates support physical subjects. Remotion remains for its code and terminal components.

Run `skills/studio/bin/studio preflight` to inspect prerequisites. The launcher uses the plugin's
pinned Nix environment, or an existing toolchain with `STUDIO_NO_NIX=1`. After the needed downloads
are authorized, setup normally uses:

```sh
skills/studio/bin/studio doctor --fetch --engine live --extra kokoro --extra align
skills/studio/bin/studio doctor --engine live --extra kokoro --extra align --speech
```

Videos go under `$STUDIO_HOME`, default `~/studio`. Existing videos retain their pinned kit.
Source checkpoints, protected cuts, asset provenance and cached speech remain with each video.
Publish includes a colophon beside the master. The standing `studio ablation` command prepares
paired bare-agent and Studio starts for a later comparison.

Read the [skill](skills/studio/SKILL.md), [taste](skills/studio/references/taste.md),
[kit reference](skills/studio/references/kit.md) and [design reasons](skills/studio/DESIGN.md).
