"""The sound kit: recorded CC0 effects, listed in a committed manifest and fetched once into the cache.

soundkit.json sits beside this module, so `studio init` pins it with the kit and a pinned video's
library never moves. It lists:

  packs   {id: {title, version, url, sha256, bytes, license, creator, homepage, unpack}}: a zip,
          pinned by digest and size, CC0 only, and `unpack` the glob patterns of the members a
          sound may be (the audio; never the shortcuts a pack also ships)
  sounds  [{id, pack, member, type, default?, sha256, facts?}]: the curated sounds, one a line, each a
          member of a pack with its own digest, a type (what it is for; one sound of each type is its
          default) and measured facts (`measure`: its length and contact in samples at sfx.RATE, peak,
          attack, brightness, floor and events), which the sfx kit provider places it by, and
          its trim_db (`trim`): the gain that brings it to the level of the synth voice of its type

`studio doctor --fetch --sounds` downloads every pack into $STUDIO_HOME/cache/sounds/, verified, and
leaves it zipped: a sound is read from the verified zip by its member name, so nothing edited in the
cache and no archive's paths reach a video. A video never reads the cache when it renders: `studio
asset library` copies a sound into the video with its provenance, read from the verified zip itself.
"""
import io
import json
import re
import sys
import zipfile
import fnmatch
from pathlib import Path

from . import fetch
from .env import ROOT

MANIFEST = Path(__file__).with_name("soundkit.json")
LICENSES = {"CC0-1.0": "CC0 1.0"}          # SPDX id: how a credit line writes it
SLUG = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
HEX64 = re.compile(r"[0-9a-f]{64}")
SCHEMES = ("https://",)                    # a pack's url (tests add file://)
PACK_KEYS = {"title": str, "version": str, "url": str, "sha256": str, "bytes": int, "license": str,
             "creator": str, "homepage": str, "unpack": list}
SOUND_KEYS = {"id": str, "pack": str, "member": str, "type": str, "sha256": str}
TRIM_RANGE = (-30.0, 12.0)                 # dB a sound's trim may be


def repair():
    return f"{ROOT / 'bin/studio'} doctor --fetch --sounds"


def problems(manifest):
    """Every way `manifest` breaks the schema, as sentences; empty when it is valid."""
    out = []
    if manifest.get("version") != 1:
        out.append("version must be 1")
    packs = manifest.get("packs")
    if not isinstance(packs, dict) or not packs:
        return out + ["packs must be a non-empty object"]
    for pid, p in packs.items():
        where = f"pack {pid}"
        if not SLUG.fullmatch(pid):
            out.append(f"{where}: the id must be lower-case words joined by hyphens")
        mistyped = [f"{where}: {key} must be a {kind.__name__}" for key, kind in PACK_KEYS.items()
                    if not isinstance(p, dict) or not isinstance(p.get(key), kind)]
        if mistyped:
            out += mistyped
            continue
        if not p["url"].startswith(SCHEMES) or not p["homepage"].startswith("https://"):
            out.append(f"{where}: url and homepage must be https")
        if not HEX64.fullmatch(p["sha256"]):
            out.append(f"{where}: sha256 must be 64 lower-case hex digits")
        if p["bytes"] <= 0:
            out.append(f"{where}: bytes must be positive")
        if p["license"] not in LICENSES:
            out.append(f"{where}: license {p['license']!r} is not allowed (only {', '.join(LICENSES)})")
        if not p["creator"].strip() or not p["title"].strip():
            out.append(f"{where}: title and creator must not be empty")
        if not p["unpack"] or not all(isinstance(m, str) and m for m in p["unpack"]):
            out.append(f"{where}: unpack must list glob patterns")
    sounds = manifest.get("sounds")
    if not isinstance(sounds, list):
        return out + ["sounds must be a list"]
    seen, defaults = set(), {}
    for i, s in enumerate(sounds):
        where = f"sound {s.get('id', i) if isinstance(s, dict) else i}"
        if not isinstance(s, dict) or any(not isinstance(s.get(k), t) for k, t in SOUND_KEYS.items()):
            out.append(f"{where}: needs " + ", ".join(SOUND_KEYS) + " as strings")
            continue
        if not SLUG.fullmatch(s["id"]):
            out.append(f"{where}: the id must be lower-case words joined by hyphens")
        if s["id"] in seen:
            out.append(f"{where}: the id is used twice")
        seen.add(s["id"])
        if not HEX64.fullmatch(s["sha256"]):
            out.append(f"{where}: sha256 must be 64 lower-case hex digits")
        if s["pack"] not in packs:
            out.append(f"{where}: no pack {s['pack']}")
        elif not allowed_member(packs[s["pack"]], s["member"]):
            out.append(f"{where}: {s['member']} is not one of the pack's sounds (a relative name matching its unpack patterns)")
        if not isinstance(s.get("facts", {}), dict):
            out.append(f"{where}: facts must be an object")
        elif not _contact_ok(s.get("facts", {})):
            out.append(f"{where}: facts.contact must be a sample within facts.samples")
        elif not _trim_ok(s.get("facts", {})):
            out.append(f"{where}: facts.trim_db must be dB from {TRIM_RANGE[0]:g} to {TRIM_RANGE[1]:g}")
        if s.get("default", False) is not False:
            if s["default"] is not True:
                out.append(f"{where}: default must be true or left out")
            elif s["type"] in defaults:
                out.append(f"{where}: {s['type']} already has a default ({defaults[s['type']]})")
            else:
                defaults[s["type"]] = s["id"]
    return out


