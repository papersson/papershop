"""The palette's legibility rules, computed from the engines' own theme files."""
import re

import pytest

from studio_kit.check import contrast_ratio
from studio_kit.env import engine_dir

MIN_GRAPHIC = 3.0      # WCAG's non-text contrast: a line that carries meaning, against what it is drawn on


def rgb(hex_):
    return tuple(int(hex_[i:i + 2], 16) for i in (1, 3, 5))


def consts(path):
    return {k: rgb(v) for k, v in re.findall(r"export const (\w+) = '(#[0-9A-Fa-f]{6})'", path.read_text())}


def css_vars(path):
    return {k: rgb(v) for k, v in re.findall(r"--([\w-]+): (#[0-9A-Fa-f]{6})", path.read_text())}


def test_the_live_boards_arrows_stand_out_too():
    colours = css_vars(engine_dir("live") / "src/theme.css")
    (idle,) = set(re.findall(r"S\.line\(k, x1, y1, x2, y2, \{ stroke: 'var\(--([\w-]+)\)'", (engine_dir("live") / "src/player.js").read_text()))
    for under in ("bg", "bg2", "panel"):
        assert contrast_ratio(colours[idle], colours[under]) >= MIN_GRAPHIC, (idle, under)
