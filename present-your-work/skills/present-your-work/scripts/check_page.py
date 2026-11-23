#!/usr/bin/env python3
"""Check a presentation page against the rules a script can see, at three window sizes.

    python3 -I scripts/check_page.py OUT_DIR

Loads OUT_DIR/page.html?check in headless Chrome at 2000x1150, 1440x900 and 1280x720, reads the
report the engine writes, and prints one line per problem: a click that changes no object or more
than one, a caption over budget or with two sentences, text that overlaps other text or leaves the
stage, a ring that points at nothing, a stage that does not fit the window, and a page that has
drifted from its approved click list (OUT_DIR/clicks.json). Exits 1 on any problem. Prints nothing
for a page that is done; a note (placeholders left) does not fail the check.
"""
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pagelib  # noqa: E402


CAPTION_WIDTH = 1400  # the caption line: the stage's width less 100px each side
TEXT_FLOOR = 20       # stage px: about 18 px in a 1440-wide window, the smallest a reader reads at a glance
LABEL_WORDS = 4       # a label names a thing; a fifth word starts explaining it
FAR_JUMP = 480        # stage px between one subject and the next, 30% of the stage's width
HERO_SHARE = 0.002    # the subject's share of the stage (a short chip), below which the eye has to hunt for it


def gap(a, b):
    """Distance between two boxes' nearest edges, 0 when they touch or overlap."""
    dx = max(0, max(a["x"], b["x"]) - min(a["x"] + a["w"], b["x"] + b["w"]))
    dy = max(0, max(a["y"], b["y"]) - min(a["y"] + a["h"], b["y"] + b["h"]))
    return (dx * dx + dy * dy) ** 0.5


def attention_problems(frames):
    """Where the eye goes: one thing at full ink, the next subject near the last, large enough to find."""
    out, prev = [], None
    for f in frames:
        n, where = f["n"], f"click {f['n']}"
        if n == 0:
            continue
        if len(f["lit"]) > 1:
            out.append(f"{where} has {len(f['lit'])} things at full ink ({', '.join(f['lit'])}): one subject per click")
        if len(f["second"]) > 2:
            out.append(f"{where} has {len(f['second'])} things at the second tone ({', '.join(f['second'])}): at most two")
        box = f.get("subjectBox")
        if box:
            share = box["w"] * box["h"] / (1600 * 900)
            if share < HERO_SHARE:
                out.append(f"{where} subject '{f['subject']}' is {share:.2%} of the stage: too small to find at a glance; "
                           "draw it larger, or make the part that changed the subject")
            if prev and prev.get("subjectBox") and prev["chapter"] == f["chapter"] and not f["travelled"]:
                d = gap(prev["subjectBox"], box)
                if d > FAR_JUMP:
                    out.append(f"{where} subject '{f['subject']}' is {d:.0f}px from the last one: the eye has to jump; "
                               "bring it nearer, or let the thing travel there")
        out += [f"{where} text is too small to read: {s}" for s in f["small"]]
        for label in f["labels"]:
            text = label.split('"', 1)[1].rstrip('"')
            if len(pagelib.words(text)) > LABEL_WORDS:
                out.append(f"{where} label {label} has more than {LABEL_WORDS} words: a label names, the caption explains")
        prev = f
    return out


