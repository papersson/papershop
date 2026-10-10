"""The sound sheet: a soundtrack drawn over time, for Claude to look at before anyone listens.

One PNG, drawn by ffmpeg alone (showwavespic, showspectrumpic, drawbox, drawtext), top to bottom:

  effects     a label per effect at its contact time, "fx3 confirm (land)", in up to LABEL_ROWS rows so
              neighbours don't overlap, with what audio-check flagged on it (LOUD, MASKED, QUIET, SYNC,
              PICTURE, PAUSE); a flagged effect is red, the others amber
  narration   a band per sentence, its id in it; a word audio-check found masked is a red block
  waveform    the mix's waveform (amplitude on a square-root scale, so a quiet tick still shows); on a
              close-up, a green line where the picture does what an effect's tag says (its
              picture_frame, from audio-check), so sound and picture read side by side
  spectrum    its spectrogram, 60 Hz to 16 kHz on a log axis
  time        seconds along the bottom; on a close-up also a tick per video frame, numbered every
              fifth, so a marker reads against the frame grid

Every effect's marker is a vertical line through all four lanes. `studio audio-check` draws the whole
video (out/audio-sheet.png) and a close-up around each hero effect (out/audio-sheet/fxN.png);
`studio review-motion` draws one per window that has effects, from the cut's own sound. The labels
use the same named font file as the motion review's frame numbers (motion_review.label_font), so
fontconfig is never asked; with no font at all the sheet is drawn without text.
"""
import math
import re

from . import proc

TITLE_H, LABEL_ROW_H, LABEL_ROWS, SPEECH_H, WAVE_H, SPECTRUM_H, AXIS_H = 30, 26, 3, 30, 170, 220, 40
FONT = 16                   # px: legible at the width Claude is shown an image (about 1500 px)
OK, FLAGGED, SPEECH, MASKED, PICTURE = "0xffc94d", "0xff4d4d", "0x3d6b8f", "0xff4d4d", "0x5ce0b8"
BG = "0x14181d"


def _safe(text):
    """Text drawtext can take unescaped inside quotes: letters, digits and a few marks."""
    return re.sub(r"[^A-Za-z0-9 ._()+/#-]", " ", str(text))


def _text(font, x, y, text, color="white", size=FONT, box=None):
    b = f":box=1:boxcolor={box}:boxborderw=3" if box else ""
    return f"drawtext={font}text='{_safe(text)}':x={x:.0f}:y={y:.0f}:fontsize={size}:fontcolor={color}{b}"


def _rows(labels, width_of):
    """Each label's row: the first where it clears the last label placed in it, else the row whose
    last label ends soonest (it overlaps, but stays readable on top)."""
    ends, out = [-1e9] * LABEL_ROWS, []
    for x, text in labels:
        r = next((i for i, e in enumerate(ends) if x >= e + 6), min(range(LABEL_ROWS), key=lambda i: ends[i]))
        ends[r] = x + width_of(text)
        out.append(r)
    return out


