"""`studio sfx VIDEO CUES.json`: effects placed on the timeline, and `studio sound-lab`.

CUES.json is a list of cues:

  {"t": 1.5 | "reveal" | {anchor},   when: seconds, a cue or beat name, or an anchor
   "type": "click",                  the category: a synth voice's name, or a type only the kit has
   "sound": "kit:interface-click-001", optional: one specific sound, as provider:name (synth:NAME,
                                     kit:ID), or "kit" for the type's default recording
   "gain": 0,                        dB, optional
   "params": {"freq": 1800},         optional: what a synth reads (freq, decay, length); a recording takes none
   "visual": "land"}                 optional: what the picture does on the effect's frame (VISUALS: cut,
                                     move, land, appear), which audio-check measures and the motion review shows

`t` may be a cue or beat name ("reveal:s1_03", "beat_3", "downbeat_1", "hit_2") from the timeline,
or an anchor as cues.json takes one (timeline.event_time). Naming the cue a scene waits on gives
picture and sound one time on the frame grid.

An effect's sound comes from one resolver (`resolve`): the cue's `sound` id, else its type as a
synth's name, is made by a provider into a Sound, which says where in it the cue lands (`contact`)
and carries a digest for cache keys. Two providers: the synths, small numpy voices (VOICES: click,
pop, thump, whoosh and twenty neutral ones for an explainer's moves, each with a line on what it is
for), and the kit (`Kit`), the sound kit's curated CC0 recordings (soundkit.json). A synth build
(riser, swell) ends on its cue and every other voice starts on it; a recording lands on its
transient peak, measured once at curation, since a recording has a lead-in. Recordings are opt-in:
a cue's type alone keeps its synth voice (a type only the kit has, such as question or dice, plays
the kit's default), and `studio sfx` copies each recording a cue names into assets/sounds/ with its
provenance, so a render reads the video, never the cache. Where each effect sits on a timeline
is one function too (`place`), which the render, the motion review's windows, the cut's snapshot and
audio-check's sync all read. `studio sfx` checks the cues and keeps them as audio/sfx.json; every mix
renders them against the timeline it mixes (`rendered`, into audio/sfx.wav, again only when a
placement changed), so a re-narration moves an effect with its cue. The timeline mixes it at -8 dB
under the narration.

A cue's `visual` tag says what the picture does at that moment, never when: the time is still the cue
or beat the effect names, the beat sheet's one time for picture and sound. The tag lets audio-check
judge the cut's picture there (a cut, a move at its fastest, a landing, an appearance), labels the
effect on the sound sheet, and shows in the motion review's windows. In those reports each effect is
fxN, its place in audio/sfx.json (`effect_id`).

A recording plays at its trim (facts.trim_db in soundkit.json) plus the cue's gain. Kenney's files are
normalised near -1 dBFS, so a kit confirm played 12.9 dB over the voice at gain 0; the trim, measured
at curation (soundkit.trim), brings each to the level of the synth voice of its type by
soundkit.level (the K-weighted loudest 10 ms), so swapping a synth for a recording keeps the mix.

Sound effects are off by default and belong in pauses. The sound lab renders candidates for each
type (the synth's, then the kit's recordings once the kit is fetched), each played alone and in
context (after a sentence of the narration, in its pause), on one page with a radio group per type
and a "Copy choices" export of each type's `sound`, so the choice is made by listening.
"""
import hashlib
import html
import json
import math
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Callable

from . import timeline as tl
from .workspace import atomic_json

RATE = 48_000
SEED = 42
NEEDS = "sfx needs numpy and soundfile: run `studio doctor --fetch --extra audio`"

# The synth provider's table (only Synth reads it): name -> (synth, default length in seconds, where
# its cue falls: "start", or "end" for a build that lands on the cue). Each synth takes the times t of
# its samples and the cue's params (freq, decay, length, as each voice reads them) and returns
# samples within [-1, 1].
VOICES = {}
SYNTH_VERSION = 1       # in every synth's digest: bump it when a voice's sound changes, to re-render


def _voice(name, length, lands="start"):
    def put(fn):
        VOICES[name] = (fn, length, lands)
        return fn
    return put


def _noise(n):
    """Deterministic noise (the LCG the article's synth uses), so a render is identical every run."""
    import numpy as np
    out = np.empty(n)
    s = SEED
    for i in range(n):
        s = (s * 1664525 + 1013904223) & 0xFFFFFFFF
        out[i] = s / 2147483648 - 1
    return out


def _smooth(x, k):
    """A moving average over k samples: noise softened to a hiss, or a hiss to a rumble."""
    import numpy as np
    return np.convolve(x, np.ones(k) / k, mode="same")


def _sin(f, t):
    import numpy as np
    return np.sin(2 * math.pi * f * t)


def _chirp(f0, f1, t):
    """A sine gliding from f0 to f1 over t's span (the phase is the integral of the frequency)."""
    import numpy as np
    span = max(t[-1], 1e-9) if len(t) else 1.0
    return np.sin(2 * math.pi * (f0 * t + (f1 - f0) * t * t / (2 * span)))


