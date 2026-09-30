---
type: llm
weight: 3
---

PASS if the response treats this as PIXEL ART with real constraints: a fixed logical grid drawn on a canvas and scaled by a whole number with nearest-neighbour, a small fixed palette chosen first, movement on whole pixels, text from a bitmap font so it stays on the palette, and checks that the output is on-grid and on-palette.
FAIL if it plans anti-aliased, fractionally scaled or freely coloured graphics.
