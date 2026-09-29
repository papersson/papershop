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

    args = p.parse_args(argv)
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
