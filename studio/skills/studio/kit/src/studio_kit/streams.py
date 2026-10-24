"""Event streams: many small events (keystrokes, footsteps, ticks) played as one effect, a texture.

Typing is hundreds of keystrokes, too many to be cues: every cue gets a still and a motion-review
window. So one effect in audio/sfx.json carries them all, on the cue a scene waits on for the burst:

  {"t": "type-s1", "type": "key-tick", "stream": "typing:s1",      the label reports use
   "events": [[0.0, "key"], [0.11, "key"], [0.6, "enter"], …],      seconds after the cue, and a kind
   "sounds": {"key": "grains:kit:keys-typing-cherry-blue",          a sound per kind ("*" for the rest)
              "enter": {"sound": "kit:keys-enter-press", "gain": -14}},
   "gain": 0, "under_speech": -6}

A kind's sound is a sound as a cue names one ("kit:ID", "asset:PATH", "synth:NAME"), a pool of them,
or "grains:REF": key-sized grains cut from a take of real typing (the kit's key-take), a few hundred
of them, sorted by brightness ("grains:REF#low" the darkest quarter, for a space bar; "#high" the
brightest, for a backspace). Either may be {"sound", "gain"} for its own level against the others.

How it sounds is the point (references/taste.md): every event plays a different variant than
the one before it of its kind, a little higher or lower and louder or softer, a few milliseconds off
the grid (not when the stream is "exact": true, as typed keys are, which sit on their frames); crowded events thin out (above DENSE events a second each is quieter, so fast typing is a
texture, not a louder one); and an event under a spoken word steps back by `under_speech` dB, so the
voice stays on top and keys in a pause come forward. The stream's sound is one Sound whose contact is
its cue, so placing, the track's key and audio-check's sync treat it as one effect.
"""
import math
import random

STREAM_VERSION = 1
PAD = 0.02              # seconds of room before the first event, for its jitter and a grain's pre-roll
TAIL = 0.4              # seconds after the last event, for its ring
TIMING = 0.004          # seconds an event may fall off the grid
PITCH = 0.04            # a variant's pitch: +-4%
GAIN = 1.5              # and its level: +-1.5 dB
DENSE = 6.0             # events a second (within +-0.18 s) before they thin: -6 dB per doubling past it
UNDER_SPEECH = -6.0     # dB for an event under a spoken word
GRAIN_PEAK = -25.0      # dBFS a grain plays at on the effects track (a recorded key is its own level)
GRAIN = (0.03, 0.085)   # seconds a grain may last


def problem(c):
    """Why a stream effect can't be placed, or None."""
    ev = c.get("events")
    if not isinstance(ev, list) or not ev:
        return "a stream lists its events: [[seconds after the cue, kind], …]"
    for e in ev:
        if not (isinstance(e, list) and len(e) == 2 and isinstance(e[0], (int, float)) and not isinstance(e[0], bool)
                and isinstance(e[1], str)):
            return f"a stream event is [seconds, kind], not {e!r}"
    sounds = c.get("sounds")
    if not isinstance(sounds, dict) or not sounds:
        return "a stream names a sound for each kind of event in `sounds`"
    missing = sorted({k for _, k in ev} - set(sounds) - {"*"}) if "*" not in sounds else []
    if missing:
        return f"no sound for {', '.join(map(repr, missing))} (name one in `sounds`, or \"*\" for the rest)"
    return None


def spec(value):
    """A kind's sound as (members, gain dB, grains selector or None): members are cues the resolver takes."""
    from .sfx import pool_ref
    gain = 0.0
    if isinstance(value, dict) and "gain" in value and set(value) <= {"sound", "gain", "params"}:
        gain = value["gain"]
        value = {k: v for k, v in value.items() if k != "gain"}
        value = value["sound"] if set(value) == {"sound"} else value
    if isinstance(value, str) and value.startswith("grains:"):
        ref, _, part = value[len("grains:"):].partition("#")
        return [pool_ref(ref)], gain, part or "all"
    if isinstance(value, dict) and str(value.get("sound", "")).startswith("grains:"):
        ref, _, part = value["sound"][len("grains:"):].partition("#")
        return [{"sound": ref, "params": value.get("params", {})}], gain, part or "all"
    return [pool_ref(m) for m in (value if isinstance(value, list) else [value])], gain, None


