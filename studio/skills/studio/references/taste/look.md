# The look: what a finished explainer looks like

These came from a learner's reactions to fourteen videos and two work projects, from the user's
notes on later ones, and from what people found when they studied what made generated motion design
look cheap. Each rule has its reason; keep the reason when you bend the rule. Motion and sound are
in `delight.md`, text on screen in `screen-text.md`, the narration in `narration.md`.

## Clean, with an identity

The learner compared a "cinematic" attempt with the best explainer channels, found it nowhere
close, and asked for something cleaner: diagrams, labels, narration that explains while the picture
shows. No title cards between chapters, no music, no decoration. Clean means no decoration; it does
not mean flat or silent. The subject's own events are performed (`delight.md`), and the biggest
single improvement in the work projects was giving the thing the video follows a visual identity:

- **A protagonist.** Give the thing the video follows (a request, a record, a payment) a token with
  a glyph that changes with its state, and keep it on screen. A proposed change can be a
  translucent "ghost" of it.
- **Real imagery beats illustration**: a screenshot, a real capture, a real location as a
  full-bleed background. Treat it as evidence: record its source and capture parameters.

This is the plain tone, and "fun" or "engaging" asks for it done well. A comic video (video.json
`tone: comic`, only on request) adds gags, acting and layered sound on top of these rules:
`comic.md`.

## Map and close-ups

The older rule, one diagram that builds up across the video with details beside it, produced
clutter: by minute eight one frame held a category list, a table, a record's fields and buttons.
"The macro view needs to be super clean."

- **The map** is the system overview: component names only, plus state (which box or arrow is lit,
  where the token is). The test: any text on the map that isn't a component name is a bug.
- The map's layout is fixed, but the frame isn't: the camera frames the boxes that exist so far
  and stays centred as boxes appear, so early chapters aren't top-heavy. When the layout has a
  header strip (a chapter label, a title), framing keeps it clear the way it keeps the band clear.
- **The camera moves on keys.** A push-in, a pull back, a pan or a move to frame a group is one
  declaration (`camAt` in live, `<Camera keys>` in Remotion; `../engines.md`), so it renders at any
  frame. The element the narration names stays in frame while it is named (`studio check` warns).
  The default minimap highlight is ice; a close-up's `accent` changes it only where the video gives
  the explained thing another colour.
- **A close-up** is one component or one record, full screen, opened from its box: the box lights
  just before the zoom (anticipation). A corner minimap has no labels and fills only the source
  box. The header is the item's name only: no breadcrumb, no subtitle.
- **Move toward what you introduce.** "This is the piece we want to read" over a still wide shot
  left the user asking to be taken there: when the narration singles something out, the camera goes
  to it (or it comes to the camera) before the sentence ends.
- Zooming back out returns to the same map with one state change. Nothing from the close-up stays.
- Hypothetical content is marked by the narration ("suppose", "if the reviewer approves"), not by
  tags or dashed outlines, which were tried and removed as clutter. A value on screen that is
  neither real nor framed as supposed is removed, not labelled.

## 3D, when the flat diagram hides something

Most explainers never need 3D: code, tables, equations, timelines, state machines, request flows,
comparisons and architecture maps read better flat, and a server drawn as a cuboid teaches nothing.
Use the live engine's 3D stage (`../engines.md`) only when this sentence is true: **"the viewer needs
to see ___, and the flat diagram hides it."** A mechanism whose parts sit behind each other, an
assembly taken apart, a stack of layers, a bond angle, an orbit's tilt, height on a map. If the blank
is "more cinematic" or "more alive", stay flat. A video about a physical object the user can hold (a
hard drive, an engine, a lock) often passes the test for its hero shots and fails it everywhere else.

- **Open from the diagram, flatten back to it.** Build the model in the diagram's own coordinates,
  open into depth on the cue where the narration needs it, and return to the same flat diagram with
  the one thing that changed (a ring that was a track is now a cylinder). The viewer should feel one
  picture turning, not two videos.
