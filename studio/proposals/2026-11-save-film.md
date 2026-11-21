# Proposal: what the Save film taught Studio

Status: proposed, 21 November 2026. Phase 1 is in this pull request (studio 0.36.0); phases 2 to 5
are proposals for Patrik to accept, reorder or drop.

## Why

"What happens when I click Save?" is the longest Studio film so far: five acts, 44:53, built over
five days. Patrik's notes on it kept coming back to a few things, and the film's own folders grew
the rules and tools that answered them: ten staging rules and an attention audit for Act 4, a film
bible, a ledger of canonical terms, and finally a polish run on three clips that hill-climbed
against frozen metrics and a blind judge for three hours. He liked the result: "I love how smooth
the animations are." None of that is in the plugin yet, so the next film would start from scratch.

His priorities, in the order they matter to him (from his notes, ranked by how often and how
strongly they came back):

1. **Staging of attention.** One subject at a time, the eye drawn to it, everything else blank or
   quiet, and time to digest it.
2. **Clean means focused, not pale.** A dark ground with real contrast and rich pictures.
3. **Draw the real thing.** Real machines, a distinct form per component, reusable in any film
   about the same fundamentals.
4. **Show, don't annotate.** Animate a claim on the picture instead of labelling it.
5. **Smooth, continuous movement on one map.** No jarring transitions.
6. **Fewer pauses, with a music bed under them,** recorded sound for touch, designed sound for
   physical consequences.
7. **Canonical terms,** load-bearing ones defined, every term introduced before it is used.
8. **Quick sketches first,** then the whole film built with the same care.

## What the plugin already has

"One place to look" and a second reviewer for it (0.35.0), no boxes-and-arrows clip art, the
recorded keyboard and mouse, the rhythm rule for pauses, palette music, canonical-term guidance in
script.md, and the elicit step. What it lacks is the detail that made attention work on the Save
film, the checks that measured it, and the polish loop that found the last ten percent.

## Phase 1: the rules (this pull request)