def refs(c):
    """Every sound a stream effect names, as cues the resolver takes (for checking, pinning and copying in)."""
    return [m for v in c["sounds"].values() for m in spec(v)[0]]


def pin(c, pin_member):
    """The stream effect with each kind's sounds pinned (kit defaults named, the video's own recordings
    measured) by `pin_member`, keeping a kind's gain and grains selector."""
    out = {}
    for kind, v in c["sounds"].items():
        members, gain, part = spec(v)
        pinned = [pin_member(m) for m in members]
        if part:
            p = pinned[0]
            ref = p if isinstance(p, str) else p["sound"]
            sound = {"sound": f"grains:{ref}" + ("" if part == "all" else f"#{part}")}
            if not isinstance(p, str):
                sound["params"] = p["params"]
        else:
            sound = {"sound": pinned if len(pinned) > 1 else pinned[0]}
        if gain:
            sound["gain"] = gain
        out[kind] = sound["sound"] if set(sound) == {"sound"} else sound
    return {**c, "sounds": out}


def _words(timeline, a, b):
    return [(w["start"], w["end"]) for s in timeline.get("tracks", {}).get("narration", [])
            for w in s.get("words", []) if w["end"] >= a and w["start"] <= b]


def sound(c, at, timeline, video=None):
    """The stream as one Sound: its contact is the cue (an event at 0 lands on it)."""
    from .sfx import RATE, SEED, Sound, _digest, resolve
    events = sorted(c["events"], key=lambda e: e[0])
    lo, hi = min(0.0, events[0][0]), events[-1][0]
    contact = int(round((PAD - lo) * RATE))
    length = int(round((PAD + hi - lo + TAIL) * RATE))
    label = c.get("stream", "stream")
    words = [] if at is None else [(round(s - at, 3), round(e - at, 3)) for s, e in _words(timeline, at + lo - 1, at + hi + 1)]
    under = c.get("under_speech", UNDER_SPEECH)
    kinds = {k: spec(v) for k, v in c["sounds"].items()}
    jitter = c.get("jitter", True) is not False
    exact = c.get("exact") is True        # events sit on their frames: pitch and gain vary, timing does not
    members = {k: [resolve({**m, "type": c.get("type")}, video=video) for m in ms] for k, (ms, _, _) in kinds.items()}
    digest = _digest("stream", STREAM_VERSION, SEED, label, events, words, under, jitter, exact,
                     {k: [[s.digest for s in members[k]], g, part] for k, (_, g, part) in kinds.items()})

    def make():
        import numpy as np
        rng = random.Random(f"{SEED}:{label}")
        buf = np.zeros(length + RATE, dtype=np.float32)
        variants = {k: _variants(members[k], part) for k, (_, _, part) in kinds.items()}
        times = [e[0] for e in events]
        last, chosen = {}, []
        for off, kind in events:
            k = kind if kind in kinds else "*"
            pool, gain = variants[k], kinds[k][1]
            j = rng.randrange(len(pool))
            if len(pool) > 1 and j == last.get(k):
                j = (j + 1) % len(pool)
            last[k] = j
            chosen.append(j)
            y, hit = pool[j]
            level = gain
            if jitter:
                p = 1 + rng.uniform(-PITCH, PITCH)
                y = np.interp(np.arange(0, len(y) - 1, p), np.arange(len(y)), y)
                hit = int(hit / p)
                level += rng.uniform(-GAIN, GAIN)
                off = off if exact else off + rng.uniform(-TIMING, TIMING)
            near = sum(1 for t in times if abs(t - off) <= 0.18)
            rate = near / 0.36
            level -= 6.0 * math.log2(rate / DENSE) if rate > DENSE else 0.0
            if any(s - 0.03 <= off <= e + 0.03 for s, e in words):
                level += under
            i = contact + int(round(off * RATE)) - hit
            seg = (y * 10 ** (level / 20)).astype(np.float32)[max(0, -i):]
            i = max(0, i)
            buf[i:i + len(seg)] += seg[:len(buf) - i]
        _picks[digest] = chosen
        return buf[:length]
    return Sound(f"stream:{label}", "start", contact, length, digest, make)


