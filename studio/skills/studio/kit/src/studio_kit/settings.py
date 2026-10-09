"""video.json, read in one place.

Every key the kit reads is listed here with its default and meaning, so a new setting has one home
and a reader of the code can see the whole schema. `load` returns the file merged over DEFAULTS;
keys without a default are simply absent when unset (callers use .get).

  title              the video's name (new)
  version            "v1", "v2", ... (new, revisions)
  genre              explainer | motion | launch | pixel | footage            default "explainer"
  drive              author | learner (explainers)
  level              intro | deep-dive                                         default "intro"
  destination        private-page | share | social | files                    default "private-page"
  engine             remotion | motion-canvas | live                           default "remotion" (studio new picks live for explainers)
  mode               background | interactive: an agent builds the video unattended, or the user
                     follows on the desk and the builder works chapter by chapter, note by note
                     default "background" ("interactive" when an older video says checkpoints: many)
  checkpoints        few | many: superseded by mode; still read from older videos
  poster             [clip, seconds] for the poster frame
  budget             minutes, over the level's defaults (stage): "first_cut", "round" and
                     "structural_round" (default 4 × round) for the scopes; any other key is a stage's
                     name, a budget for every run of that stage since the latest round mark (none
                     by default)
  keep_cuts          playable cuts kept by clean                               default 10
  teaching_contract  true: script check and review receipts gate narration and publish
  review_roles       extra script reviewers beyond those drive and level require
  max_rounds         cap on script review rounds per revision of the script, counted since the
                     latest structural stage mark (default by economy/thorough, reviews)
  economy, thorough  effort settings (review)
  frame_review       true: an independent frame review is required before publish
  script_check       {"accept": [...], "products": {...}, "product_budget": n, "number_budget": n}
  target_minutes     intended main-story length
  learner            path to the learner model (review)
  source             {"path", "commit"} of a repository the video explains (new)
  git                {"sign": true | false | null} for checkpoint commits
  pixel              {"grid": [w, h], "palette": [...]} (pixel genre)
  loop               true: a motion piece must loop seamlessly
  duration           seconds: the length of a piece with no narration (new --duration), the
                     timeline's base when there are no narration timings
  clips              [{"id", "title", "seconds"}]: such a piece in chapters, back to back, one
                     scene each; replaces duration (both may stay only if they agree)
"""

import json
from pathlib import Path

DEFAULTS = {
    "genre": "explainer",
    "level": "intro",
    "destination": "private-page",
    "engine": "remotion",
    "checkpoints": "few",
    "keep_cuts": 10,
}

MODES = ("background", "interactive")

CHOICES = {
    "checkpoints": ("few", "many"),
    "mode": MODES,
    "level": ("intro", "deep-dive"),
}


def raw(video):
    """The file as written, or {} when there is none."""
    f = Path(video) / "video.json"
    return json.loads(f.read_text()) if f.exists() else {}


def load(video):
    """video.json over the defaults, with enumerated values checked."""
    cfg = {**DEFAULTS, **raw(video)}
    cfg.setdefault("mode", "interactive" if cfg.get("checkpoints") == "many" else "background")
    for key, allowed in CHOICES.items():
        if cfg.get(key) not in allowed:
            raise SystemExit(f"video.json {key} must be one of {', '.join(allowed)} (got {cfg.get(key)!r})")
    return cfg


def get(video, key):
    return load(video).get(key)
