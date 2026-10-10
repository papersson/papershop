"""`studio music VIDEO --bed`: an optional quiet bed, generated, for the mix to duck under the voice.

A pad of slow chords, one a bar of four beats from a small progression in the key (major I-vi-IV-V,
minor i-VI-III-VII), each note two slightly detuned sines that swell in and cross-fade into the next
chord, and a soft low knock on every beat, a little stronger on the downbeat. It is numpy and no
randomness, so the same settings write the same file. It goes to audio/bed.wav and registers itself
in audio/tracks.json as a music track (the mix ducks it under speech and puts it in the effects'
room), at a gain that sits it BED_UNDER LU under the narration as measured now (under -20 LUFS before
there is one). It also writes audio/beats.json with its grid, so `beat_N` and `downbeat_N` cues
land on its pulse. A re-narration does not move the bed's level: run it again to re-level it.

Off by default: an explainer has no music (style.md), and the bed is an opt-in for when the user
asks for one. Melodic motifs are out of scope; they belong to a comic video, made by hand.
`--remove` takes the bed, its track entry and its grid out again.
"""
import json
import math
from pathlib import Path

from . import timeline as tl
from .workspace import atomic_json

RATE = 48_000
BED = "audio/bed.wav"
BED_UNDER = 20.0          # LU under the narration, before ducking
NO_VOICE = -20.0          # LUFS assumed for a narration not yet made
NOTES = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6,
         "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}
# (semitones above the key, minor) for each bar, repeated
PROGRESSIONS = {"major": ((0, False), (9, True), (5, False), (7, False)),
                "minor": ((0, True), (8, False), (3, False), (10, False))}
ATTACK, RELEASE, FADE_IN, FADE_OUT = 0.8, 0.8, 2.0, 3.0


def parse_key(key):
    """(the tonic's semitone above C, "major" or "minor") from "C", "F#", "Bb" or "Am"."""
    name, mode = (key[:-1], "minor") if key.endswith("m") and key[:-1] in NOTES else (key, "major")
    if name not in NOTES:
        raise SystemExit(f"--key {key!r}: a note (C, F#, Bb, ...) with m for minor (Am)")
    return NOTES[name], mode


def grid(seconds, bpm):
    """Beat times from 0 for `seconds` at `bpm`."""
    step = 60 / bpm
    return [round(k * step, 4) for k in range(int(seconds / step) + 1) if k * step < seconds]


def render(seconds, key="C", bpm=72.0):
    """The bed as a float32 array at RATE, peaking at -6 dBFS."""
    import numpy as np
    tonic, mode = parse_key(key)
    n = int(seconds * RATE)
    out = np.zeros(n, dtype=np.float32)
    bar = 4 * 60 / bpm
    root = 48 + tonic                                 # the C below middle C, moved to the key
    for b in range(math.ceil(seconds / bar)):
        step, minor = PROGRESSIONS[mode][b % 4]
        start, end = b * bar, min((b + 1) * bar + RELEASE, seconds)
        i0, i1 = int(start * RATE), int(end * RATE)
        t = np.arange(i1 - i0) / RATE
        env = np.minimum(1, t / ATTACK) ** 2 * np.clip((end - start - t) / RELEASE, 0, 1)
        chord = np.zeros(len(t))
        for semis in (0, 3 if minor else 4, 7, 12):
            f = 440 * 2 ** ((root + step + semis - 69) / 12)
            chord += np.sin(2 * math.pi * f * 0.9985 * t) + np.sin(2 * math.pi * f * 1.0015 * t) + 0.2 * np.sin(4 * math.pi * f * t)
        out[i0:i1] += (chord * env * 0.05).astype(np.float32)
    knock = np.arange(int(0.25 * RATE)) / RATE
    knock = (np.sin(2 * math.pi * (70 - 40 * knock) * knock) * np.exp(-knock * 18)
             + 0.3 * np.sin(2 * math.pi * 180 * knock) * np.exp(-knock * 30)) * np.minimum(1, knock / 0.004)   # a body small speakers play
    for k, at in enumerate(grid(seconds, bpm)):
        i = int(at * RATE)
        seg = knock[:n - i] * (0.35 if k % 4 == 0 else 0.22)
        out[i:i + len(seg)] += seg.astype(np.float32)
    t = np.arange(n) / RATE
    out *= (np.minimum(1, t / FADE_IN) * np.clip((seconds - t) / FADE_OUT, 0, 1)).astype(np.float32)
    peak = float(np.abs(out).max()) or 1.0
    return out * (0.5 / peak)


