# The visual system

These are the rules that make a cartograph diagram look *designed* rather than generated. They are
already baked into `templates/renderer.html`; this file explains them so the spine stays coherent if
you ever extend it, and so the extracted *model* is shaped to render well. The order is roughly the
order in which a choice matters.

## Five non-negotiables (the load-bearing ones)

1. **No legends. Direct-label instead.** A legend forces the eye to leave the mark, decode a key, and
   come back. Put the meaning *on the mark*: an edge's value is written along the edge (`at-least-once`,
   `gRPC`, `eventual`), coloured to match, so colour and text are redundant and decode in place. A
   node's class is a tag on the node. The only "key-like" thing allowed is the **toggle control**,
   which names the active *dimension* — never a swatch box.

2. **The diagram fills the viewport.** One slim top bar (wordmark + controls), then the canvas takes
   all remaining height (`flex:1`, SVG `width/height:100%`, `preserveAspectRatio` meet). No page
   scroll, no hero header, no lede paragraph, no footer. The graph is the product; everything else is
   overhead to be minimised.

3. **One global layer at a time.** Scanning the whole graph for a property (delivery, consistency,
   criticality, durability, team) is a *recolour*, and exactly one may be active. Painting several at
   once rebuilds the hairball the diagram exists to avoid. The base (transport colour + sync/async line
   style + team on nodes) is always on; everything else is a single mutually-exclusive toggle.

4. **Local drill = all facets at once.** The correlated "if I touch X, who breaks, on what contract,
   into what store?" question is answered by clicking one element and co-rendering *everything* about
   it — because it is scoped to one element, it is free. Global scanning is one-dimension; local
   inspection is all-dimensions. Keep that split sharp.

5. **Lineage is first-class.** Data derivation is its own graph (fields, not services) and its own
   view, not a layer. Clicking a field traces upstream sources and downstream consumers. This is often
   the most valuable view; treat it as a peer of the Map, not a bonus.

Self-evident channels stay bare: arrowheads carry direction, dashed = async. Don't label what the form
already says.

## Palette & tokens

Warm, paper-like, restrained. Dominant neutral with a few semantic accents — never an even rainbow.

```
--paper #FAF7F1   --card #FFFDF8   --ink #211E1A   --muted #8A8377   --hair #E3DCCE
roles:   client/edge teal #0E8388 · svc indigo #3A47B0 · async/broker violet #7A4FBF · store amber #B5641F
status:  good/live green #2E7D52 · warn amber #C97A12 · error red #C0392B
```

Colour means one thing at a time and is reused consistently across views (a service is the same colour
in the Map, the Sequence, and the drill). Node fills are pale tints of the role colour; strokes are the
role colour. Edges are ink at rest and take the active layer's colour when scanning.

Transport colours (the always-on base): `rest` teal · `grpc` indigo · `kafka/avro` violet · `sql` amber
· `bytes` brown · `cache` ochre.

## Typography

Two families, both from the **system stack** (no web fonts — the file must make zero network requests):

- **Display / headings / state names** — a system serif with character: `"Iowan Old Style", Palatino,
  Georgia, ui-serif`. This is the one place personality lives.
- **Everything technical** — a monospace: `ui-monospace, "SF Mono", Menlo`. Labels, tags, edge values,
  schemas, captions. Mono signals "this is a precise machine fact."
- **UI chrome** — `system-ui` sans for buttons.

Never Inter/Roboto/Arial, never a Google Fonts `<link>`. The serif+mono pairing is most of the
"designed" feel.

## Layout

- ViewBox `1280 × 720` for Map / Sequence / Lifecycle; `1340 × 700` for Lineage.
- **Place nodes by data-flow**, not alphabetically: sources top-left, sinks bottom-right, the event bus
  as a horizontal spine in the middle. Group by role into bands. ~150px between node centres.
- Edges are gentle cubic béziers biased toward the dominant axis (horizontal-dominant edges curve
  horizontally), so they read as routed, not scribbled. Give a node enough breathing room that its edge
  labels don't collide.
- The event bus is one wide bar (`bus:true`); producers drop into it from above, consumers draw from
  below — this tames a dozen async edges into one legible spine.
- Lineage is strict left-to-right columns; never let two columns share an x, and size each field box to
  its text so tags never overlap labels.

## Motion (restrained, accessible)

- Entrances and state changes use a single ease-out curve `cubic-bezier(0.23, 1, 0.32, 1)`; durations
  ~200–280ms. The drawer slides; the spotlight dims. Nothing bounces.
- Hover is decorative and gated (`@media (hover:hover)`); click *pins*.
- **Honour `prefers-reduced-motion`**: replace transforms with opacity, drop the slide. Never animate a
  keyboard-frequency action.

## What keeps it from looking generated

- No legend, no title hero, no "Overview / Key" boxes, no purple-on-white gradient, no emoji.
- Generous quiet (the dot-grid canvas) around a dense, legible graph — density where the information
  is, calm everywhere else.
- One confident accent per state, consistent across views; restraint over decoration.
- Direct labels in mono with a paper halo (`paint-order:stroke`) so text stays legible over edges and
  grid without boxes.

## Taming a dense graph

The data-flow placement above gets you a clean small graph. A real 15-20 node graph with a busy edge
set turns into a hairball, and the auto-router alone won't save it. These are the moves that work
(layout-level, so they're fair game in the editorial pass — see SKILL.md):

- **Suppress the dominant label; show only exceptions.** If one transport (often REST) is on most edges,
  labelling all of them is noise. Set `meta.suppressLabel: ["REST"]` (general — any dominant value) so
  the renderer omits those labels and draws only the *exceptions*, which is the information.
- **Calm the resting state.** Lower resting-edge opacity so the graph reads as quiet until hover/scan
  brings an edge forward. Density where the information is, calm everywhere else.
- **Tier the strokes.** A two-tier stroke (heavier for P0/critical, lighter for the rest) gives the eye
  a spine to follow without a colour layer.
- **Spine over bus when async is light.** The wide event-bus bar earns its place only with real
  fan-out; with a handful of async edges, a central-spine arrangement reads cleaner. Drop the bus node.
- **Place by data-flow, not by category** — sources top-left, sinks bottom-right; let the model carry
  good `x,y` (auto-layout is a fallback, not the goal).

This suppresses a *label*, not an edge; hiding whole edges is a separate concern and out of scope.
Real edge *routing* (beyond axis-biased béziers) is a larger effort — its own finding if you need it.

## Rendering details not to regress

A few spine decisions are deliberate; a future edit should preserve them:
- **One arrowhead marker**, fill `context-stroke`, so the head inherits each edge's stroke including the
  active-layer recolour. Don't reintroduce per-colour markers (the head/line will diverge under a layer).
- **Nodes size to their text** (canvas `measureText` in `nodeWidth()`); never go back to a fixed width.
- **Lineage boxes and the sequence divider** size/position from content and the model, not constants.

## Extending the spine — logic vs. layout

The invariant is about *logic*, not *layout* (SKILL.md). So:
- **Hand-tuning layout** (placement, de-clutter, routing) is a sanctioned editorial pass, not a
  violation — do it, and record what you tuned.
- **A capability the model genuinely can't express** (a new semantic the renderer would need *branching*
  for) is a **finding**: grow the spine (renderer + MODEL.md) so *every* project gets it, rather than
  forking the renderer for one project. Document why the model couldn't express it.

The goal stands: every project is a new *model*. The renderer grows only when a missing capability is
general — and then it grows once, for all.
