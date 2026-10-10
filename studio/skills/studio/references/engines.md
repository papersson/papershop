# Engines: live, Remotion and Motion Canvas

Every engine implements the same four operations (still, render, boxes, duration) and reads the
same `timeline.json` and `layout.json`, so cuts, checks, sheets, exports, the desk and publishing
don't care which one draws. A video picks its engine in video.json (`"engine": "live"`,
`"remotion"` or `"motion-canvas"`; `studio new --engine …`). One engine per video.

What the engines have in common is written once, in `engines/shared/`: the motion maths
(`motion.js`: eases, springs, `track`, `pulse`, `keyed`, `follow`, `settle`, `wobble`, ...), the narration times (`timing.js`: `at`, `end`,
`word`, `phrase`, `cue`, half-up frame rounding), the camera maths (`camera.js`: camera keys and
`frameOn`, used by live and Remotion) and the pixel-art core (`pixels.ts`). Each kit
re-exports them under its own names and defaults. Captions are wrapped by the kit for every
format and stored in timeline.json; an engine never wraps them.

## Which to use

- **Live** (default for explainers). A chapter is a plain JS module that draws one frame of SVG
  from `t`; there is no build step, so the desk plays the current scenes and redraws them the
  moment a file changes, and the same code renders the cut. Use it whenever the user may follow on
  the desk, and for any explainer that doesn't need the Remotion code components.
- **Remotion** (code explainers, motion, launch, footage). Scenes are React components, and every
  frame is a pure function of time. It has the whole component kit: `Txt`, `Rect`, `Arrow`, the map
  and close-up components, `CodePanel`, `Terminal` (a long line shrinks to fit the panel, down to
  18 px, before it clips), `PixelCanvas`, `Shot` (captured assets),
  `Footage`, closed-form springs. Licence: free for individuals and very small companies, a company
  licence above that; check the current terms before using it for a company.
- **Motion Canvas** (work). Scenes are generators (`yield*` animations), written against Motion
  Canvas's 2D nodes. Use it where Remotion's licence is a problem, or where a scene is naturally a
  sequence of tweens. The kit has the same components (below).

## Live scenes

`scenes/<clip>.js` exports `default function draw(c)`; an optional `scenes/overlay.js` exports
`default function overlay(c)`, drawn over every chapter (a ladder of stages, a running clock, a title
card as each chapter begins). A chapter without a scene file shows its board, so every cut and the
desk play the whole video. `templates/live/scenes/` has a worked example of each.

The context `c` (all times in clip seconds):

