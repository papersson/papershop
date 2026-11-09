#!/usr/bin/env python3
"""Screenshot every click of a walkthrough, finished, at three sizes, plus chosen clicks mid-motion.

    python3 -I scripts/shoot.py OUT_DIR --out shots --mid 3,8 [--at 450] [--sizes 1440x900] [--scale 2] [--strip]

Writes shots/<W>x<H>/07.png for click 7 finished (00.png is the cover), shots/mid/08-450ms.png for
click 8 frozen 450 ms into its motion, shots/strip.png for every click as small multiples (--strip),
and shots/captions.md: each click's number, chapter and caption beside its screenshot, which is the
packet a fresh reader gets. Runs in parallel, one headless Chrome (with its own temporary profile)
per shot. Virtual time makes the shots deterministic.
"""
import argparse
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import walklib  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out_dir")
    ap.add_argument("--out", default=None, help="where the shots go (default OUT_DIR/shots)")
    ap.add_argument("--mid", default="", help="clicks to freeze mid-motion, e.g. 3,8")
    ap.add_argument("--at", type=int, default=450, help="ms into the motion for --mid (default 450)")
    ap.add_argument("--sizes", help="WxH,WxH (default: 2000x1150,1440x900,1280x720)")
    ap.add_argument("--scale", type=int, default=1, help="device scale factor; 2 for shots a person will see")
    ap.add_argument("--strip", action="store_true", help="also shoot the ?strip overview")
    args = ap.parse_args()
    chrome = walklib.find_chrome()
    if not chrome:
        sys.exit(walklib.NO_BROWSER)
    sizes = [tuple(int(v) for v in s.split("x")) for s in args.sizes.split(",")] if args.sizes else walklib.SIZES
    out = Path(args.out) if args.out else Path(args.out_dir) / "shots"

    rep = walklib.check_report(chrome, args.out_dir, (1440, 900))
    if rep.get("errors"):
        sys.exit("the page has errors; run check.py first:\n" + "\n".join(rep["errors"]))
    frames = rep["frames"]
    jobs = []  # (path, size, url, budget)
    for w, h in sizes:
        for f in frames:
            jobs.append((out / f"{w}x{h}" / f"{f['n']:02d}.png", (w, h), walklib.page_url(args.out_dir, "", str(f["n"])), 3000))
    mids = [int(m) for m in args.mid.split(",") if m.strip()]
    for n in mids:
        if not 1 <= n <= rep["clicks"]:
            sys.exit(f"--mid {n}: clicks run from 1 to {rep['clicks']}")
        w, h = sizes[len(sizes) // 2]
        jobs.append((out / "mid" / f"{n:02d}-{args.at}ms.png", (w, h), walklib.page_url(args.out_dir, f"mid={n}&at={args.at}"), 3000))
    if args.strip:
        rows = -(-len(frames) // 4)
        jobs.append((out / "strip.png", (1780, 120 + rows * 330), walklib.page_url(args.out_dir, "strip"), 2000))

    def shoot(job):
        path, size, url, budget = job
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            path.unlink()
        result = walklib.run_chrome(chrome, size, url, [f"--screenshot={path.resolve()}"], args.scale, budget)
        return None if path.exists() else f"{path}: no screenshot ({(result.stderr or '').strip().splitlines()[-1:]})"

    with ThreadPoolExecutor(min(8, os.cpu_count() or 2)) as pool:
        failures = [f for f in pool.map(shoot, jobs) if f]

    w, h = sizes[len(sizes) // 2]
    lines = [f"# {rep['title']}", "", f"Finished state of every click at {w}x{h}.", ""]
    for f in frames:
        chapter = rep["chapters"][f["chapter"] - 1] if f["chapter"] else "cover"
        label = "cover" if f["n"] == 0 else f"{f['n']}/{rep['clicks']}"
        lines += [f"## {label}: {chapter}", "", f"![{label}]({w}x{h}/{f['n']:02d}.png)", "",
                  f"> {f['caption']}" if f["caption"] else "_(no caption)_", ""]
    (out / "captions.md").write_text("\n".join(lines))
    for f in failures:
        print(f)
    print(f"{len(jobs) - len(failures)} shots in {out}")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