def _contact_ok(facts):
    if "contact" not in facts and "samples" not in facts:
        return True
    c, n = facts.get("contact"), facts.get("samples")
    return all(isinstance(v, int) and not isinstance(v, bool) for v in (c, n)) and 0 <= c < n


def _trim_ok(facts):
    v = facts.get("trim_db", 0)
    return isinstance(v, (int, float)) and not isinstance(v, bool) and TRIM_RANGE[0] <= v <= TRIM_RANGE[1]


def load(path=None):
    path = path or MANIFEST
    m = json.loads(Path(path).read_text())
    bad = problems(m)
    if bad:
        raise SystemExit(f"{path} is not a valid sound kit manifest:\n  " + "\n  ".join(bad))
    return m


def allowed_member(pack, member):
    """Whether `member` is one of the pack's sounds: a relative name with no `..`, matching `unpack`."""
    parts = member.replace("\\", "/").split("/")
    return (not member.startswith(("/", "\\")) and ":" not in member and ".." not in parts
            and any(fnmatch.fnmatchcase(member, pat) for pat in pack["unpack"]))


def archive(pid, pack):
    """Where a pack's zip is cached: named by its digest, so manifests of two kits never collide."""
    return fetch.cache_root() / "sounds" / f"{pid}-{pack['sha256'][:12]}.zip"


def state(pid, pack):
    """'ok', 'missing' (never fetched) or 'changed' (the cached zip is not the pinned one)."""
    z = archive(pid, pack)
    if not z.exists():
        return "missing"
    return "ok" if fetch.verified(z, pack["sha256"]) else "changed"


def fetch_kit(manifest=None, progress=sys.stderr):
    """Download every pack, verified. Raises fetch.Offline when a host can't be reached."""
    manifest = manifest or load()
    fetch.cache_root(create=True)
    for pid, pack in manifest["packs"].items():
        if state(pid, pack) == "ok":
            continue
        z = fetch.fetch(pack["url"], archive(pid, pack), pack["sha256"], pack["bytes"], progress=progress)
        print(f"sound kit: {pack['title']}: {z}", file=progress or sys.stdout)


def hosts(manifest=None):
    """The hosts the sound kit downloads from, as URLs of their roots."""
    from urllib.parse import urlsplit
    return list(dict.fromkeys(f"{u.scheme}://{u.netloc}/" for u in
                              (urlsplit(p["url"]) for p in (manifest or load())["packs"].values())))


