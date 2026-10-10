"""The kinds of review, each with its policies declared in one place.

  roles      the receipts it writes (research/reviews/<role>.json)
  scope      what its revision hashes (review_state.fingerprint): "script" or "frames"
  verdict    how a reviewer's text becomes a status: "passed" when its last verdict line passes
  rounds     the cap on rounds (from video.json, or none), and the kinds of stage mark that start
             the count again when the material changed across them: a round is a review of a
             revision not yet reviewed since the latest such mark (review_state.rounds), whatever
             number the caller gives it
  freshness  what a result for an older revision does: "refuse" it, or "record-stale": import it
             marked stale, with what changed since, so the receipt shows the work but `require`
             still asks for a review of the current revision
  settled    the statuses `require` accepts: passed or waived, and for a motion review also
             "known-issues" (stopped by its rule with should-fix findings left on the cut)
  stands     what a settled receipt stands for: the "revision" it judged, or the "lineage": every
             later revision until a stage mark that starts the kind's round count again over changed
             material (review_state.stands)

  records    the statuses `studio review-status` may record for it: unavailable or waived for a
             reviewer, passed or waived for the listening check

A script review runs reviewers against the current revision, so it has nothing to import; a frame
review is packaged for the main session and its result imported later, which is where freshness
applies. A motion review is packaged the same way, and its rounds stop by a rule (motion_review.py):
at a round with no must-fix findings, or at the cap. The CLI's review-status roles and
review_state.require are read from here.

The listening check is not a reviewer: the kit measures sound (audio-check) and cannot hear it, so
the user listens once to the finished mix and the builder records it (review-status VIDEO listen
passed or waived). audio-check chooses about five timecodes for that listen, each with its reason
(audio_check.listening), and publish's warning and the handoff's step name them; the receipt keeps
the timecodes listened at (--at, else the ones chosen for that mix), and one recorded with none
still stands. Its revision is the soundtrack's stamp (audio.revision), so it goes stale when the
mix changes. Nothing requires it: publish warns when a video with effects or music has none standing
(review_state.listening), and the handoff lists it as a next step.
"""
import re
from dataclasses import dataclass, field

# Rounds are the slowest loop in a build (one search video spent six rounds reaching the gate), so
# the default is two rounds plus one more for an expert's blocking finding; "thorough" restores six.
DEFAULT_MAX_ROUNDS = {"thorough": 6, "default": 3, "economy": 2}


# Should-fix findings plateaued at 25 to 45 a round in one long session, so a motion review stops at
# a round with no must-fix findings, or after two rounds, and what is left is recorded on the cut.
DEFAULT_MOTION_ROUNDS = 2


def script_cap(cfg):
    """video.json's max_rounds, else the default for its pace (economy, default or thorough)."""
    pace = "thorough" if cfg.get("thorough") else "economy" if cfg.get("economy") else "default"
    return cfg.get("max_rounds", DEFAULT_MAX_ROUNDS[pace])


def motion_cap(cfg):
    """video.json's motion_rounds, else DEFAULT_MOTION_ROUNDS."""
    return cfg.get("motion_rounds", DEFAULT_MOTION_ROUNDS)


@dataclass(frozen=True)
class Rounds:
    cap: object = None          # video.json -> the rounds allowed, or None for no cap
    resets_on: tuple = ()       # kinds of stage mark (stage.py's --kind; "fork", fork's first mark) that
                                # start the count again, when the material changed across the mark
    past_cap: object = ""       # why a round past the cap is refused, and what to do instead: a string
                                # filled with {number}, {cap}, {count}, {where} (the mark the count runs
                                # from) and {video} (its path, quoted), or a function of those and `last`,
                                # the kind's receipt


def motion_past_cap(number, cap, count, where, video, last):
    """A motion round past the cap. A review that ended clean (passed, known issues on the cut) or was
    waived is settled and nothing more is needed; only must-fix findings still open leave a choice."""
    new_count = (f"A structural revision (studio stage {video} revision --kind structural --summary …) starts a new "
                 "count and a new review")
    counted = f"{count} cuts of this lineage have been motion-reviewed since {where}"
    if last.get("status") == "findings":
        return (f"a motion review round {number} would pass motion_rounds ({cap}): {counted}, and the last (cut "
                f"{last.get('cut', '?')}) stopped at the cap with {last.get('must_fix', 'some')} must-fix finding(s) open. "
                f"To proceed: fix them and record the user's acceptance with studio review-status {video} motion waived "
                "--reason …; or, only if the user explicitly asks for more rounds, raise video.json motion_rounds. " + new_count)
    how = {"passed": "passed with nothing left",
           "known-issues": f"ended by its rule with {last.get('left', 'some')} should-fix or nit finding(s) left, recorded "
                           f"on cut {last.get('cut', '?')} as known issues",
           "waived": "was waived"}.get(last.get("status"), "ended")
    return (f"the motion review is settled and nothing more is needed: it {how}. {counted}, and "
            f"motion_rounds ({cap}) allows no round {number}. " + new_count)