def _fade(t, out=0.01):
    """1, falling to 0 over the last `out` seconds, so a voice never ends on a click."""
    import numpy as np
    end = t[-1] if len(t) else 0.0
    return np.clip((end - t) / out, 0, 1)


@_voice("click", 0.05)
def _click(t, p):
    """A UI click: a step, a selection, a value set."""
    import numpy as np
    return _sin(p.get("freq", 1800), t) * np.exp(-t * p.get("decay", 90)) * 0.5


@_voice("pop", 0.15)
def _pop(t, p):
    """Something appearing: a node, a label, a bubble."""
    import numpy as np
    return np.sin(2 * math.pi * (p.get("freq", 600) + 900 * t) * t) * np.exp(-t * p.get("decay", 30)) * 0.4


@_voice("thump", 0.5)
def _thump(t, p):
    """A heavy landing: a box set down, a conclusion arriving."""
    import numpy as np
    return np.sin(2 * math.pi * (p.get("freq", 90) - 60 * t) * t) * np.exp(-t * p.get("decay", 9)) * 0.9


@_voice("whoosh", 0.35)
def _whoosh(t, p):
    """A fast move across the frame: a transition, a camera swing."""
    import numpy as np
    return _noise(len(t)) * np.sin(math.pi * np.minimum(1, t / (len(t) / RATE))) * 0.25


@_voice("soft-tick", 0.03)
def _soft_tick(t, p):
    """A cursor stepping through a list, item by item: quieter and shorter than a click."""
    import numpy as np
    return _sin(p.get("freq", 3000), t) * np.exp(-t * p.get("decay", 160)) * 0.25


@_voice("tap", 0.06)
def _tap(t, p):
    """A finger on a button or a card picked out: a soft, low knock."""
    import numpy as np
    f = p.get("freq", 900)
    return _chirp(1.4 * f, 0.8 * f, t) * np.exp(-t * p.get("decay", 70)) * 0.45


@_voice("confirm", 0.3)
def _confirm(t, p):
    """A check that passes, a right answer: two rising tones a fifth apart."""
    import numpy as np
    f, d = p.get("freq", 880), p.get("decay", 18)
    first, second = t < 0.12, t >= 0.12
    tone = np.where(first, _sin(f, t) * np.exp(-t * d), _sin(1.5 * f, t) * np.exp(-(t - 0.12) * d) * second)
    return tone * _fade(t) * 0.3


@_voice("error", 0.3)
def _error(t, p):
    """A wrong turn or a failing test, without alarm: two soft low buzzes."""
    import numpy as np
    f = p.get("freq", 220)
    buzz = _sin(f, t) + _sin(3 * f, t) / 3 + _sin(5 * f, t) / 5
    gate = ((t % 0.15) < 0.11) * np.exp(-(t % 0.15) * p.get("decay", 12))
    return buzz * gate * _fade(t) * 0.25


@_voice("slide-in", 0.3)
def _slide_in(t, p):
    """A panel or label entering from the side: a rising glide with a hiss under it."""
    import numpy as np
    f, span = p.get("freq", 300), max(t[-1], 1e-9)
    env = np.sin(0.5 * math.pi * t / span) ** 2 * _fade(t, 0.03)
    return (_chirp(f, 3 * f, t) * 0.6 + _smooth(_noise(len(t)), 6) * 0.8) * env * 0.3


@_voice("slide-out", 0.3)
def _slide_out(t, p):
    """A panel or label leaving: the slide-in's glide falling away."""
    import numpy as np
    f, span = p.get("freq", 300), max(t[-1], 1e-9)
    env = np.cos(0.5 * math.pi * t / span) ** 2 * np.clip(t / 0.01, 0, 1)
    return (_chirp(3 * f, f, t) * 0.6 + _smooth(_noise(len(t)), 6) * 0.8) * env * 0.3


@_voice("riser", 0.8, lands="end")
def _riser(t, p):
    """A short build toward a reveal: rising pitch and hiss that end on the cue."""
    import numpy as np
    f, span = p.get("freq", 200), max(t[-1], 1e-9)
    env = (t / span) ** 2 * _fade(t, 0.015)
    return (_chirp(f, 6 * f, t) * 0.5 + _smooth(_noise(len(t)), 3) * 0.5) * env * 0.35


@_voice("drop", 0.6)
def _drop(t, p):
    """Something falling into place, or a number falling: a pitch that drops and settles."""
    import numpy as np
    f = p.get("freq", 400)
    return _chirp(f, f / 6, t) * np.exp(-t * p.get("decay", 5)) * _fade(t) * 0.6


@_voice("snap", 0.04)
def _snap(t, p):
    """A piece snapping into place, a node attaching: a dry, bright crack."""
    import numpy as np
    d = p.get("decay", 250)
    return (np.diff(_noise(len(t) + 1)) * 0.5 + _sin(p.get("freq", 2500), t) * 0.5) * np.exp(-t * d) * 0.5


