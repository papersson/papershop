"""Shared look and timing for every scene.

Palette, fonts (set 4x and scaled down, which fixes Pango's kerning at small sizes), the amber
counter, and CueScene, which times a scene against the narration's sentence ids. Amber is reserved
for cost, ice marks the current selection, coral marks failure.
"""
import json
import math
from pathlib import Path

import numpy as np
from manim import *

import os
from xml.etree import ElementTree as _ET

import svgelements as _se
from manim.mobject.svg.svg_mobject import SVGMobject as _SVGMobject


def _generate_mobject(self):
    """Manim's own version writes the modified SVG to a temp file named after the text's hash and
    deletes it after parsing. Scenes render in parallel processes, so two processes rendering the
    same text raced on that file (FileNotFoundError). Same steps, with the process id in the name."""
    file_path = self.get_file_path()
    new_tree = self.modify_xml_tree(_ET.parse(file_path))
    tmp = file_path.with_name(f"{file_path.stem}_{os.getpid()}{file_path.suffix}")
    new_tree.write(tmp)
    svg = _se.SVG.parse(tmp)
    tmp.unlink(missing_ok=True)
    mobjects, mobject_dict = self.get_mobjects_from(svg)
    self.add(*mobjects)
    self.id_to_vgroup_dict = mobject_dict
    self.flip(RIGHT)
    return self


_SVGMobject.generate_mobject = _generate_mobject

# A lesson's scenes live in <lesson>/scenes/; the build passes the lesson folder in LESSON_DIR.
ROOT = Path(os.environ.get("LESSON_DIR", Path.cwd().parent)).resolve()
DATA, AUDIO, CAPTURES = ROOT / "data", ROOT / "audio", ROOT / "captures"

BG = "#0F1318"
INK = "#E6EBF0"
MUTED = "#8C97A4"
FAINT = "#56606B"
DIM = "#2B333C"
PANEL = "#151B22"
TRAY_FILL = "#17202A"
TRAY_EDGE = "#C9D3DD"
AMBER = "#F2A93B"
ICE = "#8FD3FF"
IDLE = "#3E4750"

SANS = "IBM Plex Sans"
MONO = "IBM Plex Mono"

config.background_color = BG

# --- value colors: seaborn "mako", trimmed so the darkest cards still read on BG
_MAKO = None


def vcolor(x):
    global _MAKO
    if _MAKO is None:
        import seaborn as sns
        _MAKO = sns.color_palette("mako", as_cmap=True)
    r, g, b, _ = _MAKO(0.22 + 0.74 * float(np.clip(x, 0, 1)))
    return ManimColor.from_rgb((r, g, b))


def ink_on(x):
    c = vcolor(x).to_rgb()
    lum = 0.2126 * c[0] ** 2.2 + 0.7152 * c[1] ** 2.2 + 0.0722 * c[2] ** 2.2
    return BG if lum > 0.28 else INK


# Pango lays out small sizes with broken kerning, so text is set 4x large and scaled down.
# Manim renders text into a canvas as wide as the video (Text) or 600 px (MarkupText) and
# wraps at that width; at 4x that wraps ordinary lines, so give Pango a wide canvas instead.
_K = 4

import manimpango
from manimpango import MarkupUtils

_text2svg = manimpango.text2svg
_markup2svg = MarkupUtils.text2svg


def _wide_text2svg(settings, size, line_spacing, liga, file_name, sx, sy, w, h, orig, pango_width=None):
    return _text2svg(settings, size, line_spacing, liga, file_name, sx, sy, 16000, 4000, orig, None)


def _wide_markup2svg(text, font, slant, weight, size, ls, liga, file_name, sx, sy, w, h, **kw):
    kw["pango_width"] = None
    return _markup2svg(text, font, slant, weight, size, ls, liga, file_name, sx, sy, 16000, 4000, **kw)


manimpango.text2svg = _wide_text2svg
MarkupUtils.text2svg = staticmethod(_wide_markup2svg)


def T(s, size=30, color=INK, font=SANS, weight=NORMAL, **kw):
    return Text(s, font=font, font_size=size * _K, color=color, weight=weight, **kw).scale(1 / _K)


def M(s, size=30, color=INK, font=SANS, weight=NORMAL, **kw):
    return MarkupText(s, font=font, font_size=size * _K, color=color, weight=weight, **kw).scale(1 / _K)


def label(s, size=20, color=MUTED):
    """Small uppercase label."""
    return T(s.upper(), size, color, font=MONO, weight=MEDIUM)


# --- the trip counter --------------------------------------------------------------
class Counter(VGroup):
    """Amber number with a small label. Animate with `counter.to(n)`."""

    def __init__(self, value=0, title="TRIPS", size=44, anchor=None, color=AMBER, **kw):
        super().__init__(**kw)
        self.color = color
        self.tracker = ValueTracker(value)
        self.size = size
        self._cache = {}
        self.title = T(title, size * 0.38, MUTED, font=MONO, weight=MEDIUM)
        self.anchor = np.array(anchor if anchor is not None else [6.55, 3.3, 0])
        self.num = self._text(value)
        self._place()
        def update(m):
            m.become(self._text(int(round(self.tracker.get_value()))))
            self._align(m)
        self.num.add_updater(update)
        self.add(self.title, self.num)

    def _text(self, v):
        if v not in self._cache:
            self._cache[v] = Text(f"{v:,}", font=MONO, font_size=self.size, color=self.color,
                                  weight=MEDIUM)
        return self._cache[v].copy()

    def _align(self, m):
        m.next_to(self.title, DOWN, buff=0.08, aligned_edge=RIGHT)

    def _place(self):
        self.title.move_to(self.anchor, aligned_edge=RIGHT)
        self._align(self.num)

    def to(self, n, **kw):
        return self.tracker.animate(**kw).set_value(n)

    def value(self):
        return int(round(self.tracker.get_value()))


# --- scene with narration cues -----------------------------------------------------
_TIMINGS = None


def timings():
    global _TIMINGS
    if _TIMINGS is None:
        _TIMINGS = json.loads((AUDIO / "timings.json").read_text())
    return _TIMINGS


class CueScene(Scene):
    SEG = None

    def setup(self):
        seg = next(s for s in timings()["segments"] if s["id"] == self.SEG)
        self.t0, self.dur = seg["start"], seg["end"] - seg["start"]
        self.cues = {l["id"].split("_")[1]: (l["start"] - self.t0, l["end"] - self.t0)
                     for l in seg["lines"]}

    def now(self):
        return self.renderer.time

    def until(self, t):
        dt = t - self.now()
        if dt > 1 / 60:
            self.wait(dt)

    def at(self, lid, dt=0.0):
        self.until(self.cues[lid][0] + dt)

    def end_of(self, lid, dt=0.0):
        return self.cues[lid][1] + dt

    def start_of(self, lid, dt=0.0):
        return self.cues[lid][0] + dt

    def finish(self):
        self.until(self.dur)


def chip(text, color=MUTED):
    """Top-left section marker."""
    return label(text, 20, color).to_corner(UL, buff=0.45)




CORAL = "#E4715F"


def mono(s, size=20, color=INK):
    return T(s, size, color, font=MONO)
