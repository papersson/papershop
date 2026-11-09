# Visuals: which piece for which data, where things go, and colour

The page format and every piece's options are in the header comments of `engine/walk.js`. This file
is about choosing.

## Which piece

| The data | The piece | Moves by |
|---|---|---|
| one value: a key, a hash, a path, a count | `chip` (label names it, value in mono) | gliding from where it is made to where it is used |
| a record with named fields | `card`, with chips docking into `Walk.slot(card, state, field)` | a chip taking a slot (add class `no-label`) |
| nested data: JSON, a config, a protobuf message | `tree` with `data` or `text` (protobuf text format) | `at:PATH` marker walking rows, `lit:PATH`, `box:PATH` |
| code, usually the last chapter | `code` with `[mark, line]` margin numbers | `lit:3-5` lighting lines and dimming the rest |
| a yes or no about one thing | `text` with `verdict: 'yes'` or `'no'` | appearing beside the thing |
| a measured number with its name | `text`, larger `size` | appearing |
| a structure with its own shape: a table of buckets, a queue, a grid, a timeline | a custom piece | classes the piece's CSS transitions |

A custom piece is one function that renders once and returns an update for its classes:

```js
Walk.piece('buckets', (el, object, page) => {
  // build rows from object.fruit, using page.make(tag, cls, parent, html) and page.esc(text)
  return cls => { /* toggle row classes from tokens like 'focus:5' */ };
});
```

It stays one object, so filling it, lighting a part or fading the rest is one change per click.
Give the parts it will point at a data attribute (`data-entry="5.1"`) so a click can aim the ring
with `highlight: '[data-entry="5.1"]'`. Stagger a group's motion with a CSS variable per element
(`style.setProperty('--i', i)`) and `transition-delay: calc(var(--i) * 110ms)`: one change, read
as one gesture. `assets/example/page.html` has a complete one.

Do not build pieces for data nobody has asked to explain yet.

## Layout zones on the 1600 by 900 stage

| Zone | Where |
|---|---|
| chapter title | top left, x 80, y 40 to 110 |
| objects | y 140 to 740, x 80 to 1520 |
| caption | one line centred at y 772, 1400 wide |
| count | bottom right corner |

The checker reports object text in the caption band (y 756 to 836), text off the stage, and text
overlapping other text. Leave the left third for what is being made (a key and its hash) and the
right for where it goes (the table), so motion reads left to right.

## Colour

- `--ink` for data. It is the brightest thing on the stage.
- `--dim` for names, labels and chrome. `--faint` for lines and rules.
- Three meaning colours, `--a`, `--b`, `--c` (classes `tone-a` and so on). Give each a meaning once
  per page and keep it: in the example, `--a` is a key, `--b` is a stored value, `--c` is a bucket
  number.
- `--hi` means "what changed" and nothing else: the ring, a lit row, a lit line, the marker.
- `--yes` and `--no`, green and red, for verdicts only.
- One sans stack (`system-ui` and friends) and one mono stack. No gradients, no shadows, no
  decoration. A surface (`--tint`) only when a value needs to read as one thing.

## Motion

Objects move with `transform` and `opacity` over 0.9 s on `cubic-bezier(.4, 0, .2, 1)`, fading in
0.5 s. Objects appearing as a chapter opens wait 0.5 s for the old ones to fade. The ring arrives
after `settle` (by default the motion's length plus a beat). Raise `settle` on a click whose piece
runs a longer staggered motion. `prefers-reduced-motion` jumps instead of moving.
