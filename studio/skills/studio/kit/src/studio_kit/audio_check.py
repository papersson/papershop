"""`studio audio-check VIDEO [--cut N]`: the soundtrack measured, since the kit cannot judge it by ear.

Every row is ok or a warning, except the pauses guard, which fails. All of it is measured on stems the
kit renders itself (audio.stem: one role's sub-bus as it sits in the mix, processed), at the master's
level (the finish's fixed gain applied to each), so nothing is unmixed. The report is written to
out/audio-check.json and printed a line a row; the exit status is 1 when a row failed. Effects are
named fxN, their place in audio/sfx.json (sfx.effect_id), in every row, sheet and timecode.

  sync      each effect placed on a named event (a cue name or an anchor in audio/sfx.json), or tagged
            with a `visual`: its contact in the effects stem against the event's frame, warning past
            SYNC_FRAMES (a build that lands on its cue, a riser or a swell, is timed by its end, and a
            kit recording by its transient peak, since its file has a lead-in). With a cut's video,
            the picture there (motion.frame_signal, PICTURE_WINDOW frames either side):
              untagged  the nearest start or end of motion, or cut, noted and not judged
              tagged    judged (`tagged`), the mark's offset from the event's frame reported in frames,
                        a warning past VISUAL_FRAMES, never a failure:
                          cut     a cut within 1 frame: a full-frame change, or the picture changing
                                  at a clip seam, since two scenes on one background change only their
                                  content and read as motion (motion.CUT_SHARE); a motion start
                                  anywhere else is not a cut
                          move    the peak speed of a move (its largest frame change) within 3 frames
                          land    where motion ends within 2
                          appear  where motion starts within 2 (an ease's first frames barely change)
            The tag says what the picture does, never when: the time is the cue's, the beat sheet's.
            Motion under way through the window has no start or end in it, so an `appear` over
            ambient motion can miss; the sheet and the motion review see it too.
  audible   each effect, in a window around its contact: masked when it lifts the narration and music
            there by under AUDIBLE_LIFT dB, both wideband and in its own band (an octave either side of
            its spectral centroid), and too quiet when its loudest 10 ms is more than AUDIBLE_UNDER dB
            under the voice's level, so an effect in a silent pause, which nothing masks, still warns
            when nobody would hear it at the volume the voice was set to
  loud      each effect's level (soundkit.level: K-weighted, its loudest 10 ms) against the voice's
            peaks (the VOICE_PEAK percentile of its own 10 ms levels), warning past LOUD_OVER dB; the
            kit's trims put every default recording where its synth voice is, and all of those pass
  ducking   music under speech against the music in the pauses (from 0.7 s after a sentence, once the
            duck has let go, in pauses of at least 1 s), warning under DUCK_MIN dB
  masking   per spoken word, the effects and music in 1-4 kHz against the narration in that band,
            warning when they come within MASK_MARGIN dB of it; the closest word is kept either way
  pauses    an effect rising over PAUSE_PEAK dBFS (in the effects stem, at the master's gain, before
            its limiter) during a spoken word fails, naming the part of the word it covers: effects belong in pauses (style.md), and the finish limits peaks, it
            does not unmask a word. A quiet effect under speech, below it, is allowed
  loudness  the master's integrated loudness and true peak against its target and ceiling, and the web
            copy's true peak when out/web.mp4 exists

Then what a person needs, in that order: the sound sheet to look at, and the timecodes to listen at.

  sheet     out/audio-sheet.png, the whole mix as a waveform and a spectrogram with a marker per
            effect (its id and tag, red when a row flagged it), a band per sentence and the masked
            words (sound_sheet.py), and out/audio-sheet/fxN.png, a close-up 0.6 s before to 0.9 s after
            each hero effect, with the frame grid and the frame where the picture does what the tag
            says. Heroes (`heroes`): the tagged effects, or the ones on named events when none is
            tagged, and always the loudest; at most HERO_MAX, loudest first.
  listen    about LISTEN_MAX timecodes for the one human listen (`listening`), each with its reasons:
            the tagged effect furthest from its picture, the closest masking margin (under
            LISTEN_MASK dB), the loudest effect, the music's first entry, then the heroes; moments
            within LISTEN_MERGE s are one. They go into the report with the soundtrack's stamp, so the
            listen checkpoint (publish's warning, the handoff, `review-status VIDEO listen passed`)
            uses them only for the mix they were chosen for (`moments`, `listen_hint`).

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
PEAK_WINDOW = 0.15       # seconds either side of an event searched for a recording's peak
PICTURE_WINDOW = 12      # frames either side of an event searched for picture motion
AUDIBLE_WINDOW = (-0.03, 0.15)  # seconds around an effect's contact where it must be heard
AUDIBLE_LIFT = 6.0       # dB an effect lifts the narration and music in its window, at least
AUDIBLE_UNDER = 30.0     # dB an effect's loudest 10 ms may sit under the voice's level, at most
# The picture a `visual` tag names, and how many frames from the event's frame its mark may fall:
# a cut is one frame, so it gets one; a move's fastest frame is broad, three; where motion ends or
# starts, two, since an ease's first or last frames change by less than the moving level.
VISUAL_FRAMES = {"cut": 1, "move": 3, "land": 2, "appear": 2}
MARKS = {"cut": "cut", "move": "move", "land": "motion end", "appear": "motion start"}
VERBS = {"cut": "cut", "move": "move", "land": "land", "appear": "show something appearing"}
# Loud: an effect's level (soundkit.level, the K-weighted loudest 10 ms) against the voice's peaks
# (the VOICE_PEAK percentile of its own 10 ms levels over its sentences), so like is measured against
# like. Calibrated on a Kokoro narration (af_heart): its 99th percentile sits 6.8 dB over its mean, the
# synth voices at gain 0 (which the kit's trims match) sit from 10.5 dB under those peaks (key-tick)
# to 4.3 dB over (thump), so every default passes at LOUD_OVER, and a +10 dB gain warns on every voice
# from confirm up (the untrimmed kit confirm sat 12.9 dB over the voice's mean).
LOUD_OVER = 6.0
VOICE_PEAK = 99


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


def _band_power(x, band=BAND):
    import numpy as np
    if len(x) < 64:
        return 0.0
    spectrum = np.abs(np.fft.rfft(x * np.hanning(len(x)))) ** 2
    freq = np.fft.rfftfreq(len(x), 1 / audio.RATE)
    return float(spectrum[(freq >= band[0]) & (freq <= band[1])].sum() / len(x))


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
    of the window after it, or for a build, the last within LANDING dB of the peak before it, or for a
    recording ("peak"), its transient peak in the window either side, found as the kit found it at
    curation (soundkit.contact), so the stem's peak is compared with the frame it was placed on."""
    import numpy as np
    r = audio.RATE
    if lands == "peak":
        from .soundkit import contact
        i0 = max(0, int((t0 - PEAK_WINDOW) * r))
        seg = y[i0:max(i0, int((t0 + PEAK_WINDOW) * r))]
        return None if not len(seg) or np.abs(seg).max() <= 0 else (i0 + contact(seg, r)) / r
    a, b = (t0 - 0.3, t0 + 0.05) if lands == "end" else (t0 - 0.1, t0 + 0.25)
    i0 = max(0, int(a * r))
    seg = np.abs(y[i0:max(i0, int(b * r))])
    if not len(seg) or seg.max() <= 0:
        return None
    over = np.nonzero(seg >= seg.max() * 10 ** ((LANDING if lands == "end" else ONSET) / 20))[0]
    return (i0 + (over[-1] if lands == "end" else over[0])) / r


