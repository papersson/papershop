# Pixel art

A retro look with real constraints: a fixed logical grid, a limited palette, and whole-number
scaling. `studio new NAME --genre pixel` (with a script and narration) or `--duration N` (silent).
video.json holds `"pixel": {"grid": [320, 180], "palette": ["#0f1318", ...]}`.

## How it is drawn

`PixelCanvas` draws the grid on a canvas and scales it by a whole number with nearest-neighbour, so
every logical pixel is an exact k×k block (320×180 at 5× fills a 1920×920 stage at 1600×900).
`draw(px, t)` paints the whole frame from the clip time: a pure function of time like every scene.
`Pixels` has `clear`, `rect`, `dot`, `sprite(rows, x, y, legend)` and `text`, all rounding to whole
pixels, so nothing moves by a fraction of a pixel. `text` uses a built-in 3×5 bitmap font
(upper-case, digits, common punctuation), so text stays on the palette; the browser's own text would
be anti-aliased and off it. Sprites are rows of characters with a legend to palette names.

## Rules that `studio check` enforces

- **grid**: the canvas's output is whole k×k blocks: crop it, scale down and back up with
  nearest-neighbour, and it must not change. A fractional scale, blur or sub-pixel motion fails.
- **palette**: every colour on the canvas, read at its logical resolution, is in the palette.
  Anti-aliased fills and colours typed in by hand fail.
- The usual ones too: the band, bounds, legibility, determinism.

## Craft

- Choose the palette first: a background, an ink, one accent for the thing the video follows, one for
  cost or warning, a dim for structure. Fewer colours read better than more.
- Move on whole pixels and at a rhythm: step animations (a sprite falls 12 px in a few frames and
  rests) read as pixel art; eased sub-pixel drift doesn't.
- Text sizes are multiples of the font's grid (`scale` 2 or 3 for headings). Keep captions in the
  caption band, which is drawn at full resolution, not on the canvas.
- Big pieces: scenes are functions of time, so an animation of a hundred sprites is a loop over an
  array with `time` deciding each one's state.