def draw(audio_file, out, a, b, effects=(), sentences=(), masked=(), fps=None, width=1600, title=""):
    """Draw seconds a..b of `audio_file` into `out` (PNG). effects: [{id, type, visual?, t, flags}];
    sentences: [{id, start, end}]; masked: [(start, end)] of words; fps: draw a tick per frame (a
    close-up). Audio short of b (a close-up near the video's end) is padded with silence, so the
    picture keeps its time scale. Returns whether the text was drawn (False when ffmpeg has no font)."""
    from .motion_review import label_font
    span = max(b - a, 1e-3)
    x_of = lambda t: (t - a) / span * width                                   # noqa: E731
    lanes = TITLE_H + LABEL_ROW_H * LABEL_ROWS
    wave_y, spec_y = lanes + SPEECH_H, lanes + SPEECH_H + WAVE_H
    axis_y = spec_y + SPECTRUM_H
    height = axis_y + AXIS_H
    font = label_font()
    boxes, texts = [], []
    for s in sentences:                                                       # the narration's sentences
        if s["end"] < a or s["start"] > b:
            continue
        x0, x1 = max(0, x_of(s["start"])), min(width, x_of(s["end"]))
        boxes.append(f"drawbox=x={x0:.0f}:y={lanes + 3}:w={max(1, x1 - x0):.0f}:h={SPEECH_H - 6}:color={SPEECH}@0.9:t=fill")
        if x1 - x0 > FONT * 2:
            texts.append(_text(font, x0 + 4, lanes + 7, s["id"], size=FONT - 2))
    for w0, w1 in masked:                                                     # masked words, over speech and waveform
        if w1 < a or w0 > b:
            continue
        x0 = max(0, x_of(w0))
        boxes.append(f"drawbox=x={x0:.0f}:y={lanes}:w={max(2, min(width, x_of(w1)) - x0):.0f}:h={SPEECH_H + WAVE_H}:"
                     f"color={MASKED}@0.35:t=fill")
    step = tick_step(span)
    k = int(a // step) + 1 if a > 0 else 0
    while k * step <= b + 1e-9:                                               # seconds along the bottom
        t = k * step
        boxes.append(f"drawbox=x={x_of(t):.0f}:y={axis_y}:w=1:h=10:color=white@0.8:t=fill")
        texts.append(_text(font, min(width - 50, x_of(t) + 3), axis_y + 20, f"{t:g}s", color="white@0.85", size=FONT - 3))
        k += 1
    if fps:                                                                   # a close-up: the frame grid
        f = int(a * fps) + 1
        while f / fps <= b:
            x = x_of(f / fps)
            tall = f % 5 == 0
            boxes.append(f"drawbox=x={x:.0f}:y={axis_y}:w=1:h={18 if tall else 5}:color=0x8fd3ff:t=fill")
            if tall:
                texts.append(_text(font, x + 3, axis_y + 2, f"f{f}", color="0x8fd3ff", size=FONT - 4))
            f += 1
    for e in effects:                                                         # a close-up: where the picture does it
        if fps and e.get("picture_frame") is not None and a <= e["picture_frame"] / fps <= b:
            x = x_of(e["picture_frame"] / fps)
            boxes.append(f"drawbox=x={x:.0f}:y={lanes}:w=2:h={axis_y - lanes}:color={PICTURE}@0.9:t=fill")
            texts.append(_text(font, min(x + 4, width - 200), lanes + SPEECH_H + 4, f"{e['id']} picture f{e['picture_frame']}",
                               color="black", size=FONT - 2, box=PICTURE))
    shown = [e for e in effects if a <= e["t"] <= b]
    rows = _rows([(x_of(e["t"]), _label(e)) for e in shown], lambda text: len(text) * FONT * 0.62 + 8)
    for e, r in zip(shown, rows):                                             # the markers, on top
        x, color = x_of(e["t"]), FLAGGED if e.get("flags") else OK
        y = TITLE_H + r * LABEL_ROW_H
        boxes.append(f"drawbox=x={x - 1:.0f}:y={y}:w=3:h={axis_y - y}:color={color}@0.95:t=fill")
        texts.append(_text(font, min(x + 4, width - len(_label(e)) * FONT * 0.62 - 6), y + 3, _label(e), color="black", box=color))
    texts.insert(0, _text(font, 8, 7, title, color="white@0.9", size=FONT - 1))
    lanes_graph = (f"color=c={BG}:s={width}x{lanes + SPEECH_H}[top];color=c={BG}:s={width}x{WAVE_H}[wb];"
                   f"color=c={BG}:s={width}x{AXIS_H}[axis];")
    pictures = (f"[0:a]aformat=channel_layouts=mono,apad=whole_dur={span:.3f},atrim=duration={span:.3f},asplit=2[a1][a2];"
                f"[a1]showwavespic=s={width}x{WAVE_H}:colors=0x8fd3ff:scale=sqrt[w];[wb][w]overlay=format=auto[wave];"
                f"[a2]showspectrumpic=s={width}x{SPECTRUM_H}:legend=0:fscale=log:color=magma:scale=log:drange=70:"
                f"start=60:stop=16000[spec];")
    stack = "[top][wave][spec][axis]vstack=inputs=4"
    for with_text in (bool(font), False):
        graph = lanes_graph + pictures + stack + "".join("," + f for f in boxes + (texts if with_text else [])) + "[o]"
        try:
            proc.ffmpeg("-ss", f"{max(0.0, a):.3f}", "-t", f"{span:.3f}", "-i", str(audio_file), "-filter_complex", graph,
                        "-map", "[o]", "-frames:v", "1", str(out))
            return with_text
        except proc.SubprocessError:
            if not with_text:
                raise
    return False


def tick_step(span):
    """Seconds between the time axis's labels: at most 24 across `span`, on a round step."""
    return next((s for s in (0.1, 0.2, 0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300, 600) if span / s <= 24),
                60 * math.ceil(span / 24 / 60))


def _label(e):
    flags = " ".join(e.get("flags") or ())
    return f"{e['id']} {e.get('type') or ''}" + (f" ({e['visual']})" if e.get("visual") else "") + (f" {flags}" if flags else "")


def height():
    """The sheet's height in pixels (every sheet is this tall)."""
    return TITLE_H + LABEL_ROW_H * LABEL_ROWS + SPEECH_H + WAVE_H + SPECTRUM_H + AXIS_H


def closeup_span(t, before=0.6, after=0.9):
    """The seconds a hero effect's close-up covers: 0.6 s before its contact (a lead-in, the frames
    before) and 0.9 s after (its tail and the settle)."""
    return max(0.0, t - before), t + after