@_voice("card-flip", 0.12)
def _card_flip(t, p):
    """A card turning over to show its other side: two quick papery ticks."""
    import numpy as np
    n = np.diff(_noise(len(t) + 1)) * 0.5
    d = p.get("decay", 180)
    second = t >= 0.045
    return n * (np.exp(-t * d) + np.exp(-(t - 0.045) * d) * second * 0.8) * 0.3


@_voice("paper-slide", 0.4)
def _paper_slide(t, p):
    """A sheet or panel sliding across the desk: a soft hiss, gentler than a whoosh."""
    import numpy as np
    span = max(t[-1], 1e-9)
    return _smooth(_noise(len(t)), 4) * np.sin(math.pi * t / span) * 0.35


@_voice("pop-small", 0.08)
def _pop_small(t, p):
    """A small thing appearing, one of many (dots, list items): a light pop."""
    import numpy as np
    return np.sin(2 * math.pi * (p.get("freq", 900) + 1400 * t) * t) * np.exp(-t * p.get("decay", 55)) * 0.3


@_voice("pop-large", 0.25)
def _pop_large(t, p):
    """A big thing appearing, the one that matters: a round, lower pop."""
    import numpy as np
    return np.sin(2 * math.pi * (p.get("freq", 300) + 500 * t) * t) * np.exp(-t * p.get("decay", 18)) * _fade(t) * 0.5


@_voice("chime", 1.0)
def _chime(t, p):
    """A milestone, a chapter's end, a result worth remembering: a small bell."""
    import numpy as np
    f, d = p.get("freq", 1046), p.get("decay", 4)
    bell = sum(g * _sin(f * r, t) * np.exp(-t * d * k) for r, g, k in ((1, 1.0, 1), (2.76, 0.5, 1.6), (5.4, 0.25, 2.4)))
    return bell * np.clip(t / 0.002, 0, 1) * _fade(t) * 0.25


@_voice("low-hit", 0.6)
def _low_hit(t, p):
    """A key fact set down, weight without a bang: a soft low hit, rounder than a thump."""
    import numpy as np
    f = p.get("freq", 55)
    body = _sin(f, t) + 0.4 * _sin(2 * f, t)
    return body * np.clip(t / 0.005, 0, 1) * np.exp(-t * p.get("decay", 6)) * _fade(t) * 0.55


@_voice("swell", 1.2, lands="end")
def _swell(t, p):
    """A gentle build into a summary or a big picture: a soft chord that swells to the cue."""
    import numpy as np
    f, span = p.get("freq", 220), max(t[-1], 1e-9)
    chord = _sin(f, t) + 0.6 * _sin(1.5 * f, t) + 0.4 * _sin(2 * f, t)
    return chord * np.sin(0.5 * math.pi * t / span) ** 2 * _fade(t, 0.04) * 0.15


@_voice("glitch", 0.15)
def _glitch(t, p):
    """A bug, a corrupted value, something not quite right: a subtle digital stutter."""
    import numpy as np
    f = p.get("freq", 1200)
    steps = (1.0, 0.0, 1.6, 0.7, 0.0, 2.3, 1.2, 0.0, 0.5, 1.9)       # a fixed pattern, so it is the same every time
    k = np.minimum((t / 0.015).astype(int), len(steps) - 1)
    ratio = np.array(steps)[k]
    return np.sign(_sin(f * np.maximum(ratio, 0.01), t)) * (ratio > 0) * _fade(t) * 0.07


@_voice("shimmer", 0.8)
def _shimmer(t, p):
    """Something new and bright appearing, a highlight: high partials with a soft tremolo."""
    import numpy as np
    f, d = p.get("freq", 2093), p.get("decay", 4)
    tones = sum(_sin(f * r, t) * (1 + 0.5 * _sin(7 + 2 * i, t)) for i, r in enumerate((1, 1.26, 1.5, 2)))
    return tones / 6 * np.clip(t / 0.02, 0, 1) * np.exp(-t * d) * _fade(t) * 0.3


@_voice("key-tick", 0.025)
def _key_tick(t, p):
    """A keystroke as text types out on screen: a tiny clack, one per character or word."""
    import numpy as np
    return (np.diff(_noise(len(t) + 1)) * 0.4 + _sin(p.get("freq", 4000), t) * 0.3) * np.exp(-t * p.get("decay", 300)) * 0.4


@_voice("counter-tick", 0.03)
def _counter_tick(t, p):
    """A number counting up or down, one tick per step: a clean, pitched tick."""
    import numpy as np
    f = p.get("freq", 2200)
    return (_sin(f, t) + 0.3 * _sin(2 * f, t)) * np.exp(-t * p.get("decay", 200)) * 0.25


KINDS = tuple(VOICES)

# What a cue's `visual` tag says the picture does on the effect's frame; audio-check measures it
# (audio_check.VISUAL_FRAMES has each one's tolerance).
VISUALS = {"cut": "the picture cuts to another shot",
           "move": "a move at its fastest (a whoosh, a slide)",
           "land": "a move landing: its motion ends (a thump, a snap)",
           "appear": "something appearing: motion starts (a pop)"}


def effect_id(i):
    """An effect's id in the reports (audio-check's rows, the sound sheet, the motion review): fxN, its
    place in audio/sfx.json from 1."""
    return f"fx{i + 1}"