References only, no code: `references/staging.md` (eleven rules and the audit's aims), and the rest
folded where agents already read (taste.md, grammar.md, shoot.md, taste/notes.md). Details in
HISTORY.md under 0.36.0.

## Phase 2: checks that hold the rules

Each is small, deterministic, and lives in the kit beside the checks it resembles.

| Check | What it does | Where | Notes |
|---|---|---|---|
| `attention` | Port the Save film's attention audit (149 lines, numpy and Pillow): lit_over2, split, far_jumps, fast_onsets, hero, rest_motion, with `--where` times. Run on draft renders; aims as warnings, rest_motion as a failure. | new `kit/src/studio_kit/attention.py`, a `studio attention VIDEO [CLIP]` command, and an input to `review-pack`'s ATTENTION.md | The aims in staging.md. Its readings are a proxy, so it reports times to look at rather than verdicts. |
| `legible` at 26 px | Raise the floor from 18 to 26 px at 1080p, measured at the camera's zoom. | `check.py` | The film bible and the polish run both used 26 px; v9 found three labels at 16.8 to 24.96 px that 18 px let through. May fail older films' fixtures; give them a per-video override. |
| `inframe` for every named thing | Fail when a thing the sentence names is clipped by the frame edge, including while it enters. | `check.py` (inframe exists as a warning) | Five of the nine accepted polish rounds fixed edge clipping. |
| rests still | Make motion inside a marked rest a failure rather than a warning. | `check.py` pacing | Allow a declared exception per rest, for a designed drain like the memory emptying in the dark. |
| straight cuts | Fail a scene-to-scene cut inside a chapter unless the chapter declares it; `join = 'hard'` must sit in a silence. | `check.py` | The v9 check measured frame difference against a threshold per clip. |
| voice over everything | The voice at least 12 dB over the bed and effects at every word, and each effect within 40 ms of its visual. | `audio_check.py` | Both were measured in v9, which used the first to quiet the server fans under "Then the server loses power". |

## Phase 3: a polish command

`studio polish VIDEO [--clips ...] [--hours N]`, the loop that produced v9, built into the kit so it
runs the same way on any machine.

- **Freeze the measures first:** the hard checks (phase 2 plus narration fingerprints, loudness at
  -16 LUFS ±0.5 and at most -1 dBTP, cues within 80 ms of their words, protected numbers, shared
  files identical) and the attention readings, written to `polish/baseline.json`.
- **Hill-climb one chapter at a time,** weakest first, shared-code changes first. Every candidate
  passes the hard checks, then a blind pairwise judge in both orders, each in a fresh context,
  sees both renders, contact sheets at every onset and rest, and the sound around the hero moment.
  Accept only a win in both orders. A shared change must win its chapter and lose none it touches.
- **Stop** a chapter after three rounds without a win, and the run at its time cap; keep a
  checkpoint film every few hours, tag each accepted version, and write `POLISH-LOG.md` and a
  `REPORT.md` with metrics before and after and the moments to watch first.
- **The judge is pluggable:** Gemini through the agy CLI (as v9 ran) or Claude. The rubric is the
  staging rules plus taste.md's "never" list, with the director's notes as the target.

Sources to port: v9's `check.py`, `judge.py`, `rubric.md` and `text_check.mjs` (in the polish
bundle on Patrik's Mac, `~/studio/click-save-polish-v9`).

## Phase 4: structure for a film of real machines

- **A shared library per film** with a sync command and an identity check (`studio shared sync`,
  and a check that every act's copy matches), since look, parts and overlay drifted in all five
  acts.
- **A parts library of fundamentals** in `templates/`: a 1U server, a laptop with its mouse, a home
  router, DRAM chips, a drive, each as one drawing function in the Sumi look, plus the living
  network and the to-scale zoom from the Save film's `network.js` and `zoom-a1.js`. Patrik asked
  for visuals of memory and disk that "fit in any video about memory and disk", so these are the
  first reusable cast.
- **A film of several videos** (acts) gets an `assemble` step: the act cuts joined with dissolves
  into one film at -16 LUFS, which the Save film did with a shell script.

## Phase 5: narration and sound that survive another machine

- **Per-sentence narration cache, and splicing.** Kokoro does not give the same samples on two
  machines, so re-narrating a whole act to change one sentence changes every sentence. Keep each
  sentence's audio with the source and re-narrate only changed sentences, splicing them in.
- **Keep the music bed's recipe.** `bed.py --sections` arguments were never recorded, so the Save
  film's bed can only be rebuilt by ear. Write them to `research/music/bed.json` and rebuild from it.
- **Designed consequence sounds in the sound kit:** a relay or contactor clunk, fans spinning down
  and up, measured and pinned like the recorded keys.
- **Doctor on NixOS.** On a NixOS server the kit's numpy import fails without the nix-ld library
  path, and `studio doctor` still reports the audio extra as installed. Doctor should import it,
  and name the fix.
- **Scripts run on macOS bash 3.2,** which the Mac still has (an empty array expansion broke a
  clip script there); add a check that runs the kit's shell scripts under it or under `sh`.

## Also worth deciding

- **Packaging a film for another machine.** Moving the film to the server meant hand-building a
  bundle of served file types with a checksum manifest and a setup script. A `studio pack`
  command could make that bundle reproducibly.
- **Sketch first, then the whole film.** Patrik's "let's do much quicker iterations... 20-30 sec
  clips" while a look is unsettled, then "let's do the whole video" once it is. This could become
  a stage of `studio stage`, with stills and short clips before the shoot.

## How to tell it is done

- A new film's chapter agents read staging.md, and a reviewer can point to each rule in a chapter's
  stills without asking which subject a sentence has.
- `studio check` fails a 24 px label, a clipped name, motion inside a rest and an undeclared cut,
  on fixtures made for each.
- `studio polish` run on the three v2 clips reproduces most of v9's gains (all hard checks pass,
  Clip C's still share rises from about 5% to over 30%) without hand mixing.
- Changing one sentence of a narrated act leaves every other sentence's samples identical.
- And the one Patrik will judge: the next film's first cut needs fewer notes about attention than
  the Save film's did.
