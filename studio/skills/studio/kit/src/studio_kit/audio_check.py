"""`studio audio-check VIDEO [--cut N]`: the soundtrack measured, since the kit cannot judge it by ear.

Every row is ok or a warning, except the pauses guard, which fails. All of it is measured on stems the
kit renders itself (audio.stem: one role's sub-bus as it sits in the mix, processed), at the master's
level (the finish's fixed gain applied to each), so nothing is unmixed. The report is written to
out/audio-check.json and printed a line a row; the exit status is 1 when a row failed.

  sync      each effect placed on a named event (a cue name or an anchor in audio/sfx.json): its onset in
            the effects stem against the event's frame, warning past SYNC_FRAMES (a build that lands on
            its cue, a riser or a swell, is timed by its end). With a cut's video, the nearest start or
            end of picture motion around the event is noted too, not judged: a contact is a start for a
            pop and an end for a landing, and the beat sheet already gives both one frame.
  ducking   music under speech against the music in the pauses (from 0.7 s after a sentence, once the
            duck has let go, in pauses of at least 1 s), warning under DUCK_MIN dB
  masking   per spoken word, the effects and music in 1-4 kHz against the narration in that band,
            warning when they come within MASK_MARGIN dB of it
  pauses    an effect rising over PAUSE_PEAK dBFS (in the effects stem, at the master's gain, before
            its limiter) during a spoken word fails, naming the part of the word it covers: effects belong in pauses (style.md), and the finish limits peaks, it
            does not unmask a word. A quiet effect under speech, below it, is allowed
  loudness  the master's integrated loudness and true peak against its target and ceiling, and the web
            copy's true peak when out/web.mp4 exists

`studio check` runs the pauses guard as its `pauses` check whenever the soundtrack has an effect
(audio/sfx.json, or an audio/tracks.json entry with role sfx) and a narration, so publish, whose gate
is the full check, stops on it; the other rows are this command's. Both measure at the target the
mix was last finished to, so a check after `export --lufs -14` does not re-finish it at -16.
"""
import json
from pathlib import Path

from . import audio
from . import timeline as tl

SYNC_FRAMES = 1.0
DUCK_MIN = 6.0           # dB the music drops under speech, at least
DUCK_RELEASE = 0.7       # seconds after a sentence before the pause is measured
MASK_MARGIN = 10.0       # dB the effects and music stay under a word in its presence band
PAUSE_PEAK = -24.0       # dBFS an effect may peak at under a word
BAND = (1000, 4000)
ONSET = -20.0            # dB under the effect's peak that marks its onset
LANDING = -10.0          # dB under its peak that marks where a build ends (above the room's reflections)
PICTURE_WINDOW = 12      # frames either side of an event searched for picture motion


def _mono(f):
    import numpy as np
    import soundfile as sf
    y, rate = sf.read(f, dtype="float32", always_2d=True)
    assert rate == audio.RATE, f"{f}: {rate} Hz"
    return y.mean(axis=1) if y.shape[1] > 1 else y[:, 0]


def _db(power):
    import math
    return 10 * math.log10(power) if power > 1e-20 else -200.0


def words(timeline):
    """[(word, start, end)] of the narration, from its word timings (or shared out by characters)."""
    out = []
    for s in timeline["tracks"].get("narration", []):
        caption = s.get("caption", s.get("text", "")).split()
        out += [(w, a, b) for w, (a, b) in zip(caption, tl._word_times(s, caption))]
    return out


class Stems:
    """The video's stems at the master's level, rendered (and cached) on first use."""

    def __init__(self, video, timeline, record):
        self.video, self.timeline = Path(video), timeline
        self.files = audio.sources(self.video, timeline)
        self.roles = {tl.audio_role(e) for e, _ in self.files}
        self.gain = 10 ** ((record or {}).get("gain_db", 0) / 20)
        self._cache = {}

    def __getitem__(self, role):
        import numpy as np
        if role not in self._cache:
            n = int(self.timeline["duration"] * audio.RATE)
            y = _mono(audio.stem(self.video, self.timeline, role, self.files)) * self.gain if role in self.roles else np.zeros(n, "float32")
            self._cache[role] = np.pad(y, (0, max(0, n - len(y))))[:n]
        return self._cache[role]

    def span(self, role, a, b):
        return self[role][max(0, int(a * audio.RATE)):max(0, int(b * audio.RATE))]


def _band_power(x):
    import numpy as np
    if len(x) < 64:
        return 0.0
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freq = np.fft.rfftfreq(len(x), 1 / audio.RATE)
    return float(spectrum[(freq >= BAND[0]) & (freq <= BAND[1])].sum() / len(x))


