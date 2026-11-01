# Screens: desktops, editors, terminals and browsers

Read this when a film shows people working at a computer: code typed in an editor, commands run in a
terminal, a product page or dashboard in a browser. The grammar comes from observability episode 1,
which built it by hand; the screens layer makes it the default for any screen film.

## The grammar

- **A desktop for a different kind of work, a tab for more of the same.** The laptop (editor and the
  shop's page side by side) is one desktop, the servers another, the product a third. A second
  server is a tab on the servers' desktop, not a new desktop.
- **Desktops sit side by side** on one wide stage with a strip of wallpaper (24 px) between them. A
  desktop switch slides the whole desk across with ease out (320 ms for the first, tightening to
  220 ms by the last, as the viewer learns the move). A tab switch snaps.
- **The camera goes out, across, in.** Around each switch it eases out to the whole desktop, slides
  rigidly, and eases back in to where the chapter was looking, so the viewer always sees the whole
  plate move and knows where they are. The dots under the desk say which desktop is shown.
- **A switch lands between sentences**, never under a spoken word, with a third of a second after it
  before the next word (`SETTLE`). `studio screens` moves each switch into the nearest gap within
  1.5 s and fails the check when there is none: move the cue or open a hold in the narration.
- **Typing has a human rhythm**: seeded bursts, faster inside a word, pauses after punctuation, never
  faster than 13 keys a second on average (faster reads as autotype). Enter has a breath before the
  output; long output streams a line at a time.
- **One meaning per colour**: the accent (green) for what works, the problem colour (coral) for what
  fails, and nothing else coloured. A pull-back to every desktop at once ends a chapter that moved
  between them.
- **Type stays legible**: window type sizes default to sizes that read at 1080p without a push-in;
  the legibility check samples every moment the screens change (each command, output and landing).
- Reconstructed product screens (a Datadog or Sentry page drawn from its docs) carry a small
  "reconstruction" label in `productFrame`; never pass off a drawing as a capture.

## data/screens.json

One log per film, shared by every chapter: the desktops, then what happens on them, in order.

```json
{
  "seed": "film",
  "desktops": [
    {"id": "laptop", "kind": "editor", "plate": "laptop", "frame": [0, 0, 0.6, 1], "grow": true,
     "title": "shop — editor", "files": {"shop.py": "data/shop/shop_v0.py"},
     "panel": {"title": "TERMINAL", "rows": 12, "size": 22}},
    {"id": "shop", "kind": "browser", "plate": "laptop", "frame": [0.6, 0, 0.4, 1], "light": true,
     "tabs": [{"id": "shop", "title": "Shop", "url": "localhost:8000", "page": "basket"}]},
    {"id": "servers", "kind": "terminal", "arrive": "s1-servers", "size": 36,
     "tabs": [{"id": "one", "title": "tea@one", "prompt": "tea@one:~$ "}]}
  ],
  "runs": {"grep": "data/runs/grep.json"},
  "actions": [
    {"at": "s1-run", "on": "laptop", "type": "python shop.py", "returns": false},
    {"at": "s1-print", "on": "laptop", "edit": {"file": "shop.py", "line": 20, "indent": 8, "text": "print(\"here\")"}},
    {"at": "s1-save", "on": "laptop", "save": true},
    {"at": "s1-checkout", "on": "shop", "click": "checkout", "page": "placed"},
    {"at": "s1-servers", "switch": "servers"},
    {"at": "s2-grep", "on": "servers", "type": "grep 1004 shop.log", "run": "grep"}
  ]
}
```

**Desktops.** `id`; `kind` is `editor`, `terminal` or `browser`. Windows that name the same `plate`
share one desktop, each in its `frame` [x, y, w, h] as fractions of it; `grow` lets a window take
the whole desktop when it is alone there. `arrive` names the cue a desktop appears at (before it, it
is not on the desk). `title`, `size` (type size), `light` (a paper window), `tabsAlways` (show the
tab strip with one tab). An editor has `files` (name to text, or a path from the video folder) and
an optional terminal `panel` {title, name, rows, size, prompt}. Terminals and browsers have `tabs`
{id, title, prompt | url, page}.

**Actions.** Each has `at` (a cue name, or a number in film seconds), optional `off` (seconds after
the cue) and one verb:

| verb | on | what it does |
|---|---|---|
| `type` | window | types the text at the prompt (or the editor's panel), Enter, then `run` (a captured run's output) or `output` (lines); the prompt comes back once the last output line is in (at once for a command ending in `&`, or with `returns: true`); `returns: false` for a server or `tail -f`: the prompt stays away until `clear`; `enter: false` types without Enter; `speed`, `lead`, `pause`, `breath`, `stream` tune the rhythm |
| `edit` | editor | {file, line, text, mode}: `insert` (default) a new line below `line` with `indent` spaces, `replace` the line keeping its first `keep` characters, or `append` to it |
| `save` | editor | Cmd-S: the dirty dot clears |
| `open` | editor, browser | a file (editor; optional `line`), or {url, page, title} (browser) |
| `tab` | terminal, browser | snaps to tab `tab`; `new` {title, prompt or url, page} opens it first |
| `switch` | (a desktop) | slides to that desktop; `snap: false` keeps it on the cue exactly (and fails the check if that is under a word) |
| `click` | browser | the pointer travels to page target `click` and presses; `page`, `url` change the page |
| `drag` | browser | presses on `drag` and drags `from` → `to` (fractions of the target) over `dur`; the selection is the tab's |
| `page` | browser | the tab shows another page, no pointer |
| `output` | terminal | lines appear without a command (a log being written) |
| `clear`, `split`, `unsplit`, `close`, `show` | window | clears a terminal; splits it; closes or shows a window |
| `point` | window | underlines a target and dims the rest of the window, whole on the cue; `until` (a cue) or `for` (seconds, default 2.5); `dim` |
| `mark` | window | puts an outcome mark after a target: `state` is `running`, `finished`, `failed`, `cancelled` or `none` (removes it) |

Keep captured runs ({argv, stdout, stderr, exit}) as files under data/runs/ and real source
versions under data/: the screen shows what the program actually prints.

`slide` {first, last} changes the slide lengths, `maxKeys` the autotype ceiling, `look` any colour
of the default look (screens-draw.js `LOOK`), and `sounds` the sound kit files each kind uses.

## A chapter

```js
import { loadScreens, screensAt, screensCamera, drawScreens } from '@studio/screens-draw.js'
const scr = await loadScreens(import.meta.url)          // data/screens.json, its files and runs

export default function draw(c) {
  const s = screensAt(c, scr)                            // every window's state at this frame
  screensCamera(c, scr, s, [[0, 'whole'], [4.2, {window: 'servers', pad: 20}], [9, 'all']])
  drawScreens(c, scr, s, {pages: {basket, placed: basket}})
}
```

`screensCamera` keys are [clip seconds, target, ease?]; a target is `'whole'` (the desktop shown
then), `'all'` (the pull-back), `{on, region: [x0, y0, x1, y1]}` in that desktop's pixels,
`{window, pad}` or a plain `{x, y, z}`. It never shows wallpaper outside a slide or a pull-back.
A browser page is `page(c, box, tab, ctx)`, drawn in world pixels inside `box`; it returns
`{targets: {name: [x, y, w, h]}}` so clicks, drags, points and marks know where to go. `tab.clicked`,
`tab.selected` and `tab.since` say what has happened on it. `drawScreens` returns each window's box
for annotations on top; window boxes are named `scr:<id>` for the checks. The template is
`templates/live/scenes/example-screens.js`.

## Pointing and outcome marks

The narrator names a thing and the screen shows which one: point on the word, act in the pauses
(`taste.md`, "Perform the hero moments"). A `point` puts its cue on the word, a `phrase` anchor in
cues/<clip>.json; the underline draws in over the 0.2 s before it and is whole as the word is said,
while the rest of the window dims (a veil in the window's own background). One point a window at a
time: a newer one takes over. A `mark` is an act, so its cue sits in the pause after the sentence
(an `end` anchor with an offset). Marks stay until replaced: running spins, finished is a tick in
the accent, failed a cross in the problem colour, cancelled a dash.

A target is named the way the window draws things:

- editor: `{"line": 12}`, `{"line": 12, "text": "stock.take"}` or `{"text": "stock.take"}` (the first
  line showing it); `{"panel": true, "text": "…"}` in the terminal panel;
- terminal: `{"text": "…"}`, the newest row showing it;
- browser: a page target's name. A page target may be `{box: [x, y, w, h], line: [x0, x1]}` when the
  underline should run under part of it (a trace row: label and bar lit, the line under the bar).
  Pages get the window's marks in `ctx.marks`, so a failed row can turn the problem colour itself.

A target scrolled out of view draws nothing. `"outcomeSounds": true` at the top of the log adds two
generated sounds, `finished` and `failed` (sfx.py voices), on their marks; they are a trial, off by
default, and judged by ear in a cut. The template is `templates/live/scenes/example-pointing.js`.

## Overlays and page parts

`c.kit` (or `@studio/pages.js`) has the explaining overlays and the parts of product pages:

- `defCard(c, key, {term, def, tools, t0, t1, diagram, diagramH, variant, focus})`: the definition
  card, when a core term first matters. `variant` is one of `CARD_VARIANTS`: `blur` (the default and
  episode 1's: the scene blurs behind a centred card), `side` (a panel over the right third, scene sharp),
  `lower` (a strip above the captions), `spotlight` (all dims but `focus`) or `type` (the term typed
  large on the wall). Start it in a pause or on the defining sentence's first word.
- `progressStrip(c, stages, current)` and `checklist(c, items, ticks)`: where the film is.
- `productFrame(c, key, box, {product, title, recon})` with `timeSeries`, `table`, `waterfall`,
  `pointPlot` (drag selection) and `rankedList` (rows reorder) inside it, all from data, so a page
  shown in three chapters is one page.

## Sound and checks

`studio screens VIDEO` replays the log in node and writes one key-tick stream per action into
audio/sfx.json (each character, Enter, the chords of a tab, desktop switch or save, clicks and a
drag's press and release), marked `"source": "screens"`; it keeps other effects. Run it after
changing the log or the timeline. The sounds follow the permitted-sound rule in `taste.md`: keys and
clicks that are performed, nothing on an abstraction; the outcome sounds only when the log asks.

`studio check` runs the `screens` check whenever data/screens.json exists: a name the log doesn't
declare, a switch with no gap, an action before its desktop arrives, or stale sounds fail; a line
that has to wrap inside a token at its window's width, or typing over the autotype ceiling, warns.