def size_problems(rep, size):
    """Problems in one size's report, as (message) strings."""
    if rep.get("errors"):
        return [f"page error: {e}" for e in rep["errors"]]
    out = []
    vw, vh = rep["viewport"]
    if (vw, vh) != tuple(size):
        out.append(f"the window measured {vw}x{vh}, not {size[0]}x{size[1]}: this Chrome ignores --window-size")
    x, y, w, h = rep["stageBox"]
    k = min(vw / 1600, vh / 900)
    if x < -1 or y < -1 or x + w > vw + 1 or y + h > vh + 1 or abs(w - 1600 * k) > 2:
        out.append("the stage does not fit the window, letterboxed")
    for f in rep["frames"]:
        n = f["n"]
        if n == 0:
            continue
        where = f"click {n}"
        if f["clear"]:
            if not f["hidden"]:
                out.append(f"{where} is a clear that hides nothing")
            if f["changed"]:
                out.append(f"{where} is a clear but also changes {', '.join(f['changed'])}")
        elif not f["changed"]:
            out.append(f"{where} changes nothing: '{f['object']}' is already in state '{f['state']}'")
        elif len(f["changed"]) > 1:
            out.append(f"{where} changes {len(f['changed'])} objects ({', '.join(f['changed'])}): one change per click")
        elif f["changed"] != [f["object"]]:
            out.append(f"{where} names '{f['object']}' but '{f['changed'][0]}' is what changed")
        out += [f"{where} {p}" for p in pagelib.caption_problems(f["caption"], f.get("predict", False))]
        if f.get("captionWidth", 0) > CAPTION_WIDTH:
            out.append(f"{where} caption is {f['captionWidth']}px wide, more than one line ({CAPTION_WIDTH}px); shorten it")
        ring = f.get("ring")
        if ring and not ring["found"]:
            out.append(f"{where} highlight '{ring['selector']}' matches nothing")
        elif ring and not ring["visible"]:
            out.append(f"{where} highlight points at something hidden")
        out += [f"{where} text overlaps: {o}" for o in f["overlaps"]]
        out += [f"{where} text runs outside the stage: {o}" for o in f["outside"]]
        out += [f"{where} object text sits in the caption band: {o}" for o in f["band"]]
    return out + attention_problems(rep["frames"])


def page_problems(rep, out_dir):
    """Problems that do not depend on the window: prose and drift from the approved list."""
    out = [f"object '{u}' is on the page but no click is about it: cut it, or mark it context if it is a frame of reference"
           for u in rep.get("unused", [])]
    for text in dict.fromkeys(rep.get("prose", [])):
        out += [f"text '{text[:50]}' {p}" for p in pagelib.punctuation_problems(text)]
    for i, title in enumerate(rep.get("chapters", []), 1):
        out += [f"chapter {i} title '{title}' {p}" for p in pagelib.title_problems(title)]
    approved = Path(out_dir) / "clicks.json"
    if approved.exists():
        spec = pagelib.load_list(approved)
        clicks = spec.get("clicks", [])
        frames = [f for f in rep["frames"] if f["n"] > 0]
        if len(clicks) != len(frames):
            out.append(f"the page has {len(frames)} clicks, its approved list (clicks.json) has {len(clicks)}")
        if spec.get("chapters") != rep.get("chapters"):
            out.append("the chapter titles differ from the approved list (clicks.json)")
        for c, f in zip(clicks, frames):
            if (c.get("caption") or "") != (f["caption"] or ""):
                out.append(f"click {f['n']} caption differs from the approved list: '{f['caption']}' vs '{c.get('caption', '')}'")
            if c.get("chapter") != f["chapter"]:
                out.append(f"click {f['n']} is in chapter {f['chapter']}, the approved list says {c.get('chapter')}")
            for key in ("object", "state"):
                if c.get(key) and c[key] != f[key]:
                    out.append(f"click {f['n']} {key} is '{f[key]}', the approved list says '{c[key]}'")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out_dir")
    ap.add_argument("--sizes", help="WxH,WxH (default: 2000x1150,1440x900,1280x720)")
    args = ap.parse_args()
    chrome = pagelib.find_chrome()
    if not chrome:
        sys.exit(pagelib.NO_BROWSER)
    sizes = [tuple(int(v) for v in s.split("x")) for s in args.sizes.split(",")] if args.sizes else pagelib.SIZES
    pagelib.page_url(args.out_dir)
    pagelib.dom_offset(chrome)  # measure once, before the parallel runs
    with ThreadPoolExecutor(len(sizes)) as pool:
        reports = list(pool.map(lambda s: pagelib.check_report(chrome, args.out_dir, s), sizes))

    found = {}  # message -> sizes it appears at, in first-seen order
    for size, rep in zip(sizes, reports):
        for msg in size_problems(rep, size):
            found.setdefault(msg, []).append(f"{size[0]}x{size[1]}")
    lines = [m if len(s) == len(sizes) else f"{m} [{', '.join(s)}]" for m, s in found.items()]
    good = next((r for r in reports if not r.get("errors")), None)
    if good:
        lines += page_problems(good, args.out_dir)
    for line in lines:
        print(line)
    if good and good.get("placeholders"):
        print(f"note: {good['placeholders']} placeholders left to replace", file=sys.stderr)
    sys.exit(1 if lines else 0)


if __name__ == "__main__":
    main()
