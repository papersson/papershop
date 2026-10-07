"""The `studio` command. Every kit operation is a subcommand, so the agent needs one entry point.

Each command is a row of COMMANDS: its help, its arguments, and the "module:function" that runs it.
Modules load only when their command runs, so `studio doctor` works before anything is installed.
"""
import argparse
import importlib
import json
import sys
from pathlib import Path

LAYERS = ["all", "no-captions", "no-band", "background"]


# --- handlers that are only a few lines --------------------------------------------------------

def _engine_call(args):
    from .engine import Engine
    e = Engine(args.video)
    if args.cmd == "still":
        r = e.still(args.clip, args.t, args.out, args.layers, args.scale)
    elif args.cmd == "boxes":
        r = e.boxes(args.clip, args.t)
    elif args.cmd == "render":
        r = e.render(args.clip, args.out, args.quality, args.range)
    else:
        r = e.duration(args.clip)
    print(json.dumps(r))
    return 0


def _cut(args):
    from .render import make_cut
    log = json.loads(Path(args.changelog).read_text()) if args.changelog else None
    rec = make_cut(args.video, args.quality, args.stills_only, log)
    done = [c["id"] for c in rec["clips"] if c["rendered"]]
    what = "stills only" if args.stills_only else f"rendered {', '.join(done) or 'no clips (all cached)'}"
    m = rec["media"]
    print(f"cut {rec['cut']}: {what}; {m['width']}×{m['height']}, {m['fps']:g} fps; "
          f"quality={rec['quality']}, final={str(rec['final']).lower()}; seconds {rec['seconds']}")
    return 0


def _import_tutor(args):
    from . import timeline
    t = timeline.from_tutor(args.lesson, args.video)
    print(f"{len(t['tracks']['scene'])} clips, {len(t['tracks']['narration'])} sentences, "
          f"{t['duration']:.1f} s → {args.video}/timeline.json")
    return 0


# --- the commands: name -> (help, [(argument names, options)], handler) ---------------------------

def A(*names, **kw):
    return names, kw


