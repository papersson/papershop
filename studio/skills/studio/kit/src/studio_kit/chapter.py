"""Private render inputs let chapter agents check their work without shared writes."""
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

from . import timeline as tl
from .workspace import atomic_json


def validate(video, clip):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", clip):
        raise SystemExit(f"invalid chapter id {clip!r}")
    if clip not in {c["id"] for c in tl.load(video)["tracks"]["scene"]}:
        raise SystemExit(f"no chapter {clip}")
    return clip


@contextmanager
def working_copy(video, clip):
    """Copy source inputs so renderers and timeline migration only write in this chapter's cache."""
    video = Path(video).resolve()
    validate(video, clip)
    cache = video / ".cache" / "chapters" / clip
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=cache, prefix="work-") as folder:
        work = Path(folder)
        for name in ("video.json", "layout.json", "narration.json", "timeline.json", "captions.json", "cues.json",
                     "SCRIPT.md", "lexicon.json", "audio", "scenes", "data", "assets", "boards", "sims"):
            src, dst = video / name, work / name
            if src.is_dir():
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns("node_modules", ".cache", ".git"))
            elif src.is_file():
                shutil.copy2(src, dst)
        # Every chapter's cues, since a shared log (data/screens.json) can anchor on another chapter's
        # cue, such as a desktop that arrives in an earlier chapter. Only this chapter's file is its own:
        # if another chapter's cues don't build, this chapter checks against its own and says why.
        if (video / "cues").is_dir():
            (work / "cues").mkdir()
            for f in sorted((video / "cues").glob("*.json")):
                shutil.copy2(f, work / "cues" / f.name)
        try:
            timeline = tl.build(work, quiet=True)
        except SystemExit as e:
            others = [f for f in (work / "cues").glob("*.json") if f.name != f"{clip}.json"]
            if not others:
                raise
            for f in others:
                f.unlink()
            timeline = tl.build(work, quiet=True)
            print(f"{clip}: checked without other chapters' cues, which don't build: {e}")
        yield work, timeline


def check(video, clip, samples=3, only=None, fmt=None):
    from . import events
    from . import check as checks
    from .engine import Engine
    with working_copy(video, clip) as (work, timeline):
        # Keep other chapter ids in the timeline: cache keys need to distinguish their code from helpers.
        kinds = only or list(checks.CHECKS) + ["legible", "overlap", "pacing", "flash", "inframe", "occluded"]
        rows = checks.run(work, samples, kinds, fmt=fmt, chapter=clip)
        output = Path(video) / ".cache" / "chapters" / clip
        stills = [{"clip": clip, "t": r["t"], "out": str(output / f"frame-{i}.png"), "scale": 0.5}
                  for i, r in enumerate(checks.sample_times(timeline, samples, {clip}))]
        if set(kinds) - {"script", "pauses", "staging", "code-view"}:
            Engine(work, fmt=fmt).stills(stills)
        atomic_json(output / "check.json", rows)
        start = tl.clip(timeline, clip)['start']
        run = events.emit(video, 'checks.ran', 'Chapter checks ran', lane=clip,
                          source=f'.cache/chapters/{clip}/check.json')['id']
        for row in rows:
            if row.get('t') is not None:
                events.emit(video, 'check.passed' if row.get('ok') else 'check.failed', row.get('detail', ''),
                            lane=clip, t=start + row['t'], check=row['check'], run=run,
                            source=f'.cache/chapters/{clip}/check.json')
    print(f"Chapter checks and stills: {output}")
    return rows
