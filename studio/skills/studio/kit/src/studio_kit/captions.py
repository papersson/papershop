"""`studio captions VIDEO`: the caption file, out/captions.vtt, beside the master.

Captions are never burned into the picture: on screen they compete with the diagrams the film is
made of, and a viewer who wants them can turn them on. So they ship as a WebVTT sidecar, written from
the timeline's caption chunks (tracks.captions: phrases of at most two lines, timed to the voice,
timeline.py), and every player that shows them keeps them off until the viewer asks:

  studio publish     out/captions.vtt next to out/master.mp4, and out/page/captions.vtt, which the
                     page offers as a captions track, off by default
  studio export      <slug>_<format>.vtt beside each exported video
  studio captions    out/captions.vtt alone, from the current timeline: for a film already published
                     before captions were a file, without rendering anything

A video without narration has no captions and gets no file.
"""
from pathlib import Path

from . import timeline as tl


def stamp(seconds):
    """WebVTT time: hh:mm:ss.mmm."""
    ms = max(0, round(seconds * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _cue_text(lines):
    # "-->" would end a cue's timing line, and "&" and "<" start markup in a cue's text.
    return "\n".join(line.replace("&", "&amp;").replace("<", "&lt;").replace("-->", "->") for line in lines)


def vtt(t):
    """The timeline's captions as a WebVTT document, or None when it has none."""
    cues = [c for c in t["tracks"].get("captions", []) if c.get("lines") and c["end"] > c["start"]]
    if not cues:
        return None
    out = ["WEBVTT", ""]
    for i, c in enumerate(cues, 1):
        out += [str(i), f"{stamp(c['start'])} --> {stamp(c['end'])}", _cue_text(c["lines"]), ""]
    return "\n".join(out)


def write(t, path):
    """Write the timeline's captions to `path`; returns the path, or None (and removes a stale file)
    when there are none."""
    path, text = Path(path), vtt(t)
    if text is None:
        path.unlink(missing_ok=True)
        return None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def main(args):
    video = Path(args.video).resolve()
    t = tl.build(video)
    out = write(t, video / "out" / "captions.vtt")
    if out is None:
        print("no captions: the video has no narration")
        return 0
    print(f"{len(t['tracks']['captions'])} captions → {out}")
    return 0
