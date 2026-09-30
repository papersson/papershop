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
  sequence of tweens. The kit is smaller (below).

## Motion Canvas scenes

`scenes/project.ts` lists one scene per clip in `timeline.json`, in order; each scene is
`studioScene('s1', function* (c) { ... })` from `@studio-mc`, and holds its last frame until its
clip's end so the clips tile the video. The context `c` gives:

- `c.at('03')`, `c.end('03', 0.5)`, `c.word('03', 2)`, `c.cue(name)`: times in clip seconds;
  `yield* c.until(t)` waits for one;
- `c.text(string, [x, y], {size, color, font, weight, opacity, name})` and
  `c.box([x, y], w, h, {fill, stroke, radius, opacity, name})`: nodes placed in stage units (the
  stage is 8 units tall above the caption band, origin at its centre, y up, as in Remotion);
  named nodes are what `studio boxes` reports, and text nodes count for the legibility check;
- the caption band and the layers (`all`, `no-captions`, `no-band`, `background`) are handled by
  the kit, so `studio check` works unchanged.

Anything Motion Canvas offers is available: import from `@motion-canvas/core` and
`@motion-canvas/2d` (the engine resolves them for you). `spring(t)` is exported as well.

## What Motion Canvas doesn't have yet

The map and close-up components, `PixelCanvas` (pixel art), `Shot` (captured assets) and `Footage`
(edits) exist for Remotion only, so pixel, launch and footage videos use Remotion. A video that
needs both should pick Remotion. Nothing prevents porting them; each is a small module.

## Measured (an 8-core Apple silicon machine)

| | Remotion | Motion Canvas |
|---|---|---|
| a frame after editing a scene | 1.6 s | 1.2 s |
| a 15 s clip at draft quality, in a cut | (13.5 s for a 32 s chapter) | 18 s including stills and the composite |
| determinism (a frame twice) | identical | identical |

Both start their bundle or dev server on every call; Motion Canvas's first call after installing
takes about 20 s while Vite optimises its dependencies, and is quick afterwards.