# --- pauses: the guard ----------------------------------------------------------------------------

def pauses(stems, timeline):
    """Rows: a failure for every spoken word an effect rises over PAUSE_PEAK during, naming the part of
    the word it is over the line and its peak there, else one ok row. Levels are at the master's gain,
    before its limiter (which takes the peaks past the ceiling down, and unmasks nothing)."""
    import numpy as np
    if "sfx" not in stems.roles:
        return []
    said = words(timeline)
    bad, line = [], 10 ** (PAUSE_PEAK / 20)
    for w, a, b in said:
        seg = np.abs(stems.span("sfx", a, b))
        over = np.nonzero(seg > line)[0]
        if not len(over):
            continue
        a0 = max(0, int(a * audio.RATE))
        x, y = (a0 + over[0]) / audio.RATE, (a0 + over[-1] + 1) / audio.RATE
        peak = 20 * np.log10(float(seg[over].max()))
        bad.append({"check": "pauses", "clip": "audio", "t": round(x, 2), "ok": False, "peak_dbfs": round(peak, 1),
                    "overlap": [round(x, 3), round(y, 3)],
                    "detail": f"an effect is over {PAUSE_PEAK:g} dBFS for {x:.2f}-{y:.2f} s of the word {w!r} "
                              f"({a:.2f}-{b:.2f} s), peaking there at {peak:.1f} dBFS at the master's gain, before its "
                              f"limiter: move it into a pause or keep it under {PAUSE_PEAK:g} dBFS"})
    return bad or [{"check": "pauses", "clip": "audio", "ok": True,
                    "detail": f"no effect over {PAUSE_PEAK:g} dBFS under any of {len(said)} spoken words"}]


def has_effects(video, timeline):
    """Whether the soundtrack has an effect: audio/sfx.json's, or any audio entry with role sfx."""
    return (Path(video) / "audio" / "sfx.json").exists() or any(tl.audio_role(e) == "sfx" for e in timeline["tracks"]["audio"])


def finished(video, timeline):
    """The finish record for the current mix, made at the target and ceiling it was last finished to
    (after `export --lufs -14` it stays at -14), else at the defaults."""
    done = audio._record(video)
    if done:
        return audio.finish(video, done["target_lufs"], done["ceiling_dbtp"], timeline=timeline)
    return audio.finish(video, timeline=timeline)


def guard(video, timeline=None):
    """The pauses guard as `studio check` runs it: rows, empty when there are no effects or no words to
    guard (a piece with no narration, by design), skipped while the narration is an estimate."""
    video = Path(video)
    timeline = timeline or tl.load(video)
    if not timeline["tracks"].get("narration") or not has_effects(video, timeline):
        return []
    if tl.timing(video, timeline) == "estimate":
        return [{"check": "pauses", "clip": "audio", "ok": True, "skipped": True,
                 "detail": "no narration audio yet: the guard runs once `studio narrate` has voiced it"}]
    try:
        import numpy, soundfile  # noqa: F401
    except ImportError:
        from .sfx import NEEDS
        raise SystemExit(NEEDS)
    return pauses(Stems(video, timeline, finished(video, timeline)), timeline)


# --- sync -----------------------------------------------------------------------------------------

def _onset(y, t0, lands):
    """The effect's contact near t0 in stem y, in seconds: the first sample within ONSET dB of the peak
    of the window after it, or for a build, the last within LANDING dB of the peak before it."""
    import numpy as np
    r = audio.RATE
    a, b = (t0 - 0.3, t0 + 0.05) if lands == "end" else (t0 - 0.1, t0 + 0.25)
    i0 = max(0, int(a * r))
    seg = np.abs(y[i0:max(i0, int(b * r))])
    if not len(seg) or seg.max() <= 0:
        return None
    over = np.nonzero(seg >= seg.max() * 10 ** ((LANDING if lands == "end" else ONSET) / 20))[0]
    return (i0 + (over[-1] if lands == "end" else over[0])) / r


