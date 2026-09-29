"""The `studio` command. Every kit operation is a subcommand, so the agent needs one entry point."""
import argparse
import sys


def main(argv=None):
    p = argparse.ArgumentParser(prog="studio", description="Drive the studio kit.")
    sub = p.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("doctor", help="check the environment and print fixes")
    d.add_argument("--fetch", action="store_true", help="install the engines' node packages first")
    d.add_argument("--net", action="store_true", help="also check the hosts downloads come from")

    args = p.parse_args(argv)
    if args.cmd == "doctor":
        from . import doctor
        return doctor.main(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
