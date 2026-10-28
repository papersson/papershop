"""The `studio` command. Every kit operation is a subcommand, so the agent needs one entry point.

Each command is a row of COMMANDS: its help, its arguments, and the "module:function" that runs it.
Modules load only when their command runs, so `studio doctor` works before anything is installed.
A video argument is checked while parsing, before any handler or lock: a mistyped path stops with
the nearest videos, instead of becoming a new folder.
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




# --- video arguments -------------------------------------------------------------------------------

def video(arg):
    """ARG as a path, when it is a video folder (one holding video.json)."""
    p = Path(arg).expanduser()
    if (p / "video.json").is_file():
        return p.resolve()
    import difflib
    from .env import studio_home
    home = studio_home()
    folders = [f for f in (home, home / "films") if f.is_dir()]
    videos = {d.name: d for f in folders for d in f.iterdir() if (d / "video.json").is_file()}
    near = difflib.get_close_matches(p.resolve().name, list(videos), n=5, cutoff=0.5)
    lines = [f"{arg} is not a video: " + (f"{p.resolve()} has no video.json" if p.is_dir() else f"no folder at {p.resolve()}")]
    if near:
        lines += [f"nearest videos in {home}:"] + [f"  {videos[n]}" for n in near] + ["pass the video's path"]
    else:
        lines += [f"no video in {home} has a similar name; `studio new NAME` makes one"]
    raise SystemExit("\n".join(lines))


def changed_video(arg):
    """A video the command changes: checked as `video`, and main runs it under the operation lock."""
    return video(arg)


def path(arg):
    """ARG as an absolute path, resolved against the caller's directory while parsing: a handler or a
    script under `studio run` (which works in the video's folder) never reads it from another one."""
    return Path(arg).expanduser().resolve()


# --- the commands: name -> (help, [(argument names, options)], handler) ---------------------------
# An argument is A (plain), V (a video folder that must exist), W (one the command also changes) or
# P (a file or folder path, made absolute).
# The name of a new video is plain.

def A(*names, **kw):
    return names, kw


def V(*names, **kw):
    return A(*names, type=video, **kw)


def W(*names, **kw):
    return A(*names, type=changed_video, **kw)


def P(*names, **kw):
    return A(*names, type=path, **kw)


COMMANDS = {
    "preflight": ("check prerequisites without installs, downloads or browser/model launches", [
        V("video", nargs="?", help="check this video's selected engine and narration requirements"),
        A("--engine", choices=["live"], help="engine to check (default: live, or the video's engine)"),
        A("--extra", action="append", choices=["audio", "align", "kokoro"], help="check only these extras (default: kokoro and align, or the video's requirements)"),
        A("--silent", action="store_true", help="no narration extras for a video without speech"),
    ], "doctor:main_preflight"),
    "doctor": ("check the environment and print fixes", [
        V("video", nargs="?", help="diagnose extras required by this video"),
        A("--fetch", action="store_true", help="install the engines' node packages and headless browser first"),
        A("--net", action="store_true", help="also check the hosts downloads come from"),
        A("--extra", action="append", default=[], choices=["audio", "align", "kokoro"], help="with --fetch: a Python extra to install (audio, align, kokoro)"),
        A("--engine", action="append", default=[], choices=["live"], help="with --fetch, install the live engine"),
        A("--speech", action="store_true", help="smoke-test local narration and recognition; may download model weights"),
        A("--sounds", action="store_true", help="with --fetch: fetch the sound kit (recorded CC0 effects), verified, into the cache; the engines too only with --engine or --extra, or when live is not installed"),
    ], "doctor:main"),
    "ablation": ("prepare paired bare-agent and Studio video folders and prompts", [A("--topic", default="shaders")], "ablation:main"),
    "new": ("a video folder, ready for a script", [
        A("name"),
        P("--dir", help="where to create it (default: $STUDIO_HOME/films/NAME when films/ exists, else $STUDIO_HOME/NAME; STUDIO_HOME defaults to ~/studio)"),
        A("--title"),
        V("--from", dest="from_video", help="inherit look and pronunciation from a series episode"),
        A("--include", action="append", default=[], help="relative source/data file to copy from --from (repeatable)"),
        P("--source", help="the repo or folder the video explains; its path and commit are recorded"),
        A("--duration", type=float, help="seconds for a silent scene test"),
        A("--engine", choices=["live"], help="which engine renders the scenes (default: live)"),
    ], "new:main"),
    "narrate": ("narration from SCRIPT.md into audio/ and the timeline", [
        W("video"),
        A("--plan", action="store_true", help="report cached chunks and what would be synthesised"),
        A("--estimate", action="store_true", help="timings from word counts, no audio"),
        A("--list", action="store_true", help="print the sentence ids"),
        A("--fetch-only", action="store_true", help="elevenlabs: fill the response cache and stop"),
        A("--yes", action="store_true", help="elevenlabs: spend credits past the confirmation limit"),
        P("--config", help="another settings file instead of narration.json"),
    ], "narration:main"),
    "voice-check": ("transcribe every sentence and score it against the script", [
        W("video"), A("--model", default="small.en"),
        A("--below", type=float, default=0.8, help="flag sentences scoring under this"),
        A("--all", action="store_true", help="transcribe every sentence again, ignoring the cache"),
    ], "voice_check:main"),
    "align": ("word timings for the narration; re-chunk captions", [W("video"), A("--model", default="small.en")], "align:main"),
    "timeline": ("build timeline.json from its sources (after editing cues/<clip>.json or audio/tracks.json)", [
        W("video"), A("--events", action="store_true", help="also list the beat sheet: every cue's time, frame, clip and anchor"),
    ], "timeline:main"),
    "capture": ("a screenshot of a page into assets/, recorded with its source", [
        A("url"), W("video"), A("--name"), A("--size", default="1440x900"),
        A("--wait", type=int, default=4000, help="virtual milliseconds to let the page settle"),
    ], "assets:main_capture"),
    "asset": ("add a file to assets/ with its provenance, copy in a sound kit sound, or list them", [
        A("action", choices=["add", "library", "restore", "list"]), W("video"),
        A("file", nargs="?", help="add: the file; library: a sound kit id, or PACK:MEMBER"),
        A("--kind", default="supplied", choices=["capture", "generated", "supplied"]),
        A("--source", help="a URL, a prompt and tool, or a person"), A("--license", default=""),
        A("--name", help="the file's name in assets/ (library: the sound's id, in assets/sounds/)"),
        A("--credits", action="store_true", help="list: the CREDITS block for the page or description"),
    ], "assets:main_asset"),
    "audio": ("finish the whole mix: 48 kHz, one fixed gain to the target loudness, a true-peak limiter", [
        W("video"),
        A("--lufs", type=float, default=-16.0, help="target integrated loudness (default -16; -14 for social)"),
        A("--peak", type=float, default=-1.5, help="true-peak ceiling in dBTP"),
    ], "audio:main"),
    "beats": ("a beat grid (bpm, beats, downbeats, hits) from a music track, into audio/beats.json and the timeline", [W("video"), P("file")], "beats:main"),
    "sfx": ("effects from a cues file, on the timeline: synth voices, or sound kit recordings landing on their peak", [
        W("video"), P("cues", help='JSON list of {"t": seconds | cue or beat name | anchor, "type": "click", '
                                   '"sound": "synth:NAME" | "kit:ID" | "kit" (the type\'s default recording), "gain": dB, '
                                   '"params": {freq, decay, length} (synths only), "visual": "cut" | "move" | "land" | '
                                   '"appear" (what the picture does on its frame, which audio-check judges)}; sound is '
                                   'optional (the type\'s synth voice); a kit sound is copied into assets/sounds/ and '
                                   'plays at its trim'),
    ], "sfx:main"),
    "sound-lab": ("a page to choose effects by listening: each type's synth candidates and kit recordings", [V("video")], "sfx:main_lab"),
    "audio-check": ("measure the soundtrack: effect sync (a recording by its peak) and each tagged effect's picture, each effect heard and none too loud, ducking, masking, the pauses guard and loudness, into out/audio-check.json; draw the sound sheet (out/audio-sheet.png) and choose the timecodes to listen at", [
        W("video"), A("--cut", type=int, help="the cut whose picture the sync rows look at (default: the latest rendered one)"),
    ], "audio_check:main"),
    "stage": ("record elapsed stage time (--report: the table)", [
        V("video"), A("name", nargs="?"), A("--report", action="store_true"),
    ], "stage:main"),
    "event": ("append a production fact for the desk (agents or hooks)", [
        V('video'), A('kind'), A('message', nargs='*'), A('--lane'), A('--t', type=float),
        A('--source'), A('--check'), A('--hook', action='store_true', help='read Claude hook JSON from stdin; retain metadata only'),
        P('--rollout', help='import only activity metadata from this explicitly associated Codex rollout'),
        A('--follow', action='store_true', help='keep following --rollout; no synthetic heartbeats'),
    ], 'events:main'),
    "open": ("open and protect a playable cut", [V("video"), A("cut", nargs="?", type=int)], "cuts:main_open"),
    "commit": ("checkpoint this video's sources, respecting git.sign", [W("video"), A("message")], "checkpoint:main"),
    "media": ("push: upload the media a clone can't remake to the bucket and list it in media.json; pull: fetch what media.json lists", [
        A("action", choices=["push", "pull"]), W("video"),
        A("paths", nargs="*", help="push: also list these files (default: the ignored media outside caches, cuts and reviews)"),
        A("--dry-run", action="store_true", help="pull: only say what is present and what would be fetched"),
        A("--force", action="store_true", help="pull: replace a file that differs from media.json"),
    ], "media:main"),
    "plate": ("render a chapter's plate (video.json plates) in Blender, or probe how long it will take", [
        W("video"), A("clips", nargs="*", help="the chapters (default: every plated chapter)"),
        A("--quality", default="draft", choices=["draft", "final"]),
        A("--probe", type=int, nargs="?", const=6, help="render N frames spread over the clip and estimate the rest"),
    ], "plates:main"),
    "typing": ("type code into an editor from a plan: the editor's steps (data/typing.json), cues and key sounds",
               [W("video"), P("plan", help="the plan: sources, bursts of edits, the run (typecode.py)")], "typecode:main"),
    "lexicon": ("promote a pronunciation to STUDIO_HOME/lexicon.json", [
        A("action", choices=["add"]), A("word"), A("--spoken"), A("--phonemes"),
    ], "preferences:main_lexicon"),
    "run": ("run a builder's Python or node script with the kit, in the video's folder", [
        V("video"), A("script", help="a .py, .mjs or .js file inside the video (sims/, .studio/work, scenes)"),
        A("args", nargs=argparse.REMAINDER, help="passed to the script"),
        A("--allow-outside", action="store_true", help="run a script outside the video's folder"),
    ], "run:main"),
    "still": ("render the frame at clip time t", [
        W("video"), A("clip"), A("t", type=float), P("--out", required=True),
        A("--layers", default="all", choices=LAYERS), A("--scale", type=float, default=1.0),
    ], _engine_call),
    "boxes": ("pixel boxes of the labelled elements at clip time t", [V("video"), A("clip"), A("t", type=float)], _engine_call),
    "duration": ("a clip's length as the engine computes it", [V("video"), A("clip")], _engine_call),
    "render": ("render one clip as a silent video", [
        W("video"), A("clip"), P("--out", required=True),
        A("--quality", default="draft", choices=["draft", "final"]), A("--range", nargs=2, type=float, metavar=("A", "B")),
    ], _engine_call),
    "cut": ("make the next cut: stills, changed clips, composite", [
        W("video"), A("--quality", default="draft", choices=["draft", "final"]),
        A("--stills-only", action="store_true", help="stills only (a look gate, or a quick answer)"),
        P("--changelog", help="JSON list of {note, change} answering the previous cut's notes"),
    ], _cut),
    "reel": ("narrate and hold the story boards to the real voice, with a pacing report", [W("video")], "reel:main"),
    "panel": ("one parallel reading of the brief by an expert, viewer and editor", [V("video")], "panel:main"),
    "suggest": ("import reviewer findings as suggested notes for the user on the desk", [V("video"), P("file")], "suggest:main"),
    "review-pack": ("combine motion windows, frame stills and sound for one chapter reviewer", [
        V("video"), A("--chapter", required=True), A("--cut", type=int),
    ], "review_pack:main"),
    "shoot": ("narrate and write a separate brief for each parallel chapter agent", [W("video")], "shoot:main"),
    "boards": ("a stills cut of every chapter's board (boards/boards.json, notes from the screen notes)", [
        W("video"),
    ], "boards:main"),
    "animatic": ("stills or boards held to the narration, with its audio, and a pacing report", [
        W("video"), A("--boards", action="store_true", help="boards for every chapter (default: scenes, boards where a chapter has none)"),
    ], "animatic:main"),
    "export": ("the whole video in several formats (16:9, 9:16, 1:1) from one timeline, into out/export/", [
        W("video"), A("--formats", default="16:9,9:16,1:1"),
        A("--quality", default="final", choices=["draft", "final"]),
        A("--lufs", type=float, default=-16.0, help="finish the mix to this loudness (default -16; -14 for social)"),
    ], "render:main_export"),
    "clean": ("remove stale caches and unprotected draft previews; keep cut videos by default and print what it freed", [
        W("video"), A("--dry-run", action="store_true", help="only print what would be removed"),
        A("--videos", action="store_true", help="also remove eligible unprotected old draft videos"),
    ], "clean:main"),
    "check": ("length, determinism, bounds, band and contrast checks", [
        W("video"), A("--chapter", help="check one chapter in its private work folder"), A("--samples", type=int, default=3, help="moments per clip"),
        A("--only", help="comma-separated checks, including script (no browser required)"),
        A("--format", help="check this format's layout (9:16, 1:1); default 16:9"),
        A("--all", action="store_true", help="check every chapter, not only those changed since their last pass"),
    ], "check:main"),
    "sheets": ("contact sheets, a phone-width sheet, strips and full-resolution label crops", [
        W("video"), P("outdir"), A("--cut", type=int),
        A("--strip", nargs=2, action="append", metavar=("CLIP", "T"), help="12 consecutive frames around T (repeatable)"),
        P("--windows", metavar="FILE", help="JSON list of strips {clip, t, frames?, fps?}"),
        A("--below", type=float, default=40, help="crop labels under this many px tall"),
    ], "sheets:main"),
    "look-sheet": ("the model sheet: every element in each state, in the video's theme, layout and engine, into out/look/", [
        W("video"), A("--format", help="this format's layout (9:16, 1:1); default 16:9"),
    ], "look:main"),
    "desk": ("the desk: play the latest cut, take notes on sentences, show progress and replies",
             [V("video"), A("--port", type=int, help="default: the first free port from 8765"), A('--foreground', action='store_true', help=argparse.SUPPRESS)], "page:main_serve"),
    "serve": ("alias of desk", [V("video"), A("--port", type=int, help="default: the first free port from 8765"), A('--foreground', action='store_true', help=argparse.SUPPRESS)], "page:main_serve"),
    "notes": ("the notes on a cut, numbered; --start / --resolve mark one", [
        V("video"), A("--cut", type=int), A("--start", metavar="ID", help="mark a note as being worked on"),
        A("--accept", metavar="ID", help="accept a suggested note at the user’s request"),
        A("--dismiss", metavar="ID", help="dismiss a suggested note at the user’s request"),
        A("--resolve", metavar="ID", help="mark a note done"), A("--reply", help="one line shown under a resolved note"),
    ], "page:main_notes"),
    "glossary": ("the motion glossary: words a note can use for motion, and the helper behind each", [
        A("--term", help="one term, or the terms a note's text mentions"),
    ], "glossary:main"),
    "wait": ("block until a new note arrives on the desk, then print it", [
        V("video"), A("--timeout", type=float, help="give up after this many seconds (exit 2)"), A('--chapter', help='only this lane and whole-video notes'),
    ], "page:main_wait"),
    "status": ("set the builder's status line on the desk (no text clears it)", [
        V("video"), A("text", nargs="*"), A("--busy", action="store_true", help="show it as work in progress"),
    ], "page:main_status"),
    "publish": ("final cut, web encode, poster and the page in out/page/", [W("video"), A("--by", help="record who said ship it; use after the user’s decision")], "publish:main"),
}


# Engine calls share renderer caches, so their operation lock waits for the current writer.
ENGINE_READS = {"boxes", "duration"}


def reads_only(args):
    return ((args.cmd == "clean" and args.dry_run) or (args.cmd == "check" and args.chapter)
            or (args.cmd == "media" and args.action == "pull" and args.dry_run))


def build_parser():
    p = argparse.ArgumentParser(prog="studio", description="Drive the studio kit.")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, (help_, arguments, _) in COMMANDS.items():
        sp = sub.add_parser(name, help=help_)
        for names, kw in arguments:
            sp.add_argument(*names, **kw)
    return p


def script_args(argv):
    """(the arguments to parse, a script's own arguments or None): everything after `run`'s SCRIPT
    goes to the script verbatim, where argparse would drop a `--` that follows it."""
    if argv[:1] != ["run"] or "-h" in argv[:3] or "--help" in argv[:3]:
        return argv, None
    positional = [i for i, a in enumerate(argv) if i and not a.startswith("-")]
    return (argv[:positional[1] + 1], argv[positional[1] + 1:]) if len(positional) > 1 else (argv, None)


def main(argv=None):
    argv, verbatim = script_args(list(sys.argv[1:] if argv is None else argv))
    args = build_parser().parse_args(argv)
    if verbatim is not None:
        args.args = verbatim
    _, arguments, handler = COMMANDS[args.cmd]
    if isinstance(handler, str):
        module, func = handler.split(":")
        handler = getattr(importlib.import_module(f".{module}", __package__), func)
    changes = any(kw.get("type") is changed_video for _, kw in arguments)
    if (changes and not reads_only(args)) or args.cmd in ENGINE_READS:
        from .workspace import operation
        with operation(args.video):
            return handler(args) or 0
    return handler(args) or 0


if __name__ == "__main__":
    sys.exit(main())