- **The same identity.** One colour legend for flat and 3D (a face takes its meaning's colour), the
  same protagonist, the same labels. Labels stay SVG text on projected points, upright and at least
  18 px, never painted onto a surface.
- **Three looks, chosen per chapter.** *Flat*, the house look: no lights, shadows, bloom, depth of
  field, textures or grain; faces in three tones of their colour, outlines in pixels with outer
  contours heavier than inner detail. It matches the diagrams it opens from and renders on any
  machine. *Lit*: the same 3D stage with `G.lit()` (`../engines.md`): light, soft shadows and
materials with roughness and metalness, still live and quick to iterate, for a mechanism that
should look like a thing. *Plate*: Blender renders the picture behind a live chapter (`../engines.md`, Plates), with
  real materials, light and shadow, for the few hero shots of a physical object the user wants to
  feel ("tactile", "realistic"); the labels and band stay live. A hard-drive film looked "not very
  3D" and "underwhelming" in the flat look, and its Blender plates were what the user liked. Every
  other chapter stays flat: a plate costs seconds a frame, and code, maps and diagrams gain nothing
  from it. When the user's own reference is more dimensional than the flat look (an isometric
  figure, a photo of the object), match the reference.
- **The camera moves to show a relation, then holds.** An orbit that reveals which part sits behind
  which earns its seconds; an orbit for its own sake does not. Stage camera moves and changes to the
  model as in 2D.
- **What is narrated can be seen.** A part the sentence names must show at the sentence's end and at
  its event: `studio check` warns (`occluded`) when one shows under 30%. Turn the camera or move the
  part, as a cutaway would, rather than leave the narration naming something hidden.
- **Geometry is a claim.** A model that looks precise is read as accurate. Build it from the
  evidence, keep it as simple as the explanation allows, and record where its numbers come from. An
  exaggerated scale (a gap widened so it can be seen) is said in the narration or shown against the
  true scale first: a widened gap with a small disclaimer taught a viewer that the head touches the
  platter.

## Colour

One meaning per colour for the whole video, declared in video.json `legend` (meaning → theme colour;
`../engines.md`): by default amber for cost or a number to watch, ice blue for the thing being
explained or the current selection, coral for failure, grey for idle. Tag what a meaning's colour
draws (`means`); `studio check` warns when a colour stands for two meanings, a meaning changes colour,
or a reserved colour appears on anything else, and the look sheet draws the legend. A colour used for
two things was the most common frame-review finding; in one video two colours swapped roles between
chapters. The kit's own accent states follow these roles and are tagged `kit`; tag a component with
`means` when the legend gives its colour another meaning.

## Line weight

Outer contours are heavier than inner detail: a box's outline is heavier than the dividers between
its fields, a table's outline heavier than its cell lines, a close-up's panel heavier than its
minimap. Equal weights flatten a diagram into a grid, and the eye can no longer find where one
thing ends. The kit's components follow it (live boxes 3 over 1.5 dividers; Remotion close-up 2 px
over a 1 px minimap as rendered, a table 3 px over single 1 px dividers); a lit or selected element
may be heavier still, since that weight is state, not structure. The look sheet shows it.

## The look sheet

The model sheet (`studio look-sheet`, `../engines.md`) is drawn at the look stage, before scenes:
every element in each of its states, in the video's theme and layout. Scenes draw what is on it; a new
element or state goes on the sheet first. The motion review checks drawings are on sheet.

## Banned defaults

These are the tells of generated design (from a study of 26 of them, and of what made "one prompt"
videos look alike). The craft critique hunts for them:

- labels on nearly every object, arrow and section; descriptions that repeat the heading;
  captions that explain an obvious illustration; title banners over a shot and footnotes under it;
- decorative icons beside every point, or an icon in a coloured rounded square atop every card;
- pills for everything; rounded cards inside rounded cards; coloured strips along box edges;
- purple gradients, glows, frosted glass over blur (a frosted caption band is allowed only over
  full-bleed imagery), a different background effect per section;
- oversized headings over tiny grey descriptions; widely spaced uppercase everywhere (keep it to
  one small chapter label); short labels separated by dots; a decorative dash before labels;
- every element entering with the same fade-and-slide; continuously moving background particles;
  thin lines with glowing dots travelling between boxes (the protagonist token moves only when the
  story says so, and it is the subject, not decoration);
- centred text on a gradient; corner labels and frame borders; blinking "live" dots; a centred
  headline over three equal cards.

## Length

Choose it from the learning brief and the deletion test in `../pedagogy.md`. Give longer arcs local
closure, and let a dense passage breathe: the user asked for more narration and longer holds around
an exploded view rather than fewer ideas. Keep optional reference separate from the main story;
engagement alone is not learning.