def _signal(video, timeline, frame, cut):
    """The cut's frame signal over PICTURE_WINDOW frames either side of `frame` (motion.frame_signal)."""
    from . import motion
    first = max(0, frame - PICTURE_WINDOW)
    return motion.frame_signal(cut, tl.layout(video), timeline["fps"], first, 2 * PICTURE_WINDOW + 1)


def _picture(video, timeline, frame, cut, signal=None):
    """(the nearest frame around `frame` in a cut's video where picture motion starts or ends or the
    picture cuts, "starts", "ends" or "cut"); "throughout" when it moves through the whole window;
    None when nothing moves. Motion starts on the first frame that differs and ends on the last one
    that does (motion.frame_signal and its helpers)."""
    from . import motion
    fps = timeline["fps"]
    signal = _signal(video, timeline, frame, cut) if signal is None else signal
    edges = sorted([(f, "starts") for f in motion.starts(signal, fps)] + [(f, "ends") for f in motion.ends(signal, fps)]
                   + [(f, "cut") for f in motion.cuts(signal)], key=lambda e: e[0])
    if not edges:
        return "throughout" if motion.moving(signal, fps) else None
    return min(edges, key=lambda e: abs(e[0] - frame))


def seams(timeline):
    """The first frame of every clip after the first: where one scene cuts to the next."""
    return [tl.half_up(c["start"] * timeline["fps"]) for c in timeline.get("tracks", {}).get("scene", [])[1:]]


