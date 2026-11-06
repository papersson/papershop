# The light layer (c.L)

For a picture of scale that a few SVG shapes cannot show: traffic on the world's cables, a zoom from
one home out to the planet, the dozens of requests behind one page, a whole evening's traffic. One
request between two boxes stays SVG. The worked example is `templates/live/scenes/example-light.js`.

## What it draws

`c.L` is a WebGL2 canvas under the 3D canvas and the SVG stage, made the first time a scene asks for
it and hidden on a frame that draws no light.

- `L.point(x, y, r, colour, op)`: a round light at world (x, y), radius `r` in world units, so it grows
  with a push-in. Under about a pixel it keeps its size and dims instead of vanishing.
- `L.line(ax, ay, bx, by, w, colour, op)`: a line of light, `w` screen pixels wide at any zoom.
- `L.look({bloom, soft, minPx, ground})`: this frame's look. `bloom` 1 (0 is none), `soft` 0.85 (a
  point's edge), `minPx` 1.2 (the smallest point), `ground` a colour or `[top, bottom]` for a
  vertical gradient (default `var(--bg)`).
- `L.count()`: how many points and lines this frame drew.

A colour is a theme name (`'cold'`, `'hot'`), `var(--name)`, `#rrggbb` or any CSS colour. Light adds
up, so crowded places glow; a soft bloom and a shoulder towards white keep bright cores from
clipping, and a fixed dither keeps the dark gradients from banding after a video encode.

## How it fits the frame

- Same world as the SVG. Points and lines use the coordinates the scene's SVG uses and go through
  the camera the SVG ends the frame with (`S.cam`, `c.camAt`, shots, a match cut), so a label drawn in
  SVG sits on its light. Light drawn inside a nested scene (a join's incoming chapter, a callback)
  follows that scene's camera, inset and opacity, and a dissolve fades the outgoing chapter's light
  with its SVG.
- It paints the background. Light can only add to what is under it, so the layer paints the ground
  itself; a scene that uses it draws nothing opaque in the SVG's back layer. Where there is no light
  the ground is exactly the theme's `--bg`, so a cut to a frame without light shows no seam. Anything
  the SVG draws on top with a fill covers the light under it: keep fills over light faint.
- One backdrop per frame. The 3D stage's canvas is opaque and sits above the light, so a frame uses
  `c.G` or `c.L` as its backdrop, not both.
- A pure function of time. Fill it from `t` and fixed seeds (`kit.rand`, `kit.rng`), never
  `Math.random` and never state kept between frames, so any frame draws alone and repeats exactly.

## Cost and encodes

Tens of thousands of points a frame are cheap on a GPU. Without one, Chrome draws in software
(`studio doctor` names the renderer): a frame of 36,000 points can take up to a second there, so
render long light chapters on a machine with a GPU (video.json `gl`). Very fine specks blur away in a 1080p encode at YouTube's rates: for a film, prefer
fewer, larger lights, and look at an encoded frame at full size before calling a shot done.

## Use it with care

Light is beautiful, which is its risk: the director has called a moving river of light "too
elegant/poetic for the subject matter". Keep the picture as plain as the subject (`taste.md`), keep
warm for the one thing the viewer follows, and say in the narration what the light stands for.