def check(manifest=None):
    """(level, detail): 'ok' when every pack is fetched and verified, else 'missing' with which."""
    manifest = manifest or load()
    states = {pid: state(pid, p) for pid, p in manifest["packs"].items()}
    bad = {pid: s for pid, s in states.items() if s != "ok"}
    if not bad:
        return "ok", f"{len(states)} packs verified in {fetch.cache_root() / 'sounds'}"
    if all(s == "missing" for s in bad.values()) and len(bad) == len(states):
        return "missing", "not fetched (recorded effects are optional; synth voices need nothing)"
    return "missing", "; ".join(f"{pid} {s}" for pid, s in bad.items())


def sound(sid, manifest=None):
    manifest = manifest or load()
    for s in manifest["sounds"]:
        if s["id"] == sid:
            return s
    raise SystemExit(f"no sound {sid!r} in the sound kit; name one as PACK:MEMBER, e.g. "
                     f"{next(iter(manifest['packs']))}:Audio/<file>.ogg")


def default(kind, manifest=None):
    """The id of the curated sound a type uses unless a cue names another: the one marked default,
    else the type's first; None when the kit has no sound of that type."""
    manifest = manifest or load()
    of = [s for s in manifest["sounds"] if s["type"] == kind]
    return next((s["id"] for s in of if s.get("default")), of[0]["id"] if of else None)


def types(manifest=None):
    """The effect types the kit has sounds for, in the manifest's order."""
    return list(dict.fromkeys(s["type"] for s in (manifest or load())["sounds"]))


def read_member(pid, member, manifest=None):
    """(the member's bytes, its pack): read from the cached zip after verifying the zip's digest, so
    a file edited in the unpacked folder can't reach a video."""
    manifest = manifest or load()
    pack = manifest["packs"].get(pid)
    if pack is None:
        raise SystemExit(f"no pack {pid!r} in the sound kit (packs: {', '.join(manifest['packs'])})")
    if not allowed_member(pack, member):
        raise SystemExit(f"{member} is not one of {pid}'s sounds (members matching {', '.join(pack['unpack'])})")
    z = archive(pid, pack)
    if not fetch.verified(z, pack["sha256"]):
        raise SystemExit(f"the sound kit's {pid} is {'not fetched' if not z.exists() else 'not the pinned zip'}; "
                         f"run `{repair()}`")
    with zipfile.ZipFile(z) as f:
        try:
            return f.read(member), pack
        except KeyError:
            raise SystemExit(f"{pid} has no member {member}") from None


# --- decoding and measuring a recording -----------------------------------------------------------

ENVELOPE = 0.002        # seconds: the RMS window a contact is found on (a transient's scale)
NEAR_PEAK = -6.0        # dB: the first envelope peak this close to the loudest is the contact
ONSET = -30.0           # dB under the loudest envelope that marks where the sound begins
SILENT = -50.0          # dB under it that counts as silence (a lead-in or a tail)
EVENT_RISE = 12.0       # dB an envelope climbs from a dip to count as a new event
EVENT_NEAR = -10.0      # dB under the loudest that a new event must reach