def _peaks(signal, fps):
    """The peak frame (the largest change) of each run of consecutive moving frames: where each move
    is fastest."""
    from . import motion
    on, runs = set(motion.moving(signal, fps)), []
    for f, change, *_ in signal:
        if f in on:
            if runs and runs[-1][-1][0] == f - 1:
                runs[-1].append((f, change))
            else:
                runs.append([(f, change)])
    return [max(run, key=lambda r: r[1])[0] for run in runs]


def tagged(signal, frame, visual, fps, cuts_at=()):
    """What the picture does nearest `frame` for an effect tagged `visual`: (its frame, what it is)
    or None when the window has none. The tag's mark: a cut (a full-frame change, or the picture
    changing at a clip seam in `cuts_at`, since a cut between two scenes on one background changes
    only their content and reads as motion, motion.CUT_SHARE); a move's peak speed (the largest
    change in a run of moving frames); where motion ends (a landing); where it starts (an
    appearance)."""
    from . import motion
    if visual == "cut":
        on = set(motion.moving(signal, fps))
        marks = [(f, "a cut") for f in motion.cuts(signal)] + \
            [(f, "a cut on one background (the picture changes at the clip seam)") for f in cuts_at if f in on]
    elif visual == "move":
        marks = [(f, "a move's peak speed") for f in _peaks(signal, fps)]
    elif visual == "land":
        marks = [(f, "motion ends") for f in motion.ends(signal, fps)]
    else:
        marks = [(f, "motion starts") for f in motion.starts(signal, fps)]
    return min(marks, key=lambda m: (abs(m[0] - frame), m[0]), default=None)


def _event(c, timeline):
    """The cue name or anchor an effect is placed on, or None for seconds or a beat."""
    if isinstance(c["t"], str) and c["t"] in timeline.get("cues", {}):
        return c["t"]
    return tl.describe_anchor(c["t"]) if isinstance(c["t"], dict) else None


def _note(pic, frame):
    """An untagged effect's picture note: the nearest motion edge or cut, not judged."""
    if pic == "throughout":
        return f"; picture: motion throughout {PICTURE_WINDOW} frames either side"
    if pic:
        return f"; picture: {'a cut' if pic[1] == 'cut' else 'motion ' + pic[1]} at frame {pic[0]} ({pic[0] - frame:+d})"
    return f"; picture: no motion within {PICTURE_WINDOW} frames"


def sync(stems, video, timeline, cut=None):
    """Rows: each effect on a named event, or tagged with a `visual`, its sound's contact against the
    event's frame; and, with a cut's video, the picture there. An untagged effect gets a note of the
    nearest motion edge, not judged; a tagged one is judged (`tagged`): its mark within
    VISUAL_FRAMES[tag] of the event's frame, or a warning with the offset measured."""
    from . import sfx
    f = Path(video) / "audio" / "sfx.json"
    if "sfx" not in stems.roles or not f.exists():
        return []
    fps, rows, at_seams = timeline["fps"], [], seams(timeline)
    for i, p in enumerate(sfx.place(json.loads(f.read_text()), timeline)):
        c, at, lands, visual = p.cue, p.time, p.sound.lands, p.cue.get("visual")
        name = _event(c, timeline)
        if name is None and not visual:
            continue                                       # seconds or a beat, untagged: nothing to be in sync with
        frame = tl.half_up(at * fps)                       # the event's frame, where the sound's contact belongs
        heard = _onset(stems["sfx"], frame / fps, lands)
        eid = sfx.effect_id(i)
        what = f"{eid} {c.get('type', p.sound.id)} on {name or f'{at:g} s'} (frame {frame})"
        row = {"check": "sync", "clip": "audio", "t": round(at, 2), "ok": True, "effect": eid, "frame": frame,
               **({"visual": visual} if visual else {})}
        if heard is None:
            row |= {"severity": "warning", "detail": f"{what}: no effect heard near it"}
        else:
            off = (heard - frame / fps) * fps
            row |= {"offset_frames": round(off, 2),
                    "detail": f"{what}: sound {off:+.1f} frames" + {"end": " (a build, timed by its end)",
                                                                      "peak": " (a recording, timed by its peak)"}.get(lands, "")}
            if abs(off) > SYNC_FRAMES:
                row["severity"] = "warning"
                row["detail"] += f"; more than {SYNC_FRAMES:g} frame off"
        if cut and visual:
            row |= _judged(_signal(video, timeline, frame, cut), frame, visual, fps, at_seams)
            if row.get("picture_ok") is False:
                row["severity"] = "warning"
        elif cut:
            row["detail"] += _note(_picture(video, timeline, frame, cut), frame)
        elif visual:
            row["detail"] += f"; picture ({visual}) not judged: no rendered cut"
        if visual and "picture" in row:
            row["detail"] += row.pop("picture")
        rows.append(row)
    return rows


