"""The kinds of review, each with its policies declared in one place.

  roles      the receipts it writes (research/reviews/<role>.json)
  scope      what its revision hashes (review_state.fingerprint): "script" or "frames"
  verdict    how a reviewer's text becomes a status: "passed" when its last verdict line passes
  rounds     the cap on rounds (from video.json, or none) and what starts the count again
  freshness  what a result for an older revision does: "refuse" it, or "record-stale": import it
             marked stale, with what changed since, so the receipt shows the work but `require`
             still asks for a review of the current revision

A script review runs reviewers against the current revision, so it has nothing to import; a frame
review is packaged for the main session and its result imported later, which is where freshness
applies. The CLI's review-status roles and review_state.require are read from here.
"""
from dataclasses import dataclass, field

# Rounds are the slowest loop in a build (one search video spent six rounds reaching the gate), so
# the default is two rounds plus one more for an expert's blocking finding; "thorough" restores six.
DEFAULT_MAX_ROUNDS = {"thorough": 6, "default": 3, "economy": 2}


def script_cap(cfg):
    """video.json's max_rounds, else the default for its pace (economy, default or thorough)."""
    pace = "thorough" if cfg.get("thorough") else "economy" if cfg.get("economy") else "default"
    return cfg.get("max_rounds", DEFAULT_MAX_ROUNDS[pace])


@dataclass(frozen=True)
class Rounds:
    cap: object = None          # video.json -> the last round allowed, or None for no cap
    resets_on: tuple = ()       # stage marks that start the count again; none yet, so a round is its number


def verdict(prefix, passing):
    """A parser: (status, the last line that is a verdict, or None)."""
    def parse(text):
        lines = [line.strip() for line in text.splitlines() if prefix(line.strip())]
        return ("passed" if lines and lines[-1] == passing else "findings"), (lines[-1] if lines else None)
    return parse


@dataclass(frozen=True)
class Kind:
    name: str
    roles: tuple
    scope: str
    verdict: object
    remedy: str                 # what `require` tells the builder to run; {role} is filled in
    rounds: Rounds = Rounds()
    freshness: str = "refuse"
    aliases: dict = field(default_factory=dict)


KINDS = {
    "script": Kind("script", ("expert", "student", "editor"), "script",
                   verdict(lambda line: "VERDICT" in line, "VERDICT: PASS"),
                   "run studio review VIDEO ROUND --only {role}", Rounds(cap=script_cap)),
    "frames": Kind("frames", ("frames",), "frames",
                   verdict(lambda line: line.startswith("FRAMES:"), "FRAMES: PASS"),
                   "run studio review-frames and return its findings", freshness="record-stale", aliases={"frame": "frames"}),
}

ROLES = tuple(r for k in KINDS.values() for r in k.roles)
ALIASES = {a: r for k in KINDS.values() for a, r in k.aliases.items()}


def role(name):
    """A role as named on the command line, its alias resolved."""
    return ALIASES.get(name, name)


def kind_of(role_name):
    found = next((k for k in KINDS.values() if role(role_name) in k.roles), None)
    if found is None:
        raise SystemExit(f"unknown review role: {role_name}")
    return found
