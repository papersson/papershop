"""A story reel puts the actual voice and the boards on the desk in one command."""
from . import animatic, narration


def make(video):
    narration.narrate(video)
    return animatic.make(video, boards=True)


def main(args):
    rec = make(args.video)
    print(f"Story reel: cut {rec['cut']}")
    print("\n".join(animatic.describe(rec['pacing'])))
    print(f"Open it with: studio desk {args.video}")
    return 0