def _picture(video, timeline, frame, cut):
    """(the nearest frame where picture motion starts or ends, "starts" or "ends") around `frame` in a
    cut's video; "throughout" when it moves through the whole window; None when nothing moves."""
    from . import motion, proc
    fps = timeline["fps"]
    first = max(0, frame - PICTURE_WINDOW)
    count = 2 * PICTURE_WINDOW + 1
    w, h = motion.PACING_SIZE
    crop = motion._crop(tl.layout(video))
    raw = proc.ffmpeg("-ss", f"{max(0.0, (first - 0.5) / fps):.4f}", "-i", str(cut), "-frames:v", str(count),   # half a frame early: frame `first` exactly
                      "-vf", f"scale={w}:{h},crop={w}:{crop}:0:0,format=gray", "-f", "rawvideo", "-",
                      capture_output=True).stdout
    frames = [raw[i:i + w * crop] for i in range(0, len(raw) - w * crop + 1, w * crop)]
    level = motion.MOVE_LEVEL * motion.PACING_FPS / fps
    # moving[k]: frame first+k+1 differs from frame first+k. Motion starts on the first frame that
    # differs, and ends on the last one that does.
    moving = [sum(map(abs, map(int.__sub__, x, y))) / (w * crop) > level for x, y in zip(frames, frames[1:])]
    edges = [(first + k + 1, "starts") if now else (first + k, "ends")
             for k, (was, now) in enumerate(zip(moving, moving[1:]), 1) if was != now]
    if not edges:
        return "throughout" if any(moving) else None
    return min(edges, key=lambda e: abs(e[0] - frame))


def sync(stems, video, timeline, cut=None):
    """Rows: each effect on a named event, its onset against the event's frame."""
    from . import sfx
    f = Path(video) / "audio" / "sfx.json"
    if "sfx" not in stems.roles or not f.exists():
        return []
    fps, rows = timeline["fps"], []
    for p in sfx.place(json.loads(f.read_text()), timeline):
        c, at, lands = p.cue, p.time, p.sound.lands
        name = c["t"] if isinstance(c["t"], str) and c["t"] in timeline.get("cues", {}) else None
        if name is None and not isinstance(c["t"], dict):
            continue                                       # seconds or a beat: no event to be in sync with
        frame = tl.half_up(at * fps)                       # the event's frame, where the sound's contact belongs
        heard = _onset(stems["sfx"], frame / fps, lands)
        what = f"{c['type']} on {name or tl.describe_anchor(c['t'])} (frame {frame})"
        if heard is None:
            rows.append({"check": "sync", "clip": "audio", "t": round(at, 2), "ok": True, "severity": "warning",
                         "detail": f"{what}: no effect heard near it"})
            continue
        off = (heard - frame / fps) * fps
        pic = _picture(video, timeline, frame, cut) if cut else None
        note = "" if not cut else (f"; picture: motion throughout {PICTURE_WINDOW} frames either side" if pic == "throughout"
                                    else f"; picture: motion {pic[1]} at frame {pic[0]} ({pic[0] - frame:+d})" if pic
                                    else f"; picture: no motion within {PICTURE_WINDOW} frames")
        row = {"check": "sync", "clip": "audio", "t": round(at, 2), "ok": True, "offset_frames": round(off, 2),
               "detail": f"{what}: sound {off:+.1f} frames" + (" (a build, timed by its end)" if lands == "end" else "") + note}
        if abs(off) > SYNC_FRAMES:
            row["severity"] = "warning"
            row["detail"] += f"; more than {SYNC_FRAMES:g} frame off"
        rows.append(row)
    return rows


# --- ducking and masking --------------------------------------------------------------------------

def ducking(stems, timeline):
    import numpy as np
    if "music" not in stems.roles:
        return []
    said = sorted((s["start"], s["end"]) for s in timeline["tracks"].get("narration", []))
    if not said:
        return [{"check": "ducking", "clip": "audio", "ok": True, "detail": "music with no narration: nothing to duck under"}]
    speech = np.concatenate([stems.span("music", a, b) for a, b in said])
    gaps = [(b + DUCK_RELEASE, n) for (_, b), (n, _) in zip(said, said[1:] + [(timeline["duration"], None)]) if n - b >= 1.0]
    rest = [stems.span("music", a, b) for a, b in gaps]
    if not rest:
        return [{"check": "ducking", "clip": "audio", "ok": True, "detail": "no pause of 1 s or more to compare the music in"}]
    under, free = _db(float(np.mean(speech ** 2))), _db(float(np.mean(np.concatenate(rest) ** 2)))
    duck = free - under
    row = {"check": "ducking", "clip": "audio", "ok": True, "duck_db": round(duck, 1),
           "detail": f"music {under:.1f} dBFS under speech, {free:.1f} dBFS in the pauses: ducked {duck:.1f} dB"}
    if duck < DUCK_MIN:
        row["severity"] = "warning"
        row["detail"] += f", under {DUCK_MIN:g} dB (video.json sound.duck, or the track's gain)"
    return [row]