def resample(y, rate, to):
    """y at `rate` resampled to `to`, band-limited and deterministic: by FFT, over a span padded with
    silence to a whole number of periods of the ratio (so 44.1 kHz to 48 kHz is exact), then trimmed."""
    import math
    import numpy as np
    if rate == to:
        return y
    g = math.gcd(rate, to)
    up, down = to // g, rate // g
    n = len(y)
    padded = -(-(n + 2048) // down) * down             # silence after it, so the wrap-around is silent too
    spectrum = np.fft.rfft(np.pad(y.astype(np.float64), (0, padded - n)))
    m = padded // down * up
    out = np.fft.irfft(spectrum, m) * (m / padded)       # the spectrum cut or padded with zeros at m
    return out[:-(-n * up // down)].astype(np.float32)


def decode(data, to=None, fallback=True):
    """A recording's bytes (an .ogg, a .wav) as (mono float32 samples at `to`, default sfx.RATE, and the
    largest absolute sample before resampling). Stereo is folded to mono by its mean. soundfile reads
    Ogg Vorbis (libsndfile does); a format it can't read goes through ffmpeg at `to`, unless not
    `fallback`: ffmpeg's resampler is not this one, and moved a contact by up to 7.4 ms, so a kit sound,
    whose facts were measured through soundfile, refuses it."""
    import numpy as np
    import soundfile as sf
    from .sfx import RATE
    to = to or RATE
    try:
        y, rate = sf.read(io.BytesIO(data), dtype="float32", always_2d=True)
    except (RuntimeError, sf.LibsndfileError) as e:
        if not fallback:
            raise SystemExit(f"soundfile could not read this recording ({e}); the kit's sounds are measured as soundfile "
                             "decodes them, so it plays none through another decoder: run `studio doctor --fetch --extra "
                             "audio` for a soundfile with Ogg Vorbis") from None
        from . import proc
        pcm = proc.ffmpeg("-i", "-", "-f", "f32le", "-ac", "1", "-ar", to, "-", input=data, capture_output=True).stdout
        y, rate = np.frombuffer(pcm, dtype=np.float32)[:, None], to
    raw = float(np.abs(y).max()) if y.size else 0.0
    return resample(y.mean(axis=1), rate, to), raw


def envelope(y, rate, seconds=ENVELOPE):
    """The RMS of y over a centred window of `seconds`, a sample at a time."""
    import numpy as np
    k = max(1, int(seconds * rate))
    c = np.concatenate([[0.0], np.cumsum(y.astype(np.float64) ** 2)])
    lo = np.clip(np.arange(len(y)) - k // 2, 0, len(y))
    hi = np.clip(lo + k, 0, len(y))
    return np.sqrt((c[hi] - c[lo]) / np.maximum(hi - lo, 1))


def contact(y, rate):
    """The sample a recording lands on its cue at: its transient peak. On a 2 ms RMS envelope, the
    first local peak (the largest within 5 ms either side) within NEAR_PEAK dB of the loudest, so an
    attack wins over a louder ring after it unless the ring is 6 dB louder, and a build with no attack
    lands on its loudest moment."""
    import numpy as np
    env = envelope(y, rate)
    if not len(env) or env.max() <= 0:
        return 0
    w = max(1, int(0.005 * rate))
    pad = np.pad(env, (w, w))
    local = np.lib.stride_tricks.sliding_window_view(pad, 2 * w + 1).max(axis=1)
    near = np.nonzero((env >= local) & (env >= env.max() * 10 ** (NEAR_PEAK / 20)))[0]
    return int(near[0])


def _db(x):
    import math
    return 20 * math.log10(x) if x > 1e-10 else -200.0


def measure(y, rate, raw_peak=None):
    """The facts a curated sound records, measured on its decoded samples at `rate`: its length and
    contact in samples, peak, lead-in, attack (onset to contact) and tail of silence, spectral centroid,
    floor (the 10th percentile of its 10 ms frames under the loudest: high for a steady noise) and
    events (bursts that climb EVENT_RISE dB from a dip to within EVENT_NEAR dB of the loudest)."""
    import numpy as np
    env = envelope(y, rate)
    top = float(env.max()) if len(env) else 0.0
    at = contact(y, rate)
    above = np.nonzero(env >= top * 10 ** (ONSET / 20))[0]
    sounding = np.nonzero(env >= top * 10 ** (SILENT / 20))[0]
    onset = int(above[0]) if len(above) else 0
    spectrum = np.abs(np.fft.rfft(y.astype(np.float64))) ** 2
    freq = np.fft.rfftfreq(len(y), 1 / rate)
    frame = int(0.01 * rate)
    frames = np.sqrt(np.mean(y[:len(y) // frame * frame].astype(np.float64).reshape(-1, frame) ** 2, axis=1)) \
        if len(y) >= frame else np.array([top])
    events, low, armed = 0, 0.0, True
    for e in frames:                         # a burst counts once it rises from a dip (or the silence before it) to near the top
        low = min(low, e)
        if armed and e >= frames.max() * 10 ** (EVENT_NEAR / 20) and e >= low * 10 ** (EVENT_RISE / 20):
            events, armed = events + 1, False
        if not armed and e <= frames.max() * 10 ** ((EVENT_NEAR - EVENT_RISE) / 20):
            armed, low = True, e
    return {"seconds": round(len(y) / rate, 3), "samples": len(y), "contact": at,
            "peak_dbfs": round(_db(float(np.abs(y).max()) if len(y) else 0.0), 1),
            **({"raw_peak": round(raw_peak, 4)} if raw_peak is not None else {}),
            "lead_ms": round(1000 * onset / rate, 1), "attack_ms": round(1000 * max(0, at - onset) / rate, 1),
            "tail_ms": round(1000 * (len(y) - 1 - (int(sounding[-1]) if len(sounding) else 0)) / rate, 1),
            "centroid_hz": round(float((freq * spectrum).sum() / max(spectrum.sum(), 1e-20))),
            "floor_db": round(_db(float(np.percentile(frames, 10))) - _db(float(frames.max())), 1) if frames.max() > 0 else 0.0,
            "events": max(events, 1)}


# --- level: how loud a sound plays against the voice -----------------------------------------------

# ITU-R BS.1770's K-weighting at 48 kHz (a high shelf of about +4 dB over 2 kHz, then a high-pass near
# 60 Hz): how loud a sound is heard, not how much energy it carries, so a 90 Hz thump and a 900 Hz
# confirm with one RMS are not one loudness. As two biquads (b, a).
K_WEIGHTING = (((1.53512485958697, -2.69169618940638, 1.19839281085285), (1.0, -1.69065929318241, 0.73248077421585)),
               ((1.0, -2.0, 1.0), (1.0, -1.99004745483398, 0.99007225036621)))
LEVEL_WINDOW = 0.01     # seconds: a sound's level is its loudest this long


def k_weighted(y, rate=48_000):
    """y through the K-weighting's magnitude response (zero-phase, by FFT, over a span padded with
    0.1 s of silence either side so nothing wraps around); at `rate` 48 kHz, the biquads' own."""
    import numpy as np
    pad = int(0.1 * rate)
    n = len(y) + 2 * pad
    spectrum = np.fft.rfft(np.pad(np.asarray(y, dtype=np.float64), (pad, pad)))
    z = np.exp(-1j * np.pi * np.fft.rfftfreq(n, 1 / rate) / (rate / 2))
    for b, a in K_WEIGHTING:
        spectrum *= np.abs((b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z))
    return np.fft.irfft(spectrum, n)[pad:pad + len(y)]


def level(y, rate=48_000):
    """A sound's level in dB (K-weighted dBFS): the power of its loudest LEVEL_WINDOW, K-weighted. The
    kit's trims and audio-check's loud audit both read it, so a trimmed sound at gain 0 is where the
    synth voice of its type is, by the measure that judges it."""
    import numpy as np
    x = k_weighted(y, rate)
    k = max(1, min(len(x), int(LEVEL_WINDOW * rate)))
    if not len(x):
        return -200.0
    c = np.concatenate([[0.0], np.cumsum(x ** 2)])
    p = float(((c[k:] - c[:-k]) / k).max())
    return 10 * np.log10(p) if p > 1e-20 else -200.0


def reference_level(kind):
    """The level a sound of type `kind` is trimmed to: the synth voice of that type at its defaults,
    or for a type only the kit has (question, dice, ...), the median of the synth voices."""
    import statistics
    from . import sfx
    if kind in sfx.VOICES:
        return level(sfx.voice(kind))
    return statistics.median(level(sfx.voice(k)) for k in sfx.VOICES)


def trim(y, kind, rate=48_000):
    """facts.trim_db for a recording's samples y of type `kind`: the dB that brings its level to
    reference_level(kind), to 0.1 dB, within TRIM_RANGE."""
    return round(float(min(TRIM_RANGE[1], max(TRIM_RANGE[0], reference_level(kind) - level(y, rate)))), 1)
