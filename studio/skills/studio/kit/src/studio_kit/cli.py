"""The `studio` command. Every kit operation is a subcommand, so the agent needs one entry point."""
import argparse
import sys


def main(argv=None):
    p = argparse.ArgumentParser(prog="studio", description="Drive the studio kit.")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="check the environment and print fixes")
    d.add_argument("--fetch", action="store_true", help="install the engines' node packages first")
    d.add_argument("--net", action="store_true", help="also check the hosts downloads come from")
    d.add_argument("--extra", action="append", default=[], help="with --fetch: a Python extra to install (align, kokoro)")

    i = sub.add_parser("import-tutor", help="make a video's timeline from a tutor lesson")
    i.add_argument("lesson")
    i.add_argument("video")

    a = sub.add_parser("align", help="word timings for the narration; re-chunk captions")
    a.add_argument("video")
    a.add_argument("--model", default="small.en")

    s = sub.add_parser("still", help="render the frame at clip time t")
    s.add_argument("video")
    s.add_argument("clip")
    s.add_argument("t", type=float)
    s.add_argument("--out", required=True)
    s.add_argument("--layers", default="all", choices=["all", "no-captions", "background"])
    s.add_argument("--scale", type=float, default=1.0)

    b = sub.add_parser("boxes", help="pixel boxes of the labelled elements at clip time t")
    b.add_argument("video")
    b.add_argument("clip")
    b.add_argument("t", type=float)

    du = sub.add_parser("duration", help="a clip's length as the engine computes it")
    du.add_argument("video")
    du.add_argument("clip")

    r = sub.add_parser("render", help="render one clip as a silent video")
    r.add_argument("video")
    r.add_argument("clip")
    r.add_argument("--out", required=True)
    r.add_argument("--quality", default="draft", choices=["draft", "final"])
    r.add_argument("--range", nargs=2, type=float, metavar=("A", "B"))

    c = sub.add_parser("cut", help="make the next cut: stills, changed clips, composite")
    c.add_argument("video")
    c.add_argument("--quality", default="draft", choices=["draft", "final"])
    c.add_argument("--stills-only", action="store_true", help="stills only (a look gate, or a quick answer)")
    c.add_argument("--changelog", help="JSON list of {note, change} answering the previous cut's notes")

    dt = sub.add_parser("determinism", help="render sample frames twice and compare their hashes")
    dt.add_argument("video")
    dt.add_argument("--samples", type=int, default=3, help="frames per clip")

    sv = sub.add_parser("serve", help="serve the review page for the latest cut")
    sv.add_argument("video")
    sv.add_argument("--port", type=int, default=8765)

    nt = sub.add_parser("notes", help="the notes on a cut, numbered")
    nt.add_argument("video")
    nt.add_argument("--cut", type=int)

    args = p.parse_args(argv)
    if args.cmd == "serve":
        from . import page
        page.serve(args.video, args.port)
        return 0
    if args.cmd == "notes":
        from . import page
        print(page.notes_text(args.video, args.cut))
        return 0
    if args.cmd == "determinism":
        from . import check
        return check.main(args)
    if args.cmd == "render":
        import json
        from .engine import Engine
        print(json.dumps(Engine(args.video).render(args.clip, args.out, args.quality, args.range)))
        return 0
    if args.cmd == "cut":
        import json
        from pathlib import Path
        from .render import make_cut
        log = json.loads(Path(args.changelog).read_text()) if args.changelog else None
        rec = make_cut(args.video, args.quality, args.stills_only, log)
        done = [c["id"] for c in rec["clips"] if c["rendered"]]
        print(f"cut {rec['cut']}: rendered {', '.join(done) or 'no clips (all cached)'}; "
              f"seconds {rec['seconds']}")
        return 0
    if args.cmd in ("still", "boxes", "duration"):
        import json
        from .engine import Engine
        e = Engine(args.video)
        if args.cmd == "still":
            r = e.still(args.clip, args.t, args.out, args.layers, args.scale)
        elif args.cmd == "boxes":
            r = e.boxes(args.clip, args.t)
        else:
            r = e.duration(args.clip)
        print(json.dumps(r))
        return 0
    if args.cmd == "doctor":
        from . import doctor
        return doctor.main(args)
    if args.cmd == "import-tutor":
        from . import timeline
        t = timeline.from_tutor(args.lesson, args.video)
        print(f"{len(t['tracks']['scene'])} clips, {len(t['tracks']['narration'])} sentences, "
              f"{t['duration']:.1f} s → {args.video}/timeline.json")
        return 0
    if args.cmd == "align":
        from . import align
        return align.main(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
