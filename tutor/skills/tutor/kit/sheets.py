"""Contact sheets: one frame near the end of every sentence, a sheet per chapter, for checking that
the picture matches the line being spoken.

    python kit/sheets.py LESSON_DIR OUTDIR                    # from out/video.mp4, every chapter
    python kit/sheets.py LESSON_DIR OUTDIR --segment s3 --video PATH/S3.mp4 [--width 854]
                                                             # one chapter's own render (e.g. a preview)

Each frame is labelled with its sentence id. Read the sheets with an image viewer (or the Read
tool); for a finding, grab the full 1080p frame with ffmpeg before acting on it.
"""
import io
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def frame(video, t, width):
    png = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", f"{max(t, 0):.2f}", "-i", str(video), "-frames:v", "1",
                          "-vf", f"scale={width}:-1", "-f", "image2pipe", "-vcodec", "png", "-"],
                         capture_output=True, check=True).stdout
    return Image.open(io.BytesIO(png)).convert("RGB")


def sheet(seg, video, offset, width, out):
    ims = []
    for ln in seg["lines"]:
        t = max(ln["start"] + 0.2, ln["end"] - 0.15) - offset
        im = frame(video, t, width)
        ImageDraw.Draw(im).text((6, 4), ln["id"], fill=(255, 90, 90))
        ims.append(im)
    w, h = ims[0].size
    cols = 3
    rows = (len(ims) + cols - 1) // cols
    s = Image.new("RGB", (cols * w + (cols - 1) * 4, rows * h + (rows - 1) * 4), (70, 70, 70))
    for i, im in enumerate(ims):
        s.paste(im, ((i % cols) * (w + 4), (i // cols) * (h + 4)))
    s.save(out)
    print(out, len(ims))


def main():
    lesson, outdir = Path(sys.argv[1]), Path(sys.argv[2])
    outdir.mkdir(parents=True, exist_ok=True)
    timings = json.loads((lesson / "audio" / "timings.json").read_text())
    width = int(arg("--width", 640))
    only = arg("--segment")
    for seg in timings["segments"]:
        if only and seg["id"] != only:
            continue
        if only:          # a single chapter's own render starts at that chapter's start
            sheet(seg, Path(arg("--video")), seg["start"], width, outdir / f"{seg['id']}.png")
        else:
            sheet(seg, lesson / "out" / "video.mp4", 0.0, width, outdir / f"{seg['id']}.png")


if __name__ == "__main__":
    main()
