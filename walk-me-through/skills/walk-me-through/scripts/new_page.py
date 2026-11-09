#!/usr/bin/env python3
"""Print a click list for approval, or build a starter page from an approved one.

    python3 -I scripts/new_page.py clicks.json --markdown     # print and lint the list
    python3 -I scripts/new_page.py clicks.json OUT_DIR        # build OUT_DIR/page.html

--markdown prints the list as the reader will follow it, then one line per problem: a caption over
12 words or with two sentences, a dash or semicolon, a chapter number out of range, a click that
does not say what changes. It exits 1 when there are problems.

Building refuses a list with problems. It writes page.html, its own copy of walk.js and walk.css,
and the approved clicks.json that check.py holds the page to. Every click starts as a dim
placeholder that reads its change, kept to its chapter, so the page runs and passes check.py at
once; replace placeholders one at a time with real pieces and states.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import walklib  # noqa: E402

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="walk.css">
</head>
<body>
<script src="walk.js"></script>
<script>
// Built from clicks.json by new_page.py. Each click starts as a placeholder (piece 'text',
// placeholder: true). Replace them one at a time with the real piece and its states; keep
// clicks.json in step, because check.py holds the page to it. The format is in walk.js's header.
Walk.page({definition});
</script>
</body>
</html>
"""


def starter(spec):
    """The page definition: one placeholder object per click, stacked down its chapter's stage."""
    objects, clicks, row = {}, [], {}
    for n, c in enumerate(spec["clicks"], 1):
        ch = c["chapter"]
        click = {"chapter": ch}
        if c.get("caption"):
            click["caption"] = c["caption"]
        if c.get("clear"):
            click.update(clear=True, keep=c.get("keep", []))
            clicks.append(click)
            continue
        i = row.get(ch, 0)
        row[ch] = i + 1
        col, line = divmod(i, 8)
        change = c["change"] if len(c["change"]) <= 56 else c["change"][:55].rstrip() + "…"
        oid = f"p{n}"
        objects[oid] = {"piece": "text", "placeholder": True, "text": f"{n}. {change}", "width": 680,
                        "ch": [ch], "states": {"shown": {"x": 100 + col * 740, "y": 150 + line * 74}}}
        click.update(object=oid, state="shown")
        clicks.append(click)
    page = {"title": spec["title"], "chapters": spec["chapters"], "objects": objects, "clicks": clicks}
    if spec.get("cover"):
        page["cover"] = spec["cover"]
    if spec.get("notes"):
        page["notes"] = spec["notes"]
    return page


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("clicks")
    ap.add_argument("out_dir", nargs="?")
    ap.add_argument("--markdown", action="store_true", help="print the list for the reader and lint it")
    ap.add_argument("--force", action="store_true", help="overwrite an existing page.html")
    args = ap.parse_args()
    spec = walklib.load_list(args.clicks)
    problems, notes = walklib.lint(spec)
    if args.markdown or not args.out_dir:
        print(walklib.markdown(spec))
    for line in notes:
        print(f"note: {line}", file=sys.stderr)
    for line in problems:
        print(line, file=sys.stderr if not args.markdown else sys.stdout)
    if problems:
        if args.out_dir and not args.markdown:
            print("not built: fix the list first", file=sys.stderr)
        sys.exit(1)
    if not args.out_dir or args.markdown:
        return
    out = Path(args.out_dir)
    if (out / "page.html").exists() and not args.force:
        sys.exit(f"{out / 'page.html'} exists; pass --force to replace it")
    out.mkdir(parents=True, exist_ok=True)
    for name in ("walk.js", "walk.css"):
        shutil.copyfile(walklib.ENGINE / name, out / name)
    if Path(args.clicks).resolve() != (out / "clicks.json").resolve():
        (out / "clicks.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
    definition = json.dumps(starter(spec), indent=2, ensure_ascii=False).replace("</", "<\\/")
    title = spec["title"].replace("&", "&amp;").replace("<", "&lt;")
    (out / "page.html").write_text(PAGE.format(title=title, definition=definition))
    print(f"wrote {out / 'page.html'}: {len(spec['clicks'])} placeholders; open it, then run check.py {out}")


if __name__ == "__main__":
    main()