def verdict(prefix, passing):
    """A parser: (status, the last line that is a verdict, or None)."""
    def parse(text):
        lines = [line.strip() for line in text.splitlines() if prefix(line.strip())]
        return ("passed" if lines and lines[-1] == passing else "findings"), (lines[-1] if lines else None)
    return parse


def loose_verdict(word):
    """A parser for "WORD: PASS" or "WORD: FIX" on a line of its own that tolerates a reviewer's drift
    in format: markdown around it (bold, a heading, a quote, backticks), a dash for the colon, a
    "Verdict:" before it, a full stop after it and its letter case; a sentence that only starts with
    it ("MOTION: PASS would be my call…") is not a verdict. The last one counts. The line is
    returned in the canonical form, or None when there is no verdict line."""
    pattern = re.compile(rf"^(?:verdict\s*:\s*)?{word}\s*[:\-]\s*(PASS|FIX)\s*[.!]?$", re.I)
    dashes = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"), "-")

    def parse(text):
        lines = (re.sub(r"[*_`#>]", "", line.translate(dashes)).strip() for line in text.splitlines())
        found = [m.group(1).upper() for m in map(pattern.match, lines) if m]
        line = f"{word}: {found[-1]}" if found else None
        return ("passed" if found and found[-1] == "PASS" else "findings"), line
    return parse


@dataclass(frozen=True)
class Kind:
    name: str
    roles: tuple
    scope: str
    verdict: object
    remedy: str                 # what `require` tells the builder to run; {role} and {video} are filled in
    rounds: Rounds = Rounds()
    freshness: str = "refuse"
    aliases: dict = field(default_factory=dict)
    settled: tuple = ("passed", "waived")
    stands: str = "revision"
    records: tuple = ("unavailable", "waived")


KINDS = {
    "script": Kind("script", ("expert", "student", "editor"), "script",
                   verdict(lambda line: "VERDICT" in line, "VERDICT: PASS"),
                   "run studio review {video} ROUND --only {role}", Rounds(cap=script_cap, resets_on=("structural", "fork"), past_cap=(
                       "round {number} is past max_rounds ({cap}): this revision of the script has had {count} review rounds "
                       "since {where}. Lock the script with every open finding logged, or ask the learner to raise the cap. "
                       "A structural rewrite (a new chapter or a changed arc, marked with studio stage {video} revision --kind "
                       "structural --summary …) starts a new count; a mark over an unchanged script does not"))),
    "frames": Kind("frames", ("frames",), "frames",
                   verdict(lambda line: line.startswith("FRAMES:"), "FRAMES: PASS"),
                   "run studio review-frames and return its findings", freshness="record-stale", aliases={"frame": "frames"}),
    # Counted per cut lineage: every round reviews a new cut (fixing changes the frames), so a count per
    # revision would never stop, and a count per script revision would buy two more rounds with every
    # local wording fix. A structural revision changes the picture widely enough to start a new count.
    "motion": Kind("motion", ("motion",), "frames", loose_verdict("MOTION"),
                   "run studio review-motion and return its findings",
                   Rounds(cap=motion_cap, resets_on=("structural", "fork"), past_cap=motion_past_cap),
                   freshness="record-stale", settled=("passed", "known-issues", "waived"), stands="lineage"),
    "listen": Kind("listen", ("listen",), "sound", None,
                   "ask the user to listen once to the finished mix (out/master.mp4, or the desk's latest cut) at the "
                   "timecodes studio audio-check chose, and record it with studio review-status {video} listen passed "
                   "--reason \"…\" (or waived)",
                   records=("passed", "waived")),
}

ROLES = tuple(r for k in KINDS.values() for r in k.roles)
RECORDS = tuple(dict.fromkeys(st for k in KINDS.values() for st in k.records))
ALIASES = {a: r for k in KINDS.values() for a, r in k.aliases.items()}


def role(name):
    """A role as named on the command line, its alias resolved."""
    return ALIASES.get(name, name)


def kind_of(role_name):
    found = next((k for k in KINDS.values() if role(role_name) in k.roles), None)
    if found is None:
        raise SystemExit(f"unknown review role: {role_name}")
    return found