def masking(stems, timeline):
    if not stems.roles & {"sfx", "music"} or "narration" not in stems.roles:
        return []
    said, close = words(timeline), []
    for w, a, b in said:
        voice = _band_power(stems.span("narration", a, b))
        if voice <= 0:
            continue
        rest = _band_power(stems.span("sfx", a, b) + stems.span("music", a, b))
        margin = _db(voice) - _db(rest)
        if margin < MASK_MARGIN:
            close.append((margin, w, a))
    rows = [{"check": "masking", "clip": "audio", "t": round(a, 2), "ok": True, "severity": "warning",
             "detail": f"effects and music {m:.1f} dB under the word {w!r} at {a:.2f} s in 1-4 kHz (keep {MASK_MARGIN:g} dB)"}
            for m, w, a in sorted(close)[:20]]
    summary = {"check": "masking", "clip": "audio", "ok": True,
               "detail": f"{len(said) - len(close)} of {len(said)} words clear by {MASK_MARGIN:g} dB in 1-4 kHz"
                         + (f"; the {len(rows)} closest above" if close else "")}
    if close:
        summary["severity"] = "warning"
    return rows + [summary]


# --- loudness -------------------------------------------------------------------------------------

def loudness(video, record):
    if record is None:
        return [{"check": "loudness", "clip": "audio", "ok": True, "detail": "a silent soundtrack: nothing to finish"}]
    video = Path(video)
    got, tp = audio.measure(video / "audio" / "final.wav")
    row = {"check": "loudness", "clip": "audio", "ok": True, "lufs": got, "true_peak_dbtp": tp,
           "detail": f"master {got:.1f} LUFS (target {record['target_lufs']:g}), true peak {tp:.1f} dBTP "
                     f"(ceiling {record['ceiling_dbtp']:g})"}
    if audio.missed({**record, "lufs": got, "true_peak_dbtp": tp}):
        row["severity"] = "warning"
    rows = [row]
    web = video / "out" / "web.mp4"
    if web.exists():
        wtp = audio.measure(web)[1]
        rows.append({"check": "loudness", "clip": "web", "ok": True, "true_peak_dbtp": wtp,
                     "detail": f"out/web.mp4 true peak {wtp:.1f} dBTP (ceiling {record['ceiling_dbtp']:g})",
                     **({"severity": "warning"} if wtp > record["ceiling_dbtp"] + 0.1 else {})})
    return rows


def run(video, cut=None):
    """All rows. `cut`: a cut's number for the picture notes (default: the latest rendered cut)."""
    from . import cuts, render
    video = Path(video)
    timeline = tl.load(video)
    audio.require_voice(video, timeline)
    try:
        import numpy, soundfile  # noqa: F401
    except ImportError:
        from .sfx import NEEDS
        raise SystemExit(NEEDS)
    record = finished(video, timeline)
    stems = Stems(video, timeline, record)
    n = cut or cuts.latest(video, cuts.RENDERED)
    rec = render.read_cut(video, n) if n else None
    movie = render.cuts_dir(video) / f"cut{n}" / rec["video"] if rec and rec.get("video") else None
    if cut and movie is None:
        raise SystemExit(f"cut {cut} has no rendered video")
    estimate = tl.timing(video, timeline) == "estimate"
    rows = (sync(stems, video, timeline, movie if movie and movie.exists() else None) + ducking(stems, timeline)
            + ([] if estimate else masking(stems, timeline) + pauses(stems, timeline)) + loudness(video, record))
    return rows, n if movie else None


def main(args):
    video = Path(args.video)
    tl.build(video, quiet=True)
    rows, n = run(video, args.cut)
    out = video / "out" / "audio-check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"cut": n, "thresholds": {"sync_frames": SYNC_FRAMES, "duck_min_db": DUCK_MIN,
                                                        "mask_margin_db": MASK_MARGIN, "pause_peak_dbfs": PAUSE_PEAK},
                               "rows": rows}, indent=1) + "\n")
    for r in rows:
        mark = "FAIL" if not r["ok"] else "WARN" if r.get("severity") == "warning" else "ok  "
        print(f"{mark}  {r['check']:9} {r['detail']}")
    print(f"{len(rows)} rows, {sum(not r['ok'] for r in rows)} failed, {sum(r.get('severity') == 'warning' for r in rows)} "
          f"warnings → {out}" + ("" if n is None else f" (picture from cut {n})"))
    return 1 if any(not r["ok"] for r in rows) else 0