- `c.S`: the stage. `rect`, `circle`, `text`, `line`, `path` (with `{p}` a draw-on), `strike`,
  `callout`, `closeUp` (below), `blur`, `el`, and `cam(x, y, zoom)`, the raw camera (it centres the
  whole frame, band included; use `c.camAt`). Every call names its node by a key; a node not drawn
  this frame is hidden, so a frame is whatever this call drew. A call's `layer` picks where it goes,
  back to front: `bg`, `main` (the default) and `fx` move with the camera; `over` (overlays, a
  ladder, a clock, a title card, the header's contents) and `ui` don't, and neither does the
  background the engine draws.
- `c.t`, `c.dur`; `c.W`, `c.H` (the stage above the caption band, in pixels); `c.unit` (`H / 8`);
  `c.header` (the strip at the stage's top that framing keeps clear: layout.json `header.height`,
  0 by default) and `c.view`, the stage below it as `[x, y, w, h]`.
- `c.camAt(keys, ease)`: the camera as one declaration (below). `keys` are `[time, {x, y, z}, ease?]`
  in time order; each key's point is centred in `c.view`. It points the stage
  there and returns `{x, y, z}`. `c.frameOn([x0, y0, x1, y1], {margin, min, max})` is the key that
  fits a region in the view: `c.camAt([[t0, {x: c.W / 2, y: c.H / 2, z: 1}], [t1, c.frameOn(box), 'heavy']])`
  is a push-in onto `box`. A key of `{x: W / 2, y: H / 2, z: 1}` with no header is the stage as
  drawn. `c.kit.camAt(t, keys)` and `c.kit.frameOn(region, [w, h])` are the pure versions.
- `S.closeUp(key, c.view, {open, from, name, map, of, accent})`: a close-up, as Remotion's. `open`
  runs 0 → 1; the box `from` (`[x, y, w, h]`) grows into the view, then the header (the name only)
  and a corner minimap of `map` (the map's boxes, unlabelled, the one at index `of` filled in
  `accent`, ice by default) fade in. It returns the open panel `{x, y, w, h}` and `inner`, the
  opacity to draw the contents with; contents may sit outside the panel.
- `c.at('03')`, `c.end('03')`, `c.word('03', 2)`, `c.phrase('03', 'the whole state')`, `c.cue(name)`.
- `c.P(t0, d, ease)` progress of a movement; `c.kit`: `ease` (`out`, `in`, `inOut`, `back`, `smooth`,
  `heavy`, `float`, `snap`), `stagger`, `pulse`, `spring`, `track` (a value that springs to each new
  key), `keyed`, `follow`, `settle`, `wobble` (below), `countUp`, `rand` and `rng(seed)` (never
  `Math.random`), `lerp`,
  `clamp`, and the theme colours `C` (`C.hot`, `C.cold`, `C.good`, `C.bad`, `C.ink`, `C.dim`, `C.edge`
  and `C.tray` for a box's outline and fill, ...).
- `c.title`, `c.index`, `c.chapters`, `c.sentences`, `c.asset(file)`.

Text is named for the checks by its key (`legible`, `overlap`, `bounds`); give a shape `{box: 'name'}`
to have it checked too (an unnamed shape isn't reported at all). A scene file that fails to load
(a syntax error) fails with its name: `scenes/s2.js: Unexpected end of input`. Keep everything above `c.H`: the band checks fail a scene that enters the
caption band. A frame must not depend on the frames before it; the engine resets every node's
attributes and stacking each frame, and `studio check` renders samples twice to prove it. A scene
that throws fails the still or render with the clip, the time and the source line.

The motion glossary (`studio glossary`, `engines/live/glossary.html`) names these helpers: a note
that says "stagger", "overshoot" or "blur them together" maps to one of them.

## Motion helpers

In `engines/shared/motion.js`, so the live kit (`c.kit`), Remotion (`@studio`) and Motion Canvas
(`@studio-mc`) have the same ones. Each is a pure function of time: any frame renders alone, and a
value never depends on what was computed before it.

- `keyed(t, [[time, value, ease?], ...], e)`: keyframes. A value is a number or an array (a point,
  `[r, g, b]`); the ease on a key shapes the move into it, as a function or a name (`'heavy'`). The
  default ease is the kit's own: `inOut` in live and Motion Canvas, `smooth` in Remotion (as `ramp`).
- Eases, beside `out`, `in`, `inOut`, `smooth` and `back` (10% overshoot): `heavy` (slow to start,
  middle at 63% of the time, a firm stop: big things, conclusions), `float` (half a cosine, the
  gentlest: drift, ambient moves), `snap` (an exponential out: fast, then a stop that reads as hard;
  things clicking into place). In Remotion, `ramp(t, start, dur, ease.heavy)`.
- `follow(t, fn, lag = 0.1, k = 120, d = 14)`: secondary motion. `fn(s)` is the source's value at
  any time `s` (write the source as a function, as `s => keyed(s, keys)`); the result trails it by
  `lag` through a slightly bouncy spring, so a tag hanging off a box starts late, swings past and
  catches up. `k` and `d` must be above 0 (a spring with no damping never settles, and `follow` says
  so), and it weighs at most 10 s of the source's past.
- `settle(t, t0, amp = 1, freq = 3, decay = 5)`: a decaying oscillation after a stop at `t0`, added to
  a value that has just landed (`y + settle(t, land, 12)`); 0 before `t0`, and it starts at 0.
- `wobble(t, amp = 1, freq = 1, seed = 0)`: smooth seeded noise in `-amp..amp`, for hand-held drift
  and idle life; a different seed per element.

Use `cue(name)` from the beat sheet (`cues.json`) for the times these take, so a move, its sound and
its still share a frame. Every engine's `t` is the clip's frame / fps, and `cue()` returns the cue's
own clip frame / fps exactly, so a hard switch `t >= cue('hit')` happens on the cue's frame, never a
frame late.

## The camera (live and Remotion)

A camera move is one declaration of keys, `[time, shot, ease?]` in time order (`engines/shared/camera.js`),
so any frame of it renders alone. Between two keys the zoom moves in proportion and the centre in
step with 1/zoom: the move is a zoom about one fixed point, so every point, the new subject
included, travels a straight line on screen and never swings out of frame on the way; at one zoom
it is a plain pan. A key without an ease takes `inOut` in both engines (the camera's own default,
not `keyed`'s), so the same keys give the same camera in live and Remotion. Keys out of order, an
x, y or zoom that isn't a finite number (a zoom above 0) and an unknown ease name throw before the
first frame, not when their move plays; equal times are a cut. Framing keeps a header strip clear at the top
(layout.json `"header": {"height": px}`, per format under `formats` too), as the caption band is
kept clear at the bottom: the camera centres a shot in the stage below the header, the map frames
its boxes there and a close-up opens there. With no header (the default) nothing moves.

- Live: `c.camAt(keys)` with `{x, y, z}` in pixels, `c.frameOn(region)`, `c.header`, `c.view` (above).
- Remotion: `<Camera keys={[[t0, {cx, cy, zoom}], [t1, frameOn(useStage(), [x0, y0, x1, y1]), 'heavy']]}>`
  in stage units, or fixed `cx`, `cy`, `zoom` as before; `camAt(t,
  keys)` is the pure version. `Camera`, `MapView`, `frameCamera` and `CloseUp` take `headerInset`
  (stage units), which defaults to the layout's header. `MapView` and `CloseUp` take `accent`, the
  colour a lit box, a lit arrow and the minimap's source box turn (ice by default). `CloseUp` draws
  its children on the whole stage, so a part can sit outside the panel; `clip` cuts them to the panel
  and `bleed` (stage units) grows that cut, so a part may cross the edge by that much and no more;
  the checks get each child's box as the clip shows it (one it hides is left out).
- Motion Canvas has none of these.

Stage camera moves and content changes; don't run them together (`style.md`). The glossary names
them: "push-in", "pull back", "pan", "frame on". `studio check`'s `inframe` warns when an element
the sentence names is cut by the frame, the header or the band at the sentence's end. `bounds` leaves
alone an element under a camera that has moved (a push-in or pan crops on purpose; the engines mark its
box `camera`), and still fails one placed past the frame's edge with the camera at rest. `band` does
the same at an opaque band, which hides what the camera pushes under it: such a box, and its pixels
in the band, are left out; a box or shape put in the band with the camera at rest fails, and under a
frosted band (which shows what is under it) a camera's box fails too. `bounds` never
fails a shape given no name of its own (a Remotion `Rect` without `name`, reported as `rect`, marked
`named: false`), as live reports no unnamed shape; text is named by its key (live) or its words
(Remotion), and is checked.

## The look sheet (live and Remotion)

`studio look-sheet VIDEO [--format F]` renders the model sheet through the video's engine, in its
theme and layout, before scenes are built: the theme's colours with their roles, the type sizes, the
caption band with a sample caption, and each element in each state (boxes idle, lit and failed;
arrows idle, active and muted; the token's glyph states; a card with lit and failed lines; a ghost;
a callout and a strike-through on live; the map, the close-up and the code components on Remotion).
The video's own elements come after, from `scenes/look.js` (live: `export default function look(c)`,
optionally `export const pages = [titles]`, `c.page` the page drawn) or `scenes/look.tsx` (Remotion: a
default export mapping each page's title to a component). Copy `templates/live/scenes/example-look.js`
or `templates/scenes/example-look.tsx`; export each element from it so the scenes import the same
drawing. A page is drawn at t = 0 with no sentence times. A video with a colour legend (below) gets a
`colour legend` page after the built-in ones: each meaning in its colour, with the colour's name. On Remotion the sheet is a bundle of its
own (`src/look-entry.tsx`), so a mistake in `scenes/look.tsx` fails `look-sheet` and nothing else;
on live a look file that fails to load is named in the error.

Output: `out/look/look-<n>.png` and `out/look/look.json` (engine, format, the page titles and files,
whether a look file was drawn, and a key over the engine and its source, the layout, the colour
legend, the look file and the scene files it imports), or `out/look/<format>/` for another format. `look.latest(video)`
returns that record with `stale` set when any of those changed since or video.json names another
engine. `studio review-motion` copies the pages into its bundle (`look/`) and the reviewer judges "on
sheet" against them; a missing or stale sheet is flagged in the bundle's manifest (`look.status`) and
in the prompt, which asks for a SHOULD FIX line naming it.

## The colour legend (live and Remotion)

A video that gives colours meanings declares them in video.json, meaning to colour, each colour a
theme name of the video's engine (live: `hot`, `warm`, `cold`, `bad`, `good`, `log`, `key`, ...;
Remotion: `amber`, `ice`, `coral`, ...) or `#rrggbb`:

```json
"legend": {"request": "warm", "error": "bad", "focus": "hot"}
```

Tag each element drawn in a meaning's colour with that meaning. Live: any drawing call takes
`means` (`S.rect(k, x, y, w, h, {stroke: c.legend.request, means: 'request', box: 'request'})`;
`c.legend` maps each meaning to its CSS colour). Remotion: `Txt`, `Rect`, `Box`, `Token` and
`GhostCard` take `means="request"`; `MapView litMeans` tags a lit box and `CloseUp means` the
minimap's filled one. An element whose name contains the meaning's words (`box request`) needs no
tag. Only named elements are seen (live text by its key, a shape with `box`).

The engines' boxes (`studio boxes`) report each named element's `fill` and `stroke` as the browser
resolves them (`rgb(…)`; on Remotion a text's colour, a box's background and border) and its
`means`. `studio check` runs `legend` at its sample times, on the boxes the other checks gather, and
warns when one colour stands for two meanings, when one meaning is drawn in two colours, and when a
colour the legend reserves is on an element tagged with another meaning or none. Only accent colours
count: neutrals (ink, dim, faint, the panels, outlines and lines) are never reserved, and a blend
mid-transition or a tint (alpha under 0.5) is no colour. Each chapter's elements are kept per clip
key, so a check of the changed chapters still compares the whole video. With no legend the check is
silent, except for one line when elements carry `means` tags. A legend colour that is no theme colour
fails. Motion Canvas boxes carry no colours, so there only the legend itself is checked.

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
...)`, which runs on every frame with the clip time (the frame / fps, as in the other engines), so each
frame is still a pure function of time:

| | Remotion | Motion Canvas |
|---|---|---|
| text and boxes in stage units | `Txt`, `Rect` | `c.text`, `c.box` (or any Motion Canvas node) |
| map, token, ghost card, close-up | `MapView`, `Token`, `GhostCard`, `CloseUp` | `new MapView(c, nodes, edges)` then `map.update({visible, lit})`; `Token`, `GhostCard`, `CloseUp` likewise |
| pixel art | `PixelCanvas` | `pixelCanvas(c, w, h, palette, draw)` (the drawing helper and bitmap font are one shared file) |
| captured assets | `Shot` | `shot(c, file, at, h, {aspect, crop})` |
| footage edits | `Footage` | `footage(c, {aspect, fit})` |
| easing and springs | `ramp`, `spring`, `track`, `swapAlpha`, `loopT`, `rng`, `ease`, `keyed`, `follow`, `settle`, `wobble` | the same names (`keyed` defaults to `inOut`) |
| camera keys, header inset, close-up `accent`/`clip`/`bleed`, the look sheet | `Camera keys`, `frameOn`, `headerInset`, `studio look-sheet` | none: these are live and Remotion only |

Two things differ. Footage is transcoded once to a seekable WebM proxy (`.cache/mc-footage/`),
because Chrome's headless builds don't decode H.264; it is cached by modification time and seeks
frame-exact. And a scene must end at its clip's end: `studioScene` holds its last frame until then,
counting frames on the thread's `fixed` clock (its `time` is the exact sum of the waits, and drifts
from the frame count after `waitFor(0.7)`). A project needs one scene per clip in the timeline, so a
video with a placeholder chapter fails with "no scene number N": add each scene as its chapter is
written. A piece without narration gets its clips from video.json `clips` (`[{"id", "title",
"seconds"}]`), never from edits to timeline.json.

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