def _judged(signal, frame, visual, fps, at_seams):
    """A tagged effect's picture verdict: {picture_frame, picture_offset_frames, picture_ok, picture
    (the detail's clause)}, its mark measured in frames from the event's frame."""
    tol = VISUAL_FRAMES[visual]
    mark = tagged(signal, frame, visual, fps, at_seams)
    if mark is None:
        return {"picture_ok": False, "picture": f"; picture ({visual}): no {MARKS[visual]} within {PICTURE_WINDOW} frames, "
                                                f"so the picture does not {VERBS[visual]} on this sound"}
    off = mark[0] - frame
    ok = abs(off) <= tol
    return {"picture_frame": mark[0], "picture_offset_frames": off, "picture_ok": ok,
            "picture": f"; picture ({visual}): {mark[1]} at frame {mark[0]} ({off:+d}), "
                       + (f"within {tol}" if ok else f"more than {tol} frame{'s' if tol > 1 else ''} off: the picture "
                                                      f"does not {VERBS[visual]} on this sound")}


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
    said, close, closest = words(timeline), [], (1e9, None, None, None)
    for w, a, b in said:
        voice = _band_power(stems.span("narration", a, b))
        if voice <= 0:
            continue
        rest = _band_power(stems.span("sfx", a, b) + stems.span("music", a, b))
        margin = _db(voice) - _db(rest)
        closest = min(closest, (margin, w, a, b)) if rest > 0 else closest
        if margin < MASK_MARGIN:
            close.append((margin, w, a, b))
    rows = [{"check": "masking", "clip": "audio", "t": round(a, 2), "ok": True, "severity": "warning", "margin_db": round(m, 1),
             "word": [round(a, 3), round(b, 3)],
             "detail": f"effects and music {m:.1f} dB under the word {w!r} at {a:.2f} s in 1-4 kHz (keep {MASK_MARGIN:g} dB)"}
            for m, w, a, b in sorted(close)[:20]]
    summary = {"check": "masking", "clip": "audio", "ok": True,
               **({"closest": {"word": closest[1], "t": round(closest[2], 2), "margin_db": round(closest[0], 1)}}
                  if closest[0] < 1e9 else {}),
               "detail": f"{len(said) - len(close)} of {len(said)} words clear by {MASK_MARGIN:g} dB in 1-4 kHz"
                         + (f"; the {len(rows)} closest above" if close else "")}
    if close:
        summary["severity"] = "warning"
    return rows + [summary]


# --- audibility: each effect heard ------------------------------------------------------------------

def _centroid(y):
    import numpy as np
    spectrum = np.abs(np.fft.rfft(np.asarray(y, dtype=np.float64))) ** 2
    freq = np.fft.rfftfreq(len(y), 1 / audio.RATE)
    return float((freq * spectrum).sum() / max(spectrum.sum(), 1e-20))


def _loudest(x, seconds=0.01):
    """The power of x's loudest `seconds` (its RMS over a sliding window, squared)."""
    import numpy as np
    k = max(1, min(len(x), int(seconds * audio.RATE)))
    if not len(x):
        return 0.0
    c = np.concatenate([[0.0], np.cumsum(x.astype(np.float64) ** 2)])
    return float(((c[k:] - c[:-k]) / k).max())


