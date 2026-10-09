# Engines: Remotion and Motion Canvas

Every engine implements the same four operations (still, render, boxes, duration) and reads the
same `timeline.json` and `layout.json`, so cuts, checks, sheets, exports, the review page and
publishing don't care which one draws. A video picks its engine in video.json
(`"engine": "remotion"`, the default, or `"motion-canvas"`; `studio new --engine motion-canvas`).
One engine per video.

## Which to use

- **Remotion** (default; personal work). Scenes are React components, and every frame is a pure
  function of time. It has the whole component kit: `Txt`, `Rect`, `Arrow`, the map and close-up
  components, `PixelCanvas`, `Shot` (captured assets), `Footage`, closed-form springs. Licence:
  free for individuals and very small companies, a company licence above that; check the current
  terms before using it for a company.
- **Motion Canvas** (work). Scenes are generators (`yield*` animations), written against Motion
  Canvas's 2D nodes. Use it where Remotion's licence is a problem, or where a scene is naturally a
  sequence of tweens. The kit has the same components (below).

## Motion Canvas scenes

`scenes/project.ts` lists one scene per clip in `timeline.json`, in order; each scene is
`studioScene('s1', function* (c) { ... })` from `@studio-mc`, and holds its last frame until its
clip's end so the clips tile the video. The context `c` gives:

- `c.at('03')`, `c.end('03', 0.5)`, `c.word('03', 2)`, `c.phrase('03', 'the whole state')`, `c.cue(name)`:
  times in clip seconds;
  `yield* c.until(t)` waits for one;
- `c.text(string, [x, y], {size, color, font, weight, opacity, name})` and
  `c.box([x, y], w, h, {fill, stroke, radius, opacity, name})`: nodes placed in stage units (the
  stage is 8 units tall above the caption band, origin at its centre, y up, as in Remotion);
  named nodes are what `studio boxes` reports, and text nodes count for the legibility check;
- the caption band and the layers (`all`, `no-captions`, `no-band`, `background`) are handled by
  the kit, so `studio check` works unchanged.

Anything Motion Canvas offers is available: import from `@motion-canvas/core` and
`@motion-canvas/2d` (the engine resolves them for you). `spring(t)` is exported as well.

## The Motion Canvas kit

Everything the Remotion kit has, in generator form. Scenes drive the components from `c.every((t) =>
...)`, which runs on every frame with the clip time, so each frame is still a pure function of time:

| | Remotion | Motion Canvas |
|---|---|---|
| text and boxes in stage units | `Txt`, `Rect` | `c.text`, `c.box` (or any Motion Canvas node) |
| map, token, ghost card, close-up | `MapView`, `Token`, `GhostCard`, `CloseUp` | `new MapView(c, nodes, edges)` then `map.update({visible, lit})`; `Token`, `GhostCard`, `CloseUp` likewise |
| pixel art | `PixelCanvas` | `pixelCanvas(c, w, h, palette, draw)` (the drawing helper and bitmap font are one shared file) |
| captured assets | `Shot` | `shot(c, file, at, h, {aspect, crop})` |
| footage edits | `Footage` | `footage(c, {aspect, fit})` |
| easing and springs | `ramp`, `spring`, `track`, `swapAlpha`, `loopT`, `rng` | the same names |

Two things differ. Footage is transcoded once to a seekable WebM proxy (`.cache/mc-footage/`),
because Chrome's headless builds don't decode H.264; it is cached by modification time and seeks
frame-exact. And a scene must end at its clip's end: `studioScene` holds its last frame until then,
counting frames on the thread's `fixed` clock (its `time` is the exact sum of the waits, and drifts
from the frame count after `waitFor(0.7)`). A project needs one scene per clip in the timeline, so a
video with a placeholder chapter fails with "no scene number N": add each scene as its chapter is
written.

Starters exist for motion, pixel, launch and footage (`studio new NAME --genre G --engine
motion-canvas`), and each passes its genre's checks unchanged.

## Measured (an 8-core Apple silicon machine)

| | Remotion | Motion Canvas |
|---|---|---|
| a frame after editing a scene | 1.6 s | 1.2 s |
| a 15 s clip at draft quality, in a cut | (13.5 s for a 32 s chapter) | 18 s including stills and the composite |
| determinism (a frame twice) | identical | identical |

Both start their bundle or dev server on every call; Motion Canvas's first call after installing
takes about 20 s while Vite optimises its dependencies, and is quick afterwards.


## Setup and render diagnostics

`studio doctor VIDEO` lists the extras needed by narration and voice-check. Install with
`studio doctor --fetch --extra kokoro --extra align`. The compatible en-core-web-sm wheel is
installed through UV_INDEX_URL, or PIP_INDEX_URL when UV_INDEX_URL is unset. A mirror without that
wheel must supply it; narration never calls spaCy's GitHub downloader. Doctor distinguishes a
reachable host from HTTP access denial. Optional extras and model wheels survive subsequent
wrapper invocations; after a pinned-kit upgrade, run the repair command printed for that kit.

A browser launch blocked from a helper script may work when the same studio command is invoked
directly through the host's approved execution path. Inspect preserved stderr, run doctor, and
select an installed browser with STUDIO_BROWSER if appropriate. Do not disable the browser or
host sandbox as an automatic workaround.

Determinism compares decoded pixels as well as recording PNG file hashes. On mismatch, the kit
keeps both images, retries the pair once and records both attempts under research/determinism/.
A retry match is reported as flaky and does not enter the pass cache. Remotion already waits for
its configured fonts; inspect cold/warm rendering, font availability and time/state behavior
before blaming fonts. Unresolved visual nondeterminism blocks final delivery.
