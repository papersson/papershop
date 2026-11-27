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
| a yes or no about one thing | `text` with `verdict: 'yes'` or `'no'`; about a part of a piece (an entry, a row), the piece draws the mark on that part | appearing beside the thing |
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
When the change is inside the piece (one bucket, one row), the piece lights that part itself and
fades the rest, from a class token such as `focus:5`, so the brightness lands exactly where the
change is. Give parts a data attribute (`data-entry="5.1"`) for the rare click that still needs
`highlight: '[data-entry="5.1"]'`, the ring. A group arrives one item at a time (a stagger): tree
rows, card fields and code lines do it by themselves when their object appears. In a custom piece,
add the class `w-part` to each item for the same, or stagger a class change with a CSS variable per
element (`style.setProperty('--i', i)`) and `transition-delay: calc(var(--i) * 110ms)`: one
change, read as one gesture. `assets/example/page.html` has a complete one.

Do not build pieces for data nobody has asked to explain yet.

## Layout zones on the 1600 by 900 stage

| Zone | Where |
|---|---|
| objects | y 80 to 740, x 80 to 1520 (no chapter title takes the top) |
| caption | one line centred at y 772, 1400 wide |
| count | bottom right corner |

The checker reports object text in the caption band (y 756 to 836), text off the stage, text
overlapping other text, text under 20 px on the stage, and labels over four words. It also reports
a subject smaller than 0.2% of the stage (about a short chip) and a subject more than 480 px from
the last one that did not travel there. Leave the left third for what is being made (a key and its hash) and the
right for where it goes (the table), so motion reads left to right.

## Colour

- `--ink` for data. It is the brightest thing on the stage.
- `--dim` for names, labels and chrome. `--faint` for lines and rules.
- Three meaning colours, `--a`, `--b`, `--c` (classes `tone-a` and so on). Give each a meaning once
  per page and keep it: in the example, `--a` is a key, `--b` is a stored value, `--c` is a bucket
  number.
- `--hi` means "what changed" and nothing else: a lit row, a lit line, the marker, the rare ring.
- Brightness is the pointer. The engine draws the click's subject at full ink, the previous
  subject at the second tone (0.6) and everything else quiet (0.32), so do not set opacity to
  point. `with: [id]` on a click holds an object the subject must be read against at the second
  tone; `context: true` on an object keeps a frame of reference quiet for good.
- `--yes` and `--no`, green and red, for verdicts only.
- One sans stack (`system-ui` and friends) and one mono stack. No gradients, no shadows, no
  decoration. A surface (`--tint`) only when a value needs to read as one thing.

## Motion

Objects move with `transform` and `opacity` over 0.9 s on `cubic-bezier(.4, 0, .2, 1)`, fading in
0.5 s. Objects appearing as a chapter opens wait 0.5 s for the old ones to fade. A ring, when a
click names one, arrives after `settle` (by default the motion's length plus a beat, longer for a
group that staggers in). Raise `settle` on a click whose custom piece runs a longer staggered motion. `prefers-reduced-motion` jumps instead of moving.
