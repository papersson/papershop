"""video.json, read in one place.

Every key the kit reads is listed here with its default and meaning, so a new setting has one home
and a reader of the code can see the whole schema. `load` returns the file merged over DEFAULTS;
keys without a default are simply absent when unset (callers use .get).

  title              the video's name (new)
  version            "v1", "v2", ... (new, revisions)
  genre              explainer | motion | launch | pixel | footage            default "explainer"
  drive              author | learner (explainers)
  level              intro | deep-dive                                         default "intro"
  tone               plain | comic: comic only when the user asks for a comic, cartoon or silly
                     video (references/taste/comic.md); "fun" or "engaging" is plain polish
                     default "plain"
  delivery           polished | session: a session video is a modest cut of the user's own
                     learning or work session: one review cycle (max_rounds and motion_rounds
                     default to 1), a 540p desk cut, visual-first staging (references/session.md)
                     default "polished"
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
                     by default). Advisory, except that in background mode a stage stops at twice
                     its own budget
  keep_cuts          playable cuts kept by clean                               default 10
  teaching_contract  true: script check and review receipts gate narration and publish
  review_roles       extra script reviewers beyond those drive and level require
  max_rounds         cap on script review rounds per revision of the script, counted since the
                     latest structural stage mark (default by economy/thorough, reviews)
  economy, thorough  effort settings (review)
  frame_review       true: an independent frame review is required before publish
  motion_rounds      cap on motion review rounds per cut lineage (counted since the latest
                     structural stage mark); the review stops at a round with no must-fix
                     findings or at the cap. Raised only when the user asks     default 2 (reviews)
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
  legend             {meaning: colour}: the video's colour legend, each colour a theme name of its
                     engine or #rrggbb; `studio check` (legend.py) holds the scenes to it and the
                     look sheet draws it
  gl                 cpu | gpu: where the live engine's 3D stage renders WebGL. cpu is SwiftShader,
                     Chrome's CPU renderer: identical frames run after run on a machine, about 3.5x
                     slower per 3D frame than the GPU. gpu is this machine's GPU (Metal on macOS):
                     3D frames cost what 2D ones do, but its pixels differ from the CPU's, 2D ones
                     included, so clips are keyed on it (keys.engine_inputs)     default "cpu"
  motion             full | reduced: reduced takes shake and hitstop out of every scene that uses
                     the feel helpers (templates/live/scenes/example-feel.js), for viewers sensitive to
                     motion; live scenes read it as c.motion, so clips are keyed on it  default "full"
  sound              {"room": 1.0, "duck": true, "presence": true}: the mix's processing of effects
                     and music (audio.py): room scales their shared room's reflections (0 or false:
                     off, up to 2), duck lowers music under the narration, presence dips their 1-4 kHz
                     band while it speaks. A narration alone is never processed
"""

import json
from pathlib import Path

DEFAULTS = {
    "genre": "explainer",
    "level": "intro",
    "tone": "plain",
    "delivery": "polished",
    "destination": "private-page",
    "engine": "remotion",
    "checkpoints": "few",
    "keep_cuts": 10,
    "gl": "cpu",
    "motion": "full",
}

MODES = ("background", "interactive")

CHOICES = {
    "checkpoints": ("few", "many"),
    "mode": MODES,
    "level": ("intro", "deep-dive"),
    "tone": ("plain", "comic"),
    "delivery": ("polished", "session"),
    "gl": ("cpu", "gpu"),
    "motion": ("full", "reduced"),
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


def update(video, **values):
    """Set keys in video.json, checked as load checks them (and an engine against the engines), and
    write it back in the file's form; returns the file as written."""
    from .engine import ENGINES
    cfg = {**raw(video), **values}
    for key, allowed in CHOICES.items():
        if key in values and values[key] not in allowed:
            raise SystemExit(f"video.json {key} must be one of {', '.join(allowed)} (got {values[key]!r})")
    if "engine" in values and values["engine"] not in ENGINES:
        raise SystemExit(f"video.json engine must be one of {', '.join(ENGINES)} (got {values['engine']!r})")
    (Path(video) / "video.json").write_text(json.dumps(cfg, indent=1) + "\n")
    return cfg


def get(video, key):
    return load(video).get(key)