def _length(video):
    if (Path(video) / "timeline.json").exists():
        return tl.load(video)["duration"]
    from . import settings
    return settings.get(video, "duration")


def voice_lufs(video):
    """The narration's integrated loudness with its gain, or NO_VOICE before there is one."""
    from . import audio
    video = Path(video)
    if not (video / "timeline.json").exists():
        return NO_VOICE
    files = [(e, f) for e, f in audio.sources(video, tl.load(video)) if tl.audio_role(e) == "narration"]
    if not files:
        return NO_VOICE
    e, f = files[0]
    return audio.measure(f)[0] + e.get("gain", 0)


def _tracks(video):
    p = Path(video) / "audio" / "tracks.json"
    return [e for e in (json.loads(p.read_text()) if p.exists() else []) if e.get("file") != BED]


def _rebuild(video):
    if (Path(video) / "timeline.json").exists():
        tl.build(video)


def remove(video):
    video = Path(video)
    atomic_json(video / "audio" / "tracks.json", _tracks(video))
    (video / BED).unlink(missing_ok=True)
    beats = video / "audio" / "beats.json"
    if beats.exists() and json.loads(beats.read_text()).get("source") == BED:
        beats.unlink()
    _rebuild(video)
    print("bed removed: audio/bed.wav, its audio/tracks.json entry and its beat grid")


def make(video, seconds=None, key="C", bpm=72.0):
    """Write the bed, its track entry and its beat grid; returns the entry."""
    from . import audio
    from .sfx import write_wav
    video = Path(video)
    seconds = seconds or _length(video)
    if not seconds:
        raise SystemExit("no length for the bed: the video has no timeline yet; pass --seconds")
    if not 40 <= bpm <= 160:
        raise SystemExit("--bpm: a slow pulse between 40 and 160")
    parse_key(key)
    try:
        buf = render(seconds, key, bpm)
    except ImportError:
        raise SystemExit("the bed needs numpy and soundfile: run `studio doctor --fetch --extra audio`")
    (video / "audio").mkdir(parents=True, exist_ok=True)
    write_wav(video / BED, buf)
    bed_lufs = audio.measure(video / BED)[0]
    entry = {"file": BED, "start": 0.0, "gain": round(voice_lufs(video) - BED_UNDER - bed_lufs, 1), "role": "music"}
    atomic_json(video / "audio" / "tracks.json", _tracks(video) + [entry])
    beats_f = video / "audio" / "beats.json"
    if beats_f.exists() and json.loads(beats_f.read_text()).get("source") != BED:
        print("warn: audio/beats.json was another track's grid; replaced by the bed's")
    beats = grid(seconds, bpm)
    atomic_json(beats_f, {"bpm": bpm, "beats": beats, "downbeats": beats[::4], "hits": [], "source": BED})
    _rebuild(video)
    return entry


def main(args):
    if args.remove:
        remove(args.video)
        return 0
    if not args.bed:
        raise SystemExit("studio music makes one thing, a generated bed: --bed (or --remove to take it out). "
                         "A track of your own goes in audio/tracks.json with role music")
    e = make(args.video, args.seconds, args.key, args.bpm)
    print(f"bed: {BED}, {args.key} at {args.bpm:g} BPM, gain {e['gain']:+.1f} dB ({BED_UNDER:g} LU under the narration "
          "before ducking), a music track in audio/tracks.json; its grid in audio/beats.json (beat_N, downbeat_N)")
    return 0