PARAMS = {"freq": (20, 20_000), "decay": (0.1, 2000), "length": (0.01, 10)}     # each voice reads some of them


def params_problem(p):
    """Why a cue's params can't be rendered, or None: only freq, decay and length, each a number in range."""
    if not isinstance(p, dict):
        return "params must be an object"
    for k, v in p.items():
        if k not in PARAMS:
            return f"unknown param {k!r} ({', '.join(PARAMS)})"
        lo, hi = PARAMS[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
            return f"{k} must be a number from {lo:g} to {hi:g} (got {v!r})"
    return None


def voice(kind, **p):
    """One synth's samples as a float array at RATE, `length` seconds long (the voice's default
    unless given)."""
    return resolve(kind, p).samples


# --- sounds: what an effect is made of -------------------------------------------------------------

@dataclass(frozen=True)
class Sound:
    """One effect's sound, resolved. Its samples (float, mono, at `rate`) are made on first use, so
    placing effects (a snapshot, sync's event times) needs no numpy."""
    id: str             # provider:name
    lands: str          # where its cue falls: "start", "end" (a build) or "peak" (a recording's transient)
    contact: int        # the sample within the sound that lands on the cue
    length: int         # in samples
    digest: str         # provider, name, params and version: what the track's cache key is made of
    make: Callable = field(repr=False, compare=False)
    rate: int = RATE

    @cached_property
    def samples(self):
        return self.make()


def _digest(*parts):
    return hashlib.sha1(json.dumps(parts, sort_keys=True).encode()).hexdigest()[:16]


class Synth:
    """The synth provider: VOICES by name. A provider names its sounds, says what one is for, why
    params can't be made, makes a Sound, and offers the lab its candidates; a kit of recordings or a
    file in the video's assets is another class with these five methods, registered in PROVIDERS."""
    name = "synth"

    def names(self):
        return KINDS

    def about(self, name):
        return (VOICES[name][0].__doc__ or "").strip()

    def problem(self, name, params):
        return params_problem(params)

    def sound(self, name, params, video=None):
        n = int(params.get("length", VOICES[name][1]) * RATE)      # its length, known before it is made

        def make():
            import numpy as np
            return VOICES[name][0](np.arange(n) / RATE, params)
        lands = VOICES[name][2]
        return Sound(f"synth:{name}", lands, n if lands == "end" else 0, n,
                     _digest(self.name, name, params, SYNTH_VERSION), make)

    def candidates(self):
        return {k: [(k, p) for p in CANDIDATES[k]] for k in KINDS}


KIT_VERSION = 1         # in every kit sound's digest: bump it when decoding or resampling changes


class Kit:
    """The kit provider: the sound kit's curated recordings (soundkit.json), by id. A recording lands
    on its cue at its transient peak, not its first sample (a recording has a lead-in): its contact is
    measured once, at curation (soundkit.contact), and read from the manifest's facts with its length,
    so placing one needs neither the file nor numpy. Its samples come from the video's own copy,
    assets/sounds/ID.ogg (put there by `studio sfx`, with its provenance row), checked against the
    manifest's sha256, so a render never reads the cache; without a video (the sound lab) they come
    from the verified kit in the cache. It takes no params; it plays at its trim (facts.trim_db, 0 when
    the manifest has none), and a cue's gain applies on top."""
    name = "kit"
    _loaded = (None, None)

    def _manifest(self):
        """soundkit.json, read again only when the file changes (placing reads it once a cue)."""
        from . import soundkit
        st = soundkit.MANIFEST.stat()
        key = (str(soundkit.MANIFEST), st.st_mtime_ns, st.st_size)
        if self._loaded[0] != key:
            self._loaded = (key, soundkit.load(soundkit.MANIFEST))
        return self._loaded[1]

    def entry(self, name):
        return next(s for s in self._manifest()["sounds"] if s["id"] == name)

    def names(self):
        return tuple(s["id"] for s in self._manifest()["sounds"])

    def types(self):
        from . import soundkit
        return soundkit.types(self._manifest())

    def default(self, kind):
        """The id a cue of type `kind` plays with `"sound": "kit"`; stops when the kit has no sound of it."""
        from . import soundkit
        sid = soundkit.default(kind, self._manifest()) if kind else None
        if sid is None:
            raise SystemExit(f"the sound kit has no {kind!r} sound for \"sound\": \"kit\" (it has {', '.join(self.types())}); "
                             "leave `sound` out for the synth voice")
        return sid

    def about(self, name):
        e = self.entry(name)
        f = e.get("facts", {})
        return (f"{e['type']}: {e['member'].rsplit('/', 1)[-1]} from {self._manifest()['packs'][e['pack']]['title']}"
                + (f", {f['seconds']:g} s, peak at {1000 * f['contact'] / RATE:.0f} ms, {f['centroid_hz']} Hz centroid"
                   if {"seconds", "contact", "centroid_hz"} <= set(f) else ""))

    def problem(self, name, params):
        if params:
            return "a kit sound takes no params (its gain is the cue's `gain`)"
        if not {"contact", "samples"} <= set(self.entry(name).get("facts", {})):
            return "the kit has no measured contact for it (facts.contact and facts.samples)"
        return None

    def sound(self, name, params, video=None):
        from . import soundkit
        e = self.entry(name)
        facts = e["facts"]

        def make():
            import hashlib
            import numpy as np
            if video is None:
                data = soundkit.read_member(e["pack"], e["member"], self._manifest())[0]
            else:
                f = Path(video) / "assets" / library_file(e)
                if not f.is_file():
                    raise SystemExit(f"{video}/assets/{library_file(e)} is missing: `studio sfx` copies a kit sound in, and "
                                     f"`studio asset restore {video}` copies back one a clone lacks (after "
                                     f"`{soundkit.repair()}` if the kit is not fetched)")
                data = f.read_bytes()
            if hashlib.sha256(data).hexdigest() != e["sha256"]:
                raise SystemExit(f"assets/{library_file(e)} is not the kit's {e['pack']}:{e['member']} (sha256 differs); "
                                 "remove it and run `studio sfx` again")
            y = soundkit.decode(data)[0] * 10 ** (trim / 20)
            return np.pad(y, (0, max(0, facts["samples"] - len(y))))[:facts["samples"]].astype(np.float32)
        trim = facts.get("trim_db", 0)
        return Sound(f"kit:{name}", "peak", facts["contact"], facts["samples"],
                     _digest(self.name, name, e["sha256"], facts["contact"], facts["samples"], trim, KIT_VERSION), make)

    def candidates(self):
        """Each type's recordings, its default first; none until the kit is fetched (the lab plays
        them from the cache)."""
        from . import soundkit
        if soundkit.check(self._manifest())[0] != "ok":
            return {}
        out = {}
        for s in sorted(self._manifest()["sounds"], key=lambda s: not s.get("default")):
            out.setdefault(s["type"], []).append((s["id"], {}))
        return out


def library_file(entry):
    """Where a curated sound sits in a video's assets/ (assets.add_library puts it there)."""
    return f"sounds/{entry['id']}{Path(entry['member']).suffix.lower()}"


PROVIDERS = {"synth": Synth(), "kit": Kit()}


def _names(p):
    names = p.names()
    return ", ".join(names) if len(names) <= 30 else f"{', '.join(names[:8])} and {len(names) - 8} more (`studio sound-lab VIDEO` plays them)"


def source(ref):
    """(provider, name) for a cue or a sound name: the cue's `sound` ("provider:name", or "kit" for
    its type's default recording), else its type: a synth's name, or a type only the kit has sounds
    for (question, dice, ...), which plays that type's default recording."""
    kind_of = ref.get("type") if isinstance(ref, dict) else None
    if isinstance(ref, dict):
        ref = ref.get("sound", kind_of)
    if ref == "kit":
        return PROVIDERS["kit"], PROVIDERS["kit"].default(kind_of)
    kind, name = ref.split(":", 1) if isinstance(ref, str) and ":" in ref else ("", ref)     # a path may hold a colon
    if not kind and name not in VOICES and name in PROVIDERS["kit"].types():
        return PROVIDERS["kit"], PROVIDERS["kit"].default(name)
    p = PROVIDERS.get(kind or "synth")
    if p is None:
        raise SystemExit(f"unknown effect {ref!r}: no sound provider {kind!r} ({', '.join(PROVIDERS)})")
    if name not in p.names():
        raise SystemExit(f"unknown effect {ref!r}: {_names(p)}")
    return p, name


def resolve(ref, params=None, at=None, video=None):
    """The Sound for a cue (its `sound` or type, and its params) or for a sound name and `params`.
    Stops on an unknown sound or params its provider can't make, naming the effect `at` a time when
    given. `video` is where a recording's samples come from (its assets/); placing needs none."""
    p, name = source(ref)
    params = (ref.get("params", {}) if isinstance(ref, dict) else {}) if params is None else params
    why = p.problem(name, params)
    if why:
        raise SystemExit(f"effect {name if at is None else f'at {at!r}'}: {why}")
    return p.sound(name, params, video)


# --- placing effects on a timeline -----------------------------------------------------------------

def _time(t, timeline):
    if isinstance(t, (int, float)):
        return float(t)
    if isinstance(t, dict):         # an anchor, as cues.json takes one: the same time a scene's cue gets
        try:
            return tl.event_time(timeline, t)
        except (ValueError, KeyError):
            return None
    if t in timeline.get("cues", {}):
        return timeline["cues"][t]
    b = timeline.get("beats", {})
    for prefix, key in (("downbeat_", "downbeats"), ("beat_", "beats"), ("hit_", "hits")):
        if t.startswith(prefix) and t[len(prefix):].isdigit():
            i = int(t[len(prefix):]) - 1
            if 0 <= i < len(b.get(key, [])):
                return b[key][i]
    return None


def resolve_time(t, timeline):
    if isinstance(t, dict):         # an anchor: say why it has no time
        try:
            return tl.event_time(timeline, t)
        except (ValueError, KeyError) as e:
            raise SystemExit(f"no time for cue {t!r}: {e}")
    at = _time(t, timeline)
    if at is None:
        raise SystemExit(f"no time for cue {t!r}")
    return at


def unresolved(cues, timeline):
    """The effect times in `cues` this timeline has no time for (a cue a re-narration dropped)."""
    return [c["t"] for c in cues if _time(c["t"], timeline) is None]


@dataclass(frozen=True)
class Placement:
    """One effect on a timeline, in samples at RATE: its sound spans start to end and its contact
    lands on the cue's time. A build longer than the time before its cue is cut at 0, so its start
    is later than end minus its length. A cue with no time here has None for all four."""
    cue: dict
    time: float | None
    start: int | None
    end: int | None
    contact: int | None
    gain: float         # dB
    sound: Sound


def place(cues, timeline, strict=True, video=None):
    """Every cue placed on this timeline, its sound's contact on the cue's time (a recording's peak,
    a build's end, else its first sample). `strict` stops on a time the timeline doesn't have (a
    render needs every one); otherwise that cue is placed nowhere (a snapshot lists it). `video`:
    where recordings' samples come from, for a render."""
    out = []
    for c in cues:
        s = resolve(c, video=video)
        at = resolve_time(c["t"], timeline) if strict else _time(c["t"], timeline)
        if at is None:
            out.append(Placement(c, None, None, None, None, c.get("gain", 0), s))
            continue
        contact = int(at * RATE)
        first = contact - s.contact
        out.append(Placement(c, at, max(0, first), first + s.length, contact, c.get("gain", 0), s))
    return out


def _mix(placed, duration):
    import numpy as np
    end = max(p.end for p in placed) if placed else RATE
    buf = np.zeros(int(max(end, duration * RATE)) + RATE, dtype=np.float32)
    for p in placed:
        v = p.sound.samples[p.start - (p.contact - p.sound.contact):]       # less a cut build's head
        buf[p.start:p.start + len(v)] += (v * 10 ** (p.gain / 20)).astype(np.float32)
    return buf


def render(cues, timeline):
    """The effects on one float track, unclipped: the timeline's -8 dB comes later, in the mix, so an
    effect over full scale here is not over it there, and the master's limiter takes what still is."""
    return _mix(place(cues, timeline), timeline["duration"])


def write_wav(path, buf, subtype="PCM_24"):
    import soundfile as sf
    sf.write(path, buf, RATE, subtype=subtype)


def check(cues, timeline):
    """Stop on an effect with no time in this timeline, a sound the resolver can't make (an unknown
    type or sound, params its provider can't render), a gain that isn't a number or a visual tag
    that isn't one of VISUALS."""
    for c in cues:
        resolve_time(c["t"], timeline)
        resolve(c, at=c["t"])
        if not isinstance(c.get("gain", 0), (int, float)):
            raise SystemExit(f"effect at {c['t']!r}: gain must be dB")
        if "visual" in c and c["visual"] not in VISUALS:
            raise SystemExit(f"effect at {c['t']!r}: visual must be one of {', '.join(VISUALS)}, what the picture does on "
                             f"its frame (got {c['visual']!r})")


TRACK_VERSION = 1       # in the track's key: bump it when placing or mixing changes how the track sounds


def key(placed, duration):
    """The rendered track's identity: each effect's sound digest, time and gain, and the track's
    length. Not this file's bytes, so an edit elsewhere in the kit keeps the render."""
    return _digest(TRACK_VERSION, duration, [[p.sound.digest, p.time, p.gain] for p in placed])


def rendered(video, timeline):
    """audio/sfx.wav for this timeline: audio/sfx.json's cues placed on it and rendered, again only
    when the key changed (kept beside the mix cache). A re-render rewrites the file, so the mix's
    stamp of it (audio.inputs: its size and time) moves with it."""
    video = Path(video)
    cues = json.loads((video / "audio" / "sfx.json").read_text())
    if unresolved(cues, timeline):
        raise SystemExit(f"audio/sfx.json: no time for {', '.join(map(repr, unresolved(cues, timeline)))} in the "
                         "timeline (a re-narration drops a reveal: cue whose hold is gone); `studio sfx VIDEO CUES` "
                         "with times that exist")
    placed = place(cues, timeline, video=video)
    k = key(placed, timeline["duration"])
    out, kept = video / "audio" / "sfx.wav", video / ".cache" / "sound" / "sfx.key"
    if out.exists() and kept.exists() and kept.read_text() == k:
        return out
    try:
        write_wav(out, _mix(placed, timeline["duration"]), "FLOAT")
    except ImportError:
        if not out.exists():
            raise SystemExit(NEEDS)
        # a video from before effects were placed at mix time: its render, at the times it was made
        print(f"warn: audio/sfx.wav kept as rendered, effects not re-placed ({NEEDS})")
        return out
    kept.parent.mkdir(parents=True, exist_ok=True)
    kept.write_text(k)
    return out


def pinned(cue):
    """The cue as audio/sfx.json keeps it: a recording named by its id ("kit:ID"), so `"sound": "kit"`
    and a type only the kit has say which recording they play, whatever a later manifest's default."""
    p, name = source(cue)
    return {**cue, "sound": f"kit:{name}"} if p.name == "kit" else cue


def copy_in(video, cues):
    """Copy every kit sound the cues play into the video's assets/sounds/ with its provenance row
    (assets.add_library, from the verified kit), unless it is there already as the manifest's file,
    so a render never reads the cache. Stops with the doctor's repair when the kit is not fetched.
    Returns the files copied."""
    import hashlib
    from . import assets
    kit, done = PROVIDERS["kit"], []
    for sid in dict.fromkeys(name for p, name in map(source, cues) if p is kit):
        e = kit.entry(sid)
        f = Path(video) / "assets" / library_file(e)
        row = next((r for r in assets.read(video) if r["file"] == library_file(e)), None)
        if f.is_file() and row and row["sha256"] == e["sha256"] == hashlib.sha256(f.read_bytes()).hexdigest():
            continue
        done.append(assets.add_library(video, sid)["file"])
    return done


def main(args):
    video = Path(args.video)
    cues = json.loads(Path(args.cues).read_text())
    try:
        import numpy, soundfile  # noqa: F401  (every mix renders the effects)
    except ImportError:
        raise SystemExit(NEEDS)
    check(cues, tl.build(video, quiet=True))      # cue and beat names resolve against the current sources
    cues = [pinned(c) for c in cues]
    copied = copy_in(video, cues)
    atomic_json(video / "audio" / "sfx.json", cues)
    rendered(video, tl.build(video))
    print(f"{len(cues)} effects → audio/sfx.json (each mix places them on the current timeline)"
          + "".join(f"\n  copied in assets/{f} from the sound kit" for f in copied))
    return 0


# --- the sound lab ---------------------------------------------------------------------------------

# Three candidates per voice: its default and two neighbours, by pitch where it has one, else by length.
CANDIDATES = {
    "click": [{"freq": 1200}, {"freq": 1800}, {"freq": 2600, "decay": 140}],
    "pop": [{"freq": 400}, {"freq": 600}, {"freq": 900, "decay": 45}],
    "thump": [{"freq": 60}, {"freq": 90}, {"freq": 120, "decay": 14}],
    "whoosh": [{"length": 0.25}, {"length": 0.35}, {"length": 0.6}],
    "soft-tick": [{"freq": 2400}, {}, {"freq": 3800}],
    "tap": [{"freq": 700}, {}, {"freq": 1200}],
    "confirm": [{"freq": 660}, {}, {"freq": 1046}],
    "error": [{"freq": 165}, {}, {"freq": 294}],
    "slide-in": [{"length": 0.2}, {}, {"length": 0.45}],
    "slide-out": [{"length": 0.2}, {}, {"length": 0.45}],
    "riser": [{"length": 0.5}, {}, {"length": 1.2}],
    "drop": [{"freq": 300}, {}, {"freq": 600}],
    "snap": [{"freq": 1800}, {}, {"freq": 3400}],
    "card-flip": [{"decay": 120}, {}, {"decay": 260}],
    "paper-slide": [{"length": 0.25}, {}, {"length": 0.6}],
    "pop-small": [{"freq": 700}, {}, {"freq": 1200}],
    "pop-large": [{"freq": 220}, {}, {"freq": 420}],
    "chime": [{"freq": 784}, {}, {"freq": 1568}],
    "low-hit": [{"freq": 45}, {}, {"freq": 70}],
    "swell": [{"length": 0.8}, {}, {"length": 1.8}],
    "glitch": [{"freq": 800}, {}, {"freq": 1800}],
    "shimmer": [{"freq": 1568}, {}, {"freq": 2637}],
    "key-tick": [{"freq": 3000}, {}, {"freq": 5000}],
    "counter-tick": [{"freq": 1600}, {}, {"freq": 3000}],
}


def lab(video):
    """out/sound-lab/index.html: every provider's candidates for each effect type, alone and in a pause
    of the narration."""
    import numpy as np
    video = Path(video)
    out = video / "out" / "sound-lab"
    out.mkdir(parents=True, exist_ok=True)
    t = tl.load(video)
    narr = video / "audio" / "narration.mp3"
    rows = []
    for provider in PROVIDERS.values():
        for kind, options in provider.candidates().items():
            for i, (name, p) in enumerate(options, 1):
                sound = resolve(f"{provider.name}:{name}", p)
                v = sound.samples.astype(np.float32)
                alone = np.zeros(max(int(1.5 * RATE), len(v) + RATE), dtype=np.float32)
                alone[RATE // 4:RATE // 4 + len(v)] = v
                stem = f"{provider.name}-{kind}-{i}"          # a file per provider, kind and candidate
                write_wav(out / f"{stem}_alone.wav", alone)
                rows.append({"kind": kind, "n": i, "stem": stem, "params": p, "alone": f"{stem}_alone.wav", "sound": sound,
                             "cue": {"sound": sound.id, **({"params": p} if p else {})},
                             "provider": provider.name, "about": provider.about(name)})
    if narr.exists() and t["tracks"]["narration"]:
        # In context: the first sentence's ending and its pause, with the effect placed 0.3 s after it.
        from . import proc
        s = t["tracks"]["narration"][0]
        pcm = proc.ffmpeg("-i", narr, "-t", f"{s['end'] + 0.3:.2f}", "-f", "f32le", "-ac", "1", "-ar", RATE, "-",
                          capture_output=True).stdout
        voice_pcm = np.frombuffer(pcm, dtype=np.float32)
        for r in rows:
            v = r["sound"].samples.astype(np.float32)
            n = int((s["end"] + 1.2) * RATE) + len(v)
            buf = np.zeros(n + RATE, dtype=np.float32)
            buf[:len(voice_pcm)] = voice_pcm[:len(buf)]
            i = max(0, int((s["end"] + 0.3) * RATE) - r["sound"].contact)        # its contact 0.3 s into the pause
            buf[i:i + len(v)] += v[:len(buf) - i] * 0.7
            name = f"{r['stem']}_context.wav"
            write_wav(out / name, buf)
            r["context"] = name
    from . import soundkit
    fetched = soundkit.check()[0] == "ok"
    (out / "index.html").write_text(lab_html(rows, t, None if fetched else soundkit.repair()), encoding="utf-8")
    return out / "index.html"


def lab_html(rows, t, kit_missing=None):
    """The lab's page: a radio group per type, the synth voice's candidates and then the kit's
    recordings (when fetched; `kit_missing` is the repair otherwise). Each radio's value is the cue's
    sound (and params), which "Copy choices" exports per type."""
    kinds = list(dict.fromkeys(r["kind"] for r in rows))
    blocks = []
    for k in kinds:
        of = [r for r in rows if r["kind"] == k]
        items = "".join(
            f'<label class="c"><input type="radio" name="{k}" value="{html.escape(json.dumps(r["cue"]))}"{" checked" if r is of[0] else ""}> '
            f'<b>{r["sound"].id}</b>' + (f' <code>{json.dumps(r["params"])}</code>' if r["params"] else "")
            + (f' <span class="about">{html.escape(r["about"])}</span>' if r["provider"] != "synth" else "")
            + f'<audio controls preload="none" src="{r["alone"]}"></audio>'
            + (f'<audio controls preload="none" src="{r["context"]}"></audio>' if r.get("context") else "")
            + "</label>" for r in of)
        about = html.escape(next((r["about"] for r in of if r["provider"] == "synth"), "recordings only (no synth voice)"))
        blocks.append(f"<fieldset><legend>{k}</legend>" + (f'<p class="about">{about}</p>' if about else "") + f"{items}</fieldset>")
    kit_note = ("<p>Recordings from the sound kit land on their peak; they are listed after each type's synth voices."
                + (f" The kit is not fetched, so none are listed: <code>{html.escape(kit_missing)}</code>." if kit_missing else "")
                + "</p>")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sound lab</title><style>
:root{{--bg:#0b0e12;--ink:#e6ebf0;--muted:#8c97a4;--line:#232b34;--accent:#8fd3ff}}
@media (prefers-color-scheme:light){{:root{{--bg:#f5f6f7;--ink:#151a20;--muted:#5b6672;--line:#dde2e7;--accent:#0a6fa8}}}}
body{{margin:0;padding:24px 16px;background:var(--bg);color:var(--ink);font:15px/1.5 system-ui,sans-serif;max-width:900px;margin-inline:auto}}
fieldset{{border:1px solid var(--line);border-radius:8px;margin:16px 0;padding:8px 16px}}legend{{padding:0 8px;color:var(--muted)}}
p.about{{margin:4px 0 8px;color:var(--muted);font-size:14px}}span.about{{color:var(--muted);font-size:13px}}.c{{display:flex;gap:12px;align-items:center;flex-wrap:wrap;padding:6px 0}}code{{color:var(--muted);font-size:12px}}audio{{height:32px}}
button{{font:inherit;padding:6px 14px;border-radius:6px;border:1px solid var(--accent);background:none;color:var(--accent);cursor:pointer}}
pre{{background:none;border:1px solid var(--line);padding:12px;border-radius:8px;white-space:pre-wrap}}
</style></head><body><h1>Sound lab</h1>
<p>Each candidate plays alone, then (when the narration exists) in the pause after the first sentence. Pick one per type; "Copy choices" gives each type's cue <code>sound</code>.</p>
{kit_note}{''.join(blocks)}<button id="copy" type="button">Copy choices</button><pre id="out" hidden></pre>
<script>
document.getElementById('copy').addEventListener('click',()=>{{
  const pick={{}};document.querySelectorAll('input[type=radio]:checked').forEach(r=>pick[r.name]=JSON.parse(r.value));
  const text=JSON.stringify(pick);const out=document.getElementById('out');out.textContent=text;out.hidden=false;
  if(navigator.clipboard)navigator.clipboard.writeText(text).catch(()=>{{}});
}});
</script></body></html>
"""


def main_lab(args):
    print(lab(args.video))
    return 0