COMMANDS = {
    "doctor": ("check the environment and print fixes", [
        A("video", nargs="?", help="diagnose extras required by this video"),
        A("--fetch", action="store_true", help="install the engines' node packages and headless browser first"),
        A("--net", action="store_true", help="also check the hosts downloads come from"),
        A("--extra", action="append", default=[], choices=["audio", "align", "kokoro"], help="with --fetch: a Python extra to install (audio, align, kokoro)"),
        A("--engine", action="append", default=[], choices=["motion-canvas"], help="with --fetch: also install this engine (Remotion always is)"),
    ], "doctor:main"),
    "new": ("a video folder, ready for a script", [
        A("name"),
        A("--dir", help="where to create it (default: $STUDIO_HOME/NAME, STUDIO_HOME defaults to ~/studio)"),
        A("--title"),
        A("--drive", default="author", choices=["author", "learner"]),
        A("--genre", default="explainer", choices=["explainer", "motion", "launch", "pixel", "footage"]),
        A("--from", dest="from_video", help="inherit look and pronunciation from a series episode"),
        A("--include", action="append", default=[], help="relative source/data file to copy from --from (repeatable)"),
        A("--source", help="the repo or folder the video explains; its path and commit are recorded"),
        A("--duration", type=float, help="seconds: a piece with no narration script (motion, launch), timed by its scenes"),
        A("--engine", choices=["remotion", "motion-canvas"], help="which engine renders the scenes"),
        A("--checkpoints", choices=["few", "many"],
          help="few (default): narrative, look and cuts; many: also boards, the animatic, the first finished chapter and each chapter"),
        A("--level", choices=["intro", "deep-dive"],
          help="intro: scaffold 3-4 key ideas (default); deep-dive: more detail and evidence"),
    ], "new:main"),
    "variant": ("a sibling video for another audience: same evidence, assets and look, a new script", [
        A("source"), A("name"), A("--dir"), A("--title"),
        A("--learner", help="the new audience's learner model"), A("--vocabulary", help="the new audience's glossary"),
    ], "new:main_variant"),
    "narrate": ("narration from SCRIPT.md into audio/ and the timeline", [
        A("video"),
        A("--plan", action="store_true", help="report cached chunks and what would be synthesised"),
        A("--estimate", action="store_true", help="timings from word counts, no audio"),
        A("--list", action="store_true", help="print the sentence ids"),
        A("--fetch-only", action="store_true", help="elevenlabs: fill the response cache and stop"),
        A("--yes", action="store_true", help="elevenlabs: spend credits past the confirmation limit"),
        A("--config", help="another settings file instead of narration.json"),
    ], "narration:main"),
    "voice-check": ("transcribe every sentence and score it against the script", [
        A("video"), A("--model", default="small.en"),
        A("--below", type=float, default=0.8, help="flag sentences scoring under this"),
        A("--all", action="store_true", help="transcribe every sentence again, ignoring the cache"),
    ], "voice_check:main"),
    "align": ("word timings for the narration; re-chunk captions", [A("video"), A("--model", default="small.en")], "align:main"),
    "capture": ("a screenshot of a page into assets/, recorded with its source", [
        A("url"), A("video"), A("--name"), A("--size", default="1440x900"),
        A("--wait", type=int, default=4000, help="virtual milliseconds to let the page settle"),
    ], "assets:main_capture"),
    "asset": ("add a file to assets/ with its provenance, or list them", [
        A("action", choices=["add", "list"]), A("video"), A("file", nargs="?"),
        A("--kind", default="supplied", choices=["capture", "generated", "supplied"]),
        A("--source", help="a URL, a prompt and tool, or a person"), A("--license", default=""), A("--name"),
    ], "assets:main_asset"),
    "init": ("pin the kit a video is made with, so a plugin update can't change how it renders", [
        A("video"), A("--update", action="store_true", help="replace the pinned copy's sources with the plugin's current ones"),
    ], "pin:main"),
    "audio": ("the audio finish: 48 kHz, one fixed gain to the target loudness, a true-peak limiter", [
        A("video"),
        A("--lufs", type=float, default=-16.0, help="target integrated loudness (default -16; -14 for social)"),
        A("--peak", type=float, default=-1.5, help="true-peak ceiling in dBTP"),
    ], "audio:main"),
    "ingest": ("a recording: transcript with word times, shot changes, filler marks, a paper edit", [
        A("file"), A("video"), A("--name"), A("--model", default="small.en"),
    ], "footage:main_ingest"),
    "edit": ("build the timeline from an edit list of footage segments", [A("video"), A("edl", help="JSON list of {src, in, out, gain}")], "footage:main_edit"),
    "beats": ("a beat grid (bpm, beats, downbeats, hits) from a music track, into the timeline", [A("video"), A("file")], "beats:main"),
    "sfx": ("synthesised effects from a cues file, on the timeline", [A("video"), A("cues", help="JSON list of {t, type, gain}")], "sfx:main"),
    "sound-lab": ("a page to choose effect candidates by listening", [A("video")], "sfx:main_lab"),
    "stage": ("mark the start of a stage; print time spent against the video's budget (--report: the table)", [
        A("video"), A("name", nargs="?"), A("--report", action="store_true"),
        A("--kind", choices=["local", "structural"], default="local"),
        A("--summary", help="revision refactoring entry: merge/trim plan and expected runtime change"),
    ], "stage:main"),
    "review": ("one round of fresh-context reviewers on SCRIPT.md or a narrative", [
        A("video"), A("round", type=int),
        A("--narrative", help="review this narrative file instead of the script"),
        A("--only", default="expert,student,editor"),
    ], "review:main"),
    "open": ("open and protect a playable cut", [A("video"), A("cut", nargs="?", type=int)], "cuts:main_open"),
    "commit": ("checkpoint this video's sources, respecting git.sign", [A("video"), A("message")], "checkpoint:main"),
    "steps": ("run program versions in scratch projects and record evidence", [A("video"), A("manifest")], "steps:main"),
    "lexicon": ("promote a pronunciation to STUDIO_HOME/lexicon.json", [
        A("action", choices=["add"]), A("word"), A("--spoken"), A("--phonemes"),
    ], "preferences:main_lexicon"),
    "lock": ("claim a video folder across stages", [
        A("video"), A("action", choices=["acquire", "release", "status"]), A("--owner", default="builder"),
        A("--recover", action="store_true", help="explicitly recover an abandoned owner's lease"),
    ], "workspace:main_lock"),
    "request": ("queue or resolve a mid-flight request", [
        A("video"), A("text", nargs="?"), A("--resolve", metavar="ID"),
    ], "workspace:main_request"),
    "review-frames": ("prepare a fresh frame-review bundle or import its result", [
        A("video"), A("--cut", type=int), A("--result", help="review response including its REVISION and FRAMES verdict"),
    ], "review_state:main_frames"),
    "review-status": ("record an unavailable or explicitly waived review", [
        A("video"), A("role", choices=["student", "expert", "editor", "frames"]),
        A("status", choices=["unavailable", "waived"]), A("--reason"),
    ], "review_state:main_status"),
    "still": ("render the frame at clip time t", [
        A("video"), A("clip"), A("t", type=float), A("--out", required=True),
        A("--layers", default="all", choices=LAYERS), A("--scale", type=float, default=1.0),
    ], _engine_call),
    "boxes": ("pixel boxes of the labelled elements at clip time t", [A("video"), A("clip"), A("t", type=float)], _engine_call),
    "duration": ("a clip's length as the engine computes it", [A("video"), A("clip")], _engine_call),
    "render": ("render one clip as a silent video", [
        A("video"), A("clip"), A("--out", required=True),
        A("--quality", default="draft", choices=["draft", "final"]), A("--range", nargs=2, type=float, metavar=("A", "B")),
    ], _engine_call),
    "cut": ("make the next cut: stills, changed clips, composite", [
        A("video"), A("--quality", default="draft", choices=["draft", "final"]),
        A("--stills-only", action="store_true", help="stills only (a look gate, or a quick answer)"),
        A("--changelog", help="JSON list of {note, change} answering the previous cut's notes"),
    ], _cut),
    "boards": ("a stills cut of every chapter's board (boards/boards.json, notes from the screen notes)", [
        A("video"),
    ], "boards:main"),
    "animatic": ("stills or boards held to the narration, with its audio, and a pacing report", [
        A("video"), A("--boards", action="store_true", help="boards for every chapter (default: scenes, boards where a chapter has none)"),
    ], "animatic:main"),
    "export": ("the whole video in several formats (16:9, 9:16, 1:1) from one timeline, into out/export/", [
        A("video"), A("--formats", default="16:9,9:16,1:1"),
        A("--quality", default="final", choices=["draft", "final"]),
        A("--lufs", type=float, help="finish the audio to this loudness first (-14 for social)"),
    ], "render:main_export"),
    "clean": ("remove stale caches and unprotected draft previews; keep cut videos by default and print what it freed", [
        A("video"), A("--dry-run", action="store_true", help="only print what would be removed"),
        A("--videos", action="store_true", help="also remove eligible unprotected old draft videos"),
    ], "clean:main"),
    "check": ("length, determinism, bounds, band and contrast checks", [
        A("video"), A("--samples", type=int, default=3, help="moments per clip"),
        A("--only", help="comma-separated checks, including script and code-source (no browser required)"),
        A("--format", help="check this format's layout (9:16, 1:1); default 16:9"),
        A("--all", action="store_true", help="check every chapter, not only those changed since their last pass"),
    ], "check:main"),
    "sheets": ("contact sheets, a phone-width sheet, strips and full-resolution label crops", [
        A("video"), A("outdir"), A("--cut", type=int),
        A("--strip", nargs=2, metavar=("CLIP", "T"), help="12 consecutive frames around T"),
        A("--below", type=float, default=40, help="crop labels under this many px tall"),
    ], "sheets:main"),
    "serve": ("serve the review page for the latest cut", [A("video"), A("--port", type=int, default=8765)], "page:main_serve"),
    "notes": ("the notes on a cut, numbered", [A("video"), A("--cut", type=int)], "page:main_notes"),
    "publish": ("final cut, web encode, poster and the page in out/page/", [A("video")], "publish:main"),
    "import-tutor": ("make a video's timeline from a tutor lesson", [A("lesson"), A("video")], _import_tutor),
}


def build_parser():
    p = argparse.ArgumentParser(prog="studio", description="Drive the studio kit.")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, (help_, arguments, _) in COMMANDS.items():
        sp = sub.add_parser(name, help=help_)
        for names, kw in arguments:
            sp.add_argument(*names, **kw)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    handler = COMMANDS[args.cmd][2]
    if isinstance(handler, str):
        module, func = handler.split(":")
        handler = getattr(importlib.import_module(f".{module}", __package__), func)
    mutating = {"narrate", "align", "voice-check", "cut", "boards", "animatic", "render", "still", "check", "sheets", "export", "clean", "publish",
                "init", "audio", "capture", "asset", "ingest", "edit", "beats", "sfx", "steps", "commit", "stage"}
    if args.cmd in mutating and not (args.cmd == "clean" and args.dry_run):
        from .workspace import operation
        with operation(args.video):
            return handler(args) or 0
    return handler(args) or 0


if __name__ == "__main__":
    sys.exit(main())
