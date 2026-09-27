"""The lesson's shared picture and helpers: one diagram that builds up across the chapters, with a
fixed geography and one meaning per colour. Every scene imports this; keep anything used by two
scenes here, so the picture cannot drift between chapters.

Colour roles (write the lesson's own here; keep one meaning per colour for the whole video):
  ICE   the thing being explained / the current selection
  AMBER cost, or a number the viewer should watch
  CORAL a failure (BAD)
  MUTED labels, FAINT guides, INK ordinary text
"""
import json

from common import *

DATA = LESSON_DIR / "data"


def load(name):
    """A data file the sims wrote: every number on screen comes from here, never from a literal."""
    p = DATA / name
    return json.loads(p.read_text()) if name.endswith(".json") else p.read_text()


def code_card(lines, size=17, title=None):
    """A block of code or terminal text: [(indent, text, color)], indented by measured width so
    Manim's dropped leading spaces don't flatten it."""
    rows = VGroup()
    unit = mono("x", size, INK).width
    for indent, text, color in lines:
        t = mono(text, size, color)
        t.shift(RIGHT * indent * 4 * unit)
        rows.add(t)
    rows.arrange(DOWN, buff=0.12, aligned_edge=LEFT)
    for (indent, _, _), t in zip(lines, rows):
        t.shift(RIGHT * indent * 4 * unit - RIGHT * (t.get_left()[0] - rows.get_left()[0]))
    box = RoundedRectangle(corner_radius=0.12, width=rows.width + 0.6, height=rows.height + 0.5,
                           stroke_color=TRAY_EDGE, stroke_width=1.5, fill_color=PANEL, fill_opacity=1)
    box.move_to(rows)
    g = VGroup(box, rows)
    if title:
        g.add(label(title, 13).next_to(box, UP, 0.1).align_to(box, LEFT))
    return g