_picks = {}             # digest -> the variant each event played, for tests and the lab


def picks(placement):
    """The variant index each event of a placed stream played (renders it if it hasn't been)."""
    placement.sound.samples
    return _picks[placement.sound.digest]


def _variants(sounds, part):
    """[(samples, the sample that lands on the event)] a kind draws from: each sound as it is, or the
    grains cut from a take (`part`: all, low or high)."""
    if part is None:
        return [(s.samples, s.contact) for s in sounds]
    import numpy as np
    from .sfx import RATE
    g = grains(sounds[0].samples, RATE)
    if not g:
        raise SystemExit(f"{sounds[0].id}: no key-sized grains found in it (a take of separate keystrokes is needed)")
    q = max(1, len(g) // 4)
    g = {"all": g, "low": g[:q], "high": g[-q:], "mid": g[q:-q] or g}.get(part)
    if g is None:
        raise SystemExit(f"grains selector #{part}: low, mid, high or none")
    peak = 10 ** (GRAIN_PEAK / 20)
    return [(y / (np.abs(y).max() + 1e-9) * peak, attack(y)) for _, y in g]


def attack(y, share=0.25):
    """The sample where a grain's transient starts: the first to reach `share` of its peak. The grain
    is cut a little before the detected onset, so its real attack is measured, not assumed."""
    import numpy as np
    a = np.abs(y)
    return int(np.argmax(a >= share * (a.max() + 1e-12)))


def onsets(x, rate):
    """Sample indices where a keystroke starts in a take: the envelope rises 10 dB over 12 ms and
    stands 15 dB over the take's floor, at least 48 ms after the last."""
    import numpy as np
    hop = int(rate * 0.004)
    n = len(x) // hop
    if n < 4:
        return []
    env = np.sqrt(np.mean(x[:n * hop].astype(np.float64).reshape(n, hop) ** 2, axis=1) + 1e-12)
    db = 20 * np.log10(env)
    floor = np.percentile(db, 20)
    out = []
    for i in range(3, n):
        if db[i] - db[i - 3:i].min() > 10 and db[i] > floor + 15 and (not out or i - out[-1] > 12):
            out.append(i)
    return [o * hop for o in out]


def grains(x, rate):
    """Key-sized grains cut from a take at its onsets, faded at both ends, darkest first:
    [(spectral centroid Hz, samples)]."""
    import numpy as np
    on = onsets(x, rate)
    out = []
    for a, b in zip(on, on[1:] + [len(x)]):
        length = min(b - a - int(0.006 * rate), int(GRAIN[1] * rate))
        if length < int(GRAIN[0] * rate):
            continue
        g = x[max(0, a - int(TIMING * rate)):a + length].astype(np.float64).copy()
        fade = min(len(g), int(0.02 * rate))
        g[-fade:] *= np.linspace(1, 0, fade)
        g[:48] *= np.linspace(0, 1, min(48, len(g)))
        s = np.abs(np.fft.rfft(g, 4096))
        f = np.fft.rfftfreq(4096, 1 / rate)
        out.append((float((s * f).sum() / (s.sum() + 1e-9)), g))
    return sorted(out, key=lambda c: c[0])


def describe(c):
    """One line for a report: the stream, its events and their kinds."""
    kinds = {}
    for _, k in c["events"]:
        kinds[k] = kinds.get(k, 0) + 1
    return f"{c.get('stream', 'stream')}: {len(c['events'])} events ({', '.join(f'{n} {k}' for k, n in kinds.items())})"