def _lift(effect, rest, band=None):
    """dB the effect raises the level of what plays with it, in `band` (Hz) or wideband: how far it
    stands out. A rest that is silent gives a lift too large to matter."""
    import numpy as np
    power = (lambda x: _band_power(x, band)) if band else (lambda x: float(np.mean(x.astype(np.float64) ** 2)))
    under = power(rest)
    return _db(power(effect + rest)) - _db(under) if under > 1e-12 else 99.0


def voice_level(stems, timeline):
    """The narration's level over its sentences in dBFS (the RMS of every spoken span: integrated over
    the voice, unweighted), or None without one."""
    import numpy as np
    spans = [stems.span("narration", s["start"], s["end"]) for s in timeline["tracks"].get("narration", [])]
    if "narration" not in stems.roles or not spans:
        return None
    power = float(np.mean(np.concatenate(spans).astype(np.float64) ** 2))
    return _db(power) if power > 0 else None


def voice_peaks(stems, timeline):
    """The voice's peaks in dB, K-weighted: the VOICE_PEAK percentile of its 10 ms levels (taken every
    millisecond) over its sentences, what an effect's soundkit.level is compared with; None without a
    narration."""
    import numpy as np
    from .soundkit import LEVEL_WINDOW, k_weighted
    if "narration" not in stems.roles or not timeline["tracks"].get("narration"):
        return None
    x, r = k_weighted(stems["narration"], audio.RATE), audio.RATE
    k, powers = int(LEVEL_WINDOW * r), []
    for s in timeline["tracks"]["narration"]:
        seg = x[max(0, int(s["start"] * r)):max(0, int(s["end"] * r))]
        if len(seg) > k:
            c = np.concatenate([[0.0], np.cumsum(seg ** 2)])
            powers.append(((c[k:] - c[:-k]) / k)[::r // 1000])
    if not powers:
        return None
    p = float(np.percentile(np.concatenate(powers), VOICE_PEAK))
    return _db(p) if p > 0 else None


def audibility(stems, video, timeline):
    """Rows: each placed effect heard or not, and the loud audit. In a window around its contact
    (AUDIBLE_WINDOW, within the sound's own span), the effects stem against the narration and music
    together: masked when it lifts them by under AUDIBLE_LIFT dB both wideband and in its own band (an
    octave either side of its spectral centroid); too quiet when its loudest 10 ms is more than
    AUDIBLE_UNDER dB under the voice's level, so an effect in a silent pause, unmasked, still has to be
    heard against the voice the listener set the volume by. Loud: a `loud` warning for each effect
    whose level over its whole span (soundkit.level, K-weighted) is more than LOUD_OVER dB over the
    voice's peaks (voice_peaks), else one ok row naming the loudest."""
    from . import sfx
    from .soundkit import level as k_level
    f = Path(video) / "audio" / "sfx.json"
    if "sfx" not in stems.roles or not f.exists():
        return []
    r, voice, rows, loud = audio.RATE, voice_level(stems, timeline), [], []
    peaks = voice_peaks(stems, timeline)
    others = [role for role in ("narration", "music") if role in stems.roles]
    for i, p in enumerate(sfx.place(json.loads(f.read_text()), timeline, strict=False, video=video)):
        if p.time is None:
            continue
        a = max(p.start, p.contact + int(AUDIBLE_WINDOW[0] * r)) / r
        b = max(min(p.end, p.contact + int(AUDIBLE_WINDOW[1] * r)) / r, a + 0.01)
        effect = stems.span("sfx", a, b)
        rest = sum((stems.span(role, a, b) for role in others), effect * 0)
        c = _centroid(p.sound.samples)
        band = (max(40.0, c / 2), min(20_000.0, c * 2))
        lift = max(_lift(effect, rest), _lift(effect, rest, band))
        level = _db(_loudest(effect))
        under = None if voice is None else voice - level
        eid = sfx.effect_id(i)
        what = f"{eid} {p.cue.get('type', p.sound.id)} at {p.time:.2f} s"
        heard = ("over silence" if lift >= 99 else f"lifts the bed {lift:.1f} dB") + f" around {c:.0f} Hz"
        over = None if peaks is None else float(k_level(stems.span("sfx", p.start / r, max(p.end, p.start + r // 100) / r), r) - peaks)
        row = {"check": "audible", "clip": "audio", "t": round(p.time, 2), "ok": True, "effect": eid,
               "lift_db": round(min(lift, 99.0), 1),
               "level_dbfs": round(level, 1), **({"under_voice_db": round(under, 1)} if under is not None else {}),
               **({"over_voice_peaks_db": round(over, 1)} if over is not None else {}),
               "detail": f"{what}: {heard}, its loudest 10 ms {level:.1f} dBFS"
                         + ("" if under is None else f", {abs(under):.1f} dB {'under' if under >= 0 else 'over'} the voice's level")}
        why = []
        if lift < AUDIBLE_LIFT:
            why.append(f"masked: it lifts the narration and music under {AUDIBLE_LIFT:g} dB (raise its gain or move it into a pause)")
        if under is not None and under > AUDIBLE_UNDER:
            why.append(f"too quiet: more than {AUDIBLE_UNDER:g} dB under the voice (raise its gain)")
        if why:
            row["severity"] = "warning"
            row["detail"] += "; " + "; ".join(why)
        rows.append(row)
        if over is not None and over > LOUD_OVER:
            loud.append({"check": "loud", "clip": "audio", "t": round(p.time, 2), "ok": True, "severity": "warning",
                         "effect": eid, "over_voice_peaks_db": round(over, 1),
                         "detail": f"{what}: {over:+.1f} dB against the voice's peaks (K-weighted, its loudest 10 ms), more "
                                   f"than {LOUD_OVER:g} dB over: lower its gain"})
    measured = [x for x in rows if "over_voice_peaks_db" in x]
    if measured and not loud:
        top = max(measured, key=lambda x: x["over_voice_peaks_db"])
        loud.append({"check": "loud", "clip": "audio", "ok": True,
                     "detail": f"no effect more than {LOUD_OVER:g} dB over the voice's peaks; the loudest, {top['effect']} at "
                               f"{top['t']:.2f} s, is at {top['over_voice_peaks_db']:+.1f} dB"})
    return rows + loud


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


# --- the effects, their heroes, the sheet and the listening timecodes ---------------------------------

HERO_MAX = 6            # close-ups on the sound sheet, at most
LISTEN_MAX = 5          # timecodes for the one human listen, at most
LISTEN_MERGE = 1.0      # seconds: moments this close are one place to listen, with every reason
LISTEN_MASK = MASK_MARGIN + 10.0    # dB: a closest masking margin wider than this is nothing to listen for


def effects(video, timeline, rows):
    """[{id, type, visual?, t, event, flags, over, picture_frame?}] for audio/sfx.json's effects placed
    on this timeline: what the sheet marks and the timecodes choose from. flags: what audio-check
    warned on for it (LOUD, MASKED, QUIET, SYNC for its sound, PICTURE for its tag, PAUSE when the
    pauses guard failed inside its span); over: its level against the voice's peaks, when measured;
    picture_frame: where the picture does what its tag says."""
    from . import sfx
    f = Path(video) / "audio" / "sfx.json"
    if not f.exists():
        return []
    out = []
    for i, p in enumerate(sfx.place(json.loads(f.read_text()), timeline, strict=False)):
        if p.time is None:
            continue
        eid, flags = sfx.effect_id(i), []
        mine = [r for r in rows if r.get("effect") == eid]
        for r in mine:
            warned = r.get("severity") == "warning"
            if r["check"] == "loud" and warned:
                flags.append("LOUD")
            elif r["check"] == "audible" and warned:
                flags += (["MASKED"] if "masked" in r["detail"] else []) + (["QUIET"] if "too quiet" in r["detail"] else [])
            elif r["check"] == "sync":
                if "offset_frames" not in r or abs(r["offset_frames"]) > SYNC_FRAMES:
                    flags.append("SYNC")
                if r.get("picture_ok") is False:
                    flags.append("PICTURE")
        if any(r["check"] == "pauses" and not r["ok"] and p.start <= r["overlap"][0] * audio.RATE < p.end for r in rows):
            flags.append("PAUSE")
        over = next((r["over_voice_peaks_db"] for r in mine if r["check"] == "audible" and "over_voice_peaks_db" in r), None)
        mark = next((r["picture_frame"] for r in mine if "picture_frame" in r), None)
        out.append({"id": eid, "type": p.cue.get("type") or p.sound.id.split(":", 1)[-1], "t": round(p.time, 3),
                    **({"visual": p.cue["visual"]} if p.cue.get("visual") else {}),
                    "event": _event(p.cue, timeline) is not None, "flags": flags, "over": over,
                    **({"picture_frame": mark} if mark is not None else {})})
    return out


def heroes(found):
    """The effects that get a close-up and a listen: the tagged ones (the author said the picture does
    something there), or when none is tagged the ones on named events; and always the loudest. At
    most HERO_MAX, loudest first."""
    picked = [e for e in found if e.get("visual")] or [e for e in found if e["event"]]
    loudest = max((e for e in found if e["over"] is not None), key=lambda e: e["over"], default=None)
    if loudest and loudest not in picked:
        picked.append(loudest)
    return sorted(picked, key=lambda e: -(e["over"] if e["over"] is not None else -999))[:HERO_MAX]


def timecode(t):
    """m:ss.s, as a player shows it."""
    return f"{int(t // 60)}:{t % 60:04.1f}"


def _name(e):
    return f"{e['id']} {e['type']}" + (f" ({e['visual']})" if e.get("visual") else "")


def listening(found, rows, timeline):
    """About LISTEN_MAX moments for the one human listen, each with its reasons: the tagged effect most
    out of sync with its picture, the closest masking margin (when under LISTEN_MASK dB), the loudest
    effect, the music's first entry, then the hero effects, flagged ones first. In that order of
    priority: past LISTEN_MAX a moment is dropped unless it is within LISTEN_MERGE s of one kept,
    where its reason joins. [{t, at, reasons}] in time order."""
    wanted = []
    judged = [r for r in rows if r["check"] == "sync" and r.get("visual") and "picture_ok" in r]
    if judged:
        worst = max(judged, key=lambda r: abs(r["picture_offset_frames"]) if "picture_offset_frames" in r else 99)
        off = (f"{worst['picture_offset_frames']:+d} frames" if "picture_offset_frames" in worst
               else f"no {MARKS[worst['visual']]} near it")
        wanted.append((worst["t"], f"{worst['effect']} ({worst['visual']}) is the tagged effect furthest from its picture: {off}"))
    closest = next((r["closest"] for r in rows if r["check"] == "masking" and "closest" in r), None)
    if closest and closest["margin_db"] < LISTEN_MASK:
        wanted.append((closest["t"], f"the closest masking margin: effects and music {closest['margin_db']:.1f} dB under the "
                                     f"word {closest['word']!r}"))
    loudest = max((e for e in found if e["over"] is not None), key=lambda e: e["over"], default=None)
    if loudest:
        wanted.append((loudest["t"], f"the loudest effect, {_name(loudest)}: {loudest['over']:+.1f} dB against the voice's peaks"))
    music = sorted(e["start"] for e in timeline["tracks"]["audio"] if tl.audio_role(e) == "music")
    if music:
        wanted.append((music[0], "the music's first entry"))
    wanted += [(e["t"], f"hero effect {_name(e)}" + (f" ({', '.join(e['flags'])})" if e["flags"] else ""))
               for e in sorted(heroes(found), key=lambda e: not e["flags"])]
    kept = []
    for t, why in wanted:
        near = next((m for m in kept if abs(m["t"] - t) <= LISTEN_MERGE), None)
        if near:
            near["reasons"].append(why)
        elif len(kept) < LISTEN_MAX:
            kept.append({"t": round(t, 2), "reasons": [why]})
    return [{**m, "at": timecode(m["t"])} for m in sorted(kept, key=lambda m: m["t"])]


def sheets(video, timeline, found, rows):
    """out/audio-sheet.png (the whole mix) and out/audio-sheet/fxN.png (a close-up of each hero), from
    audio/final.wav; returns their paths relative to the video, the overview first. Earlier close-ups
    are removed, so the folder holds this run's heroes only."""
    from . import sound_sheet
    video = Path(video)
    mix = video / "audio" / "final.wav"
    if not mix.exists():
        return []
    sentences = [{"id": s["id"], "start": s["start"], "end": s["end"]} for s in timeline["tracks"].get("narration", [])]
    masked = [tuple(r["word"]) for r in rows if r["check"] == "masking" and "word" in r]
    marks, out, made = found, video / "out", []
    out.mkdir(parents=True, exist_ok=True)
    sound_sheet.draw(mix, out / "audio-sheet.png", 0.0, timeline["duration"], marks, sentences, masked,
                     title=f"sound sheet  whole video  {timeline['duration']:.1f}s  (audio/final.wav)")
    made.append("out/audio-sheet.png")
    close = out / "audio-sheet"
    if close.exists():
        for old in close.glob("fx*.png"):
            old.unlink()
    for e in heroes(found):
        close.mkdir(parents=True, exist_ok=True)
        a, b = sound_sheet.closeup_span(e["t"])
        sound_sheet.draw(mix, close / f"{e['id']}.png", a, b, marks, sentences, masked, fps=timeline["fps"], width=1200,
                         title=f"close-up  {_name(e)} at {e['t']:.2f}s  frame {tl.half_up(e['t'] * timeline['fps'])}")
        made.append(f"out/audio-sheet/{e['id']}.png")
    return made


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
    rows = (sync(stems, video, timeline, movie if movie and movie.exists() else None) + audibility(stems, video, timeline)
            + ducking(stems, timeline)
            + ([] if estimate else masking(stems, timeline) + pauses(stems, timeline)) + loudness(video, record))
    return rows, n if movie else None


def main(args):
    video = Path(args.video)
    tl.build(video, quiet=True)
    rows, n = run(video, args.cut)
    timeline = tl.load(video)
    found = effects(video, timeline, rows)
    moments = listening(found, rows, timeline)
    drawn = sheets(video, timeline, found, rows)
    out = video / "out" / "audio-check.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"cut": n, "soundtrack": audio.revision(video, timeline),
                               "thresholds": {"sync_frames": SYNC_FRAMES, "duck_min_db": DUCK_MIN,
                                              "mask_margin_db": MASK_MARGIN, "pause_peak_dbfs": PAUSE_PEAK,
                                              "audible_lift_db": AUDIBLE_LIFT, "audible_under_voice_db": AUDIBLE_UNDER,
                                              "loud_over_voice_peaks_db": LOUD_OVER, "visual_frames": VISUAL_FRAMES},
                               "effects": found, "heroes": [e["id"] for e in heroes(found)], "sheets": drawn,
                               "listen": moments, "rows": rows}, indent=1) + "\n")
    for r in rows:
        mark = "FAIL" if not r["ok"] else "WARN" if r.get("severity") == "warning" else "ok  "
        print(f"{mark}  {r['check']:9} {r['detail']}")
    if drawn:
        print(f"sound sheet: {', '.join(drawn)} (look at it first: markers per effect, flagged ones red)")
    if moments:
        print("listen at:" + "".join(f"\n  {m['at']}  {'; '.join(m['reasons'])}" for m in moments))
    print(f"{len(rows)} rows, {sum(not r['ok'] for r in rows)} failed, {sum(r.get('severity') == 'warning' for r in rows)} "
          f"warnings → {out}" + ("" if n is None else f" (picture from cut {n})"))
    return 1 if any(not r["ok"] for r in rows) else 0


def moments(video):
    """(the listening timecodes audio-check chose for the current mix, or None when out/audio-check.json
    is missing or was made for another mix): what the listen checkpoint asks the user to hear."""
    f = Path(video) / "out" / "audio-check.json"
    if not f.exists():
        return None
    report = json.loads(f.read_text())
    try:
        current = audio.revision(video)
    except audio.MixUnavailable:
        return None
    return report.get("listen") if report.get("soundtrack") == current else None


def listen_hint(video, shown=None):
    """The timecodes as a clause for publish's warning and the handoff: "at 0:02.8 (hero effect
    ...), ..." or how to get them. `shown`: the video as the message writes it."""
    found = moments(video)
    if found is None:
        return f"run `studio audio-check {shown or video}` first for the timecodes to listen at"
    if not found:
        return "anywhere: audio-check chose no timecodes"
    return "at " + ", ".join(f"{m['at']} ({m['reasons'][0]})" for m in found)
